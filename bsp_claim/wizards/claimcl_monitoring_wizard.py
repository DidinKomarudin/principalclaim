from odoo import api, fields, models, _


class ClaimCLMonitoringReport(models.TransientModel):
    _name = 'claim.cl.monitoring.report'
    _description = 'Claim to Principal Report History'

    @api.multi
    def _compute_is_branch(self):
        for rec in self:
            if self.user_has_groups('bsp_claim.group_claim_view_user') or \
                    self.user_has_groups('bsp_claim.group_claim_branch_manajer'):
                rec.is_branch = True
            else:
                rec.is_branch = False
    def get_types(self):
        types = self.env['bsp.claim.type'].search([])
        lst = []
        for tp in types:
            lst.append((tp.code, tp.name))
        return lst


    def _get_domain(self):
        return [('id', 'in', self.env.user.operating_unit_ids.ids),('parent_id','=',False)]

    is_branch = fields.Boolean(compute="_compute_is_branch")
    branch_id = fields.Many2one('operating.unit', string='Branch',
                                default=lambda self: self.env.user.default_operating_unit_id.id,
                                domain=_get_domain)

    partner_id = fields.Many2one('res.partner', string='Principal', domain="[('supplier','=',True)]")
    claim_type = fields.Selection(selection='get_types', string='Claim Type')

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
        action_name = 'bsp_claim.action_claim_cl_monitoring_report'
        claimtype = "ALL Type"

        domain = [
            ('claim_date', '>=', self.date_from),
            ('claim_date', '<=', self.date_to)]
        if self.claim_type:
            # claimtype = dict(self._fields['claim_type'].selection).get(self.claim_type)
            claimtype = self.env['bsp.claim.type'].search_read([('code', '=', self.claim_type)],
                                                               ['name'], limit=1)[0]['name']
            domain.append(('claim_type', '=', self.claim_type))
            if self.claim_type in ('cncl', 'discount', 'faktur', 'noncl', 'mix'):
                action_name = 'bsp_claim.action_claim_cl_monitoring_report'
            else:
                action_name = 'bsp_claim.action_claim_type_monitoring_report'
            # elif self.claim_type=='discount':
            # elif self.claim_type=='cabang':
            #     action_name = 'bsp_claim.action_claim_type_monitoring_report'
            # elif self.claim_type=='manual':
            #     action_name = 'bsp_claim.action_claim_type_monitoring_report'
            # elif self.claim_type=='barang':
            #     action_name = 'bsp_claim.action_claim_type_monitoring_report'

        action = self.env.ref(action_name)


        if self.partner_id:
            domain.append(('partner_id.id', '=', self.partner_id.id))

        if self.branch_id:
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
        if self.claim_type:
            vals2["context"] = {'filtertype':True}

        vals2["name"] = "Claim Monitoring Report: " + claimtype
        vals2["domain"] = domain
        return vals2

    def _prepare_claim_monitoring_report(self):
        self.ensure_one()
        return {
            'date_from': self.date_from,
            'date_to': self.date_to or fields.Date.context_today(self),
        }
