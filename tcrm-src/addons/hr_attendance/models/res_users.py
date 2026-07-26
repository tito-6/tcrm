# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _clean_attendance_officers(self):
        attendance_officers = self.env['hr.employee'].search(
            [('attendance_manager_id', 'in', self.ids)]).attendance_manager_id
        officers_to_remove_ids = self - attendance_officers
        if officers_to_remove_ids:
            self.env.ref('hr_attendance.group_hr_attendance_officer').user_ids = [(3, user.id) for user in
                                                                               officers_to_remove_ids]
