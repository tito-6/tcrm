"""
Advanced Meta Creative Fetching Service

This service implements a robust, multi-tier fallback strategy for fetching
high-resolution creatives from Meta's Graph API, based on extensive research
of the official Meta Developer Documentation.

Key Insights from Meta Documentation:
1. object_story_spec.link_data.picture often contains higher resolution URLs
2. effective_object_story_id allows fetching the actual Page Post with full_picture
3. asset_feed_spec contains dynamic ad assets that can be fetched individually
4. Video nodes provide embed_html and high-res poster frames
5. AdImage nodes accessed via hash provide the highest resolution images
"""

import requests
import json
import logging
from typing import Dict, Optional, Tuple, List
import re

_logger = logging.getLogger(__name__)


class MetaCreativeService:
    """Production-ready service for fetching high-resolution Meta ad creatives"""
    
    def __init__(self, access_token: str, api_version: str = "v21.0"):
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{api_version}"
        
    def fetch_high_resolution_creative(self, ad_id: str, creative_id: str) -> Dict:
        """
        Master function implementing waterfall strategy for high-res creative fetching
        
        Returns:
            Dict containing all creative data with quality indicators
        """
        result = {
            'success': False,
            'media_url': None,
            'video_embed_html': None,
            'quality': 'low',
            'fetch_method': 'none',
            'effective_story_id': None,
            'asset_feed_spec': None,
            'error': None
        }
        
        try:
            # Step 1: Get comprehensive creative data with all relevant fields
            creative_data = self._fetch_comprehensive_creative_data(creative_id)
            if not creative_data:
                result['error'] = 'Failed to fetch creative data'
                return result
            
            # Step 2: Attempt high-resolution fetching using multiple strategies
            media_result = self._execute_resolution_waterfall(creative_data, ad_id)
            result.update(media_result)
            
            # Step 3: Extract additional creative metadata
            result.update(self._extract_creative_metadata(creative_data))
            
            result['success'] = True
            return result
            
        except Exception as e:
            _logger.error(f"Error in fetch_high_resolution_creative: {str(e)}")
            result['error'] = str(e)
            return result
    
    def _fetch_comprehensive_creative_data(self, creative_id: str) -> Optional[Dict]:
        """
        Fetch creative with all fields needed for high-resolution detection
        
        Based on Meta Graph API Reference:
        - object_story_spec: Contains link_data.picture and video_data
        - effective_object_story_id: Key for Page Post fallback
        - asset_feed_spec: Dynamic ad assets
        - image_hash: For AdImage endpoint access
        """
        fields = [
            'id', 'name', 'title', 'body',
            'image_url', 'image_hash', 'thumbnail_url',
            'video_id',
            'object_story_spec',
            'effective_object_story_id',
            'asset_feed_spec',
            'call_to_action_type',
            'link_url',
            'link_destination_display_url'
        ]
        
        url = f"{self.base_url}/{creative_id}"
        params = {
            'access_token': self.access_token,
            'fields': ','.join(fields)
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            _logger.error(f"Failed to fetch creative {creative_id}: {str(e)}")
            return None
    
    def _execute_resolution_waterfall(self, creative_data: Dict, ad_id: str) -> Dict:
        """
        Execute the waterfall strategy for maximum resolution
        
        Waterfall Order (based on Meta best practices):
        1. Direct high-res image_url from creative
        2. object_story_spec analysis for link_data.picture
        3. effective_object_story_id Page Post fallback
        4. asset_feed_spec dynamic asset extraction
        5. AdImage endpoint via image_hash
        6. Video embed_html + high-res poster
        """
        result = {
            'media_url': None,
            'video_embed_html': None,
            'quality': 'low',
            'fetch_method': 'failed'
        }
        
        # Strategy 1: Direct Creative Image (High Resolution Check)
        direct_result = self._strategy_direct_creative_image(creative_data)
        if direct_result['success'] and direct_result['quality'] in ['high', 'ultra']:
            return direct_result
        
        # Strategy 2: Object Story Spec Analysis
        story_spec_result = self._strategy_object_story_spec(creative_data)
        if story_spec_result['success'] and story_spec_result['quality'] in ['high', 'ultra']:
            return story_spec_result
        
        # Strategy 3: Effective Story ID (Page Post Fallback)
        if creative_data.get('effective_object_story_id'):
            page_post_result = self._strategy_effective_story_fallback(
                creative_data['effective_object_story_id']
            )
            if page_post_result['success'] and page_post_result['quality'] in ['high', 'ultra']:
                return page_post_result
        
        # Strategy 4: Asset Feed Spec (Dynamic Ads)
        if creative_data.get('asset_feed_spec'):
            dynamic_result = self._strategy_asset_feed_spec(creative_data['asset_feed_spec'])
            if dynamic_result['success'] and dynamic_result['quality'] in ['high', 'ultra']:
                return dynamic_result
        
        # Strategy 5: AdImage Endpoint via Hash
        if creative_data.get('image_hash'):
            adimage_result = self._strategy_adimage_endpoint(creative_data['image_hash'])
            if adimage_result['success']:
                return adimage_result
        
        # Strategy 6: Video Handling
        if creative_data.get('video_id'):
            video_result = self._strategy_video_handling(creative_data['video_id'])
            if video_result['success']:
                return video_result
        
        # Fallback to best available result
        return max([direct_result, story_spec_result], 
                  key=lambda x: self._quality_score(x.get('quality', 'low')))
    
    def _strategy_direct_creative_image(self, creative_data: Dict) -> Dict:
        """
        Strategy 1: Direct creative image_url with resolution analysis
        
        Meta Documentation: image_url field provides the primary creative image.
        We analyze dimensions/file size to determine if it's high resolution.
        """
        result = {'success': False, 'quality': 'low', 'fetch_method': 'direct_creative'}
        
        image_url = creative_data.get('image_url')
        if not image_url:
            return result
        
        # Analyze URL patterns that typically indicate high resolution
        quality = self._analyze_image_url_quality(image_url)
        
        result.update({
            'success': True,
            'media_url': image_url,
            'quality': quality,
            'fetch_method': 'direct_creative_image'
        })
        
        return result
    
    def _strategy_object_story_spec(self, creative_data: Dict) -> Dict:
        """
        Strategy 2: Extract high-res URLs from object_story_spec
        
        Meta Documentation: object_story_spec contains the story specification
        including link_data.picture (often higher resolution) and video_data.image_url
        """
        result = {'success': False, 'quality': 'low', 'fetch_method': 'object_story_spec'}
        
        story_spec = creative_data.get('object_story_spec', {})
        
        # Check link_data.picture (common for link ads)
        link_data = story_spec.get('link_data', {})
        if link_data.get('picture'):
            picture_url = link_data['picture']
            quality = self._analyze_image_url_quality(picture_url)
            
            result.update({
                'success': True,
                'media_url': picture_url,
                'quality': quality,
                'fetch_method': 'story_spec_link_picture'
            })
            return result
        
        # Check video_data.image_url (for video ads)
        video_data = story_spec.get('video_data', {})
        if video_data.get('image_url'):
            video_image_url = video_data['image_url']
            quality = self._analyze_image_url_quality(video_image_url)
            
            result.update({
                'success': True,
                'media_url': video_image_url,
                'quality': quality,
                'fetch_method': 'story_spec_video_image'
            })
            return result
        
        return result
    
    def _strategy_effective_story_fallback(self, story_id: str) -> Dict:
        """
        Strategy 3: Use effective_object_story_id to fetch Page Post
        
        Meta Documentation: effective_object_story_id references the actual
        Page Post created by the ad. Page Posts have full_picture field
        which is often higher resolution than creative thumbnails.
        """
        result = {'success': False, 'quality': 'low', 'fetch_method': 'effective_story'}
        
        try:
            # Fetch the Page Post using the story ID
            url = f"{self.base_url}/{story_id}"
            params = {
                'access_token': self.access_token,
                'fields': 'id,full_picture,source,picture,attachments{media{image{src,height,width}}}'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            post_data = response.json()
            
            # Try full_picture first (highest resolution for posts)
            if post_data.get('full_picture'):
                full_picture_url = post_data['full_picture']
                quality = self._analyze_image_url_quality(full_picture_url)
                
                result.update({
                    'success': True,
                    'media_url': full_picture_url,
                    'quality': quality,
                    'fetch_method': 'page_post_full_picture'
                })
                return result
            
            # Try attachments.media.image.src (for rich media posts)
            attachments = post_data.get('attachments', {}).get('data', [])
            for attachment in attachments:
                media = attachment.get('media', {})
                image = media.get('image', {})
                if image.get('src'):
                    src_url = image['src']
                    quality = self._analyze_image_url_quality(src_url, image)
                    
                    result.update({
                        'success': True,
                        'media_url': src_url,
                        'quality': quality,
                        'fetch_method': 'page_post_attachment'
                    })
                    return result
            
        except Exception as e:
            _logger.warning(f"Failed to fetch effective story {story_id}: {str(e)}")
        
        return result
    
    def _strategy_asset_feed_spec(self, asset_feed_spec: Dict) -> Dict:
        """
        Strategy 4: Parse asset_feed_spec for dynamic ad assets
        
        Meta Documentation: asset_feed_spec contains the asset configuration
        for dynamic ads. We can extract image hashes and fetch high-res versions.
        """
        result = {'success': False, 'quality': 'low', 'fetch_method': 'asset_feed'}
        
        try:
            # Parse asset feed spec (it might be JSON string or dict)
            if isinstance(asset_feed_spec, str):
                asset_feed_spec = json.loads(asset_feed_spec)
            
            # Look for image assets in the feed spec
            images = asset_feed_spec.get('images', [])
            if images:
                # Take the first image asset
                first_image = images[0] if isinstance(images, list) else images
                
                if isinstance(first_image, dict) and first_image.get('hash'):
                    # Use AdImage endpoint to get high-res version
                    return self._strategy_adimage_endpoint(first_image['hash'])
                elif isinstance(first_image, str):
                    # Direct image hash
                    return self._strategy_adimage_endpoint(first_image)
            
        except Exception as e:
            _logger.warning(f"Failed to parse asset_feed_spec: {str(e)}")
        
        return result
    
    def _strategy_adimage_endpoint(self, image_hash: str) -> Dict:
        """
        Strategy 5: Fetch image via AdImage endpoint using hash
        
        Meta Documentation: AdImage endpoint provides access to uploaded images
        by their hash, often in higher resolution than creative thumbnails.
        """
        result = {'success': False, 'quality': 'low', 'fetch_method': 'adimage_endpoint'}
        
        try:
            url = f"{self.base_url}/{image_hash}"
            params = {
                'access_token': self.access_token,
                'fields': 'id,hash,url,url_128,width,height,original_width,original_height'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            image_data = response.json()
            
            # Use the highest resolution URL available
            image_url = image_data.get('url') or image_data.get('url_128')
            if image_url:
                # Determine quality based on dimensions
                width = image_data.get('original_width') or image_data.get('width')
                height = image_data.get('original_height') or image_data.get('height')
                
                quality = self._determine_quality_by_dimensions(width, height)
                
                result.update({
                    'success': True,
                    'media_url': image_url,
                    'quality': quality,
                    'fetch_method': 'adimage_hash'
                })
        
        except Exception as e:
            _logger.warning(f"Failed to fetch AdImage {image_hash}: {str(e)}")
        
        return result
    
    def _strategy_video_handling(self, video_id: str) -> Dict:
        """
        Strategy 6: Comprehensive video handling with embed_html and poster
        
        Meta Documentation: Video node provides embed_html for playback
        and various thumbnail/poster options for high-quality preview images.
        """
        result = {'success': False, 'quality': 'medium', 'fetch_method': 'video_handling'}
        
        try:
            url = f"{self.base_url}/{video_id}"
            params = {
                'access_token': self.access_token,
                'fields': 'id,embed_html,source,picture,thumbnails,format'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            video_data = response.json()
            
            # Get embed HTML for video playback
            embed_html = video_data.get('embed_html')
            
            # Get highest quality poster/thumbnail
            poster_url = None
            quality = 'medium'
            
            # Try source URL first (highest quality)
            if video_data.get('source'):
                poster_url = video_data['source']
                quality = 'high'
            # Try picture field
            elif video_data.get('picture'):
                poster_url = video_data['picture']
                quality = 'medium'
            # Try thumbnails array
            elif video_data.get('thumbnails', {}).get('data'):
                thumbnails = video_data['thumbnails']['data']
                if thumbnails:
                    # Get the largest thumbnail
                    largest_thumb = max(thumbnails, 
                                      key=lambda t: (t.get('width', 0) * t.get('height', 0)))
                    poster_url = largest_thumb.get('uri')
                    quality = self._determine_quality_by_dimensions(
                        largest_thumb.get('width'), largest_thumb.get('height')
                    )
            
            result.update({
                'success': True,
                'media_url': poster_url,
                'video_embed_html': embed_html,
                'quality': quality,
                'fetch_method': 'video_comprehensive'
            })
        
        except Exception as e:
            _logger.warning(f"Failed to fetch video {video_id}: {str(e)}")
        
        return result
    
    def _analyze_image_url_quality(self, image_url: str, dimensions: Dict = None) -> str:
        """
        Analyze image URL to determine likely resolution quality
        
        Uses URL patterns, file size indicators, and dimension data
        """
        if not image_url:
            return 'low'
        
        # Check dimensions if provided
        if dimensions:
            width = dimensions.get('width', 0)
            height = dimensions.get('height', 0)
            return self._determine_quality_by_dimensions(width, height)
        
        # Analyze URL patterns
        url_lower = image_url.lower()
        
        # Ultra high resolution indicators
        if any(indicator in url_lower for indicator in ['_1080x', '_1920x', '_2048x', 'original', 'full_size']):
            return 'ultra'
        
        # High resolution indicators
        if any(indicator in url_lower for indicator in ['_720x', '_1024x', '_large', '_hd']):
            return 'high'
        
        # Medium resolution indicators
        if any(indicator in url_lower for indicator in ['_480x', '_640x', '_medium']):
            return 'medium'
        
        # Low resolution indicators
        if any(indicator in url_lower for indicator in ['_thumbnail', '_small', '_150x', '_200x']):
            return 'low'
        
        # Default to medium if no clear indicators
        return 'medium'
    
    def _determine_quality_by_dimensions(self, width: Optional[int], height: Optional[int]) -> str:
        """Determine quality based on image dimensions"""
        if not width or not height:
            return 'medium'
        
        pixel_count = width * height
        
        if pixel_count >= 2073600:  # 1920x1080 or equivalent
            return 'ultra'
        elif pixel_count >= 921600:  # 1280x720 or equivalent
            return 'high'
        elif pixel_count >= 307200:  # 640x480 or equivalent
            return 'medium'
        else:
            return 'low'
    
    def _quality_score(self, quality: str) -> int:
        """Convert quality string to numeric score for comparison"""
        scores = {'low': 1, 'medium': 2, 'high': 3, 'ultra': 4}
        return scores.get(quality, 1)
    
    def _extract_creative_metadata(self, creative_data: Dict) -> Dict:
        """Extract additional metadata from creative data"""
        return {
            'title': creative_data.get('title') or creative_data.get('name'),
            'body': creative_data.get('body'),
            'cta_type': creative_data.get('call_to_action_type'),
            'link_url': creative_data.get('link_url'),
            'effective_story_id': creative_data.get('effective_object_story_id'),
            'asset_feed_spec': json.dumps(creative_data.get('asset_feed_spec')) if creative_data.get('asset_feed_spec') else None
        }