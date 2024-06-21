from odoo import http
import json

def api_response(json_data={}, status=200, type='json'):
    if type == 'json' :
        http.Response.status = str(status)
        return json_data
    return http.Response(json.dumps(json_data),
        content_type='application/json;charset=utf-8',
        status=status)

def reformat_error_message(error_message):
    error_message = str(error_message).replace('\\n', ' ')
    error_message = str(error_message).replace('\n', ' ')
    error_message = error_message.replace('\\', '')
    error_message = error_message.replace(', None', '')
    error_message = error_message.replace('\"', '')
    return error_message

def get_operator(value):
    operator = '='
    if type(value) is list :
        operator = 'in'
    return operator
