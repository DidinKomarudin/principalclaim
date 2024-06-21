from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning
from odoo.addons import decimal_precision as dp
import math

class UomUom(models.Model):
    _inherit = 'uom.uom'

    # digits di sini gak ngaruh, diset di xml
    rounding = fields.Float(digits=dp.get_precision('UoM Convertion'), default=0.00000001)
    # menyebabkan eror ketika create UoM dengan uom_type reference
    # factor = fields.Float(digits=dp.get_precision('UoM Convertion'))
    # factor_inv = fields.Float(digits=dp.get_precision('UoM Convertion'))

    @api.model
    def create(self, values):
        if not values.get('rounding', 0):
            values['rounding'] = 0.00000001
        return super(UomUom, self).create(values)

    def get_all_same_uom_category(self):
        self.ensure_one()
        uom_ids = self.search([
            ('category_id','=',self.category_id.id),
        ], order='factor')
        return uom_ids

    def get_uom_string_conversion(self, qty):
        if not self or not qty:
            return ''
        self.ensure_one()
        uom_dict = self.get_uom_dict_conversion(qty)
        uom_names = []
        for level, qty in uom_dict.items():
            uom_id = self.search([
                ('category_id','=',self.category_id.id),
                ('uom_level_desc','=',level),
            ], limit=1)
            uom_names += ['%d %s' % (qty, uom_id.display_name)]
        return ', '.join(uom_names)

    def get_uom_dict_conversion(self, qty):
        if not self or not qty :
            return {}
        self.ensure_one()
        uom_dict = {}
        uom_ids = self.get_all_same_uom_category()
        # convert dulu ke UoM terkecil
        smallest_uom_id = self.get_smallest_uom_id()
        qty = self._convert_to_smallest(qty)
        pref_level = False
        for uom_id in uom_ids :
            if not qty:
                break
            uom_qty = smallest_uom_id._compute_quantity(qty, uom_id)
            if uom_id != smallest_uom_id:
                current_qty = int(uom_qty)
            else:
                current_qty = round(uom_qty)
                # cek lagi kemungkinan hasil rounding masih memenuhi 1 qty uom sebelumnya
                if pref_level:
                    prev_uom_id = self.search([
                        ('category_id','=',self.category_id.id),
                        ('uom_level_desc','=',pref_level),
                    ], limit=1)
                    conversion_qty = prev_uom_id._compute_quantity(1, smallest_uom_id) - 1
                    if current_qty > conversion_qty :
                        uom_dict[pref_level] = uom_dict.get(pref_level, 0) + 1
                        break
            if current_qty and abs(uom_qty) > abs(current_qty):
                qty = uom_qty % current_qty
            elif not current_qty and uom_qty:
                qty = uom_qty
            else:
                qty = 0
            if current_qty:
                uom_dict[uom_id.uom_level_desc] = current_qty
            # convert lagi ke UoM terkecil
            qty = uom_id._convert_to_smallest(qty)
            pref_level = uom_id.uom_level_desc
        return uom_dict

    def _compute_quantity(self, qty, to_unit, round=False, rounding_method='UP', raise_if_failure=True):
        if not to_unit :
            return qty
        return super(UomUom, self)._compute_quantity(qty=qty, to_unit=to_unit, round=round, rounding_method=rounding_method, raise_if_failure=raise_if_failure)

    def _round_decimal_min_qty(self, qty):
        frac, whole = math.modf(qty)
        if frac:
            smallest_uom = self.search([
                ('category_id', '=', self.category_id.id),
            ], limit=1, order='uom_level_desc desc')
            if smallest_uom:
                # FIXME
                # ga bisa pakai field factor_inv, karena bisa jadi reference nya bukan uom terbesar
                min_qty_uom = smallest_uom.factor_inv
                if abs(frac) < min_qty_uom:
                    qty = whole
                # elif abs(frac) > min_qty_uom:
                #     count_min_uom, remaining_qty = divmod(abs(frac), min_qty_uom)
                #     if remaining_qty:
                #         qty = qty - remaining_qty
                # else:
                #     return qty
        return qty

    @api.multi
    def compute_quantity_mobile(self, uom, uom_result, qty):
        return uom._compute_quantity(qty, uom_result)

    def get_uom_specific_level(self, qty_done1, qty_done2, qty_done3, qty_done4):
        self.ensure_one()
        uom_level_desc = []
        if qty_done1:
            uom_level_desc.append(1)
        if qty_done2:
            uom_level_desc.append(2)
        if qty_done3:
            uom_level_desc.append(3)
        if qty_done4:
            uom_level_desc.append(4)
        uom_ids = self.search([('category_id', '=', self.category_id.id), ('uom_level_desc', 'in', uom_level_desc)], order='factor')
        return uom_ids

    def get_uom_dict_specific_level(self, qty, qty_done1, qty_done2, qty_done3, qty_done4):
        if not self or not qty:
            return {}
        self.ensure_one()
        uom_dict = {}
        uom_ids = self.get_uom_specific_level(qty_done1, qty_done2, qty_done3, qty_done4)
        # convert dulu ke UoM terkecil
        smallest_uom_id = self.get_smallest_uom_id()
        qty = self._convert_to_smallest(qty)
        pref_level = False
        for uom_id in uom_ids :
            if not qty:
                break
            uom_qty = smallest_uom_id._compute_quantity(qty, uom_id)
            uom_qty += 0.01
            if uom_id != smallest_uom_id:
                current_qty = int(uom_qty)
            else:
                current_qty = round(uom_qty)
                # cek lagi kemungkinan hasil rounding masih memenuhi 1 qty uom sebelumnya
                if pref_level:
                    prev_uom_id = self.search([
                        ('category_id','=',self.category_id.id),
                        ('uom_level_desc','=',pref_level),
                    ], limit=1)
                    conversion_qty = prev_uom_id._compute_quantity(1, smallest_uom_id) - 1
                    if current_qty > conversion_qty :
                        uom_dict[pref_level] = uom_dict.get(pref_level, 0) + 1
                        break
            if current_qty and uom_qty > current_qty :
                qty = uom_qty % current_qty
            elif not current_qty and uom_qty :
                qty = uom_qty
            else:
                qty = 0
            if current_qty :
                uom_dict[uom_id.uom_level_desc] = current_qty
            # convert lagi ke UoM terkecil
            qty = uom_id._convert_to_smallest(qty)
            pref_level = uom_id.uom_level_desc
        return uom_dict

    def get_smallest_uom_level(self, is_sale=False, is_purchase=False, is_return=False, is_spreading=False):
        smallest_uom_id = self.get_smallest_uom_id(is_sale=is_sale, is_purchase=is_purchase, is_return=is_return, is_spreading=is_spreading)
        level1 = level2 = level3 = level4 = 0
        if smallest_uom_id.uom_level_desc == 1:
            level1 = 1
        if smallest_uom_id.uom_level_desc == 2:
            level2 = 1
        if smallest_uom_id.uom_level_desc == 3:
            level3 = 1
        if smallest_uom_id.uom_level_desc == 4:
            level4 = 1
        return {
            'level1': level1,
            'level2': level2,
            'level3': level3,
            'level4': level4,
        }