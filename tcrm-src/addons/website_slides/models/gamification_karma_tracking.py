# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import _, models


class GamificationKarmaTracking(models.Model):
    _inherit = 'gamification.karma.tracking'

    def _get_origin_selection_values(self):
        return (
            super()._get_origin_selection_values()
            + [('slide.slide', _('Course Quiz')), ('slide.channel', self.env['ir.model']._get('slide.channel').display_name)]
        )
