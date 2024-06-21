from odoo import api, fields, models, modules, SUPERUSER_ID, _
from odoo.modules import get_module_resource
import odoo

class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    missing = fields.Char(
        string='Missing',
        copy=False)

    def __init__(self, pool, cr):
        field_datas = [
            {"field_name": "missing", "type": "boolean"},
        ]
        env = api.Environment(cr, SUPERUSER_ID, {})
        for field in field_datas:
            env.user.add_related_fields(table_name=self._table, field=field)
        super(IrModuleModule, self).__init__(pool, cr)

    @api.model
    def update_list(self):
        res = super(IrModuleModule, self).update_list()
        for module in self.search([]):
            if module.icon:
                path_parts = module.icon.split('/')
                path = modules.get_module_resource(path_parts[1], *path_parts[2:])
            else:
                path = modules.module.get_module_icon(module.name)
            if not path :
                module.write({'missing':True})
            else :
                if module.missing :
                    module.write({'missing':False})
        return res
