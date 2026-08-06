-- Clear stale active browser sessions (calls that never completed)
UPDATE tcrm_call_record
SET status = 'canceled',
    active_browser_session = false,
    end_time = NOW()
WHERE active_browser_session = true
  AND status IN ('pending', 'queued', 'initiated', 'ringing')
  AND create_date < NOW() - INTERVAL '5 minutes';

-- Also fix any calls stuck as in-progress with no provider SID
UPDATE tcrm_call_record
SET status = 'canceled',
    active_browser_session = false,
    end_time = NOW()
WHERE active_browser_session = true
  AND status = 'in-progress'
  AND provider_call_sid IS NULL
  AND create_date < NOW() - INTERVAL '10 minutes';
