# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm.http import request, route
from tcrm.addons.mail.controllers import thread


class ThreadController(thread.ThreadController):
    @route()
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        if selected_answer_id := kwargs.pop("selected_answer_id", None):
            request.update_context(selected_answer_id=selected_answer_id)
        return super().mail_message_post(thread_model, thread_id, post_data, context, **kwargs)
