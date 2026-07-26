# -*- coding: utf-8 -*-
import base64
import json
import re

from tcrm import http
from tcrm.http import request


class PropertioReportsCenterController(http.Controller):

    @http.route('/propertio/reports/export/<string:report_key>/<string:fmt>', type='http', auth='user')
    def export_report(self, report_key, fmt, filters=None, options=None, **kwargs):
        def decode(value):
            if not value:
                return {}
            try:
                padding = '=' * (-len(value) % 4)
                return json.loads(base64.urlsafe_b64decode((value + padding).encode('ascii')).decode('utf-8'))
            except Exception:
                return {}

        engine = request.env['propertio.report.engine']
        content, content_type, extension = engine.export_bytes(report_key, fmt, decode(filters), decode(options))
        clean_name = re.sub(r'[^A-Za-z0-9_.-]+', '_', report_key).strip('_') or 'propertio_report'
        return request.make_response(
            content,
            headers=[
                ('Content-Type', content_type),
                ('Content-Disposition', 'attachment; filename="%s.%s"' % (clean_name, extension)),
            ],
        )
