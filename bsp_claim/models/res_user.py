import datetime

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError, UserError


class ChangePasswordUser(models.TransientModel):
    _inherit = 'change.password.user'

    def change_password_button(self):
        curent_user_id = self.env.user.id
        for line in self:
            if line.user_id.id in (1, 2) and curent_user_id not in (1, 2):
                raise UserError(_("Sorry. you do have permission to change admin password!"))
        res = super(ChangePasswordUser, self).change_password_button()

# class ResUsers(models.Model):
#     _inherit = 'res.users'
#
#     def dt_timezone(tz, dt=False, format='datetime'):
#         if not dt:
#             dt = datetime.now()
#         if type(dt) is str:
#             dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
#         final_date = datetime.UTC.localize(dt).astimezone(datetime.timezone(tz))
#         if format != 'datetime':
#             final_date = final_date.strftime('%Y-%m-%d %H:%M:%S')
#         return final_date
#     def date_timezone(self, dt=False, format='datetime'):
#         self.ensure_one()
#         if not self.tz:
#             raise ValidationError(_(f'Please set timezone for user {self.display_name}.'))
#         return self.dt_timezone(self.tz, dt=dt, format=format)

