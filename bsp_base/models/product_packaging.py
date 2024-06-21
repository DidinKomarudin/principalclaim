from odoo import api, fields, models


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'


    def get_ratio_pallet(self, quantity, product_id, package_storage_type_id, uom_id):
        # pakai limit karena pada saat mix product dalam satu pallet tidak ada parameter
        # yg menentukan product tersebut menggunakan packaging tertentu.
        product_packaging = self.search([
            ('product_id', '=', product_id.id),
            ('package_storage_type_id', '=', package_storage_type_id.id)
        ], limit=1)
        quantity = uom_id._compute_quantity(quantity, product_packaging.product_uom_id)
        ratio = quantity / product_packaging.qty if product_packaging.qty else 0
        return ratio

    def get_product_packaging(self, product_id, package_storage_type_id):
        product_packaging = self.env['product.packaging'].search([
            ('product_id', '=', product_id.id),
            ('package_storage_type_id', '=', package_storage_type_id.id)
        ], limit=1)
        return product_packaging