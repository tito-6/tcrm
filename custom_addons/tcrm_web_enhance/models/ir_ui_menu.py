# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
import logging

from tcrm import api, models

_logger = logging.getLogger(__name__)


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _tcrm_fix_missing_web_icons(self):
        """Repair app menus whose ``web_icon`` is set but whose ``web_icon_data``
        is empty, so their icon renders in the TCRM application sidebar.

        Some apps (notably Discuss / "Mesajlaşma" and Contacts) can end up with an
        empty ``web_icon_data`` in the database even though ``web_icon`` points at a
        valid icon file. When that happens the web client falls back to a broken
        image and the app shows no icon. ``web_icon_data`` is only (re)computed by
        the ORM when ``web_icon`` is part of a write, so we recompute it here.

        Idempotent by design: it only touches menus that are actually missing their
        icon data, so it is safe to run on every module install/upgrade.
        """
        # NB: `web_icon_data` is a Binary(attachment=True) field and therefore
        # cannot be filtered in a search domain, so we fetch every menu that has a
        # `web_icon` and check the (attachment-backed) data in Python.
        candidates = self.sudo().search([("web_icon", "!=", False)])
        fixed = self.browse()
        for menu in candidates:
            if menu.web_icon_data:
                continue
            # Re-writing `web_icon` re-triggers `_compute_web_icon_data` via the
            # write() override, which reads the icon file and stores the attachment.
            menu.write({"web_icon": menu.web_icon})
            if menu.web_icon_data:
                fixed |= menu
        if fixed:
            self.env.registry.clear_cache()
            _logger.info(
                "TCRM: recomputed web_icon_data for %s app menu(s): %s",
                len(fixed),
                ", ".join(fixed.mapped("name")),
            )
        return True
