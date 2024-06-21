from odoo import api, fields, models, SUPERUSER_ID, _


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    to_change = fields.Boolean(
        string='To Change'
    )

    def __init__(self, pool, cr):
        field_datas = [
            {"field_name": "to_change", "type": "boolean"},
        ]
        env = api.Environment(cr, SUPERUSER_ID, {})
        for field in field_datas:
            env.user.add_related_fields(table_name=self._table, field=field)
        super(IrModelFields, self).__init__(pool, cr)

    @api.multi
    def generate_to_change(self):
        for rec in self:
            if not rec.to_change:
                to_change = True
            else:
                to_change = False
            rec._cr.execute(
                """ 
                UPDATE ir_model_fields 
                SET to_change = %s
                WHERE id = %s
                """
                % (to_change, rec.id)
            )

    def get_fields_to_change(self, model):
        fields_ids = self.sudo().search([
            ('to_change','=',True),
            ('model_id','=',model),
        ])
        fields_list = [f['name'] for f in fields_ids]
        # self.env.user.log_info(f'model: {model}, fields: {fields_list}')
        return fields_list
