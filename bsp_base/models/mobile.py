from odoo.exceptions import ValidationError
from odoo import api, fields, models, _

class Mobile(models.AbstractModel):
    _name = "mobile"
    _description = "Mobile"

    inprogress_mobile = fields.Boolean(
        string='Inprogress Mobile',
        copy=False)
    assign_to = fields.Many2one(
        comodel_name='res.users',
        string='Assign To',
        track_visibility='onchange',
        copy=False
    )

    @api.multi
    def check_mobile_status(self):
        for rec in self :
            if rec.inprogress_mobile:
                raise ValidationError(_('Can not edit record %s, because mobile is in progress status' % (rec.display_name)))
        return True

    @api.multi
    def write(self, values):
        for rec in self :
            # self.env.user.log_info('self._context mobile %s' % (self._context))
            if self._context.get('source', 'odoo') != 'mobile':
                rec.check_mobile_status()
        return super(Mobile, self).write(values)

class MobileLine(models.AbstractModel):
    _name = "mobile.line"
    _description = "Mobile Line"

    is_checked = fields.Boolean(
        string='Is Checked',
        copy=False)
    time_checked = fields.Datetime(
        string='Time Checked',
        copy=False)
    time_hold = fields.Datetime(
        string='Time Hold',
        copy=False)
    time_continue = fields.Datetime(
        string='Time Continue',
        copy=False)
