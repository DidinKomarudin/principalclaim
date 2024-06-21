from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResCompany(models.Model):
    _inherit = 'res.company'

    use_websocket = fields.Boolean(
        string='Use Websocket ?'
    )

    @api.multi
    def data_correction(self):
        self.env.user.log_info(_('Data correction is running.'))

    @api.multi
    def daily_jobs(self):
        # ada error "VACUUM cannot run inside a transaction block"
        # self._cr.execute("""
        #     VACUUM FULL;
        # """)
        self.env.user.log_info(_('Daily jobs is running.'))
