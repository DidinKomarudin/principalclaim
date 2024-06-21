import logging
from datetime import datetime, timedelta

from odoo import  api, fields, models, _
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger(__name__)

class CNOthers(models.Model):
    _name = 'bsp.creditnote.other'
    _description = "BSP CLAIM to Principal"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('operating_unit_id')
    def _compute_operating_unit(self):
        for record in self:
            if record.operating_unit_id:
                record.branch_code = record.operating_unit_id.code
            # objou = self.env['operating.unit'].search([('code', '=', record.branch_code)], limit=1)
            # if objou:
            #     record.operating_unit_id = objou.id

    @api.depends('cn_type')
    def _compute_is_partial(self):
        # print('run _compute_is_partial')
        for rec in self:
            rec.is_can_partial = False
            objType = self.env['bsp.claim.type'].search([('code', '=', rec.cn_type)], limit=1)
            if objType:
                rec.is_can_partial = objType.is_can_partial

    @api.depends('partner_id')
    def _compute_principal(self):
        for record in self:
            if record.partner_id:
                record.principal_code = record.partner_id.ref

            # obj_partner = self.env['res.partner'].search([('ref', '=', record.principal_code)], limit=1)
            # if obj_partner:
            #     record.partner_id = obj_partner.id

    def _inverse_operating_unit(self):
        return True

    def _inverse_principal(self):
        return True

    def _get_domain(self):
        return [('id', 'in', self.env.user.operating_unit_ids.ids)]

    # @api.depends('alloc_ids.allocation_amount')
    @api.depends('allocated_amount')
    def _compute_allocated_amount(self):
        for record in self:
            # record.allocated_amount = 0
            # record.is_allocated =False
            # for line in record.alloc_ids:
            #     record.allocated_amount += line.allocation_amount
            record.notallocated_amount =record.cn_total - record.allocated_amount
            if record.allocated_amount > 0:
                record.is_allocated = True

    @api.depends('alloc_dates')
    def _compute_alloc_date(self):
        for record in self:
            record.alloc_dates = ''
            for line in record.alloc_ids:
                if line.allocation_date:
                    if record.alloc_dates == '':
                        record.alloc_dates = line.allocation_date.strftime("%d-%m-%Y")
                    else:
                        record.alloc_dates = record.alloc_dates +", "+ line.allocation_date.strftime("%d-%m-%Y")



    @api.onchange('allocated_amount')
    def _onchange_allocated_amount(self):
        for rec in self:
            if rec.allocated_amount > 0:
                if rec.alloc_move_id:
                    if rec.allocated_amount != rec.alloc_move_id.amount:
                        rec.alloc_move_id.button_cancel()
                        objMove = rec.alloc_move_id
                        rec.write({'alloc_move_id': False})
                        objMove.unlink()
                        rec.alloc_move_id = self.create_claim_journal('A', self.prepare_allocation_journal())
                else:
                    rec.alloc_move_id = self.create_claim_journal('A', self.prepare_allocation_journal())

    def _inverse_update_free(self):
        return True

    def _get_claim_ids(self):
        for cn in self:
            lclaim_number = []
            for claim in cn.claimcl_ids:
                lclaim_number.append(claim.claimcl_id.name)
            cn.lclaim_number = ', '.join(lclaim_number)

    @api.multi
    @api.depends('cn_total', 'paid_total')
    def _compute_remain_amount(self):
        for rec in self:
            rec.remain_total = 0
            if rec.cn_total > rec.paid_total:
                rec.remain_total = rec.cn_total - rec.paid_total

    def substring(self, s, beginning, length):
        return s[beginning: beginning + length]

    @api.multi
    @api.depends('name', 'customer_code')
    def _compute_cn_type(self):
        for rec in self:
            tipe = rec.name[:2]
            if tipe == 'CL':
                rec.cn_type = 'cncl'
            elif tipe == 'FK':
                if rec.name[-3:] in ('PRM', 'MTC','PPM'):
                    rec.cn_type = 'noncl'
                else:
                    rec.cn_type = 'faktur'
            elif tipe == 'KL':
                tp = self.substring(rec.name, 3, 2)
                if tp in ('BB', 'FB'):
                    rec.cn_type = 'barang'
                else:
                    rec.cn_type = 'discount'
            elif tipe == 'KK':
                if rec.customer_code == '1.1':
                    rec.cn_type = 'salary'
                elif rec.customer_code == '2.1':
                        rec.cn_type = 'insentif'
                elif rec.customer_code =='10.4':
                    rec.cn_type = 'pph23'
                elif rec.customer_code == '10.10':
                        rec.cn_type = 'pph21'
                elif rec.customer_code == '17.2':
                    rec.cn_type = 'promosi'
                elif rec.customer_code == '28.2':
                        rec.cn_type = 'ump'

            else:
                rec.cn_type = 'manual'


    READONLY_STATES = {
        'post': [('readonly', True)],
        'printed': [('readonly', True)],
        'paid': [('readonly', True)],
        'done': [('readonly', True)],
        'cabang': [('readonly', True)],
        'pusat': [('readonly', True)],
        'rejected': [('readonly', True)],
        'canceled': [('readonly', True)],
    }

    @api.depends('claimcl_id', 'cn_type', 'total_claimed_amount')
    def _compute_is_select(self):
        for rec in self:
            rec.is_select = True
            # if rec.cn_type == 'discount':
            if rec.is_can_partial:
                if rec.cn_total <= rec.total_claimed_amount:
                    rec.is_select = False
            elif rec.claimcl_id.id:
                rec.is_select = False

    @api.multi
    @api.depends('notes', 'state', 'claimcl_id')
    def _compute_cancel_invisible(self):
        for rec in self:
            rec.is_cancel_invisible = True
            notes = ''
            if rec.notes:
                notes = rec.notes.strip()
            if (rec.state in ('printed','draft','cabang','pusat','post') and notes != '' and rec.claimcl_id.id == False
                    and self.user_has_groups('bsp_claim.group_claim_branch_spv')) \
                    and not self.user_has_groups('bsp_claim.group_claim_user'):
                rec.is_cancel_invisible = False

    @api.onchange('cn_type')
    def _onchange_cn_type(self):
        self.ensure_one()
        # Set partner_id domain
        if self.cn_type:
            return {'domain': {'cn_ids': [('principal_code', '=', self._context.get('partner_id')),
                           ('state', 'in', self._context.get('state')),
                           ('cn_type', 'in', self._context.get('cn_type')),
                           ('is_select', '=', True)]}}

    is_select = fields.Boolean(compute="_compute_is_select", store=True)
    is_cancel_invisible = fields.Boolean(default=True, compute="_compute_cancel_invisible", store=False)
    name = fields.Char("CN Number", size=30,
                       default='New', required=True, copy=False, readonly=False, states=READONLY_STATES)
    # lambda self: self.env['ir.sequence'].next_by_code('bsp.creditnote.other'))
    cn_type = fields.Selection(
        [('cncl', 'CNCL'),
         ('discount', 'DISCOUNT'),
         ('barang', 'BARANG'),
         ('faktur', 'FAKTUR'),
         ('noncl', 'NON-CL'),
         ('manual', 'MANUAL')],
        compute='_compute_cn_type', string='CN Type', store=True, states=READONLY_STATES)
    is_can_partial = fields.Boolean('Can Partial Claim', compute='_compute_is_partial', store=False)
    cn_date = fields.Date("CN Date", required=True, default=datetime.now().date(), copy=False, states=READONLY_STATES)
    period = fields.Char("CN Period", size=20, required=True, default=datetime.now().strftime('%Y%m'), copy=False, states=READONLY_STATES)
    branch_code = fields.Char("Branch code", size=5, required=True, states=READONLY_STATES, compute='_compute_operating_unit', inverse='_inverse_operating_unit',  store=True)
    operating_unit_id = fields.Many2one('operating.unit', 'Operating unit', required=True, states=READONLY_STATES,
                                        default=lambda self: self.env.user.default_operating_unit_id.id,
                                        domain=_get_domain)

    customer_code = fields.Char("Customer Code", size=10, states=READONLY_STATES)
    customer_name = fields.Char("Customer Name", states=READONLY_STATES)
    cn_total = fields.Float(string='CN Total', states=READONLY_STATES)
    paid_total = fields.Float(string='Paid Total', readonly=True, states=READONLY_STATES)
    ump_amount = fields.Float("UMP", states=READONLY_STATES)
    state = fields.Selection(
        [('draft', 'DRAFT'),
         ('pending', 'PENDING'),
         ('post', 'POST'),
         ('printed', 'PRINTED'),
         ('paid', 'PAID'),
         ('done', 'DONE'),
         ('cabang', 'CABANG'),
         ('pusat', 'PUSAT'),
         ('canceled', 'CANCELED'),
         ('rejected', 'REJECTED')],
        string='Status', track_visibility='always', default='draft', copy=False, states=READONLY_STATES)
    partner_id = fields.Many2one('res.partner', 'Principal Name', required=False, states=READONLY_STATES)
    ref = fields.Char(related="partner_id.ref", string="Principal Code", readonly=True, store=False)
    principal_code = fields.Char("Principal Code", size=5, compute='_compute_principal', inverse='_inverse_principal', store=True, states=READONLY_STATES)
    division_code = fields.Char("Division Code", size=5, states=READONLY_STATES)
    bsp_share = fields.Float("BSP share", states=READONLY_STATES)
    principal_share = fields.Float("Principal share", states=READONLY_STATES)
    kc_no = fields.Char("KC Number", size=30)     # , states=READONLY_STATES)
    opu_no = fields.Char("OPU Number", size=30, states=READONLY_STATES)
    hobccd_no = fields.Char("HO BCCD Number", size=30, states=READONLY_STATES)
    branch_claim_no = fields.Char("Branch Claim Number", size=30, states=READONLY_STATES)
    remark = fields.Char("Program", states=READONLY_STATES)
    notes = fields.Char("Notes")
    claim_id = fields.Many2one('bsp.claim.principal', string='Claim Collection (KX)', states=READONLY_STATES)
    claimcl_id = fields.Many2one('bsp.claim.cl', string='Claim Collection', readonly=True)
    claimcl_ids = fields.One2many('bsp.claim.cl.line','cn_id', string='Claims Collection', readonly=True)
    alloc_ids = fields.One2many('bsp.creditnote.alloc', 'cn_id', String="Claim Allocations")
    kl_ids = fields.One2many('bsp.creditnote.kl.lines', 'cn_id', String="KL Product Items")
    exim_status = fields.Char("Exim status", size=3, states=READONLY_STATES)
    allocated_amount = fields.Float(string='Allocated Amount',
                                    # compute='_compute_allocated_amount',
                                    # inverse='_inverse_update_free',
                                    store=True, states=READONLY_STATES)
    is_allocated = fields.Boolean(string='Is Allocated', compute='_compute_allocated_amount', store=True)
    notallocated_amount = fields.Float(string='Not Allocated Amount', compute='_compute_allocated_amount')
    from_date = fields.Date("Begin Period", copy=False, states=READONLY_STATES)
    end_date = fields.Date("End Period", copy=False, states=READONLY_STATES)
    remain_total = fields.Float(string='Remain Total',compute='_compute_remain_amount', store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id, states=READONLY_STATES)
    journal_id = fields.Many2one('account.journal', string='Journal', default=lambda self: self.env["account.journal"].search([('code', '=', 'CJC')], limit=1), states=READONLY_STATES)
    create_move_id = fields.Many2one('account.move', string='Journal Create CN', ondelete='restrict', readonly=True, copy=False)
    alloc_move_id = fields.Many2one('account.move', string='Journal Alloc CN', ondelete='restrict', readonly=True, copy=False)
    total_claimed_amount = fields.Float(string='Total Claimed',
                                    default=0, states=READONLY_STATES)
    alloc_dates = fields.Char(string='Allocation Date', compute='_compute_alloc_date')
    lclaim_number = fields.Char('Claim Number', compute='_get_claim_ids')
    time_stamp = fields.Datetime("LastUpdate BIS")
    time_stamp_display = fields.Datetime("Last Update", compute='_get_time_stamp_display')

    _sql_constraints = [
        ('name_CN_unique_idx', 'unique (name)', "Tag Credit Note Number already exists !"),
    ]

    @api.depends('time_stamp')
    def _get_time_stamp_display(self):
        for v in self:
            v.time_stamp_display = v.time_stamp - timedelta(hours=7)
    def update_journals(self):
        create_move_id = cl.create_move_id


    @api.multi
    def button_journals(self):
        if self.cn_type == 'cncl':
            if not self.journal_id:
                self.journal_id = self.sudo().env["account.journal"].search([('code', '=', 'CJC')], limit=1)
            if not self.create_move_id:
                if self.cn_total > 0:
                    self.create_move_id = self.create_claim_journal('C', self.prepare_cl_journal())
            else:
                if (self.cn_total != self.create_move_id.amount) or (self.partner_id != self.create_move_id.partner_id):
                    self.create_move_id.button_cancel()
                    objMove = self.create_move_id
                    self.write({'create_move_id': False})
                    objMove.unlink()
                    self.create_move_id = self.create_claim_journal('C', self.prepare_cl_journal())

            if not self.alloc_move_id:
                if self.allocated_amount > 0:
                    self.alloc_move_id = self.create_claim_journal('A', self.prepare_allocation_journal())
            else:
                if (self.allocated_amount != self.alloc_move_id.amount) or (self.partner_id != self.alloc_move_id.partner_id):
                    self.alloc_move_id.button_cancel()
                    objMove = self.alloc_move_id
                    self.write({'alloc_move_id': False})
                    objMove.unlink()
                    self.alloc_move_id = self.create_claim_journal('A', self.prepare_allocation_journal())


    def button_journal_all(self):
        journal_id = self.sudo().env["account.journal"].search([('code', '=', 'CJC')], limit=1)
        cls = self.env['bsp.creditnote.other'].search([('branch_code', '=', self.branch_code),
                                                       ('cn_type', '=', 'cncl')])
                                                       # ('create_move_id', '=', False),
                                                       # ('alloc_move_id', '=', False)])
        if cls:
            for cl in cls:
                if not cl.journal_id:
                    cl.write({
                        'journal_id': journal_id.id
                    })

                create_move_id = cl.create_move_id
                alloc_move_id = cl.alloc_move_id
                if not cl.create_move_id:
                    if cl.cn_total > 0:
                        create_move_id = cl.create_claim_journal('C', cl.prepare_cl_journal())
                else:
                    if (cl.cn_total != cl.create_move_id.amount) or (
                            cl.partner_id != cl.create_move_id.partner_id):
                        cl.create_move_id.button_cancel()
                        objMove = cl.create_move_id
                        cl.write({'create_move_id': False})
                        objMove.unlink()
                        cl.create_move_id = cl.create_claim_journal('C', cl.prepare_cl_journal())

                if not cl.alloc_move_id:
                    if cl.allocated_amount > 0:
                        alloc_move_id = cl.create_claim_journal('A', cl.prepare_allocation_journal())
                else:

                    if cl.allocated_amount != cl.alloc_move_id.amount or (cl.partner_id != cl.alloc_move_id.partner_id):
                        cl.alloc_move_id.button_cancel()
                        objMove = cl.alloc_move_id
                        cl.write({'alloc_move_id': False})
                        objMove.unlink()
                        alloc_move_id = cl.create_claim_journal('A', cl.prepare_allocation_journal())

                # if create_move_id and alloc_move_id:
                cl.write({
                    'create_move_id': create_move_id.id or False,
                    'alloc_move_id': alloc_move_id.id or False
                })


    def prepare_cl_journal(self):
        data_final = []
        prepaid_claim_vals = (0, 0, {
            'name':  self.name,
            'partner_id': self.partner_id.id,
            'operating_unit_id': self.operating_unit_id.id,
            'date': self.cn_date,
            'company_id': self.env.user.company_id.id,
            'debit': self.cn_total,
            'credit': 0,
            'account_id': self.company_id.claim_prepaid_account_id.id,
        })
        data_final.append(prepaid_claim_vals)

        ump_vals = (0, 0, {
            'name': self.name,
            'partner_id': self.partner_id.id,
            'operating_unit_id': self.operating_unit_id.id,
            'date': self.cn_date,
            'company_id': self.env.user.company_id.id,
            'debit': 0,
            'credit': self.cn_total,
            'account_id': self.company_id.ump_account_id.id
        })
        data_final.append(ump_vals)
        return data_final

    def prepare_allocation_journal(self):
        data_final = []
        ump_vals = (0, 0, {
            'name': 'UMP ' + self.branch_code,
            'partner_id': self.partner_id.id,
            'operating_unit_id': self.operating_unit_id.id,
            'date': self.cn_date,
            'company_id': self.env.user.company_id.id,
            'debit': self.allocated_amount,
            'credit': 0,
            'account_id': self.company_id.ump_account_id.id
        })
        data_final.append(ump_vals)

        ar_vals = (0, 0, {
            'name': 'AR ' + self.branch_code,
            'partner_id': self.partner_id.id,
            'operating_unit_id': self.operating_unit_id.id,
            'date': self.cn_date,
            'company_id': self.env.user.company_id.id,
            'debit': 0,
            'credit': self.allocated_amount,
            'account_id': self.company_id.ar_account_id.id
        })
        data_final.append(ar_vals)
        return data_final


    def create_claim_journal(self, tp, journal_vals):
        move_id = self.env['account.move'].sudo().create({
            'name': tp + self.name,
            'ref':  self.name or '',
            'journal_id': self.journal_id.id,
            'date': self.cn_date,
            'company_id': self.env.user.company_id.id,
            'operating_unit_id': self.operating_unit_id.id,
            'line_ids': journal_vals,
        })
        move_id.post()
        return move_id




    @api.model
    def create(self, vals):
        # _logger.info('\n create vals ================>: %s', str(vals))
        if not self.user_has_groups('base.group_erp_manager'):
            raise UserError(_(
                "You just can create CL from BIS application"))

        if 'time_stamp' not in vals:
            vals['time_stamp'] = datetime.now() + timedelta(hours=7)

        if vals.get('name', 'New') == 'New':
            # jika nomor cn New, maka buatkan nomor baru, jika bukan New simpan apa adanya
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'bsp.creditnote.other') or 'New'
        else:
            if 'claim_id' in vals:
                kx_id = vals['claim_id']
                if type(kx_id) != int:
                    # jika claim_id bukan id, makan claim_id berisi nomor KX dari BIS, id cn harus di search dulu agar KX terhubung
                    objkx = self.env['bsp.claim.principal'].search([('name', '=', kx_id)], limit=1)
                    if objkx:
                        vals['claim_id'] = objkx.id
                    else:
                        vals['claim_id'] = False
            if 'branch_code' in vals:
                # kode cabang dari BIS di cari di operating unit, harus sudah ada
                objou = self.env['operating.unit'].search([('code', '=', vals['branch_code'])], limit=1)
                if objou:
                    vals['operating_unit_id'] = objou.id
            if 'principal_code' in vals:
                # kode principal dari BIS di cari di res.partner, harus ada
                objpart = self.env['res.partner'].search([('ref', '=', vals['principal_code'])], limit=1)
                if objpart:
                    vals['partner_id'] = objpart.id
        result = super(CNOthers, self).create(vals)
        result.sudo().button_journals()
        return result



    @api.multi
    def write(self, vals):
        # _logger.info('\n write vals ================> : %s', str(vals))
        if 'claim_id' in vals:
            kx_id = vals['claim_id']
            if type(kx_id) != int:
                # jika claim_id bukan id, maka claim_id berisi nomor KX dari BIS, id cn harus di search dulu agar KX terhubung
                objkx = self.env['bsp.claim.principal'].search([('name', '=', kx_id)], limit=1)
                if objkx:
                    vals['claim_id'] = objkx.id
                else:
                    vals['claim_id'] = False
        if 'branch_code' in vals:
            # kode cabang dari BIS di cari di operating unit, harus sudah ada
            objou = self.env['operating.unit'].search([('code', '=', vals['branch_code'])], limit=1)
            if objou:
                vals['operating_unit_id'] = objou.id
        if 'principal_code' in vals:
            # kode principal dari BIS di cari di res.partner, harus ada
            objpart = self.env['res.partner'].search([('ref', '=', vals['principal_code'])], limit=1)
            if objpart:
                vals['partner_id'] = objpart.id
        # vals['total_claimed_amount'] = self.total_claimed_amount
        # vals['paid_total'] = self.paid_total
        if 'time_stamp' not in vals:
            vals['time_stamp'] = datetime.now() + timedelta(hours=7)
        if 'state' in vals:
            if vals['state'] in ('cabang','pusat','printed','post'):
                removed_state = vals.pop('state')

        result = super(CNOthers, self).write(vals)
        if self.cn_type == 'cncl' and (not self.create_move_id or not self.alloc_move_id or
                                       ('principal_code' in vals) or ('cn_total' in vals) or
                                       ('allocated_amount' in vals)):
           self.sudo().button_journals()
        if vals.get('allocated_amount'):
            self._onchange_allocated_amount()

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
    def button_paid(self):
        return self.write({'state': 'paid'})



    @api.multi
    def button_cancel(self):
        if self.cn_type == 'cncl':
                self.create_move_id.button_cancel()
                self.alloc_move_id.button_cancel()
                # self.create_move_id.unlink()
                # self.alloc_move_id.unlink()
        return self.write({'state': 'canceled','create_move_id': False, 'alloc_move_id': False})

    @api.multi
    def button_printed(self):
        return self.write({'state': 'printed',
                           'total_claimed_amount': 0,
                           'paid_total': 0})

    @api.multi
    def button_revice(self):
        return self.write({'remark': self.state, 'state': "draft"})

    @api.multi
    def button_backrevice(self):
        if self.state == 'draft' and self.remark:
           return self.write({'state': self.remark,'remark': False})
        return 1

    @api.multi
    def button_quick_open_cl(self):
        self.ensure_one()
        return {
            'name': self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    # selected_claim = fields.Boolean(
    #     inverse='_inverse_set_selected_claim',
    #     help="Set this quantity to create a new line "
    #          "for this product or update the existing one."
    # )
    #
    # def _inverse_set_selected_claim(self):
    #     parent_model = self.env.context.get('parent_model')
    #     parent_id = self.env.context.get('parent_id')
    #     if parent_model:
    #         parent = self.env[parent_model].browse(parent_id)
    #         for claim in self:
    #             quick_line = parent._get_quick_line(claim)
    #             if quick_line:
    #                 parent._update_quick_line(claim, quick_line)
    #             else:
    #                 parent._add_quick_line(claim)





class CNAllocation(models.Model):
    _name = 'bsp.creditnote.alloc'
    _description = "BSP Others Credit Note Allocation"

    name = fields.Char("Allocation Number", size=30, required=True)
    offset_type = fields.Char("Offset type", size=3, oldname="offsettype")
    allocation_type = fields.Selection("Allocation Type", size=3)
    allocation_type = fields.Selection(
        [('AL', 'Alokasi'),
         ('PC', 'Pencairan')],string='Allocation Type', default='draft')
    allocation_date = fields.Date("Allocation Date", required=True, default=datetime.now().date())
    reference_no = fields.Char("Reference Number", size=30, oldname="referensi_no")
    reference_date = fields.Date("Reference Date", oldname="referensi_date")
    allocation_amount = fields.Float("Allocation")
    cn_id = fields.Many2one('bsp.creditnote.other', string='Allocation For')


    @api.model
    def create(self, vals):
        if 'cn_id' in vals:
            cn_id = vals['cn_id']
            if type(cn_id) != int:
                # jika cn_id bukan id, makan cn_id berisi nomor CN dari BIS, id cn harus di search dulu agar CN terhubung
                objcn = self.env['bsp.creditnote.other'].search([('name', '=', cn_id)], limit=1)
                if objcn:
                   vals['cn_id'] = objcn.id
                else:
                    vals['cn_id'] = False

        result = super(CNAllocation, self).create(vals)
        return result

    @api.multi
    def write(self, vals):
        if 'cn_id' in vals:
            cn_id = vals['cn_id']
            if type(cn_id) != int:
                objcn = self.env['bsp.creditnote.other'].search([('name', '=', cn_id)], limit=1)
                if objcn:
                    vals['cn_id'] = objcn.id
                else:
                    vals['cn_id'] = False

        result = super(CNAllocation, self).write(vals)
        return result

class KLProductLines(models.TransientModel):
    _name = 'bsp.creditnote.kl.lines'
    _description = "BSP Others Creditnote Barang (KL)"
    name = fields.Char("Kode Barang", size=30, required=True)
    cn_id = fields.Many2one('bsp.creditnote.other', string='KL For')
    product_name = fields.Char("Nama Barang", size=60, required=True)
    quantity = fields.Float("Jumlah Barang")
    product_unit = fields.Char('Satuan', size=10)
    hna = fields.Float("HNA")
    total = fields.Float("Total")
    reference_no = fields.Char("No Faktur", size=30, required=True)
    reference_date = fields.Date("Tgl Faktur")

    _sql_constraints = [
        ('name_KLItem_unique_idx', 'unique (name,cn_id,reference_no)', "Tag KL Item already exists !"),
    ]

    @api.model
    def create(self, vals):
        if 'cn_id' in vals:
            cn_id = vals['cn_id']
            if type(cn_id) != int:
                # jika cn_id bukan id, makan cn_id berisi nomor CN dari BIS, id cn harus di search dulu agar CN terhubung
                objcn = self.env['bsp.creditnote.other'].search([('name', '=', cn_id)], limit=1)
                if objcn:
                   vals['cn_id'] = objcn.id
                else:
                    vals['cn_id'] = False

        result = super(KLProductLines, self).create(vals)
        return result

    @api.multi
    def write(self, vals):
        if 'cn_id' in vals:
            cn_id = vals['cn_id']
            if type(cn_id) != int:
                objcn = self.env['bsp.creditnote.other'].search([('name', '=', cn_id)], limit=1)
                if objcn:
                    vals['cn_id'] = objcn.id
                else:
                    vals['cn_id'] = False
        result = super(KLProductLines, self).write(vals)
        return result