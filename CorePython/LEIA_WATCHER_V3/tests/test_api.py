import base64
import hashlib
import json
import socket
import time
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from threading import Thread
import pytest
from leia_watcher.api import handler_factory,install_read_token
from leia_watcher.db import now

@pytest.fixture
def http(env):
    root,r,c,db,e=env
    key=install_read_token(db)
    srv=ThreadingHTTPServer(('127.0.0.1',0),handler_factory(db,e))
    t=Thread(target=srv.serve_forever,daemon=True);t.start()
    yield f'http://127.0.0.1:{srv.server_port}',key,env
    srv.shutdown();srv.server_close();t.join(3)

def fetch(http,path,token=None,method='GET'):
    url,key,env=http
    headers={'Authorization':'Bearer '+token} if token else {}
    req=urllib.request.Request(url+path,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=3) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read())

def test_auth_required(http):assert fetch(http,'/v1/files')[0]==401

def test_wrong_token(http):assert fetch(http,'/v1/health','bad-token')[0]==401

def test_health(http):
    url,key,*_=http;status,data=fetch(http,'/v1/health',key)
    assert status==200 and data['ok'] and data['mode']=='no_llm'

def test_readonly(http):
    url,key,*_=http
    assert fetch(http,'/v1/files',key,method='POST')[0]==405
    assert fetch(http,'/v1/files',key,method='DELETE')[0]==405

def test_files_pagination(http):
    url,key,(root,r,c,db,e)=http
    for i in range(4):(root/f'file{i}.pdf').write_text(str(i))
    e.scan(r['id'])
    first=fetch(http,'/v1/files?limit=2',key)[1]
    assert len(first['items'])==2 and first['next_cursor']
    second=fetch(http,'/v1/files?limit=2&cursor='+first['next_cursor'],key)[1]
    assert len(second['items'])==2
    assert set(x['id'] for x in second['items']).isdisjoint(x['id'] for x in first['items'])

def test_file_detail_scope(http):
    url,key,(root,r,c,db,e)=http
    (root/'abc.txt').write_text('123');e.scan(r['id'])
    fileid=db.rows('SELECT file_id FROM file_entries')[0]['file_id']
    assert fetch(http,'/v1/files/'+fileid,key)[0]==200
    assert fetch(http,'/v1/files/unknown',key)[0]==404
    db.execute('UPDATE api_tokens SET root_allowlist_json=? WHERE token_id=?',(json.dumps(['other-root']),'default-hermes'))
    assert fetch(http,'/v1/files',key)[1]['items']==[]
    assert fetch(http,'/v1/files/'+fileid,key)[0]==404

def test_sqli_filters_inert(http):
    url,key,*_=http
    assert fetch(http,"/v1/files?root_id=%27%20OR%201=1%20--",key)[1]['items']==[]

def test_query_validation(http):
    url,key,*_=http
    assert fetch(http,'/v1/files?limit=999',key)[0]==400

def test_websocket_stream_and_auth(http):
    import websockets.sync.client
    url,key,(root,r,c,db,e)=http
    e.db.event(r['id'],'CREATED',root/'one.txt')
    uri=url.replace('http://','ws://')+'/v1/events?last_event_id=0&root_id='+r['id']
    with websockets.sync.client.connect(uri,additional_headers={'Authorization':'Bearer '+key},open_timeout=3) as ws:
        data=json.loads(ws.recv(timeout=3))
        assert data['event_type']=='CREATED' and data['root_id']==r['id']
    try:
        with websockets.sync.client.connect(uri,open_timeout=3):pass
        assert False,'Unauthorized handshake succeeded'
    except Exception:pass
