# from odoo import http


# class TrnFreight(http.Controller):
#     @http.route('/trn_freight/trn_freight', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/trn_freight/trn_freight/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('trn_freight.listing', {
#             'root': '/trn_freight/trn_freight',
#             'objects': http.request.env['trn_freight.trn_freight'].search([]),
#         })

#     @http.route('/trn_freight/trn_freight/objects/<model("trn_freight.trn_freight"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('trn_freight.object', {
#             'object': obj
#         })

