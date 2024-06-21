# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError

class ClaimBisSynch(models.Model):
    _name = "bsp.claim.bis.synch"
    _description = "BIS Claim Synch"
    _rec_name = 'operating_unit_id'

    operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        string='Operating Unit',
        default=lambda self: self.env.user.default_operating_unit_id.id,
        required=True)
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
        comodel_name='bsp.claim.bis.synch.line',
        inverse_name='claim_synch_id',
        string='Lines',
        required=False)

    type = fields.Selection([
        ('bis_to_odoo','BIS to Odoo'),
        ('odoo_to_bis','Odoo to BIS'),
    ], string='Type', default='bis_to_odoo', required=True)

    @api.multi
    def return_confirmation(self, isOK, desc, docs):
        return {
            'name': desc,
            'type': 'ir.actions.act_window',
            'res_model': 'claim.confirm.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_btn_ok': isOK, 'default_yes_no': docs}
        }

    def action_get_claim_bis(self):
        for rec in self:
            ret = self.get_claim_bis(rec.operating_unit_id, rec.fromdate, rec.todate, True)
            return self.return_confirmation(True, 'Synch Confirmation', ret)

    def get_last_timestamp(self, branchcode):
        cr = self._cr
        cr.execute("SELECT MAX(time_stamp) FROM bsp_creditnote_other where branch_code = '%s'" % branchcode)

        sTs = (cr.fetchone()[0])
        if sTs:
            dts = sTs
        else:
            sTs = '2020-01-01 00:00:00'
            dts = datetime.datetime.strptime(sTs, "%Y-%m-%d %H:%M:%S")

        return dts
    def get_claim_bis(self, ou, dateFrom, dateTo, isDemand):
        for rec in self:
            totalcreate = 0
            totalupdate = 0
            totalalloc = 0
            try:
                ts = self.get_last_timestamp(ou.code)
                # ou = self.env['operating.unit'].search([('code', '=', branch_code)], limit=1)
                cursor, connection = ou.connect_to_bis()
                # print('koneksi: berhasil' )
                # query_where = " WHERE cn_date>='" + rec.fromdate.strftime(
                #     "%Y/%m/%d") + "' and cn_date<='" + rec.todate.strftime(
                #     "%Y/%m/%d") + "' and branch_code='" + rec.operating_unit_id.code + "'"

                query_where = " WHERE LastModifiedTime > '" + ts.strftime("%Y-%m-%d %H:%M:%S") + "' and branch_code='" + ou.code+"'"
                if isDemand and rec.partner_ids:
                    # print("rec.partner_ids :")
                    if rec.partner_ids.name != 'ALL':
                        query_where += ' AND principal_code in %s' % (str(tuple([principal.ref for principal in rec.partner_ids]))).replace(',)',')')
                # print(query_where)
                query = """
                        select 
                          period,
                          branch_code,
                          name,
                          kc_no,
                          cn_date,
                          customer_code,
                          customer_name,
                          cn_total,
                          principal_code,
                          division_code,
                          bsp_share,
                          principal_share,
                          claim_id,
                          allocated_amount,
                          ump_amount,
                          from_date,
                          end_date,
                          exim_state,
                          state 
                        from
                          odoo_credit_note_exim %s                    
                    """%(query_where)
                # print("Query:" + query)
                cursor.execute(query)
                datas = cursor.fetchall()
                for data in datas:
                    cn = self.env['bsp.creditnote.other'].search([('name', '=', data['name'])], limit=1)
                    if not cn:
                        cn = self.env['bsp.creditnote.other'].create({
                                'period': data['period'],
                                'branch_code': data['branch_code'],
                                'name': data['name'],
                                'kc_no': data['kc_no'],
                                'cn_date': data['cn_date'],
                                'customer_code': data['customer_code'],
                                'customer_name': data['customer_name'],
                                'cn_total': data['cn_total'],
                                'principal_code': data['principal_code'],
                                'division_code': data['division_code'],
                                'bsp_share': data['bsp_share'],
                                'principal_share': data['principal_share'],
                                'allocated_amount': data['allocated_amount'],
                                'ump_amount': data['ump_amount'],
                                'from_date': data['from_date'],
                                'end_date': data['end_date'],
                                'exim_status': data['exim_state'],
                                'state': data['state'].lower(),
                            })
                        synch_line = self.env['bsp.claim.bis.synch.line'].create({
                                'claim_synch_id': rec.id,
                                'cn_id': cn.id,
                                'synch_status': "Insert a Record CN",
                                'synch_date': fields.Datetime.now(),
                                'remark': cn.branch_code + ": Synch Success",
                        })
                        totalcreate +=1

                    else:
                        cn.write({
                                'kc_no': data['kc_no'],
                                'cn_date': data['cn_date'],
                                'customer_code': data['customer_code'],
                                'customer_name': data['customer_name'],
                                'cn_total': data['cn_total'],
                                'bsp_share': data['bsp_share'],
                                'principal_share': data['principal_share'],
                                'allocated_amount': data['allocated_amount'],
                                'ump_amount': data['ump_amount'],
                                'from_date': data['from_date'],
                                'end_date': data['end_date'],
                        })

                        synch_line = self.env['bsp.claim.bis.synch.line'].create({
                                    'claim_synch_id': rec.id,
                                    'cn_id': cn.id,
                                    'synch_status': "Update a Record CN",
                                    'synch_date': fields.Datetime.now(),
                                    'remark': cn.branch_code + ": Success",
                        })
                        totalupdate += 1

                    self._cr.execute(""" DELETE FROM bsp_creditnote_alloc where cn_id =%s """ % (str(cn.id)))
                    # print("CN" + data['name'])
                    query_where = "where cn_id='"+data['name']+"'"
                    query = """
                                select 
                                    name,
                                    allocation_date,
                                    allocation_type,
                                    offset_type,
                                    reference_no,
                                    reference_date,
                                    allocation_amount,
                                    cn_id,
                                    exim_state 
                                from
                                    odoo_alokasi_cn_exim %s
                                    """%(query_where)
                    cursor.execute(query)
                    allocs = cursor.fetchall()
                    for alloc in allocs:
                        cnalloc = self.env['bsp.creditnote.alloc'].create({
                                    'name': alloc['name'],
                                    'allocation_date': alloc['allocation_date'],
                                    'allocation_type': alloc['allocation_type'],
                                    'offset_type': alloc['offset_type'],
                                    'reference_no': alloc['reference_no'],
                                    'reference_date': alloc['reference_date'],
                                    'allocation_amount': alloc['allocation_amount'],
                                    'cn_id': cn.id
                                    })
                        totalalloc += 1
                        # print("Alloc" + alloc['name'])
                self.write({'lastdate': fields.Datetime.now(),
                            'state': 'done'})


                cursor.close()
                connection.close()

                return "Total Create: %s  Total Update: %s  Total Alloc: %s " % (totalcreate, totalupdate, totalalloc)

            except Exception as e:
                # if type(e) in (UserError, ValidationError):
                #     raise e
                # synch_line = self.env['bsp.claim.bis.synch.line'].create({
                #         'claim_synch_id': rec.id,
                #         'cn_id': 0,
                #         'synch_status': "Synch CN Error",
                #         'synch_date': fields.Datetime.now(),
                #         'remark': "Error while connecting to MySQL: %s"%(e),
                # })
                raise ValidationError(_("Error while connecting to MySQL: %s"%(e)))

            self._cr.commit()



    def _cron_automatic_synch_claim(self):
        ou_ids = self.env['operating.unit'].search([('parent_id', '=', False),('code','!=','PST')])
        for ou in ou_ids:
            self.get_claim_bis(ou.code, self.fromdate, self.todate, False)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.line_ids :
                raise ValidationError(_('Can not delete record because synch cn was created.'))
        return super(ClaimBisSynch, self).unlink()



class ClaimBisSynchLine(models.Model):
    _name = "bsp.claim.bis.synch.line"
    _description = "BIS CN Synch Line"
    _order = 'claim_synch_id, cn_id'

    claim_synch_id = fields.Many2one(
        comodel_name='bsp.claim.bis.synch',
        string='Bis Claim Synch',
        ondelete='cascade')

    cn_id = fields.Many2one(
        comodel_name='bsp.creditnote.other',
        string='CN',
        required=True)

    synch_status = fields.Char("Status Synch", size=30)

    synch_date = fields.Datetime(
        string='Synch Time',
        copy=False)

    remark = fields.Char("Status Synch", size=80)
    


