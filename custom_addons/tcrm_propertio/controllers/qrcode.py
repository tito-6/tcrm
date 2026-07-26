# -*- coding: utf-8 -*-
from tcrm import http
from tcrm.http import request
import io
import base64


class PropertioQRCodeController(http.Controller):

    @http.route('/propertio/unit/qr/<int:unit_id>', type='http', auth='user')
    def unit_qr_image(self, unit_id, **kw):
        """Return QR code image for unit - links to unit form."""
        try:
            import qrcode
        except ImportError:
            return request.not_found()
        base_url = request.httprequest.host_url.rstrip('/')
        unit = request.env['propertio.unit'].browse(unit_id)
        if not unit.exists():
            return request.not_found()
        url = '%s/web#id=%s&model=propertio.unit&view_type=form' % (base_url, unit_id)
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return request.make_response(
            buf.getvalue(),
            headers=[
                ('Content-Type', 'image/png'),
                ('Content-Disposition', 'inline; filename=unit-%s-qr.png' % (unit.name or unit_id)),
            ])
