"""External capability dispatch over graph-native admission and budget rules.

This module is a trusted service boundary, not an agent-importable grant API.
Adapters are supplied by immutable deployment code, never graph-supplied imports.
"""
import hashlib
import json
import re
from uuid import uuid4


class InvocationDenied(RuntimeError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class Broker:
    def __init__(self,graph,principal,adapters,journal):
        self.graph,self.principal,self.adapters=graph,principal,dict(adapters)
        self.journal=journal

    def invoke(self,actor,scope,attempt,fence,invocation,capability,arguments):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}',invocation) or type(fence) is not int:
            raise InvocationDenied('invalid_invocation')
        adapter=self.adapters.get(capability)
        if adapter is None:
            raise InvocationDenied('capability_not_promoted')
        # Validation must be side-effect-free and reject unknown fields/scopes.
        normalized=adapter.validate(scope,arguments)
        params_hash=digest(dict(actor=actor,scope=scope,attempt=attempt,fence=fence,
                               capability=capability,arguments=normalized))
        self.journal.persist(invocation,'intent',dict(invocation=invocation,scope=scope,params_hash=params_hash))
        admitted=self.graph.operation('admit-invocation',actor,scope,attempt=attempt,fence=fence,
            invocation=invocation,capability=capability,generation=adapter.generation,params_hash=params_hash,
            cost_units=adapter.cost_units,max_seconds=adapter.max_seconds)
        if len(admitted)!=1:
            raise InvocationDenied('authority_or_budget_denied')
        if admitted[0]['status']!='admitted':
            # A repeated request returns known state, never redispatches an effect.
            return admitted[0]
        dispatched=self.graph.operation('dispatch-invocation',actor,scope,
            invocation=invocation,params_hash=params_hash)
        if len(dispatched)!=1:
            raise InvocationDenied('dispatch_denied_reconciliation_required')
        try:
            result=adapter.run(invocation,normalized)
            if (not isinstance(result,dict) or result.get('outcome') not in ['succeeded','failed','unknown']):
                raise ValueError('invalid_adapter_result')
        except Exception as exc:
            # Generic errors cannot establish that no external effect occurred.
            # Never persist raw output, exception text, or credentials.
            result={'outcome':'unknown','error_code':type(exc).__name__}
        receipt=dict(invocation=invocation,scope=scope,outcome=result['outcome'],result_hash=digest(result),
            artifact_hash=result.get('artifact_hash'),artifact_ref=result.get('artifact_ref'),event_id=str(uuid4()))
        self.journal.persist(invocation,'result',receipt)
        return self._settle(receipt)

    def _settle(self,receipt):
        scope=receipt['scope']
        params={k:v for k,v in receipt.items() if k!='scope'}
        settled=self.graph.operation('settle-invocation',self.principal,scope,**params)
        if len(settled)!=1:
            raise RuntimeError('settlement_unavailable_do_not_redispatch')
        self.journal.persist(receipt['invocation'],'ack',{'result_hash':receipt['result_hash']})
        return settled[0]

    def recover_receipts(self):
        recovered=[]
        for receipt in self.journal.pending():
            rows=self.graph.query("MATCH (i:Invocation {node_id:$invocation,scope_id:$scope}) "
                "RETURN i.status AS status,i.result_hash AS result_hash",receipt)
            if len(rows)!=1:
                raise RuntimeError('receipt_authoritative_invocation_missing')
            row=rows[0]
            if row['status']==receipt['outcome'] and row['result_hash']==receipt['result_hash']:
                self.journal.persist(receipt['invocation'],'ack',{'result_hash':receipt['result_hash']})
            elif row['status']=='dispatching':
                self._settle(receipt)
            else:
                raise RuntimeError('receipt_reconciliation_conflict')
            recovered.append(receipt['invocation'])
        return recovered
