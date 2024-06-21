from odoo.exceptions import ValidationError
from odoo import api, fields, models, _


class BIS(models.AbstractModel):
    _name = "bis"
    _description = "BIS"

    inprogress_bis = fields.Boolean(
        string='Inprogress BIS',
        copy=False)

    @api.multi
    def check_bis_status(self):
        for rec in self:
            if rec.inprogress_bis:
                raise ValidationError(_('Can not edit record %s, because BIS is in progress status'
                                        % rec.display_name))
        return True

    @api.multi
    def write(self, values):
        for rec in self:
            # self.env.user.log_info('self._context bis %s' % (self._context))
            if self._context.get('source', 'odoo') != 'bis':
                rec.check_bis_status()
        return super(BIS, self).write(values)
