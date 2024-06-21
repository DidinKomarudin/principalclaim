# -*- coding: utf-8 -*-

from odoo import _, models, fields, api


class SelectCL(models.TransientModel):
    _name = 'select.creditnote'

    cn_ids = fields.Many2many('bsp.creditnote.other',
                                   'bsp_creditnote_other_rel',
                                   'claimcl_id', 'cn_id',
                                   string='Claim List', cascade=True)

    @api.onchange('cn_ids')
    def _onchange_partner_type(self):
        context = self._context
        lst = []
        listPrinciple=[]
        tpc = context.get('cn_type')
        if tpc[0] == 'mix':
           types = self.env['bsp.claim.type'].search([('code', '<>', 'mix')])
           for tp in types:
                lst.append(tp.code)
        else:
            lst.append(tpc[0])

        listPrinciple.append(context.get('partner_id'))
        if context.get('partner_id') == 'RBT':
            listPrinciple.append('RBH')
        if context.get('partner_id') == 'RBH':
            listPrinciple.append('RBT')

        # request by MOM 26-01-2024 from AP and Fin dep : Pa.Hervin dan Pa Brampi
        if tpc[0] in ('mix', 'noncl'):
        # if tpc[0] == 'noncl':
            return {'domain': {'cn_ids': [('state', 'in', context.get('state')),
                                          ('cn_type', 'in', lst),
                                          ('is_select', '=', True)]}}
        else:
            return {'domain': {'cn_ids': [('principal_code', 'in', listPrinciple),
                                      ('state', 'in', context.get('state')),
                                      ('cn_type', 'in', lst),
                                      ('is_select', '=', True)]}}

    @api.multi
    def select_creditnote(self):
        claimcl_id = self.env['bsp.claim.cl'].browse(self._context.get('active_id', False))
        adopt = False
        for cn_id in self.cn_ids:
            line_id = self.env['bsp.claim.cl.line'].search([('cn_id', '=', cn_id.id)], limit=1)
            if line_id:
                # if cn_id.cn_type == 'discount' and cn_id.cn_total - cn_id.total_claimed_amount > 0:
                if cn_id.is_can_partial and cn_id.cn_total - cn_id.total_claimed_amount > 0:
                    adopt = True
            else:
                adopt = True
            principles=[]
            principles.append(claimcl_id.partner_id.ref)
            if claimcl_id.partner_id.ref == 'RBT':
                principles.append('RBH')
            if claimcl_id.partner_id.ref == 'RBH':
                principles.append('RBT')
            if adopt:
                # request by MOM 26-01-2024 from AP and Fin dep : Pa.Hervin dan Pa Brampi
                if claimcl_id.claim_type in ('mix','noncl') or cn_id.principal_code in principles:
                # if claimcl_id.claim_type == 'noncl'  or cn_id.principal_code in principles:
                    self.env['bsp.claim.cl.line'].create({
                        'cn_id': cn_id.id,
                        'claimcl_id': claimcl_id.id,
                        'description': '',
                        'cn_total': cn_id.cn_total,
                        'total_claimed_amount': cn_id.total_claimed_amount,
                        'actual_claim_amount': cn_id.cn_total - cn_id.total_claimed_amount,
                        'ump_amount': cn_id.ump_amount,
                        'bsp_share': cn_id.bsp_share,
                        'principal_share': cn_id.principal_share,
                        'exim_status': 'CC'
                    })
        claimcl_id._update_link_data(claimcl_id.id)