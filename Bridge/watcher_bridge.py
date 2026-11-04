#!/usr/bin/env python3
"""LEIA Watcher 4 WinUI authenticated stdio adapter.

This process is launched via the user's existing Watcher V3 Python runtime.
It never exposes tokens, never listens on TCP, and does not move files directly.
Each JSON request is forwarded to the authenticated existing admin API.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

# Strict command allowlist; the caller cannot ask for secrets or arbitrary Python.
READ = frozenset({'ping', 'status', 'ui_snapshot', 'ui_list', 'roots', 'preview', 'job'})
WRITE = frozenset({'add_root', 'update_root', 'remove_root', 'activate', 'pause', 'resume', 'scan', 'undo', 'export', 'backup'})
SPECIAL = frozenset({'ensure_core', 'rules_validate', 'rules_apply', 'ui_files_origin'})
ALLOW = READ | WRITE | SPECIAL


def safe_request(command, args):
    if command not in ALLOW:
        raise ValueError('Comando não autorizado pela ponte local')
    if not isinstance(args, dict) or len(json.dumps(args)) > 150_000:
        raise ValueError('Parâmetros inválidos ou excessivos')
    from leia_watcher import admin
    if command == 'ensure_core':
        if args:
            raise ValueError('Parâmetros extras rejeitados')
        try:
            return admin.request('ping')
        except (ConnectionRefusedError, OSError, EOFError):
            executable = sys.executable
            # The core's SingleInstance class is the authoritative guard.
            launch = executable.replace('python.exe', 'pythonw.exe') if os.name == 'nt' else executable
            if not pathlib.Path(launch).is_file():
                launch = executable
            opts = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        close_fds=True, start_new_session=(os.name != 'nt'))
            if os.name == 'nt':
                opts['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            subprocess.Popen([launch, '-m', 'leia_watcher.main'], **opts)
            for _ in range(32):
                time.sleep(.25)
                try:
                    return admin.request('ping')
                except (OSError, EOFError, ConnectionRefusedError):
                    pass
            raise TimeoutError('Core local não respondeu; os arquivos não foram alterados')
    if command == 'ui_files_origin':
        origin = args.get('origin', 'Todos')
        if origin not in ('Todos', 'Atuais', 'Históricos'):
            raise ValueError('Filtro de origem inválido')
        page = int(args.get('page', 0)); limit = int(args.get('limit', 40))
        if not (0 <= page <= 100_000 and 1 <= limit <= 100):
            raise ValueError('Paginação inválida')
        filters = args.get('filters', {})
        if not isinstance(filters, dict):
            raise ValueError('Filtros inválidos')
        if origin == 'Todos':
            return admin.request('ui_list', entity='files', filters=filters, page=page, limit=limit)
        # Filter across the unified catalog BEFORE pagination, using the core's
        # existing read-only pages; never query SQLite or read secrets directly.
        selected=[]
        cursor=0
        while cursor < 100_000:
            batch=admin.request('ui_list', entity='files', filters=filters, page=cursor, limit=100)
            for item in batch.get('items', []):
                legacy = item.get('status') == 'LEGACY'
                if (origin == 'Históricos') == legacy:
                    selected.append(item)
            if not batch.get('has_more', False):
                break
            cursor += 1
        else:
            raise ValueError('Catálogo excede o limite seguro de paginação')
        return {'items': selected[page*limit:(page+1)*limit],
                'total': len(selected), 'page': page, 'limit': limit,
                'has_more': (page+1)*limit < len(selected)}
    if command in ('rules_validate', 'rules_apply'):
        from leia_watcher.ui_rules import apply_rows
        root_id = args.get('root_id')
        if not isinstance(root_id, str) or len(root_id) > 200:
            raise ValueError('Selecione uma pasta válida')
        roots = admin.request('roots')
        matches = [r for r in roots if r.get('id') == root_id]
        if len(matches) != 1:
            raise KeyError('Pasta inexistente')
        root = matches[0]
        rows = args.get('rows')
        steps = args.get('steps', ['type'])
        fallback = args.get('fallback', 'Outros')
        if not isinstance(rows, list) or len(rows) > 200 or not isinstance(steps, list):
            raise ValueError('Lista de regras inválida')
        ruleset = apply_rows(root['ruleset'], rows, steps, fallback)
        if command == 'rules_validate':
            return {'valid': True, 'rules': len(ruleset['rules'])}
        if not args.get('confirmed', False):
            raise PermissionError('Confirmação explícita obrigatória antes de gravar regras')
        # Native V3 transaction: backup SQLite, validation, persisted config and audit.
        root['ruleset'] = ruleset
        return admin.request('update_root', root=root)
    if command in ('remove_root','undo','activate') and not args.get('confirmed', False):
        raise PermissionError('Confirmação explícita necessária')
    if command == 'activate' and args.get('confirmation') != 'I_CONFIRM_FILE_MOVES':
        raise PermissionError('Confirmação de movimentação necessária')
    # 'confirmed' is local UI-only metadata, not a core config field.
    args = {k: v for k, v in args.items() if k != 'confirmed'}
    return admin.request(command, **args)


def serve(lines, output):
    for line in lines:
        try:
            if len(line)>200_000:
                raise ValueError('Requisição excessiva')
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError('Formato inválido')
            result=safe_request(message.get('command'), message.get('args') or {})
            response={'ok':True,'result':result}
        except (Exception,) as exc:
            # Do not disclose exception stacktraces or token paths to stdout.
            response={'ok':False,'error':f'{type(exc).__name__}: {str(exc)[:240]}'}
        output.write(json.dumps(response,ensure_ascii=False,default=str,separators=(',',':'))+'\n')
        output.flush()

if __name__ == '__main__':
    serve(sys.stdin,sys.stdout)
