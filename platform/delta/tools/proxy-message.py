import json, os, requests, sys

registry_path = '/opt/delta/delta-registry.json'
project_name = sys.argv[1] if len(sys.argv) > 1 else 'seedforthing'

with open(registry_path) as f:
    registry = json.load(f)

proj = registry['projects'][project_name]
port = proj.get('serve_port', 7710)
linux_user = proj['linux_user']
project_dir = proj['project_dir']

print(f'{project_name}: port={port}, user={linux_user}')

try:
    resp = requests.get(f'http://127.0.0.1:{port}/global/health', timeout=5)
    print(f'Health: {resp.json()}')
except Exception as e:
    print(f'Health check failed: {e}')
    sys.exit(1)

inbox_dir = os.path.join(project_dir, 'delta-config', 'inbox')
if not os.path.isdir(inbox_dir):
    print('No inbox dir')
    sys.exit(0)

inbox_files = sorted([f for f in os.listdir(inbox_dir) if f.endswith('.json')])
print(f'Inbox messages: {len(inbox_files)}')

if not inbox_files:
    print('No pending messages')
    sys.exit(0)

latest = inbox_files[-1]
with open(os.path.join(inbox_dir, latest)) as f:
    msg = json.load(f)

user = msg.get('user_id', 'unknown')
text = msg.get('text', '')
channel = msg.get('channel_id', '')
msg_id = msg.get('msg_id', '')

print(f'Processing: from {user} in {channel}: {text[:100]}')

session_id = proj.get('session_id', '')
if not session_id:
    cresp = requests.post(f'http://127.0.0.1:{port}/session',
        json={'title': project_name}, timeout=10)
    if cresp.status_code == 200:
        session_id = cresp.json()['id']
        proj['session_id'] = session_id
        registry['projects'][project_name] = proj
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        print(f'New session: {session_id}')

if session_id:
    prompt = (
        f"A user sent you a message on Discord. Channel: {channel}. User: {user}.\n\n"
        f"Message: {text}\n\n"
        f"Respond helpfully. If you need to use tools (git, files, Rube MCP), do so. "
        f"Your response will be sent back to the Discord channel."
    )
    payload = {
        'parts': [{'type': 'text', 'text': prompt}],
        'model': 'deepseek/deepseek-v4-pro',
        'agent': 'build'
    }
    mresp = requests.post(
        f'http://127.0.0.1:{port}/session/{session_id}/message',
        json=payload, timeout=180)
    print(f'Agent responded: {mresp.status_code}')
    if mresp.status_code == 200:
        data = mresp.json()
        parts = data.get('parts', [])
        for p in parts:
            if p.get('type') == 'text':
                print(f'Response: {p["text"][:500]}')
    else:
        print(f'Error: {mresp.text[:200]}')
