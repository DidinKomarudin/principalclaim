from odoo import fields, models, api

class OperatingUnit(models.Model):
    _inherit = 'operating.unit'

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        if self._context.get('show_codename'):
            res = [(ou.id, '[%s] %s' % (ou.code, ou.name)) for ou in self]
        elif self._context.get('show_justcode'):
            res = [(ou.id, '%s' % (ou.code)) for ou in self]
        else:
            res = super(OperatingUnit, self).name_get()
        return res

class Partner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    @api.depends('name', 'ref')
    def name_get(self):
        if self._context.get('show_codename'):
            res = [(ou.id, '[%s] %s' % (ou.ref, ou.name)) for ou in self]
        elif self._context.get('show_justcode'):
            res = [(ou.id, '%s' % (ou.ref)) for ou in self]
        else:
            res = super(Partner, self).name_get()
        return res

class BankAccount(models.Model):
    _inherit = 'res.partner.bank'

    @api.multi
    @api.depends('bank_id.name', 'acc_number')
    def name_get(self):
        if self._context.get('show_bankname'):
            res = [(ou.id, '[%s] %s' % (ou.acc_number, ou.bank_id.name)) for ou in self]
        else:
            res = super(BankAccount, self).name_get()
        return res

class PaymentVoucher(models.Model):
    _inherit = 'bsp.payment.voucher'
    @api.multi
    @api.depends('name', 'ref_coa', 'trx_date')
    def name_get(self):
        contex = self._context
        if self._context.get('show_refcoa'):
            res = [(ou.id, '%s%s[%s]' % (ou.name, '[' + ou.ref_coa + ']' if ou.ref_coa != False else '', ou.trx_date.strftime("%d-%m-%Y"))) for ou in self]
        # elif self._context.get('show_date'):
        #     res = [(ou.id, '%s [%s]' % (ou.name, ou.trx_date.strftime("%d-%m-%Y"))) for ou in self]
        else:
            res = super(PaymentVoucher, self).name_get()
        return res



