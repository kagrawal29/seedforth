"""Real IPv4/IPv6 INPUT and post-DNAT forwarding in disposable namespaces.

Opt-in on delta2 only. No production interfaces, listeners or firewall tables are
changed. Unique namespaces are created and removed by this test alone.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import uuid4

import pytest

pytestmark=pytest.mark.skipif(os.environ.get('CONTROL_NETWORK_GUARD_TEST')!='1',reason='explicit namespace qualification required')


def test_real_ipv4_ipv6_public_denial_dnat_and_private_access():
    assert os.geteuid()==0 and socket.gethostname()=='vmi3556896'
    names=['sfga'+uuid4().hex[:8],'sfgb'+uuid4().hex[:8],'sfgc'+uuid4().hex[:8]]
    a,b,c=names
    created=[];processes=[]
    def run(*args):
        result=subprocess.run(list(args),capture_output=True,text=True,timeout=10)
        if result.returncode:raise RuntimeError(result.stderr[:500])
        return result.stdout
    def ns(name,*args):return run('ip','netns','exec',name,*args)
    listener="""import socket,threading,time,sys
ports=[int(p) for p in sys.argv[1].split(',')]
def serve(family,host,port):
 s=socket.socket(family);s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
 if family==socket.AF_INET6:s.setsockopt(socket.IPPROTO_IPV6,socket.IPV6_V6ONLY,1)
 s.bind((host,port));s.listen()
 while True:
  conn,_=s.accept();conn.close()
for port in ports:
 for family,host in [(socket.AF_INET,'0.0.0.0'),(socket.AF_INET6,'::')]:
  threading.Thread(target=serve,args=(family,host,port),daemon=True).start()
time.sleep(60)
"""
    def probe(namespace,address,port):
        code="import socket,sys; s=socket.create_connection((sys.argv[1],int(sys.argv[2])),timeout=.5);s.close()"
        return subprocess.run(['ip','netns','exec',namespace,sys.executable,'-c',code,address,str(port)],
                              capture_output=True,timeout=3).returncode==0
    try:
        for name in names:
            run('ip','netns','add',name);created.append(name)
            ns(name,'ip','link','set','lo','up')
        ns(a,'ip','link','add','eth0','type','veth','peer','name','peer0')
        ns(a,'ip','link','set','peer0','netns',b)
        ns(b,'ip','link','set','peer0','name','eth0')
        ns(b,'ip','link','add','inside0','type','veth','peer','name','peer1')
        ns(b,'ip','link','set','peer1','netns',c)
        ns(c,'ip','link','set','peer1','name','eth0')
        for name,interface,v4,v6 in [(a,'eth0','10.239.218.1/24','fd42:239:218::1/64'),
                (b,'eth0','10.239.218.2/24','fd42:239:218::2/64'),
                (b,'inside0','10.239.219.1/24','fd42:239:219::1/64'),
                (c,'eth0','10.239.219.2/24','fd42:239:219::2/64')]:
            ns(name,'ip','addr','add',v4,'dev',interface)
            ns(name,'ip','-6','addr','add',v6,'dev',interface,'nodad')
            ns(name,'ip','link','set',interface,'up')
        ns(c,'ip','route','add','default','via','10.239.219.1')
        ns(c,'ip','-6','route','add','default','via','fd42:239:219::1')
        ns(b,'sysctl','-w','net.ipv4.ip_forward=1')
        ns(b,'sysctl','-w','net.ipv6.conf.all.forwarding=1')
        for binary,destination in [('iptables','10.239.219.2:17474'),('ip6tables','[fd42:239:219::2]:17474')]:
            ns(b,binary,'-N','DOCKER-USER')
            ns(b,binary,'-A','FORWARD','-j','DOCKER-USER')
            ns(b,binary,'-t','nat','-A','PREROUTING','-i','eth0','-p','tcp','--dport','7474','-j','DNAT','--to-destination',destination)
        for name,ports in [(b,'22,6083,7687,8900'),(c,'17474')]:
            processes.append(subprocess.Popen(['ip','netns','exec',name,sys.executable,'-c',listener,ports],
                                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        for _ in range(30):
            if probe(a,'10.239.218.2',22):break
            time.sleep(.05)
        for address in ['10.239.218.2','fd42:239:218::2']:
            assert all(probe(a,address,p) for p in [22,6083,7474,7687,8900])
        path=Path(__file__).parents[2]/'operations/network-guard.py'
        code="import importlib.util; s=importlib.util.spec_from_file_location('g',"+repr(str(path))+");g=importlib.util.module_from_spec(s);s.loader.exec_module(g);g.enforce(dict(id='network-policy-internal-services-v1',version=1,interface='eth0',ports=[6083,7474,7687]))"
        ns(b,sys.executable,'-c',code)
        ns(b,sys.executable,'-c',code)
        for address in ['10.239.218.2','fd42:239:218::2']:
            assert all(not probe(a,address,p) for p in [6083,7474,7687])
            assert all(probe(a,address,p) for p in [22,8900])
        for address in ['127.0.0.1','::1']:
            assert all(probe(b,address,p) for p in [6083,7687])
        assert probe(b,'10.239.219.2',17474)
        assert probe(b,'fd42:239:219::2',17474)
    finally:
        for process in processes:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        for name in reversed(created):
            run('ip','netns','delete',name)
