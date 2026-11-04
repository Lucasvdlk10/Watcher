"""L.E.I.A. Watcher · Dark Program 3.0

Independent desktop operator; all state and mutations go exclusively through
admin.request (authenticated local IPC). Never opens or moves a file on startup.
Custom Tk canvas/surfaces: no ttk Notebook, Treeview or online dependencies.
"""
import copy
import json
import math
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import filedialog
from importlib import resources
from .admin import request
from .config import home
from .ui_rules import apply_rows,rule_values,KINDS
from .ui_prefs import load_mode,set_mode
from . import ui_kit as kit

PAGES=[('overview','Visão geral','activity'),('folders','Pastas','files'),('rules','Regras','automation'),
       ('files','Arquivos','organize'),('history','Histórico','logs'),('hermes','Integração Hermes','network')]


def _size(n):
    try:n=float(n)
    except (TypeError,ValueError):return '—'
    for unit in ('B','KB','MB','GB','TB'):
        if n<1024:return f'{n:,.0f} {unit}' if unit=='B' else f'{n:,.1f} {unit}'
        n/=1024
    return f'{n:.1f} PB'


def _safe(txt):
    return str(txt if txt is not None else '—')


class WaveHero(tk.Canvas):
    """Procedural, low-cost, focus-aware wave behind dashboard hero text."""
    def __init__(self,parent,on_action,active_motion=True,slow_motion=False):
        super().__init__(parent,bg='#131518',height=214,highlightthickness=0,bd=0)
        self.owner=parent.winfo_toplevel();self.motion=active_motion;self.slow=slow_motion
        self.active=False;self.job=None;self.phase=0.;self.fade=0.;self.last=None
        self.wave_items=[]
        try:
            with resources.as_file(resources.files('leia_watcher').joinpath('assets','obsidian_wave.png')) as p:
                self.picture=tk.PhotoImage(file=str(p))
            self.create_image(0,0,image=self.picture,anchor='nw')
        except (FileNotFoundError,tk.TclError):self.picture=None
        self.create_text(28,28,text='LEIA WATCHER   /   CONTROLE LOCAL',fill=kit.MUTED,anchor='nw',font=('Segoe UI',10,'bold'))
        self.create_text(28,59,text='Arquivos organizados. Tudo sob controle.',fill=kit.FG,anchor='nw',font=('Segoe UI',21,'bold'))
        self.create_text(29,103,text='Local por padrão. Regras claras. Histórico auditável.',fill='#C5C7CD',anchor='nw',font=('Segoe UI',11))
        self.action=kit.pill(self,'Adicionar pasta',on_action,'primary')
        self.create_window(29,154,window=self.action,anchor='nw')
        for i in range(4):
            self.wave_items.append(self.create_line(0,0,1,1,fill=['#40444E','#575A63','#4D5658','#5B5E6A'][i],width=1,smooth=True))
        self.bind('<Destroy>',self._destroy)
        self.owner_bindings=[(event,self.owner.bind(event,self._focus,add='+'))
                             for event in ('<FocusIn>','<FocusOut>','<Map>','<Unmap>')]
        self._focus()

    def _destroy(self,event):
        if event.widget==self:
            for name,funcid in self.owner_bindings:
                try:self.owner.unbind(name,funcid)
                except tk.TclError:pass
            self.owner_bindings=[]
            if self.job:
                try:self.after_cancel(self.job)
                except tk.TclError:pass
                self.job=None

    def _focus(self,event=None):
        if not self.winfo_exists():return
        # Delayed check avoids false inactivity when focus changes between child widgets.
        self.after(140,self._check_focus)

    def _check_focus(self):
        try:
            local=self.owner.focus_displayof()
            usable=self.motion and self.owner.state()=='normal' and self.owner.winfo_viewable() and local is not None
            self.set_active(bool(usable))
        except tk.TclError:pass

    def set_active(self,yes):
        self.active=yes
        if not yes:
            if self.job:
                self.after_cancel(self.job);self.job=None
            for item in self.wave_items:self.itemconfigure(item,state='hidden')
            return
        for item in self.wave_items:self.itemconfigure(item,state='normal')
        if self.job is None:self._tick()

    def _tick(self):
        self.job=None
        if not self.active or not self.winfo_exists():return
        self.phase+=.035;self.fade=min(1.,self.fade+.08)
        w=max(480,self.winfo_width())
        for i,item in enumerate(self.wave_items):
            pts=[]
            for x in range(0,w+28,18):
                y=189+i*6+math.sin(x/115+self.phase+i*.66)*6 + math.sin(x/175-self.phase*.68)*4
                pts.extend((x,y))
            self.coords(item,*pts)
            self.itemconfigure(item,fill=('#434752','#53545D','#405153','#5F626B')[i])
        self.job=self.after(90 if self.slow else (70 if on_battery() else 34),self._tick)


def on_battery():
    if os.name!='nt':return False
    try:
        import ctypes
        class Power(ctypes.Structure):
            _fields_=[('ACLineStatus',ctypes.c_byte),('BatteryFlag',ctypes.c_byte),('BatteryLifePercent',ctypes.c_byte),
                      ('SystemStatusFlag',ctypes.c_byte),('BatteryLifeTime',ctypes.c_ulong),('BatteryFullLifeTime',ctypes.c_ulong)]
        p=Power();return bool(ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(p)) and p.ACLineStatus==0)
    except (OSError,AttributeError):return False


def reduced_motion():
    if os.name!='nt':return False
    try:
        import ctypes
        # Windows SPI_GETCLIENTAREAANIMATION; 0 means motion reduced by OS.
        flag=ctypes.c_int()
        if ctypes.windll.user32.SystemParametersInfoW(0x1042,0,ctypes.byref(flag),0):return flag.value==0
    except (OSError,AttributeError):pass
    return False


class App:
    def __init__(self,root):
        self.root=root
        root.title('L.E.I.A. Watcher  ·  Dark Program 3.0')
        root.configure(bg=kit.BG);root.geometry('1280x800');root.minsize(960,650)
        self.page='overview';self.snapshot=None;self.roots=[];self.data={};self.page_num=0
        self.filters={};self.selected_root=None;self.selected_op=None;self.connected=False
        self.jobs=queue.Queue();self.working=False;self.closed=False;self.request_counter=0
        self.motion_mode=load_mode('reduced' if reduced_motion() else 'auto')
        self.nav={};self.search_var=tk.StringVar();self.filter_var=tk.StringVar()
        self._load_identity()
        self._layout();self.show('overview');self.refresh(render=True)
        root.bind_all('<Control-k>', self._command_palette)
        root.bind_all('<Control-K>', self._command_palette)
        root.bind_all('<F5>', lambda _e: self.refresh())
        for number,(key,_title,_icon) in enumerate(PAGES,1):
            root.bind_all(f'<Control-Key-{number}>',lambda _e,k=key:self.show(k))
        root.after(70,self._messages);root.after(8000,self._periodic)
        root.protocol('WM_DELETE_WINDOW',self._close)

    def _load_identity(self):
        """Load official LEIA Watcher branding from the installed wheel; offline."""
        self._nav_icons={}
        self._brand_logo=None
        self._app_icon=None
        try:
            base=resources.files('leia_watcher').joinpath('assets')
            with resources.as_file(base.joinpath('leia_watcher_48.png')) as image_file:
                self._brand_logo=tk.PhotoImage(file=str(image_file))
            with resources.as_file(base.joinpath('leia_watcher_256.png')) as image_file:
                self._app_icon=tk.PhotoImage(file=str(image_file))
                self.root.iconphoto(True,self._app_icon)
            for key,_,_ in PAGES:
                for state in ('idle','active'):
                    with resources.as_file(base.joinpath(f'nav_{key}_{state}.png')) as image_file:
                        self._nav_icons[(key,state)]=tk.PhotoImage(file=str(image_file))
        except (OSError,tk.TclError,FileNotFoundError):
            # UI stays usable with built-in glyphs if an asset is missing.
            self._nav_icons={}

    def _command_palette(self,event=None):
        """Keyboard-only navigation; never issues a mutating IPC request."""
        panel=tk.Toplevel(self.root,bg=kit.SIDE)
        panel.title('Ir para módulo · LEIA Watcher')
        panel.transient(self.root)
        panel.geometry('460x355')
        panel.resizable(False,False)
        panel.grab_set()
        box=tk.Frame(panel,bg=kit.SIDE,padx=19,pady=18);box.pack(fill='both',expand=True)
        kit.label(box,'ACESSO RÁPIDO  /  CTRL + K',10,kit.MUTED,'bold',bg=kit.SIDE).pack(anchor='w')
        field,term,entry=kit.field(box,initial='',width=39)
        field.pack(fill='x',pady=(13,11));entry.focus_set()
        items=tk.Frame(box,bg=kit.SIDE);items.pack(fill='both',expand=True)
        def jump(key):
            panel.grab_release();panel.destroy();self.show(key)
        def render(*_):
            for widget in items.winfo_children():widget.destroy()
            q=term.get().casefold().strip()
            for i,(key,text,_icon) in enumerate(PAGES):
                if q and q not in text.casefold():continue
                kit.pill(items,f'{i+1}   {text}',lambda target=key:jump(target),'subtle',width=390,compact=True).pack(anchor='w',pady=2)
        term.trace_add('write',render);render()
        def enter(_):
            options=[key for key,name,_ in PAGES if term.get().casefold().strip() in name.casefold()]
            if options:jump(options[0])
        entry.bind('<Return>',enter)
        panel.bind('<Escape>',lambda e:panel.destroy())
        return 'break'

    def _layout(self):
        self.side=tk.Frame(self.root,bg=kit.SIDE,width=216)
        self.side.pack(side='left',fill='y');self.side.pack_propagate(False)
        logo=tk.Frame(self.side,bg=kit.SIDE,padx=19,pady=25);logo.pack(fill='x')
        mark=tk.Label(logo,image=self._brand_logo,bg=kit.SIDE,bd=0) if self._brand_logo else kit.label(logo,'L',22,kit.FG,'bold',bg=kit.SIDE)
        mark.pack(side='left',padx=(0,12))
        words=tk.Frame(logo,bg=kit.SIDE);words.pack(side='left')
        kit.label(words,'L.E.I.A.',17,kit.FG,'bold',bg=kit.SIDE).pack(anchor='w')
        kit.label(words,'WATCHER',9,kit.SUBTLE,'bold',bg=kit.SIDE).pack(anchor='w')
        kit.label(self.side,'NAVEGAÇÃO',9,kit.SUBTLE,'bold',bg=kit.SIDE).pack(anchor='w',padx=23,pady=(35,12))
        for key,text,icon in PAGES:
            item=tk.Canvas(self.side,width=200,height=44,bg=kit.SIDE,highlightthickness=0,bd=0,takefocus=1,cursor='hand2')
            item.pack(padx=12,pady=3)
            item.bind('<Button-1>',lambda e,k=key:self.show(k))
            item.bind('<Return>',lambda e,k=key:self.show(k))
            item.bind('<space>',lambda e,k=key:self.show(k))
            self.nav[key]=(item,text,icon)
        tk.Frame(self.side,bg=kit.SIDE).pack(expand=True,fill='both')
        bottom=tk.Frame(self.side,bg=kit.SIDE,padx=18,pady=24);bottom.pack(fill='x')
        kit.label(bottom,'LOCAL  /  PRIVADO',9,kit.MUTED,'bold',bg=kit.SIDE).pack(anchor='w')
        kit.label(bottom,'Offline  ·  Zero tokens',9,kit.MUTED,bg=kit.SIDE).pack(anchor='w',pady=(8,3))
        kit.label(bottom,'v3.0  /  Dark Program',9,kit.SUBTLE,bg=kit.SIDE).pack(anchor='w')
        self.right=tk.Frame(self.root,bg=kit.BG);self.right.pack(side='left',fill='both',expand=True)
        head=tk.Frame(self.right,bg=kit.BG,height=91,padx=29,pady=12);head.pack(fill='x');head.pack_propagate(False)
        heading=tk.Frame(head,bg=kit.BG);heading.pack(side='left',fill='y')
        self.title=kit.label(heading,'',20,kit.FG,'bold');self.title.pack(anchor='w')
        self.subtitle=kit.label(heading,'Gerencie seus arquivos com segurança.',9,kit.MUTED);self.subtitle.pack(anchor='w')
        self.toolbar=tk.Frame(head,bg=kit.BG);self.toolbar.pack(side='right')
        kit.pill(self.toolbar,'Atualizar',self.refresh,'subtle',85,True).pack(side='right',padx=(8,0))
        self.state_label=kit.label(self.toolbar,'◌  VERIFICANDO',10,kit.GOLD,'bold');self.state_label.pack(side='right',padx=14)
        self.holder=tk.Frame(self.right,bg=kit.BG);self.holder.pack(fill='both',expand=True)
        self.footer=tk.Frame(self.right,bg=kit.SIDE,height=32,padx=24);self.footer.pack(fill='x');self.footer.pack_propagate(False)
        self.notice=kit.label(self.footer,'Conectando ao serviço local…',9,kit.MUTED,bg=kit.SIDE)
        self.notice.pack(side='left',pady=7)
        self.notice.bind('<Button-1>',lambda e:self.show('overview'))

    def _nav_draw(self):
        for key,(c,text,icon) in self.nav.items():
            c.delete('all');sel=key==self.page
            if sel:kit.rr(c,1,1,199,43,13,fill='#26292F',outline='#383C46')
            image=self._nav_icons.get((key,'active' if sel else 'idle'))
            if image:c.create_image(24,22,image=image,anchor='center')
            else:c.create_text(23,22,text='·',font=('Segoe UI',16),fill=kit.FG if sel else kit.SUBTLE)
            c.create_text(47,22,text=text,anchor='w',font=('Segoe UI',11,'bold' if sel else 'normal'),fill=kit.FG if sel else kit.MUTED)

    def show(self,page):
        self.page=page;self._nav_draw()
        for child in self.holder.winfo_children():child.destroy()
        self.scrollbox,self.body=kit.scroll(self.holder)
        self.scrollbox.pack(fill='both',expand=True)
        text=dict((k,v) for k,v,_ in PAGES).get(page,'L.E.I.A.')
        self.title.configure(text=text)
        self.subtitle.configure(text={'overview':'Tudo o que importa, em uma única visão.','folders':'Monitoramento e controle de cada pasta.',
            'rules':'Regras determinísticas, sem inteligência artificial.','files':'Inventário local, sem abrir conteúdo.',
            'history':'Todas as alterações têm registro.','hermes':'Consulta local com acesso somente leitura.'}.get(page,''))
        self.body.configure(padx=29,pady=19)
        if page=='overview':self.overview()
        elif page=='folders':self.folders()
        elif page=='rules':self.rules()
        elif page=='files':self.list_page('files')
        elif page=='history':self.list_page('audit')
        elif page=='hermes':self.hermes()

    def _run(self,tag,func,callback=None):
        def work():
            try:result=func();self.jobs.put((tag,True,result,callback))
            except Exception as exc:self.jobs.put((tag,False,exc,callback))
        threading.Thread(target=work,daemon=True,name='leia-ui-'+tag).start()

    def _messages(self):
        if self.closed:return
        for _ in range(20):
            try:tag,ok,data,callback=self.jobs.get_nowait()
            except queue.Empty:break
            if ok:
                if callback:callback(data)
            else:
                if tag=='refresh':
                    self.connected=False;self.state_label.configure(text='◌  DESCONECTADO',fg=kit.RED)
                    self.notice.configure(text='Serviço indisponível. Clique em Iniciar serviço para conectar.',fg=kit.GOLD)
                else:self.notice.configure(text=f'Não foi possível concluir: {type(data).__name__}: {data}',fg=kit.RED)
        self.root.after(90,self._messages)

    def _periodic(self):
        if self.closed:return
        # Background polling updates the data model and connection badges only.
        # Rebuilding the whole page every cycle causes visible Windows/Tk flicker.
        if self.root.state()=='normal' and not self.working:self.refresh(render=False)
        self.root.after(9000,self._periodic)

    @staticmethod
    def _load_all():return request('ui_snapshot'),request('roots')

    def _receive_all(self,response,render=True):
        self.connected=True;self.snapshot,self.roots=response
        self.state_label.configure(text='●  ATIVO  /  LOCAL',fg=kit.GREEN)
        self.notice.configure(text='Serviço conectado · IPC autenticado · Hermes somente leitura',fg=kit.MUTED)
        if render:self.show(self.page)

    def refresh(self,render=True):
        if self.working:return
        self._run('refresh',self._load_all,lambda response:self._receive_all(response,render=render))

    def _action(self,cmd,**params):
        if self.working:return
        self.working=True
        self.notice.configure(text='Aplicando ação local…',fg=kit.GOLD)
        def callback(result):
            self.working=False
            self.notice.configure(text='Ação concluída. Atualizando painel…',fg=kit.GREEN)
            self.refresh()
            if cmd=='preview':self.preview_dialog(result)
            if cmd=='backup':self.info('Backup criado',f'Arquivo de backup:\n{result.get("path")}')
            if cmd=='undo':self.info('Desfazer',json.dumps(result,ensure_ascii=False,indent=2)[:1700])
        def work():
            try:self.jobs.put(('action',True,request(cmd,**params),callback))
            except Exception as exc:self.jobs.put(('action',False,exc,lambda x:None))
            finally:self.jobs.put(('release',True,None,lambda x:setattr(self,'working',False)))
        threading.Thread(target=work,daemon=True).start()

    def _muted_banner(self):
        if self.connected:return False
        edge,card=kit.surface(self.body)
        edge.pack(fill='x',pady=(0,22))
        kit.label(card,'O serviço local não está em execução',15,kit.GOLD,'bold',bg=kit.PANEL).pack(anchor='w')
        kit.label(card,'Você pode abrir a interface sem ativar a organização. Iniciar o serviço é uma ação explícita.',11,kit.MUTED,bg=kit.PANEL,wrap=620).pack(anchor='w',pady=10)
        kit.pill(card,'Iniciar serviço local',self.start_core,'primary').pack(anchor='w')
        return True

    def start_core(self):
        if not kit.confirm(self.root,'Iniciar serviço','O serviço será executado localmente em segundo plano. Pastas já ativas na sua configuração poderão ser processadas de acordo com as regras salvas.'):return
        try:
            kw={}
            if os.name=='nt':kw['creationflags']=0x08000000
            subprocess.Popen([sys.executable,'-m','leia_watcher.main'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**kw)
            self.notice.configure(text='Serviço iniciado. Conectando…',fg=kit.CYAN)
            self.root.after(1400,self.refresh)
        except (OSError,ValueError) as exc:self.info('Não foi possível iniciar',str(exc))

    def section(self,title,subtitle='',action=None,callback=None,parent=None):
        p=parent or self.body
        bar=tk.Frame(p,bg=p.cget('bg'));bar.pack(fill='x',pady=(18,13))
        a=tk.Frame(bar,bg=bar.cget('bg'));a.pack(side='left')
        kit.label(a,title,14,kit.FG,'bold').pack(anchor='w')
        if subtitle:kit.label(a,subtitle,10,kit.MUTED).pack(anchor='w',pady=3)
        if action:kit.pill(bar,action,callback,'subtle',compact=True).pack(side='right')

    def _stat(self,parent,title,value,hint,accent):
        border,card=kit.surface(parent,14,15)
        kit.label(card,title.upper(),9,kit.SUBTLE,'bold',bg=kit.PANEL).pack(anchor='w')
        kit.label(card,str(value),24,accent,'bold',bg=kit.PANEL).pack(anchor='w',pady=(10,4))
        kit.label(card,hint,9,kit.MUTED,bg=kit.PANEL).pack(anchor='w')
        return border

    def overview(self):
        self._muted_banner()
        hero=WaveHero(self.body,self.add_root,self.motion_mode!='off',self.motion_mode=='reduced')
        hero.pack(fill='x',pady=(0,18))
        state=self.snapshot or {}
        current=state.get('current_files_count',state.get('files_count',0))
        legacy=state.get('legacy_files_count',0)
        inventory_hint=(f'{current:,} atuais + {legacy:,} históricos'.replace(',','.')
                        if legacy else 'inventário local')
        grid=tk.Frame(self.body,bg=kit.BG);grid.pack(fill='x')
        stats=[('Pastas monitoradas',len(self.roots),'raízes configuradas',kit.FG),
               ('Arquivos catalogados',f'{state.get("files_count",0):,}'.replace(',','.'),inventory_hint,kit.FG),
               ('Operações pendentes',state.get('pending',0),'aguardando finalização',kit.GOLD if state.get('pending',0) else kit.FG),
               ('Banco de dados','OK' if state.get('database')=='ok' else 'VERIFICAR','integridade SQLite',kit.GREEN if state.get('database')=='ok' else kit.RED)]
        for i,(name,val,hint,col) in enumerate(stats):
            card=self._stat(grid,name,val,hint,col)
            card.grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 6,0 if i==3 else 6))
            grid.columnconfigure(i,weight=1,uniform='cards')
        bottom=tk.Frame(self.body,bg=kit.BG);bottom.pack(fill='both',expand=True,pady=(7,25))
        left=tk.Frame(bottom,bg=kit.BG);left.pack(side='left',fill='both',expand=True,padx=(0,11))
        right=tk.Frame(bottom,bg=kit.BG,width=285);right.pack(side='right',fill='y');right.pack_propagate(False)
        self.section('Atividade recente','Os últimos eventos registrados no dispositivo.', 'Histórico completo',lambda:self.show('history'),left)
        box,content=kit.surface(left,12,7);box.pack(fill='both',expand=True)
        recent=state.get('recent',[])
        if not recent:kit.empty(content,'Sem eventos por enquanto','Atividades de monitoramento e auditoria aparecerão aqui.').pack(fill='both')
        for item in recent:
            r=tk.Frame(content,bg=kit.PANEL,pady=9);r.pack(fill='x')
            kit.label(r,'◉',13,kit.CYAN,bg=kit.PANEL).pack(side='left',padx=7)
            msg=tk.Frame(r,bg=kit.PANEL);msg.pack(side='left',fill='x',expand=True)
            kit.label(msg,_safe(item.get('action')),10,kit.FG,'bold',bg=kit.PANEL).pack(anchor='w')
            kit.label(msg,f"{_safe(item.get('reason_code'))} · {_safe(item.get('root_id'))}",9,kit.MUTED,bg=kit.PANEL).pack(anchor='w')
            kit.label(r,_safe(item.get('outcome')),9,kit.GREEN if item.get('outcome') in ('OK','MOVED','UNDONE') else kit.GOLD,bg=kit.PANEL).pack(side='right',padx=10)
        self.section('Ações rápidas','Atalhos seguros para operações locais.',parent=right)
        b,actions=kit.surface(right,14,10);b.pack(fill='x')
        for title,callback in [('Gerenciar pastas',lambda:self.show('folders')),
                               ('Simular regras',lambda:self.show('folders')),
                               ('Backup consistente',lambda:self._action('backup')),
                               *(([('Desfazer movimentação',self.undo)] if state.get('undo_eligible',0) else [])),
                               ('Ver integração Hermes',lambda:self.show('hermes'))]:
            kit.pill(actions,title,callback,'subtle',width=235,compact=True).pack(pady=4)
        kit.label(right,'✓  Nenhuma telemetria · 100% local',10,kit.MUTED,bg=kit.BG).pack(anchor='w',pady=17)
        kit.label(right,'MOVIMENTO AMBIENTAL',9,kit.SUBTLE,'bold').pack(anchor='w',pady=(0,5))
        modes=tk.Frame(right,bg=kit.BG);modes.pack(anchor='w')
        for key,title in [('auto','Suave'),('reduced','Reduzido'),('off','Desligado')]:
            kit.pill(modes,title,lambda m=key:self.set_motion(m),
                     'success' if key==self.motion_mode else 'subtle',compact=True).pack(side='left',padx=(0,5))

    def set_motion(self,mode):
        try:set_mode(mode)
        except (ValueError,OSError) as exc:self.info('Preferência não salva',str(exc));return
        self.motion_mode=mode
        if self.page=='overview':self.show('overview')

    def folders(self):
        self._muted_banner()
        row=tk.Frame(self.body,bg=kit.BG);row.pack(fill='x',pady=(0,16))
        kit.label(row,f'{len(self.roots)} pastas configuradas',11,kit.MUTED).pack(side='left')
        kit.pill(row,'+  Adicionar pasta',self.add_root,'primary').pack(side='right')
        snap={r['root_id']:r for r in (self.snapshot or {}).get('roots',[])}
        if not self.roots:
            box,c=kit.surface(self.body);box.pack(fill='x')
            kit.empty(c,'Comece escolhendo uma pasta','O rastreio acompanha arquivos sem modificá-los.','Adicionar pasta',self.add_root).pack(fill='x')
            return
        for root in self.roots:
            state=snap.get(root['id'],{})
            edge,card=kit.surface(self.body,17,14)
            edge.pack(fill='x',pady=(0,12))
            head=tk.Frame(card,bg=kit.PANEL);head.pack(fill='x')
            kit.label(head,'▤',17,kit.CYAN,bg=kit.PANEL).pack(side='left',padx=(0,14))
            names=tk.Frame(head,bg=kit.PANEL);names.pack(side='left',fill='x',expand=True)
            kit.label(names,root['name'],15,kit.FG,'bold',bg=kit.PANEL).pack(anchor='w')
            kit.label(names,root['path'],10,kit.MUTED,bg=kit.PANEL,wrap=570).pack(anchor='w',pady=3)
            healthy=state.get('health','OFF')
            kit.label(head,'● '+_safe(healthy),10,kit.GREEN if healthy=='WATCHING' else kit.GOLD,bg=kit.PANEL).pack(side='right')
            info=tk.Frame(card,bg=kit.PANEL);info.pack(fill='x',pady=(12,12))
            mode='ORGANIZAÇÃO' if root['mode']=='ORGANIZE' else 'RASTREIO PURO'
            kit.label(info,mode,10,kit.CYAN if root['mode']=='TRACK_ONLY' else kit.BLUE,'bold',bg=kit.PANEL).pack(side='left')
            kit.label(info,'  ·  '+('Ativa' if root.get('enabled') else 'Desativada')+'  ·  Última varredura: '+_safe(state.get('last_scan_finished_at'))[:19],9,kit.MUTED,bg=kit.PANEL).pack(side='left')
            kit.divider(card)
            action=tk.Frame(card,bg=kit.PANEL);action.pack(fill='x')
            rid=root['id']
            ops=[('Editar regras',lambda r=rid:self.edit_root(r)),('Simular',lambda r=rid:self._action('preview',root_id=r,limit=40)),
                 ('Varrer',lambda r=rid:self._action('scan',root_id=r)),
                 ('Pausar' if rid not in (self.snapshot or {}).get('paused',[]) else 'Retomar',
                  lambda r=rid:self._action('resume' if r in (self.snapshot or {}).get('paused',[]) else 'pause',root_id=r))]
            if not root.get('enabled'):ops.append(('Ativar',lambda r=rid:self.activate(r)))
            for title,fn in ops:kit.pill(action,title,fn,'subtle',compact=True).pack(side='left',padx=(0,8))
            kit.pill(action,'Remover',lambda r=rid:self.remove_root(r),'danger',compact=True).pack(side='right')

    def rules(self):
        self._muted_banner()
        self.section('Motor de regras','Escolha uma pasta. A edição visual preserva regras e IDs existentes.')
        if not self.roots:
            edge,body=kit.surface(self.body);edge.pack(fill='x')
            kit.empty(body,'Nenhuma regra cadastrada','Adicione uma pasta para configurar o motor.','Adicionar pasta',self.add_root).pack()
            return
        for root in self.roots:
            edge,card=kit.surface(self.body);edge.pack(fill='x',pady=7)
            kit.label(card,root['name'],14,kit.FG,'bold',bg=kit.PANEL).pack(anchor='w')
            rs=root.get('ruleset',{})
            steps='  →  '.join(rs.get('path_steps',[])) or 'Somente inventário'
            kit.label(card,steps,10,kit.CYAN,bg=kit.PANEL).pack(anchor='w',pady=7)
            kit.label(card,f"{len(rs.get('rules',[]))} regras · {len(root.get('exclusions',[]))} exclusões · Versão {rs.get('version',1)}",10,kit.MUTED,bg=kit.PANEL).pack(anchor='w')
            kit.pill(card,'Abrir editor visual',lambda r=root['id']:self.edit_root(r),'primary').pack(anchor='e',pady=(0,0))

    def list_page(self,entity):
        self._muted_banner()
        descriptions={'files':'Pesquise o índice, sem abrir arquivos.',
                      'audit':'Auditoria por evento, operação e resultado.',
                      'operations':'Operações e seus estados duráveis.'}
        title='Inventário de arquivos' if entity=='files' else 'Registro de atividade' if entity=='audit' else 'Movimentações'
        self.section(title,descriptions[entity],
                     'Movimentações' if entity=='audit' else 'Auditoria' if entity=='operations' else None,
                     (lambda:self.list_page('operations')) if entity=='audit' else (lambda:self.list_page('audit')) if entity=='operations' else None)
        controls=tk.Frame(self.body,bg=kit.BG);controls.pack(fill='x',pady=7)
        search_box,self.search_var,entry=kit.field(controls,'Buscar',self.filters.get('q',''),30);search_box.pack(side='left',fill='x',expand=True,padx=(0,12))
        entry.bind('<Return>',lambda e:self._query(entity,reset=True))
        kit.pill(controls,'Buscar',lambda:self._query(entity,reset=True),'primary',compact=True).pack(side='left',padx=4)
        kit.pill(controls,'Limpar',lambda:self._clear_search(entity),compact=True).pack(side='left',padx=4)
        if entity=='audit':
            kit.pill(controls,'Exportar CSV',lambda:self.export('audit'),compact=True).pack(side='right',padx=(6,0))
            if (self.snapshot or {}).get('undo_eligible',0):
                kit.pill(controls,'Desfazer último',self.undo,'danger',compact=True).pack(side='right',padx=(6,0))
        if entity=='files':kit.pill(controls,'Exportar CSV',lambda:self.export('files'),compact=True).pack(side='right',padx=(6,0))
        if entity=='operations':kit.pill(controls,'Exportar CSV',lambda:self.export('operations'),compact=True).pack(side='right',padx=(6,0))
        filter_row=tk.Frame(self.body,bg=kit.BG);filter_row.pack(fill='x',pady=(8,0))
        def dropdown(title,key,options):
            active=self.filters.get(key,'')
            text=next((name for name,value in options if value==active),'Todas')
            btn=kit.pill(filter_row,f'{title}: {text}  ▾',lambda:open_menu(),compact=True)
            def choose(value):
                self.filters[key]=value;self.page_num=0
                self.show(self.page)
            def open_menu():
                menu=tk.Menu(self.root,tearoff=0,bg=kit.ELEVATED,fg=kit.FG,
                             activebackground=kit.BLUE,activeforeground='#071126')
                for name,value in options:menu.add_command(label=name,command=lambda v=value:choose(v))
                menu.tk_popup(btn.winfo_rootx(),btn.winfo_rooty()+btn.winfo_height())
                menu.grab_release()
            btn.pack(side='left',padx=(0,8))
        dropdown('Pasta','root_id',[('Todas','')]+[(r['name'],r['id']) for r in self.roots])
        if entity=='files':
            dropdown('Estado','status',[('Todos',''),('Indexados','INDEXED'),('Movidos','MOVED'),('Histórico anterior','LEGACY'),('Indefinido','MISSING_UNCONFIRMED')])
            ext_box,ext_var,ext_field=kit.field(filter_row,initial=self.filters.get('extension',''),width=11)
            ext_box.pack(side='left',padx=5)
            ext_field.bind('<Return>',lambda e:(self.filters.update({'extension':ext_var.get().strip().lower()}),self._query(entity,reset=True)))
            kit.pill(filter_row,'Extensão ↵',lambda:(self.filters.update({'extension':ext_var.get().strip().lower()}),self._query(entity,reset=True)),compact=True).pack(side='left')
        elif entity=='audit':
            dropdown('Resultado','outcome',[('Todos',''),('OK','OK'),('Erro','FAILED'),('Movido','MOVED')])
        else:
            dropdown('Etapa','stage',[('Todas',''),('Movido','MOVED'),('Desfeito','UNDONE'),('Falha','FAILED'),('Atenção','NEEDS_ATTENTION')])
        edge,box=kit.surface(self.body,10,10)
        edge.pack(fill='both',expand=True,pady=14)
        self.table_area=box
        self.table_bottom=tk.Frame(self.body,bg=kit.BG);self.table_bottom.pack(fill='x')
        self.current_entity=entity
        self._query(entity)

    def _clear_search(self,entity):
        self.search_var.set('');self.filters={};self.page_num=0;self._query(entity)

    def _query(self,entity,reset=False):
        if reset:self.page_num=0
        q=self.search_var.get().strip()
        if q:self.filters['q']=q
        else:self.filters.pop('q',None)
        if not self.connected:
            kit.empty(self.table_area,'Sem conexão','Inicie o serviço local para consultar os dados.').pack(fill='x')
            return
        self.request_counter+=1;rid=self.request_counter
        for child in self.table_area.winfo_children():child.destroy()
        kit.label(self.table_area,'Consultando índice local…',11,kit.MUTED,bg=kit.PANEL).pack(pady=30)
        def done(data):
            if self.closed or rid!=self.request_counter or self.page not in ('files','history'):return
            self._render_table(entity,data)
        self._run('query',lambda:request('ui_list',entity=entity,filters=self.filters,page=self.page_num,limit=40),done)

    def _render_table(self,entity,data):
        box=self.table_area
        for child in box.winfo_children():child.destroy()
        records=data['items']
        if entity=='files':cols=[('filename','Nome',31),('root_id','Pasta',20),('extension','Tipo',8),('size_bytes','Tamanho',12),('status','Estado',17)]
        elif entity=='audit':cols=[('occurred_at','Data / UTC',23),('action','Ação',25),('outcome','Resultado',19),('reason_code','Detalhes',27)]
        else:cols=[('created_at','Data / UTC',23),('operation_kind','Tipo',16),('stage','Estado',22),('root_id','Pasta',25)]
        header=tk.Frame(box,bg=kit.ELEVATED,pady=10);header.pack(fill='x')
        for key,title,ratio in cols:
            kit.label(header,title,9,kit.MUTED,'bold',bg=kit.ELEVATED,width=ratio).pack(side='left',fill='x',expand=True,padx=6)
        if not records:
            kit.empty(box,'Nada encontrado','Altere a busca ou aguarde o próximo monitoramento.').pack(fill='x')
        for i,rec in enumerate(records):
            row=tk.Frame(box,bg=kit.PANEL if i%2==0 else '#192131',pady=10,cursor='hand2')
            row.pack(fill='x')
            for key,title,ratio in cols:
                val=_size(rec.get(key)) if key=='size_bytes' else _safe(rec.get(key))
                if len(val)>34:val=val[:31]+'…'
                txt=kit.label(row,val,10,kit.FG if key in ('filename','action','operation_kind') else kit.MUTED,
                              bg=row.cget('bg'),width=ratio)
                txt.pack(side='left',fill='x',expand=True,padx=6)
                txt.bind('<Button-1>',lambda e,r=rec:self.record_details(r,entity))
            row.bind('<Button-1>',lambda e,r=rec:self.record_details(r,entity))
        for child in self.table_bottom.winfo_children():child.destroy()
        foot=self.table_bottom
        kit.label(foot,f'{data["total"]} registros · página {self.page_num+1}',10,kit.MUTED).pack(side='left')
        if data['has_more']:kit.pill(foot,'Próxima ›',lambda:self._advance(entity,1),compact=True).pack(side='right')
        if self.page_num:kit.pill(foot,'‹ Anterior',lambda:self._advance(entity,-1),compact=True).pack(side='right',padx=8)

    def _advance(self,entity,delta):
        self.page_num=max(0,self.page_num+delta);self._query(entity)

    def record_details(self,record,entity):
        w=kit.modal(self.root,'Detalhes do registro','Dados locais do inventário. Nenhum conteúdo de arquivo foi aberto.',730,490)
        txt=tk.Text(w,bg=kit.ELEVATED,fg=kit.FG,font=('Consolas',10),relief='flat',wrap='word',padx=14,pady=15)
        body=json.dumps(record,ensure_ascii=False,indent=2)
        txt.insert('1.0',body);txt.configure(state='disabled');txt.pack(fill='both',expand=True,pady=10)
        bar=tk.Frame(w,bg=kit.SIDE);bar.pack(fill='x')
        kit.pill(bar,'Copiar detalhes',lambda:self.copy(body),'subtle').pack(side='left')
        kit.pill(bar,'Fechar',w.destroy,'primary').pack(side='right')

    def hermes(self):
        self._muted_banner()
        edge,card=kit.surface(self.body,24,23);edge.pack(fill='x',pady=(0,18))
        kit.label(card,'◇   API local do Hermes',19,kit.FG,'bold',bg=kit.PANEL).pack(anchor='w')
        kit.label(card,'O Hermes consulta o inventário. Ele não organiza, move ou exclui arquivos pela API HTTP.',11,kit.MUTED,bg=kit.PANEL,wrap=760).pack(anchor='w',pady=(10,17))
        for title,text,color in [('Vínculo','127.0.0.1:8766  ·  somente na sua máquina',kit.CYAN),
                                 ('Permissões','GET + WebSocket autenticados · somente leitura',kit.GREEN),
                                 ('Privacidade','Sem nuvem, sem analytics e zero chamadas LLM',kit.GREEN)]:
            row=tk.Frame(card,bg=kit.PANEL,pady=9);row.pack(fill='x')
            kit.label(row,title,11,kit.FG,'bold',bg=kit.PANEL,width=18).pack(side='left')
            kit.label(row,text,11,color,bg=kit.PANEL).pack(side='left')
        kit.divider(card)
        kit.label(card,'Exemplo seguro (token como marcador, nunca embutido)',10,kit.MUTED,bg=kit.PANEL).pack(anchor='w')
        cmd='curl -H "Authorization: Bearer <TOKEN_LOCAL>" "http://127.0.0.1:8766/v1/files?limit=10"'
        kit.label(card,cmd,10,kit.CYAN,bg=kit.PANEL,wrap=790).pack(anchor='w',pady=12)
        buttons=tk.Frame(card,bg=kit.PANEL);buttons.pack(fill='x')
        kit.pill(buttons,'Copiar exemplo',lambda:self.copy(cmd),'primary').pack(side='left',padx=(0,10))
        kit.pill(buttons,'Local do token',self.token_path).pack(side='left')
        self.section('Segurança do acesso','O segredo é lido somente pelo usuário local autorizado.')
        edge,box=kit.surface(self.body);edge.pack(fill='x')
        kit.label(box,'Nenhum token é mostrado nesta interface. O caminho do arquivo só aparece após confirmação.\nA API HTTP não possui endpoints POST, PUT, PATCH ou DELETE.',11,kit.MUTED,bg=kit.PANEL,wrap=760).pack(anchor='w')

    def copy(self,text):
        self.root.clipboard_clear();self.root.clipboard_append(text)
        self.notice.configure(text='Copiado para a área de transferência',fg=kit.CYAN)

    def token_path(self):
        if kit.confirm(self.root,'Exibir caminho do token','O caminho do segredo local será exibido, mas o conteúdo do token nunca será mostrado.'):
            self.info('Local do token de leitura',str(home()/'data'/'hermes_read.token'))

    def info(self,title,msg):
        w=kit.modal(self.root,title,str(msg),600,340)
        t=tk.Text(w,bg=kit.ELEVATED,fg=kit.FG,relief='flat',wrap='word',font=('Segoe UI',11),padx=12,pady=10)
        t.insert('1.0',str(msg));t.configure(state='disabled');t.pack(fill='both',expand=True,pady=8)
        kit.pill(w,'Fechar',w.destroy,'primary').pack(anchor='e',pady=10)

    def add_root(self):
        if not self.connected:self.info('Serviço local','Inicie primeiro o serviço na Visão geral.');return
        w=kit.modal(self.root,'Adicionar diretório','Selecione uma pasta existente e defina como o Watcher deve trabalhar nela.',650,590)
        # Reserve the action bar first so Apply/Cancel are never clipped by form content.
        bar=tk.Frame(w,bg=kit.SIDE);bar.pack(side='bottom',fill='x',pady=(14,2))
        kit.label(w,'NOME DE EXIBIÇÃO  ·  OPCIONAL',10,kit.MUTED,'bold',bg=kit.SIDE).pack(anchor='w',pady=(3,4))
        namebox,name,ent=kit.field(w);namebox.pack(fill='x')
        kit.label(w,'Se ficar vazio, será usado automaticamente o nome do diretório.',9,kit.SUBTLE,bg=kit.SIDE).pack(anchor='w',pady=(4,0))
        kit.label(w,'DIRETÓRIO LOCAL',10,kit.MUTED,'bold',bg=kit.SIDE).pack(anchor='w',pady=(15,4))
        pathrow=tk.Frame(w,bg=kit.SIDE);pathrow.pack(fill='x')
        pathbox,path,pa=kit.field(pathrow,width=41);pathbox.pack(side='left',fill='x',expand=True)
        def browse():
            chosen=filedialog.askdirectory(parent=w,title='Escolher diretório existente')
            if chosen:
                path.set(chosen)
                if not name.get().strip():name.set(Path(chosen).name)
        kit.pill(pathrow,'Procurar',browse,compact=True).pack(side='right',padx=(8,0))
        mode=tk.StringVar(value='TRACK_ONLY')
        kit.label(w,'MODO DE TRABALHO',10,kit.MUTED,'bold',bg=kit.SIDE).pack(anchor='w',pady=(15,4))
        for value,txt in [('TRACK_ONLY','Rastreio puro — cataloga sem mover arquivos'),('ORGANIZE','Organização — aplica uma estratégia nesta pasta')]:
            tk.Radiobutton(w,text=txt,value=value,variable=mode,bg=kit.SIDE,fg=kit.FG,
                           activebackground=kit.SIDE,activeforeground=kit.CYAN,selectcolor=kit.ELEVATED,font=('Segoe UI',10)).pack(anchor='w')
        organize_box=tk.Frame(w,bg=kit.ELEVATED,padx=13,pady=10)
        kit.label(organize_box,'COMO ORGANIZAR',9,kit.CYAN,'bold',bg=kit.ELEVATED).pack(anchor='w',pady=(0,5))
        profile=tk.StringVar(value='TYPE')
        for value,txt in [('TYPE','Por tipo de arquivo — Imagens, PDFs, Compactados…'),
                          ('TYPE_DATE','Por tipo e data — Categoria / Ano / Mês'),
                          ('DATE','Por data — Ano / Mês')]:
            tk.Radiobutton(organize_box,text=txt,value=value,variable=profile,bg=kit.ELEVATED,fg=kit.FG,
                           activebackground=kit.ELEVATED,activeforeground=kit.CYAN,selectcolor=kit.PANEL,font=('Segoe UI',9)).pack(anchor='w')
        activate=tk.BooleanVar(value=True)
        loose=tk.BooleanVar(value=False)
        tk.Checkbutton(organize_box,text='Ativar organização assim que eu aplicar',variable=activate,bg=kit.ELEVATED,fg=kit.FG,
                       activebackground=kit.ELEVATED,activeforeground=kit.CYAN,selectcolor=kit.PANEL,font=('Segoe UI',9)).pack(anchor='w',pady=(7,0))
        tk.Checkbutton(organize_box,text='Mover subpastas fora do padrão para “Pastas avulsas”',variable=loose,bg=kit.ELEVATED,fg=kit.FG,
                       activebackground=kit.ELEVATED,activeforeground=kit.CYAN,selectcolor=kit.PANEL,font=('Segoe UI',9)).pack(anchor='w')
        def update_mode(*_):
            if mode.get()=='ORGANIZE':organize_box.pack(fill='x',pady=(10,0))
            else:organize_box.pack_forget()
        mode.trace_add('write',update_mode);update_mode()
        def save():
            selected=path.get().strip()
            if not selected:self.info('Diretório necessário','Selecione um diretório local para continuar.');return
            if not Path(selected).is_dir():self.info('Diretório inválido','A pasta selecionada não existe ou não está acessível.');return
            params={'name':name.get().strip(),'path':selected,'mode':mode.get()}
            if mode.get()=='ORGANIZE':
                params.update(organization_profile=profile.get(),activate=activate.get(),
                              organize_loose_folders=loose.get())
                if activate.get():
                    if not kit.confirm(self.root,'Ativar organização',
                        'O Watcher começará a organizar esta pasta usando o modo selecionado. Colisões preservam os dois arquivos e nenhum arquivo será sobrescrito.',
                        critical=True,word='ORGANIZAR'):return
                    params['confirmation']='I_CONFIRM_FILE_MOVES'
            w.destroy();self._action('add_root',**params)
        kit.pill(bar,'Cancelar',w.destroy).pack(side='right',padx=5)
        kit.pill(bar,'Aplicar pasta',save,'primary').pack(side='right',padx=5)

    def activate(self,rid):
        root=next((x for x in self.roots if x['id']==rid),None)
        if not root:return
        if root['mode']=='ORGANIZE':
            if not kit.confirm(self.root,'Ativar organização',f'ATENÇÃO: a pasta {root["name"]} poderá ter arquivos movidos. Confirme apenas após executar Simular e revisar as regras.',critical=True,word='ORGANIZAR'):return
            self._action('activate',root_id=rid,confirmation='I_CONFIRM_FILE_MOVES')
        else:self._action('activate',root_id=rid)

    def remove_root(self,rid):
        root=next((x for x in self.roots if x['id']==rid),None)
        if not root:return
        if kit.confirm(self.root,'Remover monitoramento',f'A pasta {root["name"]} deixará de ser observada. Os arquivos físicos não serão excluídos. Histórico é preservado.',critical=True,word='REMOVER'):
            self._action('remove_root',root_id=rid)

    def preview_dialog(self,data):
        self.info('Simulação · nenhuma alteração realizada',json.dumps(data,ensure_ascii=False,indent=2)[:6000])

    def undo(self):
        if kit.confirm(self.root,'Desfazer a última movimentação',
                       'O sistema verificará identidade e integridade do arquivo antes de restaurar. Uma restauração pode falhar de forma segura se o arquivo foi modificado.',True,'DESFAZER'):
            self._action('undo')

    def export(self,kind):
        if not self.connected:return
        path=filedialog.asksaveasfilename(parent=self.root,title='Exportar dados locais',defaultextension='.csv',
                                          filetypes=[('CSV','*.csv'),('JSON','*.json')])
        if path and kit.confirm(self.root,'Exportar arquivos',f'Esta exportação pode conter nomes e caminhos privados. Deseja salvar em:\n{path}?'):
            self._action('export',kind=kind,path=path)

    def edit_root(self,rid):
        root=next((copy.deepcopy(r) for r in self.roots if r['id']==rid),None)
        if not root:return
        current=getattr(self,'rule_editor',None)
        if current is not None:
            try:
                if current.window.winfo_exists():
                    current.window.deiconify();current.window.lift();current.window.focus_force();return
            except (AttributeError,tk.TclError):pass
        try:self.rule_editor=RuleEditor(self,root)
        except Exception as exc:self.info('Editor visual não abriu',f'{type(exc).__name__}: {exc}')

    def _close(self):
        self.closed=True
        self.root.destroy()


def main():
    root=tk.Tk();App(root);root.mainloop()

if __name__=='__main__':main()

class RuleEditor:
    """Visual root/rules editor. Original rules remain intact until Save over IPC.

    Edits to already-active ORGANIZE roots first deactivate the root. The user
    must preview and explicitly activate again, preventing silent reprocessing.
    """
    def __init__(self,app,original):
        self.app=app;self.original=original;self.root=copy.deepcopy(original)
        self.window=kit.modal(app.root,'Editor de regras · '+original['name'],
                         'A alteração de regras numa pasta em organização ativa a desativa até nova confirmação.',990,730)
        self.window.minsize(850,600)
        self.rules=copy.deepcopy(self.root.get('ruleset',{}).get('rules',[]))
        self.rows=[];self.steps={};self.exclusions=None
        actions=tk.Frame(self.window,bg=kit.SIDE);actions.pack(side='bottom',fill='x',pady=(9,0))
        kit.pill(actions,'Cancelar',self.window.destroy).pack(side='right',padx=5)
        kit.pill(actions,'Salvar com validação',self.save,'primary').pack(side='right',padx=5)
        kit.pill(actions,'JSON avançado',self.advanced).pack(side='left',padx=4)
        self.scroller,body=kit.scroll(self.window);self.scroller.pack(fill='both',expand=True)
        self.body=body;self._build()

    def _build(self):
        for widget in self.body.winfo_children():widget.destroy()
        root=self.root;rs=root.get('ruleset',{})
        kit.label(self.body,'CONFIGURAÇÃO DA PASTA',10,kit.CYAN,'bold').pack(anchor='w',pady=(10,8))
        panel,c=kit.surface(self.body,14,12);panel.pack(fill='x')
        cols=tk.Frame(c,bg=kit.PANEL);cols.pack(fill='x')
        a=tk.Frame(cols,bg=kit.PANEL);a.pack(side='left',fill='x',expand=True,padx=(0,10))
        b=tk.Frame(cols,bg=kit.PANEL);b.pack(side='left',fill='x',expand=True)
        self.name=self._value_field(a,'Nome visível',root.get('name',''))
        self.output=self._value_field(b,'Diretório de saída',root.get('output_path') or '')
        choices=tk.Frame(c,bg=kit.PANEL);choices.pack(fill='x',pady=(16,5))
        self.mode=tk.StringVar(value=root['mode']);self.collision=tk.StringVar(value=root.get('conflict_policy','RENAME'))
        self.recursive=tk.BooleanVar(value=bool(root.get('recursive',True)))
        self.enabled=tk.BooleanVar(value=bool(root.get('enabled',False)))
        self._choice(choices,'Modo',self.mode,('TRACK_ONLY','ORGANIZE')).pack(side='left',padx=(0,18))
        self._choice(choices,'Colisão',self.collision,('RENAME','SKIP')).pack(side='left',padx=(0,18))
        for txt,var in [('Incluir subpastas',self.recursive),('Ativa',self.enabled)]:
            tk.Checkbutton(choices,text=txt,variable=var,bg=kit.PANEL,fg=kit.FG,
                           activebackground=kit.PANEL,activeforeground=kit.FG,
                           selectcolor=kit.ELEVATED,font=('Segoe UI',10)).pack(side='left',padx=(0,15))
        kit.label(c,'OVERWRITE continua desativado neste editor. Mantenha a configuração original para ajustes avançados protegidos.',9,kit.GOLD,bg=kit.PANEL,wrap=850).pack(anchor='w',pady=(12,0))
        kit.label(self.body,'ORDEM DAS ETAPAS',10,kit.CYAN,'bold').pack(anchor='w',pady=(21,8))
        stepbox,steps=kit.surface(self.body,13,9);stepbox.pack(fill='x')
        kit.label(steps,'Marque as etapas na ordem: Tipo → Palavra-chave → Data → Tamanho → Origem.\nA ordem será mantida conforme a lista abaixo.',10,kit.MUTED,bg=kit.PANEL).pack(anchor='w')
        line=tk.Frame(steps,bg=kit.PANEL);line.pack(fill='x',pady=8)
        for key,txt in [('type','Tipo'),('keyword','Palavra'),('date','Data'),('size','Tamanho'),('source','Origem')]:
            var=tk.BooleanVar(value=key in rs.get('path_steps',[]));self.steps[key]=var
            tk.Checkbutton(line,text=txt,variable=var,bg=kit.PANEL,fg=kit.FG,activebackground=kit.PANEL,
                           activeforeground=kit.FG,selectcolor=kit.ELEVATED,font=('Segoe UI',10)).pack(side='left',padx=6)
        self.fallback=self._value_field(steps,'Pasta padrão',rs.get('fallback_folder','Outros'))
        kit.label(self.body,'REGRAS DE CLASSIFICAÇÃO',10,kit.CYAN,'bold').pack(anchor='w',pady=(20,5))
        kit.label(self.body,'Use vírgulas nas listas de extensões, palavras e origens. As regras superiores têm prioridade.',10,kit.MUTED).pack(anchor='w',pady=(0,8))
        self.rows_holder=tk.Frame(self.body,bg=kit.BG);self.rows_holder.pack(fill='x')
        self._render_rows()
        buttons=tk.Frame(self.body,bg=kit.BG);buttons.pack(fill='x',pady=(10,6))
        kit.pill(buttons,'+ Adicionar regra',self.add_rule,'primary').pack(side='left')
        kit.label(self.body,'EXCLUSÕES  ·  uma máscara por linha',10,kit.CYAN,'bold').pack(anchor='w',pady=(17,6))
        self.exclusions=tk.Text(self.body,height=5,bg=kit.ELEVATED,fg=kit.FG,insertbackground=kit.CYAN,
                        relief='flat',font=('Consolas',10),padx=12,pady=9)
        self.exclusions.pack(fill='x')
        self.exclusions.insert('1.0','\n'.join(root.get('exclusions',[])))
        kit.label(self.body,'* As regras e exclusões são validadas pelo mesmo motor determinístico do Watcher.',9,kit.MUTED).pack(anchor='w',pady=(8,30))

    def _value_field(self,parent,text,initial):
        kit.label(parent,text,10,kit.MUTED,'bold',bg=parent.cget('bg')).pack(anchor='w',pady=(3,6))
        widget,var,entry=kit.field(parent,initial=initial)
        widget.pack(fill='x');return var

    def _choice(self,parent,title,var,values):
        holder=tk.Frame(parent,bg=kit.PANEL)
        kit.label(holder,title,10,kit.MUTED,bg=kit.PANEL).pack(anchor='w',pady=(0,4))
        menu=tk.OptionMenu(holder,var,*values)
        menu.configure(bg=kit.ELEVATED,fg=kit.FG,activebackground='#303C58',activeforeground=kit.FG,
                       relief='flat',bd=0,highlightthickness=0,font=('Segoe UI',10),width=14)
        menu['menu'].configure(bg=kit.ELEVATED,fg=kit.FG,activebackground=kit.BLUE,activeforeground='#080B12')
        menu.pack(fill='x');return holder

    def _render_rows(self):
        for w in self.rows_holder.winfo_children():w.destroy()
        self.rows=[]
        for pos,r in enumerate(self.rules):
            frame=tk.Frame(self.rows_holder,bg=kit.PANEL,padx=9,pady=8)
            frame.pack(fill='x',pady=3)
            row=tk.Frame(frame,bg=kit.PANEL);row.pack(fill='x')
            kit.label(row,f'{pos+1:02}',10,kit.SUBTLE,bg=kit.PANEL).pack(side='left',padx=(0,7))
            var_kind=tk.StringVar(value=r.get('kind','type'))
            var_target=tk.StringVar(value=r.get('target','Outros'))
            var_data=tk.StringVar(value=rule_values(r))
            var_on=tk.BooleanVar(value=r.get('enabled',True))
            kind=tk.OptionMenu(row,var_kind,*KINDS)
            kind.configure(bg=kit.ELEVATED,fg=kit.FG,relief='flat',bd=0,highlightthickness=0,
                           activebackground=kit.BLUE,activeforeground='#071126',font=('Segoe UI',9),width=9)
            kind['menu'].configure(bg=kit.ELEVATED,fg=kit.FG)
            kind.pack(side='left',padx=5)
            for v,width in ((var_target,16),(var_data,39)):
                inp=tk.Entry(row,textvariable=v,bg=kit.ELEVATED,fg=kit.FG,insertbackground=kit.CYAN,
                             relief='flat',bd=0,font=('Segoe UI',10),width=width)
                inp.pack(side='left',padx=5,ipady=9,ipadx=5,fill='x',expand=(v is var_data))
            tk.Checkbutton(row,variable=var_on,bg=kit.PANEL,activebackground=kit.PANEL,selectcolor=kit.ELEVATED).pack(side='left',padx=5)
            kit.pill(row,'↑',lambda i=pos:self._move(i,-1),compact=True,width=33).pack(side='left',padx=1)
            kit.pill(row,'↓',lambda i=pos:self._move(i,1),compact=True,width=33).pack(side='left',padx=1)
            kit.pill(row,'×',lambda i=pos:self._remove(i),'danger',width=33,compact=True).pack(side='left',padx=1)
            self.rows.append((r['id'],var_kind,var_target,var_data,var_on))

    def _collect(self):
        return [{'id':rid,'kind':kind.get(),'target':target.get(),'values':values.get(),'enabled':enabled.get()}
                for rid,kind,target,values,enabled in self.rows]

    def _sync(self):
        edits=self._collect()
        old={r['id']:r for r in self.rules}
        self.rules=[]
        for e in edits:
            r=old.get(e['id'],{'id':e['id']})
            try:
                rs=apply_rows({'rules':[r]},[e],[])
                self.rules.append(rs['rules'][0])
            except (ValueError,KeyError):
                self.rules.append(dict(r,kind=e['kind'],target=e['target'],extensions=e['values'].split(',')))

    def add_rule(self):
        self._sync()
        self.rules.append({'id':'custom-'+uuid.uuid4().hex[:8],'kind':'type','target':'Nova categoria','extensions':['.ext'],'enabled':True})
        self._render_rows()

    def _remove(self,i):
        self._sync();self.rules.pop(i);self._render_rows()

    def _move(self,i,d):
        self._sync();j=i+d
        if 0<=j<len(self.rules):self.rules[i],self.rules[j]=self.rules[j],self.rules[i]
        self._render_rows()

    def _payload(self):
        r=copy.deepcopy(self.original)
        r['name']=self.name.get().strip();r['mode']=self.mode.get()
        r['recursive']=self.recursive.get();r['conflict_policy']=self.collision.get()
        r['exclusions']=[x.strip() for x in self.exclusions.get('1.0','end').splitlines() if x.strip()]
        r['output_path']=self.output.get().strip() or None
        existing=r.get('ruleset',{})
        # Existing order takes precedence, then newly selected steps.
        requested=[k for k in ('type','keyword','date','size','source') if self.steps[k].get()]
        order=[k for k in existing.get('path_steps',[]) if k in requested]
        order.extend(k for k in requested if k not in order)
        r['ruleset']=apply_rows(existing,self._collect(),order,self.fallback.get())
        r['enabled']=self.enabled.get()
        if r['mode']=='ORGANIZE':
            if not r['output_path']:r['output_path']=str(Path(r['path'])/'_LEIA_Organizado')
            modified=(r['ruleset']!=self.original.get('ruleset',{}) or r['mode']!=self.original['mode']
                     or r['exclusions']!=self.original.get('exclusions') or r['output_path']!=self.original.get('output_path')
                     or r['conflict_policy']!=self.original.get('conflict_policy'))
            if modified and self.original.get('enabled'):r['enabled']=False
        return r

    def save(self):
        try:
            payload=self._payload()
            from .config import validate
            current=copy.deepcopy(self.app.snapshot or {})
            cfg={'schema_version':1,'api':{'host':'127.0.0.1','port':8766},'roots':[payload]}
            # validate exact root and rules with domain checks before IPC
            validate(cfg)
        except Exception as exc:
            self.app.info('Validação não concluída',str(exc));return
        if payload['mode']=='ORGANIZE' and payload['enabled'] and not self.original.get('enabled'):
            self.app.info('Confirmação necessária','Salve a raiz DESATIVADA. Simule as regras e use o botão Ativar para autorizar movimentações.');return
        if self.original.get('enabled') and not payload.get('enabled') and payload['mode']=='ORGANIZE':
            message='A pasta ficará desativada. Execute Simular antes de reativá-la. Salvar mudanças?'
        else:message='As alterações serão persistidas localmente via IPC autenticado. Continuar?'
        if not kit.confirm(self.window,'Aplicar regras',message):return
        self.window.destroy();self.app._action('update_root',root=payload)

    def advanced(self):
        try:data=self._payload()
        except Exception:data=copy.deepcopy(self.original)
        w=kit.modal(self.window,'JSON avançado','Editor técnico completo. Mantém os mesmos requisitos de validação.',790,620)
        editor=tk.Text(w,bg=kit.ELEVATED,fg=kit.FG,insertbackground=kit.CYAN,relief='flat',font=('Consolas',10),wrap='none')
        editor.pack(fill='both',expand=True)
        editor.insert('1.0',json.dumps(data,ensure_ascii=False,indent=2))
        def save_json():
            try:
                obj=json.loads(editor.get('1.0','end'))
                if obj.get('id')!=self.original['id']:raise ValueError('O ID da pasta não pode mudar')
                from .config import validate
                validate({'schema_version':1,'api':{'host':'127.0.0.1'},'roots':[obj]})
            except Exception as exc:self.app.info('JSON inválido',str(exc));return
            if obj['mode']=='ORGANIZE' and obj.get('enabled') and obj!=self.original:
                obj['enabled']=False
            if not kit.confirm(w,'Confirmar JSON','A alteração validada será salva localmente. Pastas ORGANIZE alteradas serão desativadas.'):
                return
            w.destroy();self.window.destroy();self.app._action('update_root',root=obj)
        kit.pill(w,'Salvar JSON validado',save_json,'primary').pack(anchor='e',pady=8)


if __name__ == '__main__':
    main()
