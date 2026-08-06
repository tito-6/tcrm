# Part of TCRM AI. See LICENSE for details.

import io
import json
import logging
import uuid

from tcrm import http, _
from tcrm.http import request, content_disposition

from ..services import entitlement as entitlement_svc
from ..services.constants import CODE_TO_STATUS, SAFE_ERROR_CODES
from ..services.rate_limit import usage_dashboard

_logger = logging.getLogger(__name__)


def _json_safe(obj):
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, (int, float, bool)):
        return obj
    return str(obj)


def _require_ai_user():
    user = request.env.user
    if not (
        user.has_group('tcrm_ai.group_tcrm_ai_user')
        or user.has_group('tcrm_ai.group_tcrm_ai_admin')
        or user.has_group('base.group_system')
    ):
        return {
            'success': False,
            'status': 'forbidden',
            'answer': _('TCRM AI erişiminiz yok.'),
            'tables': [],
            'links': [],
            'error': True,
            'error_code': 'forbidden',
        }
    return None


def _correlation_id(kwargs=None, payload=None):
    for src in (kwargs or {}, payload if isinstance(payload, dict) else {}):
        cid = src.get('correlation_id')
        if cid and isinstance(cid, str) and cid.strip():
            return cid.strip()[:64]
    hdr = request.httprequest.headers.get('X-Correlation-Id') or request.httprequest.headers.get('X-Request-Id')
    if hdr:
        return hdr.strip()[:64]
    return uuid.uuid4().hex


def _strip_chat_secrets(result):
    """Ensure chat responses never carry provider/key/token diagnostics."""
    if not isinstance(result, dict):
        return result
    banned = (
        'api_key', 'api_key_masked', 'api_key_encrypted', 'Authorization',
        'provider', 'model', 'base_url', 'usage',
    )
    out = {k: v for k, v in result.items() if k not in banned}
    # Keep structured error fields.
    if 'status' not in out:
        if out.get('error'):
            out['status'] = CODE_TO_STATUS.get(out.get('error_code') or 'unknown', 'internal_error')
            out['success'] = False
        else:
            out['status'] = 'success'
            out['success'] = True
    return out


class TcrmAiController(http.Controller):
    @http.route('/web/tcrm_ai/ping', type='http', auth='user', methods=['GET'])
    def ping(self):
        return request.make_response('ok', headers=[('Content-Type', 'text/plain')])

    @http.route(['/tcrm_ai/status', '/tcrm/ai/status'], type='jsonrpc', auth='user')
    def status(self):
        """Chat-safe status (no provider/model/key/tokens)."""
        denied = _require_ai_user()
        if denied:
            return {
                'chat_enabled': False,
                'chat_disabled_reason': denied['answer'],
                'title': 'TCRM AI Asistan',
            }
        return request.env['tcrm.ai.config'].get_chat_status()

    @http.route('/tcrm_ai/admin_status', type='jsonrpc', auth='user')
    def admin_status(self):
        """Admin settings status (masked key allowed)."""
        if not (
            request.env.user.has_group('tcrm_ai.group_tcrm_ai_admin')
            or request.env.user.has_group('base.group_system')
        ):
            return {'error': _('Access denied')}
        return request.env['tcrm.ai.config'].get_public_status()

    @http.route('/tcrm_ai/usage_dashboard', type='jsonrpc', auth='user')
    def usage(self):
        if not (
            request.env.user.has_group('tcrm_ai.group_tcrm_ai_admin')
            or request.env.user.has_group('base.group_system')
        ):
            return {'error': _('Access denied')}
        return usage_dashboard(request.env)

    @http.route('/tcrm_ai/settings/save', type='jsonrpc', auth='user')
    def save_settings(self, values=None, **kwargs):
        values = values or kwargs.get('values') or {}
        status = request.env['tcrm.ai.config'].save_settings_rpc(values)
        return status

    @http.route('/tcrm_ai/settings/test_connection', type='jsonrpc', auth='user')
    def test_connection(self):
        config = request.env['tcrm.ai.config'].get_config()
        try:
            config.action_test_connection()
            return {
                'ok': True,
                'message': _('Groq bağlantısı başarılı.'),
                'status': config.get_public_status(),
            }
        except Exception as exc:
            msg = str(exc)
            if 'gsk_' in msg:
                msg = SAFE_ERROR_CODES.get('invalid_api_key', msg)
            return {
                'ok': False,
                'message': msg,
                'status': config.get_public_status(),
            }

    @http.route(
        ['/tcrm_ai/ask', '/tcrm/ai/ask'],
        type='jsonrpc',
        auth='user',
    )
    def ask(self, message=None, session_id=None, conversation_id=None, correlation_id=None, source=None, **kwargs):
        denied = _require_ai_user()
        if denied:
            denied['correlation_id'] = _correlation_id(kwargs, {'correlation_id': correlation_id})
            return denied
        ok, code = entitlement_svc.entitlement_allows_requests(request.env)
        cid = _correlation_id(kwargs, {
            'correlation_id': correlation_id,
            'message': message if isinstance(message, dict) else {},
        })
        if not ok:
            return {
                'success': False,
                'status': CODE_TO_STATUS.get(code or 'entitlement_denied', 'forbidden'),
                'answer': SAFE_ERROR_CODES.get(code or 'entitlement_denied'),
                'tables': [],
                'links': [],
                'error': True,
                'error_code': code or 'entitlement_denied',
                'disabled': True,
                'correlation_id': cid,
            }
        base_url = request.httprequest.url_root.rstrip('/')
        payload = message
        if not isinstance(payload, dict):
            payload = {
                'text': message or '',
                'session_id': session_id,
                'conversation_id': conversation_id,
                'correlation_id': cid,
                'source': source or 'assistant',
            }
        else:
            payload = dict(payload)
            payload.setdefault('correlation_id', cid)
            if session_id and 'session_id' not in payload:
                payload['session_id'] = session_id
            if conversation_id and 'conversation_id' not in payload:
                payload['conversation_id'] = conversation_id
            if source and 'source' not in payload:
                payload['source'] = source
        try:
            result = request.env['tcrm.ai.engine']._ask(payload, base_url=base_url, correlation_id=cid)
            safe = _strip_chat_secrets(result if isinstance(result, dict) else {'answer': str(result), 'error': False})
            _logger.info(
                'TCRM AI /ask cid=%s status=%s db=%s',
                safe.get('correlation_id') or cid,
                safe.get('status'),
                request.env.cr.dbname,
            )
            return _json_safe(safe)
        except ModuleNotFoundError as exc:
            _logger.exception('TCRM AI /ask missing dependency cid=%s: %s', cid, getattr(exc, 'name', ''))
            return {
                'success': False,
                'status': 'internal_error',
                'answer': _(
                    'TCRM AI Groq yoluna geçirildi. Lütfen sayfayı yenileyin; sorun sürerse '
                    'Ayarlar > TCRM AI bölümünden Bağlantıyı Test Et çalıştırın.'
                ),
                'tables': [],
                'links': [],
                'error': True,
                'error_code': 'internal_error',
                'correlation_id': cid,
            }
        except Exception:
            _logger.exception('TCRM AI /ask failed cid=%s', cid)
            return {
                'success': False,
                'status': 'internal_error',
                'answer': SAFE_ERROR_CODES['internal_error'],
                'tables': [],
                'links': [],
                'error': True,
                'error_code': 'internal_error',
                'correlation_id': cid,
            }

    @http.route('/tcrm_ai/conversations', type='jsonrpc', auth='user')
    def list_conversations(self, limit=40):
        denied = _require_ai_user()
        if denied:
            return {'conversations': [], 'error': denied['answer']}
        limit = max(1, min(100, int(limit or 40)))
        Conv = request.env['tcrm.ai.assistant.conversation']
        convs = Conv.search([
            ('user_id', '=', request.env.user.id),
            ('company_id', '=', request.env.company.id),
        ], limit=limit, order='last_message_date desc, id desc')
        rows = []
        for c in convs:
            title = c.name or _('Sohbet')
            if title.startswith('session:'):
                title = _('Sohbet')
            rows.append({
                'id': c.id,
                'name': title,
                'last_message_date': c.last_message_date and c.last_message_date.isoformat(),
                'message_count': c.message_count,
                'source_type': c.source_type if 'source_type' in c._fields else 'assistant',
            })
        return {'conversations': rows}

    @http.route('/tcrm_ai/conversation/messages', type='jsonrpc', auth='user')
    def conversation_messages(self, conversation_id=None):
        denied = _require_ai_user()
        if denied:
            return {'messages': [], 'error': denied['answer']}
        if not conversation_id:
            return {'messages': []}
        conv = request.env['tcrm.ai.assistant.conversation'].browse(int(conversation_id))
        if not conv.exists() or conv.user_id != request.env.user:
            return {'messages': [], 'error': _('Sohbet bulunamadı.')}
        messages = []
        for m in conv.message_ids.sorted('id'):
            if m.role == 'tool':
                continue
            messages.append({
                'id': m.id,
                'role': m.role,
                'content': m.content or '',
                'create_date': m.create_date.isoformat() if m.create_date else '',
            })
        return {
            'conversation_id': conv.id,
            'name': conv.name,
            'messages': messages,
        }

    @http.route('/tcrm_ai/conversation/new', type='jsonrpc', auth='user')
    def new_conversation(self, source='assistant'):
        denied = _require_ai_user()
        if denied:
            return denied
        conv = request.env['tcrm.ai.assistant.conversation'].create({
            'name': _('Yeni Sohbet'),
            'user_id': request.env.user.id,
            'company_id': request.env.company.id,
            'source_type': source if source in dict(request.env['tcrm.ai.assistant.conversation']._fields['source_type'].selection) else 'assistant',
        })
        return {'conversation_id': conv.id, 'name': conv.name}

    @http.route('/tcrm_ai/clear_session', type='jsonrpc', auth='user')
    def clear_session(self, session_id=None, conversation_id=None):
        try:
            if conversation_id:
                conv = request.env['tcrm.ai.assistant.conversation'].browse(int(conversation_id))
                if conv.exists() and conv.user_id == request.env.user:
                    conv.unlink()
            elif session_id:
                if 'tcrm.ai.session' in request.env:
                    request.env['tcrm.ai.session'].clear(session_id)
                conv = request.env['tcrm.ai.assistant.conversation'].search([
                    ('user_id', '=', request.env.user.id),
                    ('name', '=', 'session:%s' % session_id),
                ], limit=1)
                if conv:
                    conv.unlink()
            return {'ok': True}
        except Exception as e:
            _logger.warning('TCRM AI clear_session: %s', type(e).__name__)
            return {'ok': False}

    @http.route('/tcrm_ai/export', type='http', auth='user', methods=['POST'], csrf=False)
    def export(self, **kw):
        try:
            body = request.httprequest.get_data(as_text=True) or '{}'
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {}
            fmt = (data.get('format') or 'xlsx').lower()
            tables_data = data.get('tables') or []
            title = data.get('title') or 'TCRM AI Report'
            if not tables_data:
                return request.make_response(
                    _('No table data to export.'),
                    headers=[('Content-Type', 'text/plain; charset=utf-8')],
                    status=400,
                )
            config = request.env['tcrm.ai.config'].get_config()
            if not config.allow_reports:
                return request.make_response(_('Rapor dışa aktarma kapalı.'), status=403)
            if fmt == 'xlsx':
                return self._export_xlsx(tables_data, title)
            if fmt in ('html', 'pdf'):
                return self._export_html(tables_data, title)
            return request.make_response('Unknown format', status=400)
        except Exception:
            _logger.exception('TCRM AI export failed')
            return request.make_response('export failed', status=500)

    def _export_xlsx(self, tables_data, title):
        import xlsxwriter  # noqa: PLC0415
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#e0e0e0'})
        for sheet_idx, tbl in enumerate(tables_data[:10]):
            headers = tbl.get('headers') or []
            rows = tbl.get('rows') or []
            sheet_name = (title or 'Sheet')[:31]
            if sheet_idx > 0:
                sheet_name = '%s %d' % (sheet_name, sheet_idx + 1)
            worksheet = workbook.add_worksheet(sheet_name)
            for col, h in enumerate(headers):
                worksheet.write(0, col, str(h), header_fmt)
            for row_idx, row in enumerate(rows, 1):
                cells = row if isinstance(row, (list, tuple)) else [row.get(h, '') for h in headers]
                for col_idx, cell in enumerate(cells):
                    worksheet.write(row_idx, col_idx, str(cell) if cell is not None else '')
            worksheet.set_column(0, max(0, len(headers) - 1), 18)
        workbook.close()
        filename = (title or 'tcrm_ai_export').replace(' ', '_') + '.xlsx'
        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ],
        )

    def _export_html(self, tables_data, title):
        parts = ['<!DOCTYPE html><html><head><meta charset="utf-8"><title>%s</title></head><body>' % (title or 'Report')]
        parts.append('<h1>%s</h1>' % (title or 'TCRM AI Report'))
        for tbl in tables_data:
            headers = tbl.get('headers') or []
            rows = tbl.get('rows') or []
            parts.append('<table border="1" cellpadding="6" style="border-collapse:collapse;margin:1em 0;">')
            parts.append('<thead><tr>' + ''.join('<th>%s</th>' % str(h).replace('<', '&lt;') for h in headers) + '</tr></thead><tbody>')
            for row in rows:
                cells = row if isinstance(row, (list, tuple)) else [row.get(h, '') for h in headers]
                parts.append('<tr>' + ''.join('<td>%s</td>' % (str(c).replace('<', '&lt;') if c is not None else '') for c in cells) + '</tr>')
            parts.append('</tbody></table>')
        parts.append('</body></html>')
        return request.make_response(''.join(parts), headers=[('Content-Type', 'text/html; charset=utf-8')])
