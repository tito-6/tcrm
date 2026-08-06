# -*- coding: utf-8 -*-
"""Deprecated launcher — use _fix_propertio_tr_menus.py via exec(open...).

Do NOT pipe Turkish source through PowerShell Get-Content; it turns ö/ş/ı into ?.
"""
exec(open(r"d:\tcrm\scripts\_fix_propertio_tr_menus.py", encoding="utf-8").read())
