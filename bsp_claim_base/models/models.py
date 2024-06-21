from odoo import fields, models, api
import odoo
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)

# @api.multi
# def read(self, fields=None, load='_classic_read'):
#     """ read([fields])
#
#     Reads the requested fields for the records in ``self``, low-level/RPC
#     method. In Python code, prefer :meth:`~.browse`.
#
#     :param fields: list of field names to return (default is all fields)
#     :return: a list of dictionaries mapping field names to their values,
#              with one dictionary per record
#     :raise AccessError: if user has no read rights on some of the given
#             records
#     """
#     # check access rights
#     self.check_access_rights('read')
#     fields = self.check_field_access_rights('read', fields)
#
#     # split fields into stored and computed fields
#     stored, inherited, computed = [], [], []
#     for name in fields:
#         field = self._fields.get(name)
#         if field:
#             if field.store:
#                 stored.append(name)
#             elif field.base_field.store:
#                 inherited.append(name)
#             else:
#                 computed.append(name)
#         else:
#             _logger.warning("%s.read() with unknown field '%s'", self._name, name)
#
#     # fetch stored fields from the database to the cache; this should feed
#     # the prefetching of secondary records
#     self._read_from_database(stored, inherited)
#
#     # retrieve results from records; this takes values from the cache and
#     # computes remaining fields
#     self = self.with_prefetch(self._prefetch.copy())
#     data = [(record, {'id': record._ids[0]}) for record in self]
#     use_name_get = (load == '_classic_read')
#     for name in (stored + inherited + computed):
#         convert = self._fields[name].convert_to_read
#         # restrict the prefetching of self's model to self; this avoids
#         # computing fields on a larger recordset than self
#         self._prefetch[self._name] = set(self._ids)
#         for record, vals in data:
#             # missing records have their vals empty
#             if not vals:
#                 continue
#             try:
#                 vals[name] = convert(record[name], record, use_name_get)
#             except MissingError:
#                 vals.clear()
#
#             # start custom by Miftah
#             # diconvert ke string karna formatnya jadi aneh. misal 0.00000001 jadi 1e-08 (float)
#             if type(vals.get(name, '')) is float:
#                 vals_string = str(vals[name])
#                 if 'e' in vals_string or 'E' in vals_string :
#                     str_format = '{:.%sf}'%(int(vals_string[-1]))
#                     vals[name] = str_format.format(vals[name])
#             # end custom by Miftah
#     result = [vals for record, vals in data if vals]
#
#     return result
#
# odoo.models.BaseModel.read = read
