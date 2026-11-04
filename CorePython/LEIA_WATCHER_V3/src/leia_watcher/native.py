"""Windows ReadDirectoryChangesW event source, conservative bounded queue."""
import os
import queue
import struct
import threading
from pathlib import Path

class WindowsEvents:
    """Non-blocking delivery from WinAPI threads; periodic scan reconciles lost signals."""
    def __init__(self):
        self.queue=queue.Queue(maxsize=4096)
        self.overflows=set()
        self.lock=threading.RLock()
        self.stop=threading.Event()
        self.handles={}
        self.threads={}
        self.root_stop={}
        self.desired={}

    def emit(self,rid,action,path):
        try:self.queue.put_nowait((rid,action,path))
        except queue.Full:
            with self.lock:self.overflows.add(rid)

    def start(self,roots):
        if os.name!='nt':return
        new={r['id']:(r['path'],r.get('recursive',True)) for r in roots if r.get('enabled',True)}
        for rid in list(self.desired):
            if rid not in new or self.desired[rid]!=new[rid]:
                self.root_stop[rid].set()
                with self.lock:
                    h=self.handles.get(rid)
                    if h:
                        import ctypes
                        k=ctypes.WinDLL('kernel32',use_last_error=True)
                        from ctypes import wintypes
                        k.CancelIoEx.argtypes=(wintypes.HANDLE,ctypes.c_void_p)
                        k.CancelIoEx(h,None)
                self.threads.pop(rid,None);self.root_stop.pop(rid,None)
        self.desired=new
        for r in roots:
            if r.get('enabled',True) and r['id'] not in self.threads:
                self.root_stop[r['id']]=threading.Event()
                t=threading.Thread(target=self._watch,args=(r,),daemon=True,name='ntfs-'+r['id'])
                self.threads[r['id']]=t;t.start()

    def _watch(self,r):
        import ctypes
        from ctypes import wintypes
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        create=k.CreateFileW
        create.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE)
        create.restype=wintypes.HANDLE
        read=k.ReadDirectoryChangesW
        read.argtypes=(wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,wintypes.BOOL,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p,ctypes.c_void_p)
        read.restype=wintypes.BOOL
        close=k.CloseHandle
        close.argtypes=(wintypes.HANDLE,)
        h=create(str(Path(r['path'])),0x0001,0x7,None,3,0x02000000,None)
        stop_this=self.root_stop[r['id']]
        if h in (-1,ctypes.c_void_p(-1).value):
            self.emit(r['id'],'OVERFLOW','');return
        with self.lock:self.handles[r['id']]=h
        action_names={1:'CREATED',2:'REMOVED',3:'MODIFIED',4:'RENAMED_OLD',5:'RENAMED_NEW'}
        try:
            while not self.stop.is_set() and not stop_this.is_set():
                buf=ctypes.create_string_buffer(65536)
                out=wintypes.DWORD(0)
                ok=read(h,buf,len(buf),bool(r.get('recursive',True)),0x1|0x2|0x8|0x10|0x40,ctypes.byref(out),None,None)
                if not ok or not out.value:
                    if not self.stop.is_set() and not stop_this.is_set():self.emit(r['id'],'OVERFLOW','')
                    break
                pos=0
                while pos+12<=out.value:
                    offset,act,count=struct.unpack_from('<III',buf.raw,pos)
                    if count>out.value-pos-12 or count%2:
                        self.emit(r['id'],'OVERFLOW','');break
                    relative=buf.raw[pos+12:pos+12+count].decode('utf-16-le',errors='replace')
                    self.emit(r['id'],action_names.get(act,'CHANGED'),str(Path(r['path'])/relative))
                    if offset==0:break
                    if offset<=0 or pos+offset>=out.value:break
                    pos+=offset
        finally:
            with self.lock:self.handles.pop(r['id'],None)
            close(h)

    def drain(self):
        items=[]
        while len(items)<4096:
            try:items.append(self.queue.get_nowait())
            except queue.Empty:break
        with self.lock:
            missing=set(self.overflows);self.overflows.clear()
        return items,missing

    def close(self):
        self.stop.set()
        if os.name=='nt':
            import ctypes
            k=ctypes.WinDLL('kernel32',use_last_error=True)
            from ctypes import wintypes
            k.CancelIoEx.argtypes=(wintypes.HANDLE,ctypes.c_void_p)
            with self.lock:
                for h in list(self.handles.values()):
                    # Cancel pending synchronous directory reads by closing handle.
                    k.CancelIoEx(h,None)
        for t in list(self.threads.values()):t.join(timeout=1)
