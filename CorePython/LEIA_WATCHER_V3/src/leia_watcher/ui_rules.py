"""Deterministic transformations for the visual rule editor."""
import copy
from .rules import validate_rules

KINDS=('type','keyword','source','date','size')


def split_csv(text):return [x.strip() for x in text.split(',') if x.strip()]


def rule_values(rule):
    kind=rule.get('kind','type')
    if kind=='type':return ', '.join(rule.get('extensions',[]))
    if kind=='keyword':return ', '.join(rule.get('keywords',[]))
    if kind=='source':return ', '.join(rule.get('categories',[]))
    if kind=='size':return str(rule.get('min_bytes',0))+', '+('' if rule.get('max_bytes') is None else str(rule['max_bytes']))
    return rule.get('pattern','YYYY/MM')


def apply_rows(ruleset, edits, steps, fallback='Outros'):
    result=copy.deepcopy(ruleset)
    result['path_steps']=[s for s in steps if s in KINDS]
    result['fallback_folder']=fallback
    previous={r['id']:r for r in ruleset.get('rules',[])}
    new=[]
    ids=set()
    for i,row in enumerate(edits):
        kind=row['kind'];rid=row['id'];target=row.get('target','Outros').strip();raw=row.get('values','')
        if kind not in KINDS or rid in ids or not rid:raise ValueError('Regra inválida ou duplicada')
        ids.add(rid)
        r=copy.deepcopy(previous.get(rid,{}));r.update({'id':rid,'kind':kind,'priority':len(edits)-i,'enabled':bool(row.get('enabled',True))})
        for k in ('extensions','keywords','categories','min_bytes','max_bytes','pattern'):r.pop(k,None)
        if kind in ('type','keyword','source'):r['target']=target
        if kind=='type':
            r['extensions']=[x.lower() for x in split_csv(raw)]
        elif kind=='keyword':r['keywords']=split_csv(raw)
        elif kind=='source':r['categories']=split_csv(raw)
        elif kind=='size':
            parts=raw.split(',');r['min_bytes']=int(parts[0].strip());r['max_bytes']=int(parts[1].strip()) if len(parts)>1 and parts[1].strip() else None
            r['target']=target
        else:r['pattern']='YYYY/MM'
        new.append(r)
    result['rules']=new
    validate_rules(result)
    return result
