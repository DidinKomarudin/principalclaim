from odoo import  api, fields, models, _
from datetime import timedelta, datetime
from odoo.exceptions import  UserError
from mysql.connector import Error



class ClaimReason(models.Model):
    _name = 'bsp.claim.reason'
    _description = 'Claim Reason Master'
    name = fields.Char("Reason Description", size=60, required=True)
    type = fields.Selection(
        [('rc', 'Reject/Cancel'),
         ('corr', 'Correction')],
                    required=True, string='Reason Type')

class ClaimMontlyLock(models.Model):
    _name = 'bsp.claim.lock'
    _description = 'Lock Claim base on send-date'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Reason Description", size=60, required=True)
    state = fields.Selection(
        [('inactive', 'IN-ACTIVE'),
         ('active', 'ACTIVE')],
        string='Closing Lock Status',
        track_visibility='onchange',
        required=True, default='inactive', copy=False)

    date_from = fields.Date("From")
    date_to = fields.Date("To")
    date_process = fields.Datetime("Process Date")

    def button_process(self):
        for ml in self:
            cls_locked = self.env['bsp.claim.cl'].search([('is_locked','!=',True),
                                                          ('send_date', '>=', ml.date_from),
                                                          ('send_date', '<=', ml.date_to)])
            rec = 0
            if cls_locked:
                rec = len(cls_locked)
                query = f""" UPDATE bsp_claim_cl SET is_locked = true WHERE is_locked is not true 
                        AND send_date BETWEEN '{(ml.date_from).strftime("%Y/%m/%d")}' and '{(ml.date_to).strftime("%Y/%m/%d")}' """
                print(query)
                self._cr.execute(query)

                ml.write({'date_process': datetime.now(),
                          'state': 'active'})
            return self.return_confirmation(True, 'Locked Claim on this ranges : ',rec)

    @api.multi
    def return_confirmation(self, isOK, desc, docs):
        return {
            'name': desc,
            'type': 'ir.actions.act_window',
            'res_model': 'claim.confirm.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_btn_ok': isOK, 'default_yes_no': docs}
        }

class PaymentVoucherBank(models.Model):
    _name = 'bsp.payment.voucher'
    _description = 'PV Bank Masuk dab Bank Keluar'

    @api.multi
    @api.depends('total_amount', 'alloc_amount')
    def _compute_remain_amount(self):
        for rec in self:
            rec.remain_amount = 0
            if rec.total_amount > rec.alloc_amount:
                rec.remain_amount = rec.total_amount - rec.alloc_amount



    def get_allocated_amount_all(self):
        for pv in self:
            query = f"""
            select sum(ail.price_subtotal)
            from account_payment ap join payment_invoice_line pil on ap.id=pil.payment_id  
            join account_invoice_line ail on pil.invoice_id =ail.invoice_id 
            where pv_id= {pv.id} and state not in ('cancelled') and allocated_amount>0 """
            self._cr.execute(query)
            return self._cr.fetchone()[0]

    def get_allocated_amount_send(self):
        for pv in self:
            query = f"""
            select sum(ail.price_subtotal) 
            from account_payment ap join payment_invoice_line pil on ap.id=pil.payment_id  
            join account_invoice_line ail on pil.invoice_id =ail.invoice_id 
            where pv_id= {pv.id} and state ='done' and allocated_amount>0"""
            self._cr.execute(query)
            return self._cr.fetchone()[0]


    def _get_invoice_line_ids(self):
        for pv in self:
            inv_lines = self.env['account.invoice.line']
            lines = self.env['payment.invoice.line']
            payments = self.env['account.payment'].sudo().search([('pv_id', '=', pv.id)])
            dAmount = 0
            inv_Amount = 0
            if payments:
                for payment in payments:
                    # print('Payment:'+ payment.name)
                    if payment.state not in ('cancelled'):
                        dAmount += (payment.amount - payment.balance)
                    payment_lines = self.env['payment.invoice.line'].sudo().search([('payment_id','=', payment.id),('allocated_amount','<>',0)])
                    lines |= payment_lines
                if lines:
                    for line in lines:
                        invoice_lines = self.env['account.invoice.line'].sudo().search([('invoice_id', '=', line.invoice_id.id)])
                        inv_lines |= invoice_lines

                for l in inv_lines:
                    inv_Amount += (l.price_subtotal)
                    # if l.claimcl_id:
                    #     inv_Amount += (l.payment_amount)
                    # else:
                    #     inv_Amount += (l.price_subtotal)
                pv.invoice_line_ids = inv_lines
                pv.invoice_line_count = len(inv_lines)
                pv.invoice_line_amount = inv_Amount
                # pv.alloc_amount = inv_Amount

    def calc_alloc_amount(self):
        tot_payment = sum(self.env['account.payment']
                              .search([('pv_id', '=', self.id),('state', 'not in', ('draft','cancelled'))])
                              .mapped('amount'))
        return tot_payment

    def _calc_send_alloc_amount(self):
        tot_payment = sum(self.env['account.payment']
                              .search([('pv_id', '=', self.id),('state', '=', 'done')])
                              .mapped('amount'))
        return tot_payment


    name = fields.Char("No. Referensi Bank Masuk", size=60, required=True)
    principal_code = fields.Char(string='Principal Code')
    total_amount = fields.Float("Total Amount")
    alloc_amount = fields.Float("Allocation Amount", default=0.0)
    # alloc_amount = fields.Float("Allocation Amount", compute='_get_invoice_line_ids', store=True)
    remain_amount = fields.Float("Remain Amount", compute='_compute_remain_amount', store=True)
    type = fields.Selection(
        [('pv', 'Payment Voucher'),
         ('bm', 'Bank Masuk'),
         ('bk', 'Bank Keluar')],
                    required=True, string='Voucher Type')
    state = fields.Selection(
        [('open', 'OPEN'),
         ('alloc', 'ALLOCATED'),
         ('post', 'POSTED'),
         ('close', 'CLOSE'),
         ('cancel', 'CANCEL')],
        string='Voucher Status', track_visibility='always', default='open')
    trx_date = fields.Date("Transantion Date")
    ref_document = fields.Char("Referensi Doc", size=60)
    ref_document_id = fields.Integer("Referensi DocID")
    ref_hodocument = fields.Char("Referensi BM/BK", size=60)
    ref_coa = fields.Char("Referensi COA", size=10)
    time_stamp = fields.Datetime("LastUpdate BIS")
    time_stamp_display = fields.Datetime("Last Update", compute='_get_time_stamp_display')
    invoice_line_ids = fields.Many2many('account.invoice.line', compute='_get_invoice_line_ids', copy=False)
    invoice_line_count = fields.Integer('Invoice Line Count', compute='_get_invoice_line_ids')
    invoice_line_amount = fields.Float('Invoice Line Info', compute='_get_invoice_line_ids')
    isreadonly = fields.Boolean("Is ReadOnly", compute='_set_readoly')
    legacy_state = fields.Char('Document State', size=10)
    # _sql_constraints = [
    #     ('name_coa_uniq', 'unique (name,ref_coa)', "Tag Voucher Number already exists !"),
    # ]

    @api.depends('time_stamp')
    def _get_time_stamp_display(self):
        for v in self:
            v.time_stamp_display = v.time_stamp + timedelta(hours=-7)

    # @api.multi
    # @api.depends('name', 'ref_coa')
    # def name_get(self):
    #     if self._context.get('show_coa'):
    #         res = [(ou.id, '%s%s' % ('['+ou.ref_coa+']' if ou.ref_coa != False else '', ou.name)) for ou in self]
    #     else:
    #         res = super(PaymentVoucherBank, self).name_get()
    #     return res
    def open_payment_line_matching_screen(self):
        action = self.env.ref('bsp_claim.action_account_payments_invoice_line').read()[0]
        # action.setdefault('context', {})
        action['context'] = {'active_model': ''}
        action['domain'] = [('id', 'in', self.invoice_line_ids.ids)]
        return action

    def button_generete_bk(self):
        for pv in self:
            pv_synch = self.env['bsp.payment.voucher.synch'].search([('name','=','_POSTEDPV1_')])
            if pv_synch:
                ret = pv_synch.generate_bk_by_posted_pv_bis(pv, True)
                return self.return_confirmation(True, 'Generate BK Confirmation',ret)

    def button_get_bk_hoccd(self):
        for pv in self:
            pv_synch = self.env['bsp.payment.voucher.synch'].search([('name','=','_POSTEDPV1_')])
            if pv_synch:
                ret = pv_synch.get_posted_bk_hoccd_loss(pv.ref_hodocument, pv.ref_document_id)
                return self.return_confirmation(True, 'Get BK Confirmation',ret)

    def button_regenerete_bk(self):
        for pv in self:
            pv_synch = self.env['bsp.payment.voucher.synch'].search([('name','=','_POSTEDPV1_')])
            if pv_synch:
                ret = pv_synch.generate_bk_by_posted_pv_bis(pv, False)
                return self.return_confirmation(True, 'Regenerate BK Confirmation',ret)

    @api.multi
    def return_confirmation(self, isOK, desc, docs):
        return {
            'name': desc,
            'type': 'ir.actions.act_window',
            'res_model': 'claim.confirm.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_btn_ok': isOK, 'default_yes_no': docs}
        }

    def _set_readoly(self):
        for v in self:
            v.isreadonly = not self.user_has_groups('base.group_system')

    def action_voucher_to_open(self):
        mess='Fail'
        for vc in self:
            if vc.state != 'open':
               mess = 'Current BK:' + vc.ref_hodocument + ' not found!'
               ret_bk = vc.delete_bk_hoccd()
               if ret_bk > 0:
                   mess = 'Current BK:'+vc.ref_hodocument+ 'Deleted !'

               ret_pv = vc.update_pv2pending()
               if ret_pv == 1:
                   mess += '\r\n Posted PV:' + vc.ref_hodocument + 'set to Pending !'

               vc.ref_document_id = False
               vc.ref_hodocument =  False
               vc.state = 'open'
               return self.return_confirmation(True, 'Confirmation', mess)

    def delete_bk_hoccd(self):
        global cursor, connection
        for vc in self:
            ret = 0
            if vc.type == 'pv' and vc.ref_document_id:
               try:
                    ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
                    cursor, connection = ou.connect_to_bis()
                    # query = f""" CALL usp_delete_banktoken_header({vc.ref_document_id})"""
                    args = [vc.ref_document_id]
                    cursor.callproc('usp_delete_banktoken_header', args)
                    records = cursor.stored_results()
                    rets = []
                    for r in records:
                        rets += r.fetchall()
                    ret = rets[0][0]
                    # connection.commmit()
                    cursor.close()
                    connection.close()
               except Error as e:
                   cursor.close()
                   connection.close()
                   raise UserError("Error while connecting to MySQL %s"%(e))
            return ret

    def update_pv2pending(self):
        global cursor, connection
        for vc in self:
            ret = 0
            if vc.type == 'pv' and vc.ref_document_id:
               try:
                    ou = self.env['operating.unit'].search([('code', '=', 'BISAP')], limit=1)
                    cursor, connection = ou.connect_to_bis()
                    query = f""" update pc_payment_voucher set status_pv='PENDING' where No_PV='{vc.name}'"""
                    cursor.execute(query)
                    # connection.commmit()
                    cursor.close()
                    connection.close()
                    ret = 1
               except Error as e:
                   cursor.close()
                   connection.close()
                   raise UserError("Error while connecting to MySQL", e)
            return ret

    def button_reset_bm(self):
        payments = self.env['account.payment'].search([('pv_id', '=', self.id), ('state', '=', 'done')])
        if not payments:
            raise UserError(_("Info: DONE Payment not fount!!"))
        try:
            ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
            cursor, connection = ou.connect_to_bis()
            idUMP = 0
            queryCOATitipan = "SELECT int_banktokendetailid idUMP FROM  banktoken_dtl WHERE int_banktokenid = " + str(
                self.ref_document_id) + " AND int_coaid IN (SELECT int_coaid FROM coa_ms WHERE txt_coacode = '" + self.ref_coa + "') limit 1;"
            cursor.execute(queryCOATitipan)
            record = cursor.fetchone()

            if record:
                idUMP = record["idUMP"]
            else:
                raise UserError(_("Error: COA UMP/TITIPAN not found!!"))

            queryDeleteAlloc = "DELETE FROM  banktoken_dtl WHERE int_banktokenid = " + str(self.ref_document_id) + \
                               " and txt_description like '%" + self.ref_coa + "'"
            cursor.execute(queryDeleteAlloc)

            for p in payments:
                for pvl in p.invoice_lines:
                    if pvl.allocated_amount:
                        for inv_line in pvl.invoice_id.invoice_line_ids:
                            coa = self.ref_coa
                            dAmount = inv_line.price_subtotal #payment_amount
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
                                    coding = inv_line.claimcl_id.claim_type_id.coding.upper()
                            byrArg = [
                                self.ref_document_id,
                                inv_line.claimcl_id.branch_code if inv_line.claimcl_id else inv_line.branch_code,
                                'BM',
                                inv_line.claimcl_id.name if inv_line.claimcl_id else inv_line.name,
                                inv_line.claimcl_id.vistex if inv_line.claimcl_id and inv_line.claimcl_id.vistex else '',
                                # referensi principal
                                inv_line.claimcl_id.service_inv if inv_line.claimcl_id and inv_line.claimcl_id.service_inv else '',
                                # faktur jasa
                                0,  # pph amount
                                dAmount,  # total without  tax amount
                                inv_line.claimcl_id.remark if inv_line.claimcl_id else rmk,
                                coding,
                                coa,
                                p.payment_date.strftime("%Y-%m-%d"),
                                inv_line.id
                            ]
                            cursor.callproc('usp_insert_banktoken_bayar', byrArg)


            queryCOATitipan = "update banktoken_dtl set curr_amount = round(" + str(
                self.remain_amount) + ",2)  where  int_banktokendetailid = " + str(idUMP)
            cursor.execute(queryCOATitipan)

            qsumbiaya = "select sum(curr_amount) totBiaya from banktoken_dtl where int_banktokenid=" +  str(self.ref_document_id)
            cursor.execute(qsumbiaya)
            totBiayaDict = cursor.fetchone()
            totBiaya = 0
            if totBiayaDict:
                totBiaya = totBiayaDict.get("totBiaya", 0)

            qupdatetotal = "Update banktoken_hdr set curr_amounttotal = " + str(totBiaya)+ " where int_banktokenid=" + \
                           str(self.ref_document_id)
            cursor.execute(qupdatetotal)
            connection.commit()
            return self.return_confirmation(True, 'Confirmation', "BM HOCCD allocation has been updated!")
        except Exception as e:
            raise e