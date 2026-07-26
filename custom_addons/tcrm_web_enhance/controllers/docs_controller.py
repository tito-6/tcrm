# -*- coding: utf-8 -*-
from tcrm import http
from tcrm.http import request

class DocsController(http.Controller):

    @http.route('/docs', type='http', auth="public", website=True)
    def docs_index(self, **kw):
        return request.render('tcrm_web_enhance.docs_index_template')

    @http.route('/docs/propertio', type='http', auth="public", website=True)
    def docs_propertio(self, **kw):
        return request.render('tcrm_web_enhance.docs_propertio_template')

    @http.route('/docs/crm', type='http', auth="public", website=True)
    def docs_crm(self, **kw):
        return request.render('tcrm_web_enhance.docs_crm_template')

    @http.route('/docs/santral', type='http', auth="public", website=True)
    def docs_santral(self, **kw):
        return request.render('tcrm_web_enhance.docs_santral_template')

    @http.route('/docs/marketing-hub', type='http', auth="public", website=True)
    def docs_marketing_hub(self, **kw):
        return request.render('tcrm_web_enhance.docs_marketing_hub_template')

    @http.route('/docs/ai', type='http', auth="public", website=True)
    def docs_ai(self, **kw):
        return request.render('tcrm_web_enhance.docs_ai_template')

    @http.route('/docs/vector-sync', type='http', auth="public", website=True)
    def docs_vector_sync(self, **kw):
        return request.render('tcrm_web_enhance.docs_vector_sync_template')

    @http.route('/docs/market-analysis', type='http', auth="public", website=True)
    def docs_market_analysis(self, **kw):
        return request.render('tcrm_web_enhance.docs_market_analysis_template')

    @http.route('/docs/whatsapp', type='http', auth="public", website=True)
    def docs_whatsapp(self, **kw):
        return request.render('tcrm_web_enhance.docs_whatsapp_template')
