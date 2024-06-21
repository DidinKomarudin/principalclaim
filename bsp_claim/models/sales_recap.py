from datetime import date

from odoo import fields, models, api


class SalesRecap(models.Model):
    _name = 'bsp.sales.recap'
    _description = 'Monthly recap of sales by branch and principal'
    _sql_constraints = [
        ('value_recap_uniq', 'unique (yearperiod,monthperiod,branch_code,principal_code,division_code)', 'This attribute value already exists !')
    ]

    def _get_domain(self):
        return [('id', 'in', self.env.user.operating_unit_ids.ids)]

    @api.multi
    def _compute_ref_data(self):
        for rec in self:
            if rec.branch_code:
                # kode cabang dari BIS di cari di operating unit, harus sudah ada
                objbr = self.env['operating.unit'].search([('code', '=', rec.branch_code.strip())], limit=1)
                if objbr:
                    rec.operating_unit_id = objbr.id
            if rec.principal_code:
                # kode cabang dari BIS di cari di operating unit, harus sudah ada
                objpr = self.env['res.partner'].search([('ref', '=', rec.principal_code.strip())], limit=1)
                if objpr:
                    rec.partner_id = objpr.id

    @api.multi
    @api.depends('yearperiod','monthperiod')
    def _compute_eomday(self):
        """returns the number of days in a given month"""
        for rec in self:
            days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            d = days_per_month[rec.monthperiod - 1]
            if rec.monthperiod == 2 and (rec.yearperiod % 4 == 0 and rec.yearperiod % 100 != 0 or rec.yearperiod % 400 == 0):
                d = 29
            rec.dateperiod = date(rec.yearperiod, rec.monthperiod, d)

    @api.multi
    @api.depends('dateperiod', 'branch_code','principal_code')
    def _compute_claim_amount(self):
        for rec in self:
            period = rec.dateperiod.strftime("%Y%m")
            groups = self.env['bsp.creditnote.other'].read_group([('period','=',period),
                                                                  ('branch_code','=',rec.branch_code),
                                                                  ('principal_code','=',rec.principal_code)],
                                                                 ['cn_date', 'cn_total','paid_total'], ['cn_date:month'])
            for group in groups:
                rec.claim_amount = group['cn_total']
                rec.paid_amount = group['paid_total']

    yearperiod = fields.Integer("Year Period", required=True)
    monthperiod = fields.Integer("Month Period", required=True)
    dateperiod = fields.Date(compute="_compute_eomday", string="Date Period", store=True)
    branch_code = fields.Char("Branch code", size=5, required=True)
    operating_unit_id = fields.Many2one('operating.unit', 'Operating unit',
                                        default=lambda self: self.env.user.default_operating_unit_id.id,
                                        domain=_get_domain)
    principal_code = fields.Char("Principal Code", size=5)
    partner_id = fields.Many2one('res.partner', 'Principal Name',
                                 required=False)
    division_code = fields.Char("Division Code", size=5)
    sales_amount = fields.Float("Sales Amount")
    claim_amount = fields.Float("Claim Amount", compute='_compute_claim_amount', store=True)
    paid_amount = fields.Float("Paid Amount", compute='_compute_claim_amount', store=True)

    @api.model
    def create(self, vals):
        if 'branch_code' in vals:
            # kode cabang dari BIS di cari di operating unit, harus sudah ada
            # vals['branch_code'] = (vals['branch_code']).strip()
            objou = self.env['operating.unit'].search([('code', '=', vals['branch_code'])], limit=1)
            if objou:
                vals['operating_unit_id'] = objou.id
        if 'principal_code' in vals:
            # kode principal dari BIS di cari di res.partner, harus ada
            # vals['principal_code'] = (vals['principal_code']).strip()
            objpart = self.env['res.partner'].search([('ref', '=', vals['principal_code'])], limit=1)
            if objpart:
                vals['partner_id'] = objpart.id
        result = super(SalesRecap, self).create(vals)
        return result

    @api.multi
    def write(self, vals):
        if 'branch_code' in vals:
            # kode cabang dari BIS di cari di operating unit, harus sudah ada
            # vals['branch_code'] = (vals['branch_code']).strip()
            objou = self.env['operating.unit'].search([('code', '=', vals['branch_code'])], limit=1)
            if objou:
                vals['operating_unit_id'] = objou.id
        if 'principal_code' in vals:
            # kode principal dari BIS di cari di res.partner, harus ada
            # vals['principal_code'] = (vals['principal_code']).strip()
            objpart = self.env['res.partner'].search([('ref', '=', vals['principal_code'])], limit=1)
            if objpart:
                vals['partner_id'] = objpart.id

        result = super(SalesRecap, self).write(vals)
        return result
