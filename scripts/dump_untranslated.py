import os
import re

I18N = '/opt/tcrm/custom_addons/tcrm_propertio/i18n'
tr_po = os.path.join(I18N, 'tr.po')

with open(tr_po, 'r', encoding='utf-8') as f:
    lines = f.readlines()

untranslated = []
for i in range(len(lines)):
    if lines[i].startswith('msgid '):
        msgid = lines[i][6:].strip().strip('"')
        msgstr = lines[i+1][7:].strip().strip('"') if i+1 < len(lines) and lines[i+1].startswith('msgstr ') else ""
        if msgid and msgstr and msgid == msgstr:
            untranslated.append(msgid)

with open('/tmp/untranslated.txt', 'w', encoding='utf-8') as f:
    for u in untranslated:
        f.write(u + '\n')
print(f"Found {len(untranslated)} untranslated items.")
