from odoo import  api, fields, models, _
from datetime import date, datetime
from odoo.exceptions import ValidationError

class KC(models.Model):
    _name = 'bsp.kc'
    _description = 'Branch Correspondence'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_domain(self):
        return [('id', 'in', self.env.user.operating_unit_ids.ids)]

    @api.multi
    @api.constrains('valid_from', 'valid_to')
    def date_constrains(self):
        for rec in self:
            if rec.valid_to < rec.valid_from:
                raise ValidationError(_('Sorry, Valid From  Must be greater Than Valid To...'))

    @api.multi
    @api.constrains('claim_period_from', 'claim_period_to')
    def date_constrains(self):
        for rec in self:
            if rec.claim_period_to < rec.claim_period_from:
                raise ValidationError(_('Sorry, Claim Period From  Must be greater Than Claim Period To...'))

    name = fields.Char("KC Number", size=30, required=True)
    kc_type = fields.Selection(
                  [('diskon', 'DISCOUNT'),
                   ('promo', 'PROMOTION')],
                    string='KC Type', default='diskon')
    kc_date = fields.Date("KC Date", copy=False, required=True, default=datetime.now().date())
    partner_id = fields.Many2one('res.partner', 'Principal', required=True)
    valid_from = fields.Date("Valid From", required=True, default=datetime.now().date())
    valid_to = fields.Date("Valid To", required=True, default=datetime.now().date())
    claim_period_from = fields.Date("Claim Period From", default=datetime.now().date())
    claim_period_to = fields.Date("Claim Period To", default=datetime.now().date())
    reference_no = fields.Char("Reference Number", size=30)
    operating_unit_ids = fields.Many2many('operating.unit',
                                          string='Branch',
                                          domain=_get_domain,
                                          required=False)
    refoutlet = fields.Char("Outlet")
    doc_kc = fields.Binary(
        "Doc. KC", attachment=True,
        help="This field holds the image used as image for the KCs, limited to 1024x1024px.")
    file_name = fields.Char("Nama File", size=256)
    remark = fields.Char("Program")
    notes = fields.Text("Description")
    state = fields.Selection(
        [('draft', 'DRAFT'),
         ('pending', 'PENDING'),
         ('post', 'POST'),
         ('cancel', 'CANCEL')],
                    string='KC Status', track_visibility='always', default='draft')


    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag KC Number already exists !"),
    ]

    @api.multi
    def write(self, vals):
        result = super(KC, self).write(vals)
        return result

    @api.multi
    def button_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def button_pending(self):
        return self.write({'state': 'pending'})

    @api.multi
    def button_post(self):
        return self.write({'state': 'post'})

    @api.multi
    def button_cancel(self):
        return self.write({'state': 'cancel'})