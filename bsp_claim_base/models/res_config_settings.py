from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_websocket = fields.Boolean(
        string='Use Websocket ?',
        readonly=False,
        related='company_id.use_websocket',
    )