from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.http import request
from odoo.osv import expression

import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    join_date = fields.Date(
        string='Join Date',
        default=fields.Date.today,
        required=False)
    left_date = fields.Date(
        string='Left Date',
        required=False)

    def __init__(self, pool, cr):
        field_datas = [
            {"field_name": "join_date", "type": "DATE"},
            {"field_name": "left_date", "type": "DATE"},
            {"field_name": "latitude", "type": "DOUBLE PRECISION"},
            {"field_name": "longitude", "type": "DOUBLE PRECISION"},
        ]
        env = api.Environment(cr, SUPERUSER_ID, {})
        for field in field_datas:
            env.user.add_related_fields(table_name=self._table, field=field)
        super(ResPartner, self).__init__(pool, cr)

    @api.model
    def create(self, values):
        if not values.get('join_date'):
            values['join_date'] = fields.Date.today()
        return super(ResPartner, self).create(values)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        self.env.user.log_info(f'domain partner: {domain}')
        return super(ResPartner, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def _get_name(self):
        res = super(ResPartner, self)._get_name()
        if self.barcode :
            res = f'{self.barcode} {res}'
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', ('name', operator, name), ('ref', operator, name), ('barcode', operator, name)]
        rec_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return self.browse(rec_ids).name_get()
