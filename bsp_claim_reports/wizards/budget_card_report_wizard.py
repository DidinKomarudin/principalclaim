# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval
from odoo.tools import pycompat


class financeclaimReportWizard(models.TransientModel):
    _name = 'finance.claim.report.wizard'
    _description = 'Financial Claim Report Wizard'

    def _get_domain(self):
        return [('id', 'in', self.env.user.operating_unit_ids.ids)]

    def _get_journaldomain(self):
        return [('type', 'in', ['sale', 'purchase'])]

    operating_unit_id = fields.Many2one('operating.unit', 'Branch',
                                        track_visibility='onchange',
                                        default=lambda self: self.env.user.default_operating_unit_id.id,
                                        domain=_get_domain)
    report_name = fields.Selection(
        [('arcard','AR Claim Card'),
         ('aging','Claim vs Aging'),
         ('rcl', 'Recap CNCL'),
         ('journal', 'Journal List'),
         ('monitor', 'Claim Monitoring Report'),
         ('bm', 'Claim-BM Recapituation Report'),
         ('bk', 'Claim-BK Recapituation Report'),
         ('bm_alloc', 'BM Allocation Report'),
         ('bk_alloc', 'BK Allocation Report'),
         # ('claim_balance', 'Claim AR Balance Report'),
         ],

        string='Report Name',
        default='arcard')

    date_from = fields.Date(
        string='Start Date',
    )
    date_to = fields.Date(
        string='End Date',
    )
    year_period = fields.Integer(string='Year Period', default=datetime.now().date().year)
    # journal_ids = fields.Many2many('account.journal', string='Journals',
    #                                default=lambda self: self.env['account.journal'].search(
    #                                 [('type', 'in', ['sale', 'purchase'])]))
    journal_ids = fields.Many2many('account.journal',
                                   string='Journals',
                                   default=lambda self: self.env['account.journal'].search([('code', 'in', ['CLM', 'BNK1','OFS','PYD','CSH1'])]))


    # partner_id = fields.Many2one('res.partner', 'Principal', domain="[('supplier','=',True)]")
    partner_ids = fields.Many2many(
        comodel_name='res.partner',
        string='Principal',
        domain="[('supplier','=',True)]",
        # required=True,
    )

    coa_no = fields.Char("COA Number", size=5)



    @api.onchange('partner_ids')
    def onchange_partner_ids(self):
        domain = []
        if self.operating_unit_id:
            domain = [('operating_unit_id', '=', self.operating_unit_id.id)]
        if len(self.partner_ids) == 1 and self.partner_ids.name == "ALL":
            # partners = self.env['res.partner'].search([('supplier', '=', True),('ref','not in',('ALL',''))])
            partners = self.env['bsp.creditnote.other'].search(domain).mapped("partner_id")
            self.partner_ids = partners

    @api.onchange('operating_unit_id')
    def onchange_operating_unit(self):
        if self.partner_ids:
            self.partner_ids = False

    @api.onchange('report_name')
    def onchange_report_name(self):
        if self.partner_ids:
            self.partner_ids = False

    @api.multi
    def button_export_html(self):
        self.ensure_one()
        action_name = 'bsp_claim_reports.action_budget_card_report_html'
        if self.report_name == 'aging':
            action_name = 'bsp_claim_reports.action_aging_claim_report_html'
        elif self.report_name == 'rcl':
            action_name = 'bsp_claim_reports.action_cl_recap_report_html'
        elif self.report_name == 'journal':
            action_name = 'bsp_claim_reports.action_claim_journal_report_html'
        elif self.report_name == 'monitor':
            action_name = 'bsp_claim_reports.action_claim_monitoring_report_html'
        elif self.report_name == 'bm':
            action_name = 'bsp_claim_reports.action_claim_bm_report_html'
        elif self.report_name == 'bk':
            action_name = 'bsp_claim_reports.action_claim_bk_report_html'
        elif self.report_name == 'bm_alloc':
            action_name = 'bsp_claim_reports.action_bm_allocation_report_html'
        elif self.report_name == 'bk_alloc':
            action_name = 'bsp_claim_reports.action_bk_allocation_report_html'
        elif self.report_name == 'claim_balance':
            action_name = 'bsp_claim_reports.action_claim_balance_report_html'
        action = self.env.ref(action_name)
        vals = action.read()[0]
        context = vals.get('context', {})
        if isinstance(context, pycompat.string_types):
            context = safe_eval(context)
        model_name = 'budget.card.report'
        if self.report_name == 'aging':
            model_name = 'aging.claim.report'
        elif self.report_name == 'rcl':
            model_name = 'cl.recap.report'
        elif self.report_name == 'journal':
            model_name = 'claim.journal.report'
        elif self.report_name == 'monitor':
            model_name = 'claim.monitoring.report'
        elif self.report_name == 'bm':
            model_name = 'claim.bmbk.report'
        elif self.report_name == 'bk':
            model_name = 'claim.bmbk.report'
        elif self.report_name == 'bm_alloc':
            model_name = 'bmbk.allocation.report'
        elif self.report_name == 'bk_alloc':
            model_name = 'bmbk.allocation.report'
        elif self.report_name == 'claim_balance':
            model_name = 'claim.balance.report'
        context['pv_type'] = self.report_name
        model = self.env[model_name]
        report = model.create(self._prepare_the_report())
        context['active_id'] = report.id
        context['active_ids'] = report.ids
        vals['context'] = context
        return vals

    @api.multi
    def button_export_pdf(self):
        self.ensure_one()
        report_type = 'qweb-pdf'
        return self._export(report_type)

    @api.multi
    def button_export_xlsx(self):
        self.ensure_one()
        report_type = 'xlsx'
        return self._export(report_type)

    def _prepare_the_report(self):
        self.ensure_one()
        return {
            'report_name': self.report_name,
            'operating_unit_id': self.operating_unit_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to or fields.Date.context_today(self),
            'year_period': self.year_period,
            'partner_ids': [(6, 0, self.partner_ids.ids)],
            'journal_ids': [(6, 0, self.journal_ids.ids)],
            'coa_no': self.coa_no,
            # 'partner_id': self.location_id.id,
        }

    def _export(self, report_type):

        model_name = 'budget.card.report'
        if self.report_name == 'aging':
            model_name = 'aging.claim.report'
        elif self.report_name == 'rcl':
            model_name = 'cl.recap.report'
        elif self.report_name == 'journal':
            model_name = 'claim.journal.report'
        elif self.report_name == 'monitor':
            model_name = 'claim.monitoring.report'
        elif self.report_name == 'bm':
            model_name = 'claim.bmbk.report'
        elif self.report_name == 'bk':
            model_name = 'claim.bmbk.report'
        elif self.report_name == 'bm_alloc':
            model_name = 'bmbk.allocation.report'
        elif self.report_name == 'bk_alloc':
            model_name = 'bmbk.allocation.report'
        elif self.report_name == 'claim_balance':
            model_name = 'claim.balance.report'

        model = self.env[model_name]

        report = model.create(self._prepare_the_report())
        return report.print_report(report_type)
