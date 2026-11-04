import leia_watcher.ui as ui
from leia_watcher.ui import App


def test_edit_root_retains_editor_instance(monkeypatch):
    created=[]
    class FakeEditor:
        def __init__(self,app,root):
            self.app=app;self.root=root;created.append(self)
    monkeypatch.setattr(ui,'RuleEditor',FakeEditor)
    app=App.__new__(App);app.roots=[{'id':'r1','name':'Downloads','ruleset':{}}]
    app.edit_root('r1')
    assert created and app.rule_editor is created[0]
