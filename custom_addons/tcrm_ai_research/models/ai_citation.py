# Part of TCRM AI Research. See LICENSE for details.

from tcrm import fields, models


class TcrmAiCitation(models.Model):
    _name = 'tcrm.ai.citation'
    _description = 'AI Research Citation'
    _order = 'score desc, id asc'

    message_id = fields.Many2one(
        'tcrm.ai.message',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='message_id.company_id',
        store=True,
        index=True,
    )
    document_id = fields.Many2one('tcrm.ai.document', ondelete='set null', index=True)
    title = fields.Char()
    page_number = fields.Integer()
    chunk_text = fields.Text()
    source_url = fields.Char()
    score = fields.Float()
    external_reference = fields.Char(index=True)
