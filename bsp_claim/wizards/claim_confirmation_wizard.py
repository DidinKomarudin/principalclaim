from odoo import models, fields, api

class confirm_wizard(models.TransientModel):
    _name = 'claim.confirm.wizard'

    yes_no = fields.Char(default='Do you want to proceed?')
    btn_ok = fields.Boolean(default=False)

    @api.multi
    def yes(self):
        return True

    @api.multi
    def no(self):
        return False
