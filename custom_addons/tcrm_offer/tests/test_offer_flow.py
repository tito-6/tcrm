# -*- coding: utf-8 -*-
from datetime import timedelta

from tcrm import fields
from tcrm.tests import tagged, TransactionCase, HttpCase
from tcrm.exceptions import UserError

from ..services import tokens as token_svc
from ..services.pricing import to_kurus


@tagged('post_install', '-at_install', 'tcrm_offer')
class TestOfferFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Ahsen Mağaza Test'})
        cls.Offer = cls.env['tcrm.offer']
        cls.manager = cls.env.ref('base.user_admin')
        cls.manager.write({
            'group_ids': [(4, cls.env.ref('tcrm_offer.group_offer_manager').id)],
        })

    def _create_draft(self):
        return self.Offer.with_user(self.manager).create({
            'partner_id': self.partner.id,
            'partner_contact_name': 'Yunus Bey',
            'title': 'Test Teklif',
            'summary': '<p>Özet</p>',
            'terms_html': '<p>Şartlar</p>',
            'valid_until': fields.Date.today() + timedelta(days=15),
            'ad_budget_default': 50000,
            'item_ids': [
                (0, 0, {
                    'name': 'Meta Reklam Yönetimi',
                    'pricing_type': 'meta_budget',
                    'billing_period': 'monthly',
                    'selection_type': 'required',
                    'default_selected': True,
                    'taxable': True,
                    'sort_order': 10,
                    'code': 'meta_ads',
                }),
                (0, 0, {
                    'name': 'Sosyal — Başlangıç',
                    'pricing_type': 'fixed',
                    'unit_price': 20000,
                    'billing_period': 'monthly',
                    'selection_type': 'optional',
                    'default_selected': True,
                    'taxable': True,
                    'exclusive_group': 'social_media',
                    'sort_order': 20,
                    'code': 'sm_a',
                }),
                (0, 0, {
                    'name': 'Sosyal — Büyüme',
                    'pricing_type': 'fixed',
                    'unit_price': 27000,
                    'billing_period': 'monthly',
                    'selection_type': 'optional',
                    'taxable': True,
                    'exclusive_group': 'social_media',
                    'sort_order': 21,
                    'code': 'sm_b',
                }),
                (0, 0, {
                    'name': 'Video',
                    'pricing_type': 'fixed',
                    'unit_price': 20000,
                    'billing_period': 'per_session',
                    'selection_type': 'optional',
                    'default_selected': True,
                    'taxable': True,
                    'sort_order': 40,
                    'code': 'video',
                }),
            ],
        })

    def test_state_transitions_and_approve(self):
        offer = self._create_draft()
        self.assertEqual(offer.status, 'draft')
        offer.action_publish()
        self.assertEqual(offer.status, 'published')
        self.assertTrue(offer.public_token_plaintext)
        self.assertTrue(offer.passcode_plaintext)
        token = offer.public_token_plaintext
        passcode = offer.passcode_plaintext

        found = self.Offer._find_by_public_token(token)
        self.assertEqual(found, offer)

        self.assertFalse(offer.verify_passcode('WRONG', ip='1.2.3.4'))
        self.assertTrue(offer.verify_passcode(passcode, ip='1.2.3.4'))

        offer.mark_viewed(ip='1.2.3.4')
        self.assertEqual(offer.status, 'viewed')
        self.assertTrue(offer.public_is_selectable(), 'status=%s accessible=%s' % (
            offer.status, offer.public_is_accessible()))

        payload = offer.get_public_payload()
        self.assertTrue(all('admin_note' not in str(i) or True for i in payload['items']))
        # ensure admin_note not in public payload keys
        for item in payload['items']:
            self.assertNotIn('admin_note', item)

        selected = [
            offer.item_ids.filtered(lambda i: i.code == 'meta_ads').id,
            offer.item_ids.filtered(lambda i: i.code == 'sm_a').id,
            offer.item_ids.filtered(lambda i: i.code == 'video').id,
        ]
        self.assertTrue(all(selected), 'missing items: %s' % offer.item_ids.mapped('code'))
        approval = offer.sudo().action_approve_public(
            selected_ids=selected,
            ad_budget=50000,
            approver_name='Yunus Bey',
            approver_email='yunus@example.com',
            accepted_services=True,
            accepted_terms=True,
            accepted_kvkk=True,
            idempotency_key='test-key-1',
            ip='1.2.3.4',
        )
        self.assertEqual(offer.status, 'approved')
        self.assertEqual(approval.gross_total, 84000.0)  # 50k monthly + 20k session + 20% KDV

        # idempotent
        approval2 = offer.action_approve_public(
            selected_ids=selected,
            ad_budget=50000,
            approver_name='Yunus Bey',
            approver_email='yunus@example.com',
            accepted_services=True,
            accepted_terms=True,
            accepted_kvkk=True,
            idempotency_key='test-key-1',
        )
        self.assertEqual(approval2.id, approval.id)

        # snapshot immutable content write blocked
        with self.assertRaises(UserError):
            offer.write({'title': 'Hack'})

        offer.action_close()
        self.assertEqual(offer.status, 'closed')
        self.assertTrue(all(s.revoked for s in offer.session_ids))

    def test_exclusive_conflict_on_quote(self):
        offer = self._create_draft()
        offer.action_publish()
        a = offer.item_ids.filtered(lambda i: i.code == 'sm_a').id
        b = offer.item_ids.filtered(lambda i: i.code == 'sm_b').id
        meta = offer.item_ids.filtered(lambda i: i.code == 'meta_ads').id
        with self.assertRaises(ValueError):
            offer.action_preview_quote(selected_ids=[meta, a, b], ad_budget=50000)

    def test_paused_not_accessible(self):
        offer = self._create_draft()
        offer.action_publish()
        offer.create_access_session(ip='9.9.9.9')
        offer.action_pause()
        self.assertEqual(offer.status, 'paused')
        self.assertFalse(offer.public_is_accessible())
        self.assertTrue(all(s.revoked for s in offer.session_ids))


@tagged('post_install', '-at_install', 'tcrm_offer')
class TestOfferHttp(HttpCase):

    def test_public_closed_without_leak(self):
        partner = self.env['res.partner'].create({'name': 'HTTP Partner'})
        manager = self.env.ref('base.user_admin')
        manager.write({
            'group_ids': [(4, self.env.ref('tcrm_offer.group_offer_manager').id)],
        })
        offer = self.env['tcrm.offer'].with_user(manager).create({
            'partner_id': partner.id,
            'title': 'Secret Title Should Not Leak',
            'valid_until': fields.Date.today() + timedelta(days=10),
            'item_ids': [(0, 0, {
                'name': 'Svc', 'pricing_type': 'fixed', 'unit_price': 1000,
                'billing_period': 'one_time', 'selection_type': 'required',
            })],
        })
        offer.action_publish()
        token = offer.public_token_plaintext
        offer.action_close()
        res = self.url_open(f'/teklif/{token}')
        self.assertEqual(res.status_code, 403)
        self.assertNotIn('Secret Title Should Not Leak', res.text)
        self.assertIn('erişime açık değil', res.text)
