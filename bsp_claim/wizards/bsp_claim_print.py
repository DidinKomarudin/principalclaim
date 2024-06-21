import base64
import datetime
import os
import platform
from num2words import num2words
from datetime import datetime
from docxtpl import DocxTemplate
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class BspClaimPrintOut(models.TransientModel):
    _name = 'bsp.claim.print.docx'
    _description = 'Claim Print'

    bsp_claim_data = fields.Char('Name', size=256)
    file_name = fields.Binary('Docx Report', readonly=True)


class WizzardBspClaim(models.TransientModel):
    _name = 'wizard.bsp.claim.print'
    _description = 'BSP Claim print wizzard'

    claim = fields.Char(store=False)
    is_branch = fields.Boolean(store=False)
    @api.multi
    def _get_selection_value(self, model, field, value):
        selection = self.pool.get(model)._columns.get(field).selection
        val = ''
        for v in selection:
            if v[0] == value:
                val = v[1]
            break
        return val

    @api.multi
    def get_data(self):
        self.ensure_one()
        claims = self.env['bsp.claim.cl'].browse(self._context.get('active_ids', list()))
        # AmountText = self.env['terbilang']
        data = None
        for rec in claims:

            if rec.state not in ('draft'):
                continue
            rec.write({'print_count': rec.print_count + 1})
            self.claim = rec.ref
            self.is_branch = rec.is_branch
            doc_date = datetime.now()
            bank_name = ''
            bank_account = ''
            bank_account_owner = ''
            if rec.bank_id:
                bank_name = rec.bank_id.bank_id.name + ', ' + rec.bank_id.bank_id.street + ', ' + rec.bank_id.bank_id.city
                bank_account = 'No. Rekening ' + rec.bank_id.acc_number
                bank_account_owner ='Atas Nama ' + rec.bank_id.company_id.name

            isdisplay=True
            if rec.state in ('draft'):
                isdisplay = False
            isbarang = False
            if rec.claim_type in ('barang'):
                isbarang = True

            data = {
                'name': str(rec.name),
                'branch_city': rec.operating_unit_id.partner_id.city if rec.operating_unit_id.partner_id.city else '',
                'principal': str(rec.ref) + '('+rec.partner_id.name+')',
                'company_name': str(rec.partner_id.name),
                'address': str(rec.partner_id.street) if rec.partner_id.street else '',
                'city': str(rec.partner_id.city) if rec.partner_id.city else '' + ' ' + str(rec.partner_id.zip) if rec.partner_id.zip else '',
                'country': str(rec.partner_id.country_id.name) if rec.partner_id.country_id else '',
                'contact_person': str(rec.contact_person) if rec.contact_person else '',
                'cp_tittle': str(rec.cp_tittle) if rec.cp_tittle else '',
                'claim_letter': str(rec.claim_letter) if rec.claim_letter else '',
                'program': str(rec.remark) if rec.remark else '',
                'lampiran': str(rec.lampiran) if rec.lampiran else '',
                'customer_ref': str(rec.customer_ref) if rec.customer_ref else '',
                'vistex': str(rec.vistex) if rec.vistex else '',
                'refdoc': str(rec.refdoc) if rec.refdoc else '',
                'period': str(rec.period),
                'branch': str(rec.operating_unit_id.code),
                'ap_manager': '',
                'brand_manager': str(rec.bm_name) if rec.bm_name else '',
                'date_doc': doc_date.strftime('%d %B %Y'),
                'bank_name': bank_name,
                'bank_account': bank_account,
                'bank_account_owner': bank_account_owner,
                # 'date_send': datetime.strptime(rec.send_date, DATE_FORMAT).strftime('%d %b %Y'),
                'claim_amount': str("{0:12,.2f}".format(rec.claim_amount)),
                'ppn_amount': str("{0:12,.2f}".format(rec.tax_amount)),
                'pph_amount': str("{0:12,.2f}".format(rec.pph1_amount )),
                'net_amount': str("{0:12,.2f}".format(rec.net_amount)),
                'terbilang': num2words(rec.net_amount, lang='id').upper(),
                'top': str(rec.payment_term_id.name) if rec.payment_term_id else '30 Hari',
                'display_state': isdisplay,
                'is_barang': isbarang,
                'state': str(rec.state.upper()),

            }
        return data

    @api.multi
    def print_report(self):
        self.ensure_one()
        context = self.get_data()
        if context is None:
            raise UserError(_('Unfortunately, there is no document that can be printed'))

        datadir = os.path.dirname(__file__)
        doc_date = datetime.now()
        doc_name = 'claim_template.docx'

        if self.is_branch:
            doc_name = 'claim_branch_template.docx'

        if platform.system() == 'Linux':
            f = os.path.join(datadir, 'templates/' + doc_name)
        else:
            f = os.path.join(datadir, 'templates\\' + doc_name)

        template = DocxTemplate(f)
        template.render(context)
        if platform.system() == 'Linux':
            filename = ('/tmp/BSPClaim-'+ self.claim + '-' + doc_date.strftime('%d%B%Y') + '.docx')
        else:
            filename = ('BSPClaim-' + self.claim + '-' + doc_date.strftime('%d%B%Y') + '.docx')
        template.save(filename)
        fp = open(filename, 'rb')
        file_data = fp.read()
        out = base64.encodestring(file_data)

        attach_vals = {
            'bsp_claim_data': filename,
            'file_name': out,
        }

        act_id = self.env['bsp.claim.print.docx'].create(attach_vals)
        fp.close()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bsp.claim.print.docx',
            'res_id': act_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'context': self.env.context,
            'target': 'new',
        }
