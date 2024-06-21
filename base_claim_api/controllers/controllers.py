# -*- coding: utf-8 -*-
from odoo import http

# class BaseApi(http.Controller):
#     @http.route('/base_api/base_api/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/base_api/base_api/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('base_api.listing', {
#             'root': '/base_api/base_api',
#             'objects': http.request.env['base_api.base_api'].search([]),
#         })

#     @http.route('/base_api/base_api/objects/<model("base_api.base_api"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('base_api.object', {
#             'object': obj
#         })