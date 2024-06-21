from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import pytz


class Websocket(models.AbstractModel):
    _name = "websocket"
    _description = "Websocket"

    @api.multi
    def prepare_websocket_vals(self, request_type='replace', fields_list=[], new_values={}):
        """
            request_type value: replace, append, unlink
        """
        records = self.read(fields_list)
        # convert date and datetime to string
        for record in records:
            for key, value in record.items():
                if isinstance(value, datetime):
                    value = pytz.UTC.localize(value).astimezone(pytz.timezone(self.env.user.tz or 'UTC'))
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                    record[key] = value
                elif isinstance(value, date):
                    value = value.strftime('%Y-%m-%d')
                    record[key] = value
        vals = {'result': {
            "model": self._name,
            "request_type": request_type,
            "length": len(records),
            "records": records,
        }}
        if new_values :
            vals['result']['new_values'] = new_values
        return vals

    @api.multi
    def write(self, values):
        if self.env.user.company_id.use_websocket :
            fields_list = self.env['ir.model.fields'].get_fields_to_change(self._name)
            new_values = {}
            for f in fields_list :
                if f in values :
                    new_values[f] = values[f]
            if self and new_values:
                for rec in self :
                    websocket_vals = rec.prepare_websocket_vals(request_type='replace', fields_list=list(new_values.keys()), new_values=new_values)
                    self.env.user.send_to_websocket(message=websocket_vals)
        res = super(Websocket, self).write(values)
        return res

    @api.model
    def create(self, values):
        res = super(Websocket, self).create(values)
        fields_list = self.env['ir.model.fields'].get_fields_to_change(self._name)
        if fields_list and self.env.user.company_id.use_websocket:
            websocket_vals = res.prepare_websocket_vals(request_type='append', fields_list=fields_list)
            self.env.user.send_to_websocket(message=websocket_vals)
        return res

    @api.multi
    def unlink(self):
        if self and self.env.user.company_id.use_websocket:
            websocket_vals = self.prepare_websocket_vals(request_type='unlink', fields_list=['id'])
            self.env.user.send_to_websocket(message=websocket_vals)
        return super(Websocket, self).unlink()
