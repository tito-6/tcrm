# -*- coding: utf-8 -*-
"""Ensure marketing automation crons stay active after upgrade."""


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    from tcrm.addons.tcrm_marketing_hub.hooks import (
        ensure_daily_metrics_cron,
        ensure_meta_lead_cron,
        schedule_marketing_automation,
    )

    ensure_meta_lead_cron(env)
    ensure_daily_metrics_cron(env)
    schedule_marketing_automation(env)
