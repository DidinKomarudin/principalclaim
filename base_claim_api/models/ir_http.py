from odoo import api, fields, models, _
from odoo.http import request
import requests
import json

class Http(models.AbstractModel):
    _inherit = 'ir.http'

    # fix invalid session
    def session_info(self):
        res = super(Http, self).session_info()
        if request.params and request.params.get('db') and request.params.get('login') and request.params.get('password') and not self._context.get('skip'):
            url = request.httprequest.url
            headers = {
                'Content-Type': 'application/json'
            }
            data = {
                "jsonrpc": "2.0",
                "params": {
                    "db": request.params['db'],
                    "login": request.params['login'],
                    "password": request.params['password'],
                    "context": {'skip':True},
                }
            }
            new_res = requests.post(url=url, headers=headers, json=data)
            res['session_id'] = new_res.cookies.values()[0]
        return res
