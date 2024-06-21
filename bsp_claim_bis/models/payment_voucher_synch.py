# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PVSynch(models.Model):
    _name = "bsp.payment.voucher.synch"
    _description = "Payment Voucher Synch"

    name = fields.Char(string="Synch Name", default ="Synch from  HO")
    pv_type = fields.Selection(
        [('pv', 'Payment Voucher'),
         ('bm', 'Bank Masuk'),
         ('bk', 'Bank Keluar')],
        required=True, string='Voucher Type', default='bm')

    partner_ids = fields.Many2many(
        comodel_name='res.partner',
        string='For Principals')

    fromdate = fields.Date(
        string='Date From ',
        default=fields.Date.today,
        copy=False)
    todate = fields.Date(
        string='To ',
        default=fields.Date.today,
        copy=False)
    state = fields.Selection(
        [('open', 'Open'),
         ('cancel', 'Canceled'),
         ('done', 'done')], default='open')

    lastdate = fields.Datetime(
        string='Last Updated',
        copy=False)
    line_ids = fields.One2many(
        comodel_name='bsp.payment.voucher.synch.line',
        inverse_name='pv_synch_id',
        string='Lines',
        required=False)

    type = fields.Selection([
        ('bis_to_odoo','BIS to Odoo'),
        ('odoo_to_bis','Odoo to BIS'),
    ], string='Type', default='bis_to_odoo', required=True)

    pv_ids = fields.Many2many(
        comodel_name='bsp.payment.voucher',
        string='For PVs')


    def get_last_timestamp(self, type):
        if type=='STT':
            backdays = int(self.env['ir.config_parameter'].get_param('backdays_for_update_status', default=-2))
            dts = datetime.datetime.now() + datetime.timedelta(days=backdays)
        else:
            cr = self._cr
            cr.execute("SELECT MAX(time_stamp) FROM bsp_payment_voucher where type = '%s'" % type)

            sTs = (cr.fetchone()[0])
            if sTs:
                dts = sTs
            else:
                sTs='2023-01-01 00:00:00'
                dts = datetime.datetime.strptime(sTs, "%Y-%m-%d %H:%M:%S")

        return dts

    def action_get_pv_bis(self):
        for rec in self:
            if rec.pv_type == 'pv':
                if rec.name == '_PENDINGPV_':
                    self.get_pv_bk_bis(rec.fromdate, True)
                elif rec.name == '_POSTEDPV_':
                    self.get_posted_pv_bk_bis(rec.fromdate, True)
                elif rec.name == '_POSTEDPV1_':
                    self.get_posted_pv_bk_bis(rec.fromdate, True)
                elif rec.name == '_ALLPOSTEDPV2BK_':
                    self.generate_all_posted_pv2bk()
                else:
                    self.get_pv_bk_bis(rec.fromdate, True)
            elif rec.pv_type == 'bm':
                self.get_curr_bm_hoccd(rec.fromdate, True)
            elif rec.pv_type == 'bk':
                 self.get_posted_bk_hoccd(rec.fromdate, True)


    def get_curr_bm_hoccd(self, dateFrom, isDemand):
        rec = 0
        try:
            ts = self.get_last_timestamp('bm')
            ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
            cursor, connection = ou.connect_to_bis()
            # print('koneksi: berhasil' )
            query_where = " WHERE pv.tint_transstatusid=1 and pv.dt_bankdate >= '" + dateFrom.strftime("%Y/%m/%d") + \
                          "' and pv.sint_banktokentypeid = 1 and pv.int_principalid > 0 and coa.txt_coacode in ('28.2', '28.3')  and pv.dt_lastupdate_time > '" + \
                          ts.strftime("%Y-%m-%d %H:%M:%S") + "' group by id, tp, name, principal_code, trx_date,time_stamp,coa"
            if isDemand and self.partner_ids:
                # print("rec.partner_ids :")
                query_where += ' AND pr.txt_principalcode in %s' % (str(tuple([principal.ref for principal in self.partner_ids]))).replace(',)',')')
            # print(query_where)
            query = """
                    select 
                     pv.int_banktokenid id,
                      pv.sint_banktokentypeid  tp,
                      pv.txt_banktokennumber name,
                      pr.txt_principalcode principal_code,                      
                      pv.dt_checkingaccountdate trx_date,
                      pv.dt_lastupdate_time time_stamp,
                      coa.txt_coacode coa,
                      'CURRENT' doc_state,
                      sum(pvd.curr_amount) total_amount
                    from
                      banktoken_hdr pv  inner join principal_ms pr on pv.int_principalid= pr.int_principalid 
                      inner join banktoken_dtl pvd on pv.int_banktokenid =pvd.int_banktokenid 
                      inner join coa_ms coa on coa.int_coaid = pvd.int_coaid 
                      %s                    
                """%(query_where)
            # print("Query:" + query)
            cursor.execute(query)
            datas = cursor.fetchall()
            for data in datas:
                rec += 1
                pv = self.env['bsp.payment.voucher'].search([('name', '=', data['name']),('ref_coa','=',data['coa'])], limit=1)
                tp = 'bm'
                if data['tp'] == 2:
                    tp = 'bk'
                if not pv:
                    pv = self.env['bsp.payment.voucher'].create({
                            'name': data['name'],
                            'principal_code': data['principal_code'],
                            'total_amount': data['total_amount'],
                            'type': tp,
                            'trx_date': data['trx_date'],
                            'time_stamp': data['time_stamp'],
                            'ref_document_id': data['id'],
                            'ref_coa': data['coa'],
                            'legacy_state': data['doc_state']
                        })
                    synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                            'pv_synch_id': self.id,
                            'pv_id': pv.id,
                            'synch_status': "Insert a Record PV BM",
                            'synch_date': fields.Datetime.now(),
                            'remark': pv.name + ": Synch PV BM Success",
                    })

                else:
                    # if pv.state == 'open':
                    pv.write({
                                 'name': data['name'],
                                 'principal_code': data['principal_code'],
                                 # 'total_amount': data['total_amount'],
                                 'trx_date': data['trx_date'],
                                 'ref_document_id': data['id'],
                                 'ref_coa': data['coa'],
                                 'time_stamp': data['time_stamp'],
                                 'legacy_state': data['doc_state']
                    })

                    synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                                    'pv_synch_id': self.id,
                                    'pv_id': pv.id,
                                    'synch_status': "Update a Record BM",
                                    'synch_date': fields.Datetime.now(),
                                    'remark': pv.name + " COA:" + pv.ref_coa + " ==> BM/BK Success",
                    })
                    # else:
                    #     synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                    #         'pv_synch_id': self.id,
                    #         'pv_id': pv.id,
                    #         'synch_status': "PASS Update a Record BK/BM",
                    #         'synch_date': fields.Datetime.now(),
                    #         'remark': pv.name + " COA:" + pv.ref_coa + " ==> BM PASSED ST:"+pv.state.upper()
                    #     })


            self.write({'lastdate': fields.Datetime.now(),
                           'state': 'done'
                        })
            cursor.close()
            connection.close()

        except Exception as e:
            # if type(e) in (UserError, ValidationError):
            #     raise e
            synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                    'pv_synch_id': self.id,
                    'synch_status': "Synch CN Error",
                    'synch_date': fields.Datetime.now(), # self.env.user.date_timezone() ,
                    'remark': "Error while connecting to MySQL: %s"%(e),
            })
            # raise ValidationError(_("Error while connecting to MySQL: %s"%(e)))

        self._cr.commit()
        return ("Total synchronized BMs : %s"%(rec))

    def get_pv_hoccd(self, dateFrom, dateTo, type, isDemand):
        try:
            ts = self.get_last_timestamp(type)
            itype= '1'
            if type == 'bk':
                itype = '2'
            ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
            cursor, connection = ou.connect_to_bis()
            # print('koneksi: berhasil' )
            query_where = " WHERE pv.dt_bankdate >= '" + dateFrom.strftime("%Y/%m/%d")+"' and pv.dt_bankdate <= '" + dateTo.strftime("%Y/%m/%d") + \
                          "' and pv.sint_banktokentypeid = "+itype+" and pv.int_principalid > 0 and pv.dt_lastupdate_time > '" + \
                          ts.strftime("%Y-%m-%d %H:%M:%S") + "'"
            if isDemand and self.partner_ids:
                # print("rec.partner_ids :")
                query_where += ' AND pr.txt_principalcode in %s' % (str(tuple([principal.ref for principal in self.partner_ids]))).replace(',)',')')
            # print(query_where)
            query = """
                    select 
                     pv.int_banktokenid id,
                      pv.sint_banktokentypeid  tp,
                      pv.txt_banktokennumber name,
                      pr.txt_principalcode principal_code,
                      pv.curr_amounttotal total_amount,
                      pv.dt_checkingaccountdate trx_date,
                      pv.dt_lastupdate_time time_stamp,
                      CASE 
                            WHEN pv.tint_transstatusid = 1 THEN 'CURRENT'
                            WHEN pv.tint_transstatusid = 2 THEN 'SETOR'
                            WHEN pv.tint_transstatusid = 3 THEN 'CAIR'
                            WHEN pv.tint_transstatusid = 4 THEN 'POST'
                            ELSE 'BATAL'
                      end doc_status      
                    from
                      banktoken_hdr pv  inner join principal_ms  pr on pv.int_principalid= pr.int_principalid 
                      %s                    
                """%(query_where)
            # print("Query:" + query)
            cursor.execute(query)
            datas = cursor.fetchall()
            for data in datas:
                pv = self.env['bsp.payment.voucher'].search([('name', '=', data['name'])], limit=1)
                tp = 'bm'
                if data['tp'] == 2:
                    tp = 'bk'
                if not pv:
                    pv = self.env['bsp.payment.voucher'].create({
                            'name': data['name'],
                            'principal_code': data['principal_code'],
                            'total_amount': data['total_amount'],
                            'type': tp,
                            'trx_date': data['trx_date'],
                            'time_stamp': data['time_stamp'],
                            'ref_document_id': data['id'],
                            'legacy_state': data['doc_status']
                        })
                    synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                            'pv_synch_id': self.id,
                            'pv_id': pv.id,
                            'synch_status': "Insert a Record PV BM",
                            'synch_date': fields.Datetime.now(),
                            'remark': pv.name + ": Synch PV BM Success",
                    })

                else:
                    pv.write({
                             'total_amount': data['total_amount'],
                              'trx_date': data['trx_date'],
                             'time_stamp': data['time_stamp'],
                             'legacy_state': data['doc_status']
                    })

                    synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                                'pv_synch_id': self.id,
                                'pv_id': pv.id,
                                'synch_status':"Update a Record BK/BM",
                                'synch_date': fields.Datetime.now(),
                                'remark': pv.name + ":BM/BK Success",
                    })


            self.write({'lastdate': fields.Datetime.now(),
                           'state': 'done'
                        })
            cursor.close()
            connection.close()

        except Exception as e:
            # if type(e) in (UserError, ValidationError):
            #     raise e
            synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                    'pv_synch_id': self.id,
                    'synch_status': "Synch CN Error",
                    'synch_date': fields.Datetime.now(),
                    'remark': "Error while connecting to MySQL: %s"%(e),
            })
            # raise ValidationError(_("Error while connecting to MySQL: %s"%(e)))

        self._cr.commit()


    def update_doc_status_hoccd(self):
        rec = 0
        try:
            ts = self.get_last_timestamp('STT')
            ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
            cursor, connection = ou.connect_to_bis()
            # print('koneksi: berhasil' )
            query_where = " WHERE pv.int_principalid > 0 and pv.dt_lastupdate_time > '" + ts.strftime("%Y-%m-%d %H:%M:%S") + "'"
            # if isDemand and self.partner_ids:
            #     # print("rec.partner_ids :")
            #     query_where += ' AND pr.txt_principalcode in %s' % (str(tuple([principal.ref for principal in self.partner_ids]))).replace(',)',')')
            # print(query_where)
            query = """
                    select 
                     pv.int_banktokenid id,
                     pv.dt_lastupdate_time time_stamp,
                     CASE 
                            WHEN pv.tint_transstatusid = 1 THEN 'CURRENT'
                            WHEN pv.tint_transstatusid = 2 THEN 'SETOR'
                            WHEN pv.tint_transstatusid = 3 THEN 'CAIR'
                            WHEN pv.tint_transstatusid = 4 THEN 'POST'
                            ELSE 'BATAL'
                      end doc_status      
                    from
                      banktoken_hdr pv %s                    
                """%(query_where)

            cursor.execute(query)
            datas = cursor.fetchall()
            for data in datas:
                pv = self.env['bsp.payment.voucher'].search(['&','&','|',('legacy_state','!=',data['doc_status']),('legacy_state','=',False),('ref_document_id', '=', data['id']),('type','in',('bm','bk'))], limit=1)

                if pv:
                    rec += 1
                    pv.write({
                             'time_stamp': data['time_stamp'],
                             'legacy_state': data['doc_status']
                    })

                    synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                                'pv_synch_id': self.id,
                                'pv_id': pv.id,
                                'synch_status':"Update Status Record BK/BM",
                                'synch_date': fields.Datetime.now(),
                                'remark': pv.name + ":Update status BM/BK Success",
                    })
                    # print("Update BMBK Status : %s ==> %s " %(pv.name,data['doc_status']))

            self.write({'lastdate': fields.Datetime.now(),
                           'state': 'done'
                        })
            cursor.close()
            connection.close()
            return ("Total BM/BK Status updated : %s" % (rec))

        except Exception as e:
            # if type(e) in (UserError, ValidationError):
            #     raise e
            synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                    'pv_synch_id': self.id,
                    'synch_status': "Update BM/BK status Error",
                    'synch_date': fields.Datetime.now(),
                    'remark': "Error while connecting to MySQL: %s"%(e),
            })
            # raise ValidationError(_("Error while connecting to MySQL: %s"%(e)))

        # self._cr.commit()

    def get_pv_bk_bis(self, dateFrom, isDemand):
            pvno=''
            rec=0
            try:
                ts = self.get_last_timestamp('pv')
                ou = self.env['operating.unit'].search([('code', '=', 'BISAP')], limit=1)
                cursor, connection = ou.connect_to_bis()
                # print('koneksi: berhasil' )
                query_where = " WHERE pv.Tgl_PV >= '" + dateFrom.strftime("%Y/%m/%d") + \
                              "' and pv.Status_PV in ('PENDING','POSTED') and pv.Time_Stamp > '" + ts.strftime("%Y-%m-%d %H:%M:%S") + "'"

                if isDemand and self.partner_ids:
                    # print("rec.partner_ids :")
                    query_where += ' AND pv.Kode_Principal in %s' % (
                        str(tuple([principal.ref for principal in self.partner_ids]))).replace(',)', ')')
                # print(query_where)
                query = """
                        select 
                          pv.No_PV name,
                          pv.Kode_Principal principal_code,
                          ufn_pv_bk_amount(pv.No_PV) total_amount,
                          pv.Tgl_PV trx_date,
                          pv.Status_PV state,
                          pv.Time_Stamp time_stamp
                        from
                          pc_payment_voucher pv %s                    
                    """ % (query_where)
                print("Query:" + query)
                cursor.execute(query)
                datas = cursor.fetchall()
                for data in datas:
                    rec +=1
                    stt = 'open'
                    if data['state'] == 'POSTED':
                        stt = 'post'
                    elif data['state'] == 'PENDING':
                        stt = 'PENDING'
                    pv = self.env['bsp.payment.voucher'].search([('name', '=', data['name'])], limit=1)
                    if not pv:
                        pvno = data['name']
                        alloc = data['total_amount']
                        if stt == 'PENDING':
                            stt = 'open'
                            alloc=0
                        pv = self.env['bsp.payment.voucher'].create({
                            'name': data['name'],
                            'principal_code': data['principal_code'],
                            'total_amount': data['total_amount'],
                            'type': "pv",
                            'trx_date': data['trx_date'],
                            'state': stt,
                            'time_stamp': data['time_stamp'],
                            'legacy_state': data['state']
                        })
                        synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                            'pv_synch_id': self.id,
                            'pv_id': pv.id,
                            'synch_status': "Insert a Record PV " + stt.upper(),
                            'synch_date': fields.Datetime.now(),
                            'remark': pv.name + ": Synch PV AP Success",
                        })

                    else:
                        # if not pv.ref_hodocument:
                        pvno = pv.name
                        if stt != 'PENDING':
                            pv.write({
                                'total_amount': data['total_amount'],
                                'alloc_amount': data['total_amount'],
                                'trx_date': data['trx_date'],
                                'state': stt,
                                'time_stamp': data['time_stamp'],
                                'legacy_state': data['state']
                            })
                        else:
                            pv.write({
                                'total_amount': data['total_amount'],
                                'trx_date': data['trx_date'],
                                'time_stamp': data['time_stamp'],
                                'legacy_state': data['state']
                            })

                        synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                            'pv_synch_id': self.id,
                            'pv_id': pv.id,
                            'synch_status': "Update a Record PV "+stt.upper(),
                            'synch_date': fields.Datetime.now(),
                            'remark': pv.name + ": BK Success",
                        })

                self.write({'lastdate': fields.Datetime.now(),
                            'state': 'done'
                            })
                cursor.close()
                connection.close()

            except Exception as e:
                # if type(e) in (UserError, ValidationError):
                #     raise e
                synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                    'pv_synch_id': self.id,
                    'synch_status': "Synch PV AP Error",
                    'synch_date': fields.Datetime.now(),
                    'remark': pvno + ": Error while connecting to MySQL: %s" % (e),
                })
                # raise ValidationError(_("Error while connecting to MySQL: %s" % (e)))

            self._cr.commit()
            return ("Total synchronized PVs : %s" % (rec))

    def update_pv_status_from_bis(self):
        pvno = ''
        rec = 0
        try:
            ts = self.get_last_timestamp('STT')
            ou = self.env['operating.unit'].search([('code', '=', 'BISAP')], limit=1)
            cursor, connection = ou.connect_to_bis()
            # print('koneksi: berhasil' )
            query_where = " WHERE pv.Time_Stamp > '" + ts.strftime("%Y-%m-%d %H:%M:%S") + "'"

            # if isDemand and self.partner_ids:
            #     # print("rec.partner_ids :")
            #     query_where += ' AND pv.Kode_Principal in %s' % (
            #         str(tuple([principal.ref for principal in self.partner_ids]))).replace(',)', ')')
            # # print(query_where)
            query = """
                           select 
                             pv.No_PV name,
                             pv.Status_PV state,
                             pv.Time_Stamp time_stamp
                           from
                             pc_payment_voucher pv %s                    
                       """ % (query_where)
            # print("Query:" + query)
            cursor.execute(query)
            datas = cursor.fetchall()
            for data in datas:

                # pv = self.env['bsp.payment.voucher'].search([('name', '=', data['name'])], limit=1)
                pv = self.env['bsp.payment.voucher'].search(
                    ['&', '&', '|', ('legacy_state', '!=', data['state']), ('legacy_state', '=', False),
                     ('name', '=', data['name']), ('type', '=', 'pv')], limit=1)

                stt ='NULL'
                if pv:
                    rec += 1
                    if pv.legacy_state:
                        stt = pv.legacy_state
                    pv.write({
                        'time_stamp': data['time_stamp'],
                        'legacy_state': data['state']
                    })

                    synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                        'pv_synch_id': self.id,
                        'pv_id': pv.id,
                        'synch_status': "Update status  PV from "+ stt + ' ==> ' + data['state'],
                        'synch_date': fields.Datetime.now(),
                        'remark': pv.name + ": status update Success",
                    })

            self.write({'lastdate': fields.Datetime.now(),
                        'state': 'done'
                        })
            cursor.close()
            connection.close()
            return ("Total synchronized PVs : %s" % (rec))

        except Exception as e:
            # if type(e) in (UserError, ValidationError):
            #     raise e
            synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                'pv_synch_id': self.id,
                'synch_status': "Update status PV AP Error",
                'synch_date': fields.Datetime.now(),
                'remark': "Error while connecting to MySQL: %s" % (e),
            })
            # raise ValidationError(_("Error while connecting to MySQL: %s" % (e)))


    def InsertBK_HOCCD(self,data,pvID,data_detail,data_dn,data_bayar,ondemand):
        strerr = ''
        try:
            nama_bank = data['nama_bank']
            if nama_bank == None:
                if not ondemand:
                    synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                        'pv_synch_id': self.id,
                        'pv_id': pvID.id,
                        'synch_status': "create  BK Error",
                        'synch_date': fields.Datetime.now(),
                        'remark': "Error while connecting to MySQL: Bank Name: Not defined yet "
                    })
                return 'Generate BK Error Bank reference not defined yet'

            nama_bank = nama_bank.replace("\r\n", "")
            rek_bank = data['rek_bank']
            ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
            cr, conn = ou.connect_to_bis()

            cr.execute("select int_banktokenid bk_id, txt_banktokennumber bk_no, tint_transstatusid stt from banktoken_hdr where txt_bankacctokennumber='" + data["name"] + "';")
            pv_dict = cr.fetchone()
            if pv_dict:
                stt = pv_dict.get("stt", 0)
                stt_name = 'BATAL'
                if stt == 1:
                    stt_name = 'CURRENT'
                elif stt == 2:
                    stt_name = 'SETOR'
                elif stt == 3:
                    stt_name = 'CAIR'
                elif stt == 4:
                    stt_name = 'POST'
                else:
                    stt_name = 'BATAL'
                if not ondemand:
                    synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                        'pv_synch_id': self.id,
                        'synch_status': "Synch BK Warning",
                        'synch_date': fields.Datetime.now(), #self.env.user.date_timezone(format='string'),
                        'remark': "BK is exist on doc number: %s ID:%s" % (pv_dict.get("bk_no", ""), pv_dict.get("bk_id", 0))
                    })
                    pvID.write({
                        'ref_document_id': pv_dict.get("bk_id", 0),
                        'ref_hodocument': pv_dict.get("bk_no", ""),
                        'legacy_state': stt_name
                    })
                else:
                    pvID.write({
                        'ref_document_id': pv_dict.get("bk_id", 0),
                        'ref_hodocument': pv_dict.get("bk_no", ""),
                        'legacy_state': stt_name
                    })
                    return "BK is exist on doc number: %s ID:%s" % (pv_dict.get("bk_no", ""), pvID.ref_document_id)

            else:
                cr.execute("select coalesce(sint_bankid,0) bank_id from bank_ms where upper(txt_bankname)='"+nama_bank.upper()+"'")
                bank_dict = cr.fetchone()
                bank_id = 0
                # return "Bank " + nama_bank.upper() +'Dict:'+str(bank_dict)
                if bank_dict:
                   bank_id = bank_dict.get("bank_id",0)

                tamount = 0
                args = [
                    'BK',
                    'AP',
                    data["principal_code"].upper(),
                    data["name"].upper(),  #PV number from BIS AP
                    datetime.datetime.now().month,
                    datetime.datetime.now().year,
                    data["warkatnumber"],
                    data["warkatduedate"],
                    data["warkatstore"],
                    data["total_amount"]
                ]

                cr.callproc('usp_insert_banktoken_header', args)
                results = cr.stored_results()
                datas = []
                for result in results:
                    datas += result.fetchall()

                if not datas:
                    return "Generate BK HOCCD Insert FAIL"+ str(datas)
                # rec = cr.fetchall()
                strerr +=' usp_insert_banktoken_header'
                if data_detail:
                    for dtl in data_detail:
                        tamount += round(dtl["Total_Faktur"],2)
                        detArg=[
                            datas[0][0],
                            dtl["No_Faktur"],
                            dtl["Total_Faktur"],
                            dtl["Kode_Cabang"]
                        ]
                        cr.callproc('usp_insert_banktoken_detail', detArg)
                strerr += ' usp_insert_banktoken_detail'
                if data_dn:
                    for dn in data_dn:
                        branchcode=dn["No_Dokumen"][4:3]
                        tamount -= round(dn["Nominal_Biaya"],2)
                        dnArg=[
                            datas[0][0],
                            branchcode,
                            dn["Jenis_Biaya"],
                            dn["No_Dokumen"],
                            dn["No_Referensi"],
                            '',
                            0,
                            dn["Nominal_Biaya"],
                            dn["Jenis_Biaya"],
                            'Z','',
                            datetime.datetime.now().strftime("%Y-%m-%d"),
                            0
                        ]
                        cr.callproc('usp_insert_banktoken_bayar', dnArg)
                strerr += ' usp_insert_banktoken_bayar'
                if data_bayar:
                    for byr in data_bayar:
                        tamount -= round(byr["Nominal_Biaya"],2)
                        byrArg=[
                            datas[0][0],
                            byr["Kode_Cabang"],
                            byr["Jenis_Biaya"],
                            byr["No_Dokumen"],
                            byr["No_Referensi"],
                            byr["No_FakturJasa"],
                            byr["PPhBSP"],
                            byr["Nominal_Biaya"],
                            byr["Keterangan"],
                            byr["Koding"],'',
                            datetime.datetime.now().strftime("%Y-%m-%d"),
                            0
                        ]
                        cr.callproc('usp_insert_banktoken_bayar', byrArg)
                strerr += 'usp_insert_banktoken_bayar'
                qupdate = "Update banktoken_dtl set txt_accountnumber='" + rek_bank + "', sint_bankid=" \
                          + str(bank_id) + " where int_banktokenid="+datas[0][0]
                cr.execute(qupdate)
                strerr += 'Update banktoken_dtl set txt_accountnumber'
                qsumbiaya = "select sum(curr_amount) totBiaya from banktoken_dtl where int_banktokenid=" + datas[0][0]
                cr.execute(qsumbiaya)
                totBiayaDict = cr.fetchone()
                strerr += str(datas)
                totBiaya=0
                if totBiayaDict:
                    totBiaya = totBiayaDict.get("totBiaya", 0)

                qupdatetotal = "Update banktoken_hdr set curr_amounttotal = " + str(totBiaya) + " where int_banktokenid=" + datas[0][0]
                cr.execute(qupdatetotal)
                conn.commit()

                cr.close()
                conn.close()
                if datas:
                    pvID.write({
                        'ref_document_id': datas[0][0],
                        'ref_hodocument': datas[0][1]
                    })
                    if not ondemand:
                        synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                            'pv_synch_id': self.id,
                            'pv_id': pvID.id,
                            'synch_status': "Update a Record PV BK",
                            'synch_date': fields.Datetime.now(),
                            'remark': 'ID:' + datas[0][0] + ' BK#: ' + datas[0][1] + ": HOCCD Insert Success",
                        })
                    return 'Generate BK Success ID:' + datas[0][0] + ' BK#: ' + datas[0][1]
                else:
                    return "Generate BK HOCCD Insert FAIL"
        except Exception as e:
            # if type(e) in (UserError, ValidationError):
            #     raise e
            if not ondemand:
                synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                    'pv_synch_id': self.id,
                    'pv_id': pvID.id,
                    'synch_status': "create  BK Error",
                    'synch_date': fields.Datetime.now(),
                    'remark': "Error while connecting to MySQL: %s" % (e),
                })
            else:
                raise ValidationError(_("Error while connecting to MySQL: %s" % (strerr)))


    def UpdateBK_HOCCD(self,data,pvID,data_detail,data_dn,data_bayar,ondemand):
        strerr = ''
        try:
            nama_bank = data['nama_bank']
            if nama_bank == None:
                if not ondemand:
                    synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                        'pv_synch_id': self.id,
                        'pv_id': pvID.id,
                        'synch_status': "create  BK Error",
                        'synch_date': fields.Datetime.now(),
                        'remark': "Error while connecting to MySQL: Bank Name: Not defined yet "
                    })
                return 'Generate BK Error Bank reference not defined yet'

            nama_bank = nama_bank.replace("\r\n", "")
            rek_bank = data['rek_bank']
            ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
            cr, conn = ou.connect_to_bis()

            cr.execute("select int_banktokenid bk_id, txt_banktokennumber bk_no from banktoken_hdr where tint_transstatusid = 1 and int_banktokenid=" + str(pvID.ref_document_id))
            pv_dict = cr.fetchone()
            if pv_dict:
                cr.execute("delete from banktoken_dtl where int_banktokenid ="+str(pvID.ref_document_id))
                tamount = 0
                if data_detail:
                    for dtl in data_detail:
                        tamount += round(dtl["Total_Faktur"],2)
                        detArg=[
                            pvID.ref_document_id,
                            dtl["No_Faktur"],
                            dtl["Total_Faktur"],
                            dtl["Kode_Cabang"]
                        ]
                        cr.callproc('usp_insert_banktoken_detail', detArg)
                strerr += 'usp_insert_banktoken_detail'
                if data_dn:
                    for dn in data_dn:
                        branchcode=dn["No_Dokumen"][4:3]
                        tamount -= round(dn["Nominal_Biaya"],2)
                        dnArg=[
                            pvID.ref_document_id,
                            branchcode,
                            dn["Jenis_Biaya"],
                            dn["No_Dokumen"],
                            dn["No_Referensi"],
                            '',
                            0,
                            dn["Nominal_Biaya"],
                            dn["Jenis_Biaya"],
                            'Z','',
                            datetime.datetime.now().strftime("%Y-%m-%d"),
                            0
                        ]
                        cr.callproc('usp_insert_banktoken_bayar', dnArg)
                strerr += 'usp_insert_banktoken_bayar'
                if data_bayar:
                    for byr in data_bayar:
                        tamount -= round(byr["Nominal_Biaya"],2)
                        byrArg=[
                            pvID.ref_document_id,
                            byr["Kode_Cabang"],
                            byr["Jenis_Biaya"],
                            byr["No_Dokumen"],
                            byr["No_Referensi"],
                            byr["No_FakturJasa"],
                            byr["PPhBSP"],
                            byr["Nominal_Biaya"],
                            byr["Keterangan"],
                            byr["Koding"],'',
                            datetime.datetime.now().strftime("%Y-%m-%d"),
                            0
                        ]
                        cr.callproc('usp_insert_banktoken_bayar', byrArg)
                strerr += 'usp_insert_banktoken_bayar'

                cr.execute(
                    "select coalesce(sint_bankid,0) bank_id from bank_ms where upper(txt_bankname)='" + nama_bank.upper() + "'")
                bank_dict = cr.fetchone()
                bank_id = 0
                # return "Bank " + nama_bank.upper() +'Dict:'+str(bank_dict)
                if bank_dict:
                    bank_id = bank_dict.get("bank_id", 0)

                qupdate = "Update banktoken_dtl set txt_accountnumber='" + rek_bank + "', sint_bankid=" \
                          + str(bank_id) + " where int_banktokenid="+str(pvID.ref_document_id)
                cr.execute(qupdate)

                qsumbiaya = "select sum(curr_amount) totBiaya from banktoken_dtl where int_banktokenid=" + str(pvID.ref_document_id)
                cr.execute(qsumbiaya)
                totBiayaDict = cr.fetchone()

                totBiaya=0
                if totBiayaDict:
                    totBiaya = totBiayaDict.get("totBiaya", 0)

                qupdatetotal = "Update banktoken_hdr set curr_amounttotal = " + str(totBiaya) + " where int_banktokenid=" + str(pvID.ref_document_id)
                cr.execute(qupdatetotal)
                conn.commit()

                cr.close()
                conn.close()
                if pvID:
                    if not ondemand:
                        synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                            'pv_synch_id': self.id,
                            'pv_id': pvID.id,
                            'synch_status': "Regenerate a Record PV BK",
                            'synch_date': fields.Datetime.now(),
                            'remark': 'ID:' + str(pvID.ref_document_id) + ' BK#: ' + pvID.ref_hodocument + ": HOCCD Regenerate Success",
                        })
                    return 'Re-Generate BK Success ID:' + str(pvID.ref_document_id) + ' BK#: ' + pvID.ref_hodocument
                else:
                    return "Re-Generate BK HOCCD Insert FAIL"
            else:
                return 'Re-Generate BK FAIL CURRENT BK#: ' + pvID.ref_hodocument + ' NOT FOUND!'
        except Exception as e:
            # if type(e) in (UserError, ValidationError):
            #     raise e
            if not ondemand:
                synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                    'pv_synch_id': self.id,
                    'pv_id': pvID.id,
                    'synch_status': "create  BK Error",
                    'synch_date': fields.Datetime.now(),
                    'remark': "Error while connecting to MySQL: %s" % (e),
                })
            else:
                raise ValidationError(_("Error while connecting to MySQL: %s" % (strerr)))


    def get_posted_pv_bk_bis(self, dateFrom, isDemand):
            try:
                ts = self.get_last_timestamp('pv')

                # # SYNCH ONLY POSTED PV AP used on Odoo claim
                pvs = self.env['bsp.payment.voucher'].search_read([('type', '=', 'pv'),
                                                              ('state', '=', 'alloc'),
                                                              ('alloc_amount', '>', '0')], ['name'])
                if not pvs:
                   print ("Posted PV not found")
                   return False

                strpv = str(tuple([p.get("name",'') for p in pvs])).replace(',)', ')')

                ou = self.env['operating.unit'].search([('code', '=', 'BISAP')], limit=1)
                cursor, connection = ou.connect_to_bis()
                # print('koneksi: berhasil' )
                query_where = " WHERE pv.Tgl_PV >= '" + dateFrom.strftime(
                    "%Y/%m/%d") + "' and pv.Status_PV='POSTED' and pv.Time_Stamp > '" + \
                              ts.strftime("%Y-%m-%d %H:%M:%S") + "' AND pv.No_PV in %s" % strpv


                # # SYNCH All POSTED PV AP
                # ou = self.env['operating.unit'].search([('code', '=', 'BISAP')], limit=1)
                # cursor, connection = ou.connect_to_bis()
                # # print('koneksi: berhasil' )
                # query_where = " WHERE pv.Tgl_PV >= '" + dateFrom.strftime(
                #     "%Y/%m/%d") + "' and pv.Status_PV='POSTED' and pv.Time_Stamp > '" + \
                #               ts.strftime("%Y-%m-%d %H:%M:%S") + "'"

                if isDemand and self.partner_ids:
                    # print("rec.partner_ids :")
                    query_where += ' AND pv.Kode_Principal in %s' % (
                        str(tuple([principal.ref for principal in self.partner_ids]))).replace(',)', ')')

                if isDemand and self.pv_ids:
                    # print("rec.partner_ids :")
                    query_where += ' AND pv.No_PV in %s' % (
                        str(tuple([pv.name for pv in self.pv_ids]))).replace(',)', ')')
                # print(query_where)
                query = """
                        select 
                          pv.No_PV name,
                          pv.Kode_Principal principal_code,                          
                          ufn_pv_bk_amount(pv.No_PV) total_amount,
                          pv.Tgl_PV trx_date,
                          pv.Kode_Bank bank_code,
                          pv.No_CekBG warkatnumber,
                          pv.Tanggal_CekBG warkatstore,
                          pv.Jatuh_Tempo_CekBG warkatduedate,
                          pv.Time_Stamp time_stamp,
                          rpt.LeftStr nama_bank,
                          rpt.CenterStr rek_bank
                        from
                          pc_payment_voucher pv 
                          left join ms_report_ttd rpt 
                          on rpt.keyvalue = pv.Kode_Principal and rpt.reportName='BankKeluarAccNumber' %s                    
                    """ % (query_where)
                # print("Query:" + query)
                cursor.execute(query)
                datas = cursor.fetchall()
                for data in datas:

                    # get PV Detail
                    query_detail = f"""
                    SELECT                       
                      pvd.`No_Faktur`,
                      pvd.`Total_Faktur`,
                      pby.`Kode_Cabang`
                    FROM
                      `pc_payment_voucher_detail` pvd 
                      join `pc_bayar` pby on pvd.`No_Faktur` = pby.`No_Faktur`
                    WHERE pvd.`No_PV`= '{data["name"]}'
                    """
                    cursor.execute(query_detail)
                    data_details = cursor.fetchall()

                    query_dn = f"""
                                        SELECT  
                                          pvd.`Keterangan_DN` Jenis_Biaya,                  
                                          pvd.`No_DN` No_Dokumen,
                                          pvd.`No_Referensi`,
                                          pvd.`Total_DN` Nominal_Biaya                                       
                                        FROM
                                          `pc_payment_voucher_dn` pvd 
                                        WHERE pvd.`No_PV`= '{data["name"]}'
                                        """
                    cursor.execute(query_dn)
                    query_dn = cursor.fetchall()

                    query_bayar = f"""
                    SELECT 
                      `Kode_Cabang`,
                      `Jenis_Biaya`,
                      `No_Dokumen`,
                      `No_Referensi`,
                      `No_FakturJasa`,                      
                      `PPhBSP`,
                      `Nominal_Biaya`,
                      `Keterangan`,
                      `Koding` 
                    FROM
                      `pc_payment_voucher_bayar` 
                    WHERE No_PV = '{data["name"]}'
                    """
                    cursor.execute(query_bayar)
                    data_bayar = cursor.fetchall()


                    pv = self.env['bsp.payment.voucher'].search([('name', '=', data['name'])], limit=1)
                    if not pv:
                        pv = self.env['bsp.payment.voucher'].create({
                            'name': data['name'],
                            'principal_code': data['principal_code'],
                            'total_amount': data['total_amount'],
                            'type': "pv",
                            'trx_date': data['trx_date'],
                            'time_stamp': data['time_stamp'],
                            'state': 'post',
                            'legacy_state': 'POSTED'
                        })
                        synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                            'pv_synch_id': self.id,
                            'pv_id': pv.id,
                            'synch_status': "Insert a Record PV BK",
                            'synch_date': fields.Datetime.now(),
                            'remark': pv.name + ": Synch PV AP Success",
                        })

                    else:
                        pv.write({
                            'state': 'post',
                            'trx_date': data['trx_date'],
                            'time_stamp': data['time_stamp'],
                            'legacy_state': 'POSTED',
                        })

                        synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                            'pv_synch_id': self.id,
                            'pv_id': pv.id,
                            'synch_status': "Update a Record PV BK",
                            'synch_date': fields.Datetime.now(),
                            'remark': pv.name + ": BK Success",
                        })

                    ret = self.InsertBK_HOCCD(data, pv, data_details,query_dn, data_bayar,False)

                self.write({'lastdate': fields.Datetime.now(),
                            'state': 'done'
                            })
                cursor.close()
                connection.close()

            except Exception as e:
                # if type(e) in (UserError, ValidationError):
                #     raise e
                synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                    'pv_synch_id': self.id,
                    'synch_status': "Synch PB BK Error",
                    'synch_date': fields.Datetime.now(),
                    'remark': "Error while connecting to MySQL: %s" % (e),
                })
                # raise ValidationError(_("Error while connecting to MySQL: %s" % (e)))

            self._cr.commit()

    def generate_all_posted_pv2bk(self):
        global connection, cursor
        rec = 0
        try:
            posted_pvs = self.env['bsp.payment.voucher'].search([('state', '=', 'post'),('ref_document_id','=', False),('trx_date','>','2023-09-10')])
            ou = self.env['operating.unit'].search([('code', '=', 'BISAP')], limit=1)
            cursor, connection = ou.connect_to_bis()
            query0 = """
                        select 
                            pv.No_PV name,
                            pv.Kode_Principal principal_code,                          
                            ufn_pv_bk_amount(pv.No_PV) total_amount,
                            pv.Tgl_PV trx_date,
                            pv.Kode_Bank bank_code,
                            pv.No_CekBG warkatnumber,
                            pv.Tanggal_CekBG warkatstore,
                            pv.Jatuh_Tempo_CekBG warkatduedate,
                            pv.Time_Stamp time_stamp,
                            rpt.LeftStr nama_bank,
                            rpt.CenterStr rek_bank
                        from
                            pc_payment_voucher pv 
                            left join ms_report_ttd rpt 
                            on rpt.keyvalue = pv.Kode_Principal and rpt.reportName='BankKeluarAccNumber' 
                            WHERE pv.Status_PV='POSTED' and pv.No_PV="""
            for pv in posted_pvs:
                rec += 1
                query = f"""{query0}'{pv.name}'"""
                cursor.execute(query)
                datas = cursor.fetchall()
                for data in datas:
                    # get PV Detail
                    query_detail = f"""
                                    SELECT                       
                                      pvd.`No_Faktur`,
                                      pvd.`Total_Faktur`,
                                      pby.`Kode_Cabang`
                                    FROM
                                      `pc_payment_voucher_detail` pvd 
                                      join `pc_bayar` pby on pvd.`No_Faktur` = pby.`No_Faktur`
                                    WHERE pvd.`No_PV`= '{data["name"]}'"""
                    cursor.execute(query_detail)
                    data_details = cursor.fetchall()

                    # get PV Return
                    query_dn = f"""
                                    SELECT  
                                        pvd.`Keterangan_DN` Jenis_Biaya,                  
                                        pvd.`No_DN` No_Dokumen,
                                        pvd.`No_Referensi`,
                                        pvd.`Total_DN` Nominal_Biaya                                       
                                    FROM
                                        `pc_payment_voucher_dn` pvd 
                                    WHERE pvd.`No_PV`= '{data["name"]}'"""
                    cursor.execute(query_dn)
                    query_dn = cursor.fetchall()

                    # get PV Return
                    query_bayar = f"""
                                    SELECT 
                                      `Kode_Cabang`,
                                      `Jenis_Biaya`,
                                      `No_Dokumen`,
                                      `No_Referensi`,
                                      `No_FakturJasa`,                      
                                      `PPhBSP`,
                                      `Nominal_Biaya`,
                                      `Keterangan`,
                                      `Koding` 
                                    FROM
                                      `pc_payment_voucher_bayar` 
                                    WHERE No_PV = '{data["name"]}'
                                    """
                    cursor.execute(query_bayar)
                    data_bayar = cursor.fetchall()

                    ret = self.InsertBK_HOCCD(data, pv, data_details, query_dn, data_bayar, False)
            # connection.commit()
            cursor.close()
            connection.close()
        except Exception as e:
            cursor.close()
            connection.close()
            synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                'pv_synch_id': self.id,
                'synch_status': "Synch PB BK Error",
                'synch_date': fields.Datetime.now(),
                'remark': "Error while connecting to MySQL: %s" % (e),
            })
        self._cr.commit()
        return ("Total synchronized BKs : %s" % (rec))

    def update_bknumber_by_hoccd(self, ondemand):
        global conn, cr
        rec = 0
        try:
            posted_pvs = self.env['bsp.payment.voucher'].search([('state', '=', 'post'),('ref_document_id','!=', False),('ref_hodocument','ilike','AP/BK/PST')])
            if posted_pvs:
                ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
                cr, conn = ou.connect_to_bis()
                for pv in posted_pvs:
                    cr.execute("select int_banktokenid bk_id, txt_banktokennumber bk_no from banktoken_hdr where int_banktokenid="+str(pv.ref_document_id))
                    pv_dict = cr.fetchone()
                    if pv_dict:
                       nobk = pv_dict.get("bk_no", "")
                       if nobk != pv.ref_hodocument:
                           rec += 1
                           if not ondemand:
                              synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                                'pv_synch_id': self.id,
                                'synch_status': "Synch BK Number Updated",
                                'synch_date': fields.Datetime.now(),  # self.env.user.date_timezone(format='string'),
                                'remark': "BK number changed: %s to %s" % (pv.ref_hodocument,nobk)
                                })

                           pv.write({'ref_hodocument': nobk})
                conn.close()
                cr.close()
                # self._cr.commit()
                return ("Total synchronized BKs : %s" % (rec))
        except Exception as e:
            # if type(e) in (UserError, ValidationError):
            #     raise e
            conn.close()
            cr.close()
            synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                'pv_synch_id': self.id,
                'synch_status': "Synch BK Update Error",
                'synch_date': fields.Datetime.now(),
                'remark': "Error while connecting to MySQL: %s" % (e),
            })

    def update_bm_coa_amount(self):
        global conn, cr
        rec = 0
        try:
            bms = self.env['bsp.payment.voucher'].search([('type', '=', 'bm'),('state', '!=', 'open'),('ref_document_id','!=', False)])
            if bms:
                ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
                cr, conn = ou.connect_to_bis()
                for bm in bms:

                    queryCOATitipan = "SELECT int_banktokendetailid idUMP FROM  banktoken_dtl WHERE int_banktokenid = " + str(bm.ref_document_id) + \
                                      " AND int_coaid IN (SELECT int_coaid FROM coa_ms WHERE txt_coacode = '" + bm.ref_coa + "') limit 1"
                    self.env.user.log_info(queryCOATitipan)
                    cr.execute(queryCOATitipan)
                    record = cr.fetchone()
                    if record:
                        idUMP = record["idUMP"]
                    else:
                        continue
                    rec += 1
                    dRemain = bm.total_amount - bm._calc_send_alloc_amount()
                    # dRemain = bm.total_amount - bm.get_allocated_amount_send()
                    queryCOATitipan = "update banktoken_dtl set curr_amount = round(" + str(dRemain) + ",2)  where  int_banktokendetailid = " + str(idUMP)
                    self.env.user.log_info(queryCOATitipan)
                    cr.execute(queryCOATitipan)

                conn.commit()
                conn.close()
                cr.close()
                return ("Total synchronized BKs : %s" % (rec))
        except Exception as e:
            conn.close()
            cr.close()
            synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                'pv_synch_id': self.id,
                'synch_status': "Update Remain ump Error",
                'synch_date': fields.Datetime.now(),
                'remark': "Error while connecting to MySQL: %s" % (e),
            })






    def generate_bk_by_posted_pv_bis(self, pv, isInsert):
            q_str =''
            try:
                ou = self.env['operating.unit'].search([('code', '=', 'BISAP')], limit=1)
                cursor, connection = ou.connect_to_bis()
                # print('koneksi: berhasil' )
                # query_where = " WHERE pv.Status_PV='POSTED' and pv.No_PV='" +pv.name+"'"

                query = f"""
                        select 
                          pv.No_PV name,
                          pv.Kode_Principal principal_code,                          
                          ufn_pv_bk_amount(pv.No_PV) total_amount,
                          pv.Tgl_PV trx_date,
                          pv.Kode_Bank bank_code,
                          pv.No_CekBG warkatnumber,
                          pv.Tanggal_CekBG warkatstore,
                          pv.Jatuh_Tempo_CekBG warkatduedate,
                          pv.Time_Stamp time_stamp,
                          rpt.LeftStr nama_bank,
                          rpt.CenterStr rek_bank
                        from
                          pc_payment_voucher pv 
                          left join ms_report_ttd rpt 
                          on rpt.keyvalue = pv.Kode_Principal and rpt.reportName='BankKeluarAccNumber' 
                          WHERE pv.Status_PV='POSTED' and pv.No_PV='{pv.name}'                  
                    """
                q_str += ' => ' + query
                cursor.execute(query)
                datas = cursor.fetchall()
                if not datas:
                    cursor.close()
                    connection.close()
                    return "PV POSTED NO: "+pv.name+" NOT FOUND!"
                for data in datas:
                    # get PV Detail
                    query_detail = f"""
                    SELECT                       
                      pvd.`No_Faktur`,
                      pvd.`Total_Faktur`,
                      pby.`Kode_Cabang`
                    FROM
                      `pc_payment_voucher_detail` pvd 
                      join `pc_bayar` pby on pvd.`No_Faktur` = pby.`No_Faktur`
                    WHERE pvd.`No_PV`= '{data["name"]}'
                    """
                    q_str += ' => ' + query_detail
                    cursor.execute(query_detail)
                    data_details = cursor.fetchall()

                    query_dn = f"""
                                        SELECT  
                                          pvd.`Keterangan_DN` Jenis_Biaya,                  
                                          pvd.`No_DN` No_Dokumen,
                                          pvd.`No_Referensi`,
                                          pvd.`Total_DN` Nominal_Biaya                                       
                                        FROM
                                          `pc_payment_voucher_dn` pvd 
                                        WHERE pvd.`No_PV`= '{data["name"]}'
                                        """
                    q_str += query_dn
                    cursor.execute(query_dn)
                    query_dn = cursor.fetchall()

                    query_bayar = f"""
                    SELECT 
                      `Kode_Cabang`,
                      `Jenis_Biaya`,
                      `No_Dokumen`,
                      `No_Referensi`,
                      `No_FakturJasa`,                      
                      `PPhBSP`,
                      `Nominal_Biaya`,
                      `Keterangan`,
                      `Koding` 
                    FROM
                      `pc_payment_voucher_bayar` 
                    WHERE No_PV = '{data["name"]}'
                    """
                    q_str += ' => ' + query_bayar
                    cursor.execute(query_bayar)
                    data_bayar = cursor.fetchall()
                    q_str += ' => FINISH'
                    cursor.close()
                    connection.close()


                    if isInsert:
                        q_str += '=> Insert'
                        ret = self.InsertBK_HOCCD(data, pv, data_details, query_dn, data_bayar, True)
                    else:
                        q_str += '=> Update'
                        ret = self.UpdateBK_HOCCD(data, pv, data_details, query_dn, data_bayar,True)

                    return ret

            except Exception as e:
                raise ValidationError(_("Error while connecting to MySQL: %s Tracer: %s" % (e, q_str)))

            # self._cr.commit()


    def get_posted_bk_hoccd_loss(self, nobk, idbk):

        ts = self.get_last_timestamp('bk')
        pvs = self.env['bsp.payment.voucher'].search_read([('type', '=', 'pv'),
                                                           ('state', '=', 'post'),
                                                           ('ref_document','ilike','PV'),
                                                           ('alloc_amount', '>', '0')], ['name'])

        try:
            strpv = str(tuple([p.get("name", '') for p in pvs])).replace(',)', ')')
            ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
            cursor, connection = ou.connect_to_bis()
            # print('koneksi: berhasil' )
            query_where = " WHERE pv.int_banktokenid = " +str(idbk)

            query = """
                       select 
                         pv.int_banktokenid id,
                         pv.sint_banktokentypeid  tp,
                         pv.txt_banktokennumber name,
                         pr.txt_principalcode principal_code,
                         pv.txt_bankacctokennumber ref_number,
                         pv.curr_amounttotal total_amount,
                         pv.dt_checkingaccountdate trx_date,
                         pv.dt_lastupdate_time time_stamp,
                         CASE 
                            WHEN pv.tint_transstatusid = 1 THEN 'CURRENT'
                            WHEN pv.tint_transstatusid = 2 THEN 'SETOR'
                            WHEN pv.tint_transstatusid = 3 THEN 'CAIR'
                            WHEN pv.tint_transstatusid = 4 THEN 'POST'
                            ELSE 'BATAL'
                      end doc_status  
                       from
                         banktoken_hdr pv  inner join principal_ms  pr on pv.int_principalid= pr.int_principalid %s                    
                   """ % (query_where)
            # print("Query:" + query)
            cursor.execute(query)
            datas = cursor.fetchall()
            for data in datas:
                pv = self.env['bsp.payment.voucher'].search([('ref_document', '=', data['ref_number'])], limit=1)
                if not pv:
                    pv = self.env['bsp.payment.voucher'].create({
                        'name': data['name'],
                        'principal_code': data['principal_code'],
                        'total_amount': data['total_amount'],
                        'type': 'bk',
                        'ref_document': data['ref_number'],
                        'trx_date': data['trx_date'],
                        'time_stamp': data['time_stamp'],
                        'ref_document_id': data['id'],
                        'legacy_state': data['doc_status']
                    })
                    synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                        'pv_synch_id': self.id,
                        'pv_id': pv.id,
                        'synch_status': "Insert a Record BK",
                        'synch_date': fields.Datetime.now(),
                        'remark': pv.name + ": Synch PV BM Success",
                    })

                else:
                   pv.write({
                            'name': data['name'],
                            'total_amount': data['total_amount'],
                            'trx_date': data['trx_date'],
                            'time_stamp': data['time_stamp'],
                            'legacy_state':  data['doc_status']
                        })

                   synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                            'pv_synch_id': self.id,
                            'pv_id': pv.id,
                            'synch_status': "Update a Record BK",
                            'synch_date': fields.Datetime.now(),
                            'remark': pv.name + ":BK Update Success",
                        })



            self.write({'lastdate': fields.Datetime.now(),
                        'state': 'done'
                        })
            cursor.close()
            connection.close()

        except Exception as e:
            # if type(e) in (UserError, ValidationError):
            #     raise e
            synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                'pv_synch_id': self.id,
                'synch_status': "Synch BK Error",
                'synch_date': fields.Datetime.now(),
                'remark': "Error while connecting to MySQL: %s" % (e),
            })
            # raise ValidationError(_("Error while connecting to MySQL: %s" % (e)))

        self._cr.commit()
        return ("BK Number %s has been synchronized" % (nobk))
    def get_posted_bk_hoccd(self, dateFrom, isDemand):
        rec = 0
        ts = self.get_last_timestamp('bk')
        pvs = self.env['bsp.payment.voucher'].search_read([('type', '=', 'pv'),
                                                           ('state', '=', 'post'),
                                                           ('ref_document','ilike','PV'),
                                                           ('alloc_amount', '>', '0')], ['name'])

        try:
            strpv = str(tuple([p.get("name", '') for p in pvs])).replace(',)', ')')
            ou = self.env['operating.unit'].search([('code', '=', 'HOCCD')], limit=1)
            cursor, connection = ou.connect_to_bis()
            # print('koneksi: berhasil' )
            query_where = " WHERE pv.dt_bankdate >= '" + dateFrom.strftime("%Y/%m/%d") +\
                          "' and pv.tint_transstatusid=3  and pv.sint_banktokentypeid = 2 and pv.int_principalid > 0 and pv.dt_lastupdate_time > '" + \
                          ts.strftime("%Y-%m-%d %H:%M:%S") + "' and pv.txt_bankacctokennumber in " + strpv

            query = """
                       select 
                         pv.int_banktokenid id,
                         pv.sint_banktokentypeid  tp,
                         pv.txt_banktokennumber name,
                         pr.txt_principalcode principal_code,
                         pv.txt_bankacctokennumber ref_number,
                         pv.curr_amounttotal total_amount,
                         pv.dt_checkingaccountdate trx_date,
                         pv.dt_lastupdate_time time_stamp
                       from
                         banktoken_hdr pv  inner join principal_ms  pr on pv.int_principalid= pr.int_principalid %s                    
                   """ % (query_where)
            # print("Query:" + query)
            cursor.execute(query)
            datas = cursor.fetchall()
            for data in datas:
                rec += 1
                pv = self.env['bsp.payment.voucher'].search([('ref_document', '=', data['ref_number'])], limit=1)
                if not pv:
                    pv = self.env['bsp.payment.voucher'].create({
                        'name': data['name'],
                        'principal_code': data['principal_code'],
                        'total_amount': data['total_amount'],
                        'type': 'bk',
                        'ref_document': data['ref_number'],
                        'trx_date': data['trx_date'],
                        'time_stamp': data['time_stamp'],
                        'ref_document_id': data['id'],
                        'legacy_state': 'CAIR'
                    })
                    synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                        'pv_synch_id': self.id,
                        'pv_id': pv.id,
                        'synch_status': "Insert a Record BK",
                        'synch_date': fields.Datetime.now(),
                        'remark': pv.name + ": Synch PV BM Success",
                    })

                else:
                    if pv.state == 'open':
                        pv.write({
                            'name': data['name'],
                            'total_amount': data['total_amount'],
                            'trx_date': data['trx_date'],
                            'time_stamp': data['time_stamp'],
                            'legacy_state': 'CAIR'
                        })

                        synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                            'pv_synch_id': self.id,
                            'pv_id': pv.id,
                            'synch_status': "Update a Record BK",
                            'synch_date': fields.Datetime.now(),
                            'remark': pv.name + ":BK Update Success",
                        })
                    else:
                        synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                            'pv_synch_id': self.id,
                            'pv_id': pv.id,
                            'synch_status': "PASS Update a Record BK",
                            'synch_date': fields.Datetime.now(),
                            'remark': pv.name + ":BK Update PASSED, STT:" + pv.state.upper()
                        })


            self.write({'lastdate': fields.Datetime.now(),
                        'state': 'done'
                        })
            cursor.close()
            connection.close()

        except Exception as e:
            # if type(e) in (UserError, ValidationError):
            #     raise e
            synch_line = self.env['bsp.payment.voucher.synch.line'].create({
                'pv_synch_id': self.id,
                'synch_status': "Synch BK Error",
                'synch_date': fields.Datetime.now(),
                'remark': "Error while connecting to MySQL: %s" % (e),
            })
            # raise ValidationError(_("Error while connecting to MySQL: %s" % (e)))

        self._cr.commit()
        return ("Total synchronized BKs : %s" % (rec))

    def _cron_automatic_synch_pv_bm(self):
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name', '=', '_CURRENTBM_')])

        for c in mycrons:
            # c.todate = datetime.datetime.now().date()
            c.get_curr_bm_hoccd(c.fromdate, False)

    def _cron_automatic_synch_pv_bk(self):
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name', '=', '_PENDINGPV_')])
        for c in mycrons:
            c.get_pv_bk_bis(c.fromdate, False)

    def _cron_automatic_synch_posted_pv(self):
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name','=','_POSTEDPV_')])
        for c in mycrons:
            c.get_posted_pv_bk_bis(c.fromdate, False)

    def _cron_automatic_synch_posted_bk(self):
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name','=','_POSTEDBK_')])
        for c in mycrons:
            c.get_posted_bk_hoccd(c.fromdate, False)
    def _cron_automatic_synch_bk_number(self):
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name','=','_ALLPOSTEDPV2BK_')])
        for c in mycrons:
            c.update_bknumber_by_hoccd(c.fromdate, False)

    def _cron_automatic_update_bmbk_status(self):
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name','=','_ALLPOSTEDPV2BK_')])
        for c in mycrons:
            c.update_doc_status_hoccd()

    def _cron_automatic_update_pv_status(self):
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name', '=', '_ALLPOSTEDPV2BK_')])
        for c in mycrons:
            c.update_pv_status_from_bis()


    @api.multi
    def unlink(self):
        for rec in self:
            if rec.line_ids:
                raise ValidationError(_('Can not delete record because synch cn was created.'))
        return super(PVSynch, self).unlink()



class PVSynchLine(models.Model):
    _name = "bsp.payment.voucher.synch.line"
    _description = "BIS PV Synch Line"
    _order = 'pv_synch_id, pv_id'

    pv_synch_id = fields.Many2one(
        comodel_name='bsp.payment.voucher.synch',
        string='Bis PV Synch',
        ondelete='cascade')

    pv_id = fields.Many2one(
        comodel_name='bsp.payment.voucher',
        string='PV')

    synch_status = fields.Char("Status Synch", size=30)

    synch_date = fields.Datetime(
        string='Synch Time',
        copy=False)

    remark = fields.Char("Remark")
    


