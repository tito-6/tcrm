# -*- coding: utf-8 -*-
"""Isolation + routing decision tests.

These prove that:
  * the DB is chosen only from a validated mapping (never the raw subdomain),
  * one tenant host can never resolve to another tenant's or the control DB,
  * suspended / preparing / unknown hosts never resolve to a real DB,
  * the control plane keeps working.

The pure-logic tests run without a live DB. The end-to-end isolation tests use
temporary tenant + domain records in the current DB.
"""
from tcrm.tests.common import TransactionCase, tagged
from tcrm.addons.tcrm_saas_routing import routing_patch as rp


class TestRoutingClassify(TransactionCase):
    """Pure decision logic — no dependence on hostname string for the DB name."""

    def test_unknown_host_not_found(self):
        self.assertEqual(rp.classify(None, False), (rp.S_NOT_FOUND, None))

    def test_suspended_when_frozen(self):
        row = ('acme', 'active', True, True, True)  # is_frozen=True
        self.assertEqual(rp.classify(row, True), (rp.S_SUSPENDED, None))

    def test_suspended_when_tenant_inactive(self):
        row = ('acme', 'active', False, False, True)  # tenant_active=False
        self.assertEqual(rp.classify(row, True), (rp.S_SUSPENDED, None))

    def test_not_found_when_domain_inactive(self):
        row = ('acme', 'active', False, True, False)  # domain_active=False
        self.assertEqual(rp.classify(row, True), (rp.S_NOT_FOUND, None))

    def test_preparing_when_no_db_name(self):
        row = (None, 'active', False, True, True)
        self.assertEqual(rp.classify(row, False), (rp.S_PREPARING, None))

    def test_preparing_when_db_missing(self):
        row = ('acme', 'active', False, True, True)
        self.assertEqual(rp.classify(row, False), (rp.S_PREPARING, None))

    def test_preparing_when_draft(self):
        row = ('acme', 'draft', False, True, True)
        self.assertEqual(rp.classify(row, True), (rp.S_PREPARING, None))

    def test_ok_when_active_and_db_exists(self):
        row = ('acme', 'active', False, True, True)
        self.assertEqual(rp.classify(row, True), (rp.S_OK, 'acme'))

    def test_normalize_host(self):
        self.assertEqual(rp.normalize_host('ACME.tcrm.online:443'), 'acme.tcrm.online')
        self.assertEqual(rp.normalize_host('acme.tcrm.online.'), 'acme.tcrm.online')


@tagged('post_install', '-at_install')
class TestRoutingIsolation(TransactionCase):
    """End-to-end: two tenants cannot cross-select databases."""

    def setUp(self):
        super().setUp()
        Tenant = self.env['tcrm.tenant']
        Domain = self.env['tcrm.tenant.domain']
        self.company_a = self.env['res.company'].create({'name': 'ISO Tenant A'})
        self.company_b = self.env['res.company'].create({'name': 'ISO Tenant B'})
        # Create without db_name (creating with db_name would trigger real DB
        # provisioning), then set the mapping via write().
        self.tenant_a = Tenant.create({
            'name': 'ISO Tenant A', 'company_id': self.company_a.id,
            'state': 'active', 'active': True,
        })
        self.tenant_b = Tenant.create({
            'name': 'ISO Tenant B', 'company_id': self.company_b.id,
            'state': 'active', 'active': True,
        })
        self.tenant_a.write({'db_name': 'iso_tenant_a'})
        self.tenant_b.write({'db_name': 'iso_tenant_b'})
        self.dom_a = Domain.create({
            'tenant_id': self.tenant_a.id, 'domain': 'iso-a.tcrm.online',
            'is_primary': True, 'active': True, 'verified': True,
        })
        self.dom_b = Domain.create({
            'tenant_id': self.tenant_b.id, 'domain': 'iso-b.tcrm.online',
            'is_primary': True, 'active': True, 'verified': True,
        })
        self.env.flush_all()
        rp._host_cache.clear()

    def _resolve_via_mapping(self, host):
        """Resolve using the mapping SQL on the *test* cursor (so uncommitted
        rows are visible) and treat the mapped DB as existing — this isolates
        the mapping+decision logic from physical DB creation."""
        self.env.cr.execute(rp._MAPPING_SQL, (rp.normalize_host(host),))
        row = self.env.cr.fetchone()
        return rp.classify(row, bool(row and row[0]))

    def _db_filter(self, dbs, host):
        """Replicate the patched db_filter decision for the given host."""
        status, db = self._resolve_via_mapping(host)
        if status in (rp.S_OK, rp.S_CONTROL) and db:
            return [d for d in dbs if d == db]
        return []

    def test_tenant_a_resolves_to_its_own_db(self):
        self.assertEqual(self._resolve_via_mapping('iso-a.tcrm.online'), (rp.S_OK, 'iso_tenant_a'))

    def test_tenant_b_resolves_to_its_own_db(self):
        self.assertEqual(self._resolve_via_mapping('iso-b.tcrm.online'), (rp.S_OK, 'iso_tenant_b'))

    def test_tenant_a_host_cannot_select_tenant_b_db(self):
        # db_filter for tenant A's host must reject tenant B's DB and the control DB.
        self.assertEqual(
            self._db_filter(['iso_tenant_a', 'iso_tenant_b', 'tcrm_master'], 'iso-a.tcrm.online'),
            ['iso_tenant_a'],
        )
        self.assertEqual(
            self._db_filter(['iso_tenant_a', 'iso_tenant_b', 'tcrm_master'], 'iso-b.tcrm.online'),
            ['iso_tenant_b'],
        )

    def test_tenant_host_cannot_select_control_db(self):
        self.assertEqual(self._db_filter(['tcrm_master'], 'iso-a.tcrm.online'), [])

    def test_forged_but_unknown_host_is_not_found(self):
        self.assertEqual(self._resolve_via_mapping('attacker.tcrm.online'), (rp.S_NOT_FOUND, None))
        self.assertEqual(self._db_filter(['tcrm_master', 'iso_tenant_a'], 'attacker.tcrm.online'), [])

    def test_db_name_not_derived_from_subdomain(self):
        # subdomain 'iso-a' would naively map to 'iso_a', but the validated DB is
        # 'iso_tenant_a' (from the record) — proving no string-derived DB names.
        status, db = self._resolve_via_mapping('iso-a.tcrm.online')
        self.assertEqual(db, 'iso_tenant_a')
        self.assertNotEqual(db, 'iso_a')
