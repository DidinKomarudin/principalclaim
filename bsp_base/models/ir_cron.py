from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import config


class IrCron(models.Model):
    _inherit = 'ir.cron'

    @classmethod
    def _process_job(cls, job_cr, job, cron_cr):
        if config.get('skip_cron'):
            return False
        res = super(IrCron, cls)._process_job(job_cr, job, cron_cr)
        return res

    @api.multi
    def method_direct_trigger(self):
        if config.get('skip_cron'):
            return False
        res = super(IrCron, self).method_direct_trigger()
        return res
