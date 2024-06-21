from odoo import fields, models, api, _, sql_db
from datetime import datetime, timedelta
from odoo.exceptions import UserError, AccessDenied, ValidationError
from mysql.connector import Error
from pytz import timezone, UTC
from odoo.tools import config, human_size, ustr, html_escape
from odoo.addons.bsp_claim_base.models.common import workbook_format
from io import BytesIO
import odoorpc
import urllib

import os
import time
import base64
import mysql.connector
import requests
import json
import redis
import xlsxwriter
import pyttsx3
import ast
import csv
import xlrd
import keyword

try:
    import keyboard
except:
    pass
try:
    import pyautogui
except:
    pass
try:
    import pynput
except:
    pass

import logging

_logger = logging.getLogger(__name__)


class ClaimMagicButton(models.TransientModel):
    _name = "bsp.claim.magic.button"
    _description = "Claim Magic Button"

    action = fields.Selection([
        # ('test', 'Test'),
        ('synch_pv', 'Synch PV From BIS AP (Pending/Posted)'),
        ('synch_bm', 'Synch BM From HOCCD (Current)'),
        ('synch_pv2bk', 'Synch ALL Posted PV to Generate BK'),
        ('synch_bk', 'Synch BK From HOCCD (Cair)'),
        ('synch_nobk', 'Synch ALL No BK From HOCCD'),
        ('update_bm_alloc', 'Update ALLOCATED AMOUNT BM'),
        ('update_remainbm', 'Update Remain AMOUNT BM on HOCCD'),
        ('update_bmbk_status', 'Update status BM/BK from HOCCD'),
        ('update_pv_status', 'Update status PV from BIS AP'),
        # ('print', 'Print'),
        # ('mysql', 'Connect to MySQL'),
        # ('remove_missing_filestore', 'Remove Missing Filestore'),
        # ('clear_transaction', 'Clear All Data Transaction'),
        # ('update_currency_rate', 'Update Currency Rate')
    ], string="Action", default='test', required=True)
    file = fields.Binary(string="File")
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date', default=fields.Date.today)

    @api.multi
    def return_confirmation(self, isOK, desc, docs):
        return {
            'name': desc,
            'type': 'ir.actions.act_window',
            'res_model': 'confirm.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_btn_ok': isOK, 'default_yes_no': docs}
        }
    @api.multi
    def action_magic(self):
        # user_admin_ids = self.env.ref('base.user_admin')
        # user_admin_ids += self.env.ref('base.user_root')
        # if self.env.user.id not in user_admin_ids.ids:
        #     raise AccessDenied(_("You are not allowed to execute this action. Only admin user can execute."))
        _logger.info("\n \n logger ACTION MAGIC \n")
        # if self.action == 'test':
        #     self.action_test()
        ret = 'Finish'
        if self.action == 'synch_pv':
            ret = self.action_synch_pv()
        if self.action == 'synch_bm':
            ret = self.action_synch_bm()
        if self.action == 'synch_pv2bk':
            ret = self.action_synch_pv2bk()
        if self.action == 'synch_bk':
            ret = self.action_synch_bk()
        if self.action == 'synch_nobk':
            ret = self.action_synch_nobk()
        if self.action == 'update_bm_alloc':
            ret = self.action_update_bm_alloc()
        if self.action == 'update_remainbm':
            ret = self.action_update_remainbm()
        if self.action == 'update_bmbk_status':
            ret = self.action_update_status_bmbk()
        if self.action == 'update_pv_status':
            ret = self.action_update_status_pv()

        # self._cr.commit()
        return self.return_confirmation(True, 'Synch Confirmation', ret)
        # raise UserError(_("Finish"))


    def action_synch_pv(self):
        ret = "No PVs can be loaded!"
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name', '=', '_PENDINGPV_')])
        for c in mycrons:
            ret = c.get_pv_bk_bis(c.fromdate, True)
        return ret
    def action_synch_bm(self):
        ret = "No BMs can be loaded!"
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name', '=', '_CURRENTBM_')])
        for c in mycrons:
            # c.todate = datetime.datetime.now().date()
            ret = c.get_curr_bm_hoccd(c.fromdate, True)
        return ret

    def action_synch_pv2bk(self):
        if not self.env.user.has_group('base.group_system'):
            return "Sorry, your access no enought for this action "

        ret = "No BK can be generated!"
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name', '=', '_ALLPOSTEDPV2BK_')])
        for c in mycrons:
            ret = c.generate_all_posted_pv2bk()

        return ret
    def action_synch_bk(self):
        ret = "No BKs can be loaded!"
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name', '=', '_POSTEDBK_')])
        for c in mycrons:
            ret = c.get_posted_bk_hoccd(c.fromdate, True)

        return ret

    def action_synch_nobk(self):
        ret = "No BKs can be loaded!"
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name', '=', '_ALLPOSTEDPV2BK_')])
        for c in mycrons:
            ret = c.update_bknumber_by_hoccd(True)

        return ret

    def action_update_remainbm(self):
        if not self.env.user.has_group('base.group_system'):
            return "Sorry, your access no enought for this action "

        ret = "No BKs can be loaded!"
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name', '=', '_ALLPOSTEDPV2BK_')])
        for c in mycrons:
            ret = c.update_bm_coa_amount()

        return ret
    def action_update_status_bmbk(self):
        if not self.env.user.has_group('base.group_system'):
            return "Sorry, your access no enought for this action "

        ret = "No BMBK status updated!"
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name', '=', '_ALLPOSTEDPV2BK_')])
        for c in mycrons:
            ret = c.update_doc_status_hoccd()
        return ret

    def action_update_status_pv(self):
        if not self.env.user.has_group('base.group_system'):
            return "Sorry, your access no enought for this action "

        ret = "No PV status updated!"
        mycrons = self.env['bsp.payment.voucher.synch'].search([('name', '=', '_ALLPOSTEDPV2BK_')])
        for c in mycrons:
            ret = c.update_pv_status_from_bis()
        return ret

    def action_update_bm_alloc(self):
        if not self.env.user.has_group('base.group_system'):
            return "Sorry, your access no enought for this action "
        recs=0
        ret = "BM allocation amount has updated :"
        BMs = self.env['bsp.payment.voucher'].search([('type','=','bm'),('state','!=','open')])
        for bm in BMs:
            alloc = bm.calc_alloc_amount()
            # alloc = bm.get_allocated_amount_all()
            if alloc != bm.alloc_amount:
                recs += 1
                bm.write({'alloc_amount':alloc})
        return ret + str(recs)

    def action_remove_missing_filestore(self):
        attachment_ids = self.env['ir.attachment'].search([
            ('store_fname', '!=', False),
            ('id', '!=', 0),  # ada yg aneh, kalau gak ditambah ID dapatnya sedikit
        ], limit=0)
        for attachment_id in attachment_ids:
            full_path = attachment_id._full_path(attachment_id.store_fname)
            r = ''
            bin_size = attachment_id._context.get('bin_size')
            try:
                if bin_size:
                    r = human_size(os.path.getsize(full_path))
                else:
                    r = base64.b64encode(open(full_path, 'rb').read())
            except (IOError, OSError):
                _logger.info("\n\n _read_file reading %s", full_path, exc_info=True)
            _logger.info("\n\n r: %s, type: %s", r, type(r))
            if not r:
                attachment_id.unlink()





    def get_extension(self):
        self.ensure_one()
        template_file = self.template_file()
        if not template_file:
            return ''
        files = template_file.split('.')
        if len(files) <= 1:
            return ''
        return files[-1:][0].lower()
