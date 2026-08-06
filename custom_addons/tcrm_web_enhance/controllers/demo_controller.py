# -*- coding: utf-8 -*-
from tcrm import http
from tcrm.http import request


class DemoController(http.Controller):

    @http.route('/demo/request', type='http', auth="public", website=True)
    def demo_request(self, **kw):
        return request.render('tcrm_web_enhance.demo_request_form')

    @http.route('/demo/submit', type='http', auth="public", methods=['POST'], website=True, csrf=True)
    def demo_submit(self, **post):
        name = (post.get('name') or '').strip()
        email = (post.get('email') or '').strip()
        phone = (post.get('phone') or '').strip()
        company = (post.get('company') or '').strip()
        employees = post.get('employees')
        sector = post.get('sector')

        if name and email:
            Lead = request.env['crm.lead'].sudo()
            vals = {
                'name': f"Demo Request: {company or name}",
                'contact_name': name,
                'email_from': email,
                'phone': phone or False,
                'partner_name': company or False,
                'description': f"Sector: {sector}\nEmployees: {employees}\nSource: akod.tcrm.online /demo/request",
                'type': 'lead',
            }
            if 'source_id' in Lead._fields:
                source = request.env['utm.source'].sudo().search(
                    [('name', '=', 'TCRM Demo Form')], limit=1
                )
                if not source:
                    source = request.env['utm.source'].sudo().create({'name': 'TCRM Demo Form'})
                vals['source_id'] = source.id
            Lead.create(vals)
            return request.render('tcrm_web_enhance.demo_request_thanks')

        return request.redirect('/demo/request')
