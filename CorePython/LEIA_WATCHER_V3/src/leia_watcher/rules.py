"""Pure deterministic rules engine: no LLM, no I/O side effects."""
from dataclasses import dataclass
from pathlib import Path
import datetime as dt
import fnmatch
import re
import unicodedata

BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{n}' for p in ('COM','LPT') for n in range(1, 10)}
TEMP = ('.part','.crdownload','.download','.tmp','.partial','.!qB')
STEPS = {'type','date','keyword','size','source'}


def component(value):
    if not isinstance(value, str) or not value or value in ('.','..') or value.rstrip(' .') != value:
        raise ValueError('ERR_PATH_UNSAFE: unsafe folder name')
    value = unicodedata.normalize('NFC',value)
    if BAD.search(value) or value.partition('.')[0].upper() in RESERVED or len(value) > 100:
        raise ValueError('ERR_PATH_UNSAFE: invalid Windows component')
    return value


def validate_rules(s):
    if not isinstance(s,dict): raise ValueError('Invalid ruleset')
    steps = s.get('path_steps',[])
    if not isinstance(steps,list) or any(x not in STEPS for x in steps) or len(set(steps)) != len(steps) or len(steps)>5:
        raise ValueError('Invalid path_steps')
    if s.get('creation_fallback', 'MTIME') not in ('MTIME','SKIP'): raise ValueError('Invalid creation fallback')
    ids=set()
    for r in s.get('rules', []):
        if r.get('id') in ids or not isinstance(r.get('id'),str): raise ValueError('Duplicate rule ID')
        ids.add(r['id'])
        if r.get('kind') not in ('type','keyword','source','date','size'): raise ValueError('Unknown rule kind')
        if r.get('kind') == 'type' and any(not str(x).startswith('.') for x in r.get('extensions',[])): raise ValueError('Invalid extension')
        if r.get('kind') in ('keyword','type','source'): component(r.get('target','Unclassified'))
        if r.get('kind') == 'date' and r.get('pattern','YYYY/MM') != 'YYYY/MM': raise ValueError('Unsupported date pattern')
        if r.get('kind') == 'keyword' and r.get('mode','contains') not in ('contains','prefix','suffix','exact'): raise ValueError('Invalid match mode')
    bands=s.get('size_bands',[])
    if len(bands)>5: raise ValueError('Maximum five size bands')
    ranges=[]
    for b in bands:
        component(b['label']); lo=b['min_bytes']; hi=b.get('max_bytes')
        if not isinstance(lo,int) or lo<0 or (hi is not None and (not isinstance(hi,int) or hi <= lo)): raise ValueError('Invalid size band')
        ranges.append((lo,float('inf') if hi is None else hi))
    for i,(a,b) in enumerate(ranges):
        for c,d in ranges[i+1:]:
            if max(a,c)<min(b,d): raise ValueError('Overlapping size bands')
    if s.get('fallback_folder') is not None:component(s['fallback_folder'])


def extension(name):
    suffixes = Path(name).suffixes
    return ''.join(suffixes[-2:]).lower() if len(suffixes) >= 2 and suffixes[-2].lower() in ('.tar',) else (suffixes[-1].lower() if suffixes else '')


def excluded(path, root):
    """Exclusions work equally for top-level and nested files."""
    p = Path(path)
    rel = p.relative_to(Path(root['path']))
    q = rel.as_posix()
    if any(part in ('.git','node_modules','__pycache__','$RECYCLE.BIN','System Volume Information') for part in rel.parts):return True
    if p.name.lower().endswith(tuple(x.lower() for x in TEMP)) or p.name.startswith('~$'):return True
    output = root.get('output_path') or (str(Path(root['path']) / '_LEIA_Organizado') if root['mode']=='ORGANIZE' else None)
    if output and Path(output).resolve() != Path(root['path']).resolve():
        from .config import inside
        if inside(output,p):return True
    for glob in root.get('exclusions',[]):
        gl=glob.replace('\\','/')
        if fnmatch.fnmatch(q,gl) or fnmatch.fnmatch(p.name,gl) or (gl.startswith('**/') and fnmatch.fnmatch(q,gl[3:])):
            return True
        if gl.endswith('/**') and (q == gl[:-3] or q.startswith(gl[:-2])):return True
    return False


def normalized(s, case=True, accents=True):
    s=unicodedata.normalize('NFC',s)
    if accents:s=''.join(x for x in unicodedata.normalize('NFKD',s) if not unicodedata.combining(x))
    return s.casefold() if case else s


def matching(r, path, stat, origin):
    k=r['kind']; name=path.name
    if k=='type':return any(name.lower().endswith(str(x).lower()) for x in r.get('extensions',[]))
    if k=='keyword':
        text=normalized(name,r.get('normalize_case',True),r.get('normalize_accents',True))
        for kw in r.get('keywords',[]):
            w=normalized(str(kw),r.get('normalize_case',True),r.get('normalize_accents',True))
            if not w:continue
            mode=r.get('mode','contains')
            if {'contains':lambda:w in text,'prefix':lambda:text.startswith(w),'suffix':lambda:text.endswith(w),'exact':lambda:text==w}[mode]():return True
        return False
    if k=='source':return origin['category'] in r.get('categories',[])
    if k=='size':return r.get('min_bytes',0)<=stat.st_size and (r.get('max_bytes') is None or stat.st_size<r['max_bytes'])
    if k=='date':return True
    return False


def origin_evidence(path):
    """A Mark-of-the-Web label says internet zone, never implies browser or email."""
    if __import__('os').name == 'nt':
        try:
            with open(str(path)+':Zone.Identifier',encoding='utf-8') as fh:
                t=fh.read(2048)
            if 'ZoneId=3' in t or 'ZoneId=4' in t:
                return {'category':'WEB','source':'zone_identifier','confidence':'heuristic','evidence':'Windows internet zone (app unknown)'}
        except (OSError, UnicodeError):pass
    return {'category':'UNKNOWN','source':'none','confidence':'unknown','evidence':''}


@dataclass(frozen=True)
class Decision:
    action:str
    target:str|None
    reason:str
    rule_ids:tuple=()
    evidence:tuple=()


def evaluate(root,path,st,origin=None):
    path=Path(path)
    if excluded(path,root):return Decision('SKIP',None,'EXCLUDED')
    if root['mode']=='TRACK_ONLY':return Decision('INDEX',None,'TRACK_ONLY')
    rs=root.get('ruleset',{}); origin=origin or origin_evidence(path)
    chunks=[]; chosen=[]; evidence=[]
    for kind in rs.get('path_steps',[]):
        if kind=='date':
            created=getattr(st,'st_birthtime',None)
            if created is None and __import__('os').name=='nt':created=st.st_ctime
            if created is None:
                if rs.get('creation_fallback','MTIME')=='SKIP': return Decision('SKIP',None,'SKIPPED_UNCERTAIN')
                created=st.st_mtime; evidence.append('creation_fallback=MTIME')
            date=dt.datetime.fromtimestamp(created).astimezone()
            chunks.extend((str(date.year),f'{date.month:02d}'))
            continue
        matches=[r for r in rs.get('rules',[]) if r.get('kind')==kind and r.get('enabled',True) and matching(r,path,st,origin)]
        matches.sort(key=lambda x:(-int(x.get('priority',0)),x['id']))
        if matches:
            r=matches[0]; chosen.append(r['id']); chunks.append(component(r.get('target',r.get('label','Outros'))));continue
        if kind=='size':
            for b in sorted(rs.get('size_bands',[]),key=lambda a:a['min_bytes']):
                if b['min_bytes']<=st.st_size and (b.get('max_bytes') is None or st.st_size < b['max_bytes']):
                    chunks.append(component(b['label']));chosen.append('size:'+b['label']);break
        if kind=='source' and not matches and origin['category']=='UNKNOWN':
            evidence.append('origin=UNKNOWN')
    if not chosen and rs.get('fallback_folder'):
        chunks.insert(0,component(rs['fallback_folder']))
    elif not chosen and 'date' not in rs.get('path_steps',[]):return Decision('SKIP',None,'SKIP_NO_RULE')
    if len(chunks)>6 or len('/'.join(chunks))>240:return Decision('SKIP',None,'ERR_PATH_UNSAFE')
    target=Path(root.get('output_path') or Path(root['path']) / '_LEIA_Organizado').joinpath(*chunks,path.name)
    return Decision('MOVE',str(target),'RULE_MATCH',tuple(chosen),tuple(evidence))
