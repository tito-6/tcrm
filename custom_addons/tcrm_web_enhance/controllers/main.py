# -*- coding: utf-8 -*-
from tcrm import http
from tcrm.addons.web.controllers.home import Home
from tcrm.http import request

class CustomHome(Home):
    def _login_redirect(self, uid, redirect=None):
        if (not redirect or redirect in ('/', '', '/tcrm', '/web', '/web/')) and request.env['res.users'].browse(uid)._is_internal():
            return '/web#action=1346&view_type=list'
        return super(CustomHome, self)._login_redirect(uid, redirect)

from tcrm.addons.account.controllers.portal import CustomerPortal

class CustomCustomerPortal(CustomerPortal):
    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        if request.env.user._is_internal():
            return request.redirect('/web#model=account.move&view_type=list')
        return super(CustomCustomerPortal, self).portal_my_invoices(page, date_begin, date_end, sortby, filterby, **kw)

    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_detail(self, invoice_id, access_token=None, report_type=None, download=False, **kw):
        if request.env.user._is_internal():
            return request.redirect(f'/web#id={invoice_id}&model=account.move&view_type=form')
        return super(CustomCustomerPortal, self).portal_my_invoice_detail(invoice_id, access_token, report_type, download, **kw)

