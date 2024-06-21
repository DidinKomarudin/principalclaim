from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError, UserError
from mysql.connector import Error

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'


    claim_id = fields.Many2one(
        comodel_name='bsp.claim.principal',
        string='Add Claim Principal',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Load the vendor refund based on selected claim. Several claim can be selected.'
    )
    ref = fields.Char(related="partner_id.ref", string="Principal", store=False)
    pvbis_id = fields.Many2one('bsp.payment.voucher', string='PV-BK References', track_visibility='always')
    pvbis_no = fields.Char('No PV BIS', size=30)
    claimcl_ids = fields.One2many('bsp.claim.cl', 'invoice_id', string="Claims")
    invoice_amount = fields.Monetary("Invoice Amount",compute='_compute_amount')
    correction_amount = fields.Monetary("Correction Amount", compute='_compute_amount')
# jika refund, alokasikan total pembayaran ke realisasi line item billing
#     @api.multi

    @api.model
    def default_get(self, fields_list):
        res = super(AccountInvoice, self).default_get(fields_list)
        res['move_name'] = 'CLAIM'
        # journal_id = self.env['account.journal'].search([('code', '=', 'CLM')], limit=1)
        # account_id = self.env.user.company_id.claim_income_account_id.id
        # res['journal_id'] = journal_id.id
        # res['account_id'] = account_id
        return res
    def _compute_amount(self):
        # add by dk 2023-11-04
        inv_total = 0
        add_total = 0
        sub_total = 0
        for line in self.invoice_line_ids:
            if line.product_id.name.upper() == 'INVOICE':
                inv_total += line.price_subtotal
            if line.product_id.name.upper() == 'PENAMBAHAN LAIN-LAIN':
                add_total += line.price_subtotal
            if line.product_id.name.upper() == 'PENGURANGAN LAIN-LAIN':
                sub_total += line.price_subtotal
        self.invoice_amount = inv_total
        self.correction_amount = add_total  # sub_total - add_total
        # end add
        round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_untaxed -= (inv_total + add_total)
        self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        self.amount_total  += (inv_total +  add_total)
        # if self.amount_total < 0:
        #     self.amount_total = -self.amount_total
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id
            amount_total_company_signed = currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date_invoice or fields.Date.today())
            amount_untaxed_signed = currency_id._convert(self.amount_untaxed, self.company_id.currency_id, self.company_id, self.date_invoice or fields.Date.today())
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

    def assign_outstanding_credit(self,credit_aml_id):
        result = super(AccountInvoice,self).assign_outstanding_credit(credit_aml_id)
        self.GetInvoiceLine(credit_aml_id)
        return result

    def GetInvoiceLine(self,credit_aml_id):
        move_line = self.env['account.move.line'].browse(credit_aml_id)
        if move_line.payment_id:
            invoice = self.env['account.invoice'].search([('id','=',self.id)])
            if invoice:
                PaymentLine = self.env['payment.invoice.line']
                paymentLines = PaymentLine.search([('payment_id','=',move_line.payment_id.id),('invoice_id','=',invoice.id)])
                for pl in paymentLines:
                    pl.unlink()
                data = {
                        'payment_id': move_line.payment_id.id,
                        'invoice_id': invoice.id,
                        'amount_total': invoice.amount_total,
                        'residual': invoice.residual, #invoice.amount_residual,
                        'amount': 0,
                        'date_invoice': invoice.date_invoice,  # invoice.invoice_date,
                    }
                pym = PaymentLine.create(data)
                pym.compute_allocation_amount()

    @api.multi
    def _claim_realloc(self):
        for record in self:
            print ('record.type:' + record.type)
            realization_amount = record.amount_total - record.residual
            if record.type != 'in_refund' or realization_amount <= 0:
               break
            if record.residual <= 0:
                for line in record.invoice_line_ids:
                    self.calc_claim_realization_amount(line.claimcl_id, 0 )


            # realization_amount = record.amount_total - record.residual
            # for claim in sorted(record.claimcl_ids, key=lambda x: x.claim_date):
            # # for claim in record.claimcl_ids:
            #     objclaim = self.env['bsp.claim.cl'].search([('id', '=', claim.id)])
            #     if objclaim:
            #         tot_paid = objclaim.net_amount
            #         if tot_paid > 0:
            #             if realization_amount <= tot_paid:
            #                 tot_paid = realization_amount
            #                 realization_amount = 0
            #             else:
            #                 realization_amount -= tot_paid
            #             objclaim.write({'realization_amount': tot_paid})
        return True

    @api.multi
    def _claim_realloc_new(self):
        for record in self:
            for inv_line in record.invoice_line_ids:
                tot_payment = sum(self.env['account.invoice.line']
                                  .search([('claimcl_id', '=', inv_line.claimcl_id.id)])
                                  .mapped('payment_amount'))
                inv_line.claimcl_id.write({'realization_amount': tot_payment})
        return True

    def _realloc_invoice_to_claim(self):
        for inv in self:
            realization_amount = inv.amount_total - inv.residual
            if inv.type != 'in_refund':
               break
            for inv_line in inv.invoice_line_ids:
                if inv.state == 'paid':
                    if inv_line.claimcl_id:
                       tot_paid = inv_line.price_unit
                       if tot_paid > 0:
                          # if realization_amount <= tot_paid:
                          #    tot_paid = realization_amount
                          #    realization_amount = 0
                          # else:
                          #    realization_amount -= tot_paid
                          inv_line.write({'payment_amount': tot_paid})
                else:
                    inv_line.write({'payment_amount': 0})
        # return True

    def calc_claim_realization_amount(self, claim,corr):
        realization_amount = 0
        correction_amount = 1
        if claim.correction_amount == False and claim.realization_amount:
           if claim.state == 'paid':
              correction_amount += (claim.net_amount - claim.realization_amount)
        claim.sudo().write({'correction_amount': correction_amount})

        lineall = self.env['account.invoice.line'].search([('claimcl_id', '=', claim.id)])

        for la in lineall:
            if la.invoice_id.state != 'cancel':
                realization_amount += la.price_unit
        realization_amount -= (claim.correction_amount + corr - 1 )
        # line.claimcl_id.realization_amount = realization_amount
        claim.sudo().write({'realization_amount': realization_amount})

    def _compute_residual(self):
        res = super(AccountInvoice, self)._compute_residual()
        # do the things here
        # self._claim_realloc()
        if self.state not in ('draft','cancel'):
            self._realloc_invoice_to_claim()
        return res

    @api.multi
    def return_confirmation(self, isOK, desc, docs):
        return {
            'name': desc,
            'type': 'ir.actions.act_window',
            'res_model': 'claim.confirm.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_btn_ok':isOK, 'default_yes_no': docs}
        }


    # Do some code

    # def action_cancel(self):
    #     invoice = super(AccountInvoice, self).action_cancel()
    #     # reset Claim Allocation
    #     for line in self.invoice_line_ids:
    #             # if hasattr(line[2], 'claimcl_id'):
    #          if line.claimcl_id:
    #             # claim = self.env['bsp.claim.cl'].search([('id', '=',line.claimcl_id.id)], limit=1) #line[2]['claimcl_id'])], limit=1)
    #             line.claimcl_id.sudo().write({'realization_amount': 0})
    #             for clline in line.claimcl_id.claimline_ids:
    #                 # clline.sudo().write({'actual_claim_amount': 0})
    #                 clline.cn_id.sudo().write({'state': 'printed',
    #                                       # 'total_claimed_amount': 0,
    #                                       'paid_total': 0})
    #     return invoice

    @api.multi
    def action_invoice_cancel(self):
        set_to_cancel = False
        for invoice in self:
            if invoice.state in ('paid'):
                raise UserError(
                    _("Set to Cancel rejected: PAID invoice has been sent to HO"))
            if invoice.pvbis_no != False:
                self.delete_pv_claim_items()
            #     raise UserError(_("Set to Cancel rejected: invoice has been sent to BIS AP.(PV:"+invoice.pvbis_no+")"))
            # TODO : DELETE ITEM PV
            # for il in invoice.invoice_line_ids:
            #     il.unlink()

        return super(AccountInvoice, self).action_invoice_cancel()
    def delete_pv_claim_items(self):
        sukses = False
        for invoice in self:
            if invoice.state == 'open':
                 try:
                    if invoice.pvbis_id:
                        ou = self.env['operating.unit'].search([('code', '=', 'BISAP')], limit=1)
                        cursor, connection = ou.connect_to_bis()
                        query = " SELECT count(*) jml from pc_payment_voucher where Status_PV='PENDING' and No_PV = '"+invoice.pvbis_id.name+"'"
                        cursor.execute(query)
                        record = cursor.fetchone()
                        if record["jml"]:
                           query ="DELETE FROM pc_payment_voucher_bayar where  No_PV = '"+invoice.pvbis_id.name+"'"
                           cursor.execute(query)
                           connection.commit()
                        else:
                            raise UserError(
                            _("Set to Cancel rejected: invoice has been sent to BIS AP.(POSTED PV:" + invoice.pvbis_no + ")"))
                        # Reset PV to open
                        self.pvbis_id.write({'alloc_amount':0,'state':'open','ref_document':False})
                    self.pvbis_no = False
                    self.pvbis_id = False
                 except Error as e:
                    print("Error while connecting to MySQL", e)

    # def action_invoice_draft(self):
    #     set_to_draft = True
    #     for line in self.invoice_line_ids:
    #          if line.claimcl_id:
    #             if line.claimcl_id.state in ('paid','done'):
    #                 set_to_draft = False
    #
    #     if set_to_draft == True:
    #         res = super(AccountInvoice, self).action_invoice_draft()
    #     else:
    #         raise UserError(_("Set to Draft rejected: Some invoice items (Claims) has been invoiced."))

    def action_invoice_open(self):
        for record in self:
            for inv_line in record.invoice_line_ids:
                if inv_line.claimcl_id and (inv_line.balance_amount <= 0 or inv_line.price_unit <= 0):
                    raise ValidationError(
                        _("Sorry: line item has invalid balance/price amount"))
                elif inv_line.price_unit<=0:
                    raise ValidationError(
                        _("Sorry: line item has invalid balance/price amount"))

        return super(AccountInvoice, self).action_invoice_open()




    def IsAllocationExist(self,cursor,connection,pv_no):
        query = f'''select count(*) jml from pc_payment_voucher_bayar where No_PV='{pv_no}' '''
        cursor.execute(query)
        record = cursor.fetchone()
        return record["jml"]

    def send_invoice_ho(self):
        # global connection, cursor
        global connection, cursor
        sukses = False
        totBKAmount = 0
        # cursor, connection = any
        for invoice in self:
            if invoice.state == 'draft':
               for inv_line in invoice.invoice_line_ids:
                   if inv_line.claimcl_id and (inv_line.balance_amount <= 0 or inv_line.price_unit <= 0):
                       raise ValidationError(
                           _("Sorry: line item has invalid balance/price amount"))
                   elif inv_line.price_unit <= 0:
                       raise ValidationError(
                           _("Sorry: line item has invalid balance/price amount"))
                # if invoice.pvbis_no:
                #     return self.return_confirmation(True, 'Synch Confirmation', 'PV is exists on BISAP' + invoice.pvbis_no)

            # if invoice.amount_total > invoice.pvbis_id.remain_amount:
            #     raise ValidationError(
            #         _("Sorry: Nominal PV > PV Bis AP"))
            try:
                    ou = self.env['operating.unit'].search([('code', '=', 'BISAP')], limit=1)
                    cursor, connection = ou.connect_to_bis()

                    if self.IsAllocationExist(cursor,connection,invoice.pvbis_id.name):
                        cursor.close()
                        connection.close()
                        return self.return_confirmation(True, 'PV Confirmation',
                                                        'PV:' + invoice.pvbis_id.name+ ' Had have allocation list, plz check on BIS AP')

                    query = f"""
                    INSERT  INTO `pc_payment_voucher_bayar`(
                        `No_PV`,
                        `Kode_Cabang`,
                        `Jenis_Biaya`,
                        `No_Dokumen`,
                        `Tgl_Dokumen`,
                        `No_Referensi`,
                        No_FakturJasa,
                        Dpp,
                        PPn,
                        PPHBsp,
                        `Nominal_Biaya`,
                        `Keterangan`,
                        `Koding`
                        )
                        VALUES """

                    inst_lines = ""
                    for inv_line in invoice.invoice_line_ids:
                        jb = inv_line.product_id.name
                        if jb[:5].upper() == 'CLAIM':
                            jb = 'Claim'
                        prog = ''
                        coding = ''
                        if inv_line.claimcl_id:
                            if inv_line.claimcl_id.coding:
                                coding = inv_line.claimcl_id.coding.upper()
                            else:
                                coding = inv_line.claimcl_id.claim_type_id.name[-1].upper()
                        if inv_line.remark:
                            prog = (inv_line.remark).replace("'","")
                        inst_data = f"""
                                 (
                                     '{invoice.pvbis_id.name}',
                                     '{inv_line.branch_code}',
                                     '{jb}',
                                     '{inv_line.claimcl_id.name if inv_line.claimcl_id else inv_line.name}',
                                     '{inv_line.claimcl_id.claim_date if inv_line.claimcl_id else inv_line.document_date}',
                                     '{inv_line.claimcl_id.cn_principal if inv_line.claimcl_id.cn_principal else ""}',
                                     '{inv_line.claimcl_id.service_inv if inv_line.claimcl_id.service_inv else ""}',
                                     {inv_line.claimcl_id.claim_amount if inv_line.claimcl_id else inv_line.price_unit},
                                     {inv_line.claimcl_id.tax_amount if inv_line.claimcl_id else 0},
                                     {inv_line.claimcl_id.pph1_amount if inv_line.claimcl_id else 0},  
                                     {inv_line.price_unit},
                                     '{prog}',
                                     '{coding}'
                                )
                                """
                        if inst_lines == "":
                            inst_lines = inst_data
                        else:
                            inst_lines += ',' + inst_data

                    query += inst_lines + ';'
                    cursor.execute(query)
                    connection.commit()
                    cursor.execute("select ufn_pv_bk_amount('" + invoice.pvbis_id.name + "') bkamount")
                    totBKAmount = cursor.fetchone()['bkamount']

                    sukses = True

            except Error as e:
                    print("Error while connecting to MySQL", e)
                    return self.return_confirmation(True, 'Synch Confirmation', 'FAIL send PV to BISAP: ' + e.msg)

            finally:
                    try:
                        if sukses:
                            res = self.action_invoice_open()
                            if not res:
                                connection.rollback()
                                cursor.close()
                                connection.close()
                                return self.return_confirmation(True, 'Synch Confirmation',
                                                                'NOT SUCCESS send PV to BISAP')
                            cursor.close()
                            connection.close()
                            self.write({'pvbis_no': invoice.pvbis_id.name})
                            invoice.pvbis_id.write({
                                'total_amount': totBKAmount,
                                'alloc_amount': totBKAmount,
                                'ref_document': invoice.number,
                                'state': 'alloc'
                            })
                            # invoice.pvbis_id.write({
                            #     'alloc_amount': invoice.pvbis_id.alloc_amount + invoice.amount_total,
                            #     'ref_document': invoice.number,
                            #     'state':'alloc'
                            # })
                            return self.return_confirmation(True, 'Synch Confirmation',
                                                            'SUCCESS send PV to BISAP:' + invoice.pvbis_no)
                    except Exception as e:
                        raise ValidationError(
                            _(e))
                        # ignored, just a consequence of the previous exception
                        # pass



    @api.model
    def _create_from_claim_multiselect(self, claims):
        if not claims:
            return False
        if claims._name not in ('bsp.claim.cl'):
            raise ValidationError(
                _("This action only works in the context of claims"))
        if claims._name == 'bsp.claim.cl':
            # search instead of mapped so we don't include archived variants
            claimsrejected = self.env['bsp.claim.cl'].search([
                ('id', 'in', claims.ids),('state', 'not in', ['post','paid'])
            ])
            if claimsrejected:
                raise ValidationError(
                    _("This action only works for the Posted and partial Paid Claims"))

        if claims._name == 'bsp.claim.cl':
            # search instead of mapped so we don't include archived variants
            unique_list = []

            # traverse for all elements
            for x in claims:
                pid = x.partner_id
                if x.partner_id.ref in ('RBT','RBH'):
                    pid = 131
                # check if exists in unique_list or not
                if pid not in unique_list:
                    unique_list.append(pid)
            if len(unique_list) > 1:
                raise ValidationError(
                    _("This action only works for a Principal ONLY"))

            claimList = self.env['bsp.claim.cl'].search([
                ('id', 'in', claims.ids),('balance_amount','>',0)
            ])
            # claims1 = self.env['bsp.claim.cl'].search([
            #     ('id', 'in', claims.ids),('balance_amount','>',0)
            # ], limit=1)

        # date_invoice = self.default_get(['date_invoice'])['date_invoice']
            if not claimList:
                raise ValidationError(
                    _("Valid Claims not found"))
            try:
                passMess = ''
                isPass = 1
                for line in claimList:
                    if line.state == 'paid':
                        if any([inv.state in {'draft','open'} for inv in (line.invoice_line_ids).mapped('invoice_id')]):
                           passMess += line.name + ", "
                           isPass = 0
                if isPass == 0:
                    raise ValidationError(_('Sorry, claim(s) %s can not be processed, because the claim(s) already exists on draft/open invoice '
                                            % passMess))

                data_final = []
                total_amount = 0.0
                partner_id = claimList[0].partner_id.id
                product_name = 'Claim to Principal: ' + claimList[0].partner_id.ref
                product_id = self.env['product.product'].search([('name', '=', product_name)], limit=1)
                # journal_id = self.env['account.invoice'].with_context(type='in_refund')._default_journal()
                journal_id = self.env['account.journal'].search([('code', '=', 'CLM')], limit=1)
                # account_id = self.env['account.invoice.line'].with_context(journal_id=journal_id.id)._default_account()
                account_id = claimList[0].company_id.claim_income_account_id.id
                if claimList[0].claim_type in ('cncl'):
                    account_id = claimList[0].company_id.claim_prepaid_account_id.id

                if not product_id:
                    product_id = self.env['product.product'].create({
                        'name': product_name,
                        'type': 'service',
                    })

                for line in claimList:
                    invoice_line_vals = (0, 0, {
                        'product_id': product_id.id,
                        'name': product_id.name + ': ' + line.name,
                        'quantity': 1,
                        'account_id': account_id,
                        'price_unit': line.balance_amount,
                        'claimcl_id': line.id,
                        'branch_code': line.branch_code,
                        'document_date': line.claim_date
                        # 'invoice_line_tax_ids': [(6, 0, line.tax_id.ids)],
                    })
                    pid = line.partner_id.id
                    if line.partner_id.id != partner_id and line.partner_id.ref in ('RBH','RBT'):
                        pid = partner_id

                    if partner_id == pid:
                        data_final.append(invoice_line_vals)
                        total_amount += line.balance_amount
                    # else:
                    #     unprocess += 1
                if len(data_final):
                    vendor_bills_id = self.env['account.invoice'].create({
                            'type': 'in_refund',
                            'date': date.today(),
                            'date_invoice': date.today(),
                            'date_due': date.today(),    #+ relativedelta(days=10),
                            'partner_id': partner_id,
                            'payment_term_id': claimList[0].payment_term_id.id,
                            'company_id': self.env.user.company_id.id,
                            'operating_unit_id': claimList[0].operating_unit_id.id,
                            'journal_id': journal_id.id,
                            'move_name': 'CLAIM',
                            # 'account_id': claims1.partner_id.property_account_receivable_id.id,
                            'account_id': claimList[0].company_id.ar_claim_account_id.id,
                            'invoice_line_ids': data_final,
                            'amount_total': total_amount,
                        })
                    action = self.env.ref('bsp_claim.action_invoice_in_claim'
                                              ).read()[0]
                    action['views'] = [(
                            self.env.ref('account.invoice_supplier_form').id, 'form')]
                    action['res_id'] = vendor_bills_id.id
                    return action
                else:
                    raise ValidationError( _('Sorry, no claim(s) can not be processed'))

            except AccessError:
                # TODO: if there is a nice way to hide the action from the
                # Action-menu if the user doesn't have the necessary rights,
                # that would be a better way of doing this
                raise UserError(_(
                    "Unfortunately it seems you do not have the necessary rights "
                    "for creating Bill/Invoices. Please contact your "
                    "administrator."))


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

    def _get_number(self, partner_id):
        dt = datetime.now()
        rp = self.env['res.partner'].search([('id', '=', partner_id)])
        principal_code = rp.ref
        name = 'Payment Voucher Principal ' + rp.ref
        prefix = 'PV' + principal_code + '/' + str(dt.year) + '/' + self.int_to_roman(dt.month)

        return self._get_sequence(name, prefix)

    @api.model
    def create(self, vals):
        if vals.get('move_name', 'CLAIM') == 'CLAIM':
            if vals['partner_id']:
                    vals['move_name'] = self._get_number(vals['partner_id'])
                    journal_id = self.env['account.journal'].search([('code', '=', 'CLM')], limit=1)
                    account_id = self.env.user.company_id.ar_claim_account_id.id
                    vals['journal_id'] = journal_id.id
                    vals['account_id'] = account_id
            else:
                raise UserError(_("Vendor name not VALID!"))
        # if vals('amount_total') < 0:
        #     raise UserError(_("Total Amount name not VALID!"))

        invoice = super(AccountInvoice, self).create(vals)
        # line_ids = vals.get('invoice_line_ids')
        # if line_ids is not None:
        # for line in invoice.invoice_line_ids:
        #         # if hasattr(line[2], 'claimcl_id'):
        #      if line.claimcl_id:
        #         # claim = self.env['bsp.claim.cl'].search([('id', '=',line.claimcl_id.id)], limit=1) #line[2]['claimcl_id'])], limit=1)
        #         # if claim:
        #         line.claimcl_id.sudo().write({'invoice_id': invoice.id,
        #                                 'state': 'paid',
        #                                 'paid_date': datetime.now()})
        return invoice

    @api.multi
    def write(self, vals):
        invoice = super(AccountInvoice, self).write(vals)
        self._claim_realloc_new()

        # line_ids = vals.get('invoice_line_ids')
        # for rec in self:
        # # if line_ids is not None:
        #     for line in rec.invoice_line_ids:
        #         if not line.claimcl_id:
        #             continue
        #         if rec.state == 'cancel':
        #            if line.claimcl_id.invoice_id:
        #               line.claimcl_id.invoice_id = False
        #               line.claimcl_id.sudo().write({'state': 'post'})
        #               # line.claimcl_id.state = 'post'
        #         else:
        #             line.claimcl_id.invoice_id = rec.id
        #             if rec.state == 'draft':
        #                if line.claimcl_id.invoice_id:
        #                   line.claimcl_id.sudo().write({'state': 'paid'})
        #                   # line.claimcl_id.state = 'paid'

        return invoice


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    def get_payment_amount(self):
        for line in self:
            line.payment_amount = 0
            if line.claimcl_id and line.claimcl_id.state not in ('paid', 'done'):
                continue

            query = f""" select sum(ml.credit) payment_amount
                          from account_move_line ml join account_payment p on p.id=ml.payment_id 
                          join account_invoice ai on ai."number" = p.communication 
                          join account_invoice_line ail on ai.id=ail.invoice_id 
                          join bsp_claim_cl cl on cl.id=ail.claimcl_id 
                          where ml.credit >0 and cl.id = {line.claimcl_id.id}
                          and p.pv_id in  {(str(tuple([pv.id for pv in line.claimcl_id.bmbk_ids]))).replace(',)', ')')}
                          """
            self._cr.execute(query)
            line.payment_amount = self._cr.fetchone()[0]



    def get_claim_domain(self):
        claim_domain=[]
        principle_ids = []
        principle_ids.append(self.invoice_id.partner_id.id)
        if self.invoice_id.partner_id.ref == 'RBT':
            p_id = self.env['res.partner'].search([('ref', '=', 'RBH')], limit=1)
            principle_ids.append(p_id.id)
        if self.invoice_id.partner_id.ref == 'RBH':
            p_id = self.env['res.partner'].search([('ref', '=', 'RBT')], limit=1)
            principle_ids.append(p_id.id)

        claim_domain = [('partner_id','in',principle_ids),('state','in',('paid','post'))]
        return claim_domain

    claimcl_id = fields.Many2one(
            comodel_name='bsp.claim.cl',
            string='Claim Principal',
            domain=get_claim_domain,
            help='Load the vendor refund based on selected claim. Several claim can be selected.'
    )

    claim_date = fields.Date("CC Date", related="claimcl_id.claim_date")
    claim_amount = fields.Float('Claim Amount', related="claimcl_id.claim_amount")
    balance_amount = fields.Float('Balance Amount', related="claimcl_id.balance_amount")
    tax_amount = fields.Float("PPN Amount", related="claimcl_id.tax_amount")
    pph1_amount = fields.Float("PPH Amount", related="claimcl_id.pph1_amount")
    claim_date = fields.Date("CC Date", related="claimcl_id.claim_date")
    period = fields.Char("Periode",related="claimcl_id.period")
    branch_code = fields.Char("Branch")
    remark = fields.Char("Program", related="claimcl_id.remark")
    customer_ref=fields.Char("Outlet Ref.", related="claimcl_id.customer_ref")
    branch_ref = fields.Char("Branch Ref.", related="claimcl_id.branch_ref")
    refdoc = fields.Char("KC/Ref", related="claimcl_id.refdoc")
    vistex = fields.Char("Principal Ref.", related="claimcl_id.vistex")
    payment_amount = fields.Float('Payment Amount')
    document_date = fields.Date("Doc. Date")
    # payment_amount = fields.Float('Payment Amount', compute='get_payment_amount')
    # bmbk_number = fields.Char("BM/BK Number",related="claimcl_id.lpayment_bankno")
    # payment_ids = fields.One2many('account.payment', related="claimcl_id.payment_ids")
    # bmbk_ids = fields.One2many('bsp.payment.voucher', string="BM/BK",related="claimcl_id.bmbk_ids")

    @api.model
    def create(self, vals):
        if vals['price_unit'] <= 0:
            raise UserError(_("Invalid Price Unit value"))
        if vals['branch_code']:
            if not self.env['operating.unit'].search_count([('code', '=', vals['branch_code'])]):
                raise UserError(_("Please,fill with valid Branch Code!"))
        else:
            raise UserError(_("Please,fill with valid Branch Code!"))

        invoiceline = super(AccountInvoiceLine, self).create(vals)
        if invoiceline.claimcl_id:
            invoiceline.claimcl_id.write({'invoice_id': invoiceline.invoice_id.id,
                                          'state': 'paid',
                                          'paid_date': datetime.now()})
        return  invoiceline


    @api.multi
    def write(self, vals):
        if 'price_unit' in vals and vals['price_unit'] <= 0:
            raise UserError(_("Invalid Price Unit value"))

        if 'branch_code' in vals and vals['branch_code']:
            if not self.env['operating.unit'].search_count([('code', '=', vals['branch_code'])]):
                raise UserError(_("Please,fill with valid Branch Code!"))
        # else:
        #     raise UserError(_("Please,fill with valid Branch Code!"))
        ret = super(AccountInvoiceLine, self).write(vals)
        return ret

    @api.onchange('branch_code')
    def onchange_branch_code(self):
        if self.product_id:
            if self.branch_code:
               self.branch_code = self.branch_code.upper()
            if not self.branch_code or not self.env['operating.unit'].search_count([('code', '=', self.branch_code)]):
                    raise UserError(_("Please,fill with valid Branch Code!"))

    @api.onchange('claimcl_id')
    def onchange_claimcl_id(self):
        for line in self:
            if not line.claimcl_id:
                continue
            line.price_unit = 0
            unique_list = []
            for sline in line.invoice_id.invoice_line_ids:
                if line.claimcl_id.id not in unique_list:
                    if sline.price_unit and sline.claimcl_id:
                            unique_list.append(sline.claimcl_id.id)
                else:
                    raise ValidationError(_('Duplicate/Not Valid Claim item or Delete the line first to do changes this item.'))

            for invline in line.claimcl_id.invoice_line_ids:
                if not isinstance(self.id, models.NewId):
                    if invline.invoice_id.state in ('draft', 'open'):
                        raise ValidationError(
                            _('Sorry, claim  %s can not be processed, because the claim already exists on draft/open invoice '
                              % invline.invoice_id.inv.number))


            query = "select balance_amount balance FROM bsp_claim_cl WHERE id =" + str(line.claimcl_id.id)
            self._cr.execute(query)
            cl = self._cr.fetchone()

            if cl[0] <= 0:
                raise ValidationError(_('No Balance to paid anymore, DONE plz.'))

            product_name = 'Claim to Principal: ' + line.claimcl_id.partner_id.ref
            product_id = self.env['product.product'].search([('name', '=', product_name)], limit=1)
            account_id = line.claimcl_id.company_id.claim_income_account_id.id
            if line.claimcl_id.claim_type in ('cncl'):
                account_id = line.claimcl_id.company_id.claim_prepaid_account_id.id

            if not product_id:
                product_id = self.env['product.product'].create({
                    'name': product_name,
                    'type': 'service',
                })
            line.product_id = product_id
            line.name = product_id.name + ': ' + line.claimcl_id.name
            line.quantity = 1
            line.account_id = account_id
            line.balance_amount = cl[0]
            line.price_unit = cl[0]
            line.branch_code = line.claimcl_id.branch_code
            line.document_date = line.claimcl_id.claim_date
            # line.claimcl_id.balance_amount
            line.invoice_line_tax_ids = False

    @api.onchange('price_unit')
    def onchange_price_unit(self):
        if self.product_id:
            if self.claimcl_id:
               if self.price_unit <= 0 or self.price_unit > self.balance_amount:
                  raise ValidationError(_('Claim Amount allocation not VALID !'))
            else:
                if self.price_unit <= 0:
                    raise ValidationError(_('Price Unit Amount not VALID !'))

    def _onchange_account_id(self):
        ret = super()._onchange_account_id()
        self.invoice_line_tax_ids = False
        return ret




    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        principle_ids=[]
        if self.product_id and (self.product_id.name)[:5].upper() != 'CLAIM':
           self.claimcl_id = False
           if self.product_id.name.upper() == 'INVOICE':
               self.account_id = self.company_id.inv_claim_account_id.id
               self.quantity = -1
           if self.product_id.name.upper() == 'PENAMBAHAN LAIN-LAIN':
               self.account_id = self.company_id.add_claim_account_id.id
               self.quantity = -1
           if self.product_id.name.upper() == 'PENGURANGAN LAIN-LAIN':
               self.quantity = 1
               self.account_id = self.company_id.sub_claim_account_id.id
           domain['claimcl_id'] = [('id','in',[])]
        else:
           domain['claimcl_id'] = self.get_claim_domain()
        return{"domain":domain}

    def _onchange_uom_id(self):
        ret = super()._onchange_uom_id()
        self.invoice_line_tax_ids = False
        return ret
    def unlink(self):
        for line in self:
            if line.invoice_id.state not in ('draft', 'cancel'):
                raise UserError(_('Cannot delete claim(s) which are already post or paid.'))
            else:
                if not line.claimcl_id.realization_amount or line.claimcl_id.realization_amount <= 0:
                    line.claimcl_id.sudo().write({'state': 'post'})
        return super(AccountInvoiceLine, self).unlink()




