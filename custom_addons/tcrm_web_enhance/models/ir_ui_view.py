# -*- coding: utf-8 -*-
"""Strip external documentation / video links from Settings view arches."""
from lxml import etree

from tcrm import models


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    def get_combined_arch(self):
        arch = super().get_combined_arch()
        if self.model != 'res.config.settings' or not arch:
            return arch
        try:
            root = etree.fromstring(arch.encode('utf-8') if isinstance(arch, str) else arch)
        except etree.XMLSyntaxError:
            return arch
        if not self._tcrm_strip_settings_documentation(root):
            return arch
        return etree.tostring(root, encoding='unicode')

    def _tcrm_strip_settings_documentation(self, root):
        changed = False
        for el in root.xpath('//*[@documentation]'):
            if 'documentation' in el.attrib:
                del el.attrib['documentation']
                changed = True
        for el in list(root.xpath("//widget[@name='documentation_link']")):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
                changed = True
        # Enterprise upsell checkboxes → normal booleans (no YouTube dialog).
        for el in root.xpath("//field[@widget='upgrade_boolean']"):
            el.set('widget', 'boolean')
            changed = True
        return changed
