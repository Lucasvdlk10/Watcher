"""Authenticated readonly REST/WS API for Hermes, bound strictly to 127.0.0.1."""
import base64
import hashlib
import hmac
import json
import secrets
import select
import socket
import struct
import threading
import time
from collections import defaultdict,deque
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from .db import now
from .security import secret


def install_read_token(db):
    value=secret('hermes_read.token')
    hashed=hashlib.sha256(value.encode()).hexdigest()
    db.execute("INSERT INTO api_tokens(token_id,token_hash,scopes_json,root_allowlist_json,issued_at) VALUES(?,?,?,?,?) ON CONFLICT(token_id) DO UPDATE SET token_hash=excluded.token_hash",('default-hermes',hashed,json.dumps(['read']),None,now()))
    return value

class Limiter:
    def __init__(self):self.lock=threading.Lock();self.calls=defaultdict(deque)
    def ok(self,identity):
        with self.lock:
            a=self.calls[identity];t=time.monotonic()
            while a and t-a[0]>60:a.popleft()
            if len(a)>=240:return False
            a.append(t);return True


def handler_factory(db,watcher):
    limiter=Limiter()
    class Handler(BaseHTTPRequestHandler):
        server_version='LEIAWatcher/1.0'
        protocol_version='HTTP/1.1'
        def log_message(self,*args): pass  # never log bearer tokens or paths here
        def respond(self,code,obj):
            b=json.dumps(obj,ensure_ascii=False,default=str).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Length',str(len(b)))
            self.end_headers();self.wfile.write(b)
        def error(self,code,reason):
            self.respond(code,{'error':{'code':reason,'message':reason,'retryable':code>=500,'request_id':secrets.token_hex(8)}})
        def do_POST(self):self.error(405,'ERR_METHOD_READ_ONLY')
        def do_PUT(self):self.error(405,'ERR_METHOD_READ_ONLY')
        def do_DELETE(self):self.error(405,'ERR_METHOD_READ_ONLY')
        def do_PATCH(self):self.error(405,'ERR_METHOD_READ_ONLY')
        def auth(self):
            auth=self.headers.get('Authorization','')
            if not auth.startswith('Bearer ') or len(auth)>200:self.error(401,'ERR_AUTH');return None
            candidate=hashlib.sha256(auth[7:].encode()).hexdigest()
            tokens=db.rows('SELECT * FROM api_tokens WHERE revoked_at IS NULL')
            for t in tokens:
                if hmac.compare_digest(candidate,t['token_hash']):
                    if t['expires_at'] and t['expires_at']<now():continue
                    scopes=json.loads(t['scopes_json'])
                    if 'read' not in scopes:self.error(403,'ERR_SCOPE');return None
                    return json.loads(t['root_allowlist_json']) if t['root_allowlist_json'] else None
            self.error(401,'ERR_AUTH');return None
        def allowed(self,where='',args=(),allow=None):
            if allow is not None:
                if not allow:return ' AND 1=0',args
                where+=' AND root_id IN ('+','.join(['?']*len(allow))+')';args=tuple(args)+tuple(allow)
            return where,args
        def page(self,sql,args,column,limit,cursor=None):
            """Keyset pagination with fixed SQL column known at call-site."""
            sql+=' ORDER BY '+column+' ASC LIMIT ?'
            args=tuple(args)+(limit+1,)
            rows=db.rows(sql,args)
            items=rows[:limit]
            return {'items':items,'next_cursor':str(items[-1][column]) if len(rows)>limit else None}
        def do_GET(self):
            if not limiter.ok(self.client_address[0]):return self.error(429,'ERR_RATE_LIMIT')
            allow=self.auth()
            if allow is None and not self._authenticated():return
            path=urlparse(self.path)
            if path.path=='/v1/events' and self.headers.get('Upgrade','').lower()=='websocket':
                return self.websocket(path,allow)
            qs=parse_qs(path.query,keep_blank_values=True)
            try:
                limit=int(qs.get('limit',['25'])[0]);assert 1<=limit<=100
                cursor=qs.get('cursor',[None])[0]
                if cursor and len(cursor)>500:raise ValueError()
                if path.path=='/v1/health':
                    return self.respond(200,{'ok':db.health()=='ok','version':'1.0.0','database':'OK' if db.health()=='ok' else 'FAILED','roots':len(db.rows('SELECT root_id FROM watched_roots' if allow is None else 'SELECT root_id FROM watched_roots WHERE root_id IN ('+','.join('?'*len(allow))+')',() if allow is None else tuple(allow))) if allow is None or allow else 0,'mode':'no_llm','time':now()})
                if path.path=='/v1/roots':
                    where,args=self.allowed('',(),allow)
                    # public 'id' field is required by contract
                    if cursor:where+=' AND root_id>?';args+= (cursor,)
                    p=self.page('SELECT root_id as id,name,mode,health,enabled,recursive FROM watched_roots WHERE 1=1'+where,args,'id',limit)
                    return self.respond(200,p)
                if path.path=='/v1/files':
                    wh=['1=1'];args=[]
                    for key,col in [('root_id','root_id'),('extension','extension'),('status','status')]:
                        if key in qs:
                            x=qs[key][0]
                            if len(x)>200:raise ValueError()
                            wh.append(col+'=?');args.append(x)
                    if 'q' in qs:
                        query=qs['q'][0]
                        if len(query)>200:raise ValueError()
                        wh.append("(instr(lower(filename),lower(?))>0 OR instr(lower(relative_path),lower(?))>0)");args.extend((query,query))
                    if 'updated_since' in qs:wh.append('updated_at>=?');args.append(qs['updated_since'][0])
                    if 'min_size' in qs:wh.append('size_bytes>=?');args.append(int(qs['min_size'][0]))
                    if 'max_size' in qs:wh.append('size_bytes<=?');args.append(int(qs['max_size'][0]))
                    if cursor:wh.append('file_id>?');args.append(cursor)
                    w,aa=self.allowed(' AND '.join(wh),tuple(args),allow)
                    query=('SELECT file_id as id,root_id,relative_path,filename as file_name,extension,size_bytes,status,seen_at as last_seen_at,origin_category FROM file_entries WHERE '+w)
                    p=self.page(query,aa,'id',limit)
                    p['request_id']=secrets.token_hex(8);p['total_approx']=len(p['items'])
                    return self.respond(200,p)
                if path.path.startswith('/v1/files/'):
                    fid=path.path.split('/')[-1]
                    w,args=self.allowed('file_id=?',(fid,),allow)
                    rows=db.rows('SELECT file_id as id,root_id,relative_path,filename as file_name,extension,size_bytes,status,seen_at as last_seen_at,origin_category,origin_evidence_json FROM file_entries WHERE '+w,args)
                    if not rows:return self.error(404,'ERR_NOT_FOUND')
                    return self.respond(200,rows[0])
                if path.path in ('/v1/audit','/v1/operations'):
                    kind='audit_events' if path.path.endswith('audit') else 'operations'
                    key='audit_id' if kind=='audit_events' else 'operation_id'
                    where=['1=1'];args=[]
                    if 'root_id' in qs:where.append('root_id=?');args.append(qs['root_id'][0])
                    if kind=='operations' and 'stage' in qs:where.append('stage=?');args.append(qs['stage'][0])
                    if cursor:where.append(key+'>?');args.append(int(cursor) if key=='audit_id' else cursor)
                    w,aa=self.allowed(' AND '.join(where),tuple(args),allow)
                    # exclude the record's potentially sensitive precondition hashes
                    cols=('audit_id,root_id,occurred_at,action,outcome,reason_code,actor' if kind=='audit_events' else 'operation_id,root_id,operation_kind,stage,reason_code,created_at,completed_at,error_code')
                    return self.respond(200,self.page('SELECT '+cols+' FROM '+kind+' WHERE '+w,aa,key,limit))
                if path.path=='/v1/stats':
                    w,args=self.allowed('1=1',(),allow)
                    counts=db.rows('SELECT root_id,status,count(*) as total FROM file_entries WHERE '+w+' GROUP BY root_id,status',args)
                    return self.respond(200,{'files_by_root_status':counts,'no_llm':True})
                return self.error(404,'ERR_NOT_FOUND')
            except (ValueError,AssertionError,OverflowError):return self.error(400,'ERR_INVALID_QUERY')
            except Exception:return self.error(503,'ERR_SERVICE')
        def _authenticated(self):
            # Auth successfully returning None means unrestricted; verify again to distinguish.
            a=self.headers.get('Authorization','')
            if not a.startswith('Bearer '):return False
            hash_value=hashlib.sha256(a[7:].encode()).hexdigest()
            return any(hmac.compare_digest(t['token_hash'],hash_value) and 'read' in json.loads(t['scopes_json']) and not t['revoked_at'] and (not t['expires_at'] or t['expires_at']>now()) for t in db.rows('SELECT * FROM api_tokens'))
        def websocket(self,path,allow):
            self.close_connection=True
            qs=parse_qs(path.query)
            requested=qs.get('root_id',[None])[0]
            if requested and allow is not None and requested not in allow:return self.error(403,'ERR_SCOPE')
            if self.headers.get('Origin'):return self.error(403,'ERR_WS_BROWSER_ORIGIN')
            key=self.headers.get('Sec-WebSocket-Key','')
            try:
                if len(base64.b64decode(key,validate=True))!=16:raise ValueError()
            except ValueError:return self.error(400,'ERR_WS_HANDSHAKE')
            accept=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
            self.send_response(101,'Switching Protocols')
            self.send_header('Upgrade','websocket');self.send_header('Connection','Upgrade')
            self.send_header('Sec-WebSocket-Accept',accept);self.end_headers()
            try:cursor=max(0,int(qs.get('last_event_id',['0'])[0]))
            except ValueError:cursor=0
            self.connection.settimeout(1)
            end=time.monotonic()+3600
            try:
                while time.monotonic()<end:
                    # Detect peer CLOSE and broken sockets; avoid orphan websocket threads.
                    if select.select([self.connection],[],[],0)[0]:
                        if not self.ws_read_control():break
                    where='event_id>?';args=[cursor]
                    if requested:where+=' AND root_id=?';args.append(requested)
                    if allow is not None:
                        if not allow:break
                        where+=' AND root_id IN ('+','.join('?'*len(allow))+')';args+=allow
                    if cursor==0:
                        oldest=db.rows('SELECT MIN(event_id) AS first FROM fs_events')
                        if oldest and oldest[0]['first'] and oldest[0]['first']>1:
                            self.ws_frame(json.dumps({'event_type':'RETENTION_GAP','first_available_event_id':oldest[0]['first']}))
                            cursor=oldest[0]['first']-1
                    rows=db.rows('SELECT event_id,root_id,observed_at,event_type,path,old_path,source,operation_id FROM fs_events WHERE '+where+' ORDER BY event_id ASC LIMIT 50',args)
                    for item in rows:
                        cursor=item['event_id']
                        self.ws_frame(json.dumps(item,ensure_ascii=False))
                    if not rows:time.sleep(.5)
            except (BrokenPipeError,ConnectionResetError,OSError):return
        def ws_read_control(self):
            def receive(size):
                buf=b''
                while len(buf)<size:
                    part=self.connection.recv(size-len(buf))
                    if not part:raise ConnectionResetError('WS client disconnected')
                    buf+=part
                return buf
            head=receive(2)
            opcode=head[0]&15
            n=head[1]&127
            if n==126:n=struct.unpack('!H',receive(2))[0]
            if n==127:n=struct.unpack('!Q',receive(8))[0]
            if n>4096:raise ConnectionResetError('Oversized inbound WS message')
            if not head[1]&0x80:raise ConnectionResetError('Unmasked client WS frame')
            mask=receive(4);payload=bytearray(receive(n))
            for i in range(n):payload[i]^=mask[i%4]
            if opcode==8:return False
            if opcode==9:
                b=bytes(payload);self.connection.sendall(b'\x8a'+bytes([len(b)])+b)
            return True
        def ws_frame(self,s):
            b=s.encode('utf-8');n=len(b)
            header=b'\x81'+(bytes([n]) if n<126 else (b'\x7e'+struct.pack('!H',n) if n<65536 else b'\x7f'+struct.pack('!Q',n)))
            self.connection.sendall(header+b)
    return Handler


def serve(db,watcher):
    port=int(watcher.config.get('api',{}).get('port',8766))
    http=ThreadingHTTPServer(('127.0.0.1',port),handler_factory(db,watcher))
    http.daemon_threads=True
    t=threading.Thread(target=http.serve_forever,name='leia-rest-ws',daemon=True);t.start()
    return http
