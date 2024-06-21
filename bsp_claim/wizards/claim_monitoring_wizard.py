from odoo import api, fields, models, _


class ClaimMonitoringReport(models.TransientModel):
    _name = 'claim.monitoring.report'
    _description = 'Claim to Principal Report History'

    branch_code = fields.Char('Branch Code', size=4)
    partner_id = fields.Many2one('res.partner', string='Principal', domain="[('supplier','=',True)]")
    # date_range_id = fields.Many2one(
    #     comodel_name='date.range',
    #     string='Period',
    # )
    date_from = fields.Date(
        string='Start Date', default=lambda self: fields.Date.context_today(self)
    )
    date_to = fields.Date(
        string='End Date', default=lambda self: fields.Date.context_today(self)
    )


    # @api.onchange('date_range_id')
    # def _onchange_date_range_id(self):
    #     self.date_from = self.date_range_id.date_start
    #     self.date_to = self.date_range_id.date_end

    @api.multi
    def button_open(self):
        self.ensure_one()
        action = self.env.ref(
            'bsp_claim.action_claim_monitoring_report')
        domain = [
            ('claim_date', '>=', self.date_from),
            ('claim_date', '<=', self.date_to)]

        if self.partner_id:
            domain.append(('principal', '=', self.partner_id.ref))

        if self.branch_code:
            domain.append(('branch', '=', self.branch_code))

        vals = action.read()[0]
        vals["domain"] = domain
        return vals

    def _prepare_claim_monitoring_report(self):
        self.ensure_one()
        return {
            'date_from': self.date_from,
            'date_to': self.date_to or fields.Date.context_today(self),
        }
