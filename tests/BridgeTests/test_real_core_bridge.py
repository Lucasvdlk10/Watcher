"""Real headless core/bridge roundtrip with isolated ephemeral profile, never users' Downloads."""
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import closing

ROOT=pathlib.Path(__file__).resolve().parents[2]
PY_SRC=ROOT/'CorePython/LEIA_WATCHER_V3/src'
BRIDGE=ROOT/'Bridge/watcher_bridge.py'

def test_authenticated_bridge_roundtrip_with_real_core():
    with tempfile.TemporaryDirectory(prefix='leia-v4-test-') as tmp:
        home=pathlib.Path(tmp)/'app';home.mkdir()
        downloads=pathlib.Path(tmp)/'Downloads';downloads.mkdir()
        (downloads/'sample.pdf').write_text('private test document',encoding='utf-8')
        with closing(socket.socket()) as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        conf={'schema_version':1,'api':{'host':'127.0.0.1','port':port},'scan_interval_seconds':30,'reconcile_interval_seconds':900,'roots':[]}
        (home/'config.json').write_text(json.dumps(conf))
        env={**os.environ,'LEIA_WATCHER_HOME':str(home),'PYTHONPATH':str(PY_SRC),'PYTHONIOENCODING':'utf-8'}
        core=subprocess.Popen([sys.executable,'-m','leia_watcher.main'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        bridge=None
        try:
            bridge=subprocess.Popen([sys.executable,'-u',str(BRIDGE)],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
            def call(command,args=None):
                bridge.stdin.write(json.dumps({'command':command,'args':args or {}})+'\n');bridge.stdin.flush()
                line=bridge.stdout.readline()
                assert line, 'Bridge exited: '+bridge.stderr.read()[:200]
                response=json.loads(line)
                assert response['ok'],response
                return response['result']
            for attempt in range(45):
                try:
                    ping=call('ping');break
                except AssertionError:
                    time.sleep(.2)
            else:raise AssertionError('Core never started')
            assert ping['no_llm'] and ping['db']=='ok' and ping['version']=='3.0.0'
            result=call('add_root',{'path':str(downloads),'mode':'TRACK_ONLY','name':'Downloads de teste'})
            assert result['root']['mode']=='TRACK_ONLY'
            snap=call('ui_snapshot')
            assert len(snap['roots'])==1 and snap['no_llm'] is True
            assert snap['pending']==0
            listed=call('ui_files_origin',{'origin':'Todos','page':0,'limit':40,'filters':{}})
            assert 'items' in listed and 'total' in listed
            assert (downloads/'sample.pdf').exists()
            assert not (downloads/'_LEIA_Organizado').exists()
            call('backup')
            assert list((home/'backups').rglob('*'))
            assert call('status')['database']=='ok'
        finally:
            if bridge:
                try:
                    bridge.terminate();bridge.wait(timeout=4)
                except Exception:bridge.kill()
            try:
                from leia_watcher.admin import request
                old=os.environ.get('LEIA_WATCHER_HOME');os.environ['LEIA_WATCHER_HOME']=str(home)
                try:request('stop')
                except Exception:pass
                if old is None:os.environ.pop('LEIA_WATCHER_HOME',None)
                else:os.environ['LEIA_WATCHER_HOME']=old
            except Exception:pass
            try:core.wait(timeout=4)
            except subprocess.TimeoutExpired:core.terminate();core.wait(timeout=4)
