# -*- coding: utf-8 -*-
from tcrm import http
from tcrm.http import request

from ..reports.report_i18n import t


class PropertioReportShareController(http.Controller):
    """Serve Propertio reports as real HTML pages (not raw/JSON binary dumps)."""

    def _html_response(self, html: str, *, status: int = 200):
        return request.make_response(
            html,
            headers=[
                ('Content-Type', 'text/html; charset=utf-8'),
                ('X-Content-Type-Options', 'nosniff'),
                ('Cache-Control', 'no-store'),
            ],
            status=status,
        )

    def _closed_page(self):
        msg = t('This report link has been closed or is invalid.')
        return self._html_response(
            f'<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">'
            f'<title>{msg}</title></head>'
            f'<body style="font-family:sans-serif;padding:40px;color:#4a5568;">'
            f'<h2>{msg}</h2></body></html>',
            status=404,
        )

    @http.route(
        '/propertio/r/<string:token>',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        readonly=True,
    )
    def public_report(self, token, **kwargs):
        """Public shareable report — no login required when is_public + active."""
        share = request.env['propertio.report.share'].sudo().search([
            ('access_token', '=', token),
            ('active', '=', True),
            ('is_public', '=', True),
        ], limit=1)
        if not share:
            return self._closed_page()
        return self._html_response(share.html_content or '')

    @http.route(
        '/propertio/report/view/<int:share_id>',
        type='http',
        auth='user',
        methods=['GET'],
        csrf=False,
        readonly=True,
    )
    def private_report_view(self, share_id, token=None, **kwargs):
        """Logged-in view of a generated report (always text/html)."""
        share = request.env['propertio.report.share'].browse(share_id)
        if not share.exists() or not share.active:
            return self._closed_page()
        if token and share.access_token != token:
            return self._closed_page()
        try:
            share.check_access_rights('read')
            share.check_access_rule('read')
        except Exception:
            return request.not_found()
        return self._html_response(share.html_content or '')
