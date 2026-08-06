# -*- coding: utf-8 -*-
"""Backfill CRM create_date from Meta lead filled time; ensure havuzu list limit."""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE crm_lead AS l
           SET create_date = m.created_time
          FROM tcrm_marketing_meta_lead AS m
         WHERE m.crm_lead_id = l.id
           AND m.created_time IS NOT NULL
           AND (l.create_date IS DISTINCT FROM m.created_time)
        """
    )
    cr.execute(
        """
        UPDATE ir_act_window
           SET "limit" = 80
         WHERE res_model = 'crm.lead'
           AND (
                id IN (
                    SELECT res_id FROM ir_model_data
                     WHERE module = 'tcrm_propertio'
                       AND name = 'action_lead_havuzu'
                       AND model = 'ir.actions.act_window'
                )
                OR id IN (
                    SELECT res_id FROM ir_model_data
                     WHERE module = 'crm'
                       AND name IN ('crm_lead_all_leads', 'crm_lead_action_pipeline')
                       AND model = 'ir.actions.act_window'
                )
           )
        """
    )
