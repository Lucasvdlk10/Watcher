"""Real core + real Tk UI smoke in temporary TRACK_ONLY home; Linux CI only.
No production paths, no Downloads mutation, no LLM or network external.
"""
import json,os,subprocess,sys,tempfile,time
from pathlib import Path
from leia_watcher.config import initial_config,new_root,write_atomic
from leia_watcher.admin import request

with tempfile.TemporaryDirectory(prefix='leia-v3-smoke-') as temporary:
    base=Path(temporary);home=base/'datahome';root_path=base/'Downloads';root_path.mkdir()
    (root_path/'safe_note.txt').write_text('preserve-me')
    os.environ['LEIA_WATCHER_HOME']=str(home)
    c=initial_config()
    watched=new_root('Downloads',str(root_path),'TRACK_ONLY')
    watched['recursive']=False
    c['roots']=[watched]
    write_atomic(home/'config.json',c)
    core=subprocess.Popen([sys.executable,'-m','leia_watcher.main'],env=os.environ.copy(),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for _ in range(70):
            try:
                ping=request('ping');break
            except Exception:time.sleep(.15)
        else:raise AssertionError('Core did not start')
        assert ping['version']=='3.0.0' and ping['no_llm'] is True and ping['db']=='ok',ping
        import tkinter as tk
        from leia_watcher.ui import App
        win=tk.Tk()
        app=App(win)
        assert app._brand_logo is not None
        assert len(app._nav_icons)==12
        pages=['overview','folders','rules','files','history','hermes','overview']
        failures=[]
        def switch(index):
            try:
                if index<len(pages):
                    app.show(pages[index]);win.after(200,lambda:switch(index+1))
                else:
                    assert app.connected is True
                    assert len(app.roots)==1
                    assert app.roots[0]['recursive'] is False
                    assert app.roots[0]['mode']=='TRACK_ONLY'
                    assert app.roots[0]['name']=='Downloads'
                    win.update_idletasks()
                    if os.environ.get('LEIA_V3_SCREENSHOT'):
                        subprocess.run(['scrot',os.environ['LEIA_V3_SCREENSHOT']],check=False,timeout=8)
                    win.after(350,win.destroy)
            except Exception as e:
                failures.append(str(e));win.destroy()
        win.after(900,lambda:switch(0))
        win.after(6000,lambda:win.destroy() if win.winfo_exists() else None)
        win.mainloop()
        if failures:raise AssertionError(failures)
        assert (root_path/'safe_note.txt').read_text()=='preserve-me'
        assert len(list(root_path.iterdir()))==1,'TRACK_ONLY moved or created a file'
        print(json.dumps({'core_ping':ping,'ui_pages':pages,'real_ipc':True,'download_root_nonrecursive':True,'no_move':True}))
    finally:
        try:request('stop')
        except Exception:pass
        try:core.wait(timeout=5)
        except subprocess.TimeoutExpired:core.terminate();core.wait(timeout=4)
