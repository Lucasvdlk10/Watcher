#!/usr/bin/env python3
"""Converte TOKENS.json da LEIA para tokens QML. stdlib only."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
tokens=json.loads((root/'TOKENS.json').read_text(encoding='utf-8'))
lines=['pragma Singleton','import QtQuick 2.15','QtObject {']
for theme,values in tokens['color'].items():
    prefix={'dark':'dark','light':'light','highContrast':'highContrast'}[theme]
    for key,color in values.items():
        lines.append('    readonly property color '+prefix+key[0].upper()+key[1:]+': "'+color+'"')
lines.append('}')
p=Path(__file__).with_name('LeiaTokens.qml')
p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Gerado:',p)
