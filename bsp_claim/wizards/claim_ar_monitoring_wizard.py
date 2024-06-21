from calendar import monthrange
from datetime import datetime

from odoo import api, fields, models, _


class ClaimARMonitoringReport(models.TransientModel):
    _name = 'claim.ar.monitoring.report'
    _description = 'Claim AR BAlance Monitoring Report'

    @api.multi
    def _compute_is_branch(self):
        for rec in self:
            if self.user_has_groups('bsp_claim.group_claim_view_user') or \
                    self.user_has_groups('bsp_claim.group_claim_branch_manajer'):
                rec.is_branch = True
            else:
                rec.is_branch = False


    def _get_domain(self):
        return [('id', 'in', self.env.user.operating_unit_ids.ids),('parent_id','=',False)]

    @api.depends('year_period','month_period')
    def _get_periode(self):
        for ar in self:
            ar.date_from = datetime.strptime("%s-%s-01" % (ar.year_period,ar.month_period), '%Y-%m-%d').date()
            mdays = monthrange(ar.date_from.year, ar.date_from.month)[1]
            ar.date_to = datetime.strptime("%s-%s-%s" % (ar.year_period, ar.month_period,str(mdays)), '%Y-%m-%d').date()

    is_branch = fields.Boolean(compute="_compute_is_branch")
    branch_id = fields.Many2one('operating.unit', string='Branch',
                                domain=_get_domain)

    partner_id = fields.Many2one('res.partner', string='Principal', domain="[('supplier','=',True)]")

    date_from = fields.Date(
        string='Start Date', compute='_get_periode'
    )
    date_to = fields.Date(
        string='End Date', compute='_get_periode'
    )
    month_period = fields.Selection(
        [('1', 'January'),
         ('2', 'February'),
         ('3', 'March'),
         ('4', 'April'),
         ('5', 'May'),
         ('6', 'June'),
         ('7', 'July'),
         ('8', 'August'),
         ('9', 'September'),
         ('10', 'October'),
         ('11', 'November'),
         ('12', 'December'),
         ],
        string='Month ', required=True, default= lambda self: str(fields.Date.today().month))

    year_period = fields.Selection(
        [('2020', '2020'),
         ('2021', '2021'),
         ('2022', '2022'),
         ('2023', '2023'),
         ('2024', '2024'),
         ('2025', '2025'),
         ('2026', '2026'),
         ('2027', '2027'),
         ('2028', '2028'),
         ('2029', '2029'),
         ('2030', '2030'),
         ],
        string='Year', required=True, default=lambda self:str(fields.Date.today().year))


    # @api.onchange('date_range_id')
    # def _onchange_date_range_id(self):
    #     self.date_from = self.date_range_id.date_start
    #     self.date_to = self.date_range_id.date_end

    @api.multi
    def button_open(self):
        self.ensure_one()
        action_name = 'bsp_claim.action_claim_ar_monitoring_report'


        domain = [
            ('send_date', '>=', self.date_from),
            ('send_date', '<=', self.date_to)]


        action = self.env.ref(action_name)

        partner = 'ALL'
        if self.partner_id:
            partner = self.partner_id.ref
            domain.append(('partner_id.id', '=', self.partner_id.id))

        branch = 'ALL'
        if self.branch_id:
            branch = self.branch_id.code
            domain.append(('operating_unit_id.id', '=', self.branch_id.id))

        vals = action.read()[0]
        vals2 = {}
        vals2.update({
            'views': vals['views'],
            'context': vals['context'],
            'res_model': vals['res_model'],
            'view_type': vals['view_type'],
            'view_mode': vals['view_mode'],
            'target': vals['target'],
            'type': vals['type'],
        })


        month_name = dict(self._fields['month_period'].selection).get(self.month_period)
        vals2["name"] = "AR Claim Per %s %s Branch:%s Principal:%s" % (month_name,self.year_period, branch, partner)
        vals2["domain"] = domain
        return vals2

    def _prepare_claim_ar_monitoring_report(self):
        self.ensure_one()
        return {
            'date_from': self.date_from,
            'date_to': self.date_to or fields.Date.context_today(self),
        }
