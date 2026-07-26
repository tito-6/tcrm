# Part of TCRM AI Research. See LICENSE for details.
"""Build permission-safe CRM context for research prompts."""

from __future__ import annotations

import logging
from typing import Any

from tcrm.exceptions import AccessError, MissingError

_logger = logging.getLogger(__name__)

_MAX_DESC_LEN = 2000
_MAX_NOTE_LEN = 1500
_MAX_MESSAGES = 10
_MAX_ATTACHMENTS = 20


class ContextBuilder:
    """Collect readable CRM fields the current user is allowed to see."""

    def __init__(self, env):
        self.env = env

    def build(
        self,
        *,
        res_model: str | None = None,
        res_id: int | None = None,
        partner_id: int | None = None,
        lead_id: int | None = None,
        include_chatter: bool = False,
        include_attachments: bool = True,
    ) -> dict[str, Any]:
        """
        Return a compact, permission-checked context dict.

        Never raises AccessError to the caller for missing optional bits;
        inaccessible records are omitted.
        """
        context: dict[str, Any] = {
            'company_id': self.env.company.id,
            'user_id': self.env.user.id,
            'user_name': self.env.user.name,
            'record_name': None,
            'res_model': res_model,
            'res_id': res_id,
            'partner': None,
            'lead': None,
            'attachments': [],
            'prompt_text': '',
        }

        lead = self._safe_browse('crm.lead', lead_id)
        if not lead and res_model == 'crm.lead' and res_id:
            lead = self._safe_browse('crm.lead', res_id)

        partner = self._safe_browse('res.partner', partner_id)
        if not partner and lead and lead.partner_id:
            partner = lead.partner_id if self._can_read(lead.partner_id) else None
        if not partner and res_model == 'res.partner' and res_id:
            partner = self._safe_browse('res.partner', res_id)

        if lead:
            context['lead'] = self._lead_dict(lead)
            context['lead_id'] = lead.id
            context['record_name'] = lead.display_name
            context['res_model'] = 'crm.lead'
            context['res_id'] = lead.id
            if include_attachments:
                context['attachments'].extend(self._attachment_summaries('crm.lead', lead.id))
            if include_chatter:
                context['lead']['recent_notes'] = self._chatter_notes(lead)

        if partner:
            context['partner'] = self._partner_dict(partner)
            context['partner_id'] = partner.id
            if not context['record_name']:
                context['record_name'] = partner.display_name
                context['res_model'] = context['res_model'] or 'res.partner'
                context['res_id'] = context['res_id'] or partner.id
            if include_attachments:
                context['attachments'].extend(
                    self._attachment_summaries('res.partner', partner.id)
                )

        # Deduplicate attachments by id
        seen = set()
        unique = []
        for att in context['attachments']:
            if att['id'] in seen:
                continue
            seen.add(att['id'])
            unique.append(att)
        context['attachments'] = unique[:_MAX_ATTACHMENTS]
        context['prompt_text'] = self._format_prompt(context)
        return context

    def _safe_browse(self, model: str, res_id: int | None):
        if not res_id or model not in self.env:
            return self.env[model].browse() if model in self.env else None
        try:
            record = self.env[model].browse(int(res_id))
            if not record.exists():
                return self.env[model].browse()
            record.check_access('read')
            return record
        except (AccessError, MissingError, ValueError, TypeError):
            return self.env[model].browse()

    def _can_read(self, record) -> bool:
        if not record:
            return False
        try:
            record.check_access('read')
            return bool(record.exists())
        except AccessError:
            return False

    def _lead_dict(self, lead) -> dict[str, Any]:
        stage = lead.stage_id.name if lead.stage_id else None
        tags = []
        if 'tag_ids' in lead._fields:
            tags = lead.tag_ids.mapped('name')
        desc = (lead.description or '')[:_MAX_DESC_LEN]
        return {
            'id': lead.id,
            'name': lead.name,
            'type': lead.type,
            'stage': stage,
            'user': lead.user_id.name if lead.user_id else None,
            'partner_name': lead.partner_id.name if lead.partner_id else lead.contact_name,
            'email': lead.email_from,
            'tags': tags,
            'description': desc,
            'expected_revenue': float(lead.expected_revenue or 0.0) if 'expected_revenue' in lead._fields else None,
        }

    def _partner_dict(self, partner) -> dict[str, Any]:
        return {
            'id': partner.id,
            'name': partner.name,
            'is_company': partner.is_company,
            'email': partner.email,
            'phone': partner.phone,
            'city': partner.city,
            'country': partner.country_id.name if partner.country_id else None,
            'comment': (partner.comment or '')[:_MAX_NOTE_LEN],
        }

    def _attachment_summaries(self, res_model: str, res_id: int) -> list[dict[str, Any]]:
        Attachment = self.env['ir.attachment']
        try:
            atts = Attachment.search([
                ('res_model', '=', res_model),
                ('res_id', '=', res_id),
            ], limit=_MAX_ATTACHMENTS)
        except AccessError:
            return []
        result = []
        for att in atts:
            try:
                att.check_access('read')
            except AccessError:
                continue
            result.append({
                'id': att.id,
                'name': att.name,
                'mimetype': att.mimetype,
                'file_size': att.file_size,
            })
        return result

    def _chatter_notes(self, record) -> list[str]:
        if 'message_ids' not in record._fields:
            return []
        notes = []
        try:
            messages = record.message_ids.filtered(
                lambda m: m.message_type in ('comment', 'notification')
            )[:_MAX_MESSAGES]
            for msg in messages:
                body = (msg.body or '')
                # Strip tags lightly without importing HTML parsers in hot path.
                text = body.replace('<br>', '\n').replace('<br/>', '\n')
                while '<' in text and '>' in text:
                    start = text.find('<')
                    end = text.find('>', start)
                    if end == -1:
                        break
                    text = text[:start] + text[end + 1:]
                text = text.strip()
                if text:
                    notes.append(text[:_MAX_NOTE_LEN])
        except AccessError:
            return []
        return notes

    def _format_prompt(self, context: dict[str, Any]) -> str:
        parts = ['CRM Context (permission-filtered):']
        if context.get('lead'):
            lead = context['lead']
            parts.append(
                f"- Lead/Opportunity: {lead.get('name')} | stage={lead.get('stage')} "
                f"| salesperson={lead.get('user')} | tags={', '.join(lead.get('tags') or [])}"
            )
            if lead.get('description'):
                parts.append(f"- Description: {lead['description']}")
            for note in lead.get('recent_notes') or []:
                parts.append(f"- Note: {note}")
        if context.get('partner'):
            partner = context['partner']
            parts.append(
                f"- Customer: {partner.get('name')} | email={partner.get('email')} "
                f"| city={partner.get('city')}"
            )
            if partner.get('comment'):
                parts.append(f"- Customer note: {partner['comment']}")
        if context.get('attachments'):
            names = ', '.join(a['name'] for a in context['attachments'][:10])
            parts.append(f"- Related attachments: {names}")
        return '\n'.join(parts)
