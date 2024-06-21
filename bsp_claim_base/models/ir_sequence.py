from odoo import models, fields, api
from datetime import datetime
import pytz

class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    def get_sequence(self, name, code, pref, company_id=False, date_format='%(range_year)s%(month)s', padding=5, with_slash=True):
        if not company_id :
            company_id = self.env.user.company_id.id
        if with_slash:
            pref = '%s/%s/' % (pref, date_format)
        else:
            pref = '%s%s' % (pref, date_format)
        sequence_id = self.env['ir.sequence'].sudo().search([
            ('code', '=', code),
            ('prefix', '=', pref),
            ('company_id', '=', company_id),
        ], limit=1)
        if not sequence_id :
            sequence_id = self.env['ir.sequence'].sudo().search([
                ('code', '=', code),
                ('prefix', '=', pref),
                ('company_id', '=', False),
            ], limit=1)
            if sequence_id :
                sequence_id.sudo().write({'company_id':company_id})
        if not sequence_id :
            sequence_id = self.env['ir.sequence'].sudo().create({
                'name': name,
                'code': code,
                'implementation': 'no_gap',
                'prefix': pref,
                'padding': padding,
                'company_id': company_id,
            })
        return sequence_id.next_by_id()

    def get_sequence_suffix(self, name, code, suf, company_id=False, date_format='%(range_year)s%(month)s', padding=5, with_slash=True):
        if not company_id :
            company_id = self.env.user.company_id.id
        if with_slash:
            suf = '%s/%s/' % (suf, date_format)
        else:
            suf = '%s%s' % (suf, date_format)
        sequence_id = self.env['ir.sequence'].sudo().search([
            ('code', '=', code),
            ('suffix', '=', suf),
            ('company_id', '=', company_id),
        ], limit=1)
        if not sequence_id :
            sequence_id = self.env['ir.sequence'].sudo().search([
                ('code', '=', code),
                ('suffix', '=', suf),
                ('company_id', '=', False),
            ], limit=1)
            if sequence_id :
                sequence_id.sudo().write({'company_id':company_id})
        if not sequence_id :
            sequence_id = self.env['ir.sequence'].sudo().create({
                'name': name,
                'code': code,
                'implementation': 'no_gap',
                'suffix': suf,
                'padding': padding,
                'company_id': company_id,
            })
        return sequence_id.next_by_id()

    @api.multi
    def reset_sequence_monthly(self):
        current_date = pytz.UTC.localize(datetime.now()).astimezone(pytz.timezone(self.env.user.tz or 'UTC'))
        domain = [
            '|',
            ('prefix','like','%(month)s'),
            ('suffix','like','%(month)s'),
        ]
        if current_date.month == 1 :
            domain = ['|', '|', '|', '|', '|', '|'] + domain
            domain += [
                ('prefix','like','%(year)s'),
                ('suffix','like','%(year)s'),
                ('prefix','like','%(y)s'),
                ('suffix','like','%(y)s'),
                ('prefix','like','%(range_year)s'),
                ('suffix','like','%(range_year)s'),
            ]
        sequence_ids = self.env['ir.sequence'].sudo().search(domain)
        sequence_ids.write({
            'number_next_actual': 1,
            'use_date_range': False,
        })
