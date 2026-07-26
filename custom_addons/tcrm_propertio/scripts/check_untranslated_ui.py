#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Heuristic scanner for English UI leftovers in Propertio + Marketing Hub.

Scans XML/JS under tcrm_propertio and tcrm_marketing_hub for common English
UI phrases in user-facing attributes / OWL text. Prints candidates for review.

NOTE: Technical IDs, field names, external IDs, API keys, URLs, chart type
tokens (bar/line/pie), and framework names must be reviewed manually — this
script only surfaces candidates, it does not prove a string is user-facing.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

# Avoid Windows console UnicodeEncodeError on Turkish characters.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_MODULES = ("tcrm_propertio", "tcrm_marketing_hub")

# Multi-word / distinctive English UI phrases (fewer false positives than bare "All"/"To").
ENGLISH_UI_PHRASES = (
    r"Reports?\s+Center",
    r"Search\s+reports",
    r"Loading\s+report",
    r"New\s+Leads?",
    r"Qualified\s+Leads?",
    r"My\s+Leads?",
    r"Creation\s+Date",
    r"Sales\s+Team",
    r"Salesperson",
    r"Unassigned",
    r"Opportunities",
    r"Target\s+Property",
    r"Property\s+(Project|Unit|Contracts)",
    r"Project\s+Name",
    r"Amenities\s*&\s*Features",
    r"Standard\s+Amenities",
    r"Available\s+Upgrades",
    r"Features\s*&\s*Upgrades",
    r"Financial\s+Stats",
    r"Total\s+GDV",
    r"Create\s+Reminder",
    r"Chart\s+Group",
    r"Chart\s+Metric",
    r"No\s+chart\s+data",
    r"No\s+data\s+found",
    r"Choose\s+a\s+Group",
    r"Report\s+preset",
    r"\bInventory\b",
    r"\bEnvanter\b",
    r"\bAccrual\b",
    r"\bContracts\b",
    r"Lead\s*/\s*Opportunity",
)

# Single tokens only when clearly UI-labelled (string=/placeholder=/_t / button text).
ENGLISH_UI_TOKENS = (
    r"Search",
    r"Category",
    r"Save",
    r"Run",
    r"List",
    r"Groups",
    r"Chart",
    r"Loading",
    r"From",
    r"To",
    r"None",
    r"Apply",
    r"Customer",
    r"Campaign",
    r"Medium",
    r"Source",
    r"Stage",
    r"Blocks",
    r"Property",
    r"Cash",
    r"All",
    r"Tag",
    r"Type",
    r"Won",
    r"Lost",
    r"Archived",
    r"Project",
)

SKIP_DIR_PARTS = (
    "/i18n",
    "/__pycache__",
    "/node_modules",
    "/static/description",
    "/.git",
    "/scripts",
    "/tests",
    "/security",
    "/data",
)

UI_ATTR_RE = re.compile(
    r"""(?:string|title|placeholder|confirm|help|alt)\s*=\s*['"]([^'"]+)['"]"""
)
OWL_TEXT_RE = re.compile(
    r""">\s*([^<>{}]{2,100}?)\s*</(?:button|span|label|a|strong|h[1-6]|th|small|option)>"""
)
T_RE = re.compile(r"""_t\(\s*['"]([^'"]+)['"]\s*\)""")
FALLBACK_RE = re.compile(r"""\|\|\s*['"]([^'"]{2,80})['"]""")
PHRASE_RE = re.compile("|".join("(?:%s)" % w for w in ENGLISH_UI_PHRASES), re.IGNORECASE)
TOKEN_RE = re.compile(
    r"\b(?:" + "|".join(ENGLISH_UI_TOKENS) + r")\b",
    re.IGNORECASE,
)


def should_skip_dir(path: str) -> bool:
    norm = "/" + path.replace("\\", "/")
    return any(part in norm for part in SKIP_DIR_PARTS)


def extract_ui_strings(line: str):
    for regex in (UI_ATTR_RE, OWL_TEXT_RE, T_RE, FALLBACK_RE):
        for m in regex.finditer(line):
            yield m.group(1).strip()


def is_candidate(text: str) -> str | None:
    if not text or text.startswith(("fa-", "%", "{", "/", "#", ".")):
        return None
    # Skip technical snake/dot identifiers
    if re.fullmatch(r"[a-z0-9_./:-]+", text):
        return None
    m = PHRASE_RE.search(text)
    if m:
        return m.group(0)
    m = TOKEN_RE.search(text)
    if m:
        return m.group(0)
    return None


def scan_module(module_path: str):
    hits = []
    seen = set()
    for dirpath, dirnames, files in os.walk(module_path):
        dirnames[:] = [d for d in dirnames if not should_skip_dir(os.path.join(dirpath, d))]
        if should_skip_dir(dirpath):
            continue
        for fname in files:
            if not fname.endswith((".xml", ".js")):
                continue
            path = os.path.join(dirpath, fname)
            rel = os.path.relpath(path, ADDON_ROOT).replace("\\", "/")
            try:
                lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
            except OSError:
                continue
            for lineno, line in enumerate(lines, start=1):
                stripped = line.strip()
                if stripped.startswith(("<!--", "//", "*", "/*")):
                    continue
                for candidate in extract_ui_strings(line):
                    match = is_candidate(candidate)
                    if not match:
                        continue
                    key = (rel, lineno, candidate)
                    if key in seen:
                        continue
                    seen.add(key)
                    hits.append((rel, lineno, match, candidate))
    return hits


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "modules",
        nargs="*",
        default=list(DEFAULT_MODULES),
        help="Module folder names under custom_addons (default: propertio + marketing_hub)",
    )
    args = parser.parse_args(argv)

    print(
        "Heuristic English UI scan — review technical IDs manually.\n"
        "Modules: %s\n" % ", ".join(args.modules)
    )
    total = 0
    for module in args.modules:
        path = os.path.join(ADDON_ROOT, module)
        if not os.path.isdir(path):
            print("SKIP missing module:", path)
            continue
        hits = scan_module(path)
        total += len(hits)
        print("=== %s (%s candidates) ===" % (module, len(hits)))
        for rel, lineno, match, candidate in hits:
            print("%s:%s: [%s] %s" % (rel, lineno, match, candidate))
        print()
    print("Total candidates: %s" % total)
    print(
        "\nReminder: technical model/field/external IDs and URLs are out of scope; "
        "verify each candidate before translating."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
