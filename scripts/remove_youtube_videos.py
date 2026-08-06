#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remove YouTube / Odoo promo video embeds from a TCRM database.

Run on the VPS (or any env with TCRM ORM):

  sudo -u tcrm env PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python \\
    /opt/tcrm/scripts/remove_youtube_videos.py -c /opt/tcrm/tcrm.prod.conf -d DBNAME

Or via tcrm shell:

  exec(open('/opt/tcrm/scripts/remove_youtube_videos.py').read())
  # then: run(env)

What it cleans:
  * ir.ui.view arch_db (iframe/embed/a tags pointing at youtube/youtu.be)
  * mail.template body_html
  * website pages / qweb views containing youtube embeds
  * ir.config_parameter keys that store promo video URLs (when present)
"""
from __future__ import annotations

import argparse
import logging
import re
import sys

from lxml import etree, html

_logger = logging.getLogger("remove_youtube_videos")

YOUTUBE_RE = re.compile(
    r"(youtube\.com|youtu\.be|youtube-nocookie\.com)",
    re.IGNORECASE,
)

IFRAME_SRC_RE = re.compile(
    r"""<iframe\b[^>]*\b(?:src|data-src)\s*=\s*["'][^"']*(?:youtube\.com|youtu\.be|youtube-nocookie\.com)[^"']*["'][^>]*>\s*</iframe>""",
    re.IGNORECASE | re.DOTALL,
)
ANCHOR_YT_RE = re.compile(
    r"""<a\b[^>]*\bhref\s*=\s*["'][^"']*(?:youtube\.com|youtu\.be)[^"']*["'][^>]*>.*?</a>""",
    re.IGNORECASE | re.DOTALL,
)
EMBED_DIV_RE = re.compile(
    r"""<div\b[^>]*class=["'][^"']*o_video_embed[^"']*["'][^>]*>.*?</div>""",
    re.IGNORECASE | re.DOTALL,
)


def _strip_youtube_html(content: str) -> tuple[str, bool]:
    if not content or not YOUTUBE_RE.search(content):
        return content, False
    cleaned = content
    for pattern in (IFRAME_SRC_RE, ANCHOR_YT_RE, EMBED_DIV_RE):
        cleaned = pattern.sub("", cleaned)
    # Also drop bare youtube URLs left as text nodes in simple cases.
    cleaned = re.sub(
        r"https?://(?:www\.)?(?:youtube\.com|youtu\.be|youtube-nocookie\.com)/\S+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned, cleaned != content


def _strip_youtube_xml_arch(arch: str) -> tuple[str, bool]:
    if not arch or not YOUTUBE_RE.search(arch):
        return arch, False
    try:
        root = etree.fromstring(arch.encode("utf-8") if isinstance(arch, str) else arch)
    except etree.XMLSyntaxError:
        # Fall back to regex HTML strip for non-strict arches.
        return _strip_youtube_html(arch)

    changed = False
    # Remove iframes / embeds / anchors pointing at YouTube.
    for el in list(root.xpath(
        "//iframe[contains(@src,'youtube') or contains(@src,'youtu.be') "
        "or contains(@data-src,'youtube') or contains(@data-src,'youtu.be')]"
        "|//embed[contains(@src,'youtube') or contains(@src,'youtu.be')]"
        "|//a[contains(@href,'youtube') or contains(@href,'youtu.be')]"
        "|//*[contains(@class,'o_video_embed')]"
    )):
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)
            changed = True

    if not changed:
        return arch, False
    return etree.tostring(root, encoding="unicode"), True


def run(env, dry_run=False):
    """ORM entrypoint — call from tcrm shell as run(env)."""
    stats = {
        "views": 0,
        "mail_templates": 0,
        "params": 0,
    }

    View = env["ir.ui.view"].sudo()
    views = View.search([("arch_db", "ilike", "youtu")])
    for view in views:
        new_arch, changed = _strip_youtube_xml_arch(view.arch_db or "")
        if not changed:
            new_arch, changed = _strip_youtube_html(view.arch_db or "")
        if changed:
            stats["views"] += 1
            _logger.info("view %s (%s)", view.id, view.name)
            if not dry_run:
                view.write({"arch_db": new_arch})

    if "mail.template" in env:
        Template = env["mail.template"].sudo()
        templates = Template.search([("body_html", "ilike", "youtu")])
        for tmpl in templates:
            new_body, changed = _strip_youtube_html(tmpl.body_html or "")
            if changed:
                stats["mail_templates"] += 1
                _logger.info("mail.template %s (%s)", tmpl.id, tmpl.name)
                if not dry_run:
                    tmpl.write({"body_html": new_body})

    Param = env["ir.config_parameter"].sudo()
    for key in (
        "web.base.url.youtube",
        "sale.promo_video_url",
        "base.promo_video_url",
    ):
        p = Param.search([("key", "=", key)], limit=1)
        if p and p.value and YOUTUBE_RE.search(p.value):
            stats["params"] += 1
            _logger.info("ir.config_parameter %s", key)
            if not dry_run:
                p.unlink()

    # Clear asset caches so UI refreshes without stale YouTube embeds.
    if not dry_run:
        env["ir.attachment"].sudo().search([
            ("name", "ilike", "web.assets_backend"),
            ("url", "ilike", "/web/assets/"),
        ]).unlink()
        env.registry.clear_cache()

    _logger.info(
        "Done. views=%s mail_templates=%s params=%s dry_run=%s",
        stats["views"], stats["mail_templates"], stats["params"], dry_run,
    )
    return stats


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--config", required=True, help="TCRM config file")
    parser.add_argument("-d", "--database", required=True, help="Database name")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not write")
    args = parser.parse_args(argv)

    # Bootstrap TCRM / Odoo
    sys.path.insert(0, "/opt/tcrm/tcrm-src")
    from tcrm.tools import config as tcrm_config
    from tcrm.modules.registry import Registry
    import tcrm
    from tcrm.api import Environment

    tcrm_config.parse_config(["-c", args.config, "-d", args.database])
    registry = Registry(args.database)
    with registry.cursor() as cr:
        env = Environment(cr, tcrm.SUPERUSER_ID, {})
        stats = run(env, dry_run=args.dry_run)
        if not args.dry_run:
            cr.commit()
        print(stats)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # When exec()'d from tcrm shell, `env` already exists — expose run().
    if "env" in globals():
        print(run(globals()["env"]))
    else:
        main()
