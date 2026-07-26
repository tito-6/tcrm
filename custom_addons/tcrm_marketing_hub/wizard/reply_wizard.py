# -*- coding: utf-8 -*-
from tcrm import _, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import ZernioError


class ReplyWizard(models.TransientModel):
    _name = 'tcrm.marketing.reply.wizard'
    _description = 'Gelen Kutusu Yanıtı'

    conversation_id = fields.Many2one('tcrm.marketing.conversation', required=True)
    message = fields.Text(string='Yanıt', required=True)

    def action_send(self):
        self.ensure_one()
        conv = self.conversation_id
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            client.send_inbox_message(
                conv.zernio_id,
                account_id=conv.account_id.zernio_id,
                message=self.message,
            )
        except ZernioError as exc:
            raise UserError(str(exc)) from exc
        conv.action_load_messages()
        conv.last_message = self.message
        conv.last_message_at = fields.Datetime.now()
        return {'type': 'ir.actions.act_window_close'}


class CommentReplyWizard(models.TransientModel):
    _name = 'tcrm.marketing.comment.reply.wizard'
    _description = 'Yorum Yanıtı'

    comment_id = fields.Many2one('tcrm.marketing.comment', required=True)
    message = fields.Text(string='Yanıt', required=True)

    def action_send(self):
        self.ensure_one()
        comment = self.comment_id
        if not comment.account_id:
            raise UserError(_('Yorumun bağlı sosyal hesabı yok.'))
        post_id = comment.post_id_remote or comment.zernio_id
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            client.reply_comment(
                post_id,
                account_id=comment.account_id.zernio_id,
                message=self.message,
                comment_id=comment.zernio_id,
            )
        except ZernioError as exc:
            raise UserError(str(exc)) from exc
        return {'type': 'ir.actions.act_window_close'}
