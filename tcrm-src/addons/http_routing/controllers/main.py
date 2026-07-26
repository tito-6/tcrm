# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import http
from tcrm.http import request
from tcrm.addons.web.controllers.home import Home
from tcrm.addons.web.controllers.session import Session
from tcrm.addons.web.controllers.webclient import WebClient


class Routing(Home):

    @http.route('/website/translations', type='http', auth="public", website=True, readonly=True, sitemap=False)
    def get_website_translations(self, hash=None, lang=None, mods=None):
        IrHttp = request.env['ir.http'].sudo()
        modules = IrHttp.get_translation_frontend_modules()
        if mods:
            modules += mods.split(',')
        return WebClient().translations(hash, mods=','.join(modules), lang=lang)


class SessionWebsite(Session):

    @http.route('/web/session/logout', website=True, multilang=False, sitemap=False)
    def logout(self, redirect='/tcrm'):
        return super().logout(redirect=redirect)
