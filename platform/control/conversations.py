"""Conversation identity binding and external request normalization.

Admission, sequencing, status and durable content live in authored graph reducers.
"""
import hashlib
import json
import re


def identifiers(actor,scope,key,request_id=None):
    if not isinstance(key,str) or not re.fullmatch('[A-Za-z0-9_-]{1,128}',key):
        raise ValueError('invalid_conversation_key')
    def digest(parts):
        return hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).hexdigest()
    result={'conversation_id':'conversation-'+digest([actor,scope,key])}
    if request_id is not None:
        if not isinstance(request_id,str) or not re.fullmatch('[A-Za-z0-9_-]{1,128}',request_id):
            raise ValueError('invalid_request_id')
        result['message_id']='message-'+digest([actor,scope,request_id])
    return result
