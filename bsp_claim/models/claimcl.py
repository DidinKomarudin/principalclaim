import json
import time
from odoo import api, fields, models, _
from lxml import etree
from datetime import date, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
# from dateutil.relativedelta import relativedelta
from odoo.tests.common import Form
from odoo.exceptions import  ValidationError, UserError
from odoo.addons import decimal_precision as dp
from odoo.osv import expression

class ClaimCL(models.Model):
    _name = 'bsp.claim.cl'
    _description = "Claim CL to Principal"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # def _compute_invoice(self):
    # @api.depends('invoice_ids')
    #     for record in self:
    #         record.invoice_count = len(record.invoice_ids)

    @api.depends('send_date', 'paid_date')
    def _compute_claim_age(self):

        for record in self:
            record.claim_age = 0
            if record.paid_date:
                currentDate = record.paid_date.date()
            else:
                currentDate = datetime.now().date()
            initial_aging_date = record.send_date

            if initial_aging_date:
                dy = (currentDate - initial_aging_date).days
                record.claim_age = dy

    @api.depends('pending_date', 'paid_date')
    def _compute_claim_age0(self):


        for record in self:
            record.claim_age0 = 0
            if record.paid_date:
                currentDate = record.paid_date.date()
            else:
                currentDate = datetime.now().date()
            record.claim_age0 = 0
            initial_aging_date = record.pending_date

            if initial_aging_date:
                dy = (currentDate - initial_aging_date.date()).days
                record.claim_age0 = dy

    @api.depends('receive_date', 'send_date')
    def _compute_process_ap(self):
        for record in self:
            record.process_ap = 0
            initial_aging_date = record.receive_date
            send_date = record.send_date
            if send_date and initial_aging_date:
                dy = (send_date - initial_aging_date).days
                record.process_ap = dy

# Alokasikan realisasi pembayaran ke CL terkait
#     @api.depends('realization_amount')
#     @api.onchange('realization_amount')
    def claim_alloc(self):
        for record in self:
            realization_amount = 0
            # if record.claim_type in ('cncl', 'discount', 'barang','faktur','noncl'):
            if record.is_from_bis:
                realization_amount = record.realization_amount
                for cn in record.claimline_ids:
                    # objcn = self.env['bsp.creditnote.other'].search([('id', '=', cn.cn_id.id)])
                    # if cn.cn_id:
                        # tot_paid = cn.cn_total - cn.cn_id.paid_total
                        # if tot_paid > 0:
                    alloc_amount = cn.actual_claim_amount
                    if realization_amount <= alloc_amount:
                       alloc_amount = realization_amount
                    cn.write({'paid_total': alloc_amount})
                    # cn.paid_total = alloc_amount
                    realization_amount -= alloc_amount
                    tot_paid = sum(self.env['bsp.claim.cl.line']
                                      .search([('cn_id', '=', cn.cn_id.id)])
                                      .mapped('paid_total'))
                    if tot_paid >= cn.cn_total:
                      cn.cn_id.write({'paid_total': cn.cn_total, 'state': 'paid'})  #,'remark':str(tot_paid)+'<--updated paid-->'+ str(alloc_amount)})
                    else:
                      cn.cn_id.write({'paid_total': tot_paid})  #,'remark':str(tot_paid)+'<--updated parsial-->'+ str(alloc_amount)})
                    # if realization_amount <= 0:
                    #     break
            record.unrealized_amount = realization_amount


    @api.depends('add_amount','claimline_ids.cn_total', 'claimline_ids.bsp_share',
                 'claimline_ids.principal_share','claimline_ids.actual_claim_amount')
    def _compute_calc_claim_amount(self):
        for record in self:
            if not record.claimline_ids:
                break
            for line in record.claimline_ids:
                # if record.claim_type == 'discount':
                if record.is_can_partial:
                    record.claim_amount += line.actual_claim_amount
                else:
                    record.claim_amount += line.cn_total

                record.total_bsp_share += line.bsp_share
                record.total_principal_share += line.principal_share
            if record.claim_type == 'mix':
                record.claim_amount += record.add_amount

    def _inverse_update_free(self):
        return True



    @api.depends('partner_id')
    def _compute_bank_account(self):
        for record in self:
            if record.partner_id.ref == 'NFI':
                record.bank_id = self.env['res.partner.bank'].search([('partner_id.ref', '=', 'NFI')], limit=1)
            else:
                record.bank_id = self.env['res.partner.bank'].search([], limit=1)



    @api.depends('claim_amount', 'tax_id')
    def _compute_calc_amount(self):
        for record in self:
            res = record.tax_id.compute_all(record.claim_amount)
            record.tax_amount = 0
            record.pph1_amount = 0
            for tax_vals in res['taxes']:
                if 'PPN' in tax_vals['name']:
                    record.tax_amount += tax_vals['amount']
                if 'PPH' in tax_vals['name']:
                    record.pph1_amount += tax_vals['amount']
            record.net_amount = record.claim_amount + record.tax_amount + record.pph1_amount

    @api.multi
    @api.depends('claim_age', 'net_amount', 'realization_amount')
    def _compute_calc_age(self):
        for record in self:
            record.day90 = 0
            record.day61_90 = 0
            record.day31_60 = 0
            record.day0_30 = 0
            record.balance_amount = record.net_amount - record.realization_amount #- record.correction_amount
            if record.balance_amount > 0:
                if record.claim_age > 90:
                   record.day90 = record.balance_amount
                else:
                    if record.claim_age > 60:
                        record.day61_90 = record.balance_amount
                    else:
                        if record.claim_age > 30:
                            record.day31_60 = record.balance_amount
                        else:
                            record.day0_30 = record.balance_amount
            # else:
            #     if record.state == 'paid':
            #         record.is_claim_done()

    # @api.depends('operating_unit_id')
    # def _compute_operating_unit(self):
    #     for record in self:
    #         if record.operating_unit_id:
    #             record.branch_code = record.operating_unit_id.code
    #         # objou = self.env['operating.unit'].search([('code', '=', record.branch_code)], limit=1)
    #         # if objou:
    #         #     record.operating_unit_id = objou.id
    #


    def _get_domain(self):
        return [('id', 'in', self.env.user.operating_unit_ids.ids),('parent_id','=',False)]

    def _get_domain_depo(self):
        return [('id', 'in', self.env.user.operating_unit_ids.ids),('parent_id','<>',False)]

    def _get_domain_branch(self):
        return [('branch_code', 'in', [o.code for o in self.env.user.operating_unit_ids]),
                ('cc_id', '=', False)]

    def _get_payment_terms(self):
        retval=0
        obj_pt = self.env['account.payment.term'].sudo().search([('name', 'like', '30')], limit=1)
        if obj_pt:
            retval=obj_pt.id
        return retval

    def _get_domain_type(self):
        retdomain = []
        # if not self.user_has_groups('bsp_claim.group_claim_user'):
        #     retdomain = [('code', 'not in', ['other'])]
        return retdomain



    @api.multi
    @api.depends('state', 'is_branch', 'is_usrdoc_match')
    def _compute_is_editable(self):
        for rec in self:
            rec.is_editable = True
            if not rec.is_usrdoc_match \
                or rec.state in ('done', 'reject', 'cancel') \
                or (rec.state in ('pending', 'post', 'paid') and not(self.user_has_groups('bsp_claim.group_claim_manager'))):
                rec.is_editable = False


    @api.multi
    @api.depends('state', 'is_branch')
    def _compute_is_editable_pusat(self):
        for rec in self:
            rec.is_editable_pusat = True
            if rec.state in ('draft','done', 'reject', 'cancel') \
                or rec.is_branch:
                rec.is_editable_pusat = False

    # @api.multi
    # @api.depends('claim_type_id', 'ref')
    def _compute_get_coa_acc(self):
        for rec in self:
            ct = self.env['bsp.claim.type'].sudo().search([('coding', '=', rec.coding.upper())],limit=1)
            coa_acc = ct.coas
            if rec.coding == 'f':
                coas = coa_acc.split(',')
                coa_acc = coas[0]
                if len(coas) > 1:
                   if rec.ref == 'BDF':
                       coa_acc = coas[1]

            rec.coa_acc = coa_acc


    def _is_branch(self):
        is_hq = self.user_has_groups('bsp_claim.group_claim_user')  #bsp_claim.group_claim_spv,bsp_claim.group_claim_manajer')
        return not is_hq

    @api.multi
    def _compute_is_branch(self):
        for rec in self:
            rec.is_branch = rec._is_branch()
                    # not(self.user_has_groups('bsp_claim.group_claim_user') or self.user_has_groups('bsp_claim.group_claim_manajer'))

    def _user_title(self):
        ret = 'guest'
        if self.user_has_groups('bsp_claim.group_claim_manager'):
            ret = 'manager'
        elif self.user_has_groups('bsp_claim.group_claim_asmen'):
            ret = 'asmen'
        elif self.user_has_groups('bsp_claim.group_claim_spv'):
            ret = 'spv'
        elif self.user_has_groups('bsp_claim.group_claim_user'):
            ret = 'staf'
        elif self.user_has_groups('bsp_claim.group_claim_branch_manager'):
            ret = 'cob'
        elif self.user_has_groups('bsp_claim.group_claim_branch_spv'):
            ret = 'fs'
        elif self.user_has_groups('bsp_claim.group_claim_branch_depo_user'):
            ret = 'staf depo'
        elif self.user_has_groups('bsp_claim.group_claim_branch_user'):
            ret = 'staf cabang'
        elif self.user_has_groups('bsp_claim.group_claim_view_user'):
            ret = 'cabang view'

        return ret

    @api.multi
    def _compute_user_title(self):
        for rec in self:
            rec.user_title = rec._user_title()

    @api.multi
    @api.depends('is_branch', 'name', 'state', 'is_usrdoc_match')
    def _compute_cancel_invisible(self):
        for rec in self:
            rec.is_cancel_invisible = True
            if (rec.is_usrdoc_match and rec.state in ('draft') and rec.user_title in ('fs', 'spv', 'asmen', 'manager'))\
                or (rec.state in ('post') and rec.user_title in ('asmen', 'manager')):
                rec.is_cancel_invisible = False

    @api.multi
    @api.depends('is_branch', 'is_usrdoc_match')
    def _compute_pending_invisible(self):
        for rec in self:
            rec.is_pending_invisible = False
            if not rec.is_usrdoc_match \
                or rec.state not in ('draft') \
                or rec.user_title in ('staf'):
                rec.is_pending_invisible = True

    @api.multi
    @api.depends('name','is_branch','depo_id','user_depo_ids','user_title')
    def _compute_ismatch(self):
        for rec in self:
            rec.is_usrdoc_match = False
            if rec.name == 'New' or ('CLM' in rec.name and not rec.is_branch) \
                or ('CLM' not in rec.name and rec.is_branch and rec.user_title != 'staf depo') \
                or (rec.depo_id.id > 0 and rec.depo_id.id in rec.user_depo_ids.ids):
                rec.is_usrdoc_match = True

    @api.multi
    @api.onchange('partner_id')
    @api.depends('partner_id')
    def _compute_count_claim(self):
        cn = self.env['bsp.creditnote.other']
        for rec in self:
            principles=[]
            rec.is_claim_ready = True
            # if rec.partner_id and rec.claim_type in ('cncl','discount','barang','faktur','noncl'):
            if rec.partner_id and rec.is_from_bis:
                type = rec.claim_type
                # if type == 'barang':
                #     type='discount'
                if type != 'mix':
                    principles.append(rec.partner_id.ref)
                    if rec.partner_id.ref == 'RBT':
                        principles.append('RBH')
                    if rec.partner_id.ref == 'RBH':
                        principles.append('RBT')

                    # request by MOM 26-01-2024 from AP and Fin dep : Pa.Hervin dan Pa Brampi
                    if rec.claim_type in('noncl','mix'):
                    # if rec.claim_type == 'noncl':
                        rec_count = cn.search_count([('operating_unit_id', '=', rec.operating_unit_id.id),
                                                     ('cn_type', '=', type)])
                    else:
                        rec_count = cn.search_count([('principal_code', 'in', principles),
                                             ('operating_unit_id', '=', rec.operating_unit_id.id),
                                             ('cn_type', '=', type)])
                    if not rec_count:
                        rec.is_claim_ready = False
                        warning_mess = {
                            'title': _('CL/KL/Factur not found!'),
                            'message': _("Branch do not have CL/KL/Factur for this principal "),
                        }
                        return {'warning': warning_mess}


    @api.multi
    @api.depends('user_title')
    def _compute_getuserdepo_id(self):
        for rec in self:
            rec.user_depo_ids = []
            # if rec.user_title == 'staf depo':
            if self.user_has_groups('bsp_claim.group_claim_branch_depo_user'):
                rec.user_depo_ids = self.env.user.operating_unit_ids.filtered(lambda depo: depo.parent_id)  #[:1].id

    # @api.depends('remark')
    # def _compute_program(self):
    #     for record in self:
    #         st = str(record.remark)
    #         record.program = st.split()[0] + '...'

    READONLY_STATES = {
        'paid': [('readonly', True)],
        'done': [('readonly', True)],
        'reject': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    @api.onchange('send_date')
    def _onchange_send_date(self):
        if self.send_date:
            if self.receive_date:
                query = f""" select count(*)  from  bsp_claim_lock  WHERE date_from <= '{(self.send_date).strftime("%Y/%m/%d")}' 
                and date_to >= '{(self.send_date).strftime("%Y/%m/%d")}' """
                print(query)
                self._cr.execute(query)
                isExist = self._cr.fetchone()[0]
                if isExist > 0.0:
                   raise ValidationError(_('Sorry: Send Date to principal for this period has been CLOSE!!'))
            else:
                raise ValidationError(_('Sorry: Receive date must be define!!'))



    @api.onchange('claim_type')
    def _onchange_claim_type(self):
        if self.claim_type_id:
            self.coding = self.claim_type_id.coding.lower()  #self.claim_type_id.name[-1].lower()
        if self.name == 'New':
            self.isclaim_in_budget = False
            self.remark = ''
            self.customer_ref = ''
            self.claim_letter = ''
            self.claimline_ids = False
            self.claim_amount = 0



    # Load all claim lines
    # @api.onchange('kx_id')
    # def _onchange_kx(self):
    #     self.claimline_ids = False
    #     if not self.kx_id:
    #         self.isclaim_in_budget = False
    #         self.remark = ''
    #         self.customer_ref = ''
    #         self.claim_letter = ''
    #         self.refdoc = ''
    # #         return {}
    #
    #     new_lines = self.env['bsp.claim.cl.line']
    #     mess = ''
    #     kc=''
    #     for line in self.kx_id.cn_ids:
    #         kc = line.kc_no
    #         if not line.claimcl_id and (line.state == 'post' or line.state == 'printed'):
    #             new_lines += new_lines.new(self._prepare_claim_line(line))
    #         else:
    #             doc ='PAID'
    #             if line.claimcl_id:
    #                 doc = line.claimcl_id.name
    #             if mess != '':
    #                 mess = mess + '\n'
    #             mess = "%s %s has processed on CC :%s" % (mess, line.name, doc)
    #
    #     self.claimline_ids += new_lines
    #     operating_unit_id = self.env['operating.unit'].search([('code', '=', self.kx_id.branch_code)], limit=1)
    #     self.operating_unit_id = operating_unit_id
    #     # self.branch_code = self.kx_id.branch_code
    #     partner_id = self.env['res.partner'].search([('ref', '=', self.kx_id.principal_code)], limit=1)
    #     self.partner_id = partner_id
    #
    #     self.isclaim_in_budget = self.kx_id.isclaim_in_budget
    #     self.remark = self.kx_id.remark
    #     self.customer_ref = self.kx_id.customer_ref
    #     self.claim_letter = self.kx_id.claim_letter
    #     self.refdoc = kc
    #     warning = {}
    #     if mess != '':
    #         warning = {'warning':
    #                     {
    #                     'title': _('Warning'),
    #                     'message': _(mess)
    #                     }
    #                 }
    #
    #     return warning


    def _prepare_claim_line(self,cn_id):
        data = {
            'cn_id': cn_id.id,
            'description': '',
            'cn_total': cn_id.cn_total,
            'ump_amount': cn_id.ump_amount,
            'bsp_share': cn_id.bsp_share,
            'principal_share': cn_id.principal_share,
            'exim_status': 'CC'

        }
        return data

    @api.model
    def _selection_type(self):
        res_filter = [
                       ('cncl', 'CNCL'),
                       ('faktur', 'Faktur Principal'),
                       ('discount', 'Discount'),
                       ('barang', 'Barang'),
                       ('salary', 'Salary Salesman'),
                       ('cabang', 'USMUB/Insentif'),
                       ('manual', 'Manual OPU'),
                       ('insentif', 'Insentif BSP'),
                       ('provisi', 'Provisi Bank Garansi'),
                       ('transfer', 'Transfer via HO')]

        if self.user_has_groups('bsp_claim.group_claim_user'):
            res_filter.append(('other', _('Lain Lain')))
        return res_filter



    def _default_depo_id(self):
        default_id = lambda self: self.env.user.default_operating_unit_id.id
        depo_id = lambda self: self.env.user.operating_unit_ids.filtered(lambda depo: depo.parent_id.id == default_id)[:1].id
        return depo_id

    @api.onchange('operating_unit_id')
    def _onchange_operating_unit_id(self):
        for rec in self:
            rec.depo_id = False

    @api.onchange('remark')
    def _onchange_remark(self):
        for rec in self:
            rec.remark = rec.remark.replace('"','')
            rec.remark = rec.remark.replace("'", '')

    @api.depends('kc_id')
    def _program_from_kc(self):
        for rec in self:
            rec.remark = rec.kc_id.remark

    @api.multi
    @api.depends('move_line_ids.reconciled')
    def _get_move_reconciled(self):
        for payment in self:
            rec = False
            for aml in payment.move_line_ids.filtered(lambda x: x.account_id.reconcile):
                if not aml.reconciled:
                    rec = False
            payment.move_reconciled = rec

    # @api.multi
    # @api.depends('claim_type_id', 'claim_type')
    # def _compute_get_filter_type(self):
    #     for claim in self:
    #         if claim.claim_type_id:
    #             claim_type = claim.claim_type_id.code
    #             claim.claim_type_filter = ''
    #             if claim_type == 'mix':
    #                 types = self.env['bsp.claim.type'].search([('code', '<>', 'mix')])
    #                 lst = []
    #                 for tp in types:
    #                     lst.append(tp.code)
    #                 # claim.claim_type_filter = "'.'".join(lst)
    #
    #                 for x in lst:
    #                     if claim.claim_type_filter == '':
    #                         claim.claim_type_filter = "'" + x + "'"
    #                     else:
    #                         claim.claim_type_filter += ",'" + x + "'"
    #
    #                 claim.claim_type_filter
    #             else:
    #                 claim.claim_type_filter = "'"+claim_type + "'"



    def _get_journal_ids(self):
        for claim in self:
            journals = self.env['account.move.line']
            for line in claim.invoice_line_ids:
                if line.invoice_id:
                    mlObj = self.env['account.move.line'].search([('invoice_id','=', line.invoice_id.id)])
                    if mlObj:
                        journals |= mlObj
            claim.move_line_ids = journals

    @api.depends('state')
    def _get_payment_ids(self):
        for claim in self:
            if claim.state not in ('paid','done'):
                continue
            query =f""" select p.id payment_id
                        from account_move_line ml join account_payment p on p.id=ml.payment_id 
                        join account_invoice ai on ai."number" = p.communication 
                        join account_invoice_line ail on ai.id=ail.invoice_id 
                        join bsp_claim_cl cl on cl.id=ail.claimcl_id 
                        where ml.credit >0 and cl.id = {claim.id}
                        """
            self._cr.execute(query)
            records = self._cr.fetchall()
            if not records:
                continue
            is_bm = False
            is_bk = False
            claim.lpayments = ''
            claim.lpayment_date = ''
            claim.lpayment_app_date = ''
            claim.lpayment_bankno = ''
            payments = self.env['account.payment']
            bmbks = self.env['bsp.payment.voucher']
            for rec in records:
                pym = self.env['account.payment'].sudo().browse(rec[0])
                if pym:
                    payments |= pym
                    if pym.pv_id:
                       is_bk = pym.pv_id.type == 'bk'
                       is_bm = pym.pv_id.type == 'bm'
                       bmbks |= pym.pv_id
            claim.payment_ids = payments
            claim.bmbk_ids = bmbks
            claim.payment_count = len(payments)
            # claim.payment_count = len(claim.payment_ids)
            if claim.payment_count > 0:
                # for payment in payments:

                for payment in claim.payment_ids:
                    if claim.lpayments == '':
                        claim.lpayments = payment.name
                    else:
                        claim.lpayments += ("," + payment.name)
                    if payment.pv_id:
                        if claim.lpayment_date=='':
                            claim.lpayment_date = payment.pv_id.trx_date.strftime("%d-%m-%Y")
                            claim.lpayment_app_date = payment.approval_date.strftime("%d-%m-%Y")
                        else:
                            claim.lpayment_date += ("," + payment.pv_id.trx_date.strftime("%d-%m-%Y"))
                            claim.lpayment_app_date += ("," + payment.approval_date.strftime("%d-%m-%Y"))

                        if claim.lpayment_bankno == '':
                            claim.lpayment_bankno = payment.pv_id.name #payment.bank_reference
                        else:
                            claim.lpayment_bankno += ("," + payment.pv_id.name) #payment.bank_reference)

            if claim.has_bm != is_bm:
                claim.write({'has_bm': is_bm})
            if claim.has_bk != is_bk:
                claim.write({'has_bk': is_bk})



    def _get_invoice_count(self):
       for claim in self:
            claim.linvoices = ''
            claim.invoice_count = len(claim.invoice_line_ids)
            invoices = self.env['account.invoice']
            for line in claim.invoice_line_ids:
                if not line.invoice_id.number:
                    continue
                invoices |= line.invoice_id
                if claim.linvoices == '':
                    claim.linvoices = line.invoice_id.number
                else:
                    claim.linvoices +=(", " + line.invoice_id.number)
            claim.invoice_ids = invoices

    def _get_cn_ids(self):
        for claim in self:
            lcn_number = []
            lcn_date = []
            lcn_customer = []
            for cn in claim.claimline_ids:
                lcn_number.append(cn.cn_id.name)
                lcn_date.append(cn.cn_id.cn_date.strftime("%d-%m-%Y"))
                lcn_customer.append(f'[{cn.cn_id.customer_code}]{cn.cn_id.customer_name}')
            claim.lcn_number = ', '.join(lcn_number)
            claim.lcn_date = ', '.join(lcn_date)
            claim.lcn_customer = ', '.join(lcn_customer)

    @api.onchange('tax_inv')
    def _onchange_tax_inv(self):
        if self.tax_inv != False and  self.tax_inv != '':
           claim = self.env['bsp.claim.cl'].search([('tax_inv', '=', self.tax_inv), ('id', '!=', self._origin.id)], limit=1)
           if claim:
                warning_mess = {
                    'title': 'Found on claim#: %s' % claim.name,
                    'message': _('Tax Invoice is duplicate in another documents!'),
                }
                return {'warning': warning_mess}

    @api.onchange('service_inv')
    def _onchange_service_inv(self):
        if self.service_inv != False and self.service_inv != '':
            claim = self.env['bsp.claim.cl'].search([('service_inv', '=', self.service_inv), ('id', '!=', self._origin.id)],
                                                    limit=1)
            if claim:
                warning_mess = {
                    'title': 'Found on claim#: %s' % claim.name,
                    'message': _('Service Invoice is duplicate in another documents!'),
                }
                return {'warning': warning_mess}



    # @api.constrains('claim_amount')
    # def _check_used_qty(self):
    #     for rec in self:
    #         if rec.claim_amount <= 0:
    #             raise Warning(_('You can\'t \
    #                             enter Claim Amount as Zero!'))

    user_depo_ids = fields.Many2many('operating.unit', compute='_compute_getuserdepo_id', store=False)
    is_claim_ready = fields.Boolean(default=False,compute='_compute_count_claim', store=False)
    user_title = fields.Char(default=_user_title, compute='_compute_user_title', store=False)
    is_usrdoc_match = fields.Boolean(default=True, compute='_compute_ismatch', store=False)
    is_editable = fields.Boolean(compute="_compute_is_editable")
    is_editable_pusat= fields.Boolean(compute="_compute_is_editable_pusat")
    is_cancel_invisible = fields.Boolean(default=True, compute="_compute_cancel_invisible", store=False)
    is_pending_invisible = fields.Boolean(default=True, compute="_compute_pending_invisible", store=False)
    is_branch = fields.Boolean(default=_is_branch,compute='_compute_is_branch', store=False)

    name = fields.Char("CC No.", size=40,
                       default='New', required=True,  readonly=True,copy=False)
                       # lambda self: self.env['ir.sequence'].next_by_code('bsp.claim.cl'))
    claim_date = fields.Date("CC Date", required=True, default=fields.Date.today, readonly=True, copy=False, states=READONLY_STATES)
    period = fields.Char("Periode", size=20, default=datetime.now().strftime('%Y%m'), required=True, copy=False, states=READONLY_STATES)


    claim_type_id = fields.Many2one('bsp.claim.type', 'Claim Type',
                                    track_visibility='onchange', required=True,
                                    domain=_get_domain_type,
                                    states=READONLY_STATES)
    claim_type = fields.Char(related="claim_type_id.code",
                                  store=True,
                                  readonly='True',
                                  string='CC Type')
    is_can_partial = fields.Boolean(related="claim_type_id.is_can_partial",
                              string="Claim can partial",  store=False)
    # claim_type_filter = fields.Char(compute="_compute_get_filter_type",
    #                     readonly = 'True',
    #                     string = 'Filter Type')

    is_from_bis = fields.Boolean(related="claim_type_id.is_from_bis",
                              string="Source from BIS",  store=False)
    # coa_pettycash = fields.Char(related="claim_type_id.coas",
    #                              string="COA Pettycash", store=False)
    claim_subtype = fields.Selection(
        [('dr', 'Discount Regular'),
         ('ds', 'Discount Special')],
        string='Discount Type', track_visibility='onchange',  default='dr', states=READONLY_STATES)
    product_subtype = fields.Selection(
        [('money', 'Money'), ('product', 'Product')],
        default='money', string='Charge Type',
        track_visibility='onchange',
        states=READONLY_STATES)

    an_receipt = fields.Selection([('prc','Principal'),('bsp','BSP')], default='prc', string='Kuitansi A.N', states=READONLY_STATES)
    state = fields.Selection(
                  [('draft', 'DRAFT'),
                   ('pending', 'PENDING'),
                   ('incomplete', 'INCOMPLETE'),
                   ('post', 'POST'),
                   ('paid', 'PAID'),
                   ('done', 'DONE'),
                   ('reject', 'REJECTED'),
                   ('cancel', 'CANCELED')],
        string='CC Status',
        track_visibility='onchange',
        required=True, default='draft', copy=False, states=READONLY_STATES)
    partner_id = fields.Many2one('res.partner', 'Principal', domain="[('supplier','=',True)]",
                                 track_visibility='onchange', required=False, states=READONLY_STATES)
    ref = fields.Char(related="partner_id.ref", string="Principal", store=False)

    # branch_code = fields.Char("Branch Code", size=5, required=True,
    #                           compute='_compute_operating_unit',
    #                           inverse='_inverse_operating_unit',  store=True)
    operating_unit_id = fields.Many2one('operating.unit', 'Branch',
                                        track_visibility='onchange', required=True,
                                        default=lambda self: self.env.user.default_operating_unit_id.id,
                                        domain=_get_domain, states=READONLY_STATES)
    branch_code = fields.Char(related="operating_unit_id.code", string="Branch Code", readonly=True, store=False, states=READONLY_STATES)
    depo_id = fields.Many2one('operating.unit', 'Depo',
                                track_visibility='onchange',
                              default=_default_depo_id,
                              states=READONLY_STATES)
                              # domain=_get_domain_depo,
    isclaim_in_budget = fields.Boolean("ON Budget", states=READONLY_STATES)
    remark = fields.Char("Program",
                         compute='_program_from_kc', inverse='_inverse_update_free',
                         store=True, copy=True,
                         required=True, states=READONLY_STATES)
    # program = fields.Char("Program", compute='_compute_program', states=READONLY_STATES)
    notes = fields.Char("Notes", track_visibility='onchange')
    claim_letter = fields.Char("No.Claim Principal", size=30, track_visibility='onchange', copy=False) #, states=READONLY_STATES)
    claim_letter_date = fields.Date("Claim Letter Date",  default=fields.Date.today, copy=False)
    service_inv = fields.Char("Faktur Jasa", size=30, copy=False)
    tax_inv = fields.Char("Faktur Pajak", size=30, copy=False)
    customer_ref = fields.Char("Outlet Ref.", size=60, copy=False, states=READONLY_STATES)
    branch_ref = fields.Char("Branch Ref.", size=60, copy=False, states=READONLY_STATES)
    refdoc = fields.Char("KC/Ref", size=200, copy=False, states=READONLY_STATES)
    vistex = fields.Char("Principal Ref.", size=30, copy=False, states=READONLY_STATES)
    # Additin by meet 21/08/2020
    opu_ref = fields.Char("OPU No.", size=60, copy=False, states=READONLY_STATES)
    bkkk_ref = fields.Char("BKKK No.", size=60, copy=False, states=READONLY_STATES)
    iom_ref = fields.Char("IOM No.", size=60, copy=False, states=READONLY_STATES)
    iom_date = fields.Date("IOM Date", copy=False, states=READONLY_STATES)
    discount_amount = fields.Float("Disc.Amount (Sys)", digits=dp.get_precision('Product Price'), copy=False, states=READONLY_STATES)
    receive_date = fields.Date("Receive Date", copy=False)
    # end add
    claim_amount = fields.Float("Claim amount",
                                compute='_compute_calc_claim_amount',
                                track_visibility='always',
                                inverse='_inverse_update_free',
                                store=True, copy=False, states=READONLY_STATES)
    total_bsp_share = fields.Float("BSP Share", readonly=True,
                                   compute='_compute_calc_claim_amount',
                                   digits=dp.get_precision('Product Price'), copy=False,
                                store=True)
    total_principal_share = fields.Float("Principal Share",
                                         compute='_compute_calc_claim_amount',
                                         digits=dp.get_precision('Product Price'), readonly=True, copy=False,
                                store=True)
    realization_amount = fields.Float("Real. Amount",track_visibility='always', copy=False)
    balance_amount = fields.Float("Bal. Amount", compute="_compute_calc_age",
                                  readonly=True, copy=False, store=True)
    cn_ids = fields.One2many('bsp.creditnote.other', 'claimcl_id', string="Claims" , copy=False, states=READONLY_STATES)
    claimline_ids = fields.One2many('bsp.claim.cl.line', 'claimcl_id', string="Collection Line Items" , copy=False, states=READONLY_STATES)
    # invoice_ids = fields.One2many('account.invoice', 'claimcl_id', string="Refund Lines", readonly=True,
    #                                 copy=False)
    # invoice_count = fields.Integer(compute="_compute_invoice", string='Bill Count', copy=False, default=0, store=True)
    payment_term_id = fields.Many2one(
        'account.payment.term', track_visibility='onchange',
        string='Payment Terms', default=_get_payment_terms, states=READONLY_STATES)
    tax_id = fields.Many2many('account.tax', string='Taxes',
                              track_visibility='onchange',
                              domain=[('tax_group_id', 'in',('PPN','PPH'))], states=READONLY_STATES)
        # fields.Many2many('account.tax', string='PPN', ondelete='restrict' , store=True)
    tax_amount = fields.Float("PPN Amount", compute="_compute_calc_amount", digits=dp.get_precision('Product Price'),
                              readonly=True, copy=False , store=True)
    # pph1_id = fields.Many2one('account.tax', string='PPH an BSP', ondelete='restrict', store=True)
    pph1_amount = fields.Float("PPH Amount", compute="_compute_calc_amount", digits=dp.get_precision('Product Price'),
                               readonly=True, copy=False , store=True)
    # pph2_id = fields.Many2one('account.tax', string='PPH an Outlet', ondelete='restrict', store=True)
    # pph2_amount = fields.Float("PPH Outlet amount", compute="_compute_calc_amount", readonly=True, copy=False , store=True)
    cn_date = fields.Date('CN Date', states=READONLY_STATES)
    cn_number = fields.Char('CN Number', size=30, states=READONLY_STATES)
    bank_id = fields.Many2one('res.partner.bank', string='Bank Account',
                              compute='_compute_bank_account',
                              inverse='_inverse_update_free', store=True,
                              help='Bank Account Number to which the invoice will be paid. ', copy=False, states=READONLY_STATES)
    invoice_id = fields.Many2one('account.invoice', string='Bill No (NOT USED AGAIN!)', ondelete='restrict', readonly=True, copy=False)
    coding = fields.Selection(
        [('a', 'A'),
         ('b', 'B'),
         ('c', 'C'),
         ('d', 'D'),
         ('e', 'E'),
         ('f', 'F'),
         ('g', 'G'),
         ('h', 'H')
         ],
        string='Coding', track_visibility='onchange', default='d', states=READONLY_STATES)

    send_date = fields.Date("Send to Principal", track_visibility='onchange', copy=False)
    process_ap = fields.Integer("Proc.AP", compute='_compute_process_ap', readonly=True)

    pending_date = fields.Datetime("Send to HQ", track_visibility='onchange', copy=False)
    resi_number = fields.Char('Resi Number', size=30, states=READONLY_STATES)
    expedition_name = fields.Char('Expedition by', size=30, states=READONLY_STATES)
    post_date = fields.Datetime("Post at", readonly=True, copy=False)
    paid_date = fields.Datetime("Paid at", readonly=True, copy=False)
    done_date = fields.Datetime("Done at", readonly=True, copy=False)
    reject_date = fields.Datetime("Reject at", readonly=True, copy=False)
    claim_age = fields.Integer("HQ Aging", compute="_compute_claim_age")
    claim_age0 = fields.Integer("Branch Aging", compute="_compute_claim_age0")
    net_amount = fields.Float('Net Amount', compute="_compute_calc_amount" , copy=False, store=True)

    day90 = fields.Float('>90days', compute="_compute_calc_age")
    day61_90 = fields.Float('61~90days', compute="_compute_calc_age")
    day31_60 = fields.Float('31~60days', compute="_compute_calc_age")
    day0_30 = fields.Float('0~30days', compute="_compute_calc_age")
    contact_person = fields.Char('Contact Person Name', size=60, states=READONLY_STATES)
    cp_tittle = fields.Char('Job Tittle', size=60, states=READONLY_STATES)
    cp_telp = fields.Char('Hp/Telp', size=30, states=READONLY_STATES)
    bm_name = fields.Char('BM Name', size=60, states=READONLY_STATES)
    reason_reject_id = fields.Many2one("bsp.claim.reason", string='Reject/Cancel',
                                       track_visibility='onchange', domain=[('type','=','rc')], states=READONLY_STATES)
    reason_correction_id = fields.Many2one("bsp.claim.reason", string='Corrention For',
                                           track_visibility='onchange', domain=[('type','=','corr')], states=READONLY_STATES)
    correction_amount =fields.Float('Corr Amount', track_visibility='onchange', states=READONLY_STATES)
    unrealized_amount =fields.Float('Unrealized Amount', states=READONLY_STATES)
    kx_id = fields.Many2one('bsp.claim.principal', string='Capture from KX',
                            # domain=_get_domain_branch,
                            copy=False, states=READONLY_STATES)
    kc_id = fields.Many2one('bsp.kc', string='KC', copy=False,  states=READONLY_STATES)
    rev_seq = fields.Integer('Revision Sequence', default=0, copy=False, states=READONLY_STATES)
    is_nonclaim = fields.Boolean("Is Non Claim", default=False, states=READONLY_STATES)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 default=lambda self: self.sudo().env["account.journal"].search([('code', '=', 'CJC')],
                                                                                         limit=1))
    ar_claim_move_id = fields.Many2one('account.move', string='Journal AR Claim', ondelete='restrict', readonly=True,
                                     copy=False)
    print_count = fields.Integer('Print Status', default=0, readonly=True, copy=False)
    lampiran = fields.Char("Lampiran", size=255, states=READONLY_STATES)

    move_line_ids = fields.Many2many('account.move.line', compute='_get_journal_ids',  copy=False)
    payment_ids = fields.One2many('account.payment', compute='_get_payment_ids', search='_payment_search',string="Payments", copy=False)
    payment_count = fields.Integer('Payment Count', compute='_get_payment_ids')


    lpayments = fields.Char('Payment No', compute='_get_payment_ids')
    lpayment_date = fields.Char('BM/BK Date', compute='_get_payment_ids', search='_payment_date_search')
    lpayment_app_date = fields.Char('Principal App', compute='_get_payment_ids', search='_payment_date_search')
    lpayment_bankno = fields.Char('Bank Reference', compute='_get_payment_ids')

    add_amount = fields.Float('Additional Amount', track_visibility='onchange', default=0, states=READONLY_STATES)
    add_remark = fields.Char('Remark', size=120, states=READONLY_STATES)
    lcn_number = fields.Char('CN', compute='_get_cn_ids')
    lcn_date = fields.Char('CN Date', compute='_get_cn_ids')
    lcn_customer = fields.Char('Customer', compute='_get_cn_ids')
    cn_principal = fields.Char("Principal CN.", size=30, copy=False) #, states=READONLY_STATES)
    invoice_line_ids = fields.One2many('account.invoice.line', 'claimcl_id',
                                       string='Invoices Lines', copy=False)
    invoice_count = fields.Integer(compute='_get_invoice_count')
    invoice_ids = fields.One2many('account.invoice', compute='_get_invoice_count',string="Payment Vouchers", search='_invoice_search')
    linvoices = fields.Char('Payment Voucher', compute='_get_invoice_count')
    has_bm = fields.Boolean('Has BM')
    has_bk = fields.Boolean('Has BK')
    bmbk_ids = fields.One2many('bsp.payment.voucher',string="BM/BK", compute='_get_payment_ids', search='_bmbk_search', copy=False)
    is_locked = fields.Boolean('Is LOCK')
    coa_acc = fields.Char('COA Accounting', compute='_compute_get_coa_acc')
    _sql_constraints = [
        ('name_claim_cl_unique_idx', 'unique (name)', "Tag Claim Collection Number already exists !"),
    ]

    @api.multi
    def _invoice_search(self, operator, operand):
        query = f""" select cl.id claimcl_id
                                        from account_invoice ai
                                        join account_invoice_line ail on ai.id=ail.invoice_id
                                        join bsp_claim_cl cl on cl.id=ail.claimcl_id
                                        where ai.number like '%{operand.upper()}%'"""

        self._cr.execute(query)
        records = self._cr.fetchall()
        return [('id', 'in', [p[0] for p in records])]
        # invoices = self.sudo.env['account.invoice.line'].sudo().search([
        #     ('invoice_id', operator, operand)]).read(['claimcl_id'])
        # return [('id', 'in', [inv['claimcl_id'][0] for inv in invoices])]

    @api.multi
    def _payment_search(self, operator, operand):
        query = f""" select cl.id claimcl_id
                                from account_move_line ml join account_payment p on p.id=ml.payment_id 
                                join account_invoice ai on ai."number" = p.communication 
                                join account_invoice_line ail on ai.id=ail.invoice_id 
                                join bsp_claim_cl cl on cl.id=ail.claimcl_id 
                                where ml.credit >0 and p.name like '%{operand.upper()}%'"""

        self._cr.execute(query)
        records = self._cr.fetchall()

        # payment = self.env['account.payment'].sudo().name_search(operand,operator=operator)

        return [('id', 'in', [p[0] for p in records])]

    @api.multi
    def _bmbk_search(self, operator, operand):
        query = f""" select cl.id claimcl_id
                                        from account_move_line ml join account_payment p on p.id=ml.payment_id 
                                        join account_invoice ai on ai."number" = p.communication 
                                        join bsp_payment_voucher pv on pv.id = p.pv_id
                                        join account_invoice_line ail on ai.id=ail.invoice_id 
                                        join bsp_claim_cl cl on cl.id=ail.claimcl_id 
                                        where ml.credit >0 and AND pv.type = '{operand.upper()}'"""

        self._cr.execute(query)
        records = self._cr.fetchall()
        return [('id', 'in', [p[0] for p in records])]

    @api.multi
    def _payment_date_search(self, operator, operand):
        query = f""" select cl.id claimcl_id
                                            from account_move_line ml join account_payment p on p.id=ml.payment_id 
                                            join bsp_payment_voucher pv on pv.id = p.pv_id
                                            join account_invoice ai on ai."number" = p.communication 
                                            join account_invoice_line ail on ai.id=ail.invoice_id 
                                            join bsp_claim_cl cl on cl.id=ail.claimcl_id 
                                            where ml.credit >0 and pv.trx_date >= '{operand}'"""

        self._cr.execute(query)
        records = self._cr.fetchall()
        return [('id', 'in', [p[0] for p in records])]

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(ClaimCL, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby,
                                                 lazy=lazy)
        if 'day90' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(line['__domain'])
                    total_day90 = 0.0
                    total_day61_90 = 0.0
                    total_day31_60 = 0.0
                    total_day0_30 = 0.0
                    max_claim_age0 = 0
                    max_claim_age = 0
                    for record in lines:
                        if record.claim_age> max_claim_age:
                            max_claim_age=record.claim_age
                        if record.claim_age0> max_claim_age0:
                            max_claim_age0=record.claim_age0

                        total_day90 += record.day90
                        total_day61_90 += record.day61_90
                        total_day31_60 += record.day31_60
                        total_day0_30 += record.day0_30

                    line['claim_age0'] = max_claim_age0
                    line['claim_age'] = max_claim_age
                    line['day90'] = total_day90
                    line['day61_90'] = total_day61_90
                    line['day31_60'] = total_day31_60
                    line['day0_30'] = total_day0_30

        return res

    def _search_cn(self, operator, value):
        return [('lcn_number', 'like', '%'+value+'%')]

    @api.multi
    def button_journal_entries(self):
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.mapped('move_line_ids').mapped('move_id').ids)],
            'context': {
                'journal_id': self.journal_id.id,
            }
        }



    @api.multi
    def button_invoice_entries(self):
        action = self.env.ref('bsp_claim.action_claim_account_invoice_line').read()[0]
        # action.setdefault('context', {})
        action['context'] = {'active_model': ''}
        action['domain'] = [('id', 'in', self.invoice_line_ids.ids)]
        return action

    @api.multi
    def button_invoices(self):
        action = {
            'name': _('Paid Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.mapped('invoice_line_ids').mapped('invoice_id').ids)],
            # 'domain': [('id', '=', self.invoice_id.id)],
        }
        action['views'] = [(self.env.ref('account.invoice_supplier_tree').id, 'tree'),
                           (self.env.ref('account.invoice_supplier_form').id, 'form')]
        action['context'] = {
                'type': 'in_refund',
                'default_type': 'in_refund',
            }

        return action

    def open_payment_matching_screen(self):
        action = self.env.ref('bsp_claim.action_account_payments_claim').read()[0]
        # action.setdefault('context', {})
        action['context'] = {'active_model': ''}
        action['domain'] = [('id', 'in', self.payment_ids.ids)]
        return action



    @api.model
    def fields_view_get(self, view_id=None, view_type=Form, toolbar=False, submenu=False):
        res = super(ClaimCL, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        # if not self.is_branch:
        # print('fields_view_get claim:%s' % view_type)
        # context = self._context
        if view_type == 'form':
            if self.user_has_groups('bsp_claim.group_claim_user,bsp_claim.group_claim_spv,bsp_claim.group_claim_manajer'):
                doc = etree.XML(res['arch'])
                for node in doc.xpath("//button[@name='button_pending']"):
                    node.set('string', 'Pending')
                res['arch'] = etree.tostring(doc, encoding='unicode')


            # form_tag = '<form string = "Form Claim Collection"  delete = "0" >'
            # current_id = context.get('params',{}).get('id')
            # isLock = self.browse(current_id).is_locked
            # if isLock:
            #     modify_edit_str = 'edit="false"'
            #     form_tag = '<form string = "Form Claim Collection"  delete = "0" %s>'%( modify_edit_str)
            #
            # res['arch'] = res['arch'].replace('<form>', form_tag)
            # # else:
            #     pass
        # print(res)
        return res

    def action_invoice_in_refund(self, invoice_id):
        action = self.env.ref('account.action_invoice_in_refund')
        result = action.read()[0]
        result['views'] = [(
            self.env.ref('account.invoice_supplier_form').id, 'form')]
        result['res_id'] = invoice_id
        return result

    def int_to_roman(self, input):
        ints = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
        nums = ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')

        result = ""
        for i in range(len(ints)):
            count = int(input / ints[i])
            result += nums[i] * count
            input -= ints[i] * count
        return result

    def _get_sequence(self, name, prefix):
        seq = self.env['ir.sequence'].sudo().search([('code', '=', prefix)])
        if not seq:
            vals = {
                'name': name,
                'code': prefix,
                'implementation': 'no_gap',
                'prefix': prefix + '/',
                'suffix': '',
                'padding': 4
            }
            seq = self.env['ir.sequence'].sudo().create(vals)

        return seq.next_by_id()

    def _get_number_branch(self, ou, rp, bb):
        dt = datetime.now()
        dept = '/AP/'
        if bb == 'product':
            dept = '/LOG/'

        branch_code = ou.partner_id.barcode
        principal_code = rp.ref
        name = 'Branch Claim ' + ou.partner_id.ref + ' Principal ' + rp.ref
        prefix = branch_code + '/' + principal_code + dept + str(dt.year) + '/' + self.int_to_roman(dt.month)

        return self._get_sequence(name, prefix)

    def _get_number_pst(self, ou, rp, bb):
        dt = datetime.now()
        branch_code = ou.code
        principal_code = rp.ref
        dept = 'AP-CLM/'
        if bb == 'product':
            dept = 'LOG-CLM/'
        name = 'HC Claim ' + ou.partner_id.ref + ' Principal ' + rp.ref
        prefix = dept + principal_code + '/' + branch_code + '/' + str(dt.year) + '/' + self.int_to_roman(dt.month)
        return self._get_sequence(name, prefix)

    def _get_number(self, ou_id, partner_id,bb):
        ou = self.env['operating.unit'].search([('id', '=', ou_id)])
        rp = self.env['res.partner'].search([('id', '=', partner_id)])
        if self.user_has_groups('bsp_claim.group_claim_user,bsp_claim.group_claim_spv,bsp_claim.group_claim_manajer'):
            return self._get_number_pst(ou, rp,bb)
        else:
            return self._get_number_branch(ou, rp,bb)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            prefix = ''
            if vals['operating_unit_id']:
                # if vals['kx_id']:
                #     vals['name'] = vals['claim_letter']
                # else:

                vals['name'] = self._get_number(vals['operating_unit_id'], vals['partner_id'],vals['product_subtype'])
        if vals['is_nonclaim']:
            vals['name'] = vals['name'] + '-NK'
        result = super(ClaimCL, self).create(vals)
        result._update_link_data(result.id)
        # if result.kx_id:
        #     result.kx_id.write({'exim_status': 'CC',
        #                         'cc_id': result.id})

        return result

    @api.multi
    def write(self, vals):
        # Reset changed KX to NEW
        # for claim in self:
        #     # if claim.kx_id:
        #     #     claim.kx_id.write({'exim_status': 'NEW',
        #     #                        'cc_id': False})
        #     for line in claim.claimline_ids:
        #         _id = line.cn_id.id
        #         objcn = self.env['bsp.creditnote.other'].search([('id', '=', _id)])
        #         # update cn
        #         rec = objcn.write({'claimcl_id': False,
        #                            'total_claimed_amount': line.total_claimed_amount})

        # if 'kx_id' in vals:
        #     if 'claim_letter' in vals:
        #         vals['name'] = vals['claim_letter']


        result = super(ClaimCL, self).write(vals)
        realisasi = vals.get('realization_amount')
        is_nonclaim = vals.get('is_nonclaim')
        if realisasi is not None:
            alloc = self.claim_alloc()
        # Reset Used KX to CC
        for claim in self:
            if is_nonclaim is not None and claim.state == 'draft':
                nk = claim.name[-3:]
                if claim.is_nonclaim:
                    if nk != '-NK':
                        claim.write({'name': claim.name+'-NK'})
                else:
                    if nk == '-NK':
                        nm = claim.name[:len(claim.name)-3]
                        claim.write({'name': nm})

            if claim.state == 'paid' and claim.balance_amount <= 0:
                claim.write({'state': 'done',
                            'done_date': datetime.now()})
            elif claim.state == 'done' and claim.balance_amount > 0:
                claim.write({'state': 'paid'})

            claim._update_link_data(claim.id)
            # if claim.kx_id:
            #     claim.kx_id.write({'exim_status': 'CC',
            #                        'cc_id': claim.id
            #                        })

        return result


    @api.multi
    def unlink(self):
        for claim in self:
            if claim.state not in ('draft', 'cancel'):
                raise UserError(_('Cannot delete claim(s) which are already post or paid.'))
            # if claim.kx_id:
            #     claim.kx_id.write({'exim_status': 'NEW',
            #                     'cc_id': False})
        return super(ClaimCL, self).unlink()

    @api.multi
    def button_draft(self):
        oriname = self.name
        if oriname[:3] == 'REV':
            oriname = oriname[5:]
        newname = 'REV' + str(self.rev_seq + 1) + '/' + oriname
        dict_update = {
            'name': newname,
            'reason_reject_id': False,
            'state': 'draft',
            'rev_seq': self.rev_seq + 1
        }
        return self.write(dict_update)

    # # @api.multi
    # def is_claim_done(self):
    #     # lots of duplicate calls to action_invoice_paid, so we remove those already paid
    #     # for claim in self:
    #     if self.state == 'paid':
    #         if self.balance_amount <= 0:
    #             self.write({'state': 'done', 'done_date': datetime.now()})


    @api.multi
    def button_pending(self):
        for claim in self:
            if claim.is_from_bis:
                if not claim.claimline_ids:
                    raise UserError(_('Sorry, Claim can''t be changed to PENDING , list cl still empty'))
            if claim.print_count > 0:
                if claim.pending_date:
                    return self.write({'reason_reject_id': False, 'state': 'pending'})
                else:
                    raise UserError(_('Cannot PENDING claim(s) without  Send to HQ date.'))
                    # return self.write({'reason_reject_id': False, 'state': 'pending', 'pending_date': datetime.now()})
            else:
                raise UserError(_('Sorry, Claim amount is not valid or Claim letter is still not printed'))

    @api.multi
    def button_to_pending(self):
        for claim in self:
            old_state = claim.state
            if claim.print_count > 0:
                if claim.pending_date:
                    self.write({'reason_reject_id': False,'realization_amount':0, 'state': 'pending'})
                else:
                    self.write({'reason_reject_id': False,'realization_amount':0, 'state': 'pending', 'pending_date': datetime.now()})
                if old_state == 'post':
                    for line in claim.claimline_ids:
                         # line.write({'actual_claim_amount': 0})
                         line.cn_id.write({'state': 'printed',
                                      # 'total_claimed_amount': 0,
                                      'paid_total': 0})
            else:
                raise UserError(_('Sorry, Claim amount is not valid or Claim letter is still not printed'))


    @api.multi
    def button_reject(self):
        for claim in self:
            if claim.reason_reject_id:
                return self.write({'state': 'reject', 'reject_date': datetime.now()})
            else:
                raise UserError(_('Cannot reject claim(s) without a reason.'))


    @api.multi
    def button_post(self):
        for claim in self:
            if claim.receive_date and  claim.send_date:
                ret = self.write({'reason_reject_id': False,
                                   'state': 'post',
                                   'post_date': datetime.now()})
                # self.button_journals()
                return ret
            else:
                raise UserError(_('Cannot POST claim(s) without Receive and Send to Principal date.'))

    @api.multi
    def button_incomplete(self):
        for claim in self:
            if claim.receive_date:
                ret = self.write({'state': 'incomplete'})
                return ret
            else:
                raise UserError(_('Cannot set to InComplete  without Received Docs Date.'))



    @api.multi
    def button_done(self):
        return self.write({'reason_reject_id': False, 'state': 'done', 'done_date': datetime.now()})


    @api.multi
    def button_cancel(self):
        for claim in self:
            if claim.reason_reject_id:
                for cd in claim.claimline_ids:
                    cd.unlink()
                return self.write({'state': 'cancel', 'cancel_date': datetime.now()})
            else:
                raise UserError(_('Cannot cancel claim(s) without a reason.'))

    @api.model
    def _common_action_keys(self):
        """ Call it in your own child module
        """
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bsp.creditnote.other',
            'target': 'current',
            'context': {'parent_id': self.id, 'parent_model': self._name},
            'view_mode': 'tree',
        }

    @api.multi
    def _update_link_data(self, id):
        objclaim = self.env['bsp.claim.cl'].browse(id)
        for line in objclaim.claimline_ids:
            _id = line.cn_id.id
            objcn = self.env['bsp.creditnote.other'].search([('id', '=', _id)])
            # update cn
            rec = objcn.write({'claimcl_id': objclaim.id,
                               'total_claimed_amount': line.total_claimed_amount})
        return True

    # @api.multi
    # def add_cl(self):
    #     self.ensure_one()
    #     res = self._common_action_keys()
    #     # res["context"].update(
    #     #     {
    #     #         "search_default_filter_to_purchase": 1,
    #     #         "search_default_filter_for_current_supplier": 1,
    #     #     }
    #     # )
    #     commercial = self.partner_id.name
    #     res["name"] = "🔙 %s (%s)" % (_("Claim CL to Principal"), commercial)
    #     res["view_id"] = (
    #         self.env.ref("bsp_claim.cl_tree_view4claim").id)
    #     # res["search_view_id"] = (
    #     #     self.env.ref("purchase_quick.claim_search_view4purchase").id,
    #     # )
    #     return res
    #
    # def _get_quick_line(self, claim):
    #     return self.env["bsp.claim.cl.line"].search(
    #         [("cn_id", "=", claim.id), ("claimcl_id", "=", self.id)],
    #         limit=1,
    #     )
    #
    # def _add_quick_line(self, claim):
    #     vals = self._prepare_quick_line(claim)
    #     vals = self._complete_quick_line_vals(vals)
    #     self.write({'claimline_ids': [(0, 0, vals)]})
    #
    # def _prepare_quick_line(self, claim):
    #     res = self._get_quick_line_qty_vals(claim)
    #     res.update({
    #         'cn_id': claim.id
    #     })
    #     return res
    #
    # def _get_quick_line_qty_vals(self, claim):
    #     return {"cn_id": claim.id}
    #
    # def _complete_quick_line_vals(self, vals):
    #     form_parent = Form(self)
    #     form_line = False
    #     if vals.get('id'):
    #         for index, line in enumerate(self['claimline_ids']):
    #             if line.id == vals.get('id'):
    #                 form_line = getattr(form_parent, 'claimline_ids').edit(index)
    #                 del vals['id']
    #                 break
    #     init_keys = ['cn_id']
    #     init_vals = [(key, val) for key, val in vals.items()
    #                  if key in init_keys]
    #     if not form_line:
    #         form_line = getattr(form_parent, 'claimline_ids').new()
    #         form_line._values.update(init_vals)
    #         form_line._perform_onchange(init_keys)
    #
    #     update_keys = [key for key in vals.keys() if key not in init_keys]
    #     update_vals = [(key, val) for key, val in vals.items()
    #                    if key not in init_keys]
    #     form_line._values.update(update_vals)
    #     form_line._perform_onchange(update_keys)
    #     return form_line._values
    #
    # def _update_quick_line(self, claim, line):
    #     if claim.qty_to_process:
    #         vals = self._get_quick_line_qty_vals(claim)
    #         vals['id'] = line.id
    #         vals = self._complete_quick_line_vals(vals)
    #         line.write(vals)
    #     else:
    #         line.unlink()

    @api.multi
    def button_journals(self):
        if not self.ar_claim_move_id:
            self.ar_claim_move_id = self.create_ar_claim_journal('AR Claim CL:', self.prepare_ar_cl_journal())

    def prepare_ar_cl_journal(self):
        data_final = []
        ar_claim_vals = (0, 0, {
            'name': 'AR Claim ' + self.branch_code,
            'partner_id': self.partner_id.id,
            'date': self.claim_date,
            'company_id': self.env.user.company_id.id,
            'operating_unit_id': self.operating_unit_id.id,
            'debit': self.net_amount,
            'credit': 0,
            'account_id': self.company_id.ar_claim_account_id.id
        })
        data_final.append(ar_claim_vals)

        prepaid_claim_vals = (0, 0, {
            'name': 'Prepaid Claim (CL) ' + self.branch_code,
            'partner_id': self.partner_id.id,
            'date': self.cn_date,
            'company_id': self.env.user.company_id.id,
            'operating_unit_id': self.operating_unit_id.id,
            'debit': 0,
            'credit': self.net_amount,
            'account_id': self.company_id.claim_prepaid_account_id.id,
        })
        data_final.append(prepaid_claim_vals)
        return data_final

    def create_ar_claim_journal(self, desc, journal_vals):
        move_id = self.env['account.move'].sudo().create({
            'ref': desc + self.name or '',
            'journal_id': self.journal_id.id,
            'date': self.cn_date,
            'company_id': self.env.user.company_id.id,
            'operating_unit_id': self.operating_unit_id.id,
            'line_ids': journal_vals,
        })
        move_id.post()
        return move_id


    @api.multi
    def button_paid(self):

        if any([inv.state in {'draft', 'open'} for inv in
                (self.invoice_line_ids).mapped('invoice_id')]):
            raise UserError(
                _('Sorry, claim  %s can not be processed, because the claim already exists on draft/open invoice '
                  % self.name))

        if self.balance_amount <= 0:
            raise UserError(_('No Balance to paid anymore, DONE plz.'))

        product_name = 'Claim to Principal: ' + self.partner_id.ref
        product_id = self.env['product.product'].search([('name', '=', product_name)], limit=1)
        # journal_id = self.env['account.invoice'].with_context(type='in_refund')._default_journal()
        journal_id = self.sudo().env['account.journal'].search([('code', '=', 'CLM')], limit=1)
        # account_id = self.env['account.invoice.line'].with_context(journal_id=journal_id.id)._default_account()
        account_id = self.company_id.claim_income_account_id.id
        if self.claim_type in ('cncl'):
            account_id = self.company_id.claim_prepaid_account_id.id

        if not product_id:
            product_id = self.env['product.product'].create({
                'name': product_name,
                'type': 'service',
            })

        # for line in self.cn_ids:
        data_final = []
        invoice_line_vals = (0, 0, {
            'product_id': product_id.id,
            'name': product_id.name + ': ' + self.name,
            'quantity': 1,
            'account_id': account_id,
            'price_unit': self.balance_amount,
            'claimcl_id': self.id,
            'branch_code': self.branch_code,
            'document_date': self.claim_date
            # 'invoice_line_tax_ids': [(6, 0, self.tax_id.ids)],
        })
        data_final.append(invoice_line_vals)

        vendor_bills_id = self.env['account.invoice'].create({
            'type': 'in_refund',
            'date': self.claim_date,
            'date_invoice': date.today(),
            'payment_term_id': self.payment_term_id.id,
            'date_due': date.today(),      #+ relativedelta(days=10),
            'partner_id': self.partner_id.id,
            'company_id': self.env.user.company_id.id,
            'operating_unit_id': self.operating_unit_id.id,
            'journal_id': journal_id.id,
            'move_name': 'CLAIM',
            # 'account_id': self.partner_id.property_account_receivable_id.id,
            'account_id': self.company_id.ar_claim_account_id.id,
            'invoice_line_ids': data_final,
            'amount_total': self.balance_amount,
        })




        # if vendor_bills_id:
        #     self.write({'state': 'paid', 'paid_date': datetime.now()})

        result = self.action_invoice_in_refund(vendor_bills_id.id)
        return result

    @api.multi
    def button_print_claim(self):
        self.write({'print_count': self.print_count + 1})
        return self.env.ref('bsp_claim.action_report_print_form_claim_letter').report_action(self)


@api.multi
def action_claim_open(self):
    data_final = []

class ClaimCLline(models.Model):
    _name = 'bsp.claim.cl.line'
    _description = "BSP Others Claim line items"
    _rec_name ='claimcl_id'

    @api.multi
    @api.depends('actual_claim_amount')
    def _compute_claimed_amount(self):
        for rec in self:
            search_args = [('cn_id', '=', rec.cn_id.id)]
            res = self.read_group(search_args, ['actual_claim_amount'], [])
            last_total = res[0]['actual_claim_amount']
            rec.total_claimed_amount = last_total



    # @api.onchange('actual_claim_amount')
    # def onchange_actual_claim_amount(self):
    #     for rec in self:
    #         search_args = [('cn_id', '=', rec.cn_id.id)]
    #         res = self.read_group(search_args, ['actual_claim_amount'], [])
    #         last_total = res[0]['actual_claim_amount']
    #         if rec.cn_id.cn_total < (last_total - rec.actual_claim_old + rec.actual_claim_amount):
    #             raise UserError(_('Sorry, Claim amount too much'))
    #         rec.actual_claim_old = rec.actual_claim_amount
    #
    # def _get_actual_amount(self):
    #     if self.actual_claim_old == 0:
    #         self.actual_claim_old = self.actual_claim_amount

    claimcl_id = fields.Many2one("bsp.claim.cl", string="CC Number", required=True, ondelete='cascade')
    cn_id = fields.Many2one("bsp.creditnote.other", string="CN Number")
    description = fields.Char("Description")
    # branch_code = fields.Char(related="cn_id.branch_code", string="Branch code", store=True)
    customer_code = fields.Char(related="cn_id.customer_code", string="Customer", store=True)
    cn_total = fields.Float( string='CN Total', track_visibility='onchange', digits=dp.get_precision('Product Price'))
    actual_claim_amount = fields.Float(string='Actual Claim', track_visibility='onchange',
                                       digits=dp.get_precision('Product Price'))
    # actual_claim_old = fields.Float(string='Actual Claim', compute='_get_actual_amount', store=False)
    total_claimed_amount = fields.Float(string='Total Claimed', compute='_compute_claimed_amount',
                                        digits=dp.get_precision('Product Price'))

    paid_total = fields.Float( string='Paid Allocated', store=True, digits=dp.get_precision('Product Price'))
    ump_amount = fields.Float(string="UMP", track_visibility='onchange', digits=dp.get_precision('Product Price'))
    # principal_code = fields.Char(related="cn_id.principal_code",string="Principal Code", store=True)
    bsp_share = fields.Float(string="BSP share", digits=dp.get_precision('Product Price'))
    principal_share = fields.Float(string="Principal share")
    kc_no = fields.Char(related="cn_id.kc_no", string="KC Number", size=60, store=True)
    state = fields.Selection(
        [('draft', 'DRAFT'),
         ('pending', 'PENDING'),
         ('post', 'POST'),
         ('printed', 'PRINTED'),
         ('paid', 'PAID'),
         ('done', 'DONE'),
         ('canceled', 'CANCELED'),
         ('rejected', 'REJECTED')],
        string='CN Status', related="cn_id.state", readonly=False, store=True)
    exim_status = fields.Char("Exim status", track_visibility='onchange',
                              related="cn_id.exim_status",
                              size=3, readonly=False, store=True)

    def write(self, vals):
        if 'actual_claim_amount' in vals:
            if self.total_claimed_amount - self.actual_claim_amount + vals['actual_claim_amount'] > self.cn_total:
                raise UserError(_('Sorry, Claim#:' + self.cn_id.name + ', claim amount too much'))
        result = super(ClaimCLline, self).write(vals)

    @api.multi
    def unlink(self):
        for claimline in self:
            if claimline.claimcl_id:
                cn = self.env['bsp.creditnote.other'].search([('id', '=', claimline.cn_id.id)])
                claimed_amount = 0
                stt = 'NEW'
                # if claimline.claimcl_id.claim_type == 'discount':
                if claimline.claimcl_id.is_can_partial:
                    claimed_amount = cn.total_claimed_amount - claimline.actual_claim_amount
                    if claimed_amount > 0:
                        stt = 'CC'
                cn.write({'claimcl_id': None,
                          'exim_status': stt,
                          'total_claimed_amount': claimed_amount})

        return super(ClaimCLline, self).unlink()



class ClaimType(models.Model):
    _name = "bsp.claim.type"
    _description = "Claim Type"
    _order = 'sequence, id'

    # @api.depends('code')
    # def _compute_is_display(self):
    #     for rec in self:
    #         rec.is_display = True
    #         if not self.user_has_groups('bsp_claim.group_claim_user') and rec.code == 'other':
    #             rec.is_display = False

    name = fields.Char('Claim Type', required=True, index=True)
    code = fields.Char('Claim Type Code', required=True, index=True)
    color = fields.Integer('Color')
    sequence = fields.Integer('Sequence', help="Used to order the 'All Operations' kanban view", index=True)
    is_from_bis = fields.Boolean('Source from BIS', default=True)
    is_display = fields.Boolean('Always Display', default=True)
    is_can_partial = fields.Boolean('Can Partial Claim', default=False)
    # Statistics for the kanban view
    last_done_claim = fields.Char('Last 10 Done Pickings', compute='_compute_last_done_claim')
    count_claim_draft = fields.Integer(compute='_compute_claim_count')
    count_claim_pending = fields.Integer(compute='_compute_claim_count')
    count_claim_incomplete = fields.Integer(compute='_compute_claim_count')
    count_claim_post = fields.Integer(compute='_compute_claim_count')
    count_claim_paid = fields.Integer(compute='_compute_claim_count')
    count_claim_done = fields.Integer(compute='_compute_claim_count')
    count_claim_late = fields.Integer(compute='_compute_claim_count')
    coas = fields.Char('Grouping')
    coding=fields.Char('Coding', size=1)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        domain = []
        if not self.user_has_groups('bsp_claim.group_claim_user'):
            domain = [('is_display', '=', True)]
        return super().search(domain + args, offset=offset, limit=limit,
                              order=order, count=count)

    @api.model
    def search_count(self, args):
        domain = []
        if not self.user_has_groups('bsp_claim.group_claim_user'):
            domain = [('is_display', '=', True)]
        return super().search_count(domain + args)




    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []

        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            connector = '&' if operator in expression.NEGATIVE_TERM_OPERATORS else '|'
            domain = [connector, ('code', operator, name), ('name', operator, name)]
        claim_type_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return self.browse(claim_type_ids).name_get()

    @api.one
    def _compute_last_done_claim(self):
        # TDE TODO: true multi
        tristates = []
        for claim in self.env['bsp.claim.cl'].search([('claim_type_id', '=', self.id), ('state', '=', 'done')],
                                                        order='done_date desc', limit=10):
            if claim.date_done > claim.claim_date:
                tristates.insert(0, {'tooltip': claim.name or '' + ": " + _('Late'), 'value': -1})
            elif claim.invoice_id:
                tristates.insert(0, {'tooltip': claim.name or '' + ": " + _('Invoice exists'), 'value': 0})
            else:
                tristates.insert(0, {'tooltip': claim.name or '' + ": " + _('OK'), 'value': 1})
        self.last_done_claim = json.dumps(tristates)

    def _compute_claim_count(self):
        # TDE TODO count claim can be done using previous two
        domains = {
            'count_claim_draft': [('state', '=', 'draft')],
            'count_claim_pending': [('state', '=', 'pending')],
            'count_claim_incomplete': [('state', '=', 'incomplete')],
            'count_claim_post': [('state', '=', 'post')],
            'count_claim_paid': [('state', '=', 'paid')],
            'count_claim_done': [('state', '=', 'done')],
            'count_claim_late': [('claim_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                   ('state', 'in', ('pending','incomplete', 'post'))],
        }
        for field in domains:
            data = self.env['bsp.claim.cl'].read_group(domains[field] +
                                                        [('state', 'not in', ('cancel','reject')),
                                                         ('claim_type_id', 'in', self.ids)],
                                                        ['claim_type_id'], ['claim_type_id'])
            count = {
                x['claim_type_id'][0]: x['claim_type_id_count']
                for x in data if x['claim_type_id']
            }
            for record in self:
                record[field] = count.get(record.id, 0)

    def _get_action(self, action_xmlid):
        # TDE TODO check to have one view + custo in methods
        action = self.env.ref(action_xmlid).read()[0]
        if self:
            action['display_name'] = self.name
        return action

    def get_action_claim_tree_late(self):
        return self._get_action('bsp_claim.action_claim_tree_late')

    def get_action_claim_tree_paid(self):
        return self._get_action('bsp_claim.action_claim_tree_paid')

    def get_action_claim_tree_done(self):
        return self._get_action('bsp_claim.action_claim_tree_done')

    def get_action_claim_tree_draft(self):
        return self._get_action('bsp_claim.action_claim_tree_draft')

    def get_action_claim_tree_pending(self):
        return self._get_action('bsp_claim.action_claim_tree_pending')

    def get_action_claim_tree_incomplete(self):
        return self._get_action('bsp_claim.action_claim_tree_incomplete')

    def get_action_claim_tree_post(self):
        return self._get_action('bsp_claim.action_claim_tree_post')

    def get_action_claim_tree_done(self):
        return self._get_action('bsp_claim.action_claim_tree_done')

    def get_action_claim_tree_cancel(self):
        return self._get_action('bsp_claim.action_claim_tree_cancel')

    def get_action_claim_tree_reject(self):
        return self._get_action('bsp_claim.action_claim_tree_reject')

    def get_bsp_claim_action_claim_type(self):
        return self._get_action('bsp_claim.bsp_claim_action_claim_type')


