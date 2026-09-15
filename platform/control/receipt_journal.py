"""Durable restricted I/O receipts. Never a work queue or execution authority."""
import json
import os
from pathlib import Path
import re
from uuid import uuid4


class ReceiptJournal:
    def __init__(self,root):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        if self.root.stat().st_mode & 0o077:
            raise RuntimeError('receipt_directory_must_be_private')

    def persist(self,invocation,kind,value):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}',invocation) or kind not in ['intent','result','ack']:
            raise ValueError('invalid_journal_identity')
        path=self.root/(invocation+'.'+kind+'.json')
        raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
        if path.exists():
            if path.read_bytes()!=raw:
                raise RuntimeError('receipt_identity_collision')
            return
        candidate=self.root/('.pending-'+uuid4().hex)
        fd=os.open(candidate,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        # Hard link provides an atomic, no-overwrite publication.
        try:
            os.link(candidate,path)
        except FileExistsError:
            if path.read_bytes()!=raw:
                raise RuntimeError('receipt_identity_collision')
        finally:
            candidate.unlink()
        directory=os.open(self.root,os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)

    def pending(self):
        count=0
        for path in sorted(self.root.glob('*.result.json')):
            invocation=path.name.removesuffix('.result.json')
            if not (self.root/(invocation+'.ack.json')).exists():
                yield json.loads(path.read_text())
                count+=1
                if count==100:
                    return
