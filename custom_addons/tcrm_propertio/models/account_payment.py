# -*- coding: utf-8 -*-
from tcrm import _, SUPERUSER_ID, fields, models
from tcrm.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = ['account.payment', 'propertio.audit.mixin']

    propertio_reversal_payment_id = fields.Many2one(
        'account.payment',
        string='Propertio Reversal Payment',
        readonly=True,
        copy=False,
    )
    propertio_reversed_payment_id = fields.Many2one(
        'account.payment',
        string='Propertio Original Payment',
        readonly=True,
        copy=False,
    )
    propertio_cancel_reason_code = fields.Char(readonly=True, copy=False)
    propertio_cancel_explanation = fields.Text(readonly=True, copy=False)

    def _propertio_owner_can_delete(self):
        """Yazılım Sahibi (sistem yöneticisi) veya çerçeve/sudo işlemleri fiziksel
        silme yapabilir. Mesajın belirttiği "Software Owner" pratikte
        base.group_system yetkisine sahip yönetici hesabıdır; ayrıca Odoo'nun
        kendi iç işlemleri (mutabakat geri alma, rapor render, yeniden hesaplama)
        sudo/su modunda çalıştığında engellenmemelidir."""
        env = self.env
        if env.su or env.uid == SUPERUSER_ID:
            return True
        if env.context.get('propertio_financial_internal'):
            return True
        try:
            return env.user.has_group('base.group_system')
        except Exception:
            return False

    def write(self, vals):
        protected = {'amount', 'date', 'payment_type', 'partner_id', 'journal_id', 'currency_id', 'state'}
        if (
            not self.env.context.get('propertio_financial_internal')
            and protected.intersection(vals)
            and self.filtered(lambda p: p.state not in ('draft',))
            and not self._propertio_owner_can_delete()
        ):
            for rec in self:
                rec._audit_log(
                    'blocked',
                    {'blocked_values': vals, 'message': 'Account payment mutation requires reversal workflow.'},
                    original_model=rec._name,
                    original_res_id=rec.id,
                )
                rec.message_post(body=_('Blocked account.payment mutation. Create a refund/reversal instead.'))
            raise UserError(_('Posted account payments are immutable. Create a refund/reversal; only the Software Owner can physically alter them.'))
        return super().write(vals)

    def unlink(self):
        if self._propertio_owner_can_delete():
            return super().unlink()
        for rec in self:
            rec._audit_log(
                'blocked',
                {'message': 'account.payment deletion blocked.'},
                original_model=rec._name,
                original_res_id=rec.id,
            )
            rec.message_post(body=_('Deletion blocked by financial anti-fraud protocol. Create a refund/reversal instead.'))
        raise UserError(_('Account payments cannot be deleted. Only the Software Owner can physically delete records.'))
