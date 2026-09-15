"""Explicit additive deployment adapter; no domain rules are implemented here."""
import argparse
import hashlib
import json
from pathlib import Path

from control.graph import Graph, GraphError, operation_sources

ROOT = Path(__file__).resolve().parents[1] / 'mycelium/graph/knowledge'
SOURCES = ['seedforth-control-model-v1.cypher', 'seedforth-control-model-v2.cypher',
           'seedforth-upgrade-pilot-scopes.cypher','seedforth-pilot-runtime-sources.cypher',
           'seedforth-pilot-code-sources.cypher',
           'seedforth-delta-event-sources-v1.cypher',
           'seedforth-service-health-sources-v1.cypher',
           'seedforth-graphify-source-v1.cypher',
           'seedforth-conversation-model-v1.cypher',
           'seedforth-upgrade-work-plan.cypher',
           'awareness-event-contract-v1.cypher',
           'system-awareness-metabolism-workstream.cypher',
           'seedforth-control-owner.cypher',
           'seedforth-owner-conversations-v1.cypher']


def split_cypher_statements(source):
    """Split source on statement semicolons, preserving comments and strings."""
    statements, current = [], []
    i = 0
    quote = False
    line_comment = False
    block_comment = False
    while i < len(source):
        char = source[i]
        next_char = source[i + 1] if i + 1 < len(source) else ''
        if line_comment:
            current.append(char)
            if char == '\n':
                line_comment = False
            i += 1
            continue
        if block_comment:
            current.append(char)
            if char == '*' and next_char == '/':
                current.append(next_char)
                block_comment = False
                i += 2
            else:
                i += 1
            continue
        if not quote and char == '/' and next_char == '/':
            current.extend((char, next_char))
            line_comment = True
            i += 2
            continue
        if not quote and char == '/' and next_char == '*':
            current.extend((char, next_char))
            block_comment = True
            i += 2
            continue
        if char == "'":
            current.append(char)
            if quote and next_char == "'":
                current.append(next_char)
                i += 2
                continue
            quote = not quote
            i += 1
            continue
        if char == ';' and not quote:
            statement = ''.join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        i += 1
    statement = ''.join(current).strip()
    if statement:
        statements.append(statement)
    return statements


def migrate(graph, revision):
    # Fail before touching schema if this is not the inspected product identity set.
    rows = graph.query("MATCH (p:Project) WHERE p.node_id IN $ids "
                       "RETURN p.node_id AS id,count(p) AS n ORDER BY id",
                       {'ids':['proj-mycelium','project-cajon-sensei','project-flowing-indian']})
    if rows != [{'id':'proj-mycelium','n':1},{'id':'project-cajon-sensei','n':1},{'id':'project-flowing-indian','n':1}]:
        raise GraphError('pilot_identity_preflight_failed')
    digest = hashlib.sha256()
    for name in SOURCES:
        source = (ROOT/name).read_text()
        digest.update(source.encode())
        for statement in split_cypher_statements(source):
            graph.query(statement)
    for path in operation_sources():
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    graph.promote()
    graph.query("MERGE (r:MigrationReceipt {node_id:$id}) "
                "ON CREATE SET r.created_at=datetime(),r.source_revision=$revision,"
                "r.source_hash=$hash,r.status='applied',r.project='system'",
                {'id':'migration-control-v2-'+digest.hexdigest(),
                 'revision':revision,'hash':digest.hexdigest()})
    return {'migration':'control-v2','source_hash':digest.hexdigest(),'status':'applied'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint',required=True)
    parser.add_argument('--revision',required=True)
    args=parser.parse_args()
    print(json.dumps(migrate(Graph(endpoint=args.endpoint),args.revision)))
