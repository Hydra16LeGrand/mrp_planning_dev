# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    def finished_product_transfer(self):
        print(f"self.product_id : {self.product_id}")
        quant_lst = []

        for rec in self:
            print(f"rec.location_id.temp_stock : {rec.location_id.temp_stock}")
            # quant_lst = []
            if not rec.location_id.temp_stock:
                quant_lst.append(rec.id)
            else:
                raise UserError(_("You cannot create a transfer from the packed stock to itself."))

        if quant_lst:
            # print(f"quant_lst : {quant_lst}")
            # action_context = []
            # for elm in quant_lst:
            #     quant = self.env['stock.quant'].browse(elm)
            #     val =
            #     action_context.append((0, 0, {
            #         'product_id': quant.product_id,
            #         'location_id': quant.location_id,
            #         'quantity': quant.quantity,
            #         'product_uom_id': quant.product_uom_id,
            #     }))
            action = self.env.ref('mrp_planning.action_picking_finished_product').read()[0]
            action['context'] = {
                'quant_line': quant_lst
            }
            print(f'action : {action}')
            return action