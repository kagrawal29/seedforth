#!/usr/bin/env python3
"""Graph interpreter with strict reads, bounded chains, and durable atom evidence.

No raw outputs are logged. External execution is denied until an exact capability
is promoted in the immutable release, independently of writable graph content.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

sys.path.insert(0, os.path.dirname(__file__))
from neo4j_helper import q_strict


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def get_protocols(cadence=None, protocol_id=None):
    return q_strict("MATCH (p:Protocol {enabled:true}) "
                   "WHERE ($cadence IS NULL OR p.cadence=$cadence) "
                   "AND ($pid IS NULL OR p.node_id=$pid) RETURN p.node_id ORDER BY p.node_id",
                   {"cadence": cadence, "pid": protocol_id})


def get_atoms(protocol_id):
    roots = q_strict("MATCH (:Protocol {node_id:$pid})-[:FIRST_ATOM]->(a) RETURN a.node_id",
                     {"pid": protocol_id})
    if len(roots) != 1 or not roots[0][0]:
        raise ValueError("protocol_requires_one_first_atom")
    atoms, visited, current = [], set(), roots[0][0]
    while current:
        if current in visited or len(atoms) >= 64:
            raise ValueError("cyclic_or_excessive_chain")
        visited.add(current)
        rows = q_strict("MATCH (a {node_id:$id}) WHERE a:CypherAtom OR a:ExternalAtom "
                        "OPTIONAL MATCH (a)-[:FOLLOWS]->(n) RETURN a.node_id,a.cypher,"
                        "a.script,a.argv_json,a.timeout_seconds,collect(n.node_id)", {"id": current})
        if len(rows) != 1:
            raise ValueError("ambiguous_atom")
        aid, cypher, script, argv, timeout, successors = rows[0]
        if len(successors) > 1 or bool(cypher) == bool(script):
            raise ValueError("invalid_linear_atom")
        atom = dict(node_id=aid, cypher=cypher, script=script, argv_json=argv, timeout=timeout)
        atom["generation"] = fingerprint(atom)
        atoms.append(atom)
        current = successors[0] if successors else None
    return atoms


def run_atom(atom):
    if not atom.get("script"):
        return True, {"rows": len(q_strict(atom["cypher"]))}
    root = Path(__file__).resolve().parent
    manifest = root / "external-capabilities.json"
    entry = json.loads(manifest.read_text()).get(atom["node_id"]) if manifest.exists() else None
    if not entry:
        raise PermissionError("external_not_promoted")
    args = json.loads(atom.get("argv_json") or "[]")
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        raise ValueError("invalid_arguments")
    program = (root / entry["path"]).resolve()
    if (not program.is_relative_to(root) or not program.is_file()
            or atom["script"] != entry["path"] or args != entry.get("args", [])):
        raise PermissionError("external_contract_mismatch")
    if hashlib.sha256(program.read_bytes()).hexdigest() != entry["sha256"]:
        raise PermissionError("external_source_changed")
    timeout = atom.get("timeout")
    if type(timeout) is not int or not 1 <= timeout <= entry["max_seconds"]:
        raise PermissionError("external_timeout_not_approved")
    result = subprocess.run([sys.executable, str(program), *args], timeout=timeout,
                            capture_output=True, check=False, cwd=root)
    return result.returncode == 0, {"exit_code": result.returncode,
        "output_hash": hashlib.sha256(result.stdout + result.stderr).hexdigest()}


def write(query, params):
    rows = q_strict(query, params)
    if len(rows) != 1:
        raise RuntimeError("evidence_not_persisted")


def start(protocol_id, run_id, atoms):
    write("MATCH (p:Protocol {node_id:$pid,enabled:true}) "
          "CREATE (r:ProtocolRun:VersionedProtocolRun {node_id:$rid,protocol:$pid,project:'system',"
          "timestamp:datetime(),started_at:datetime(),status:'running',atoms_ok:0,"
          "atoms_total:$total,generation:$generation,source_revision:$revision}) "
          "CREATE (r)-[:RAN {decay_protected:true}]->(p) RETURN r.node_id",
          {"pid": protocol_id, "rid": run_id, "total": len(atoms),
           "generation": fingerprint([(a["node_id"], a["generation"]) for a in atoms]),
           "revision": os.environ.get("SEEDFORTH_RELEASE_SHA", "unrecorded")})


def finish(run_id, ok_count, status, error=None):
    write("MATCH (r:ProtocolRun {node_id:$id}) SET r.atoms_ok=$ok,r.status=$status,"
          "r.error_code=$error,r.finished_at=datetime() RETURN r.node_id",
          {"id": run_id, "ok": ok_count, "status": status, "error": error})


def execute_protocol(protocol_id):
    run_id = f"prun-{uuid4()}"
    try:
        atoms = get_atoms(protocol_id)
    except Exception as exc:
        start(protocol_id, run_id, [])
        finish(run_id, 0, "failed", type(exc).__name__)
        return False
    start(protocol_id, run_id, atoms)
    ok_count = 0
    for index, atom in enumerate(atoms):
        event_id = f"{run_id}:atom:{index}"
        write("MATCH (r:ProtocolRun {node_id:$rid}) MATCH (a {node_id:$aid}) "
              "WHERE a:CypherAtom OR a:ExternalAtom "
              "CREATE (e:AtomRun {node_id:$eid,project:'system',status:'running',"
              "started_at:datetime(),generation:$generation,step:$step}) "
              "CREATE (r)-[:HAS_ATOM_RUN]->(e) CREATE (e)-[:EXECUTED]->(a) RETURN e.node_id",
              {"rid": run_id, "aid": atom["node_id"], "eid": event_id,
               "generation": atom["generation"], "step": index})
        try:
            ok, result = run_atom(atom)
        except Exception as exc:
            ok, result = False, {"error_code": type(exc).__name__}
        write("MATCH (e:AtomRun {node_id:$id,status:'running'}) "
              "SET e.status=$status,e.result_json=$result,e.finished_at=datetime() RETURN e.node_id",
              {"id": event_id, "status": "succeeded" if ok else "failed", "result": json.dumps(result)})
        if not ok:
            finish(run_id, ok_count, "failed", result.get("error_code", "external_exit"))
            return False
        ok_count += 1
    finish(run_id, ok_count, "succeeded")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cadence", choices=["heartbeat", "dream", "deep", "fast", "weekly"])
    group.add_argument("--protocol")
    group.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    try:
        protocols = get_protocols(args.cadence, args.protocol)
        if not protocols:
            return 2
        failed = 0
        for (pid,) in protocols:
            ok = execute_protocol(pid)
            print(json.dumps({"protocol": pid, "success": ok}))
            failed += not ok
        return 1 if failed else 0
    except Exception as exc:
        print(json.dumps({"runner_error": type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
