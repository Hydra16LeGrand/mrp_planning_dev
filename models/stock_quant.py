# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    def finished_product_transfer(self):
        quant_lst = []

        for rec in self:
            # quant_lst = []
            if rec.location_id.unpackaged_finished_product:
                quant_lst.append(rec.id)
            elif rec.location_id.temp_stock:
                raise UserError(_("You cannot create a transfer from a Raw Material location."))
            elif rec.location_id.packaged_finished_product:
                raise UserError(_("You cannot create a transfer from a finished product location."))
            else:
                raise UserError(_("You cannot create a transfer from this location."))

        if quant_lst:
            # action = self.env.ref('mrp_planning.action_picking_finished_product').read()[0]
            # action['context'] = {
            #     'quant_line': quant_lst
            # }
            action = {
                "name": "Picking Finished Product",
                "res_model": "create.picking.finished.product",
                "type": "ir.actions.act_window",
                "view_mode": "form",
                # "view_id": self.env.ref("view_create_overview_wizard_from").id,
                'target': 'new',
                "context": {
                    'quant_line': quant_lst,
                },
            }

            return action

    def calculating_packs(self):
        quant_lst = []
        for rec in self:
            if rec.location_id.packaged_finished_product and rec.pack_of:
                quant_lst.append(rec.id)
            else:
                raise UserError(_("You cannot calculate the packs of these transfers"))

        if quant_lst:
            action = self.env.ref('mrp_planning.action_calculating_packs').read()[0]
            action['context'] = {
                'quant_line': quant_lst
            }
            return action

    # pack_of_bool = fields.Boolean(compute="_compute_pack_of_bool")
    pack_of_bool = fields.Selection([
        ('true', 'True'),
        ('false', 'False'),
    ], compute="_compute_pack_of_bool")
    pack_of = fields.Char('Pack Of')
    package = fields.Integer('Package')
    pack = fields.Integer('Pack')

    @api.depends('pack_of')
    def _compute_pack_of_bool(self):
        for rec in self:
            if rec.pack_of:
                print(f"rec.pack_of : {rec.pack_of}")
                rec.pack_of_bool = "true"
            else:
                rec.pack_of_bool = "false"
