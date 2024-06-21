import logging
from odoo import models

_logger = logging.getLogger(__name__)

class ReportAgingClaimReportXlsx(models.AbstractModel):
    _name = 'report.bsp_claim_reports.aging_claim_report_xlsx'
    _inherit = 'base.claim.report_xlsx'

    def _get_ws_params(self, wb, data):
        filter_template = {
            '1_date_from': {
                'header': {
                    'value': 'Date from',
                },
                'data': {
                    'value': self._render('date_from'),
                    'format': self.format_tcell_date_center,
                },
            },
            '2_date_to': {
                'header': {
                    'value': 'Date to',
                },
                'data': {
                    'value': self._render('date_to'),
                    'format': self.format_tcell_date_center,
                },
            },
            
        }
        initial_template = {
            '1_ref': {
                'data': {
                    'value': 'Initial',
                    'format': self.format_tcell_center,
                },
                'colspan': 5,
            },
            '2_balance': {
                'data': {
                    'value': self._render('balance'),
                    'format': self.format_tcell_amount_right,
                },
            },
            '3_pass': {
                'data': {
                    'value': '',
                    'format': self.format_tcell_center,
                },
            },
            '4_ump': {
                'data': {
                    'value': self._render('ump'),
                    'format': self.format_tcell_amount_right,
                },
            },
        }

        aging_claim_template = {
            '1_code': {
                'header': {
                    'value': 'Code',
                },
                'data': {
                    'value': self._render('code'),
                    'format': self.format_tcell_date_left,
                },
                'width': 25,
            },
            '2_principal': {
                'header': {
                    'value': 'Principal',
                },
                'data': {
                    'value': self._render('principal'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '3_saldoawal': {
                'header': {
                    'value': 'Saldo Awal',
                },
                'data': {
                    'value': self._render('begin_balance'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("totbegin_balance"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '4_debit': {
                'header': {
                    'value': 'Debit',
                },
                'data': {
                    'value': self._render('debit'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("totdebit"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '5_credit': {
                'header': {
                    'value': 'Credit',
                },
                'data': {
                    'value': self._render('credit'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("totcredit"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '6_saldoakhir': {
                'header': {
                    'value': 'Saldo Akhir',
                },
                'data': {
                    'value': self._render('end_balance'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("totend_balance"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '7_total_claim': {
                'header': {
                    'value': 'Total Claim',
                },
                'data': {
                    'value': self._render('total_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tottotal_amount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '8_90': {
                'header': {
                    'value': 'More than 90',
                },
                'data': {
                    'value': self._render('morethan90'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("totmorethan90"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '9_60': {
                'header': {
                    'value': '61 sd 90',
                },
                'data': {
                    'value': self._render('bt61and90'),

                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("totbt61and90"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            'A_30': {
                'header': {
                    'value': '31 sd 60',
                },
                'data': {
                    'value': self._render('bt31and60'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("totbt31and60"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            'B_00': {
                'header': {
                    'value': '0 sd 30',
                },
                'data': {
                    'value': self._render('bt00and30'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("totbt00and30"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
        }



        ws_params = {
            'ws_name': "AR Card vs Aging Claim",
            'generate_ws_method': '_aging_claim_report',
            'title': 'Aging Claim',
            'wanted_list_filter': [k for k in sorted(filter_template.keys())],
            'col_specs_filter': filter_template,
            'wanted_list': [k for k in sorted(aging_claim_template.keys())],
            'col_specs': aging_claim_template,
        }
        return [ws_params]

    def _aging_claim_report(self, wb, ws, ws_params, data, objects):
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(self.xls_headers['standard'])
        ws.set_footer(self.xls_footers['standard'])
        self._set_column_width(ws, ws_params)
        # Title
        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params, True)
        # Filter Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center,
            col_specs='col_specs_filter', wanted_list='wanted_list_filter')

        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='data',
            render_space={
                'date_from': objects.date_from or '',
                'date_to': objects.date_to or '',
            },
            col_specs='col_specs_filter', wanted_list='wanted_list_filter')
        row_pos += 1
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center)
        ws.freeze_panes(row_pos, 0)

        partner_lines = objects.results
        wanted_list = ws_params['wanted_list']
        debit_pos = '4_debit' in wanted_list and wanted_list.index('4_debit')
        credit_pos = '5_credit' in wanted_list and wanted_list.index('5_credit')
        begin_balance_pos = '3_saldoawal' in wanted_list and wanted_list.index('3_saldoawal')
        end_balance_pos = '6_saldoakhir' in wanted_list and wanted_list.index('6_saldoakhir')
        total_amount_pos = '7_total_claim' in wanted_list and wanted_list.index('7_total_claim')
        morethan90_pos = '8_90' in wanted_list and wanted_list.index('8_90')
        bt61and90_pos = '9_60' in wanted_list and wanted_list.index('9_60')
        bt31and60_pos = 'A_30' in wanted_list and wanted_list.index('A_30')
        bt00and30_pos = 'B_00' in wanted_list and wanted_list.index('B_00')


        for line in partner_lines:
            row_pos = self._write_line(
                ws, row_pos, ws_params, col_specs_section='data',
                render_space={
                    'code': line.partner_id.ref or '',
                    'principal': line.partner_id.name or '',
                    'begin_balance': line.begin_balance or 0,
                    'debit': line.debit or 0,
                    'credit': line.credit or 0,
                    'end_balance': line.end_balance or 0,
                    'total_amount':line.total_amount or 0,
                    'morethan90': line.morethan90 or 0,
                    'bt61and90':line.bt61and90 or 0,
                    'bt31and60': line.bt31and60 or 0,
                    'bt00and30':line.bt00and30 or 0,

                },
                default_format=self.format_tcell_amount_right)
        i = len(partner_lines)
        totbegin_balance = self.get_sum_formula(begin_balance_pos, i, row_pos)
        totdebit = self.get_sum_formula(debit_pos, i, row_pos)
        totcredit = self.get_sum_formula(credit_pos, i, row_pos)
        totend_balance = self.get_sum_formula(end_balance_pos, i, row_pos)
        tottotal_amount = self.get_sum_formula(total_amount_pos, i, row_pos)
        totmorethan90 = self.get_sum_formula(morethan90_pos, i, row_pos)
        totbt61and90 = self.get_sum_formula(bt61and90_pos, i, row_pos)
        totbt31and60 = self.get_sum_formula(bt31and60_pos, i, row_pos)
        totbt00and30 = self.get_sum_formula(bt00and30_pos, i, row_pos)
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='totals',
            render_space={'totbegin_balance': totbegin_balance,
                          'totdebit': totdebit,
                          'totcredit': totcredit,
                          'totend_balance': totend_balance,
                          'tottotal_amount': tottotal_amount,
                          'totmorethan90': totmorethan90,
                          'totbt61and90': totbt61and90,
                          'totbt31and60': totbt31and60,
                          'totbt00and30': totbt00and30,
                          },
            default_format=self.format_theader_yellow_left)

class ReportBudgetCardReportXlsx(models.AbstractModel):
    _name = 'report.bsp_claim_reports.budget_card_report_xlsx'
    _inherit = 'base.claim.report_xlsx'

    def generate_xlsx_report(self, workbook, data, objects):
        self._define_formats(workbook)
        for partner in objects.partner_ids:
            for ws_params in self._get_ws_params(workbook, data, partner):
                ws_name = ws_params.get('ws_name')
                ws_name = self._check_ws_name(ws_name)
                ws = workbook.add_worksheet(ws_name)
                generate_ws_method = getattr(
                    self, ws_params['generate_ws_method'])
                generate_ws_method(
                    workbook, ws, ws_params, data, objects, partner)

    def _get_ws_params(self, wb, data, partner):
        filter_template = {
            '1_date_from': {
                'header': {
                    'value': 'Date from',
                },
                'data': {
                    'value': self._render('date_from'),
                    'format': self.format_tcell_date_center,
                },
            },
            '2_date_to': {
                'header': {
                    'value': 'Date to',
                },
                'data': {
                    'value': self._render('date_to'),
                    'format': self.format_tcell_date_center,
                },
            },

        }
        initial_template = {
            '1_ref': {
                'data': {
                    'value': 'Initial',
                    'format': self.format_tcell_center,
                },
                'colspan': 5,
            },
            '2_balance': {
                'data': {
                    'value': self._render('balance'),
                    'format': self.format_tcell_amount_right,
                },
            },
            '3_pass': {
                'data': {
                    'value': '',
                    'format': self.format_tcell_center,
                },
            },
            '4_pass': {
                'data': {
                    'value': '',
                    'format': self.format_tcell_center,
                },
            },
            '5_pass': {
                'data': {
                    'value': '',
                    'format': self.format_tcell_center,
                },
            },
            '6_ump': {
                'data': {
                    'value': self._render('ump'),
                    'format': self.format_tcell_amount_right,
                },
            },
        }
        budget_card_template = {
            '1_date': {
                'header': {
                    'value': 'Date',
                },
                'data': {
                    'value': self._render('date'),
                    'format': self.format_tcell_date_left,
                },
                'width': 25,
            },
            '2_reference': {
                'header': {
                    'value': 'Reference',
                },
                'data': {
                    'value': self._render('reference'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '3_journalno': {
                'header': {
                    'value': 'No.Journal',
                },
                'data': {
                    'value': self._render('journalno'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '4_input': {
                'header': {
                    'value': 'Input',
                },
                'data': {
                    'value': self._render('input'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("total_in"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '5_output': {
                'header': {
                    'value': 'Output',
                },
                'data': {
                    'value': self._render('output'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("total_out"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '6_balance': {
                'header': {
                    'value': 'Balance',
                },
                'data': {
                    'value': self._render('balance'),
                },
                'width': 25,
            },
            '7_alloc': {
                'header': {
                    'value': 'Total Allocation',
                },
                'data': {
                    'value': self._render('alloc_amount'),
                },

                'totals': {
                    'type': 'formula',
                    'value': self._render("total_alloc"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '8_alloc_detail': {
                'header': {
                    'value': 'Allocation',
                },

                'alloc': {
                    'value': self._render('alloc_value'),
                },

                'width': 18,
            },
            '9_alloc_detail': {
                'header': {
                    'value': 'Ref. Allocation',
                },

                'alloc': {
                    'value': self._render('alloc_number'),
                },

                'width': 30,
            },
            'a_ump': {
                'header': {
                    'value': 'UMP',
                },
                'data': {
                    'value': self._render('ump_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("total_ump"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            # '9_remark': {
            #     'header': {
            #         'value': 'Remark',
            #     },
            #     'alloc': {
            #         'value': self._render('alloc_number'),
            #     },
            #     'data': {
            #         'value': self._render('alloc_rmk'),
            #         'format': self.format_tcell_date_left,
            #     },
            #     'width': 65,
            # },
        }



        ws_params = {
            'ws_name': partner.name,
            'generate_ws_method': '_budget_card_report',
            'title': 'AR Card - {}'.format(partner.name),
            'wanted_list_filter': [k for k in sorted(filter_template.keys())],
            'col_specs_filter': filter_template,
            'wanted_list_initial': [k for k in sorted(initial_template.keys())],
            'col_specs_initial': initial_template,
            'wanted_list': [k for k in sorted(budget_card_template.keys())],
            'col_specs': budget_card_template,
        }
        return [ws_params]

    def _budget_card_report(self, wb, ws, ws_params, data, objects, partner):
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(self.xls_headers['standard'])
        ws.set_footer(self.xls_footers['standard'])
        self._set_column_width(ws, ws_params)
        # Title
        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params, True)
        # Filter Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center,
            col_specs='col_specs_filter',
            wanted_list='wanted_list_filter')
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='data',
            render_space={
                'date_from': objects.date_from or '',
                'date_to': objects.date_to or '',
            },
            col_specs='col_specs_filter', wanted_list='wanted_list_filter')
        row_pos += 1
        # Budget Card Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center)
        ws.freeze_panes(row_pos, 0)
        balance = objects._get_initial(objects.results.filtered(
            lambda l: l.partner_id == partner and l.is_initial))
        ump = objects._get_initial_ump(objects.results.filtered(
            lambda l: l.partner_id == partner and l.is_initial))
        row_pos = self._write_line(
            ws, row_pos, ws_params,
            col_specs_section='data',
            render_space={'balance': balance, 'ump': ump},
            col_specs='col_specs_initial',
            wanted_list='wanted_list_initial')
        partner_lines = objects.results.filtered(
            lambda l: l.partner_id == partner and not l.is_initial)
        wanted_list = ws_params['wanted_list']
        in_pos = '4_input' in wanted_list and wanted_list.index('4_input')
        out_pos = '5_output' in wanted_list and wanted_list.index('5_output')
        alloc_pos = '7_balance' in wanted_list and wanted_list.index('7_balance')
        ump_pos = '8_ump' in wanted_list and wanted_list.index('8_ump')
        for line in partner_lines:
            balance += line.ar_in - line.ar_out
            line_ump = 0
            if line.alloc_amount > 0:
                line_ump = line.ar_in - line.alloc_amount
            row_pos = self._write_line(
                ws, row_pos, ws_params, col_specs_section='data',
                render_space={
                    'date': line.date or '',
                    'reference': line.reference or '',
                    'journalno': line.move_name,
                    'input': line.ar_in or 0,
                    'output': line.ar_out or 0,
                    'balance': balance,
                    'alloc_amount': line.alloc_amount or 0,
                    'ump_amount': line_ump,
                    'alloc_rmk': line.alloc_rmk,
                },
                default_format=self.format_tcell_amount_right)
            for alloc in line.alloc_ids:
                row_pos = self._write_line(
                    ws, row_pos, ws_params, col_specs_section='alloc',
                    render_space={
                        'alloc_number': alloc.alloc_number or '',
                        'alloc_value': alloc.alloc_value or 0,
                    },
                    default_format=self.format_tcell_amount_right)


        i = len(partner_lines)
        total_in = self.get_sum_formula(in_pos, i, row_pos)
        total_out = self.get_sum_formula(out_pos, i, row_pos)
        total_alloc = self.get_sum_formula(alloc_pos, i, row_pos)
        total_ump = self.get_sum_formula(ump_pos, i, row_pos)
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='totals',
            render_space={'total_in': total_in,
                          'total_out': total_out,
                          'total_alloc': total_alloc,
                          'total_ump': total_ump,
                          },
            default_format=self.format_theader_blue_center)

class ReportCLRecapReportXlsx(models.AbstractModel):
    _name = 'report.bsp_claim_reports.cl_recap_report_xlsx'
    _inherit = 'base.claim.report_xlsx'

    def generate_xlsx_report(self, workbook, data, objects):
        self._define_formats(workbook)
        for partner in objects.partner_ids:
            for ws_params in self._get_ws_params(workbook, data, partner):
                ws_name = ws_params.get('ws_name')
                ws_name = self._check_ws_name(ws_name)
                ws = workbook.add_worksheet(ws_name)
                generate_ws_method = getattr(
                    self, ws_params['generate_ws_method'])
                generate_ws_method(
                    workbook, ws, ws_params, data, objects, partner)

    def _get_ws_params(self, wb, data, partner):
        filter_template = {
            '1_branch': {
                'header': {
                    'value': 'Branch',
                },
                'data': {
                    'value': self._render('branch'),
                    'format':self.format_tcell_left,
                },
            },
            '2_year_period': {
                'header': {
                    'value': 'Year Period',
                },
                'data': {
                    'value': self._render('year_period'),
                    'format': self.format_tcell_left,
                },
            },

        }

        initial_template = {
            '1_ref': {
                'data': {
                    'value': '',
                    'format': self.format_tcell_center,
                },
            },
            '2_alloc': {
                'data': {
                    'value': 'Total CL Sudah Alokasi',
                    'format': self.format_tcell_center,
                },
                'colspan': 5,
            },
            '3_notalloc': {
                'data': {
                    'value': 'Total CL Belum Alokasi',
                    'format': self.format_tcell_center,
                },
                'colspan': 5,
            },
            '4_all': {
                'data': {
                    'value': 'Total CL',
                    'format': self.format_tcell_center,
                },
                'colspan': 5,
            },
        }


        cl_recap_template = {
            '1_month': {
                'header': {
                    'value': 'Bulan',
                },
                'data': {
                    'value': self._render('monthname'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '2_atotalcl': {
                'header': {
                    'value': 'Total CL',
                },
                'data': {
                    'value': self._render('alloctotalcl'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotalcl"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            
            '3_atotalclclaim': {
                'header': {
                    'value': 'Sudah di Klaim',
                },
                'data': {
                    'value': self._render('alloctotalclclaim'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotalclclaim"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '4_atotalclnotclaim': {
                'header': {
                    'value': 'Debit',
                },
                'data': {
                    'value': self._render('alloctotalclnotclaim'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotalclnotclaim"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '5_atotalclpaid': {
                'header': {
                    'value': 'Sudah Penggantian',
                },
                'data': {
                    'value': self._render('alloctotalclpaid'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotalclpaid"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '6_atotalclnotpaid': {
                'header': {
                    'value': 'Belum Penggantian',
                },
                'data': {
                    'value': self._render('alloctotalclnotpaid'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotalclnotpaid"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '7_natotalcl': {
                'header': {
                    'value': 'Total CL',
                },
                'data': {
                    'value': self._render('notalloctotalcl'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tnatotalcl"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '8_natotalclclaim': {
                'header': {
                    'value': 'Sudah di Klaim',
                },
                'data': {
                    'value': self._render('notalloctotalclclaim'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tnatotalclclaim"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '9_natotalclnotclaim': {
                'header': {
                    'value': 'Debit',
                },
                'data': {
                    'value': self._render('notalloctotalclnotclaim'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tnatotalclnotclaim"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            'A_natotalclpaid': {
                'header': {
                    'value': 'Sudah Penggantian',
                },
                'data': {
                    'value': self._render('notalloctotalclpaid'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tnatotalclpaid"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            'B_natotalclnotpaid': {
                'header': {
                    'value': 'Belum Penggantian',
                },
                'data': {
                    'value': self._render('notalloctotalclnotpaid'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tnatotalclnotpaid"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            
            
            
            'C_totalcl': {
                'header': {
                    'value': 'Total CL',
                },
                'data': {
                    'value': self._render('totalcl'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("ttotalcl"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            'D_totalclclaim': {
                'header': {
                    'value': 'Sudah di Klaim',
                },
                'data': {
                    'value': self._render('totalclclaim'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("ttotalclclaim"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            'E_totalclnotclaim': {
                'header': {
                    'value': 'Debit',
                },
                'data': {
                    'value': self._render('totalclnotclaim'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("ttotalclnotclaim"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            'F_totalclpaid': {
                'header': {
                    'value': 'Sudah Penggantian',
                },
                'data': {
                    'value': self._render('totalclpaid'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("ttotalclpaid"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            'G_totalclnotpaid': {
                'header': {
                    'value': 'Belum Penggantian',
                },
                'data': {
                    'value': self._render('totalclnotpaid'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("ttotalclnotpaid"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
        }
        
        ws_params = {
            'ws_name': partner.name,
            'generate_ws_method': '_cl_recap_report',
            'title': 'CL Recap - {}'.format(partner.name),
            'wanted_list_filter': [k for k in sorted(filter_template.keys())],
            'col_specs_filter': filter_template,
            'wanted_list_initial': [k for k in sorted(initial_template.keys())],
            'col_specs_initial': initial_template,
            'wanted_list': [k for k in sorted(cl_recap_template.keys())],
            'col_specs': cl_recap_template,
        }
        return [ws_params]

    def _cl_recap_report(self, wb, ws, ws_params, data, objects, partner):
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(self.xls_headers['standard'])
        ws.set_footer(self.xls_footers['standard'])
        self._set_column_width(ws, ws_params)
        # Title
        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params, True)
        # Filter Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center,
            col_specs='col_specs_filter',
            wanted_list='wanted_list_filter')
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='data',
            render_space={
                'branch': objects.operating_unit_id.name or '',
                'year_period': objects.year_period or 0,
            },
            col_specs='col_specs_filter', wanted_list='wanted_list_filter')
        row_pos += 1

        row_pos = self._write_line(
            ws, row_pos, ws_params,
            col_specs_section='data',
            col_specs='col_specs_initial',
            wanted_list='wanted_list_initial')
        # Budget Card Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center)
        ws.freeze_panes(row_pos, 0)
        partner_lines = objects.results.filtered(lambda l: l.partner_id == partner)
        wanted_list = ws_params['wanted_list']
        atcl_pos = '2_atotalcl' in wanted_list and wanted_list.index('2_atotalcl')
        atclcl_pos = '3_atotalclclaim' in wanted_list and wanted_list.index('3_atotalclclaim')
        atclncl_pos = '4_atotalclnotclaim' in wanted_list and wanted_list.index('4_atotalclnotclaim')
        atclp_pos = '5_atotalclpaid' in wanted_list and wanted_list.index('5_atotalclpaid')
        atclnp_pos = '6_atotalclnotpaid' in wanted_list and wanted_list.index('6_atotalclnotpaid')

        natcl_pos = '7_natotalcl' in wanted_list and wanted_list.index('7_natotalcl')
        natclcl_pos = '8_natotalclclaim' in wanted_list and wanted_list.index('8_natotalclclaim')
        natclncl_pos = '9_natotalclnotclaim' in wanted_list and wanted_list.index('9_natotalclnotclaim')
        natclp_pos = 'A_natotalclpaid' in wanted_list and wanted_list.index('A_natotalclpaid')
        natclnp_pos = 'B_natotalclnotpaid' in wanted_list and wanted_list.index('B_natotalclnotpaid')

        tcl_pos = 'C_totalcl' in wanted_list and wanted_list.index('C_totalcl')
        tclcl_pos = 'D_totalclclaim' in wanted_list and wanted_list.index('D_totalclclaim')
        tclncl_pos = 'E_totalclnotclaim' in wanted_list and wanted_list.index('E_totalclnotclaim')
        tclp_pos = 'F_totalclpaid' in wanted_list and wanted_list.index('F_totalclpaid')
        tclnp_pos = 'G_totalclnotpaid' in wanted_list and wanted_list.index('G_totalclnotpaid')
        for line in partner_lines:
            row_pos = self._write_line(
                ws, row_pos, ws_params, col_specs_section='data',
                render_space={
                    'monthname': line.monthname or '',
                    'alloctotalcl': line.alloctotalcl or 0,
                    'alloctotalclclaim': line.alloctotalclaim or 0,
                    'alloctotalclnotclaim': line.alloctotalnotclaim or 0,
                    'alloctotalclpaid': line.alloctotalpaid or 0,
                    'alloctotalclnotpaid': line.alloctotalnotpaid or 0,
                    'notalloctotalcl': line.notalloctotalcl or 0,
                    'notalloctotalclclaim': line.notalloctotalclaim or 0,
                    'notalloctotalclnotclaim': line.notalloctotalnotclaim or 0,
                    'notalloctotalclpaid': line.notalloctotalpaid or 0,
                    'notalloctotalclnotpaid': line.notalloctotalnotpaid or 0,
                    'totalcl': line.totalcl or 0,
                    'totalclclaim': line.totalclaim or 0,
                    'totalclnotclaim': line.totalnotclaim or 0,
                    'totalclpaid': line.totalpaid or 0,
                    'totalclnotpaid': line.totalnotpaid or 0,
                },
                default_format=self.format_tcell_amount_right)

        i = len(partner_lines)

        tatotalcl = self.get_sum_formula(atcl_pos, i, row_pos)
        tatotalclclaim = self.get_sum_formula(atclcl_pos, i, row_pos)
        tatotalclnotclaim = self.get_sum_formula(atclncl_pos, i, row_pos)
        tatotalclpaid = self.get_sum_formula(atclp_pos, i, row_pos)
        tatotalclnotpaid = self.get_sum_formula(atclnp_pos, i, row_pos)
        tnatotalcl = self.get_sum_formula(natcl_pos, i, row_pos)
        tnatotalclclaim = self.get_sum_formula(natclcl_pos, i, row_pos)
        tnatotalclnotclaim = self.get_sum_formula(natclncl_pos, i, row_pos)
        tnatotalclpaid = self.get_sum_formula(natclp_pos, i, row_pos)
        tnatotalclnotpaid = self.get_sum_formula(natclnp_pos, i, row_pos)
        ttotalcl = self.get_sum_formula(tcl_pos, i, row_pos)
        ttotalclclaim = self.get_sum_formula(tclcl_pos, i, row_pos)
        ttotalclnotclaim = self.get_sum_formula(tclncl_pos, i, row_pos)
        ttotalclpaid = self.get_sum_formula(tclp_pos, i, row_pos)
        ttotalclnotpaid = self.get_sum_formula(tclnp_pos, i, row_pos)

        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='totals',
            render_space={'tatotalcl': tatotalcl,
                          'tatotalclclaim': tatotalclclaim,
                          'tatotalclnotclaim': tatotalclnotclaim,
                          'tatotalclpaid': tatotalclpaid,
                          'tatotalclnotpaid': tatotalclnotpaid,
                          'tnatotalcl': tnatotalcl,
                          'tnatotalclclaim': tnatotalclclaim,
                          'tnatotalclnotclaim': tnatotalclnotclaim,
                          'tnatotalclpaid': tnatotalclpaid,
                          'tnatotalclnotpaid': tnatotalclnotpaid,
                          'ttotalcl': ttotalcl,
                          'ttotalclclaim': ttotalclclaim,
                          'ttotalclnotclaim': ttotalclnotclaim,
                          'ttotalclpaid': ttotalclpaid,
                          'ttotalclnotpaid': ttotalclnotpaid,
                          },
            default_format=self.format_theader_blue_center)

class ReportClaimJournaReportXlsx(models.AbstractModel):
    _name = 'report.bsp_claim_reports.claim_journal_report_xlsx'
    _inherit = 'base.claim.report_xlsx'

    def generate_xlsx_report(self, workbook, data, objects):
        self._define_formats(workbook)
        for partner in objects.journal_ids:
            for ws_params in self._get_ws_params(workbook, data, partner):
                ws_name = ws_params.get('ws_name')
                ws_name = self._check_ws_name(ws_name)
                ws = workbook.add_worksheet(ws_name)
                generate_ws_method = getattr(
                    self, ws_params['generate_ws_method'])
                generate_ws_method(
                    workbook, ws, ws_params, data, objects, partner)

    def _get_ws_params(self, wb, data,partner):
        filter_template = {
            '1_date_from': {
                'header': {
                    'value': 'Date from',
                },
                'data': {
                    'value': self._render('date_from'),
                    'format': self.format_tcell_date_center,
                },
            },
            '2_date_to': {
                'header': {
                    'value': 'Date to',
                },
                'data': {
                    'value': self._render('date_to'),
                    'format': self.format_tcell_date_center,
                },
            },

        }
        # initial_template = {
        #     '1_ref': {
        #         'data': {
        #             'value': 'Initial',
        #             'format': self.format_tcell_center,
        #         },
        #         'colspan': 5,
        #     },
        #     '2_balance': {
        #         'data': {
        #             'value': self._render('balance'),
        #             'format': self.format_tcell_amount_right,
        #         },
        #     },
        #     '3_pass': {
        #         'data': {
        #             'value': '',
        #             'format': self.format_tcell_center,
        #         },
        #     },
        #     '4_ump': {
        #         'data': {
        #             'value': self._render('ump'),
        #             'format': self.format_tcell_amount_right,
        #         },
        #     },
        # }


        claim_journal_template = {

            '1_no': {
                'header': {
                    'value': 'FNOBON',
                },
                'data': {
                    'value': self._render('journalno'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '2_date': {
                'header': {
                    'value': 'FTGL',
                },
                'data': {
                    'value': self._render('journaldate'),
                    'format': self.format_tcell_date_left,
                },
                'width': 25,
            },
            '3_noidx': {
                'header': {
                    'value': 'FNO',
                },
                'data': {
                    'value': self._render('journalidx'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },

            '4_coa_bccd': {
                'header': {
                    'value': 'FBCCDNOACC',
                },
                'data': {
                    'value': self._render('group_code'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '5_coa_bccd_desc': {
                'header': {
                    'value': 'FBCCDCOANO',
                },
                'data': {
                    'value': self._render('group_name'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '6_coa': {
                'header': {
                    'value': 'FNOACC',
                },
                'data': {
                    'value': self._render('account_code'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '7_coa_desc': {
                'header': {
                    'value': 'FURAIAN',
                },
                'data': {
                    'value': self._render('account_name'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },

            '8_debit': {
                'header': {
                    'value': 'FDEBET',
                },
                'data': {
                    'value': self._render('debit'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("totdebit"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '9_credit': {
                'header': {
                    'value': 'FKREDIT',
                },
                'data': {
                    'value': self._render('credit'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("totcredit"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },


        }

        ws_params = {
            'ws_name': partner.name,
            'generate_ws_method': '_claim_journal_report',
            'title': 'CLAIM Journal - {}'.format(partner.name),
             'wanted_list_filter': [k for k in sorted(filter_template.keys())],
            'col_specs_filter': filter_template,
            'wanted_list': [k for k in sorted(claim_journal_template.keys())],
            'col_specs': claim_journal_template,
        }
        return [ws_params]

    def _claim_journal_report(self, wb, ws, ws_params, data, objects, partner):
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(self.xls_headers['standard'])
        ws.set_footer(self.xls_footers['standard'])
        self._set_column_width(ws, ws_params)
        # Title
        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params, True)
        # Filter Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center,
            col_specs='col_specs_filter', wanted_list='wanted_list_filter')

        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='data',
            render_space={
                'date_from': objects.date_from or '',
                'date_to': objects.date_to or '',
            },
            col_specs='col_specs_filter', wanted_list='wanted_list_filter')
        row_pos += 1
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center)
        ws.freeze_panes(row_pos, 0)

        partner_lines = objects.results
        wanted_list = ws_params['wanted_list']
        debit_pos = '8_debit' in wanted_list and wanted_list.index('8_debit')
        credit_pos = '9_credit' in wanted_list and wanted_list.index('9_credit')

        for line in partner_lines:
            row_pos = self._write_line(
                ws, row_pos, ws_params, col_specs_section='data',
                render_space={
                    'journalno': line.journalno or '',
                    'journaldate': line.journaldate or '',
                    'journalidx': line.journalidx or '',
                    'group_code': line.account_id.group_id.code_prefix or 0,
                    'group_name': line.account_id.group_id.name or '',
                    'account_code': line.account_id.code or 0,
                    'account_name': line.account_id.name or '',
                    'debit': line.debet or 0,
                    'credit': line.credit or 0,

                },
                default_format=self.format_tcell_amount_right)
        i = len(partner_lines)
        totdebit = self.get_sum_formula(debit_pos, i, row_pos)
        totcredit = self.get_sum_formula(credit_pos, i, row_pos)

        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='totals',
            render_space={'totdebit': totdebit,
                          'totcredit': totcredit,
                          },
            default_format=self.format_theader_yellow_left)

class ReportClaimMonitoringReportXlsx(models.AbstractModel):
    _name = 'report.bsp_claim_reports.claim_monitoring_report_xlsx'
    _inherit = 'base.claim.report_xlsx'

    def generate_xlsx_report(self, workbook, data, objects):
        self._define_formats(workbook)
        for ws_params in self._get_ws_params(workbook, data):
            ws_name = ws_params.get('ws_name')
            ws_name = self._check_ws_name(ws_name)
            ws = workbook.add_worksheet(ws_name)
            generate_ws_method = getattr(self, ws_params['generate_ws_method'])
            # generate_ws_method(workbook, ws, ws_params, data, objects, partner)
            generate_ws_method(ws, ws_params, objects)

    def _get_ws_params(self, wb, data):
        filter_template = {
             '01_date_from': {
                'header': {
                    'value': 'Date from',
                },
                'data': {
                    'value': self._render('date_from'),
                    'format': self.format_tcell_date_center,
                },
            },
            '02_date_to': {
                'header': {
                    'value': 'Date to',
                },
                'data': {
                    'value': self._render('date_to'),
                    'format': self.format_tcell_date_center,
                },
            },

        }


        cl_monitoring_template = {
            '01_principal': {
                'header': {
                    'value': 'Principal',
                },
                'data': {
                    'value': self._render('principal'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '02_branch': {
                'header': {
                    'value': 'Cabang',
                },
                'data': {
                    'value': self._render('branch'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '03_principal': {
                'header': {
                    'value': 'Program',
                },
                'data': {
                    'value': self._render('program'),
                    'format': self.format_tcell_left,
                },
                'width': 80,
            },
            '04_period': {
                'header': {
                    'value': 'Periode',
                },
                'data': {
                    'value': self._render('period'),
                    'format': self.format_tcell_left,
                },
                'width':20,
            },

            '05_kcref': {
                'header': {
                    'value': 'KC/REF',
                },
                'data': {
                    'value': self._render('kcref'),
                    'format': self.format_tcell_left,
                },
                'width': 20,
            },

            '06_fp': {
                'header': {
                    'value': 'PF',
                },
                'data': {
                    'value': self._render('pf'),
                    'format': self.format_tcell_left,
                },
                'width': 20,
            },

            '07_refoutlet': {
                'header': {
                    'value': 'Ref.Outlet',
                },
                'data': {
                    'value': self._render('refoutlet'),
                    'format': self.format_tcell_left,
                },
                'width': 20,
            },

            '08_rcvdate': {
                'header': {
                    'value': 'Tgl.Terima Klaim',
                },
                'data': {
                    'value': self._render('rcv_date'),
                    'format': self.format_tcell_date_left,
                },
                'width': 20,
            },

            '09_noclaimbr': {
                'header': {
                    'value': 'No.Klaim Cabang',
                },
                'data': {
                    'value': self._render('no_claim'),
                    'format': self.format_tcell_left,
                },
                'width': 30,
            },


            '10_coding': {
                'header': {
                    'value': 'KODING',
                },
                'data': {
                    'value': self._render('coding'),
                    'format': self.format_tcell_left,
                },
                'width': 10,
            },

            '11_netamount': {
                'header': {
                    'value': 'Jumlah',
                },
                'data': {
                    'value': self._render('net_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_netamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '12_approcess': {
                'header': {
                    'value': 'AP Process',
                },
                'data': {
                    'value': self._render('approcess'),
                    'format': self.format_tcell_left,
                },
                'width': 5,
            },
            '13_claimdate': {
                'header': {
                    'value': 'Tgl.Klaim',
                },
                'data': {
                    'value': self._render('claim_date'),
                    'format': self.format_tcell_date_left,
                },
                'width': 30,
            },

            '14_fjasa': {
                'header': {
                    'value': 'Faktur Jasa',
                },
                'data': {
                    'value': self._render('service_inv'),
                    'format': self.format_tcell_left,
                },
                'width': 20,
            },
            '14_fpajak': {
                'header': {
                    'value': 'Faktur Pajak',
                },
                'data': {
                    'value': self._render('tax_inv'),
                    'format': self.format_tcell_left,
                },
                'width': 20,
            },

            '15_dpp': {
                'header': {
                    'value': 'DPP',
                },
                'data': {
                    'value': self._render('claim_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_dppamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '16_ppn': {
                'header': {
                    'value': 'PPN',
                },
                'data': {
                    'value': self._render('tax_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_ppnamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '17_pph': {
                'header': {
                    'value': 'PPH',
                },
                'data': {
                    'value': self._render('pph1_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_pphamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '18_claimtotal': {
                'header': {
                    'value': 'Jumlah',
                },
                'data': {
                    'type': 'formula',
                    'value': self._render('fclaimtotal_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_fclaimamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },



            '19_senddate': {
                'header': {
                    'value': 'Send Date',
                },
                'data': {
                    'value': self._render('send_date'),
                    'format': self.format_tcell_date_left,
                },
                'width': 20,
            },


        }

        ws_params = {
            'ws_name': 'Monitoring',  #partner.name,
            'generate_ws_method': '_cl_monitoring_report',
            'title': 'Claim Monitoring Report', #- {}'.format(partner.name),
            'wanted_list_filter': [k for k in sorted(filter_template.keys())],
            'col_specs_filter': filter_template,
            # 'wanted_list_initial': [k for k in sorted(initial_template.keys())],
            # 'col_specs_initial': initial_template,
            'wanted_list': [k for k in sorted(cl_monitoring_template.keys())],
            'col_specs': cl_monitoring_template,
        }
        return [ws_params]

    def _cl_monitoring_report(self, ws, ws_params, objects):
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(self.xls_headers['standard'])
        ws.set_footer(self.xls_footers['standard'])
        self._set_column_width(ws, ws_params)
        # Title
        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params, True)
        # Filter Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center,
            col_specs='col_specs_filter',
            wanted_list='wanted_list_filter')
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='data',
            render_space={
                'date_from': objects.date_from or '',
                'date_to': objects.date_to or '',
            },
            col_specs='col_specs_filter', wanted_list='wanted_list_filter')
        row_pos += 1

        row_pos = self._write_line(
            ws, row_pos, ws_params,
            col_specs_section='data',
            col_specs='col_specs_initial',
            wanted_list='wanted_list_initial')
        # claim monitoring Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center)
        ws.freeze_panes(row_pos, 0)
        partner_lines = objects.results #.filtered(lambda l: l.partner_id == partner)
        wanted_list = ws_params['wanted_list']
        atcl_pos = '11_netamount' in wanted_list and wanted_list.index('11_netamount')

        dpp_pos = '15_dpp' in wanted_list and wanted_list.index('15_dpp')
        pph_pos = '17_pph' in wanted_list and wanted_list.index('17_pph')
        ppn_pos = '16_ppn' in wanted_list and wanted_list.index('16_ppn')
        claimtotal_pos = '18_claimtotal' in wanted_list and wanted_list.index('18_claimtotal')

        for line in partner_lines:
            claim = line.claim_id
            fclaimtotal_amount ="%s+%s+%s" % (self._rowcol_to_cell(row_pos, dpp_pos),
                                              self._rowcol_to_cell(row_pos, ppn_pos),
                                              self._rowcol_to_cell(row_pos, pph_pos))
            row_pos = self._write_line(
                ws, row_pos, ws_params, col_specs_section='data',
                render_space={
                    'branch': claim.operating_unit_id.code or '',
                    'principal': claim.partner_id.name or '',
                    'program': claim.remark or '',
                    'period': claim.period or '',
                    'kcref': claim.refdoc or '',
                    'pf': claim.tax_inv or '',
                    'refoutlet': claim.customer_ref or '',
                    'no_claim': claim.name or '',
                    'rcv_date': claim.receive_date or '',
                    'coding': claim.coding.upper() or '',
                    'net_amount': claim.net_amount or 0,
                    'approcess': claim.process_ap or '',
                    'claim_date': claim.claim_date or '',
                    'service_inv': claim.service_inv or '',
                    'tax_inv': claim.tax_inv or '',
                    'claim_amount': claim.claim_amount or 0,
                    'tax_amount': claim.tax_amount or 0,
                    'pph1_amount': claim.pph1_amount or 0,
                    'fclaimtotal_amount': fclaimtotal_amount or 0,
                    'send_date': claim.send_date or '',

                },
                default_format=self.format_tcell_amount_right)

        i = len(partner_lines)

        tatotal_netamount = self.get_sum_formula(atcl_pos, i, row_pos)
        tatotal_dppamount = self.get_sum_formula(dpp_pos, i, row_pos)
        tatotal_ppnamount = self.get_sum_formula(ppn_pos, i, row_pos)
        tatotal_pphamount = self.get_sum_formula(pph_pos, i, row_pos)
        tatotal_fclaimamount = self.get_sum_formula(claimtotal_pos, i, row_pos)


        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='totals',
            render_space={
                            'tatotal_netamount': tatotal_netamount,
                            'tatotal_dppamount': tatotal_dppamount,
                            'tatotal_ppnamount': tatotal_ppnamount,
                            'tatotal_pphamount': tatotal_pphamount,
                            'tatotal_fclaimamount': tatotal_fclaimamount,
                          },
            default_format=self.format_theader_blue_center)

class ReportClaimBMBKReportXlsx(models.AbstractModel):
    _name = 'report.bsp_claim_reports.claim_bmbk_report_xlsx'
    _inherit = 'base.claim.report_xlsx'

    def generate_xlsx_report(self, workbook, data, objects):
        self._define_formats(workbook)
        for ws_params in self._get_ws_params(workbook, data,objects):
            ws_name = ws_params.get('ws_name')
            ws_name = self._check_ws_name(ws_name)
            ws = workbook.add_worksheet(ws_name)
            generate_ws_method = getattr(self, ws_params['generate_ws_method'])
            # generate_ws_method(workbook, ws, ws_params, data, objects, partner)
            generate_ws_method(ws, ws_params, objects)

    def _get_ws_params(self, wb, data,objects):
        filter_template = {
             '01_date_from': {
                'header': {
                    'value': 'Date from',
                },
                'data': {
                    'value': self._render('date_from'),
                    'format': self.format_tcell_date_center,
                },
            },
            '02_date_to': {
                'header': {
                    'value': 'Date to',
                },
                'data': {
                    'value': self._render('date_to'),
                    'format': self.format_tcell_date_center,
                },
            },

        }


        cl_bmbk_template = {

            '00_nomor': {
                'header': {
                    'value': 'No.',
                },
                'data': {
                    'value': self._render('nomor'),
                    'format': self.format_tcell_right,
                },
                'width': 5,
            },
            '01_program': {
                'header': {
                    'value': 'Program',
                },
                'data': {
                    'value': self._render('program'),
                    'format': self.format_tcell_left,
                },
                'width': 80,
            },
            '02_branch': {
                'header': {
                    'value': 'Cabang',
                },
                'data': {
                    'value': self._render('branch'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '03_claimdate': {
                'header': {
                    'value': 'Tgl.Klaim',
                },
                'data': {
                    'value': self._render('claim_date'),
                    'format': self.format_tcell_date_left,
                },
                'width': 30,
            },
            '04_noclaimbr': {
                'header': {
                    'value': 'No.Klaim Cabang',
                },
                'data': {
                    'value': self._render('no_claim'),
                    'format': self.format_tcell_left,
                },
                'width': 30,
            },
            '05_fjasa': {
                'header': {
                    'value': 'Faktur Jasa',
                },
                'data': {
                    'value': self._render('service_inv'),
                    'format': self.format_tcell_left,
                },
                'width': 20,
            },
            '06_dpp': {
                'header': {
                    'value': 'DPP',
                },
                'data': {
                    'value': self._render('claim_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_dppamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '07_ppn': {
                'header': {
                    'value': 'PPN',
                },
                'data': {
                    'value': self._render('tax_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_ppnamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '08_pph': {
                'header': {
                    'value': 'PPH',
                },
                'data': {
                    'value': self._render('pph1_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_pphamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '09_netamount': {
                'header': {
                    'value': 'Jumlah',
                },
                'data': {
                    'value': self._render('net_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_netamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '10_realisasi': {
                'header': {
                    'value': 'Realisasi',
                },
                'data': {
                    'value': self._render('realization_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_realisasi"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '11_balance': {
                'header': {
                    'value': 'Balance',
                },
                'data': {
                    'value': self._render('balance_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_balance"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '12_paymentdate': {
                'header': {
                    'value': 'Tgl.BM/BK',
                },
                'data': {
                    'value': self._render('payment_date'),
                    'format': self.format_tcell_date_left,
                },
                'width': 20,
            },
            '131_paymentappdate': {
                'header': {
                    'value': 'Tgl.Approval Principal',
                },
                'data': {
                    'value': self._render('payment_app_date'),
                    'format': self.format_tcell_date_left,
                },
                'width': 20,
            },
            '132_bankref': {
                'header': {
                    'value': 'No.Ref Bank',
                },
                'data': {
                    'value': self._render('bank_ref'),
                    'format': self.format_tcell_left,
                },
                'width': 60,
            },

            '14_pv': {
                'header': {
                    'value': 'No.Payment Voucher',
                },
                'data': {
                    'value': self._render('no_pv'),
                    'format': self.format_tcell_left,
                },
                'width': 60,
            },
            '15_alokasibmbk': {
                'header': {
                    'value': 'Total BM/BK',
                },
                'data': {
                    'value': self._render('total_realisasi'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_alloc"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '16_coding': {
                'header': {
                    'value': 'KODING',
                },
                'data': {
                    'value': self._render('coding'),
                    'format': self.format_tcell_left,
                },
                'width': 10,
            },

            '17_principal': {
                'header': {
                    'value': 'Principal',
                },
                'data': {
                    'value': self._render('principal'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },

            '18_nocl_principal': {
                'header': {
                    'value': 'No.Klaim Principal',
                },
                'data': {
                    'value': self._render('cl_principal'),
                    'format': self.format_tcell_left,
                },
                'width': 20,
            },
        }
        report_title = 'Claim BM Recapitulation Report'
        sheet_name = 'BM Recap'
        if objects.report_name=='bk':
            report_title = 'Claim BK Recapitulation Report'
            sheet_name = 'BK Recap'

        ws_params = {
            'ws_name': sheet_name,  #partner.name,
            'generate_ws_method': '_cl_bmbk_report',
            'title': report_title, #- {}'.format(partner.name),
            'wanted_list_filter': [k for k in sorted(filter_template.keys())],
            'col_specs_filter': filter_template,
            # 'wanted_list_initial': [k for k in sorted(initial_template.keys())],
            # 'col_specs_initial': initial_template,
            'wanted_list': [k for k in sorted(cl_bmbk_template.keys())],
            'col_specs': cl_bmbk_template,
        }
        return [ws_params]

    def _cl_bmbk_report(self, ws, ws_params, objects):
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(self.xls_headers['standard'])
        ws.set_footer(self.xls_footers['standard'])
        self._set_column_width(ws, ws_params)
        # Title
        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params, True)
        # Filter Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center,
            col_specs='col_specs_filter',
            wanted_list='wanted_list_filter')
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='data',
            render_space={
                'date_from': objects.date_from or '',
                'date_to': objects.date_to or '',
            },
            col_specs='col_specs_filter', wanted_list='wanted_list_filter')
        row_pos += 1

        row_pos = self._write_line(
            ws, row_pos, ws_params,
            col_specs_section='data',
            col_specs='col_specs_initial',
            wanted_list='wanted_list_initial')
        # claim bmbk Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center)
        ws.freeze_panes(row_pos, 0)
        partner_lines = objects.results #.filtered(lambda l: l.partner_id == partner)
        wanted_list = ws_params['wanted_list']


        dpp_pos = '06_dpp' in wanted_list and wanted_list.index('06_dpp')
        ppn_pos = '07_ppn' in wanted_list and wanted_list.index('07_ppn')
        pph_pos = '08_pph' in wanted_list and wanted_list.index('08_pph')
        netamount_pos = '09_netamount' in wanted_list and wanted_list.index('09_netamount')
        real_pos = '10_realisasi' in wanted_list and wanted_list.index('10_realisasi')
        blc_pos = '11_balance' in wanted_list and wanted_list.index('11_balance')
        alloc_pos = '15_alokasibmbk' in wanted_list and wanted_list.index('15_alokasibmbk')

        for line in partner_lines:
            claim = line.claim_id
            cod = ''
            if claim.coding:
                cod = claim.coding.upper()
            # fclaimtotal_amount ="%s+%s+%s" % (self._rowcol_to_cell(row_pos, dpp_pos),
            #                                   self._rowcol_to_cell(row_pos, ppn_pos),
            #                                   self._rowcol_to_cell(row_pos, pph_pos))
            row_pos = self._write_line(
                ws, row_pos, ws_params, col_specs_section='data',
                render_space={
                    'nomor':line.nomor or 0,
                    'program': claim.remark or '',
                    'branch': claim.operating_unit_id.code or '',
                    'claim_date': claim.claim_date or '',
                    'no_claim': claim.name or '',
                    'service_inv': claim.service_inv or '',
                    'claim_amount': claim.claim_amount or 0,
                    'tax_amount': claim.tax_amount or 0,
                    'pph1_amount': claim.pph1_amount or 0,
                    'net_amount': claim.net_amount or 0,
                    'realization_amount': claim.realization_amount or 0,
                    'balance_amount': claim.balance_amount or 0,
                    'payment_date': claim.lpayment_date or '',
                    'payment_app_date': claim.lpayment_app_date or '',
                    'bank_ref': claim.lpayment_bankno or '',
                    'no_pv': claim.linvoices or '',
                    'total_realisasi':line.total_realisasi or 0,
                    'coding': cod or '',
                    'principal': claim.partner_id.ref or '',
                    'cl_principal': claim.claim_letter or '',
                },
                default_format=self.format_tcell_amount_right)

        i = len(partner_lines)


        tatotal_dppamount = self.get_sum_formula(dpp_pos, i, row_pos)
        tatotal_ppnamount = self.get_sum_formula(ppn_pos, i, row_pos)
        tatotal_pphamount = self.get_sum_formula(pph_pos, i, row_pos)
        tatotal_netamount = self.get_sum_formula(netamount_pos, i, row_pos)
        tatotal_realisasi = self.get_sum_formula(real_pos, i, row_pos)
        tatotal_balance = self.get_sum_formula(blc_pos, i, row_pos)
        tatotal_alloc = self.get_sum_formula(alloc_pos, i, row_pos)

        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='totals',
            render_space={

                            'tatotal_dppamount': tatotal_dppamount,
                            'tatotal_ppnamount': tatotal_ppnamount,
                            'tatotal_pphamount': tatotal_pphamount,
                            'tatotal_netamount': tatotal_netamount,
                            'tatotal_realisasi': tatotal_realisasi,
                            'tatotal_balance': tatotal_balance,
                            'tatotal_alloc': tatotal_alloc,
                          },
            default_format=self.format_theader_blue_center)

class ReportBMBKAllocationReportXlsx(models.AbstractModel):
    _name = 'report.bsp_claim_reports.bmbk_allocation_report_xlsx'
    _inherit = 'base.claim.report_xlsx'

    def generate_xlsx_report(self, workbook, data, objects):
        self._define_formats(workbook)
        for ws_params in self._get_ws_params(workbook, data,objects):
            ws_name = ws_params.get('ws_name')
            ws_name = self._check_ws_name(ws_name)
            ws = workbook.add_worksheet(ws_name)
            generate_ws_method = getattr(self, ws_params['generate_ws_method'])
            # generate_ws_method(workbook, ws, ws_params, data, objects, partner)
            generate_ws_method(ws, ws_params, objects)

    def _get_ws_params(self, wb, data,objects):
        filter_template = {
             '01_date_from': {
                'header': {
                    'value': 'Date from',
                },
                'data': {
                    'value': self._render('date_from'),
                    'format': self.format_tcell_date_center,
                },
            },
            '02_date_to': {
                'header': {
                    'value': 'Date to',
                },
                'data': {
                    'value': self._render('date_to'),
                    'format': self.format_tcell_date_center,
                },
            },

        }






        cl_bmbk_template = {

            '00_nomor': {
                'header': {
                    'value': 'No.',
                },
                'data': {
                    'value': self._render('nomor'),
                    'format': self.format_tcell_right,
                },
                'width': 5,
            },
            '01_bank_ref_no': {
                'header': {
                    'value': 'BM/BK Number',
                },
                'data': {
                    'value': self._render('bank_ref_no'),
                    'format': self.format_tcell_left,
                },
                'width': 20,
            },
            '02_bank_ref_date': {
                'header': {
                    'value': 'BM/BK Date',
                },
                'data': {
                    'value': self._render('bank_ref_date'),
                    'format': self.format_tcell_date_left,
                },
                'width': 15,
            },
            '021_total_amount': {
                'header': {
                    'value': 'BM/BK Amount',
                },
                'data': {
                    'value': self._render('total_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_total_amount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '022_alloc_amount': {
                'header': {
                    'value': 'BM/BK Allocated',
                },
                'data': {
                    'value': self._render('alloc_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_alloc_amount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '023_remain_amount': {
                'header': {
                    'value': 'BM/BK Remain',
                },
                'data': {
                    'value': self._render('remain_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_remain_amount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '03_pv_line_item': {
                'header': {
                    'value': 'Allocation Item',
                },
                'data': {
                    'value': self._render('pv_line_item'),
                    'format': self.format_tcell_left,
                },
                'width': 20,
            },
            '04_branch': {
                'header': {
                    'value': 'Branch',
                },
                'data': {
                    'value': self._render('branch'),
                    'format': self.format_tcell_left,
                },
                'width': 5,
            },
            '05_principal': {
                'header': {
                    'value': 'Principal',
                },
                'data': {
                    'value': self._render('principal'),
                    'format': self.format_tcell_left,
                },
                'width': 5,
            },
            '06_realisasi_amount': {
                'header': {
                    'value': 'Realisasi',
                },
                'data': {
                    'value': self._render('realisasi_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_realisasi_amount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '07_pv_number': {
                'header': {
                    'value': 'PV Number',
                },
                'data': {
                    'value': self._render('pv_number'),
                    'format': self.format_tcell_left,
                },
                'width': 18,
            },

            '08_payment_number': {
                'header': {
                    'value': 'Payment Number',
                },
                'data': {
                    'value': self._render('payment_number'),
                    'format': self.format_tcell_left,
                },
                'width': 18,
            },

            '09_service_inv': {
                'header': {
                    'value': 'Faktur Jasa',
                },
                'data': {
                    'value': self._render('service_inv'),
                    'format': self.format_tcell_left,
                },
                'width': 18,
            },

            '10_program': {
                'header': {
                    'value': 'Program',
                },
                'data': {
                    'value': self._render('program'),
                    'format': self.format_tcell_left,
                },
                'width': 80,
            },

            '11_coding': {
                'header': {
                    'value': 'Coding',
                },
                'data': {
                    'value': self._render('coding'),
                    'format': self.format_tcell_left,
                },
                'width': 10,
            },


        }
        report_title = 'BM Allocation  Report'
        sheet_name = 'BM Allocation'
        if objects.report_name == 'bk_alloc':
            report_title = 'BK Allocation Report'
            sheet_name = 'BK Allocation'

        ws_params = {
            'ws_name': sheet_name,  #partner.name,
            'generate_ws_method': 'bmbk_allocation_report',
            'title': report_title, #- {}'.format(partner.name),
            'wanted_list_filter': [k for k in sorted(filter_template.keys())],
            'col_specs_filter': filter_template,
            # 'wanted_list_initial': [k for k in sorted(initial_template.keys())],
            # 'col_specs_initial': initial_template,
            'wanted_list': [k for k in sorted(cl_bmbk_template.keys())],
            'col_specs': cl_bmbk_template,
        }
        return [ws_params]

    def bmbk_allocation_report(self, ws, ws_params, objects):
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(self.xls_headers['standard'])
        ws.set_footer(self.xls_footers['standard'])
        self._set_column_width(ws, ws_params)
        # Title
        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params, True)
        # Filter Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center,
            col_specs='col_specs_filter',
            wanted_list='wanted_list_filter')
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='data',
            render_space={
                'date_from': objects.date_from or '',
                'date_to': objects.date_to or '',
            },
            col_specs='col_specs_filter', wanted_list='wanted_list_filter')
        row_pos += 1

        row_pos = self._write_line(
            ws, row_pos, ws_params,
            col_specs_section='data',
            col_specs='col_specs_initial',
            wanted_list='wanted_list_initial')
        # claim bmbk Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center)
        ws.freeze_panes(row_pos, 0)
        partner_lines = objects.results #.filtered(lambda l: l.partner_id == partner)
        wanted_list = ws_params['wanted_list']

        amount_pos = '021_total_amount' in wanted_list and wanted_list.index('021_total_amount')
        alloc_pos = '022_alloc_amount' in wanted_list and wanted_list.index('022_alloc_amount')
        remain_pos = '023_remain_amount' in wanted_list and wanted_list.index('023_remain_amount')
        real_pos = '06_realisasi_amount' in wanted_list and wanted_list.index('06_realisasi_amount')





        for line in partner_lines:
            claim = line.claim_id
            cod = ''
            if claim and claim.coding:
                cod=claim.coding.upper()

            row_pos = self._write_line(
                ws, row_pos, ws_params, col_specs_section='data',
                render_space={
                    'nomor':line.nomor or 0,
                    'bank_ref_no': line.bmbk_group or '',
                    'bank_ref_date': line.bmbk_date or '',
                    'total_amount': line.total_amount or 0,
                    'alloc_amount': line.alloc_amount or 0,
                    'remain_amount': line.remain_amount or 0,
                    'pv_line_item': line.item_name or '',
                    'branch': line.branch_code or '',
                    'principal': line.partner_id.ref or '',
                    'realisasi_amount': line.real_amount or 0,
                    'pv_number': line.pv_number or '',
                    'payment_number': line.payment_number or '',
                    'service_inv': claim.service_inv or '',
                    'program': claim.remark or '',
                    'coding': cod or '',
                },
                default_format=self.format_tcell_amount_right)

        i = len(partner_lines)

        tatotal_total_amount = self.get_sum_formula(amount_pos, i, row_pos)
        tatotal_alloc_amount = self.get_sum_formula(alloc_pos, i, row_pos)
        tatotal_remain_amount = self.get_sum_formula(remain_pos, i, row_pos)
        tatotal_realisasi_amount = self.get_sum_formula(real_pos, i, row_pos)


        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='totals',
            render_space={
                'tatotal_total_amount': tatotal_total_amount,
                'tatotal_alloc_amount': tatotal_alloc_amount,
                'tatotal_remain_amount': tatotal_remain_amount,
                'tatotal_realisasi_amount': tatotal_realisasi_amount,
                },
            default_format=self.format_theader_blue_center)

class ReportClaimBalanceReportXlsx(models.AbstractModel):
    _name = 'report.bsp_claim_reports.claim_balance_report_xlsx'
    _inherit = 'base.claim.report_xlsx'

    def generate_xlsx_report(self, workbook, data, objects):
        self._define_formats(workbook)
        for ws_params in self._get_ws_params(workbook, data,objects):
            ws_name = ws_params.get('ws_name')
            ws_name = self._check_ws_name(ws_name)
            ws = workbook.add_worksheet(ws_name)
            generate_ws_method = getattr(self, ws_params['generate_ws_method'])
            # generate_ws_method(workbook, ws, ws_params, data, objects, partner)
            generate_ws_method(ws, ws_params, objects)

    def _get_ws_params(self, wb, data,objects):
        filter_template = {
             '01_date_from': {
                'header': {
                    'value': 'Date from',
                },
                'data': {
                    'value': self._render('date_from'),
                    'format': self.format_tcell_date_center,
                },
            },
            '02_date_to': {
                'header': {
                    'value': 'Date to',
                },
                'data': {
                    'value': self._render('date_to'),
                    'format': self.format_tcell_date_center,
                },
            },

        }


        cl_balance_template = {

            '00_nomor': {
                'header': {
                    'value': 'No.',
                },
                'data': {
                    'value': self._render('nomor'),
                    'format': self.format_tcell_right,
                },
                'width': 5,
            },
            '01_program': {
                'header': {
                    'value': 'Program',
                },
                'data': {
                    'value': self._render('program'),
                    'format': self.format_tcell_left,
                },
                'width': 80,
            },
            '02_branch': {
                'header': {
                    'value': 'Cabang',
                },
                'data': {
                    'value': self._render('branch'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },
            '03_claimdate': {
                'header': {
                    'value': 'Tgl.Klaim',
                },
                'data': {
                    'value': self._render('claim_date'),
                    'format': self.format_tcell_date_left,
                },
                'width': 30,
            },
            '04_noclaimbr': {
                'header': {
                    'value': 'No.Klaim Cabang',
                },
                'data': {
                    'value': self._render('no_claim'),
                    'format': self.format_tcell_left,
                },
                'width': 30,
            },
            '05_fjasa': {
                'header': {
                    'value': 'Faktur Jasa',
                },
                'data': {
                    'value': self._render('service_inv'),
                    'format': self.format_tcell_left,
                },
                'width': 20,
            },
            '06_dpp': {
                'header': {
                    'value': 'DPP',
                },
                'data': {
                    'value': self._render('claim_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_dppamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },
            '07_ppn': {
                'header': {
                    'value': 'PPN',
                },
                'data': {
                    'value': self._render('tax_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_ppnamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '08_pph': {
                'header': {
                    'value': 'PPH',
                },
                'data': {
                    'value': self._render('pph1_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_pphamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '09_netamount': {
                'header': {
                    'value': 'Jumlah',
                },
                'data': {
                    'value': self._render('net_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_netamount"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '10_realisasi': {
                'header': {
                    'value': 'Realisasi',
                },
                'data': {
                    'value': self._render('realization_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_realisasi"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '11_balance': {
                'header': {
                    'value': 'Balance',
                },
                'data': {
                    'value': self._render('balance_amount'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_balance"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '12_paymentdate': {
                'header': {
                    'value': 'Tgl.BM/BK',
                },
                'data': {
                    'value': self._render('payment_date'),
                    'format': self.format_tcell_date_left,
                },
                'width': 20,
            },
            '131_paymentappdate': {
                'header': {
                    'value': 'Tgl.Approval Principal',
                },
                'data': {
                    'value': self._render('payment_app_date'),
                    'format': self.format_tcell_date_left,
                },
                'width': 20,
            },
            '132_bankref': {
                'header': {
                    'value': 'No.Ref Bank',
                },
                'data': {
                    'value': self._render('bank_ref'),
                    'format': self.format_tcell_left,
                },
                'width': 60,
            },

            '14_pv': {
                'header': {
                    'value': 'No.Payment Voucher',
                },
                'data': {
                    'value': self._render('no_pv'),
                    'format': self.format_tcell_left,
                },
                'width': 60,
            },
            '15_alokasibalance': {
                'header': {
                    'value': 'Total BM/BK',
                },
                'data': {
                    'value': self._render('total_realisasi'),
                },
                'totals': {
                    'type': 'formula',
                    'value': self._render("tatotal_alloc"),
                    'format': self.format_theader_yellow_amount_right,
                },
                'width': 18,
            },

            '16_coding': {
                'header': {
                    'value': 'KODING',
                },
                'data': {
                    'value': self._render('coding'),
                    'format': self.format_tcell_left,
                },
                'width': 10,
            },

            '17_principal': {
                'header': {
                    'value': 'Principal',
                },
                'data': {
                    'value': self._render('principal'),
                    'format': self.format_tcell_left,
                },
                'width': 25,
            },

            '18_nocl_principal': {
                'header': {
                    'value': 'No.Klaim Principal',
                },
                'data': {
                    'value': self._render('cl_principal'),
                    'format': self.format_tcell_left,
                },
                'width': 20,
            },
        }
        report_title = 'Claim BM Recapitulation Report'
        sheet_name = 'BM Recap'
        if objects.report_name=='bk':
            report_title = 'Claim BK Recapitulation Report'
            sheet_name = 'BK Recap'

        ws_params = {
            'ws_name': sheet_name,  #partner.name,
            'generate_ws_method': '_cl_balance_report',
            'title': report_title, #- {}'.format(partner.name),
            'wanted_list_filter': [k for k in sorted(filter_template.keys())],
            'col_specs_filter': filter_template,
            # 'wanted_list_initial': [k for k in sorted(initial_template.keys())],
            # 'col_specs_initial': initial_template,
            'wanted_list': [k for k in sorted(cl_balance_template.keys())],
            'col_specs': cl_balance_template,
        }
        return [ws_params]

    def _cl_balance_report(self, ws, ws_params, objects):
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(self.xls_headers['standard'])
        ws.set_footer(self.xls_footers['standard'])
        self._set_column_width(ws, ws_params)
        # Title
        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params, True)
        # Filter Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center,
            col_specs='col_specs_filter',
            wanted_list='wanted_list_filter')
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='data',
            render_space={
                'date_from': objects.date_from or '',
                'date_to': objects.date_to or '',
            },
            col_specs='col_specs_filter', wanted_list='wanted_list_filter')
        row_pos += 1

        row_pos = self._write_line(
            ws, row_pos, ws_params,
            col_specs_section='data',
            col_specs='col_specs_initial',
            wanted_list='wanted_list_initial')
        # claim balance Table
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_blue_center)
        ws.freeze_panes(row_pos, 0)
        partner_lines = objects.results #.filtered(lambda l: l.partner_id == partner)
        wanted_list = ws_params['wanted_list']


        dpp_pos = '06_dpp' in wanted_list and wanted_list.index('06_dpp')
        ppn_pos = '07_ppn' in wanted_list and wanted_list.index('07_ppn')
        pph_pos = '08_pph' in wanted_list and wanted_list.index('08_pph')
        netamount_pos = '09_netamount' in wanted_list and wanted_list.index('09_netamount')
        real_pos = '10_realisasi' in wanted_list and wanted_list.index('10_realisasi')
        blc_pos = '11_balance' in wanted_list and wanted_list.index('11_balance')
        alloc_pos = '15_alokasibalance' in wanted_list and wanted_list.index('15_alokasibalance')

        for line in partner_lines:
            claim = line.claim_id
            cod = ''
            if claim.coding:
                cod = claim.coding.upper()
            # fclaimtotal_amount ="%s+%s+%s" % (self._rowcol_to_cell(row_pos, dpp_pos),
            #                                   self._rowcol_to_cell(row_pos, ppn_pos),
            #                                   self._rowcol_to_cell(row_pos, pph_pos))
            row_pos = self._write_line(
                ws, row_pos, ws_params, col_specs_section='data',
                render_space={
                    'nomor':line.nomor or 0,
                    'program': claim.remark or '',
                    'branch': claim.operating_unit_id.code or '',
                    'claim_date': claim.claim_date or '',
                    'no_claim': claim.name or '',
                    'service_inv': claim.service_inv or '',
                    'claim_amount': claim.claim_amount or 0,
                    'tax_amount': claim.tax_amount or 0,
                    'pph1_amount': claim.pph1_amount or 0,
                    'net_amount': claim.net_amount or 0,
                    'realization_amount': claim.realization_amount or 0,
                    'balance_amount': claim.balance_amount or 0,
                    'payment_date': claim.lpayment_date or '',
                    'payment_app_date': claim.lpayment_app_date or '',
                    'bank_ref': claim.lpayment_bankno or '',
                    'no_pv': claim.linvoices or '',
                    'total_realisasi':line.total_realisasi or 0,
                    'coding': cod or '',
                    'principal': claim.partner_id.ref or '',
                    'cl_principal': claim.claim_letter or '',
                },
                default_format=self.format_tcell_amount_right)

        i = len(partner_lines)


        tatotal_dppamount = self.get_sum_formula(dpp_pos, i, row_pos)
        tatotal_ppnamount = self.get_sum_formula(ppn_pos, i, row_pos)
        tatotal_pphamount = self.get_sum_formula(pph_pos, i, row_pos)
        tatotal_netamount = self.get_sum_formula(netamount_pos, i, row_pos)
        tatotal_realisasi = self.get_sum_formula(real_pos, i, row_pos)
        tatotal_balance = self.get_sum_formula(blc_pos, i, row_pos)
        tatotal_alloc = self.get_sum_formula(alloc_pos, i, row_pos)

        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='totals',
            render_space={

                            'tatotal_dppamount': tatotal_dppamount,
                            'tatotal_ppnamount': tatotal_ppnamount,
                            'tatotal_pphamount': tatotal_pphamount,
                            'tatotal_netamount': tatotal_netamount,
                            'tatotal_realisasi': tatotal_realisasi,
                            'tatotal_balance': tatotal_balance,
                            'tatotal_alloc': tatotal_alloc,
                          },
            default_format=self.format_theader_blue_center)