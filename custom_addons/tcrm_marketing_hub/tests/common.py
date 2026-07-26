# -*- coding: utf-8 -*-
from tcrm.tests import TransactionCase, tagged

_LEADGEN_SEQ = 0


def _next_leadgen():
    global _LEADGEN_SEQ
    _LEADGEN_SEQ += 1
    return 'lg_test_%s' % _LEADGEN_SEQ


@tagged('tcrm_marketing_hub')
class MarketingHubCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({'name': 'MH Other Co'})

        cls.profile = cls.env['tcrm.marketing.profile'].create({
            'name': 'MH Test Profil',
            'zernio_id': 'z_prof_test_1',
            'company_id': cls.company.id,
            'is_default': True,
        })
        cls.other_profile = cls.env['tcrm.marketing.profile'].create({
            'name': 'MH Other Profil',
            'zernio_id': 'z_prof_other_1',
            'company_id': cls.other_company.id,
            'is_default': True,
        })

        cls.account_enabled = cls.env['tcrm.marketing.account'].create({
            'name': 'Aktif Sayfa',
            'username': 'aktif_sayfa',
            'zernio_id': 'z_acc_enabled',
            'platform': 'facebook',
            'profile_id': cls.profile.id,
            'status': 'connected',
            'sync_enabled': True,
            'active': True,
        })
        cls.account_disabled = cls.env['tcrm.marketing.account'].create({
            'name': 'Kapalı Sayfa',
            'username': 'kapali_sayfa',
            'zernio_id': 'z_acc_disabled',
            'platform': 'facebook',
            'profile_id': cls.profile.id,
            'status': 'connected',
            'sync_enabled': False,
            'active': True,
        })
        cls.other_account = cls.env['tcrm.marketing.account'].create({
            'name': 'Diğer Şirket Sayfa',
            'zernio_id': 'z_acc_other',
            'platform': 'facebook',
            'profile_id': cls.other_profile.id,
            'status': 'connected',
            'sync_enabled': True,
            'active': True,
        })

        cls.group_user = cls.env.ref('tcrm_marketing_hub.group_marketing_user')
        cls.group_manager = cls.env.ref('tcrm_marketing_hub.group_marketing_manager')

        cls.user_marketing = cls.env['res.users'].create({
            'name': 'MH Marketing User',
            'login': 'mh_marketing_user',
            'email': 'mh_user@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.group_user.id,
            ])],
        })
        cls.user_manager = cls.env['res.users'].create({
            'name': 'MH Marketing Manager',
            'login': 'mh_marketing_manager',
            'email': 'mh_manager@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.group_manager.id,
            ])],
        })

    def _make_form(self, account, form_remote_id='form_1', name='Test Form'):
        return self.env['tcrm.marketing.lead.form'].create({
            'name': name,
            'zernio_form_id': form_remote_id,
            'account_id': account.id,
            'leads_count': 1,
        })

    def _make_meta_lead(self, form, **kwargs):
        vals = {
            'contact_name': 'Test Lead',
            'email': 'lead@example.com',
            'phone': '+905551112233',
            'leadgen_id': kwargs.pop('leadgen_id', _next_leadgen()),
            'form_id': form.id,
            'source_platform': 'instagram',
            'ad_id': 'ad_100',
            'ad_name': 'Story Ad',
            'campaign_id_remote': 'camp_200',
            'campaign_name': 'Summer Campaign',
            'state': 'imported',
        }
        vals.update(kwargs)
        return self.env['tcrm.marketing.meta.lead'].create(vals)
