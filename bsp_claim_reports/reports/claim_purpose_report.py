import base64
from datetime import datetime

from dbfpy3 import dbf
from odoo import api, fields, models



class BudgetReport(models.TransientModel):
    _name = 'budget.card.report'
    _inherit = 'base.claim.report'
    _description = 'AR Claim Card Report'

    # Data fields, used to browse report data
    results = fields.Many2many(
        comodel_name='budget.card.view',
        compute='_compute_results',
        help='Use compute fields, so there is nothing store in database',
    )

    @api.multi
    def _compute_results(self):
        self.ensure_one()
        date_from = self.date_from or '0001-01-01'
        date_to = self.date_to or fields.Date.context_today(self)
        company = self.env.user.company_id
        # account_id = self.partner_ids[0].property_account_receivable_id.id
        account_id = company.ar_claim_account_id.id
        # params = [date_from, self.partner_ids.ids, 'posted', account_id, 'posted', company.id, company.id,  date_to]
        query = """
            	SELECT 	"account_move_line".date, 
            	"account_move_line".partner_id,
			    "account_move_line".journal_id,
			    acc.id as account_id, 
			    "account_move_line".id as credit_move_id, 
			    "account_move_line".ref as reference, 
			    m.name as move_name, 
			    case when "account_move_line".date < %s then True else False end as is_initial,
			    "account_move_line".credit as ar_in,
			    "account_move_line".debit as ar_out,
			    (select sum(amount) from account_partial_reconcile where  credit_move_id="account_move_line".id) alloc_amount		    
                FROM "account_move" as "account_move_line__move_id","account_move_line"
                    left join res_partner p on (p.id= "account_move_line".partner_id)
                    LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
                    LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
                    LEFT JOIN res_currency c ON ("account_move_line".currency_id=c.id)
                    LEFT JOIN account_move m ON (m.id="account_move_line".move_id)
                WHERE "account_move_line".partner_id  in %s AND
                    m.state = %s AND 
                    "account_move_line".account_id = %s AND 
                    "account_move_line"."move_id"="account_move_line__move_id"."id" AND 
                    "account_move_line__move_id"."state" = %s AND  
                    "account_move_line"."company_id" = %s AND 
                    ("account_move_line"."company_id" IS NULL   OR  "account_move_line"."company_id" = %s) AND 
                    "account_move_line".full_reconcile_id IS NULL and
					"account_move_line".date <= %s
					order by "account_move_line".partner_id, "account_move_line".date,"account_move_line".id           	
					"""

        self._cr.execute(query, (date_from, tuple(self.partner_ids.ids),
                                 'posted', account_id, 'posted', company.id, company.id,  date_to))
        budget_card_results = self._cr.dictfetchall()
        report_line = self.env['budget.card.view']
        self.results = [report_line.new(line).id for line in budget_card_results]

    @api.multi
    def _get_initial(self, partner_line):
        partner_input_qty = sum(partner_line.mapped('ar_in'))
        partner_output_qty = sum(partner_line.mapped('ar_out'))
        return partner_input_qty - partner_output_qty

    def _get_initial_ump(self, partner_line):
        partner_ump_qty = sum(partner_line.mapped('ump_amount'))
        return partner_ump_qty

class BudgetCardView(models.TransientModel):
    _name = 'budget.card.view'
    _description = 'Budget Card View'
    _order = 'date'

    @api.depends('alloc_amount')
    def _compute_alloc(self):
        for rec in self:
            rec.alloc_rmk = ''
            if rec.alloc_amount > 0:
                reconcile_obj = self.env['account.partial.reconcile']
                reconcile_lines = reconcile_obj.search([('credit_move_id', '=', rec.credit_move_id)])
                if reconcile_lines:
                    list_ids = []
                    for line in reconcile_lines:
                        list_ids.append([0, 0, {
                                "budget_card_id": rec.id,
                                "alloc_number": str(line.debit_move_id.invoice_id.number),
                                "alloc_value": line.amount}])
                    rec.alloc_ids = list_ids
                        # self.env['budget.card.view.alloc'].create(
                        #     {
                        #         "budget_card_id": rec.id,
                        #         "alloc_number": str(line.debit_move_id.invoice_id.number),
                        #         "alloc_value": line.amount})


                        # if rec.alloc_rmk == '':
                        #     rec.alloc_rmk = str(line.debit_move_id.invoice_id.number) + ':' + str(line.amount)
                        # else:
                        #     rec.alloc_rmk += ', ' + str(line.debit_move_id.invoice_id.number) + ':' + str(line.amount)

    @api.depends('alloc_amount')
    def _compute_ump(self):
        for rec in self:
            rec.ump_amount = 0
            if rec.alloc_amount > 0:
                rec.ump_amount = rec.ar_in -  rec.alloc_amount

    date = fields.Date()
    partner_id = fields.Many2one(comodel_name='res.partner')
    journal_id = fields.Many2one(comodel_name='account.journal')
    account_id = fields.Many2one(comodel_name='account.journal')
    credit_move_id = fields.Integer()
    reference = fields.Char()
    move_name = fields.Char()

    is_initial = fields.Boolean()
    ar_in = fields.Float()
    ar_out = fields.Float()
    alloc_amount = fields.Float()
    ump_amount = fields.Float(compute='_compute_ump')
    alloc_rmk = fields.Char()
    alloc_ids = fields.One2many(compute='_compute_alloc', comodel_name='budget.card.view.alloc')
class BudgetCardViewAlloc(models.TransientModel):
    _name = 'budget.card.view.alloc'
    _description = 'Budget Card Allocation'

    budget_card_id = fields.Many2one("budget.card.view")
    alloc_number = fields.Char(size=30)
    alloc_value = fields.Float()

class AgingClaimView(models.TransientModel):
    _name = 'aging.claim.view'
    _description = 'Aging Claim View'
    _order = 'date'

    partner_id = fields.Many2one(comodel_name='res.partner')
    begin_balance = fields.Float()
    debit = fields.Float()
    credit = fields.Float()
    end_balance = fields.Float()
    total_amount = fields.Float()
    morethan90 = fields.Float()
    bt61and90 = fields.Float()
    bt31and60 = fields.Float()
    bt00and30 = fields.Float()
class AgingClaimReport(models.TransientModel):
    _name = 'aging.claim.report'
    _inherit = 'base.claim.report'
    _description = 'Aging Claim Report'

    # Data fields, used to browse report data
    results = fields.Many2many(
        comodel_name='aging.claim.view',
        compute='_compute_results',
        help='Use compute fields, so there is nothing store in database',
    )

    @api.multi
    def _compute_results(self):
        self.ensure_one()
        date_from = self.date_from or '0001-01-01'
        date_to = self.date_to or fields.Date.context_today(self)
        # company = self.env.user.company_id
        # account_id = self.partner_ids[0].property_account_receivable_id.id
        str_partners=''
        if self.partner_ids:
            str_partners = "%s %s" % ('and partner.id in ', tuple(self.partner_ids.ids))
            str_partners = str_partners.replace(",)",")")

        query = """
            	select x.partner_id,
                sum(case when x.send_date<%s then x.net_amount-coalesce(x.realization_amount,0) else 0 end) begin_balance,
                sum(case when x.send_date>=%s then x.net_amount else 0 end) debit,
                sum(case when x.send_date>=%s then coalesce(x.realization_amount,0) else 0 end) credit,
                sum( x.net_amount-coalesce(x.realization_amount,0)) end_balance,
                sum( x.net_amount-coalesce(x.realization_amount,0)) total_amount,
                sum(case when x.age>90 then x.net_amount-coalesce(x.realization_amount,0) else 0 end) as "morethan90",
                sum(case when x.age>60 and x.age<=90 then x.net_amount-coalesce(x.realization_amount,0) else 0 end) as "bt61and90",	
                sum(case when x.age>30 and x.age<=60 then x.net_amount-coalesce(x.realization_amount,0) else 0 end) as "bt31and60",
                sum(case when x.age>=0 and x.age<=30 then x.net_amount -coalesce(x.realization_amount,0) else 0 end) as "bt00and30"
                from (
                SELECT claim.partner_id, partner.name partner, claim.send_date,
                case when claim.send_date is null or claim.send_date<='1900-01-01' then -1
                     when claim.done_date is not null and claim.send_date>'1900-01-01'  
                        then claim.done_date::date -  claim.send_date
                     when claim.send_date>'1900-01-01'  
                        then CURRENT_DATE -  claim.send_date
                    else 0 
                end as age,	
                claim.net_amount net_amount,claim.realization_amount,
                claim.state
                FROM bsp_claim_cl claim join res_partner partner on claim.partner_id=partner.id
                where claim.state in ('post', 'paid','done') """ + str_partners + ") as x group by x.partner_id"

        self._cr.execute(query, (date_from, date_from, date_from))  #, tuple(self.partner_ids.ids)))
        aging_claim_results = self._cr.dictfetchall()
        report_line = self.env['aging.claim.view']
        self.results = [report_line.new(line).id for line in aging_claim_results]

class CLRecapitulationView(models.TransientModel):
    _name = 'cl.recap.view'
    _description = 'Claim Recapitulation View'
    _order = 'period'

    def month_name(self,month):
        names = {
            '01': 'January',
            '02': 'February',
            '03': 'March',
            '04': 'April',
            '05': 'May',
            '06': 'June',
            '07': 'July',
            '08': 'August',
            '09': 'September',
            '10': 'October',
            '11': 'November',
            '12': 'December',
        }
        return names[month]

    @api.depends('period')
    def _compute_monthname(self):
        for rec in self:
            month = rec.period[4:]
            rec.monthname = self.month_name(month)


    period = fields.Char()
    partner_id = fields.Many2one(comodel_name='res.partner')
    monthname = fields.Char(compute='_compute_monthname')
    alloctotalcl = fields.Float()
    alloctotalclaim = fields.Float()
    alloctotalnotclaim = fields.Float()
    alloctotalpaid = fields.Float()
    alloctotalnotpaid = fields.Float()
    notalloctotalcl = fields.Float()
    notalloctotalclaim = fields.Float()
    notalloctotalnotclaim = fields.Float()
    notalloctotalpaid = fields.Float()
    notalloctotalnotpaid = fields.Float()
    totalcl = fields.Float()
    totalclaim = fields.Float()
    totalnotclaim = fields.Float()
    totalpaid = fields.Float()
    totalnotpaid = fields.Float()
class CLRecapitulationReport(models.TransientModel):
    _name = 'cl.recap.report'
    _inherit = 'base.claim.report'
    _description = 'Claim Recapitulation Report'

    # Data fields, used to browse report data
    results = fields.Many2many(
        comodel_name='cl.recap.view',
        compute='_compute_results',
        help='Use compute fields, so there is nothing store in database',
    )

    @api.multi
    def _compute_results(self):
        self.ensure_one()
        date_from = self.date_from or '1900-01-01'
        date_to = self.date_to or fields.Date.context_today(self)

        # company = self.env.user.company_id
        # account_id = self.partner_ids[0].property_account_receivable_id.id

        # if len(self.partner_ids) == 1 and self.partner_ids.name == "ALL":
        #     partners = self.env['res.partner'].search([('supplier','=',True)])
        #     self.partner_ids = partners

        query = """
            	select cl.period period,cl.partner_id,
                sum(case when coalesce(alloc.len,0)>0 then cl.cn_total else 0 end) alloctotalcl,
                sum(case when coalesce(alloc.len,0)>0 and cl.claimcl_id is not null then cl.cn_total else 0 end) alloctotalclaim,
                sum(case when coalesce(alloc.len,0)>0 and cl.claimcl_id is null then cl.cn_total else 0 end) alloctotalnotclaim ,
                sum(case when coalesce(alloc.len,0)>0 then coalesce(cl.paid_total,0) else 0 end) alloctotalpaid ,
                sum(case when coalesce(alloc.len,0)>0 and cl.claimcl_id is not null then cl.cn_total-coalesce(cl.paid_total,0) else 0 end) alloctotalnotpaid,
                sum(case when coalesce(alloc.len,0)=0 then cl.cn_total else 0 end) notalloctotalcl,
                sum(case when coalesce(alloc.len,0)=0 and cl.claimcl_id is not null then cl.cn_total else 0 end) notalloctotalclaim,
                sum(case when coalesce(alloc.len,0)=0 and cl.claimcl_id is null then cl.cn_total else 0 end) notalloctotalnotclaim ,
                sum(case when coalesce(alloc.len,0)=0 then coalesce(cl.paid_total,0) else 0 end) notalloctotalpaid ,
                sum(case when coalesce(alloc.len,0)=0 and cl.claimcl_id is not null then cl.cn_total-coalesce(cl.paid_total,0) else 0 end) notalloctotalnotpaid,
                sum(cl.cn_total) totalcl,
                sum(case when cl.claimcl_id is not null then cl.cn_total else 0 end) totalclaim,
                sum(case when cl.claimcl_id is null then cl.cn_total else 0 end) totalnotclaim ,
                sum( coalesce(cl.paid_total,0)) totalpaid ,
                sum(case when cl.claimcl_id is not null then cl.cn_total-coalesce(cl.paid_total,0) else 0 end) totalnotpaid
                from bsp_creditnote_other cl 
                left join
                (select cn_id, count(*) len from  bsp_creditnote_alloc group by cn_id) as alloc on cl.id=alloc.cn_id
                where (cl.operating_unit_id = %s or 0=%s) AND cl.partner_id  in %s AND left(cl.period,4) = %s
                and cl.cn_date between %s and %s
                group by cl.period,partner_id
                order by cl.period,partner_id
                """

        pOU_unit_id = 0
        if self.operating_unit_id:
            pOU_unit_id =self.operating_unit_id.id



        self._cr.execute(query, (str(pOU_unit_id), str(pOU_unit_id),
                         tuple(self.partner_ids.ids), str(self.year_period), date_from, date_to))
        cl_recap_results = self._cr.dictfetchall()
        report_line = self.env['cl.recap.view']
        self.results = [report_line.new(line).id for line in cl_recap_results]

class ClaimJournalView(models.TransientModel):
    _name = 'claim.journal.view'
    _description = 'Claim Journal View'
    _order = 'journal_id'


    operating_unit_id = fields.Many2one(comodel_name= 'operating.unit')
    partner_id = fields.Many2one(comodel_name='res.partner')
    journal_id = fields.Many2one(comodel_name='account.journal')
    journalno = fields.Char('FNOBON', size=30)
    journaldate = fields.Date('FTGL')
    journalidx = fields.Integer('FNO')
    # bccdaccount_id = fields.Many2one(comodel_name='account.account',string='FBCCDNOACC')
    # bccdaccount_desc = fields.Char('FBCCDCOANO', size=80)
    account_id = fields.Many2one(comodel_name='account.account',string='FNOACC')
    # account_desc = fields.Char('FURAIAN', size=80)
    debet = fields.Float( 'FDEBET')
    credit = fields.Float('FKREDIT')
class ClaimJournalReport(models.TransientModel):
    _name = 'claim.journal.report'
    _inherit = 'base.claim.report'
    _description = 'Claim Journal Report'

    # Data fields, used to browse report data
    results = fields.Many2many(
        comodel_name='claim.journal.view',
        compute='_compute_results',
        help='Use compute fields, so there is nothing store in database',
    )

    @api.multi
    def _compute_results(self):
        self.ensure_one()
        date_from = self.date_from or '2020-01-01'
        date_to = self.date_to or fields.Date.context_today(self)
        # year_period = self.year_period



        query = """
                SELECT am.operating_unit_id operating_unit_id,am.partner_id partner_id, 
                am.journal_id journal_id,am.name journalno, am.date journaldate,
                1 journalidx,amline.account_id account_id,amline.debit debet, amline.credit credit
	            FROM account_move_line amline 
	            join account_move am on amline.move_id=am.id 
                where  am.journal_id  in %s
                and am.date between %s and %s               
                order by am.operating_unit_id,am.journal_id,am.partner_id,am.name, am.date
                """


        # pOU_unit_id = 0
        # if self.operating_unit_id:
        #     pOU_unit_id =self.operating_unit_id.id



        self._cr.execute(query, (tuple(self.journal_ids.ids), date_from, date_to))
        claim_journal_results = self._cr.dictfetchall()
        report_line = self.env['claim.journal.view']
        self.results = [report_line.new(line).id for line in claim_journal_results]
        self._create_dbf_file(self.results)
        # self.download_dbf("pidpi.dbf")



    def _create_dbf_file(self, journals):
        db = dbf.Dbf("/odoo/pidpi.dbf", new=True)
        db.header.code_page = 0x78
        db.add_field(
            ('C', "FNOBON", 20),
            ('D', "FTGL"),
            ('C', "FNO", 3),
            ('C', "FBCCDNOACC", 15),
            ('C', "FBCCDCOANO", 40),
            ('C', "FNOACC", 15),
            ('C', "FURAIAN", 40),
            ('N', "FDEBET", 10, 2),
            ('N', "FKREDIT", 10, 2),
        )
        # db.write("pidpi.dbf")
        for journal in journals:
            rec = db.new()
            rec["FNOBON"] = journal.journalno
            rec["FTGL"] = journal.journaldate
            rec["FNO"] = journal.journalidx
            if journal.account_id.group_id:
                rec["FBCCDNOACC"] = journal.account_id.group_id.code_prefix
                rec["FBCCDCOANO"] = journal.account_id.group_id.name
            else:
                rec["FBCCDNOACC"] = ''
                rec["FBCCDCOANO"] = ''
            rec["FNOACC"] = journal.account_id.code
            rec["FURAIAN"] = journal.account_id.name
            rec["FDEBET"] = journal.debet
            rec["FKREDIT"] = journal.credit
            db.write(rec)
        db.close()

    def download_dbf(self, filename):
        files = base64.b64encode(open("/odoo/"+filename, 'rb').read())

        filedbf = self.env['ir.attachment']
        filedbf.create({
            'name': filename,
            'datas': files,
            'datas_fname': filename
        })
        attachment = self.env['ir.attachment'].search([('name', '=', filename)], limit=1)
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (attachment.id),
            'target': 'new',
            'nodestroy': False,
        }

    @api.one
    def _get_template(self):
        self.dbf_template = base64.b64encode(open("pidpi.dbf", "rb").read())

    dbf_template = fields.Binary('Template', compute="_get_template")

    @api.multi
    def get_dbf_template(self):
        return {
            'type': 'ir.actions.act_url',
            'name': 'pidpi',
            'url': '/web/content/model.name/%s/dbf_template/pidpi.dbf?download=true' % (self.id),
        }

class CLMonitoringView(models.TransientModel):
    _name = 'claim.monitoring.view'
    _order = 'claim_id'
    _description = 'Claim Monitoring view'

    operating_unit_id = fields.Many2one(comodel_name='operating.unit')
    partner_id = fields.Many2one(comodel_name='res.partner')
    claim_id = fields.Many2one(
        comodel_name='bsp.claim.cl', string='CC Number')
class CLMonitoringReport(models.TransientModel):
    _name = 'claim.monitoring.report'
    _inherit = 'base.claim.report'
    _description = 'Claim Monitoring Report'

    # Data fields, used to browse report data
    results = fields.Many2many(
        comodel_name='claim.monitoring.view',
        compute='_compute_results',
        help='Use compute fields, so there is nothing store in database',
    )

    @api.multi
    def _compute_results(self):
        self.ensure_one()
        date_from = self.date_from or '1900-01-01'
        date_to = self.date_to or fields.Date.context_today(self)
        pOU_unit_id = 0
        query_principal = ''
        if self.operating_unit_id:
            pOU_unit_id = self.operating_unit_id.id
        if self.partner_ids:
            query_principal = ' AND cl.partner_id in %s' % (str(tuple(self.partner_ids.ids))).replace(',)', ')')


        query = """
                    SELECT  row_number() OVER (PARTITION BY true) AS id,
                        cl.operating_unit_id,
                        cl.partner_id,                    
                        cl.id AS claim_id
                    from bsp_claim_cl cl 
                    where (cl.operating_unit_id = %s or 0=%s) %s 
                    and  cl.claim_date between '%s' and '%s'
                    order by claim_id """ % ((str(pOU_unit_id), str(pOU_unit_id),
                                              query_principal, date_from, date_to))



        self._cr.execute(query)
        # , (str(pOU_unit_id), str(pOU_unit_id),
        #                  tuple(self.partner_ids.ids), date_from, date_to))
        cl_monitoring_results = self._cr.dictfetchall()
        report_line = self.env['claim.monitoring.view']
        self.results = [report_line.new(line).id for line in cl_monitoring_results]

class CLBMBKView(models.TransientModel):
    _name = 'claim.bmbk.view'
    # _order = 'claim_id'
    _description = 'Claim bmbk view'

    nomor = fields.Integer("No.")
    operating_unit_id = fields.Many2one(comodel_name='operating.unit')
    partner_id = fields.Many2one(comodel_name='res.partner')
    # invoice_line_id = fields.Many2one(
    #     comodel_name='account.invoice.line', string='Invoice Line')
    claim_id = fields.Many2one(
        comodel_name='bsp.claim.cl', string='CC Number')
    total_realisasi = fields.Float('Total Alokasi')
class CLBMBKReport(models.TransientModel):
    _name = 'claim.bmbk.report'
    _inherit = 'base.claim.report'
    _description = 'Claim BM-BK Report'

    # Data fields, used to browse report data
    results = fields.Many2many(
        comodel_name='claim.bmbk.view',
        compute='_compute_results',
        help='Use compute fields, so there is nothing store in database',
    )

    @api.multi
    def _compute_results(self):
        self.ensure_one()
        date_from = self.date_from or '1900-01-01'
        date_to = self.date_to or fields.Date.context_today(self)
        pOU_unit_id = 0
        query_principal = ''
        query_bmbk= ''
        query_coa = ''
        if self.operating_unit_id:
            pOU_unit_id = self.operating_unit_id.id
        if self.partner_ids:
            # query_principal =  """ AND cl.partner_id in %s """ % (tuple(self.partner_ids.ids))
            query_principal = ' AND cl.partner_id in %s' % (str(tuple(self.partner_ids.ids))).replace(',)', ')')

        if self.report_name == 'bm':
            query_bmbk = " AND pv.type = 'bm'"
        if self.report_name == 'bk':
            query_bmbk = " AND pv.type = 'bk'"
        if self.coa_no in ('28.2', '28.3'):
            query_coa = " AND pv.ref_coa = '%s' " % self.coa_no

        query = f""" 
                    SELECT  row_number() OVER (PARTITION BY true) AS id,
                        row_number() OVER (PARTITION BY true) AS nomor,
                        cl.operating_unit_id,
                        cl.partner_id,                
                        cl.id AS claim_id,                        
                        sum(ail.price_subtotal) total_realisasi
                        from account_move_line ml join account_payment p on p.id=ml.payment_id 
                        join bsp_payment_voucher pv on pv.id = p.pv_id
                        join account_invoice ai on ai."number" = p.communication 
                        join account_invoice_line ail on ai.id=ail.invoice_id 
                        join bsp_claim_cl cl on cl.id=ail.claimcl_id 
                        where ml.credit >0 
                        and (cl.operating_unit_id = %s or 0=%s) %s %s %s
                        and  pv.trx_date between '%s' and '%s' 
                        group by cl.operating_unit_id, cl.partner_id, cl.id
                        order by id  """ % ((str(pOU_unit_id), str(pOU_unit_id),
                                                  query_principal, query_bmbk, query_coa, date_from, date_to))



        self._cr.execute(query)
        # , (str(pOU_unit_id), str(pOU_unit_id),
        #                  tuple(self.partner_ids.ids), date_from, date_to))
        cl_bmbk_results = self._cr.dictfetchall()
        report_line = self.env['claim.bmbk.view']
        self.results = [report_line.new(line).id for line in cl_bmbk_results]



class BMBKAllocationView(models.TransientModel):
    _name = 'bmbk.allocation.view'
    _description = 'BMBK Allocatioan View'

    nomor = fields.Integer("No.")
    partner_id = fields.Many2one(comodel_name='res.partner')
    bmbk_number = fields.Char("BMBK Number", size=30)
    bmbk_group = fields.Char("BMBK Group", size=30)
    bmbk_date = fields.Date("BMBK Date")
    total_amount = fields.Float("Total Amount")
    alloc_amount = fields.Float("Alloc Amount")
    remain_amount = fields.Float("Remain Amount")
    item_name = fields.Char("Item Allocation", size=100)
    branch_code = fields.Char("Branch Code", size=5)
    real_amount = fields.Float("Realization Amount")
    pv_number = fields.Char("PV Number", size=30)
    payment_number = fields.Char("Payment Number", size=30)
    pv_id = fields.Many2one(
        comodel_name='bsp.payment.voucher', string='BMBK Number')
    item_id = fields.Many2one(
        comodel_name='account.invoice.line', string='Invoice Line')
    payment_id =fields.Many2one(
        comodel_name='account.payment', string='Payment Number')
    # invoice_line_id = fields.Many2one(
    #     comodel_name='account.invoice.line', string='Invoice Line')
    claim_id = fields.Many2one(
        comodel_name='bsp.claim.cl', string='CC Number')
class BMBKAllocationReport(models.TransientModel):
    _name = 'bmbk.allocation.report'
    _inherit = 'base.claim.report'
    _description = 'BM-BK Allocation Report'

    # Data fields, used to browse report data
    results = fields.Many2many(
        comodel_name='bmbk.allocation.view',
        compute='_compute_results',
        help='Use compute fields, so there is nothing store in database',
    )

    @api.multi
    def _compute_results(self):
        self.ensure_one()
        date_from = self.date_from or '1900-01-01'
        date_to = self.date_to or fields.Date.context_today(self)
        pOU_unit_id = 0
        query_principal = ''
        query_bmbk= ''
        query_coa = ''
        if self.operating_unit_id:
            pOU_unit_id = self.operating_unit_id.id
        if self.partner_ids:
            # query_principal =  """ AND cl.partner_id in %s """ % (tuple(self.partner_ids.ids))
            query_principal = ' AND ai.partner_id in %s' % (str(tuple(self.partner_ids.ids))).replace(',)', ')')

        if self.report_name == 'bm_alloc':
            query_bmbk = " AND pv.type = 'bm'"
        if self.report_name == 'bk_alloc':
            query_bmbk = " AND pv.type = 'bk'"
        if self.coa_no in ('28.2', '28.3'):
            query_coa = " AND pv.ref_coa = '%s' " % self.coa_no

        query = f""" 
                    SELECT  row_number() OVER (PARTITION BY true) AS id,
                        row_number() OVER (PARTITION BY true) AS nomor,
                        bmbk.*
                        from ( SELECT ai.partner_id, 
                        pv."name" bmbk_number,
                        case when (LAG(pv."name",1) OVER (
						            ORDER BY pv."name"))=pv."name" then '' else pv."name" end bmbk_group,  
						case when (LAG(pv."name",1) OVER (
						            ORDER BY pv."name"))=pv."name" then null else pv.trx_date end bmbk_date,
                        case when (LAG(pv."name",1) OVER (
						            ORDER BY pv."name"))=pv."name" then null else pv.total_amount end total_amount,
						case when (LAG(pv."name",1) OVER (
						            ORDER BY pv."name"))=pv."name" then null else pv.alloc_amount end alloc_amount,
						case when (LAG(pv."name",1) OVER (
						            ORDER BY pv."name"))=pv."name" then null else pv.remain_amount end remain_amount,                       
                        case when ail.claimcl_id is null 
                        then ail."name" else cl."name" end item_name, 
                        case when ail.claimcl_id is null 
                        then ail."name" else cl."name" end item_name,     
                        ail.branch_code,
                        ail.price_subtotal real_amount,
                        ai.number pv_number,
                        p.name payment_number,
                        pv.id pvi_d,
                        ail.id item_id,
                        p.id payment_id,
                        ail.claimcl_id claim_id
                        from account_move_line ml join account_payment p on p.id=ml.payment_id 
                        join bsp_payment_voucher pv on pv.id = p.pv_id
                        join account_invoice ai on ai."number" = p.communication 
                        join account_invoice_line ail on ai.id=ail.invoice_id 
                        left join bsp_claim_cl cl on cl.id=ail.claimcl_id 
                        where ml.credit >0 %s %s %s
                        and  pv.trx_date between '%s' and '%s' )bmbk                     
                        order by id  """ % (query_principal, query_bmbk, query_coa, date_from, date_to)



        self._cr.execute(query)
        # , (str(pOU_unit_id), str(pOU_unit_id),
        #                  tuple(self.partner_ids.ids), date_from, date_to))
        bmbk_results = self._cr.dictfetchall()
        report_line = self.env['bmbk.allocation.view']
        self.results = [report_line.new(line).id for line in bmbk_results]


class ClaimBalanceView(models.TransientModel):
    _name = 'claim.balance.view'
    _description = 'Claim AR Balance View'

    nomor = fields.Integer("No.")
    operating_unit_id = fields.Many2one(comodel_name='operating.unit')
    partner_id = fields.Many2one(comodel_name='res.partner')
    claim_id = fields.Many2one(
        comodel_name='bsp.claim.cl', string='CC Number')
    total_realisasi = fields.Float('Total Alokasi')
class ClaimBalanceReport(models.TransientModel):
    _name = 'claim.balance.report'
    _inherit = 'base.claim.report'
    _description = 'Claim AR Report'

    # Data fields, used to browse report data
    results = fields.Many2many(
        comodel_name='claim.balance.view',
        compute='_compute_results',
        help='Use compute fields, so there is nothing store in database',
    )

    @api.multi
    def _compute_results(self):
        self.ensure_one()
        date_from = self.date_from or '1900-01-01'
        date_to = self.date_to or fields.Date.context_today(self)
        pOU_unit_id = 0
        query_principal = ''
        query_bmbk = ''
        query_coa = ''
        if self.operating_unit_id:
            pOU_unit_id = self.operating_unit_id.id
        if self.partner_ids:
            # query_principal =  """ AND cl.partner_id in %s """ % (tuple(self.partner_ids.ids))
            query_principal = ' AND cl.partner_id in %s' % (str(tuple(self.partner_ids.ids))).replace(',)', ')')

        if self.report_name == 'bm':
            query_bmbk = " AND pv.type = 'bm'"
        if self.report_name == 'bk':
            query_bmbk = " AND pv.type = 'bk'"
        if self.coa_no in ('28.2', '28.3'):
            query_coa = " AND pv.ref_coa = '%s' " % self.coa_no

        query = f""" 
                    SELECT  row_number() OVER (PARTITION BY true) AS id,
                        row_number() OVER (PARTITION BY true) AS nomor,
                        cl.operating_unit_id,
                        cl.partner_id,                
                        cl.id AS claim_id,                        
                        sum(ail.price_subtotal) total_realisasi
                        from account_move_line ml join account_payment p on p.id=ml.payment_id 
                        join bsp_payment_voucher pv on pv.id = p.pv_id
                        join account_invoice ai on ai."number" = p.communication 
                        join account_invoice_line ail on ai.id=ail.invoice_id 
                        join bsp_claim_cl cl on cl.id=ail.claimcl_id 
                        where ml.credit >0 
                        and (cl.operating_unit_id = %s or 0=%s) %s %s %s
                        and  cl.send_date between '%s' and '%s' 
                        group by cl.operating_unit_id, cl.partner_id, cl.id
                        order by id  """ % ((str(pOU_unit_id), str(pOU_unit_id),
                                             query_principal, query_bmbk, query_coa, date_from, date_to))

        self._cr.execute(query)
        # , (str(pOU_unit_id), str(pOU_unit_id),
        #                  tuple(self.partner_ids.ids), date_from, date_to))
        cl_bmbk_results = self._cr.dictfetchall()
        report_line = self.env['claim.balance.view']
        self.results = [report_line.new(line).id for line in cl_bmbk_results]









