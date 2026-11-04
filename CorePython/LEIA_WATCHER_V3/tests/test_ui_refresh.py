from leia_watcher.ui import App


class FakeWidget:
    def __init__(self): self.calls=[]
    def configure(self, **kwargs): self.calls.append(kwargs)


class FakeRoot:
    def __init__(self): self.scheduled=[]
    def state(self): return 'normal'
    def after(self, delay, callback): self.scheduled.append((delay, callback))


def test_periodic_refresh_does_not_rebuild_visible_page():
    app=App.__new__(App)
    app.closed=False;app.working=False;app.root=FakeRoot();calls=[]
    app.refresh=lambda *,render=True:calls.append(render)
    app._periodic()
    assert calls==[False]
    assert app.root.scheduled[0][0]==9000


def test_background_receive_updates_state_without_showing_page():
    app=App.__new__(App)
    app.state_label=FakeWidget();app.notice=FakeWidget();app.page='overview';shown=[]
    app.show=lambda page:shown.append(page)
    snapshot={'database':'ok'};roots=[]
    app._receive_all((snapshot,roots),render=False)
    assert app.connected is True
    assert app.snapshot is snapshot and app.roots is roots
    assert shown==[]


def test_manual_receive_renders_current_page():
    app=App.__new__(App)
    app.state_label=FakeWidget();app.notice=FakeWidget();app.page='overview';shown=[]
    app.show=lambda page:shown.append(page)
    app._receive_all(({},[]),render=True)
    assert shown==['overview']
