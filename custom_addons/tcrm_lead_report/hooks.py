# -*- coding: utf-8 -*-
"""Ensure Lead Raporu is fully automatic after install/upgrade."""


def post_init_hook(env):
    """Activate marketing automation crons and queue an immediate backfill."""
    from tcrm.addons.tcrm_marketing_hub.hooks import (
        ensure_daily_metrics_cron,
        ensure_meta_lead_cron,
        schedule_marketing_automation,
    )

    ensure_meta_lead_cron(env)
    ensure_daily_metrics_cron(env)
    schedule_marketing_automation(env, daily_days_back=30)
