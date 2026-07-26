# -*- coding: utf-8 -*-
"""Build tr.po / tr_TR.po for tcrm_marketing_hub (source is largely Turkish)."""
from __future__ import annotations

import os
import re
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I18N = os.path.dirname(os.path.abspath(__file__))

GLOSSARY = {
    "Marketing Hub": "Marketing Hub",
    "Marketing Administrator": "Marketing Yönetici (Admin)",
    "Marketing Yönetici (Admin)": "Marketing Yönetici (Admin)",
    "Marketing Yönetici": "Marketing Yönetici",
    "Marketing Kullanıcı": "Marketing Kullanıcı",
    "Marketing Manager": "Marketing Yönetici",
    "Marketing User": "Marketing Kullanıcı",
    "API URL": "API URL",
    "Platform": "Platform",
    "UTM": "UTM",
    "Form": "Form",
    "CRM": "CRM",
    "Meta Lead": "Meta Lead",
    "Lead Pivot": "Lead Pivot",
    "Lead Raporu": "Lead Raporu",
    "Hub Ana Sayfa": "Hub Ana Sayfa",
    "Yayınlama": "Yayınlama",
    "Yeni Gönderi": "Yeni Gönderi",
    "Gönderiler": "Gönderiler",
    "Gelen Kutusu": "Gelen Kutusu",
    "Meta Reklamlar": "Meta Reklamlar",
    "Meta Leadler": "Meta Leadler",
    "Analitik": "Analitik",
    "Sosyal Hesaplar": "Sosyal Hesaplar",
    "Senkronize Et": "Senkronize Et",
    "Ayarlar": "Ayarlar",
    "Kaynak Bilgileri": "Kaynak Bilgileri",
    "Reklam Kreatifi": "Reklam Kreatifi",
}


def extract_strings() -> OrderedDict:
    found: OrderedDict[str, str] = OrderedDict()

    def add(s: str, src: str):
        s = (s or "").strip()
        if not s or len(s) < 2 or len(s) > 180:
            return
        if s.startswith(("fa-", "%", "{", "/", "#", ".")) or s.isdigit():
            return
        if re.fullmatch(r"[a-z0-9_.]+", s):
            return
        if s not in found:
            found[s] = src

    for dirpath, _, files in os.walk(ROOT):
        if any(x in dirpath for x in ("i18n", "__pycache__", "node_modules")):
            continue
        for fname in files:
            if not fname.endswith((".py", ".xml", ".js")):
                continue
            path = os.path.join(dirpath, fname)
            rel = os.path.relpath(path, ROOT)
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if fname.endswith(".py"):
                for m in re.finditer(r"""(?:string|_)\(\s*['"]([^'"]+)['"]""", text):
                    add(m.group(1), rel)
                for m in re.finditer(r"""help\s*=\s*['"]([^'"]+)['"]""", text):
                    add(m.group(1), rel)
            else:
                for m in re.finditer(
                    r"""(?:string|title|placeholder|confirm|help|alt)\s*=\s*['"]([^'"]+)['"]""",
                    text,
                ):
                    add(m.group(1), rel)
                for m in re.finditer(r"""<menuitem[^>]*\sname=['"]([^'"]+)['"]""", text):
                    add(m.group(1), rel)
                for m in re.finditer(r"""<field name=['"]name['"]>([^<]+)</field>""", text):
                    add(m.group(1), rel)
                for m in re.finditer(
                    r""">([A-ZÇĞİÖŞÜa-zçğıöşü][^<>{}]{0,80})</(?:button|span|label|a|strong|h[1-6]|th|small|dt)>""",
                    text,
                ):
                    add(m.group(1).replace("&amp;", "&").strip(), rel)
    for k in GLOSSARY:
        add(k, "glossary")
    return found


HEADER = """# Turkish (Turkey) translation for TCRM Marketing Hub.
# Copyright (C) TCRM
# This file is distributed under the same license as the tcrm_marketing_hub package.
#
msgid ""
msgstr ""
"Project-Id-Version: TCRM Marketing Hub 1.5\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: 2026-07-24 00:00+0000\\n"
"PO-Revision-Date: 2026-07-24 00:00+0000\\n"
"Last-Translator: TCRM <info@tcrm.com>\\n"
"Language-Team: Turkish\\n"
"Language: tr_TR\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=1; plural=0;\\n"

"""


def po_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def translate(msgid: str) -> str:
    if msgid in GLOSSARY:
        return GLOSSARY[msgid]
    # Source is already Turkish for most UI; keep identity mapping.
    return msgid


def build():
    strings = extract_strings()
    lines = [HEADER]
    mapped = 0
    for msgid, src in strings.items():
        tr = translate(msgid)
        if tr != msgid or msgid in GLOSSARY:
            mapped += 1
        lines.append("#. module: tcrm_marketing_hub\n")
        lines.append("#: %s\n" % src.replace("\\", "/"))
        lines.append('msgid "%s"\n' % po_escape(msgid))
        lines.append('msgstr "%s"\n' % po_escape(tr))
        lines.append("\n")
    body = "".join(lines)
    for name in ("tr.po", "tr_TR.po"):
        path = os.path.join(I18N, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        print("Wrote", path, "entries=", len(strings), "mapped=", mapped)


if __name__ == "__main__":
    build()
