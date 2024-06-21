
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PaymentInvoiceLine(models.Model):
    _name = 'payment.invoice.line'
    _description = 'Payment Invoice Lines'

    def compute_current_residual(self):
        for line in self:
            if line.invoice_id:
                line.current_residual = line.invoice_id.residual


    # invoice_id = fields.Many2one('account.move', 'Invoice')
    invoice_id = fields.Many2one('account.invoice', 'Invoice')
    payment_id = fields.Many2one('account.payment', 'Related Payment')
    partner_id = fields.Many2one('res.partner', related='invoice_id.partner_id', string='Partner' )
    amount_total = fields.Monetary('Amount Total')
    residual = fields.Monetary('Amount Due')
    amount = fields.Monetary('Amount To Pay',
        help="Enter amount to pay for this invoice, supports partial payment")
    actual_amount = fields.Float(compute='compute_actual_amount',
                                 string='Actual amount paid',
                                 help="Actual amount paid in journal currency")
    # add by dk
    current_residual = fields.Float(compute='compute_current_residual',
                                 string='Current Residual',
                                 help="Current residual amount")
    allocated_amount = fields.Float(string='Allocation amount paid',
                                 help="Allocation amount paid in journal")
    # end add
    date_invoice = fields.Date(related='invoice_id.date_invoice', string='Invoice Date')
    currency_id = fields.Many2one(related='invoice_id.currency_id', string='Currency')
    company_id = fields.Many2one(related='payment_id.company_id', string='Company')


    # @api.depends('amount_total')
    def compute_allocation_amount(self):
        move_line_obj = self.env['account.move.line']
        reconcile_obj = self.env['account.partial.reconcile']
        for rec in self:
            rec.allocated_amount = 0
            debit_move_id = move_line_obj.search([('invoice_id', '=', rec.invoice_id.id),('debit','>',0)], limit=1)
            credit_move_id = move_line_obj.search([('payment_id', '=', rec.payment_id.id), ('credit', '>', 0)], limit=1)
            if debit_move_id and credit_move_id:
                reconcile_lines = reconcile_obj.search([('debit_move_id', '=', debit_move_id.id),('credit_move_id', '=', credit_move_id.id)])
                if reconcile_lines:
                    for recon in reconcile_lines:
                        rec.allocated_amount += recon.amount



    @api.depends('amount', 'payment_id.payment_date')
    def compute_actual_amount(self):
        for line in self:
            if line.amount > 0:
                line.actual_amount = line.currency_id._convert(
                    line.amount, line.payment_id.currency_id, line.company_id, line.payment_id.payment_date,
                    round=False)
            else:
                line.actual_amount = 0.0


    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.amount < 0:
                raise UserError(_('Amount to pay can not be less than 0! (Invoice code: %s)')
                    % line.invoice_id.name)
            if line.amount > line.residual:
                raise UserError(_('"Amount to pay" can not be greater than than "Amount '
                                  'Due" ! (Invoice code: %s)')
                                % line.invoice_id.name)

    @api.onchange('invoice_id')
    def onchange_invoice(self):
        if self.invoice_id:
            self.amount_total = self.invoice_id.amount_total
            self.residual = self.invoice_id.residual
        else:
            self.amount_total = 0.0
            self.residual = 0.0


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def _compute_is_finance_user(self):
        self.is_finance_user = self.user_has_groups('bsp_claim.group_hoccd_user') and not self.user_has_groups('bsp_claim.group_claim_branch_user')


    state = fields.Selection(track_visibility='onchange')
    invoice_lines = fields.One2many('payment.invoice.line', 'payment_id', 'Invoice Lines',
        help='Please select invoices for this partner for the payment')
    selected_inv_total = fields.Float(compute='compute_selected_invoice_total',
                                      string='Assigned Amount')
    balance = fields.Float(compute='_compute_balance', string='Balance')
    partner_id = fields.Many2one('res.partner', copy=False)
    amount = fields.Monetary(default=0.0, copy=False)
    is_finance_user = fields.Boolean(compute='_compute_is_finance_user', default=False)

    @api.multi
    @api.depends('amount', 'selected_inv_total')
    def _compute_balance(self):
        for payment in self:
            balance = payment.amount - payment.selected_inv_total
            if payment.company_id:
                payment.balance = payment.currency_id._convert(
                    balance, payment.currency_id, payment.company_id, payment.payment_date,
                    round=False)
                print('\n payment.balance', payment.balance)
            else:
                payment.balance = 0.0



    @api.constrains('journal_id')
    def _check_journalbyuser(self):
        for payment in self:
                if (self.user_has_groups('bsp_claim.group_hoccd_user') and not self.user_has_groups('bsp_claim.group_claim_branch_user')):
                    if payment.journal_id.code not in ('BNK1', 'CSH1'):
                      raise UserError(_('You may only use BANK and CASH payment journals'))

    @api.multi
    @api.depends('invoice_lines.allocated_amount', 'invoice_lines.actual_amount')
    def compute_selected_invoice_total(self):
        for payment in self:
            total = 0
            for line in payment.invoice_lines:
                total += line.actual_amount + line.allocated_amount
            payment.selected_inv_total = total

    def inverse_update(self):
        return True

    @api.constrains('amount', 'selected_inv_total', 'invoice_lines')
    def _check_invoice_amount(self):
        ''' Function to validate if user has selected more amount invoices than payment '''
        for payment in self:
            if payment.invoice_lines:
                if (payment.selected_inv_total - payment.amount) > 0.05:
                    raise UserError(_('You cannot select more value invoices than the payment amount'))

    def generate_all_allocation_amount(self):
        list_ids = self.search([])
        for line in list_ids:
            line.compute_allocation_amount()
    def generate_allocation_amount(self):
        for line in self.invoice_lines:
            line.compute_allocation_amount()

    @api.onchange('partner_id', 'payment_type')
    def onchange_partner_id(self):
        # print("\n self.reconciled_invoice_ids",self.reconciled_invoice_ids)
        # print("\n self",self)
        # Invoice = self.env['account.move']
        Invoice = self.env['account.invoice']
        PaymentLine = self.env['payment.invoice.line']
        context = self.env.context
        # print ('context....', context)
        # if context.get('active_model', '') == 'account.move':
        if context.get('active_model', '') == 'account.invoice' or \
            (self.user_has_groups('bsp_claim.group_hoccd_user') and not self.user_has_groups('bsp_claim.group_claim_branch_user')):
            self.invoice_lines = []
            # print ('here....')
            return
        # print ('Now also....')
        if self.partner_id: #and not self.invoice_ids: ?? tobe check!!!!

            partners_list = self.partner_id.child_ids.ids
            partners_list.append(self.partner_id.id)
            line_ids = []
            type = []
            if self.payment_type == 'outbound':
                type.append('in_invoice')
            elif self.payment_type == 'inbound':
                type.append('out_invoice')
                type.append('in_refund')
            invoices = Invoice.search(['|',
                                       '&',
                                       '&',
                                       '&',
                                       ('partner_id', 'in', partners_list),
                                       ('state', 'in', ('posted','open')),
                                       ('type', 'in', type),
                                       ('residual', '>', 0.0),
                                       ('id', 'in', self.reconciled_invoice_ids.ids)], order="date_invoice")
                                       # ('amount_residual', '>', 0.0)], order="invoice_date")
            for invoice in invoices:
                if self.pv_type == 'bk':
                    if invoice.pvbis_id:
                        self.AddPaymentInvoiceLine(PaymentLine, invoice)
                else:
                    if not invoice.pvbis_id:
                        self.AddPaymentInvoiceLine(PaymentLine, invoice)

        else:
            if self.invoice_lines:
                for line in self.invoice_lines:
                    line.unlink()
            self.invoice_lines = []

    def AddPaymentInvoiceLine(self, PaymentLine, invoice):
        if invoice.id in self.invoice_lines.mapped('invoice_id.id'):
            data = {
                'amount_total': invoice.amount_total,
                'residual': invoice.residual,  # invoice.amount_residual,
                'amount': 0.0,
                'date_invoice': invoice.date_invoice,  # invoice.invoice_date,
            }
            paymentLines = self.invoice_lines.filtered(lambda l: l.invoice_id.id == invoice.id)
            if paymentLines:
                paymentLines[:1].write(data)

        else:
            if self.id:
                data = {
                    'payment_id': self.id,
                    'invoice_id': invoice.id,
                    'amount_total': invoice.amount_total,
                    'residual': invoice.residual,  # invoice.amount_residual,
                    'amount': 0.0,
                    'date_invoice': invoice.date_invoice,  # invoice.invoice_date,
                }
                PaymentLine.create(data)

    @api.onchange('amount')
    def onchange_amount(self):
        ''' Function to reset/select invoices on the basis of invoice date '''
        if self.amount > 0 and self.invoice_lines:
            print ('here....2.')
            total_amount = self.amount
            for line in self.invoice_lines:
                if total_amount > 0:
                    conv_amount = self.currency_id._convert(
                        total_amount, line.currency_id, self.company_id, self.payment_date, round=False)
                    if line.residual < conv_amount:
                        line.amount = line.residual
                        if line.currency_id.id == self.currency_id.id:
                            total_amount -= line.residual
                        else:
                            spend_amount = line.currency_id._convert(
                                line.residual, self.currency_id, self.company_id, self.payment_date, round=False)
                            total_amount -= spend_amount
                    else:
                        line.amount = self.currency_id._convert(
                            total_amount, line.currency_id, self.company_id, self.payment_date, round=False)
                        total_amount = 0
                else:
                    line.amount = 0.0
        if (self.amount <= 0):
            for line in self.invoice_lines:
                line.amount = 0.0





    def post(self):
        """ Function reconcile selected invoices """
        res = super(AccountPayment, self).post()
        self.GetInvoiceLine()
        # self.validate()
        return res

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(invoice_lines=[], invoice_total=0.0)
        return super(AccountPayment, self).copy(default)



    def validate(self):
        reconcile_obj = self.env['account.partial.reconcile']
        move_line_obj = self.env['account.move.line']
        for rec in self:
            invoice_lines = rec.invoice_lines.filtered(lambda line: line.amount > 0.0)
            # add by dk 01-10-2020
            if invoice_lines:
                invoice_ids = invoice_lines.mapped('invoice_id')
            else:
                invoice_ids = rec.invoice_ids
            # invoice_ids._claim_realloc()
            # end add
            if not invoice_lines:
                return 1

            company_currency = rec.company_id.currency_id
            move_lines = move_line_obj.search([('payment_id', '=', rec.id)])
            # if rec.payment_type == 'inbound':
            #     inv_move_lines = move_line_obj.search([('invoice_id', 'in', invoice_ids),('credit','>',0.0)])
            #     move_lines.write=({'account_id':inv_move_lines[0].account_id.id})

            for line in invoice_lines:
                if rec.payment_type == 'outbound':
                    credit_lines = move_lines.filtered(lambda line: line.debit > 0.0)
                    if not credit_lines:
                        continue
                    for credit_line in credit_lines:
                        # invoice_debit_line = line.invoice_id.line_ids.filtered(
                        invoice_debit_line = line.invoice_id.move_id.line_ids.filtered(
                            lambda l: l.account_id.id == credit_line.account_id.id)
                        if not invoice_debit_line:
                            continue
                        for debit_line in invoice_debit_line:
                            if rec.currency_id == company_currency:
                                amount_currency = 0.0
                                currency_id = False
                                amount = line.actual_amount
                            else:
                                amount_currency = line.actual_amount
                                currency_id = rec.currency_id.id
                                amount = rec.currency_id._convert(
                                    line.actual_amount, company_currency, rec.company_id,
                                    rec.payment_date, round=False)
                            data = {
                                'debit_move_id': debit_line.id,
                                'credit_move_id': credit_line.id,
                                'amount': -amount,
                                'amount_currency': -amount_currency or 0.0,
                                'currency_id': currency_id or False,
                            }
                            reconcile_obj.create(data)
                if rec.payment_type == 'inbound':
                    credit_lines = move_lines.filtered(lambda line: line.credit > 0.0)
                    if not credit_lines:
                        continue
                    for credit_line in credit_lines:
                        # invoice_debit_line = line.invoice_id.line_ids.filtered(
                        invoice_debit_line = line.invoice_id.move_id.line_ids.filtered(
                            lambda l: l.account_id.id == credit_line.account_id.id)
                        # print("\n invoice_debit_line:",invoice_debit_line)
                        if not invoice_debit_line:
                            continue
                        for debit_line in invoice_debit_line:
                            if rec.currency_id == company_currency:
                                amount_currency = 0.0
                                currency_id = False
                                amount = line.actual_amount
                            else:
                                amount_currency = line.actual_amount
                                currency_id = rec.currency_id.id
                                amount = rec.currency_id._convert(
                                    line.actual_amount, company_currency, rec.company_id,
                                    rec.payment_date, round=False)
                            data = {
                                'debit_move_id': debit_line.id,
                                'credit_move_id': credit_line.id,
                                'amount': amount,
                                'amount_currency': amount_currency,
                                'currency_id': currency_id or False,
                            }
                            reconcile_obj.create(data)
                # rec.pv_id.write({'alloc_amount': rec.pv_id.alloc_amount + line.amount})
                if rec.pv_id.type == 'bm':
                    rec.pv_id.write({'alloc_amount': rec.pv_id.calc_alloc_amount()})
                    # rec.pv_id.write({'alloc_amount': rec.pv_id.get_allocated_amount_all()})
            rec.button_reallocation()


    @api.multi
    def button_validate(self):
        self.validate()

    def action_validate_invoice_payment(self):
        if self.pv_type in ('bm') and self.amount > self.pv_amount:
           raise UserError(_('Amount BM less than Payment amount'))
        result = super(AccountPayment,self).action_validate_invoice_payment()
        self.GetInvoiceLine()
        return result

    def GetInvoiceLine(self):
        invoice = self.env['account.invoice'].search([('number','=',self.communication)])
        if invoice:

            PaymentLine = self.env['payment.invoice.line']
            line_ids = []
            data = {
                        'invoice_id': invoice.id,
                        'amount_total': invoice.amount_total,
                        'residual': invoice.residual, #invoice.amount_residual,
                        'amount': 0, #self.amount,
                        'date_invoice': invoice.date_invoice,  # invoice.invoice_date,
                    }
            line = PaymentLine.create(data)
            # line.compute_allocation_amount()
            line_ids.append(line.id)
            self.invoice_lines = [(6, 0, line_ids)]
            if self.pv_id:
                # 'alloc_amount': self.pv_id.alloc_amount + invoice.amount_total,
                if self.pv_id.type == 'bm':
                    self.pv_id.write({
                        'alloc_amount': self.pv_id.calc_alloc_amount(), #self.pv_id.get_allocated_amount_all(),   #
                        'state': 'alloc'
                    })
            self.generate_allocation_amount()
            if self.pv_type != 'bm':
                self.write({'state':'done'})


    @api.multi
    def button_reallocation(self):
        for payment in self:
            # payment.selected_inv_total = payment.amount - payment.amount_residual
            for inv in payment.invoice_lines:
                # if inv.allocated_amount and inv.allocated_amount != inv.amount:
                inv.residual = inv.current_residual
                inv.amount = inv.residual
                inv.compute_allocation_amount()
                # if not inv.allocated_amount:
                #     inv.unlink()
            self.onchange_partner_id()
                    # inv.amount = inv.allocated_amount
                    # inv.residual = inv.current_residual
