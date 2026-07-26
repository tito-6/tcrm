# Part of Tcrm. See LICENSE file for full copyright and licensing details.
from tcrm import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'it')], order="parent_path"):
        env['account.chart.template'].try_loading('it', company, force_create=False)
