from odoo import models, fields, api
import os
import requests
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Basic Meta fields
    meta_leadgen_id = fields.Char(string='Meta Leadgen ID', index=True)
    meta_page_id = fields.Char(string='Meta Page ID', index=True)
    meta_form_id = fields.Char(string='Meta Form ID', index=True)
    meta_raw_payload = fields.Text(string='Meta Raw Payload')
    meta_submitted_on = fields.Datetime(string='Submitted On', help='When the lead form was submitted on Meta/Facebook')
    
    # Campaign tracking fields
    meta_campaign_id = fields.Char(string='Meta Campaign ID', index=True)
    meta_campaign_name = fields.Char(string='Meta Campaign Name')
    meta_adset_id = fields.Char(string='Meta Ad Set ID', index=True)
    meta_adset_name = fields.Char(string='Meta Ad Set Name')
    meta_ad_id = fields.Char(string='Meta Ad ID', index=True)
    meta_ad_name = fields.Char(string='Meta Ad Name')
    meta_medium = fields.Char(string='Medium', default='facebook_ads')
    meta_source = fields.Char(string='Source', default='facebook')
    meta_platform = fields.Char(string='Platform', help='Instagram or Facebook')
    
    # Form data
    meta_form_answers = fields.Text(string='Form Answers', help='Client\'s complete form responses')
    
    # Ad Creative fields
    meta_creative_id = fields.Char(string='Creative ID', index=True)
    meta_creative_type = fields.Selection([
        ('image', 'Image'),
        ('video', 'Video'),
        ('carousel', 'Carousel'),
        ('collection', 'Collection')
    ], string='Creative Type')
    meta_creative_media_url = fields.Char(string='Creative Media URL', help='Direct URL to creative image or video thumbnail')
    meta_creative_body = fields.Text(string='Ad Body Text')
    meta_creative_title = fields.Char(string='Ad Title')
    meta_creative_cta = fields.Char(string='Call to Action')
    meta_creative_preview = fields.Html(string='Creative Preview', help='Formatted preview of the ad creative', compute='_compute_creative_preview', store=True)
    
    # Legacy field for compatibility
    meta_ad_creative = fields.Html(string='Ad Creative Preview (Legacy)', help='Visual preview of the ad creative content')

    @api.depends('meta_creative_media_url', 'meta_creative_body', 'meta_creative_title', 'meta_creative_cta', 'meta_ad_name', 'meta_creative_type')
    def _compute_creative_preview(self):
        """Compute formatted creative preview"""
        for lead in self:
            if not any([lead.meta_creative_media_url, lead.meta_creative_body, lead.meta_ad_name]):
                lead.meta_creative_preview = False
                continue
                
            # Build creative preview HTML
            html_parts = []
            
            # Header
            html_parts.append('''
            <div style="border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 8px 0; background: #fff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            ''')
            
            # Ad name
            if lead.meta_ad_name:
                html_parts.append(f'''
                <div style="background: #f8f9fa; padding: 12px; border-radius: 6px; margin-bottom: 12px; border-left: 3px solid #007bff;">
                    <strong style="color: #007bff;">📱 {lead.meta_ad_name}</strong>
                </div>
                ''')
            
            # Media preview
            if lead.meta_creative_media_url:
                media_type = lead.meta_creative_type or 'image'
                if media_type == 'video':
                    html_parts.append(f'''
                    <div style="text-align: center; margin-bottom: 12px;">
                        <div style="position: relative; display: inline-block;">
                            <img src="{lead.meta_creative_media_url}" style="max-width: 300px; max-height: 200px; border-radius: 6px; border: 1px solid #ddd;" alt="Video Thumbnail"/>
                            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.7); border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;">
                                <span style="color: white; font-size: 16px;">▶️</span>
                            </div>
                        </div>
                        <div style="font-size: 12px; color: #6c757d; margin-top: 4px;">🎬 Video Creative</div>
                    </div>
                    ''')
                else:
                    html_parts.append(f'''
                    <div style="text-align: center; margin-bottom: 12px;">
                        <img src="{lead.meta_creative_media_url}" style="max-width: 300px; max-height: 200px; border-radius: 6px; border: 1px solid #ddd;" alt="Ad Creative"/>
                        <div style="font-size: 12px; color: #6c757d; margin-top: 4px;">🖼️ Image Creative</div>
                    </div>
                    ''')
            
            # Title
            if lead.meta_creative_title:
                html_parts.append(f'''
                <div style="font-weight: bold; font-size: 16px; color: #333; margin-bottom: 8px;">
                    {lead.meta_creative_title}
                </div>
                ''')
            
            # Body text
            if lead.meta_creative_body:
                html_parts.append(f'''
                <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-bottom: 10px; line-height: 1.4;">
                    {lead.meta_creative_body}
                </div>
                ''')
            
            # Call to action
            if lead.meta_creative_cta:
                html_parts.append(f'''
                <div style="text-align: center; margin-top: 12px;">
                    <span style="background: #007bff; color: white; padding: 8px 16px; border-radius: 20px; font-size: 13px; font-weight: 600;">
                        {lead.meta_creative_cta.replace('_', ' ').title()}
                    </span>
                </div>
                ''')
            
            # Footer
            html_parts.append('''
            <div style="border-top: 1px solid #dee2e6; margin-top: 12px; padding-top: 8px; text-align: center;">
                <small style="color: #6c757d;">📊 Meta Ad Creative Preview</small>
            </div>
            </div>
            ''')
            
            lead.meta_creative_preview = ''.join(html_parts)

    def action_refresh_ad_creative(self):
        """Action to manually refresh ad creative data"""
        self.ensure_one()
        
        if not self.meta_ad_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Ad ID',
                    'message': 'This lead does not have a Meta Ad ID to fetch creative data.',
                    'type': 'warning'
                }
            }
        
        # Get access token
        access_token = os.environ.get('META_USER_ACCESS_TOKEN')
        if not access_token:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Access Token Missing',
                    'message': 'Meta access token is not configured. Please check your environment variables.',
                    'type': 'warning'
                }
            }
        
        try:
            # Fetch ad creative data
            creative_data = self._fetch_ad_creative_from_meta(self.meta_ad_id, access_token)
            
            if creative_data:
                # Update the lead with creative data
                self.write(creative_data)
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success!',
                        'message': 'Ad creative data has been refreshed successfully.',
                        'type': 'success'
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Data Found',
                        'message': 'Could not fetch ad creative data. The ad may no longer exist or you may not have permissions.',
                        'type': 'warning'
                    }
                }
                
        except Exception as e:
            _logger.error(f"Error refreshing ad creative: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Error fetching ad creative: {str(e)}',
                    'type': 'danger'
                }
            }

    def _fetch_ad_creative_from_meta(self, ad_id, access_token):
        """Fetch ad creative data from Meta Graph API"""
        try:
            # Get ad data
            ad_url = f"https://graph.facebook.com/v24.0/{ad_id}"
            ad_params = {
                'access_token': access_token,
                'fields': 'id,name,status,creative{id,object_story_spec,image_url,video_id,thumbnail_url}'
            }
            
            ad_response = requests.get(ad_url, params=ad_params, timeout=10)
            if ad_response.status_code != 200:
                _logger.error(f"Error fetching ad: {ad_response.status_code} - {ad_response.text}")
                return None
                
            ad_data = ad_response.json()
            creative_info = ad_data.get('creative', {})
            
            update_data = {
                'meta_ad_name': ad_data.get('name'),
            }
            
            # If we have creative data, get more details
            if creative_info.get('id'):
                creative_id = creative_info['id']
                creative_url = f"https://graph.facebook.com/v24.0/{creative_id}"
                creative_params = {
                    'access_token': access_token,
                    'fields': 'id,name,object_story_spec,image_url,video_id,thumbnail_url,body,title'
                }
                
                creative_response = requests.get(creative_url, params=creative_params, timeout=10)
                if creative_response.status_code == 200:
                    creative_data = creative_response.json()
                    
                    # Get media URL
                    media_url = None
                    creative_type = 'image'
                    
                    if creative_data.get('video_id'):
                        creative_type = 'video'
                        # Try to get video thumbnail
                        media_url = self._get_video_thumbnail_from_meta(creative_data['video_id'], access_token)
                    elif creative_data.get('image_url'):
                        media_url = creative_data['image_url']
                    elif creative_data.get('thumbnail_url'):
                        media_url = creative_data['thumbnail_url']
                    
                    # Extract call-to-action
                    cta = ""
                    story_spec = creative_data.get('object_story_spec', {})
                    if story_spec.get('page_post_data', {}).get('call_to_action'):
                        cta = story_spec['page_post_data']['call_to_action'].get('type', '')
                    
                    update_data.update({
                        'meta_creative_id': creative_data.get('id'),
                        'meta_creative_type': creative_type,
                        'meta_creative_media_url': media_url,
                        'meta_creative_body': creative_data.get('body'),
                        'meta_creative_title': creative_data.get('title'),
                        'meta_creative_cta': cta,
                    })
            
            return update_data
            
        except Exception as e:
            _logger.error(f"Exception fetching ad creative: {str(e)}")
            return None

    def _get_video_thumbnail_from_meta(self, video_id, access_token):
        """Get video thumbnail URL from Meta"""
        try:
            video_url = f"https://graph.facebook.com/v24.0/{video_id}"
            video_params = {
                'access_token': access_token,
                'fields': 'thumbnails.limit(1){uri},picture'
            }
            
            response = requests.get(video_url, params=video_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Try thumbnails first
                thumbnails = data.get('thumbnails', {}).get('data', [])
                if thumbnails:
                    return thumbnails[0].get('uri')
                
                # Fallback to picture
                return data.get('picture')
            
            return None
            
        except Exception as e:
            _logger.error(f"Error fetching video thumbnail: {str(e)}")
            return None
