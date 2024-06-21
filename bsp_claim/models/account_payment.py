from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime




class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # def action_validate_invoice_payment(self):
    #     res = super(AccountPayment, self).action_validate_invoice_payment()
    #     for payment in self:
    #         payment.invoice_ids._claim_realloc()
    #     return res

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

    def _get_number(self, partner_id, payment_type):
        dt = datetime.now()
        rp = self.env['res.partner'].search([('id', '=', partner_id)])
        principal_code = rp.ref
        tp = payment_type[:2].upper()
        name = 'Payment Principal ' + tp + ' ' + rp.ref

        prefix = tp + principal_code + '/' + str(dt.year) + '/' + self.int_to_roman(dt.month)

        return self._get_sequence(name, prefix)

    @api.model
    def create(self, vals):
        if vals.get('is_claim', True):
            if vals['partner_id']:
                vals['name'] = self._get_number(vals['partner_id'], vals['payment_type'])
        if vals['pv_id']:
            if 'payment_date' not in vals:
                pv = self.env["bsp.payment.voucher"].browse(vals['pv_id'])
                vals['payment_date'] = pv.trx_date
                # vals['approval_date'] = pv.trx_date
        if 'bank_reference' not in vals:
            vals['bank_reference'] = vals['name']
        payment = super(AccountPayment, self).create(vals)

        return payment



    @api.one
    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        super(AccountPayment,self)._compute_destination_account_id()
        if self.is_claim:
            if self.partner_id:
                partner = self.partner_id.with_context(force_company=self.company_id.id)
                # self.destination_account_id = partner.property_account_receivable_id.id
                self.destination_account_id = self.company_id.ar_claim_account_id.id

    @api.depends('pv_id','pv_type')
    def _compute_voucher_references(self):
        for record in self:
            coa_code=''
            if record.pv_type in('bm','bk'):
                record.pv_amount = record.pv_id.remain_amount
                coa_code = '['+record.pv_id.ref_coa+']' if record.pv_id.ref_coa != False else ''

            if record.pv_id:
                record.payment_date = record.pv_id.trx_date
                record.approval_date = record.payment_date
                record.bank_reference = '%s%s' % (coa_code, record.pv_id.name)
            record.approval = record.payment_date
    @api.onchange('partner_id', 'payment_type')
    def _onchange_partner_id(self):
        for record in self:
            if self._context.get('active_model', '') != 'account.invoice':
                record.pv_id = False
                record.pv_amount = 0
                record.bank_reference = ''

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        super(AccountPayment, self)._onchange_payment_type()
        if self.is_claim:
            self.partner_type = 'supplier'

    @api.onchange('pv_id')
    def _onchange_pv_id(self):
        for p in self:
            if p.pv_type == 'bm':
                print (p.pv_id.name)
                if p.pv_id:
                    if p.amount > p.pv_id.remain_amount:
                        raise ValidationError(_('Sorry: BM Remain Amount not enought '))


    @api.onchange('is_claim')
    def _onchange_is_claim(self):
        if self.is_claim:
            self.partner_type = 'supplier'
            self.payment_type = 'inbound'

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        for p in self:
            active_id = self.env.context.get('active_id')
            if self._context.get('active_model', '') == 'account.invoice':
                invoice_id = self.env["account.invoice"].browse(active_id)
                p.pv_id=False
                p.bank_reference = ''
                if invoice_id:
                   if p.pv_type == 'bk':
                      if invoice_id.pvbis_id:
                         bk_id = self.env['bsp.payment.voucher'].search([('type', '=', 'bk'), ('state', '=', 'open'),
                                                                          ('ref_document', '=',
                                                                           invoice_id.pvbis_id.name)], limit=1)
                         if bk_id:
                            p.payment_date = bk_id.trx_date
                            p.approval_date = bk_id.trx_date
                            p.pv_id = bk_id.id
                            p.pv_amount = bk_id.total_amount
                            p.bank_reference = bk_id.name
                         else:
                              raise ValidationError(
                                  _('You can not create Payment , reference BK not available yet. Synch BK from HOCCD!'))

                      else:
                         raise ValidationError(_('PV cannot use this jurnal type'))
                   else:
                      if invoice_id.pvbis_id:
                         raise ValidationError(_('PV cannot use this jurnal type'))

    def _inverse_update_free(self):
        return True
    @api.multi
    @api.depends('journal_id')
    def _compute_pv_type(self):
        for payment in self:
            payment.pv_type = 'bm'
            if payment.journal_id.code =='PYD':
                payment.pv_type = 'bk'
            elif payment.journal_id.code == 'OFS':
                payment.pv_type = 'ofs'
            elif payment.journal_id.code == 'CSH1':
                payment.pv_type = 'CSH'



    @api.model
    def default_get(self, fields_list):
        res = super(AccountPayment, self).default_get(fields_list)
        # if res['payment_date']:
        #     res['approval_date'] = res['payment_date']
        # else:
        res['approval_date'] = datetime.now().date()
        active_id = self.env.context.get('active_id')
        if self._context.get('active_model', '') == 'account.invoice':
            invoice_id = self.env["account.invoice"].browse(active_id)

            if invoice_id.pvbis_id:
                journal = self.env['account.journal'].search([('code', '=', 'PYD')],limit=1)
                res['journal_id'] = journal.id
                res['pv_type'] = 'bk'
                # default  bk by pv
                bk_id = self.env['bsp.payment.voucher'].search([('type', '=','bk'),('state', '=','open'),
                                                            ('ref_document', '=',invoice_id.pvbis_id.name)], limit=1)
                if bk_id:
                    res['payment_date'] = bk_id.trx_date
                    res['approval_date'] = bk_id.trx_date
                    res['pv_id'] = bk_id.id
                    res['pv_amount'] = bk_id.total_amount
                    res['bank_reference'] = bk_id.name
                else:
                    raise ValidationError(_('You can not create Payment , reference BK not available yet. Synch BK from HOCCD!'))

        return res

    @api.constrains('payment_type')
    def _check_payment_type(self):
        if self.is_claim and self.payment_type == 'transfer':
            raise ValidationError(_('You can not create Payment type as Trasfer on Payment Claim.'))

    @api.depends('ref')
    def get_principal2(self):
        for v in self:
            if v.ref=='RBH':
               v.ref2='RBT'
            elif v.ref=='RBT':
               v.ref2='RBH'
            else:
               v.ref2 = v.ref

    is_claim = fields.Boolean('Is Principal Claim', default=True)
    ref = fields.Char(related="partner_id.ref", string="Principal", store=False)
    ref2 = fields.Char( string="Principal2", compute='get_principal2')
    bank_reference = fields.Char(" Bank Number/Ref.Number", required=True)
    ref_payment_id = fields.Many2one('account.payment', string='Payment Reference')
    pv_id = fields.Many2one('bsp.payment.voucher', string='Payment Voucher References',track_visibility='always')
    ref_coa = fields.Char("Ref. COA", related="pv_id.ref_coa", search='_coa_search')
    pv_amount = fields.Float("Voucher Amount", track_visibility='always', compute='_compute_voucher_references',
                                inverse='_inverse_update_free',
                                store=True, copy=False)
    pv_type = fields.Char("Voucher Type", compute='_compute_pv_type', store=False)
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled'),('done', 'Done'),
                              ('cancelled', 'Cancelled')], readonly=True, default='draft', copy=False, string="Status")
    approval_date = fields.Date("Principal Appropal Date")


    # result_trigger_field = fields.Char(store=False,)
    #
    # @api.onchange('result_trigger_field')
    # def onchange_result_trigger_field(self):
    #     print('This method will be called in edit mode')
    #     self.validate()


    def  cancel(self):
        super(AccountPayment, self).cancel()
        for ln in self.invoice_lines:
            ln.unlink()
    @api.multi
    def _coa_search(self, operator, operand):
        query = f""" select pym.id payment_id
                     from account_payment pym join bsp_payment_voucher pv on pv.id=pym.pv_id 
                     where pv.ref_coa like '%{operand.upper()}%'"""

        self._cr.execute(query)
        records = self._cr.fetchall()
        return [('id', 'in', [p[0] for p in records])]

    def  send_allocation_pv_to_ho(self):
        retval = False
        for payment in self:
            if payment.pv_type == 'bm':
                retval = payment.send_bm(payment.invoice_lines)
            # elif payment.pv_type == 'bk':
            #     retval = payment.send_bk(payment.invoice_lines)
        return  retval


    def write(self, vals):
        # invoice_lines = vals.get('invoice_lines',False)
        # if invoice_lines:
        #     for line in invoice_lines:
        #         if line[1]:
        #             if line[2]['amount'] == 0 and line[2]['allocated_amount'] == 0:
        #                 inv_line = self.env['payment.invoice.line'].browse(line[1])
        #                 inv_line.unlink()
        # if 'pv_id' in vals:  # keep assignment history
        #     for rec in self:
        #         rec.pv_id.write({'alloc_amount': rec.pv_id.alloc_amount - rec.amount})
        ret = super(AccountPayment, self).write(vals)
        if 'pv_id' in vals:
            for rec in self:
                if rec.pv_type == 'pv':
                   rec.pv_id.write({'alloc_amount': rec.pv_id.total_amount})
                if rec.pv_type == 'bm':
                   rec.pv_id.write({'alloc_amount': rec.pv_id.calc_alloc_amount()})
                   # rec.pv_id.write({'alloc_amount': rec.pv_id.invoice_line_amount})
        return ret


    def action_done(self):
        alloc_amount = sum((self.invoice_lines).mapped('allocated_amount'))
        if not alloc_amount  or alloc_amount <= 0:
            raise ValidationError(_('Sorry :  Allocated PV not found on Payment Items'))

        self.send_allocation_pv_to_ho()
        self.write({'state': 'done'})
        if self.pv_id.remain_amount < 100:
            self.pv_id.write({'state': 'close'})
        else:
            self.pv_id.write({'state': 'alloc'})
    def action_reset2posted(self):
        for payment in self:
            if payment.state != 'done':
                continue
            if payment.pv_type != 'bm':
                payment.write({'state': 'posted'})
            else:
                isExist = self.reset_bm()
                if not isExist:
                    raise ValidationError(_('WARNING :  Data on HOCCD can not be reset, need to update HOCCD manually'))





    def GetAllocatedInvoice(self,pv_no):
        partners_list = self.partner_id.child_ids.ids
        partners_list.append(self.partner_id.id)
        line_invoices = []
        type = []
        Invoice = self.env['account.invoice']
        pv = self.env['bsp.payment.voucher'].search([('name', '=', pv_no)], limit=1)
        if pv:

            if pv.type == 'bk':
                type.append('in_invoice')
            elif self.type == 'bm':
                type.append('out_invoice')
                type.append('in_refund')
            invoices = Invoice.search(['|',
                                   '&',
                                   '&',
                                   '&',
                                   ('partner_id', 'in', partners_list),
                                   ('state', 'in', ('posted', 'open')),
                                   ('type', 'in', type),
                                   ('residual', '>', 0.0), ('id', 'in', self.reconciled_invoice_ids.ids)],
                                  order="date_invoice")
        # ('amount_residual', '>', 0.0)], order="invoice_date")
            for invoice in invoices:

                data = {
                    'invoice_id': invoice.id,
                  'amount_total': invoice.amount_total,
                  'residual': invoice.residual,  # invoice.amount_residual,
                  'amount': 0.0,
                   'date_invoice': invoice.date_invoice,  # invoice.invoice_date,
                 }
                line_invoices.append(data)

    def  get_alloc_bm(self):
        for pv in self:
            inv_lines = self.env['account.invoice.line']
            lines = self.env['payment.invoice.line']
            payments = self.env['account.payment'].sudo().search([('pv_id', '=', pv.id)])
            if payments:
                for payment in payments:
                    print('Payment:'+ payment.name)
                    payment_lines = self.env['payment.invoice.line'].sudo().search([('payment_id','=', payment.id),('allocated_amount','<>',0)])
                    lines |= payment_lines
                if lines:
                    for line in lines:
                        invoice_lines = self.env['account.invoice.line'].sudo().search([('invoice_id', '=', line.invoice_id.id)])
                        inv_lines |= invoice_lines

    def send_bm(self,pv_lines):
        try:
            ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
            cursor, connection = ou.connect_to_bis()
            idUMP = 0
            queryCOATitipan= "SELECT int_banktokendetailid idUMP FROM  banktoken_dtl WHERE int_banktokenid = " + str(self.pv_id.ref_document_id)+\
                             " AND int_coaid IN (SELECT int_coaid FROM coa_ms WHERE txt_coacode = '" + self.pv_id.ref_coa + "') limit 1;"
            cursor.execute(queryCOATitipan)
            record = cursor.fetchone()
            if record:
                idUMP = record["idUMP"]
            else:
                 raise ValidationError(_("Error: COA UMP/TITIPAN not found!!"))

            for pv in pv_lines:
                if pv.allocated_amount:
                    for inv_line in pv.invoice_id.invoice_line_ids:
                        coa = self.pv_id.ref_coa
                        dAmount = inv_line.price_subtotal
                        rmk = ''
                        # masukan ke coa pembulatan Kurang
                        if inv_line.product_id.name.upper() == 'PENAMBAHAN LAIN-LAIN':
                            rmk = '28.9'

                        # masukan ke coa pembulatan lebih
                        if inv_line.product_id.name.upper() == 'PENGURANGAN LAIN-LAIN':
                            rmk = '28.8'

                        coding = ''
                        if inv_line.claimcl_id:
                            if inv_line.claimcl_id.coding:
                                coding = inv_line.claimcl_id.coding.upper()
                            else:
                                coding = inv_line.claimcl_id.claim_type_id.name[-1].upper()
                        byrArg = [
                            self.pv_id.ref_document_id,
                            inv_line.claimcl_id.branch_code if inv_line.claimcl_id else inv_line.branch_code,
                            'BM',
                            inv_line.claimcl_id.name if inv_line.claimcl_id else inv_line.name,
                            inv_line.claimcl_id.vistex if inv_line.claimcl_id and inv_line.claimcl_id.vistex else '',  #referensi principal
                            inv_line.claimcl_id.service_inv if inv_line.claimcl_id and inv_line.claimcl_id.service_inv else '',  #faktur jasa
                            0, #pph amount
                            dAmount, #total without  tax amount
                            inv_line.claimcl_id.remark if inv_line.claimcl_id else rmk,
                            coding,
                            coa,
                            self.payment_date.strftime("%Y-%m-%d"),
                            inv_line.id
                        ]
                        cursor.callproc('usp_insert_banktoken_bayar', byrArg)
                else:
                    pv.unlink()
            dSendAlloc = self.pv_id._calc_send_alloc_amount() + (self.amount - self.balance)
            # dSendAlloc = self.pv_id.get_allocated_amount_send() + (self.amount - self.balance)
            dRemain = self.pv_id.total_amount - dSendAlloc
            # if dRemain != 0 and dRemain < 100:
            #     byrArg = [
            #         self.pv_id.ref_document_id,
            #         '',
            #         'SISA ALOKASI',
            #         'Pembulatan Lebih BM',
            #         '',
            #         '',
            #         0,  # pph amount
            #         self.pv_id.remain_amount,  # total without  tax amount
            #         'Pembulatan Lebih BM',
            #         '','',
            #         self.payment_date.strftime("%Y-%m-%d")
            #     ]
            #     cursor.callproc('usp_insert_banktoken_bayar', byrArg)
            #     dRemain = 0
            #
            queryCOATitipan = "update banktoken_dtl set curr_amount = round("+str(dRemain)+",2)  where  int_banktokendetailid = "+str(idUMP)
            cursor.execute(queryCOATitipan)

            qsumbiaya = "select sum(curr_amount) totBiaya from banktoken_dtl where int_banktokenid=" + str(self.pv_id.ref_document_id)
            cursor.execute(qsumbiaya)
            totBiayaDict = cursor.fetchone()
            totBiaya = 0
            if totBiayaDict:
                totBiaya = totBiayaDict.get("totBiaya", 0)

            qupdatetotal = "Update banktoken_hdr set curr_amounttotal = " + str(totBiaya) + " where int_banktokenid=" + \
                           str(self.pv_id.ref_document_id)
            cursor.execute(qupdatetotal)

            connection.commit()
        except Exception as e:
            raise e



    def reset_bm(self):
        try:
            ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
            cursor, connection = ou.connect_to_bis()
            isExist = 0
            for pv in self.invoice_lines:
                if pv.allocated_amount:
                    if pv.invoice_id.invoice_line_ids:
                        idUMP = 0
                        queryCOATitipan = "SELECT int_banktokendetailid idUMP FROM  banktoken_dtl WHERE int_banktokenid = " + str(
                            self.pv_id.ref_document_id) + \
                                          " AND int_coaid IN (SELECT int_coaid FROM coa_ms WHERE txt_coacode = '" + self.pv_id.ref_coa + "') limit 1;"
                        cursor.execute(queryCOATitipan)
                        record = cursor.fetchone()
                        if record:
                            idUMP = record["idUMP"]
                        else:
                            raise ValidationError(_("Error: COA UMP/TITIPAN not found!!"))

                        self.write({'state': 'posted'})
                        dSendAlloc = self.pv_id._calc_send_alloc_amount() - (self.amount - self.balance)
                        # dSendAlloc = self.pv_id.get_allocated_amount_send() - (self.amount - self.balance)
                        dRemain = self.pv_id.total_amount - dSendAlloc


                        query_where = ' and int_invlineid in %s' % (
                            str(tuple([invline.id for invline in pv.invoice_id.invoice_line_ids]))).replace(',)', ')')
                        queryExist = "SELECT count(*) isExist FROM  banktoken_dtl WHERE int_banktokenid = " + str(
                            self.pv_id.ref_document_id) + query_where
                        cursor.execute(queryExist)
                        record = cursor.fetchone()
                        if record:
                            isExist = record["isExist"]
                        # query_where = ' and int_invlineid in %s' % (
                        #     str(tuple([invline.id for invline in pv.invoice_id.invoice_line_ids]))).replace(',)', ')')
                        if isExist:
                            query = "DELETE FROM banktoken_dtl where int_banktokenid = " + str(self.pv_id.ref_document_id) + query_where
                            cursor.execute(query)
                            queryCOATitipan = "update banktoken_dtl set curr_amount = round("+str(dRemain)+",2)  where  int_banktokendetailid = "+str(idUMP)
                            cursor.execute(queryCOATitipan)
                            connection.commit()
            return isExist
        except Exception as e:
            raise e



class PaymentInvoiceLine(models.Model):
    _inherit = 'payment.invoice.line'

    # add by dk
    # current_residual = fields.Float(compute='compute_current_residual',
    #                                 string='Current Residual',
    #                                 help="Current residual amount")
    # allocated_amount = fields.Float(compute = 'compute_allocation_amount',
    #                             string='Allocation amount paid',
    #                             help="Allocation amount paid in journal",
    #                             store=True)

    # compute = 'compute_allocation_amount',

    # end add

    # def compute_current_residual(self):
    #     for line in self:
    #         if line.invoice_id:
    #             line.current_residual = line.invoice_id.residual
    # @api.depends('current_residual')
    # def compute_allocation_amount(self):
    #     move_line_obj = self.env['account.move.line']
    #     reconcile_obj = self.env['account.partial.reconcile']
    #     for rec in self:
    #         rec.allocated_amount = 0
    #         debit_move_id = move_line_obj.search([('invoice_id', '=', rec.invoice_id.id),('debit','>',0)], limit=1)
    #         credit_move_id = move_line_obj.search([('payment_id', '=', rec.payment_id.id), ('credit', '>', 0)], limit=1)
    #         if debit_move_id and credit_move_id:
    #             reconcile_lines = reconcile_obj.search([('debit_move_id', '=', debit_move_id.id),('credit_move_id', '=', credit_move_id.id)])
    #             if reconcile_lines:
    #                 for recon in reconcile_lines:
    #                     rec.allocated_amount += recon.amount



    def unreconcile_line(self):
        for payment_alloc in self:
            if payment_alloc.allocated_amount > 0:
                if payment_alloc.payment_id.payment_type == 'outbound':
                    credit_aml = payment_alloc.payment_id.move_line_ids.filtered(lambda line: line.debit > 0.0)
                    credit_aml.with_context(invoice_id=payment_alloc.invoice_id.id).remove_move_reconcile()
                if payment_alloc.payment_id.payment_type == 'inbound':
                    credit_aml = payment_alloc.payment_id.move_line_ids.filtered(lambda line: line.credit > 0.0)
                    credit_aml.with_context(invoice_id=payment_alloc.invoice_id.id).remove_move_reconcile()
                pv_id = payment_alloc.payment_id.pv_id
                if pv_id:
                    if pv_id.type == 'bk':
                       pv_id.write({'state':'open','alloc_amount':0})
                    elif pv_id.type == 'bm':
                        stt = pv_id.state
                        alloc = pv_id.calc_alloc_amount()
                        # alloc = pv_id.invoice_line_amount()
                        if alloc <= 0:
                           stt='open'
                        pv_id.write({'state': stt,'alloc_amount':alloc})



    def create(self,vals):
        # apl = False
        # if vals.get('allocated_amount', 0) > 0:
        apl = super(PaymentInvoiceLine, self).create(vals)
        return apl
    def unlink(self):
        # if self.env.user != 1:
        #     raise ValidationError(_('Sorry :  this user not allow to delete payment item'))
        if self.payment_id.state == 'done':
            raise ValidationError(_('Sorry : DONE Payment cannot be updated!'))
        self.unreconcile_line()
        ret = super(PaymentInvoiceLine, self).unlink()
        return ret

class AccountRegisterPayment(models.TransientModel):
    _inherit = 'account.register.payments'

    @api.model
    def default_get(self, fields_list):
        res = super(AccountRegisterPayment, self).default_get(fields_list)
        if self._context.get('active_model', '') == 'account.invoice':
            raise ValidationError(_('Sorry :  Claim Payment can not validate from this modul'))
        return res







