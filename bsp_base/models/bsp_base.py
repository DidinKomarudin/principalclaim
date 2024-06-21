from odoo import api, fields, models

class Base(models.AbstractModel):
    _name = "bsp.base"
    _description = "BSP Base"

    def get_fields_list(self):
        return self.env['ir.model.fields'].get_fields_to_change(self._name)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        fields_list = self.env['ir.model.fields'].get_fields_to_change(self._name)
        if self._context.get('source', 'odoo') == 'mobile' and not fields :
            fields = fields_list
        return super(Base, self).read(fields, load)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        fields_list = self.env['ir.model.fields'].get_fields_to_change(self._name)
        if self._context.get('source', 'odoo') == 'mobile' and not fields :
            fields = fields_list
        return super(Base, self).search_read(domain, fields, offset, limit, order)
