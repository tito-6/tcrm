UPDATE tcrm_call_provider_config
SET recording_enabled = true,
    dual_channel_recording = true,
    recording_announcement_enabled = false
WHERE enabled = true;
