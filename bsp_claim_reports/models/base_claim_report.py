from odoo import api, fields, models

class BaseClaimReport(models.TransientModel):
    _name = 'base.claim.report'
    _description = 'base class for claim report'


    # Filters fields, used for data computation
    operating_unit_id = fields.Many2one(comodel_name='operating.unit')
    date_from = fields.Date()
    date_to = fields.Date()
    year_period = fields.Integer()
    partner_ids = fields.Many2many(comodel_name='res.partner')
    journal_ids = fields.Many2many(comodel_name='account.journal')
    report_name = fields.Char()
    coa_no = fields.Char()

    @api.onchange('operating_unit_id')
    def onchange_operating_unit_id(self):
        self.partner_ids = False

    @api.onchange('partner_ids')
    def onchange_partner_ids(self):
        if len(self.partner_ids) == 1 and self.partner_ids.name == "ALL":
            partners = self.env['bsp.creditnote.other'].search(
                [("operating_unit_id", "=", self.operating_unit_id.id)]).mapped("partner_id")
            self.partner_ids = partners

    def _getClassName(self):
        report = self
        if not report.report_name:
            report = self.browse(self._context.get('active_id'))
        class_name = str(self.__class__.__name__).replace(".", "_")
        if report.report_name in ('bm','bk'):
            ret_name = class_name.replace("bmbk", report.report_name)
        elif report.report_name in ('bm_alloc','bk_alloc'):
            ret_name = class_name.replace("bmbk", report.report_name)
        else:
            ret_name = class_name
        return ret_name

    @api.multi
    def print_report(self, report_type='qweb'):
        self.ensure_one()
        xlsx_action = "%s%s%s" % ('bsp_claim_reports.action_', self._getClassName(), "_xlsx")
        pdf_action = "%s%s%s" % ('bsp_claim_reports.action_', self._getClassName(), "_pdf")
        action = report_type == 'xlsx' and self.env.ref(xlsx_action) or \
                 self.env.ref(pdf_action)
        return action.report_action(self, config=False)

    def _get_html(self):
        result = {}
        rcontext = {}
        html_name = "%s%s%s" % ('bsp_claim_reports.', self._getClassName(), "_html")
        report = self.browse(self._context.get('active_id'))
        if report:
            rcontext['o'] = report
            result['html'] = self.env.ref(html_name).render(rcontext)
        return result

    @api.model
    def get_html(self, given_context=None):
        return self.with_context(given_context)._get_html()

class BaseClaimReportXlsx(models.AbstractModel):
    _name = 'base.claim.report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objects):
        self._define_formats(workbook)
        # for partner in objects.partner_ids:
        for ws_params in self._get_ws_params(workbook, data):
            ws_name = ws_params.get('ws_name')
            ws_name = self._check_ws_name(ws_name)
            ws = workbook.add_worksheet(ws_name)
            generate_ws_method = getattr(
                self, ws_params['generate_ws_method'])
            generate_ws_method(
                workbook, ws, ws_params, data, objects)

    def get_sum_formula(self, pos, i, row_pos):
        start = self._rowcol_to_cell(row_pos - i, pos)
        stop = self._rowcol_to_cell(row_pos - 1, pos)
        sum_formula = 'SUM(%s:%s)' % (start, stop)
        return sum_formula

    def get_cell(self,row_pos,pos):
        return self._rowcol_to_cell(row_pos, pos)