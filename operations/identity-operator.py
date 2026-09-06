"""Root-only identity enrollment/reset/backup client. Never prints invitations."""
import argparse
import json
import os
from pathlib import Path
import socket


def request(operation,principal=None):
    if os.geteuid()!=0:
        raise ValueError('root_operator_required')
    body={'operation':operation}
    if principal is not None:
        body['principal']=principal
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
        conn.settimeout(20)
        conn.connect('/run/seedforth-identity/operator.sock')
        conn.sendall(json.dumps(body).encode()+b'\n')
        data=bytearray()
        while len(data)<=8192:
            chunk=conn.recv(8193-len(data))
            if not chunk:break
            data.extend(chunk)
            if b'\n' in data:break
    if len(data)>8192 or not data.endswith(b'\n'):
        raise ValueError('invalid_operator_response')
    result=json.loads(data)
    if 'error' in result:
        raise ValueError(result['error'])
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['invite','reset','backup'])
    parser.add_argument('--principal')
    parser.add_argument('--output')
    args=parser.parse_args()
    if args.operation in {'invite','reset'}:
        if not args.principal or not args.output:
            parser.error('invitation/reset requires principal and private output file')
        target=Path(args.output)
        if (target.parent!=Path('/opt/seedforth/shared/env') or target.is_symlink() or target.exists()
                or not target.name.startswith('human-invitation-')
                or target.parent.stat().st_uid!=0 or target.parent.stat().st_mode&0o077):
            raise ValueError('invalid_invitation_output_target')
        fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        try:
            result=request(args.operation,args.principal)
            with os.fdopen(fd,'w') as stream:
                json.dump(result,stream);stream.flush();os.fsync(stream.fileno())
        except BaseException:
            # Retain the reserved empty file on uncertain failure. Inspect before
            # retrying rather than silently issuing a second invitation/reset.
            try:os.close(fd)
            except OSError:pass
            raise
        print(json.dumps({'status':'invitation_saved_privately','output':str(target)}))
    else:
        if args.principal or args.output:parser.error('backup takes no principal or output')
        print(json.dumps(request('backup')))
