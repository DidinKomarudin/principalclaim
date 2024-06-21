from odoo import tools
from odoo import api, fields, models



class InvoicePaymentReport(models.Model):
    _name = "payment.analysis"
    _description = "Payment Analysis Report"
    _auto = False
    _rec_name = 'invoice_id'
    _order = 'invoice_id desc,payment_id desc'

    invoice_id = fields.Many2one('account.invoice', 'Billing Number', readonly=True)
    date_invoice = fields.Date("Invoice Date", readonly=True)
    move_id = fields.Many2one('account.move', 'Move', readonly=True)
    # partner_id = fields.Many2one('res.partner', 'Principal', readonly=True)
    payment_id = fields.Many2one('account.payment', 'Payment', readonly=True)
    # payment_id = fields.Char( 'Payment', size=30, readonly=True)
    payment_date = fields.Date("Payment Date", readonly=True)
    invoice_amount = fields.Float("Invoice Amount", readonly=True)
    bank_amount = fields.Float("Bank Amount", readonly=True)
    cash_amount = fields.Float("Cash Amount", readonly=True)
    offset_amount = fields.Float("Offset Amount", readonly=True)
    bd_amount = fields.Float("Bill Deduction Amount", readonly=True)
    balance_amount = fields.Float('Balance Amount', readonly=True)
    # inv_id = fields.Integer(related="invoice_id.id" , readonly=True)
    # pay_id = fields.Integer(related="payment_id.id", readonly=True)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """CREATE or REPLACE VIEW %s as (
            SELECT
                -- row_number() OVER (PARTITION BY true) 
                pay.id  AS id,                  
                refund.id AS invoice_id,                
                refund.date_invoice As date_invoice,
                refund.move_id AS move_id,
                refund.amount_total as invoice_amount,
				-- refund.residual as balance_amount,
				refund.amount_total - (select sum(p.amount) from  account_invoice_payment_rel r
			        join account_payment p on r.payment_id = p.id
			    where r.invoice_id = refund.id and  p.id <= pay.id) as balance_amount,
                -- pay.move_name as payment_id,     
                pay.id as payment_id,
                pay.payment_date as payment_date,           
                case when journal.code = 'BNK1' then pay.amount else 0 end as bank_amount,
                case when journal.code = 'CSH1' then pay.amount else 0 end as cash_amount,
                case when journal.code = 'OFS' then pay.amount else 0 end as offset_amount,
                case when journal.code = 'PYD' then pay.amount else 0 end as bd_amount                             
            FROM account_invoice refund 
            left join account_invoice_payment_rel rel on rel.invoice_id = refund.id
			left join account_payment pay on rel.payment_id = pay.id
			left join account_journal journal on pay.journal_id = journal.id
			order by refund.id, pay.id
            )"""
            % (self._table)
        )
