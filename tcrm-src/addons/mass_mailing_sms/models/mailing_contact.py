# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import fields, models


class MailingContact(models.Model):
    _name = 'mailing.contact'
    _inherit = ['mailing.contact', 'mail.thread.phone']

    mobile = fields.Char(string='Mobile')
