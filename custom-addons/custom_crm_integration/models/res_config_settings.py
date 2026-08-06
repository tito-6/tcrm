# -*- coding: utf-8 -*-
try:
    from tcrm import models, fields, api
except ImportError:
    from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Meta/Facebook Lead Integration Settings
    meta_user_access_token = fields.Char(
        string='Facebook User Access Token',
        config_parameter='custom_crm_integration.meta_user_access_token',
        help='Long-lived user access token from Facebook Graph API'
    )
    
    meta_page_id = fields.Char(
        string='Facebook Page ID',
        config_parameter='custom_crm_integration.meta_page_id',
        default='542033395659747',
        help='Facebook Page ID to fetch leads from (e.g., QUEEN VILLA: 542033395659747)'
    )
    
    meta_pixel_id = fields.Char(
        string='Meta Pixel / Dataset ID',
        config_parameter='meta_leads.pixel_id',
        default='1562341125588143',
        help='Meta Dataset/Pixel ID for Conversion API (CAPI) events'
    )
    
    meta_auto_fetch_enabled = fields.Boolean(
        string='Enable Automatic Lead Fetching',
        config_parameter='custom_crm_integration.meta_auto_fetch_enabled',
        default=True,
        help='Automatically fetch new leads every 2 minutes'
    )
    
    meta_last_fetch_time = fields.Datetime(
        string='Last Fetch Time',
        config_parameter='custom_crm_integration.meta_last_fetch_time',
        readonly=True
    )
    
    meta_total_leads_fetched = fields.Integer(
        string='Total Leads Fetched',
        config_parameter='custom_crm_integration.meta_total_leads_fetched',
        readonly=True
    )

    def set_values(self):
        super().set_values()
        if self.meta_user_access_token:
            self.env['ir.config_parameter'].sudo().set_param('meta_leads.access_token', self.meta_user_access_token)

    def action_fetch_meta_leads_now(self):
        """Manually trigger lead fetch"""
        self.ensure_one()
        
        # Get the lead service
        LeadFetcher = self.env['crm.lead.fetcher']
        
        try:
            result = LeadFetcher.fetch_leads_from_meta()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lead Fetch Complete',
                    'message': f"Successfully fetched {result.get('new_leads', 0)} new leads!",
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Manual lead fetch failed: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lead Fetch Failed',
                    'message': f"Error: {str(e)}",
                    'type': 'danger',
                    'sticky': True,
                }
            }
