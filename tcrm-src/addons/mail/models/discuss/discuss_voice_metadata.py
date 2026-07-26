# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import fields, models


class DiscussVoiceMetadata(models.Model):
    _name = 'discuss.voice.metadata'
    _description = "Metadata for voice attachments"

    attachment_id = fields.Many2one(
        "ir.attachment", ondelete="cascade", bypass_search_access=True, copy=False, index=True
    )
