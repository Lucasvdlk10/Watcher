"""Obsidian Wave widget kit (stdlib Tk canvas, zero extra runtime dependencies).

Not ttk/Notebook/Treeview. Custom-drawn controls with keyboard focus and
single-page shell. Text inputs retain native accessibility and selection.
"""
import tkinter as tk

# LEIA V3 Dark Program · monochrome foundation; accents reserved for status/data.
BG='#090A0C'; SIDE='#101115'; PANEL='#17191D'; ELEVATED='#22252B'
BORDER='#30333B'; FG='#F4F5F6'; MUTED='#B0B5BF'; SUBTLE='#8D929D'
BLUE='#8AABEA'; PURPLE='#B3A7D9'; CYAN='#6ED3C5'
GREEN='#78C8A7'; GOLD='#E6BD75'; RED='#EE9299'



def label(parent,text='',size=11,fg=FG,weight='normal',bg=None,wrap=None,**kw):
    f=('Segoe UI',size,'bold' if weight=='bold' else 'normal')
    opts=dict(text=text,bg=bg or parent.cget('bg'),fg=fg,font=f,anchor='w',justify='left')
    if wrap:opts['wraplength']=wrap
    opts.update(kw)
    return tk.Label(parent,**opts)


def surface(parent,padx=18,pady=16,bg=PANEL):
    edge=tk.Frame(parent,bg=BORDER)
    inner=tk.Frame(edge,bg=bg,padx=padx,pady=pady)
    inner.pack(fill='both',expand=True,padx=1,pady=1)
    return edge,inner


def pill(parent,text,callback,kind='subtle',width=None,compact=False):
    palettes={'subtle':(ELEVATED,FG,BORDER),'primary':('#EBEDF0','#15171B','#EBEDF0'),
              'danger':('#322025',RED,'#6E4048'),'quiet':(parent.cget('bg'),MUTED,parent.cget('bg')),
              'success':('#202B2A',CYAN,'#31514C')}
    base,fg,edge=palettes.get(kind,palettes['subtle']);size=10 if compact else 11
    w=width or max(90,int(len(text)*6.5+33));h=32 if compact else 38
    c=tk.Canvas(parent,height=h,width=w,bg=parent.cget('bg'),highlightthickness=0,bd=0,takefocus=1,cursor='hand2')
    def draw(hover=False,focus=False):
        c.delete('all')
        col=base if not hover else ('#2B2F36' if kind=='subtle' else '#FFFFFF' if kind=='primary' else '#422B30')
        if focus:c.create_rectangle(1,1,w-1,h-1,outline=CYAN,width=1)
        rr(c,3,3,w-4,h-4,15 if not compact else 12,fill=col,outline=edge)
        c.create_text(w/2,h/2,text=text,font=('Segoe UI',size,'bold'),fill=fg)
    def on_key(e):
        if e.keysym in ('Return','space'):callback();return 'break'
    c.bind('<Button-1>',lambda e:callback())
    c.bind('<Return>',on_key);c.bind('<space>',on_key)
    c.bind('<Enter>',lambda e:draw(True))
    c.bind('<Leave>',lambda e:draw())
    c.bind('<FocusIn>',lambda e:draw(focus=True))
    c.bind('<FocusOut>',lambda e:draw())
    draw();return c


def rr(c,x1,y1,x2,y2,r,**opts):
    """Real rounded rectangle, without Tk spline overshoot/pointed ends."""
    r=min(float(r),(x2-x1)/2,(y2-y1)/2)
    fill=opts.get('fill',PANEL);outline=opts.get('outline')
    def layer(a,b,d,e,radius,color):
        if d<=a or e<=b:return
        c.create_rectangle(a+radius,b,d-radius,e,fill=color,width=0)
        c.create_rectangle(a,b+radius,d,e-radius,fill=color,width=0)
        for xx in (a,d-2*radius):
            for yy in (b,e-2*radius):
                c.create_oval(xx,yy,xx+2*radius,yy+2*radius,fill=color,width=0)
    if outline:layer(x1,y1,x2,y2,r,outline)
    layer(x1+1,y1+1,x2-1,y2-1,max(1,r-1),fill)



def field(parent,placeholder='',initial='',width=28):
    out=tk.Frame(parent,bg=BORDER)
    var=tk.StringVar(value=str(initial))
    e=tk.Entry(out,textvariable=var,relief='flat',bd=0,bg=ELEVATED,fg=FG,insertbackground=FG,
               font=('Segoe UI',11),width=width,highlightthickness=0)
    e.pack(fill='x',expand=True,padx=1,pady=7,ipadx=10,ipady=5)
    if placeholder:
        # True accessible label resides outside field; placeholder uses tooltip only.
        e.insert(0,initial)
    return out,var,e


def scroll(parent):
    outer=tk.Frame(parent,bg=BG)
    c=tk.Canvas(outer,bg=BG,highlightthickness=0,bd=0)
    bar=tk.Scrollbar(outer,orient='vertical',command=c.yview,bg=PANEL,troughcolor=BG,
                     activebackground=ELEVATED,relief='flat',bd=0,width=10)
    inner=tk.Frame(c,bg=BG)
    win=c.create_window((0,0),window=inner,anchor='nw')
    inner.bind('<Configure>',lambda e:c.configure(scrollregion=c.bbox('all')))
    c.bind('<Configure>',lambda e:c.itemconfigure(win,width=e.width))
    c.configure(yscrollcommand=bar.set)
    bar.pack(side='right',fill='y');c.pack(side='left',fill='both',expand=True)
    def wheel(e):
        if c.winfo_exists():c.yview_scroll(int(-1*(e.delta/120)), 'units')
    def enter(_): c.bind_all('<MouseWheel>',wheel)
    def leave(_): c.unbind_all('<MouseWheel>')
    c.bind('<Enter>',enter);c.bind('<Leave>',leave)
    return outer,inner


def divider(parent):tk.Frame(parent,bg=BORDER,height=1).pack(fill='x',pady=10)


def empty(parent,title,details,action=None,callback=None):
    outer=tk.Frame(parent,bg=PANEL,pady=45)
    label(outer,'◌',28,CYAN,bg=PANEL).pack()
    label(outer,title,15,FG,'bold',bg=PANEL).pack(pady=(10,4))
    label(outer,details,10,MUTED,bg=PANEL,wrap=500,justify='center',anchor='center').pack()
    if action and callback:pill(outer,action,callback,'primary').pack(pady=(15,0))
    return outer


def modal(parent,title,description='',width=560,height=340):
    win=tk.Toplevel(parent,bg=SIDE)
    win.title(title);win.minsize(min(width,470),min(height,280))
    # Explicitly center and raise dialogs. Windows can otherwise create a
    # transient Toplevel behind its parent, making a working button look dead.
    parent.update_idletasks()
    px=parent.winfo_rootx();py=parent.winfo_rooty()
    pw=max(parent.winfo_width(),width);ph=max(parent.winfo_height(),height)
    x=max(0,px+(pw-width)//2);y=max(0,py+(ph-height)//2)
    win.geometry(f'{width}x{height}+{x}+{y}')
    win.transient(parent);win.lift();win.grab_set();win.after_idle(win.focus_force)
    win.configure(bg=SIDE,padx=24,pady=24)
    label(win,title,19,FG,'bold',bg=SIDE).pack(anchor='w',pady=(0,8))
    if description: label(win,description,10,MUTED,bg=SIDE,wrap=width-60).pack(fill='x',pady=(0,14))
    win.bind('<Escape>',lambda e:win.destroy())
    return win


def confirm(parent,title,details,critical=False,word=None):
    w=modal(parent,title,details,550,300 if not word else 360)
    result={'ok':False}; inputvar=None
    if word:
        label(w,f'Digite {word} para confirmar:',11,GOLD,bg=SIDE).pack(anchor='w',pady=8)
        box,inputvar,e=field(w);box.pack(fill='x');e.focus_set()
    actions=tk.Frame(w,bg=SIDE);actions.pack(side='bottom',fill='x',pady=4)
    def accept():
        if word and inputvar.get()!=word:return
        result['ok']=True;w.destroy()
    pill(actions,'Cancelar',w.destroy).pack(side='right',padx=5)
    pill(actions,'Confirmar',accept,'danger' if critical else 'primary').pack(side='right',padx=5)
    w.wait_window();return result['ok']
