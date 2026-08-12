# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Tests for the Lead Havuzu merge (Adaylar + Fırsat Havuzu → one screen)."""
from tcrm.tests.common import TransactionCase
from tcrm.tools.safe_eval import safe_eval


class TestLeadHavuzu(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Action = cls.env['ir.actions.act_window']
        cls.Menu = cls.env['ir.ui.menu']
        cls.View = cls.env['ir.ui.view']

    def _action(self, xmlid):
        return self.env.ref(xmlid)

    def _domain_allows_both_types(self, action, label=None):
        label = label or action.display_name
        domain = action.domain or '[]'
        if isinstance(domain, str):
            domain = safe_eval(domain)
        self.assertEqual(domain, [], "%s domain must allow both leads and opportunities" % label)
        context = action.context or '{}'
        if isinstance(context, str):
            context = safe_eval(context)
        self.assertNotIn(
            'search_default_type', context,
            "%s must not force search_default_type" % label,
        )
        self.assertNotIn(
            'search_default_to_process', context,
            "%s must not force lead-only to_process filter" % label,
        )
        self.assertNotIn(
            'search_default_assigned_to_me', context,
            "%s must not force assigned-to-me filter" % label,
        )

    def test_01_action_lead_havuzu_exists(self):
        action = self._action('tcrm_propertio.action_lead_havuzu')
        self.assertEqual(action.res_model, 'crm.lead')
        self.assertEqual(action.name, 'Lead Havuzu')
        self.assertIn('kanban', action.view_mode)
        self.assertIn('list', action.view_mode)
        self.assertIn('form', action.view_mode)
        self.assertEqual(
            action.mobile_view_mode, 'list',
            'Lead Havuzu must open as list on mobile (not default kanban)',
        )
        self.assertTrue(
            action.view_mode.startswith('list'),
            'Desktop default view must remain list',
        )
        self._domain_allows_both_types(action, 'tcrm_propertio.action_lead_havuzu')

    def test_02_old_actions_resolve_to_merged_behavior(self):
        havuzu = self._action('tcrm_propertio.action_lead_havuzu')
        for xmlid in ('crm.crm_lead_all_leads', 'crm.crm_lead_action_pipeline'):
            action = self._action(xmlid)
            self.assertEqual(action.res_model, 'crm.lead')
            self.assertEqual(action.name, 'Lead Havuzu')
            self.assertEqual(
                action.mobile_view_mode, 'list',
                '%s must open as list on mobile' % xmlid,
            )
            self._domain_allows_both_types(action, xmlid)
            self.assertEqual(
                action.search_view_id, havuzu.search_view_id,
                "%s should use the Lead Havuzu search view" % xmlid,
            )

    def test_03_single_main_pool_menu_active(self):
        leads_menu = self._action('crm.crm_menu_leads')
        pipeline_menu = self._action('crm.menu_crm_opportunities')
        havuzu_menu = self._action('tcrm_propertio.menu_lead_havuzu')
        havuzu_action = self._action('tcrm_propertio.action_lead_havuzu')

        self.assertFalse(leads_menu.active, 'Adaylar / Leads menu must be hidden')
        self.assertFalse(pipeline_menu.active, 'Fırsat Havuzu / My Pipeline menu must be hidden')
        self.assertTrue(havuzu_menu.active, 'Lead Havuzu menu must be active')
        self.assertEqual(havuzu_menu.action, havuzu_action)

        pool_action_ids = {
            havuzu_action.id,
            self._action('crm.crm_lead_all_leads').id,
            self._action('crm.crm_lead_action_pipeline').id,
        }
        sales_menus = self.Menu.search([
            ('parent_id', '=', self.env.ref('crm.crm_menu_sales').id),
            ('active', '=', True),
            ('action', '!=', False),
        ])
        pool_menus = self.Menu.browse()
        for menu in sales_menus:
            action = menu.action
            if not action or action._name != 'ir.actions.act_window':
                continue
            if action.id in pool_action_ids or action.name == 'Lead Havuzu':
                pool_menus |= menu
        self.assertEqual(
            len(pool_menus), 1,
            'Exactly one active CRM sales menu should open the Lead Havuzu pool, got: %s'
            % pool_menus.mapped('complete_name'),
        )

    def test_04_search_view_filters_exist(self):
        search = self._action('tcrm_propertio.view_crm_lead_havuzu_search')
        self.assertEqual(search.model, 'crm.lead')
        arch = search.arch_db or search.arch
        required_filters = (
            'filter_new_leads',
            'filter_qualified_leads',
            'filter_opportunities',
            'filter_won',
            'filter_lost',
            'filter_archived',
            'filter_creation_date',
        )
        for name in required_filters:
            self.assertIn('name="%s"' % name, arch, 'Missing filter %s' % name)

        required_fields = (
            'source_id',
            'campaign_id',
            'medium_id',
            'user_id',
            'team_id',
            'propertio_project_id',
            'create_date',
        )
        for field_name in required_fields:
            self.assertIn(
                'name="%s"' % field_name, arch,
                'Missing search field %s' % field_name,
            )
        # Broker field is not on crm.lead in propertio — must not be assumed
        self.assertNotIn('name="broker', arch)
