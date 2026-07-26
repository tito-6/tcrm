# Part of TCRM AI Research. See LICENSE for details.
"""Authenticated JSON-RPC routes for the native AI research assistant."""

from __future__ import annotations

import base64
import logging
import uuid

from tcrm import http, _
from tcrm.exceptions import AccessError, UserError, ValidationError
from tcrm.http import request

from ..services.config import public_config_dict
from ..services.context_builder import ContextBuilder
from ..services.document_sync_service import DocumentSyncService
from ..services.exceptions import RagflowError

_logger = logging.getLogger(__name__)


def _err(message: str, *, code: str = 'error', status: int = 400) -> dict:
    return {'ok': False, 'error': {'code': code, 'message': message}, 'status': status}


def _ok(data=None) -> dict:
    return {'ok': True, 'data': data if data is not None else {}}


def _require_group():
    if not request.env.user.has_group('tcrm_ai_research.group_ai_research_user'):
        raise AccessError(_('You need AI Research User access.'))


def _conversation(conv_id: int):
    conv = request.env['tcrm.ai.conversation'].browse(int(conv_id))
    conv.check_access('read')
    if not conv.exists():
        raise AccessError(_('Conversation not found.'))
    conv.workspace_id._check_membership()
    return conv


class AiResearchController(http.Controller):

    @http.route('/tcrm_ai/config', type='jsonrpc', auth='user')
    def get_config(self):
        _require_group()
        return _ok(public_config_dict(request.env))

    @http.route('/tcrm_ai/workspaces', type='jsonrpc', auth='user')
    def list_workspaces(self):
        _require_group()
        workspaces = request.env['tcrm.ai.workspace'].search([
            ('company_id', 'in', request.env.companies.ids),
            ('active', '=', True),
        ])
        return _ok([{
            'id': w.id,
            'name': w.name,
            'default_language': w.default_language,
            'allow_web_research': w.allow_web_research,
            'document_count': w.document_count,
        } for w in workspaces])

    @http.route('/tcrm_ai/conversations', type='jsonrpc', auth='user', methods=['POST'])
    def create_or_list_conversations(self, workspace_id=None, partner_id=None, lead_id=None,
                                    res_model=None, res_id=None, record_name=None,
                                    name=None, language=None, limit=40, offset=0, **kwargs):
        """
        Dual-purpose route matching the suggested API:
        - With create fields (workspace_id + optional CRM context) → create
        - With only pagination → list
        """
        _require_group()
        # Detect list vs create: if only limit/offset-like args, list.
        create_requested = bool(workspace_id) or kwargs.get('create')
        if not create_requested and not (partner_id or lead_id or res_model):
            return self._list_conversations(limit=limit, offset=offset, workspace_id=workspace_id)

        if not workspace_id:
            return _err(_('workspace_id is required.'), code='validation')
        workspace = request.env['tcrm.ai.workspace'].browse(int(workspace_id))
        workspace.check_access('read')
        workspace._check_membership()

        # Validate CRM IDs — never trust the frontend blindly.
        partner = request.env['res.partner'].browse()
        lead = request.env['crm.lead'].browse()
        if partner_id:
            partner = request.env['res.partner'].browse(int(partner_id))
            partner.check_access('read')
            if not partner.exists():
                return _err(_('Partner not found or inaccessible.'), code='access', status=403)
        if lead_id:
            lead = request.env['crm.lead'].browse(int(lead_id))
            lead.check_access('read')
            if not lead.exists():
                return _err(_('Lead not found or inaccessible.'), code='access', status=403)
            if not partner and lead.partner_id:
                partner = lead.partner_id

        if res_model and res_id:
            if res_model not in request.env:
                return _err(_('Invalid model.'), code='validation')
            record = request.env[res_model].browse(int(res_id))
            record.check_access('read')
            if not record.exists():
                return _err(_('Record not found or inaccessible.'), code='access', status=403)
            record_name = record_name or record.display_name

        vals = {
            'workspace_id': workspace.id,
            'name': name or False,
            'partner_id': partner.id if partner else False,
            'lead_id': lead.id if lead else False,
            'res_model': res_model or (lead and 'crm.lead') or (partner and 'res.partner') or False,
            'res_id': int(res_id) if res_id else (lead.id if lead else (partner.id if partner else False)),
            'record_name': record_name or False,
            'language': language or workspace.default_language,
        }
        conv = request.env['tcrm.ai.conversation'].create(vals)
        return _ok(self._conversation_payload(conv))

    @http.route('/tcrm_ai/conversations/list', type='jsonrpc', auth='user')
    def list_conversations_route(self, workspace_id=None, limit=40, offset=0, **kwargs):
        _require_group()
        return self._list_conversations(limit=limit, offset=offset, workspace_id=workspace_id)

    def _list_conversations(self, limit=40, offset=0, workspace_id=None):
        domain = [('company_id', 'in', request.env.companies.ids)]
        if workspace_id:
            domain.append(('workspace_id', '=', int(workspace_id)))
        limit = max(1, min(100, int(limit or 40)))
        offset = max(0, int(offset or 0))
        conversations = request.env['tcrm.ai.conversation'].search(
            domain, limit=limit, offset=offset, order='last_activity_at desc, id desc'
        )
        return _ok([self._conversation_payload(c, include_messages=False) for c in conversations])

    @http.route('/tcrm_ai/conversations/<int:conversation_id>', type='jsonrpc', auth='user')
    def get_conversation(self, conversation_id, **kwargs):
        _require_group()
        conv = _conversation(conversation_id)
        return _ok(self._conversation_payload(conv, include_messages=True))

    @http.route('/tcrm_ai/conversations/<int:conversation_id>/message', type='jsonrpc', auth='user')
    def post_message(self, conversation_id, question=None, language=None, document_ids=None, **kwargs):
        _require_group()
        corr = str(uuid.uuid4())
        conv = _conversation(conversation_id)
        conv.check_access('write')
        if not question:
            return _err(_('Question is required.'), code='validation')
        try:
            result = conv.ask_question(
                question,
                language=language,
                document_ids=document_ids or [],
            )
        except (AccessError, UserError, ValidationError) as exc:
            return _err(str(exc), code='access', status=403)
        except Exception:
            _logger.exception(
                'ai_research_message_failed correlation_id=%s conversation_id=%s user_id=%s',
                corr, conversation_id, request.env.user.id,
            )
            return _err(_('Research request failed.'), code='provider', status=502)

        assistant = request.env['tcrm.ai.message'].browse(result['assistant_message_id'])
        _logger.info(
            'ai_research_message correlation_id=%s conversation_id=%s workspace_id=%s user_id=%s status=%s',
            corr, conv.id, conv.workspace_id.id, request.env.user.id, assistant.status,
        )
        return _ok({
            'conversation': self._conversation_payload(conv, include_messages=True),
            'assistant_message': self._message_payload(assistant),
        })

    @http.route('/tcrm_ai/conversations/<int:conversation_id>/stop', type='jsonrpc', auth='user')
    def stop_generation(self, conversation_id, **kwargs):
        _require_group()
        conv = _conversation(conversation_id)
        conv.check_access('write')
        pending = conv.ai_message_ids.filtered(lambda m: m.status in ('pending', 'streaming'))
        pending.write({'status': 'stopped'})
        return _ok({'stopped': len(pending)})

    @http.route('/tcrm_ai/documents', type='jsonrpc', auth='user')
    def list_documents(self, workspace_id=None, limit=50, **kwargs):
        _require_group()
        if not workspace_id:
            return _err(_('workspace_id is required.'), code='validation')
        workspace = request.env['tcrm.ai.workspace'].browse(int(workspace_id))
        workspace.check_access('read')
        workspace._check_membership()
        limit = max(1, min(100, int(limit or 50)))
        docs = request.env['tcrm.ai.document'].search([
            ('workspace_id', '=', workspace.id),
        ], limit=limit, order='id desc')
        return _ok([self._document_payload(d) for d in docs])

    @http.route('/tcrm_ai/documents/upload', type='jsonrpc', auth='user')
    def upload_document(self, workspace_id=None, name=None, datas=None, mimetype=None,
                        partner_id=None, lead_id=None, attachment_id=None, sync=True, **kwargs):
        _require_group()
        if not workspace_id:
            return _err(_('workspace_id is required.'), code='validation')
        workspace = request.env['tcrm.ai.workspace'].browse(int(workspace_id))
        workspace.check_access('read')
        workspace._check_membership()

        Attachment = request.env['ir.attachment']
        sync_service = DocumentSyncService(request.env)

        if attachment_id:
            attachment = Attachment.browse(int(attachment_id))
            attachment.check_access('read')
            if not attachment.exists():
                return _err(_('Attachment not found or inaccessible.'), code='access', status=403)
            content = attachment.raw or b''
            sync_service.validate_upload(attachment.name or name or 'file', content)
        else:
            if not datas or not name:
                return _err(_('name and datas are required.'), code='validation')
            try:
                content = base64.b64decode(datas)
            except Exception:
                return _err(_('Invalid file payload.'), code='validation')
            sync_service.validate_upload(name, content)
            # Create unlinked first — users may only have read on workspaces.
            attachment = Attachment.create({
                'name': name,
                'type': 'binary',
                'datas': datas,
                'mimetype': mimetype or 'application/octet-stream',
            })

        if partner_id:
            partner = request.env['res.partner'].browse(int(partner_id))
            partner.check_access('read')
            if not partner.exists():
                return _err(_('Partner not found or inaccessible.'), code='access', status=403)
        else:
            partner = request.env['res.partner'].browse()
        if lead_id:
            lead = request.env['crm.lead'].browse(int(lead_id))
            lead.check_access('read')
            if not lead.exists():
                return _err(_('Lead not found or inaccessible.'), code='access', status=403)
        else:
            lead = request.env['crm.lead'].browse()

        # Deduplicate by checksum within workspace
        checksum = sync_service.compute_checksum(attachment.raw or b'')
        existing = request.env['tcrm.ai.document'].search([
            ('workspace_id', '=', workspace.id),
            ('checksum', '=', checksum),
        ], limit=1)
        if existing:
            doc = existing
        else:
            doc = request.env['tcrm.ai.document'].create({
                'name': name or attachment.name,
                'workspace_id': workspace.id,
                'attachment_id': attachment.id,
                'partner_id': partner.id if partner else False,
                'lead_id': lead.id if lead else False,
                'checksum': checksum,
                'mime_type': attachment.mimetype,
                'file_size': attachment.file_size,
                'sync_state': 'pending',
            })
            if not attachment.res_model:
                attachment.write({
                    'res_model': 'tcrm.ai.document',
                    'res_id': doc.id,
                })
        if sync:
            try:
                sync_service.sync_document(doc)
            except (UserError, ValidationError) as exc:
                return _err(str(exc), code='sync')
            except RagflowError:
                return _err(_('Document synchronization failed.'), code='provider', status=502)
        return _ok(self._document_payload(doc))

    @http.route('/tcrm_ai/documents/<int:document_id>/sync', type='jsonrpc', auth='user')
    def sync_document(self, document_id, **kwargs):
        _require_group()
        doc = request.env['tcrm.ai.document'].browse(int(document_id))
        doc.check_access('write')
        if not doc.exists():
            return _err(_('Document not found.'), code='access', status=403)
        doc.workspace_id._check_membership()
        try:
            DocumentSyncService(request.env).sync_document(doc)
        except (UserError, ValidationError) as exc:
            return _err(str(exc), code='sync')
        except RagflowError:
            return _err(_('Document synchronization failed.'), code='provider', status=502)
        return _ok(self._document_payload(doc))

    @http.route('/tcrm_ai/messages/<int:message_id>/citations', type='jsonrpc', auth='user')
    def get_citations(self, message_id, **kwargs):
        _require_group()
        message = request.env['tcrm.ai.message'].browse(int(message_id))
        message.check_access('read')
        if not message.exists():
            return _err(_('Message not found.'), code='access', status=403)
        message.conversation_id.workspace_id._check_membership()
        return _ok([self._citation_payload(c) for c in message.citation_ids])

    @http.route('/tcrm_ai/messages/<int:message_id>/save-note', type='jsonrpc', auth='user')
    def save_note(self, message_id, **kwargs):
        _require_group()
        message = request.env['tcrm.ai.message'].browse(int(message_id))
        message.check_access('read')
        if not message.exists():
            return _err(_('Message not found.'), code='access', status=403)
        try:
            message.action_save_as_note()
        except (AccessError, UserError) as exc:
            return _err(str(exc), code='access', status=403)
        return _ok({'saved': True})

    @http.route('/tcrm_ai/messages/<int:message_id>/attach-result', type='jsonrpc', auth='user')
    def attach_result(self, message_id, **kwargs):
        _require_group()
        message = request.env['tcrm.ai.message'].browse(int(message_id))
        message.check_access('read')
        if not message.exists():
            return _err(_('Message not found.'), code='access', status=403)
        try:
            result = message.action_attach_result()
        except (AccessError, UserError) as exc:
            return _err(str(exc), code='access', status=403)
        return _ok(result)

    @http.route('/tcrm_ai/context/preview', type='jsonrpc', auth='user')
    def context_preview(self, res_model=None, res_id=None, partner_id=None, lead_id=None, **kwargs):
        _require_group()
        ctx = ContextBuilder(request.env).build(
            res_model=res_model,
            res_id=int(res_id) if res_id else None,
            partner_id=int(partner_id) if partner_id else None,
            lead_id=int(lead_id) if lead_id else None,
        )
        # Strip prompt_text length for UI indicator
        return _ok({
            'record_name': ctx.get('record_name'),
            'res_model': ctx.get('res_model'),
            'res_id': ctx.get('res_id'),
            'partner': ctx.get('partner'),
            'lead': ctx.get('lead'),
            'attachments': ctx.get('attachments'),
        })

    # ------------------------------------------------------------------
    # Serializers (never include secrets)
    # ------------------------------------------------------------------

    def _conversation_payload(self, conv, include_messages=False):
        data = {
            'id': conv.id,
            'name': conv.name,
            'workspace_id': conv.workspace_id.id,
            'workspace_name': conv.workspace_id.name,
            'partner_id': conv.partner_id.id if conv.partner_id else False,
            'lead_id': conv.lead_id.id if conv.lead_id else False,
            'res_model': conv.res_model,
            'res_id': conv.res_id,
            'record_name': conv.record_name,
            'state': conv.state,
            'language': conv.language,
            'allow_web_research': conv.allow_web_research,
            'internal_documents_only': conv.internal_documents_only,
            'last_activity_at': fields_dt(conv.last_activity_at),
            'document_ids': conv.document_ids.ids,
        }
        if include_messages:
            data['messages'] = [self._message_payload(m) for m in conv.ai_message_ids]
        return data

    def _message_payload(self, message):
        return {
            'id': message.id,
            'role': message.role,
            'content': message.content or '',
            'language': message.language,
            'status': message.status,
            'error_message': message.error_message or '',
            'create_date': fields_dt(message.create_date),
            'citation_count': len(message.citation_ids),
            'citations': [self._citation_payload(c) for c in message.citation_ids],
        }

    def _document_payload(self, doc):
        return {
            'id': doc.id,
            'name': doc.name,
            'workspace_id': doc.workspace_id.id,
            'sync_state': doc.sync_state,
            'sync_error': doc.sync_error or '',
            'mime_type': doc.mime_type,
            'file_size': doc.file_size,
            'checksum': doc.checksum,
            'last_synced_at': fields_dt(doc.last_synced_at),
        }

    def _citation_payload(self, citation):
        return {
            'id': citation.id,
            'title': citation.title or '',
            'page_number': citation.page_number or False,
            'chunk_text': citation.chunk_text or '',
            'source_url': citation.source_url or '',
            'score': citation.score or 0.0,
            'document_id': citation.document_id.id if citation.document_id else False,
            'document_name': citation.document_id.name if citation.document_id else '',
        }


def fields_dt(value):
    if not value:
        return False
    return value.isoformat(sep=' ') if hasattr(value, 'isoformat') else str(value)
