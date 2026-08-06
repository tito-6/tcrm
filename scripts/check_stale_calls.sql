SELECT id, status, active_browser_session, user_id, destination_number, create_date
FROM tcrm_call_record
WHERE active_browser_session = true
   OR status IN ('pending', 'queued', 'initiated', 'ringing', 'in-progress')
ORDER BY id DESC
LIMIT 10;
