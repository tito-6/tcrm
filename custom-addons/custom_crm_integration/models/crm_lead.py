from odoo import models, fields, api
import requests
import os
import logging
from ..services.meta_creative_service import MetaCreativeService

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Meta lead data fields
    meta_form_id = fields.Char(string='Meta Form ID', readonly=True)
    meta_ad_id = fields.Char(string='Meta Ad ID', readonly=True)
    meta_ad_name = fields.Char(string='Meta Ad Name', readonly=True)
    meta_leadgen_id = fields.Char(string='Meta Leadgen ID', readonly=True)
    meta_page_id = fields.Char(string='Meta Page ID', readonly=True)
    meta_campaign_id = fields.Char(string='Meta Campaign ID', readonly=True)
    meta_campaign_name = fields.Char(string='Campaign', readonly=True)
    meta_adset_id = fields.Char(string='Meta Adset ID', readonly=True)
    meta_adset_name = fields.Char(string='Ad Set', readonly=True)
    meta_platform = fields.Selection([
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('messenger', 'Messenger')
    ], string='Platform', readonly=True)
    
    # Submission timestamp
    submitted_on = fields.Datetime(string='Submitted On', readonly=True, help='Date and time when the lead was submitted on Facebook')
    
    # Computed field for form answers display
    form_answers_display = fields.Html(
        string='Form Answers',
        compute='_compute_form_answers_display',
        store=False
    )
    
    # Creative fields
    meta_creative_id = fields.Char(string='Creative ID', readonly=True)
    meta_creative_type = fields.Char(string='Creative Type', readonly=True)
    meta_creative_media_url = fields.Char(string='Creative Media URL', readonly=True)
    meta_creative_body = fields.Text(string='Creative Body', readonly=True)
    meta_creative_title = fields.Char(string='Creative Title', readonly=True)
    meta_creative_cta = fields.Char(string='Creative CTA', readonly=True)
    
    # Enhanced creative fields for high-resolution fetching
    meta_creative_high_res_url = fields.Char(string='High Resolution Image URL', readonly=True, store=True)
    meta_creative_video_embed_html = fields.Text(string='Video Embed HTML', readonly=True, store=True)
    meta_creative_effective_story_id = fields.Char(string='Effective Story ID', readonly=True, store=True)
    meta_creative_asset_feed_spec = fields.Text(string='Asset Feed Spec (JSON)', readonly=True, store=True)
    meta_creative_fetch_method = fields.Char(string='Fetch Method Used', readonly=True, store=True)
    meta_creative_resolution_quality = fields.Selection([
        ('low', 'Low Resolution'),
        ('medium', 'Medium Resolution'), 
        ('high', 'High Resolution'),
        ('ultra', 'Ultra High Resolution')
    ], string='Media Quality', readonly=True, store=True)
    meta_creative_fetch_error = fields.Text(string='Fetch Error Details', readonly=True, store=True)
    
    # Computed preview field
    meta_creative_preview = fields.Html(
        string='Creative Preview',
        compute='_compute_creative_preview',
        store=False
    )

    @api.depends('description')
    def _compute_form_answers_display(self):
        """Extract and format form answers from description for better display"""
        for record in self:
            if not record.description:
                record.form_answers_display = False
                continue
            
            # Parse description to extract form answers
            lines = record.description.split('\n')
            form_answers = []
            in_answers_section = False
            
            for line in lines:
                if 'Form Answers:' in line:
                    in_answers_section = True
                    continue
                
                if in_answers_section and line.strip().startswith('•'):
                    # Extract field and value
                    answer = line.strip()[1:].strip()  # Remove bullet point
                    if ':' in answer:
                        parts = answer.split(':', 1)
                        field_name = parts[0].strip()
                        field_value = parts[1].strip()
                        
                        # Clean up field names (remove underscores, Turkish characters issues)
                        field_name_clean = field_name.replace('_', ' ').replace('�', 'İ').title()
                        
                        # Determine if it's a contact field
                        field_lower = field_name.lower()
                        icon = '📧'
                        if 'phone' in field_lower or 'telefon' in field_lower or 'numara' in field_lower:
                            icon = '📱'
                        elif 'email' in field_lower or 'posta' in field_lower:
                            icon = '📧'
                        elif 'name' in field_lower or 'ad' in field_lower or 'soyad' in field_lower:
                            icon = '👤'
                        else:
                            icon = '💬'
                        
                        form_answers.append((icon, field_name_clean, field_value))
            
            if form_answers:
                html = ['<div style=\"padding: 10px; background: #f8f9fa; border-radius: 8px;\">']
                
                for icon, field, value in form_answers:
                    html.append(f'''
                        <div style=\"margin-bottom: 12px; padding: 8px; background: white; border-left: 3px solid #1877f2; border-radius: 4px;\">
                            <div style=\"display: flex; align-items: start;\">
                                <span style=\"font-size: 20px; margin-right: 10px;\">{icon}</span>
                                <div style=\"flex: 1;\">
                                    <strong style=\"color: #555; font-size: 12px; text-transform: uppercase;\">{field}</strong>
                                    <div style=\"color: #333; font-size: 14px; margin-top: 4px;\">{value}</div>
                                </div>
                            </div>
                        </div>
                    ''')
                
                html.append('</div>')
                record.form_answers_display = ''.join(html)
            else:
                record.form_answers_display = '<p style=\"color: #999; font-style: italic;\">No form answers available</p>'

    @api.depends('meta_creative_id', 'meta_creative_high_res_url', 'meta_creative_media_url', 
                 'meta_creative_title', 'meta_creative_body', 'meta_creative_cta', 'meta_creative_type',
                 'meta_creative_video_embed_html', 'meta_creative_resolution_quality')
    def _compute_creative_preview(self):
        """Generate HTML preview of the ad creative with high-resolution support"""
        """Generate HTML preview of the ad creative with high-resolution support"""
        for record in self:
            if not record.meta_creative_id:
                record.meta_creative_preview = '<p style="color: #666; font-style: italic;">This lead does not have Meta creative data.</p>'
                continue
            
            preview_html = []
            preview_html.append('<div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; max-width: 500px; margin: 10px 0;">')
            
            # Quality indicator badge
            if record.meta_creative_resolution_quality:
                quality_colors = {
                    'ultra': '#28a745',  # Green
                    'high': '#17a2b8',   # Blue  
                    'medium': '#ffc107', # Yellow
                    'low': '#dc3545'     # Red
                }
                quality_color = quality_colors.get(record.meta_creative_resolution_quality, '#6c757d')
                preview_html.append(f'''
                    <div style="margin-bottom: 10px;">
                        <span style="background: {quality_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                            {record.meta_creative_resolution_quality.upper()} QUALITY
                        </span>
                        {f'<span style="color: #666; font-size: 11px; margin-left: 10px;">via {record.meta_creative_fetch_method}</span>' if record.meta_creative_fetch_method else ''}
                    </div>
                ''')
            
            # Media section with enhanced handling
            media_url = record.meta_creative_high_res_url or record.meta_creative_media_url
            
            if record.meta_creative_type == 'video' and record.meta_creative_video_embed_html:
                # Use embed HTML for videos when available
                preview_html.append(f'''
                    <div style="margin-bottom: 15px;">
                        {record.meta_creative_video_embed_html}
                    </div>
                ''')
            elif record.meta_creative_type == 'video' and media_url:
                # Fallback video display with poster
                preview_html.append(f'''
                    <div style="margin-bottom: 15px;">
                        <div style="position: relative; background-image: url('{media_url}'); background-size: cover; background-position: center; width: 100%; height: 200px; border-radius: 4px; display: flex; align-items: center; justify-content: center;">
                            <div style="background: rgba(0,0,0,0.7); color: white; padding: 10px 15px; border-radius: 20px;">
                                <i style="font-size: 20px;">▶️ Video Creative</i>
                            </div>
                        </div>
                    </div>
                ''')
            elif media_url:
                # High-resolution image display
                preview_html.append(f'''
                    <div style="margin-bottom: 15px;">
                        <img src="{media_url}" 
                             style="width: 100%; max-width: 100%; max-height: 400px; object-fit: cover; border-radius: 4px;" 
                             alt="High Resolution Creative"
                             loading="lazy">
                    </div>
                ''')
            
            # Title
            if record.meta_creative_title:
                preview_html.append(f'<h3 style="margin: 0 0 10px 0; font-size: 18px; font-weight: bold; color: #333;">{record.meta_creative_title}</h3>')
            
            # Body
            if record.meta_creative_body:
                preview_html.append(f'<p style="margin: 10px 0; color: #555; line-height: 1.4;">{record.meta_creative_body}</p>')
            
            # CTA
            if record.meta_creative_cta:
                preview_html.append(f'''
                    <div style="text-align: center; margin-top: 15px;">
                        <button style="background: #1877f2; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-weight: bold; cursor: not-allowed;" disabled>
                            {record.meta_creative_cta}
                        </button>
                    </div>
                ''')
            
            preview_html.append('</div>')
            
            # Enhanced creative details
            preview_html.append('<div style="margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 4px;">')
            preview_html.append('<small style="color: #666;">')
            preview_html.append(f'<strong>Creative ID:</strong> {record.meta_creative_id}<br>')
            if record.meta_creative_type:
                preview_html.append(f'<strong>Type:</strong> {record.meta_creative_type.title()}<br>')
            if record.meta_creative_effective_story_id:
                preview_html.append(f'<strong>Story ID:</strong> {record.meta_creative_effective_story_id}<br>')
            if record.meta_creative_fetch_method:
                preview_html.append(f'<strong>Fetch Method:</strong> {record.meta_creative_fetch_method.replace("_", " ").title()}<br>')
            preview_html.append('</small>')
            preview_html.append('</div>')
            
            record.meta_creative_preview = ''.join(preview_html)

    def action_refresh_ad_creative(self):
        """
        Advanced Meta Creative Refresh using production-ready high-resolution fetching
        
        Implements comprehensive waterfall strategy based on Meta's official documentation:
        1. Direct creative high-res image_url analysis
        2. object_story_spec link_data.picture extraction  
        3. effective_object_story_id Page Post fallback
        4. asset_feed_spec dynamic ad asset parsing
        5. AdImage endpoint via hash for maximum resolution
        6. Video embed_html + high-res poster extraction
        """
        if not self.meta_ad_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No Meta Ad ID found for this lead',
                    'type': 'warning',
                }
            }
        
        try:
            # Get access token from environment
            access_token = os.environ.get('META_USER_ACCESS_TOKEN')
            if not access_token:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Meta access token not configured',
                        'type': 'warning',
                    }
                }
            
            # Initialize the advanced Meta Creative Service
            creative_service = MetaCreativeService(access_token)
            
            # Step 1: Fetch ad to get creative ID
            ad_url = f"https://graph.facebook.com/v21.0/{self.meta_ad_id}"
            ad_params = {
                'access_token': access_token,
                'fields': 'id,name,status,creative{id}'
            }
            
            _logger.info(f"Fetching ad data for {self.meta_ad_id}")
            response = requests.get(ad_url, params=ad_params, timeout=15)
            response.raise_for_status()
            
            ad_data = response.json()
            creative = ad_data.get('creative', {})
            creative_id = creative.get('id')
            
            if not creative_id:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'No creative found for this ad',
                        'type': 'warning',
                    }
                }
            
            # Step 2: Use advanced service to fetch high-resolution creative
            _logger.info(f"Fetching high-resolution creative for {creative_id}")
            creative_result = creative_service.fetch_high_resolution_creative(
                self.meta_ad_id, creative_id
            )
            
            if not creative_result['success']:
                error_msg = creative_result.get('error', 'Unknown error occurred')
                _logger.error(f"META FETCH FAILED for Lead {self.id}: {error_msg}")
                
                # Store error details on the lead record for user visibility
                self.write({
                    'meta_creative_fetch_error': f"Failed at {fields.Datetime.now()}: {error_msg}",
                    'meta_creative_fetch_method': 'failed',
                    'meta_creative_resolution_quality': False
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Creative Fetch Failed',
                        'message': f'Error: {error_msg}\n\nCheck the Meta Creative tab for details.',
                        'type': 'danger',
                    }
                }
            
            # Step 3: Update lead with comprehensive creative data
            update_values = {
                'meta_creative_id': creative_id,
                'meta_creative_media_url': creative_result.get('media_url'),
                'meta_creative_high_res_url': creative_result.get('media_url') if creative_result.get('quality') in ['high', 'ultra'] else None,
                'meta_creative_video_embed_html': creative_result.get('video_embed_html'),
                'meta_creative_title': creative_result.get('title'),
                'meta_creative_body': creative_result.get('body'),
                'meta_creative_cta': creative_result.get('cta_type'),
                'meta_creative_effective_story_id': creative_result.get('effective_story_id'),
                'meta_creative_asset_feed_spec': creative_result.get('asset_feed_spec'),
                'meta_creative_fetch_method': creative_result.get('fetch_method'),
                'meta_creative_resolution_quality': creative_result.get('quality'),
                'meta_creative_type': 'video' if creative_result.get('video_embed_html') else 'image',
                'meta_creative_fetch_error': False  # Clear any previous errors
            }
            
            # Filter out None values but keep False values (to clear fields)
            update_values = {k: v for k, v in update_values.items() if v is not None}
            
            if update_values:
                self.write(update_values)
                _logger.info(f"META FETCH SUCCESS for Lead {self.id}: method={creative_result.get('fetch_method')} quality={creative_result.get('quality')}")
                
                # Force recompute of preview field
                self._compute_creative_preview()
            
            # Prepare success message with quality information
            quality = creative_result.get('quality', 'unknown')
            method = creative_result.get('fetch_method', 'unknown').replace('_', ' ').title()
            
            message = f'High-resolution creative fetched successfully!\n'
            message += f'Quality: {quality.upper()}\n'
            message += f'Method: {method}\n'
            message += f'Media URL: {"✅ Found" if creative_result.get("media_url") else "❌ Missing"}'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Creative Refresh Complete',
                    'message': message,
                    'type': 'success',
                }
            }
        
        except requests.exceptions.RequestException as e:
            _logger.error(f"Network error fetching creative: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Network error: {str(e)}',
                    'type': 'danger',
                }
            }
        except Exception as e:
            _logger.error(f"Unexpected error in creative refresh: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Error: {str(e)}',
                    'type': 'danger',
                }
            }