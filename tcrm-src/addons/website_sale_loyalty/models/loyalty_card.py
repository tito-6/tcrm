# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models


class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'

    def action_coupon_share(self):
        self.ensure_one()
        return self.env['coupon.share'].create_share_action(coupon=self)
