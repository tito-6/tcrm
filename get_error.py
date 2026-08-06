import os, io

with io.open('d:/tcrm/tcrm_data/tcrm.log', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()[-200:]
with io.open('d:/tcrm/error.log', 'w', encoding='utf-8') as f:
    f.writelines(lines)
