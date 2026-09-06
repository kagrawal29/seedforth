"""Agent-authored candidate exercised through the disposable graph broker.

Not a production worker launch or accepted outcome. Fixed source revision and
explicit edits make the test repeatable without touching the product checkout.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from control.broker import Broker
from control.code_proposal import CodeProposal
from control.graph import Graph
from control.receipt_journal import ReceiptJournal
from test_control_graph_live import case, invocation_params

REVISION = '2a518d957bb1fbd39b02a8dcbc3e1f2890630b93'
REPOSITORY = '/home/proj-cajon-sensei/cajon-sensei'
RESONANCE = '''  // Groove resonance — dissolve polygons on stop
  let resonanceMult = 1.0;
  if (!playing && resonanceTs > 0) {
    const rAge = (Date.now() - resonanceTs) / 1500;
    if (rAge >= 1.0) {
      resonanceTs = 0;
    } else {
      resonanceMult = 1.0 - rAge;
    }
  }

'''
CHANGES = [
    ('  currentStep = (currentStep + 1) % rhythm.subdivisions;\n  stepHistory.push(currentStep);',
     '  const completingLoop = currentStep === rhythm.subdivisions - 1;\n  currentStep = (currentStep + 1) % rhythm.subdivisions;\n  stepHistory.push(currentStep);'),
    ('  if (currentStep === 0 && playing) {', '  if (completingLoop && playing) {'),
    ("      document.getElementById('play-btn').classList.add('active');\n      scheduleNextStep();",
     "      document.getElementById('play-btn').classList.add('active');\n      updateStep();\n      scheduleNextStep();"),
    ("  document.getElementById('play-btn').classList.add('active');\n  scheduleNextStep();",
     "  document.getElementById('play-btn').classList.add('active');\n  updateStep();\n  scheduleNextStep();"),
    ('  if (playing) {\n    clearTimeout(intervalId);\n    scheduleNextStep();\n  }\n}',
     '  if (playing) {\n    clearTimeout(intervalId);\n    currentStep = -1;\n    updateStep();\n    scheduleNextStep();\n  }\n}'),
    (RESONANCE, ''),
    ('  const steps = rhythm.subdivisions;\n\n  // Per-rhythm ambient atmosphere',
     '  const steps = rhythm.subdivisions;\n\n' + RESONANCE + '  // Per-rhythm ambient atmosphere'),
]


def main():
    graph = Graph('http://127.0.0.1:27474', user='', password='')
    graph.promote()
    c = case.__wrapped__(graph)
    root = Path(tempfile.mkdtemp(prefix='seedforth-cajon-candidate-', dir='/tmp'))
    adapter = CodeProposal({c['scope']: REPOSITORY}, {c['scope']: ['app/index.html']}, root/'artifacts')
    graph.query('MATCH (c:Capability {node_id:$id}) SET c.policy_generation=$generation',
        {'id':c['scope']+'-cap', 'generation':adapter.generation})
    p = invocation_params(graph, c)
    broker = Broker(graph, c['scope']+'-broker', {p['capability']:adapter}, ReceiptJournal(root/'receipts'))
    result = broker.invoke(c['worker'],c['scope'],p['attempt'],p['fence'],p['invocation'],p['capability'],
        {'revision':REVISION, 'changes':[{'path':'app/index.html','old':old,'new':new} for old,new in CHANGES]})
    assert result['status'] == 'succeeded'
    artifact = broker.read_artifact(c['worker'],c['scope'],p['invocation'])
    file = artifact['content']['files'][0]
    # This materialization is a disposable browser input, not the product checkout.
    target = root/'index.html'
    target.write_text(file['content'])
    assert hashlib.sha256(target.read_bytes()).hexdigest() == file['sha256']
    assert file['base_sha256'] == '56b092507f73ff644f742f63f3bd43802f3638df85895000c37282644a1b83b0'
    print(json.dumps({'fixture_scope':c['scope'], 'attempt':p['attempt'], 'invocation':p['invocation'],
        'candidate_file':str(target), 'candidate_sha256':file['sha256'], 'artifact_hash':artifact['artifact_hash'],
        'base_revision':REVISION, 'product_modified':False, 'verification':'pending'}))


if __name__ == '__main__':
    main()
