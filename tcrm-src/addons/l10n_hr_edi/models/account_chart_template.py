# Part of Tcrm. See LICENSE file for full copyright and licensing details.
from tcrm import models
from tcrm.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('hr', 'account.tax')
    def _get_hr_edi_account_tax(self):
        return self._parse_csv('hr', 'account.tax', module='l10n_hr_edi')
