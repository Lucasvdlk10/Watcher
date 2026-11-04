"""Core worker entry point, no elevated privileges and no Hermes mutations."""
import argparse
import os
import logging
from logging.handlers import RotatingFileHandler
import signal
import sys
import time
from pathlib import Path
from .config import home,load,secured_dir
from .security import secret
from .db import Database
from .engine import Watcher
from .api import install_read_token,serve
from .admin import Admin

class SingleInstance:
    def __init__(self):self.fd=None
    def __enter__(self):
        p=home()/'data'/'core.lock'
        secured_dir(p.parent)
        self.fd=open(p,'a+b')
        try:
            if os.name=='nt':
                import msvcrt
                self.fd.seek(0);self.fd.write(b' ');self.fd.flush();self.fd.seek(0)
                msvcrt.locking(self.fd.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.fd.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except (OSError,IOError):
            self.fd.close();raise RuntimeError('LEIA Watcher core is already running')
        return self
    def __exit__(self,*a):
        if self.fd:self.fd.close()


def main():
    parser=argparse.ArgumentParser(description='LEIA Watcher core')
    parser.add_argument('--home',default=None,help='Custom data directory')
    a=parser.parse_args()
    if a.home:os.environ['LEIA_WATCHER_HOME']=a.home
    for x in ('data','backups','logs','staging'):secured_dir(home()/x)
    logging.basicConfig(level=logging.INFO,handlers=[RotatingFileHandler(home()/'logs'/'watcher.log',maxBytes=2_000_000,backupCount=3,encoding='utf-8')],format='%(asctime)s %(levelname)s %(message)s')
    log=logging.getLogger('leia_watcher')
    def background_failure(args):
        log.error('Worker failure in %s',args.thread.name,exc_info=(args.exc_type,args.exc_value,args.exc_traceback))
    __import__('threading').excepthook=background_failure
    with SingleInstance():
        config=load();db=Database();watch=Watcher(db,config)
        db.apply_roots(config['roots'])
        install_read_token(db)
        secret('admin.secret')
        admin=Admin(watch,db)
        api=None
        try:
            admin.start()
            watch.start()
            api=serve(db,watch)
            log.info('LEIA Watcher core started on loopback port %d; no model calls',config['api']['port'])
            print(f'LEIA Watcher running at http://127.0.0.1:{config["api"]["port"]}; no model calls',flush=True)
            def done(*_):watch.stop.set()
            if __import__('threading').current_thread() is __import__('threading').main_thread():
                signal.signal(signal.SIGINT,done);signal.signal(signal.SIGTERM,done)
            while not watch.stop.wait(0.4):pass
        finally:
            log.info('LEIA Watcher core stopping')
            watch.shutdown();admin.shutdown()
            if api:api.shutdown();api.server_close()
            db.close()

if __name__=='__main__':main()
