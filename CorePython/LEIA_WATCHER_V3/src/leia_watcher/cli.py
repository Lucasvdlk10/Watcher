"""Operator CLI (via local authenticated IPC)."""
import argparse
import json
import os
import sys
from .config import home,load,validate
from .security import secret
from .admin import request

def main():
    p=argparse.ArgumentParser(prog='leia-watcher')
    p.add_argument('--home',default=None)
    sub=p.add_subparsers(dest='cmd',required=True)
    for c in ('core','ui','ping','status','roots','files','audit','operations','backup','token','stop','doctor','undo'):sub.add_parser(c)
    a=sub.add_parser('add');a.add_argument('name');a.add_argument('path');a.add_argument('--mode',choices=['TRACK_ONLY','ORGANIZE'],default='TRACK_ONLY')
    a=sub.add_parser('activate');a.add_argument('root_id');a.add_argument('--confirm-moves',action='store_true')
    for c in ('pause','resume','scan','remove'):
        a=sub.add_parser(c);a.add_argument('root_id')
    a=sub.add_parser('preview');a.add_argument('root_id');a.add_argument('--limit',type=int,default=50)
    a=sub.add_parser('edit');a.add_argument('root_id');a.add_argument('json_file')
    a=sub.add_parser('job');a.add_argument('job_id')
    a=sub.add_parser('export');a.add_argument('kind',choices=['files','audit','operations']);a.add_argument('path')
    a=p.parse_args()
    if a.home:os.environ['LEIA_WATCHER_HOME']=a.home
    if a.cmd=='core':
        from .main import main as run
        sys.argv=[sys.argv[0]]+(['--home',a.home] if a.home else []);return run()
    if a.cmd=='ui':
        from .ui import main as run
        return run()
    try:
        if a.cmd=='token':result={'token_file':str(home()/'data'/'hermes_read.token'),'bearer_token':secret('hermes_read.token'),'warning':'Keep token private; Hermes access is read only.'}
        elif a.cmd=='doctor':result={'config':validate(load()),'home':str(home()),'ping':request('ping')}
        elif a.cmd=='add':result=request('add_root',name=a.name,path=a.path,mode=a.mode)
        elif a.cmd=='activate':result=request('activate',root_id=a.root_id,confirmation='I_CONFIRM_FILE_MOVES' if a.confirm_moves else '')
        elif a.cmd=='remove':result=request('remove_root',root_id=a.root_id)
        elif a.cmd in ('pause','resume','scan'):result=request(a.cmd,root_id=a.root_id)
        elif a.cmd=='preview':result=request('preview',root_id=a.root_id,limit=a.limit)
        elif a.cmd=='edit':
            r=json.load(open(a.json_file,encoding='utf8'))
            if r.get('id')!=a.root_id:raise ValueError('Edited root ID mismatch')
            result=request('update_root',root=r)
        elif a.cmd=='job':result=request('job',job_id=a.job_id)
        elif a.cmd=='export':result=request('export',kind=a.kind,path=a.path)
        else:result=request(a.cmd)
        print(json.dumps(result,indent=2,ensure_ascii=False,default=str))
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        return 2
    return 0
if __name__=='__main__':sys.exit(main())
