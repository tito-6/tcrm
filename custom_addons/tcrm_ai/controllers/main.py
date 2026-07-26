# Part of TCRM AI. See LICENSE for details.

import io
import json
import logging
from tcrm import http, _
from tcrm.http import request, content_disposition

_logger = logging.getLogger(__name__)


def _json_safe(obj):
    """Ensure value is JSON-serializable and strings are ASCII-safe for any middleware."""
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj.encode('ascii', 'replace').decode('ascii')
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, (int, float, bool)):
        return obj
    return str(obj).encode('ascii', 'replace').decode('ascii')


class TcrmAiController(http.Controller):
    @http.route('/web/tcrm_ai/ping', type='http', auth='user', methods=['GET'])
    def ping(self):
        """Verify TCRM AI controller is loaded. When logged in, open: /web/tcrm_ai/ping"""
        return request.make_response('ok', headers=[('Content-Type', 'text/plain')])

    @http.route('/tcrm_ai/ask', type='json', auth='user')
    def ask(self, message, session_id=None):
        base_url = request.httprequest.url_root.rstrip('/')
        if isinstance(message, dict):
            if session_id is not None and 'session_id' not in message:
                message = dict(message, session_id=session_id)
        elif session_id is not None:
            message = {'text': message or '', 'session_id': session_id}
        try:
            result = request.env['tcrm.ai.engine']._ask(message, base_url=base_url)
            if isinstance(result, dict) and 'answer' in result:
                return _json_safe(result)
            return _json_safe({'answer': str(result), 'tables': [], 'links': [], 'error': False})
        except Exception as e:
            _logger.exception("TCRM AI /ask failed")
            err_msg = str(e).encode('ascii', 'replace').decode('ascii')
            return {
                'answer': f'TCRM AI error: {err_msg}. Check Settings > TCRM AI (API key and model).',
                'tables': [],
                'links': [],
                'error': True,
            }

    @http.route('/tcrm_ai/clear_session', type='json', auth='user')
    def clear_session(self, session_id):
        """Clear conversation history for the given session_id."""
        try:
            if session_id:
                request.env['tcrm.ai.session'].clear(session_id)
            return {'ok': True}
        except Exception as e:
            _logger.warning("TCRM AI clear_session: %s", e)
            return {'ok': False}

    @http.route('/tcrm_ai/export', type='http', auth='user', methods=['POST'], csrf=False)
    def export(self, **kw):
        """Export AI chat tables as Excel, HTML, or PDF. POST body: JSON { format, tables: [{headers,[], rows:[[]]}], title }."""
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
                    _('No table data to export. Ask the AI a question that returns data first.'),
                    headers=[('Content-Type', 'text/plain; charset=utf-8')],
                    status=400,
                )
            if fmt == 'xlsx':
                return self._export_xlsx(tables_data, title)
            if fmt == 'html':
                return self._export_html(tables_data, title)
            if fmt == 'pdf':
                return self._export_pdf(tables_data, title)
            return request.make_response('Unknown format: %s' % fmt, status=400)
        except Exception as e:
            _logger.exception("TCRM AI export failed")
            return request.make_response(str(e), status=500)

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
                for col_idx, cell in enumerate(row if isinstance(row, (list, tuple)) else [row.get(h, '') for h in headers]):
                    worksheet.write(row_idx, col_idx, str(cell) if cell is not None else '')
            worksheet.set_column(0, max(0, len(headers) - 1), 18)
        workbook.close()
        xlsx_data = output.getvalue()
        filename = (title or 'tcrm_ai_export').replace(' ', '_') + '.xlsx'
        return request.make_response(
            xlsx_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ],
        )

    def _export_html(self, tables_data, title):
        parts = ['<!DOCTYPE html><html><head><meta charset="utf-8"><title>%s</title>' % (title or 'Report'), '</head><body>']
        parts.append('<h1>%s</h1>' % (title or 'TCRM AI Report'))
        for tbl in tables_data:
            headers = tbl.get('headers') or []
            rows = tbl.get('rows') or []
            parts.append('<table border="1" cellpadding="6" style="border-collapse:collapse; margin:1em 0;">')
            parts.append('<thead><tr>')
            for h in headers:
                parts.append('<th>%s</th>' % (str(h).replace('<', '&lt;')))
            parts.append('</tr></thead><tbody>')
            for row in rows:
                parts.append('<tr>')
                for cell in (row if isinstance(row, (list, tuple)) else [row.get(h, '') for h in headers]):
                    parts.append('<td>%s</td>' % (str(cell).replace('<', '&lt;') if cell is not None else ''))
                parts.append('</tr>')
            parts.append('</tbody></table>')
        parts.append('</body></html>')
        html = ''.join(parts)
        return request.make_response(
            html,
            headers=[('Content-Type', 'text/html; charset=utf-8')],
        )

    def _export_pdf(self, tables_data, title):
        # Return HTML; user can use browser Print > Save as PDF
        return self._export_html(tables_data, title)
