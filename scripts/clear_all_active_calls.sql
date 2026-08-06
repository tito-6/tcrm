UPDATE tcrm_call_record
SET status = 'canceled',
    active_browser_session = false,
    end_time = NOW()
WHERE active_browser_session = true;
