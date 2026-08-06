# -*- coding: utf-8 -*-
"""Unit-level helpers for Perla website lead webhook (no live HTTP)."""
import hashlib
import hmac
import unittest
import uuid

from ..controllers.lead_webhook import (
    IDEMPOTENCY_SCOPE,
    INTEGRATION_NAME,
    ROUTE_PATH,
    PerlaWebsiteLeadWebhook,
)


class TestPerlaLeadWebhookHelpers(unittest.TestCase):

    def test_constants(self):
        self.assertEqual(ROUTE_PATH, '/webhook/tcrm/lead')
        self.assertEqual(INTEGRATION_NAME, 'perla_website_lead')
        self.assertEqual(IDEMPOTENCY_SCOPE, 'perla_website_lead:v1')

    def test_uuid_v4_validation(self):
        ctrl = PerlaWebsiteLeadWebhook()
        self.assertTrue(ctrl._is_uuid_v4(str(uuid.uuid4())))
        self.assertFalse(ctrl._is_uuid_v4('not-a-uuid'))
        # Nil UUID is version 0 / nil — reject as v4
        self.assertFalse(ctrl._is_uuid_v4('00000000-0000-0000-0000-000000000000'))

    def test_canonical_signature_shape(self):
        body = b'{"name":"Test"}'
        body_hash = hashlib.sha256(body).hexdigest()
        tenant = str(uuid.uuid4())
        key = str(uuid.uuid4())
        ts = '1710000000'
        canonical = f'v1\nPOST\n{ROUTE_PATH}\n{ts}\n{tenant}\n{key}\n{body_hash}'
        secret = b'x' * 32
        sig = hmac.new(secret, canonical.encode('utf-8'), hashlib.sha256).hexdigest()
        self.assertEqual(len(sig), 64)
        self.assertTrue(sig.islower())


if __name__ == '__main__':
    unittest.main()
