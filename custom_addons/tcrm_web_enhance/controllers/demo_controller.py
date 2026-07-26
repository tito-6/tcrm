# -*- coding: utf-8 -*-
from tcrm import http
from tcrm.http import request

class DemoController(http.Controller):

    @http.route('/demo/request', type='http', auth="public", website=True)
    def demo_request(self, **kw):
        return request.render('tcrm_web_enhance.demo_request_form')

    @http.route('/demo/submit', type='http', auth="public", methods=['POST'], website=True, csrf=True)
    def demo_submit(self, **post):
        # Extract fields
        name = post.get('name')
        email = post.get('email')
        phone = post.get('phone')
        company = post.get('company')
        employees = post.get('employees')
        sector = post.get('sector')

        # Create CRM Lead
        if name and email:
            request.env['crm.lead'].sudo().create({
                'name': f"Demo Request: {company or name}",
                'contact_name': name,
                'email_from': email,
                'phone': phone,
                'partner_name': company,
                'description': f"Sector: {sector}\nEmployees: {employees}",
                'type': 'lead'
            })
            return request.render('tcrm_web_enhance.demo_request_thanks')
        
        return request.redirect('/demo/request')
