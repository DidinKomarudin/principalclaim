from pytz import timezone, UTC
from datetime import datetime, timedelta
from pymemcache.client.base import Client
from odoo.http import request
import string
import ast
import logging

_logger = logging.getLogger(__name__)


def contain_number(words):
    for word in words:
        if word.isdigit():
            return True
    return False


def punctuation(words):
    for word in words:
        if word in string.punctuation:
            return True
    return False


def date_timezone(tz, dt=False, format='datetime'):
    if not dt:
        dt = datetime.now()
    if type(dt) is str:
        dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
    final_date = UTC.localize(dt).astimezone(timezone(tz))
    if format != 'datetime':
        final_date = final_date.strftime('%Y-%m-%d %H:%M:%S')
    return final_date


def date_utc(tz, dt=False, format='datetime'):
    if not dt:
        return ''
    if type(dt) is str:
        dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
    tz = timezone(tz)
    local_dt = tz.localize(dt, is_dst=None)
    final_date = local_dt.astimezone(UTC)
    if format != 'datetime':
        final_date = final_date.strftime('%Y-%m-%d %H:%M:%S')
    return final_date


def date2datetime(tz, date2convert=False, date_type='start_date', format='string'):
    if not date2convert:
        date2convert = datetime.now().date()
    tz_diff = datetime.now(timezone(tz)).strftime('%z')
    tz_diff = int(tz_diff.replace('+', '').replace('0', ''))
    if type(date2convert) is not str:
        date2convert = date2convert.strftime('%Y-%m-%d')
    date2convert = datetime.strptime(date2convert + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    if date_type == 'start_date':
        date2convert = date2convert - timedelta(hours=tz_diff)
    else:
        date2convert = date2convert + timedelta(days=1)
        date2convert = date2convert - timedelta(hours=tz_diff)
    if format == 'string':
        date2convert = date2convert.strftime('%Y-%m-%d %H:%M:%S')
    return date2convert


def connect_to_memcache():
    memcache_host_and_port = request.env['ir.config_parameter'].get_param('memcache_host_and_port')
    if not memcache_host_and_port:
        memcache_host_and_port = 'localhost:11211'
    memcache_host_and_port = memcache_host_and_port.split(':')
    host, port = memcache_host_and_port
    try:
        mc = Client((host, int(port)))
    except Exception as e:
        mc = False
        _logger.warning(e)
    return mc


def set_memcache(data):
    # data dalam format dictionary {'key':'vaue', 'key2':'value2'}
    mc = connect_to_memcache()
    if not data:
        return False
    if len(data) > 1:
        mc.set_many(data)
    else:
        for k, v in data.items():  # isinya cuma satu
            mc.set(k, v)


def delete_memcache(keys):
    # key dalam format string jika hanya satu, format list jika banyak
    mc = connect_to_memcache()
    if not keys:
        return False
    if len(keys) > 1:
        mc.delete_many(keys)
    else:
        mc.delete(keys)


def get_memcache(keys):
    # key dalam format string jika hanya satu, format list jika banyak
    mc = connect_to_memcache()
    if not keys:
        if isinstance(keys, dict):
            result = {}
        else:
            result = None
    elif isinstance(keys, str):
        result = mc.get(keys)
        if result:
            result = result.decode('utf-8')
            try:
                result = ast.literal_eval(result)
            except:
                pass
    else:
        result = mc.get_many(keys)
        if result:
            for k, v in result.items():
                v = v.decode('utf-8')
                try:
                    v = ast.literal_eval(v)
                except:
                    pass
                result[k] = v
    return result


def workbook_format(workbook):
    colors = {
        'white_orange': '#FFFFDB',
        'orange': '#FFC300',
        'red': '#FF0000',
        'yellow': '#F6FA03',
    }

    wbf = {}
    wbf['header'] = workbook.add_format(
        {'bold': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FFFFDB', 'font_color': '#000000',
         'font_name': 'Georgia'})
    wbf['header'].set_border()

    wbf['header_orange'] = workbook.add_format(
        {'bold': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': colors['orange'], 'font_color': '#000000',
         'font_name': 'Georgia'})
    wbf['header_orange'].set_border()

    wbf['header_yellow'] = workbook.add_format(
        {'bold': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': colors['yellow'], 'font_color': '#000000',
         'font_name': 'Georgia'})
    wbf['header_yellow'].set_border()

    wbf['header_no'] = workbook.add_format(
        {'bold': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FFFFDB', 'font_color': '#000000',
         'font_name': 'Georgia'})
    wbf['header_no'].set_border()
    wbf['header_no'].set_align('vcenter')

    wbf['footer'] = workbook.add_format({'align': 'left', 'font_name': 'Georgia'})

    wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss', 'font_name': 'Georgia'})
    wbf['content_datetime'].set_left()
    wbf['content_datetime'].set_right()

    wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd', 'font_name': 'Georgia'})
    wbf['content_date'].set_left()
    wbf['content_date'].set_right()

    wbf['content_no'] = workbook.add_format({'align': 'center'})
    wbf['content_no'].set_left()
    wbf['content_no'].set_right()

    wbf['title_doc'] = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 20,
        'font_name': 'Georgia',
    })
    wbf['title'] = workbook.add_format({'align': 'left', 'font_name': 'Georgia'})
    wbf['title'].set_font_size(11)

    wbf['company'] = workbook.add_format({'align': 'left', 'font_name': 'Georgia'})
    wbf['company'].set_font_size(11)

    wbf['content'] = workbook.add_format()
    wbf['content'].set_left()
    wbf['content'].set_right()

    wbf['content_float'] = workbook.add_format({'align': 'right', 'num_format': '#,##0.00', 'font_name': 'Georgia'})
    wbf['content_float'].set_right()
    wbf['content_float'].set_left()

    wbf['content_number'] = workbook.add_format({'align': 'right', 'num_format': '#,##0', 'font_name': 'Georgia'})
    wbf['content_number'].set_right()
    wbf['content_number'].set_left()

    wbf['content_percent'] = workbook.add_format({'align': 'right', 'num_format': '0.00%', 'font_name': 'Georgia'})
    wbf['content_percent'].set_right()
    wbf['content_percent'].set_left()

    wbf['total_float'] = workbook.add_format(
        {'bold': 1, 'bg_color': colors['white_orange'], 'align': 'right', 'num_format': '#,##0.00',
         'font_name': 'Georgia'})
    wbf['total_float'].set_top()
    wbf['total_float'].set_bottom()
    wbf['total_float'].set_left()
    wbf['total_float'].set_right()

    wbf['total_number'] = workbook.add_format(
        {'align': 'right', 'bg_color': colors['white_orange'], 'bold': 1, 'num_format': '#,##0',
         'font_name': 'Georgia'})
    wbf['total_number'].set_top()
    wbf['total_number'].set_bottom()
    wbf['total_number'].set_left()
    wbf['total_number'].set_right()

    wbf['total'] = workbook.add_format(
        {'bold': 1, 'bg_color': colors['white_orange'], 'align': 'center', 'valign': 'vcenter', 'font_name': 'Georgia'})
    wbf['total'].set_left()
    wbf['total'].set_right()
    wbf['total'].set_top()
    wbf['total'].set_bottom()

    wbf['total_float_yellow'] = workbook.add_format(
        {'bold': 1, 'bg_color': colors['yellow'], 'align': 'right', 'num_format': '#,##0.00',
         'font_name': 'Georgia'})
    wbf['total_float_yellow'].set_top()
    wbf['total_float_yellow'].set_bottom()
    wbf['total_float_yellow'].set_left()
    wbf['total_float_yellow'].set_right()

    wbf['total_number_yellow'] = workbook.add_format(
        {'align': 'right', 'bg_color': colors['yellow'], 'bold': 1, 'num_format': '#,##0', 'font_name': 'Georgia'})
    wbf['total_number_yellow'].set_top()
    wbf['total_number_yellow'].set_bottom()
    wbf['total_number_yellow'].set_left()
    wbf['total_number_yellow'].set_right()

    wbf['total_yellow'] = workbook.add_format(
        {'bold': 1, 'bg_color': colors['yellow'], 'align': 'center', 'valign': 'vcenter', 'font_name': 'Georgia'})
    wbf['total_yellow'].set_left()
    wbf['total_yellow'].set_right()
    wbf['total_yellow'].set_top()
    wbf['total_yellow'].set_bottom()

    wbf['total_float_orange'] = workbook.add_format(
        {'bold': 1, 'bg_color': colors['orange'], 'align': 'right', 'num_format': '#,##0.00',
         'font_name': 'Georgia'})
    wbf['total_float_orange'].set_top()
    wbf['total_float_orange'].set_bottom()
    wbf['total_float_orange'].set_left()
    wbf['total_float_orange'].set_right()

    wbf['total_number_orange'] = workbook.add_format(
        {'align': 'right', 'bg_color': colors['orange'], 'bold': 1, 'num_format': '#,##0', 'font_name': 'Georgia'})
    wbf['total_number_orange'].set_top()
    wbf['total_number_orange'].set_bottom()
    wbf['total_number_orange'].set_left()
    wbf['total_number_orange'].set_right()

    wbf['total_orange'] = workbook.add_format(
        {'bold': 1, 'bg_color': colors['orange'], 'align': 'center', 'valign': 'vcenter', 'font_name': 'Georgia'})
    wbf['total_orange'].set_left()
    wbf['total_orange'].set_right()
    wbf['total_orange'].set_top()
    wbf['total_orange'].set_bottom()

    wbf['header_detail_space'] = workbook.add_format({'font_name': 'Georgia'})
    wbf['header_detail_space'].set_left()
    wbf['header_detail_space'].set_right()
    wbf['header_detail_space'].set_top()
    wbf['header_detail_space'].set_bottom()

    wbf['header_detail'] = workbook.add_format({'bg_color': '#E0FFC2', 'font_name': 'Georgia'})
    wbf['header_detail'].set_left()
    wbf['header_detail'].set_right()
    wbf['header_detail'].set_top()
    wbf['header_detail'].set_bottom()

    return wbf, workbook