from odoo import api, fields, models, SUPERUSER_ID, _
import logging
_logger = logging.getLogger(__name__)

class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    active = fields.Boolean(
        string='Active',
        default=True,
        copy=False)

    def __init__(self, pool, cr):
        field_datas = [
            {"field_name": "active", "type": "boolean"},
        ]
        env = api.Environment(cr, SUPERUSER_ID, {})
        for field in field_datas:
            env.user.add_related_fields(table_name=self._table, field=field)
        super(IrConfigParameter, self).__init__(pool, cr)
