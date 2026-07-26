# Part of TCRM Vector Sync. See LICENSE for details.

"""Extend res.partner with vector sync mixin and semantic text for RAG."""

from tcrm import models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'tcrm.vector.sync.mixin']

    def _to_semantic_text(self):
        parts = []
        parts.append(f"Contact: {self.name or 'Unnamed'}.")
        if self.email:
            parts.append(f"Email: {self.email}.")
        if self.phone:
            parts.append(f"Phone: {self.phone}.")
        if self.mobile:
            parts.append(f"Mobile: {self.mobile}.")
        if self.is_company:
            parts.append("Type: Company.")
        else:
            parts.append("Type: Individual.")
        if self.parent_id:
            parts.append(f"Company: {self.parent_id.name}.")
        addr = []
        if self.street:
            addr.append(self.street)
        if self.street2:
            addr.append(self.street2)
        if self.city:
            addr.append(self.city)
        if self.state_id:
            addr.append(self.state_id.name)
        if self.country_id:
            addr.append(self.country_id.name)
        if addr:
            parts.append("Address: " + ", ".join(addr) + ".")
        return " ".join(parts)
