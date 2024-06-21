from odoo.tools import float_repr, float_round, frozendict, html_sanitize, human_size, pg_varchar,\
    ustr, OrderedSet, pycompat, sql, date_utils
import odoo


def convert_to_column(self, value, record, values=None, validate=True):
    result = float(value or 0.0)
    digits = self.digits
    if digits:
        precision, scale = digits
        result = float_repr(float_round(result, precision_digits=scale), precision_digits=scale)
    # custom Miftah
    exceptions = (self.model_name == 'uom.uom' and self.name == 'rounding') \
        or (self.model_name == 'bsp.stock.card.line' and self.name in ['in_qty', 'out_qty', 'balance_qty'])
    if not exceptions:
        if 'e' in str(result):
            digit = str(result).split('-')[-1]
            result = format(float(result), f'.{digit}f')
        if '.000' in str(result):
            res_list = str(result).split('.')
            result = f'{res_list[0]}.{"0"*len(res_list[1])}'
    # end of custom by Miftah
    return result


odoo.fields.Float.convert_to_column = convert_to_column
