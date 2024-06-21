# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from pymemcache.client.base import Client
from pymemcache.exceptions import MemcacheUnknownError
from odoo.addons.bsp_base.models.common import set_memcache, get_memcache, delete_memcache
import logging
import ast

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def button_scrap(self):
        set_memcache({"some_key": {'a':7, 'b':8}})
        set_memcache({"another_key": 3})
        delete_memcache("another_key")
        delete_memcache(["another_key","tidak_ada"])
        set_memcache({"key": "1", "key2": "2"})
        value = get_memcache("some_key")
        value3 = get_memcache(["some_key","key"])
