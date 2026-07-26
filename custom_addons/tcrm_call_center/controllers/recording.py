# -*- coding: utf-8 -*-
"""Protected recording playback (no direct Twilio URL to browser)."""
from __future__ import annotations

import logging

from tcrm import http, _
from tcrm.exceptions import AccessError, UserError
from tcrm.http import request
from werkzeug.wrappers import Response

_logger = logging.getLogger(__name__)


class SantralRecordingController(http.Controller):

    @http.route(
        '/tcrm/call/recording/<int:record_id>',
        type='http', auth='user', methods=['GET'], csrf=False,
    )
    def play_recording(self, record_id, download=0, **kwargs):
        env = request.env
        # 404 for cross-tenant / missing — do not disclose existence.
        recording = env['tcrm.call.recording'].browse(int(record_id))
        try:
            if not recording.exists():
                return Response(status=404)
            if bool(int(download or 0)):
                recording._check_download_access()
            else:
                recording._check_playback_access()
            content, ctype = recording.get_media_bytes()
            recording.audit_playback()
        except (AccessError, UserError):
            return Response(status=404)
        except Exception:
            _logger.exception('Santral playback failed recording_id=%s', record_id)
            return Response(status=404)

        headers = {
            'Content-Type': ctype or 'audio/mpeg',
            'Content-Length': str(len(content)),
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'private, no-store',
            'X-Content-Type-Options': 'nosniff',
        }
        if bool(int(download or 0)):
            headers['Content-Disposition'] = 'attachment; filename="santral-%s.mp3"' % record_id
        else:
            headers['Content-Disposition'] = 'inline'

        # Basic Range support
        range_header = request.httprequest.headers.get('Range')
        if range_header and range_header.startswith('bytes='):
            try:
                unit, rng = range_header.split('=', 1)
                start_s, end_s = (rng.split('-') + [''])[:2]
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else (len(content) - 1)
                end = min(end, len(content) - 1)
                chunk = content[start:end + 1]
                headers['Content-Length'] = str(len(chunk))
                headers['Content-Range'] = 'bytes %s-%s/%s' % (start, end, len(content))
                return Response(chunk, status=206, headers=headers)
            except Exception:
                pass
        return Response(content, status=200, headers=headers)
