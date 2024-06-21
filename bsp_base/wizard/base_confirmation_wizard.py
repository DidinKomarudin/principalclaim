from odoo import fields, api, models, _
from odoo.exceptions import Warning

class BaseConfirmationWizard(models.TransientModel):
    _name = "base.confirmation.wizard"
    _description = "Base Confirmation Wizard"

    name = fields.Char(default='Do you want to process it?')
    action = fields.Char()

    @api.multi
    def action_confirm(self):
        if self._context.get('active_id') and self._context.get('active_model'):
            res_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
            res_ids = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))
        else :
            res_id = res_ids = self
        return self._action_confirm(res_id, res_ids)

    @api.multi
    def _action_confirm(self, res_id, res_ids):
        raise Warning(_("Action not implemented."))
