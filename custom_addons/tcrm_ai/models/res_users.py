# Part of TCRM AI. See LICENSE for details.

from markupsafe import Markup

from tcrm import models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _init_tcrmbot(self):
        """Replace tcrmBot welcome with TCRM AI welcome."""
        self.ensure_one()
        tcrmbot_id = self.env['ir.model.data']._xmlid_to_res_id('base.partner_root')
        channel = self.env['discuss.channel']._get_or_create_chat([tcrmbot_id, self.partner_id.id])
        message = Markup(
            _("Hello, I'm <b>TCRM AI</b>.<br/>Ask me about payment plans, sales, contracts, or anything. "
              "I can read this database and give you links to open records in TCRM.")
        )
        channel.sudo().message_post(
            author_id=tcrmbot_id,
            body=message,
            message_type='comment',
            silent=True,
            subtype_xmlid='mail.mt_comment',
        )
        self.sudo().tcrmbot_state = 'idle'
        return channel
