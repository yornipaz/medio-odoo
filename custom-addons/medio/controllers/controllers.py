# -*- coding: utf-8 -*-
# from odoo import http


# class Medio(http.Controller):
#     @http.route('/medio/medio', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/medio/medio/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('medio.listing', {
#             'root': '/medio/medio',
#             'objects': http.request.env['medio.medio'].search([]),
#         })

#     @http.route('/medio/medio/objects/<model("medio.medio"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('medio.object', {
#             'object': obj
#         })
