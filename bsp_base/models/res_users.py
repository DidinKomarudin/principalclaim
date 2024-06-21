from odoo import models, fields, api, SUPERUSER_ID, _, tools
from odoo.addons.bsp_base.models.common import *
from mysql import connector
from odoo.exceptions import UserError, ValidationError
from websocket import create_connection
from datetime import date, datetime
from barcode.writer import ImageWriter
from docxtpl import InlineImage, DocxTemplate
from docx.shared import Mm
import os
import barcode
import base64
import qrcode
import odoorpc
import json
import pytz
import requests
import re

import logging

_logger = logging.getLogger(__name__)

# API_URL = 'http://192.168.8.27:5000'
# API_URL = 'http://127.0.0.1:8123'


class ResUsers(models.Model):
    _inherit = 'res.users'

    location_ids = fields.Many2many(
        comodel_name='stock.location',
        relation='res_user_rel',
        column1='user_id',
        column2='location_id',
        string='Location'
    )
    division_ids = fields.Many2many('product.category', string='Division')
    secondary_division_ids = fields.Many2many('product.category',
                                              'secondary_user_categ_rel', 'user_id', 'categ_id',
                                              string='Secondary Division')
    bis_user = fields.Boolean(
        string='BIS User'
    )

    def __init__(self, pool, cr):
        field_datas = [
            {"field_name": "bis_user", "type": "boolean"},
        ]
        env = api.Environment(cr, SUPERUSER_ID, {})
        for field in field_datas:
            env.user.add_related_fields(table_name=self._table, field=field)
        super(ResUsers, self).__init__(pool, cr)

    def add_related_fields(self, table_name, field):
        query = """
            SELECT
                column_name
            FROM
                information_schema.columns
            WHERE
                table_name = '%s'
                and column_name = '%s';
        """ % (table_name, field["field_name"])
        self._cr.execute(query)
        result = self._cr.fetchall()
        if not result:
            add_field_query = """
                ALTER TABLE
                    %s
                ADD COLUMN %s %s
            """ % (table_name, field["field_name"], field["type"])
            self._cr.execute(add_field_query)
            if field["field_name"] == 'active':
                self._cr.execute("""
                    UPDATE 
                        %s
                    SET
                        active='t'
                """ % (table_name))
            self._cr.commit()
            _logger.info(_("Column %s has been added to table %s" % (field["field_name"], table_name)))

    def get_current_stock(self, location_id, product_id, uom_id=False, child_loc=False, type='available'):
        if isinstance(location_id, int):
            location_id = self.env['stock.location'].browse(location_id)
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse(product_id)
        if isinstance(uom_id, int):
            uom_id = self.env['uom.uom'].browse(uom_id)
        if not uom_id:
            uom_id = product_id.uom_id
        domain = [
            ('product_id', '=', product_id.id),
        ]
        if child_loc:
            domain += [('location_id', 'child_of', location_id.id)]
        else:
            domain += [('location_id', '=', location_id.id)]
        quant_ids = self.env['stock.quant'].sudo().search(domain)
        if type == 'available':
            base_qty = sum(q.quantity - q.reserved_quantity for q in quant_ids)
        else:
            base_qty = sum(q.quantity for q in quant_ids)
        return product_id.uom_id._compute_quantity(base_qty, uom_id)

    def get_forecast_stock(self, location_id, product_id, uom_id=False, child_loc=False):
        if isinstance(location_id, int):
            location_id = self.env['stock.location'].browse(location_id)
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse(product_id)
        if isinstance(uom_id, int):
            uom_id = self.env['uom.uom'].browse(uom_id)
        onhand_qty = self.env.user.get_current_stock(location_id=location_id, product_id=product_id, uom_id=uom_id,
                                                     child_loc=child_loc, type='onhand')
        if not uom_id:
            uom_id = product_id.uom_id
        if child_loc:
            operator = 'child_of'
        else:
            operator = '='
        domain = [
            ('product_id', '=', product_id.id),
            ('state', 'not in', ['draft', 'cancel', 'done']),
        ]
        move_line_in_ids = self.env['stock.move.line'].sudo().search(
            domain + [('location_dest_id', operator, location_id.id)])
        move_in_ids = self.env['stock.move'].sudo().search(
            domain + [('location_dest_id', operator, location_id.id), ('move_line_ids', '=', False)])
        move_line_out_ids = self.env['stock.move.line'].sudo().search(
            domain + [('location_id', operator, location_id.id)])
        move_out_ids = self.env['stock.move'].sudo().search(
            domain + [('location_id', operator, location_id.id), ('move_line_ids', '=', False)])
        in_qty = sum(line.product_uom_id._compute_quantity(line.product_uom_qty, uom_id) for line in move_line_in_ids)
        in_qty += sum(line.product_uom._compute_quantity(line.product_uom_qty, uom_id) for line in move_in_ids)
        out_qty = sum(line.product_uom_id._compute_quantity(line.product_uom_qty, uom_id) for line in move_line_out_ids)
        out_qty += sum(line.product_uom._compute_quantity(line.product_uom_qty, uom_id) for line in move_out_ids)
        return onhand_qty + in_qty - out_qty

    def get_sum_package(self, location_id, package_type_id):
        quant_ids = location_id.quant_ids
        quant_package_ids = quant_ids.filtered(
            lambda quant: quant.package_id.package_storage_type_id.id == package_type_id.id)
        package_qty = len(quant_package_ids)
        return package_qty

    def date_timezone(self, dt=False, format='datetime'):
        self.ensure_one()
        if not self.tz:
            raise ValidationError(_(f'Please set timezone for user {self.display_name}.'))
        return date_timezone(self.tz, dt=dt, format=format)

    def date_utc(self, dt=False, format='datetime'):
        self.ensure_one()
        if not self.tz:
            raise ValidationError(_(f'Please set timezone for user {self.display_name}.'))
        return date_utc(tz=self.tz, dt=dt, format=format)

    def date2datetime(self, date2convert=False, date_type='start_date', format='string'):
        self.ensure_one()
        if not self.tz:
            raise ValidationError(_(f'Please set timezone for user {self.display_name}.'))
        return date2datetime(self.tz, date2convert=date2convert, date_type=date_type, format=format)

    def selection_lebel(self, model, field_name, field_value):
        try:
            rec_env = self.env[model]
            label = dict(rec_env._fields[field_name].selection).get(field_value)
        except:
            label = ''
        return label

    def log_info(self, log='Nothing to log'):
        _logger.info('\n\n%s\n' % (log))

    def log_warning(self, log='Nothing to log'):
        _logger.warning('\n\n%s\n' % (log))

    @api.multi
    def connect_to_mysql(self, host, database, user, password, port):
        error_message = ''
        try:
            connection = connector.connect(
                host=host,
                database=database,
                user=user,
                password=password,
                port=port
            )
            if not connection.is_connected():
                error_message = 'Failed connect to BIS'
            db_info = connection.get_server_info()
            self.env.user.log_info('Connected to MySQL Server version: %s' % (db_info))
            cursor = connection.cursor(dictionary=True)
            cursor.execute("select database();")
            record = cursor.fetchone()
            self.env.user.log_info('You\'re connected to database: %s' % (record['database()']))
        except Exception as e:
            try:
                error_message = e.__unicode__()
            except:
                try:
                    error_message = e.reason.strerror
                except:
                    error_message = e
        if error_message:
            raise UserError(_(error_message))
        return cursor, connection

    @api.multi
    def connect_to_odoo(self, host, port, db, login, password):
        error_message = ''
        try:
            res = odoorpc.ODOO(host=host, port=port)
            res.login(db=db, login=login, password=password)
        except Exception as e:
            try:
                error_message = e.__unicode__()
            except:
                try:
                    error_message = e.reason.strerror
                except:
                    error_message = e
        if error_message:
            raise UserError(_(error_message))
        return res

    @api.multi
    def send_to_websocket(self, message={}):
        try:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url').split(':')
            URL = f'ws:{base_url[1]}:8888/ws/'
            ws = create_connection(URL)
            ws.send(json.dumps(message))
            result = ws.recv()
            self.env.user.log_info("Received: '%s'" % (result))
            ws.close()
        except Exception as e:
            self.env.user.log_info(e)
            result = e
        return "Received: '%s'" % (result)

    def check_mandatory_fields(self, must_have_fields, fields_value):
        mandatory_fields = []
        empty_fields = []
        for field in must_have_fields :
            if field not in fields_value :
                mandatory_fields.append(field)
            elif not fields_value.get(field):
                empty_fields.append(field)
        if mandatory_fields :
            raise ValidationError(_(f'Mandatory fields {mandatory_fields}'))
        if empty_fields :
            raise ValidationError(_(f'Empty value {empty_fields}'))

    def workbook_format(self, workbook):
        return workbook_format(workbook)

    def contain_number(self, words):
        return contain_number(words)

    def punctuation(self, words):
        return punctuation(words)

    def get_output_docx_report(self, template_object, report_data, filename):
        template_object.render(report_data)
        folder_path = tools.config['data_dir']
        if os.sys.platform == 'win32':
            filename_path = folder_path + '\\' + filename
        else:
            filename_path = folder_path + '/' + filename
        if not os.path.exists(filename_path):
            try:
                os.mkdir(path=folder_path)
            except:
                pass
        template_object.save(filename_path)
        file_handler = open(filename_path, "rb")
        file_data = file_handler.read()
        file_output = base64.encodestring(file_data)
        file_handler.close()
        return file_output

    def generate_barcode_image(self, barcode_string=None, docx_template=None, width=50, height=12):
        if barcode_string:
            barcode128_val = barcode.get(name='code128', code=barcode_string, writer=ImageWriter())
        else:
            barcode128_val = False
        if barcode128_val:
            folder_path = tools.config['data_dir']
            if os.sys.platform == 'win32':
                folder_path = folder_path + '\\barcode_product\\'
            else:
                folder_path = folder_path + '/barcode_product/'
            if not os.path.exists(folder_path):
                try:
                    os.mkdir(path=folder_path)
                except:
                    pass
            barcode_string = barcode_string.replace('/', '-')
            filename = folder_path + barcode_string
            barcode128_val.default_writer_options['write_text'] = False
            barcode123_filename = barcode128_val.save(filename=filename)
            barcode_inline = InlineImage(tpl=docx_template,
                                         image_descriptor=barcode123_filename,
                                         width=Mm(width),
                                         height=Mm(height))
            return barcode_inline

    def generate_qrcode_image(self, qrcode_string=None, docx_template=None, width=30, height=30):
        qrcode_string_val = qrcode_string
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=4,
            error_correction=qrcode.constants.ERROR_CORRECT_L
        )
        qr.add_data(qrcode_string_val)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        folder_path = tools.config['data_dir']
        if os.sys.platform == 'win32':
            folder_path = folder_path + '\\qrcode_loc\\'
        else:
            folder_path = folder_path + '/qrcode_loc/'
        if not os.path.exists(folder_path):
            try:
                os.mkdir(path=folder_path)
            except:
                pass
        filename = folder_path + qrcode_string
        qrcode123_filename = img.save(filename)
        _logger.info("\n img: %s" % (img))
        qrcode_inline = InlineImage(tpl=docx_template,
                                    image_descriptor=filename,
                                    width=Mm(width),
                                    height=Mm(height))
        return qrcode_inline

    def get_template_object_docx(self, template):
        working_dir = os.path.dirname(__file__)
        working_dir = working_dir.split("bsp_base")[0]
        if os.sys.platform == 'win32':
            template = template.replace('/', '\\')
            template_file = os.path.join(working_dir, template)
        else:
            template_file = os.path.join(working_dir, template)
        template_object = DocxTemplate(template_file)
        return template_object

    # direct print
    # send file menggunakan flask
    def send_file(self, filename_path, filename):
        api_url = self.env['ir.config_parameter'].sudo().get_param('flask.send_print_out')
        if not api_url:
            raise ValidationError(_("Please make configuration in menu System Parameter with key : flask.send_print_out"))
        with open(filename_path, 'rb') as fp:
            content = fp.read()
        url = api_url + "/files/" + filename
        try:
            response = requests.post(
                url, data=content
            )
            self.env.user.log_info("\n response: %s" % (response))
        except Exception as e:
            raise ValidationError(_("Send file failed: \n\n%s" % e))

    # direct print
    # print file menggunakan flask
    def print_file(self, filename):
        api_url = self.env['ir.config_parameter'].sudo().get_param('flask.send_print_out')
        if not api_url:
            raise ValidationError(_("Please make configuration in menu System Parameter with key : flask.send_print_out"))
        url = api_url + "/print/" + filename
        try:
            response = requests.post(
                url
            )
            self.env.user.log_info("\n response: %s" % (response))
        except Exception as e:
            raise ValidationError(_("Print file failed: \n\n%s" % e))

    def get_postgres_detail(self):
        self.env.cr.execute('select version()')
        version = int(self.env.cr.dictfetchone()['version'][11:13])
        if version >= 11:
            type = 'PROCEDURE'
            additional_return = ''
            call_select = 'CALL'
        else:
            type = 'FUNCTION'
            additional_return = 'RETURNS VOID'
            call_select = 'SELECT'
        return {
            'version': version, 
            'type': type, 
            'additional_return': additional_return, 
            'call_select': call_select,
        }

    def stored_procedure_query(self):
        # sisipkan query di sini bung
        return []

    @api.model
    def generate_stored_procedure(self):
        postgres_detail = self.get_postgres_detail()
        for query in self.stored_procedure_query():
            query = query.format(type=postgres_detail['type'], additional_return=postgres_detail['additional_return'])
            self.env.cr.execute(query)
            self.env.cr.commit()

    def split_str(self, words):
        """
        :param words : string
        :return : list [str1, str2, ..]
        """
        res = re.split(r'[ ,|;"-]+', words)
        return res

    def convert_str2int(self, words):
        """
        :param words : string
        :return : list [int1, int2, ..]
        """
        split_str = self.split_str(words)
        int_list = [int(splt_str) for splt_str in split_str if splt_str]
        return int_list

    def zpl_label_emulator(self, label_code):
        label_code = label_code.replace("\n", "").replace(" ", "")
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/4x6/0/' + label_code
        return {
            'name': 'ZPL Label',
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }