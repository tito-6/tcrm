"""
Diagnostic Server Action for Meta Creative Data Verification
This can be added as a Server Action in Odoo to debug creative fetching issues
"""

# Server Action Code (to be added in Odoo UI: Settings > Technical > Automation > Server Actions)
# Name: Debug Meta Creative Data
# Model: crm.lead
# Action Type: Execute Python Code

def debug_meta_creative_data():
    """Diagnostic function to verify backend creative data storage"""
    
    lead = record  # This is the selected lead record in Odoo
    
    # Log initial state
    _logger.info("=== DEBUGGING META CREATIVE DATA FOR LEAD %s ===", lead.id)
    _logger.info("Lead Name: %s", lead.name)
    _logger.info("Meta Ad ID: %s", lead.meta_ad_id)
    
    # Check if we have basic meta data
    if not lead.meta_ad_id:
        raise UserError("❌ DIAGNOSIS: No Meta Ad ID found on this lead. Cannot fetch creative data.")
    
    # Force refresh creative data
    _logger.info("🔄 Force refreshing creative data...")
    try:
        refresh_result = lead.action_refresh_ad_creative()
        _logger.info("Refresh result: %s", refresh_result)
    except Exception as e:
        _logger.error("❌ REFRESH FAILED: %s", str(e))
        raise UserError(f"❌ REFRESH FAILED: {str(e)}")
    
    # Reload the record to get fresh data
    lead = lead.browse(lead.id)
    
    # Collect diagnostic data
    diagnostic_data = {
        'meta_creative_id': lead.meta_creative_id,
        'meta_creative_type': lead.meta_creative_type,
        'meta_creative_media_url': lead.meta_creative_media_url,
        'meta_creative_high_res_url': lead.meta_creative_high_res_url,
        'meta_creative_video_embed_html': lead.meta_creative_video_embed_html,
        'meta_creative_title': lead.meta_creative_title,
        'meta_creative_body': lead.meta_creative_body,
        'meta_creative_cta': lead.meta_creative_cta,
        'meta_creative_resolution_quality': lead.meta_creative_resolution_quality,
        'meta_creative_fetch_method': lead.meta_creative_fetch_method,
        'meta_creative_effective_story_id': lead.meta_creative_effective_story_id,
    }
    
    # Log all field values
    for field_name, field_value in diagnostic_data.items():
        _logger.info("Field %s: %s", field_name, field_value)
    
    # Check computed preview field
    preview_content = lead.meta_creative_preview
    _logger.info("Creative Preview HTML length: %s", len(preview_content or ''))
    _logger.info("Preview content (first 200 chars): %s", (preview_content or '')[:200])
    
    # Prepare user-friendly diagnosis
    diagnosis = []
    
    if lead.meta_creative_id:
        diagnosis.append(f"✅ Creative ID: {lead.meta_creative_id}")
    else:
        diagnosis.append("❌ No Creative ID found")
    
    if lead.meta_creative_high_res_url:
        diagnosis.append(f"✅ High-Res URL: {lead.meta_creative_high_res_url[:60]}...")
    elif lead.meta_creative_media_url:
        diagnosis.append(f"⚠️ Basic Media URL: {lead.meta_creative_media_url[:60]}...")
    else:
        diagnosis.append("❌ No Media URL found")
    
    if lead.meta_creative_resolution_quality:
        diagnosis.append(f"🎯 Quality: {lead.meta_creative_resolution_quality.upper()}")
    else:
        diagnosis.append("❌ No Quality Assessment")
    
    if lead.meta_creative_fetch_method:
        diagnosis.append(f"🔧 Method: {lead.meta_creative_fetch_method}")
    else:
        diagnosis.append("❌ No Fetch Method recorded")
    
    if lead.meta_creative_type == 'video' and lead.meta_creative_video_embed_html:
        diagnosis.append(f"🎬 Video Embed: {len(lead.meta_creative_video_embed_html)} chars")
    elif lead.meta_creative_type == 'video':
        diagnosis.append("❌ Video type but no embed HTML")
    
    # Final diagnosis message
    diagnosis_message = "META CREATIVE DIAGNOSTIC RESULTS:\n\n" + "\n".join(diagnosis)
    
    if preview_content:
        diagnosis_message += f"\n\n📄 Preview HTML Generated: {len(preview_content)} characters"
    else:
        diagnosis_message += "\n\n❌ NO PREVIEW HTML GENERATED"
    
    # Also check if fields exist in database schema
    try:
        lead_model = env['crm.lead']
        field_exists = {}
        for field in ['meta_creative_high_res_url', 'meta_creative_video_embed_html', 'meta_creative_resolution_quality']:
            field_exists[field] = hasattr(lead_model, field)
        
        diagnosis_message += "\n\nFIELD EXISTENCE CHECK:\n"
        for field, exists in field_exists.items():
            diagnosis_message += f"{'✅' if exists else '❌'} {field}: {exists}\n"
    except Exception as e:
        diagnosis_message += f"\n\n⚠️ Field check error: {str(e)}"
    
    raise UserError(diagnosis_message)

# Execute the diagnostic
debug_meta_creative_data()