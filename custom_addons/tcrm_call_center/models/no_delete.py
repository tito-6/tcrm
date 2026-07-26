# -*- coding: utf-8 -*-
"""Kayıt silme koruması (audit / veri bütünlüğü).

Bu politika kullanıcıların önemli kayıtları elle silmesini engeller, ANCAK
Odoo'nun kendi iç işlemlerini (yeniden hesaplama, mutabakat geri alma, rapor
render, sudo) ve Yazılım Sahibi / sistem yöneticisini engellememelidir.

Önceki sürüm koşulsuz olarak AccessError fırlatıyordu; bu, fatura PDF'i render
edilirken tetiklenen dahili `account.payment.unlink()` çağrısını da bloke edip
"Erişim Hatası" ile fatura yazdırma/önizlemeyi kırıyordu.
"""
from tcrm import models, _
from tcrm.exceptions import AccessError

# Silme politikasını atlaması gereken bağlam anahtarı (programatik kullanım için).
_BYPASS_KEY = 'bypass_delete_policy'


def _delete_allowed(env):
    """Silmeye izin verilen durumlar: sudo/superuser, sistem yöneticisi
    (Yazılım Sahibi) veya açık bağlam atlaması."""
    if env.su:
        return True
    if env.context.get(_BYPASS_KEY):
        return True
    try:
        return env.user.has_group('base.group_system')
    except Exception:
        return False


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def unlink(self):
        if not _delete_allowed(self.env):
            raise AccessError(_('Sistem politikası gereği fırsat ve aday kayıtları silinemez.'))
        return super().unlink()


class TcrmCallRecord(models.Model):
    _inherit = 'tcrm.call.record'

    def unlink(self):
        if not _delete_allowed(self.env):
            raise AccessError(_('Sistem politikası gereği çağrı kayıtları silinemez.'))
        return super().unlink()


class TcrmCallRecording(models.Model):
    _inherit = 'tcrm.call.recording'

    def unlink(self):
        if not _delete_allowed(self.env):
            raise AccessError(_('Sistem politikası gereği ses kayıtları silinemez.'))
        return super().unlink()


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def unlink(self):
        if not _delete_allowed(self.env):
            raise AccessError(_('Sistem politikası gereği ödeme kayıtları silinemez.'))
        return super().unlink()


class AccountMove(models.Model):
    _inherit = 'account.move'

    def unlink(self):
        if not _delete_allowed(self.env):
            raise AccessError(_('Sistem politikası gereği fatura/yevmiye kayıtları silinemez.'))
        return super().unlink()
