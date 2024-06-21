from odoo import fields, api, models, _
from odoo.exceptions import Warning
from lxml import etree


class BaseWizard(models.TransientModel):
    _name = "base.wizard"
    _description = "Base Wizard"

    name = fields.Char()
    action = fields.Char(
        help='Implement if we need call this wizard from many buttons with different action in same model')

    @api.multi
    def action_confirm(self):
        if self._context.get('active_model') and self._context.get('active_id'):
            rec_id = self.get_rec_id()
            rec_ids = self.get_rec_ids()
        else:
            rec_id = rec_ids = self
        return self._action_confirm(rec_id, rec_ids)

    @api.multi
    def _action_confirm(self, rec_id, rec_ids):
        raise Warning(_("Action not implemented."))

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(BaseWizard, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self._context.get('button_string'):
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//button[@name='action_confirm']"):
                node.set('string', self._context.get('button_string'))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def get_rec_id(self):
        return self.env[self._context['active_model']].browse(self._context['active_id'])

    def get_rec_ids(self):
        return self.env[self._context['active_model']].browse(self._context['active_ids'])
