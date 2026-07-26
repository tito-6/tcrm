# Part of TCRM AI Research. See LICENSE for details.

import logging

from markupsafe import Markup, escape

from tcrm import api, fields, models
from tcrm.exceptions import UserError

_logger = logging.getLogger(__name__)


class TcrmAiMessage(models.Model):
    _name = 'tcrm.ai.message'
    _description = 'AI Research Message'
    _order = 'id asc'

    conversation_id = fields.Many2one(
        'tcrm.ai.conversation',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='conversation_id.company_id',
        store=True,
        index=True,
    )
    role = fields.Selection(
        [('user', 'User'), ('assistant', 'Assistant'), ('system', 'System')],
        required=True,
        index=True,
    )
    content = fields.Text()
    language = fields.Selection([('tr', 'Turkish'), ('en', 'English')])
    status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('streaming', 'Streaming'),
            ('done', 'Done'),
            ('error', 'Error'),
            ('stopped', 'Stopped'),
        ],
        default='done',
        required=True,
        index=True,
    )
    error_message = fields.Char()
    ragflow_message_id = fields.Char(index=True)
    citation_ids = fields.One2many('tcrm.ai.citation', 'message_id', string='Citations')

    def _create_citations(self, citations: list):
        self.ensure_one()
        Citation = self.env['tcrm.ai.citation']
        Document = self.env['tcrm.ai.document']
        for item in citations:
            doc = Document.browse()
            ext_id = item.get('document_external_id')
            if ext_id:
                doc = Document.search([
                    ('ragflow_document_id', '=', ext_id),
                    ('workspace_id', '=', self.conversation_id.workspace_id.id),
                ], limit=1)
            page = item.get('page_number')
            if isinstance(page, (list, tuple)):
                page = page[0] if page else False
            try:
                page_number = int(page) if page not in (None, False, '') else False
            except (TypeError, ValueError):
                page_number = False
            score = item.get('score')
            try:
                score_val = float(score) if score is not None else False
            except (TypeError, ValueError):
                score_val = False
            Citation.create({
                'message_id': self.id,
                'document_id': doc.id if doc else False,
                'title': (item.get('title') or '')[:255],
                'page_number': page_number,
                'chunk_text': item.get('chunk_text') or '',
                'source_url': (item.get('source_url') or '')[:1024],
                'score': score_val,
                'external_reference': (item.get('external_reference') or '')[:255],
            })

    def action_save_as_note(self):
        """Post sanitized research result as an internal note on the CRM record."""
        self.ensure_one()
        if self.role != 'assistant':
            raise UserError(self.env._('Only assistant messages can be saved as notes.'))
        conv = self.conversation_id
        conv.workspace_id._check_membership()

        target = None
        if conv.lead_id:
            conv.lead_id.check_access('write')
            target = conv.lead_id
        elif conv.partner_id:
            conv.partner_id.check_access('write')
            target = conv.partner_id
        elif conv.res_model and conv.res_id and conv.res_model in self.env:
            target = self.env[conv.res_model].browse(conv.res_id)
            target.check_access('write')
            if not target.exists():
                target = None
        if not target:
            raise UserError(self.env._('No CRM record is linked to this conversation.'))

        body = self._format_note_body()
        target.message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
            author_id=self.env.user.partner_id.id,
        )
        _logger.info(
            'ai_research_save_note user_id=%s message_id=%s conversation_id=%s res_model=%s res_id=%s',
            self.env.user.id,
            self.id,
            conv.id,
            target._name,
            target.id,
        )
        return True

    def action_attach_result(self):
        """Attach the research answer as a plain-text attachment on the CRM record."""
        self.ensure_one()
        if self.role != 'assistant':
            raise UserError(self.env._('Only assistant messages can be attached.'))
        conv = self.conversation_id
        conv.workspace_id._check_membership()

        target = conv.lead_id or conv.partner_id
        if not target and conv.res_model and conv.res_id:
            target = self.env[conv.res_model].browse(conv.res_id)
        if not target or not target.exists():
            raise UserError(self.env._('No CRM record is linked to this conversation.'))
        target.check_access('write')

        content = (self.content or '').encode('utf-8')
        filename = f'ai_research_{conv.id}_{self.id}.txt'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': __import__('base64').b64encode(content),
            'res_model': target._name,
            'res_id': target.id,
            'mimetype': 'text/plain',
        })
        target.message_post(
            body=self.env._('AI research result attached.'),
            attachment_ids=[attachment.id],
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return {'attachment_id': attachment.id}

    def _format_note_body(self) -> Markup:
        self.ensure_one()
        conv = self.conversation_id
        citations = self.citation_ids
        citation_lines = ''.join(
            f'<li>{escape(c.title or self.env._("Source"))}'
            + (f' (p. {int(c.page_number)})' if c.page_number else '')
            + '</li>'
            for c in citations
        )
        answer_html = escape(self.content or '').replace('\n', Markup('<br/>'))
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        link = ''
        if base_url:
            link = (
                f'<p><a href="{escape(base_url)}/web#id={conv.id}'
                f'&model=tcrm.ai.conversation&view_type=form">'
                f'{escape(self.env._("Open AI conversation"))}</a></p>'
            )
        return Markup(
            '<p><strong>%(heading)s</strong></p>'
            '<p>%(answer)s</p>'
            '%(citations_block)s'
            '%(link)s'
            '<p><em>%(meta)s</em></p>'
        ) % {
            'heading': escape(self.env._('AI Research Result')),
            'answer': answer_html,
            'citations_block': (
                Markup('<p><strong>%s</strong></p><ul>%s</ul>')
                % (escape(self.env._('Citations')), Markup(citation_lines))
                if citation_lines else ''
            ),
            'link': Markup(link),
            'meta': escape(
                self.env._('Saved by %(user)s at %(when)s')
                % {
                    'user': self.env.user.name,
                    'when': fields.Datetime.to_string(fields.Datetime.now()),
                }
            ),
        }
