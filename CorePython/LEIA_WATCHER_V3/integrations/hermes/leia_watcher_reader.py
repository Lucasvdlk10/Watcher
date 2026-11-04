"""Hermes-side readonly adapter for the local LEIA Watcher API (stdlib only).

The invoking Hermes runtime controls whether/how to load this module; installation
never modifies Hermes configurations or other agent files automatically.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen


class LEIAWatcherReader:
    def __init__(self,token_file=None,port=8766):
        if token_file is None:
            home=Path(os.environ.get('LEIA_WATCHER_HOME') or (Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local'/'share'))/'LEIA'/'Watcher'))
            token_file=home/'data'/'hermes_read.token'
        self.token_file=Path(token_file)
        self.base=f'http://127.0.0.1:{int(port)}/v1'

    def _get(self,endpoint,**params):
        token=self.token_file.read_text(encoding='ascii').strip()
        url=self.base+'/'+endpoint+('?' + urlencode({k:v for k,v in params.items() if v is not None}) if params else '')
        req=Request(url,headers={'Authorization':'Bearer '+token,'Accept':'application/json'})
        with urlopen(req,timeout=5) as resp:
            return json.load(resp)

    def health(self):return self._get('health')
    def roots(self):return self._get('roots',limit=100)
    def find(self,query=None,root_id=None,extension=None,limit=25,cursor=None):
        return self._get('files',q=query,root_id=root_id,extension=extension,limit=min(100,max(1,limit)),cursor=cursor)
    def file(self,file_id):return self._get('files/'+file_id)
    def audit(self,root_id=None,limit=25):return self._get('audit',root_id=root_id,limit=limit)
    def operations(self,root_id=None,limit=25):return self._get('operations',root_id=root_id,limit=limit)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description='Readonly Hermes-Watcher local search')
    p.add_argument('query',nargs='?',default=None);p.add_argument('--root-id',default=None);p.add_argument('--extension',default=None);p.add_argument('--port',type=int,default=8766)
    a=p.parse_args()
    print(json.dumps(LEIAWatcherReader(port=a.port).find(a.query,a.root_id,a.extension),ensure_ascii=False,indent=2))
