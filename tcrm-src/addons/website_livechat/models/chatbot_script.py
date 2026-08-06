# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models


class ChatbotScript(models.Model):
    _inherit = 'chatbot.script'

    def action_test_script(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/chatbot/%s/test' % self.id,
            'target': 'self',
        }
