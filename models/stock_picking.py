# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StockPickingTypeInherit(models.Model):
    _inherit = "stock.picking.type"

    def get_mrp_stock_picking_action_picking_type(self):
        action = {
            'name': "Manufacturing Orders",
            'type': "ir.actions.act_window",
            'res_model': "mrp.production",
            'view_mode': "tree,kanban,form,calendar,pivot,graph",
            'search_view_id': self.env.ref('mrp.view_mrp_production_filter').id,
            'context': {
                'search_default_todo': True,
                'default_company_id': self.env.company.id,

                'search_default_group_by_planning': 1,
                'search_default_group_by_section': 1,
                'search_default_group_by_packaging_line_id': 1,
            },
            'domain': [('picking_type_id.active', '=', True)],
            'help': """
				<p class="o_view_nocontent_smiling_face">
	                No manufacturing order found. Let's create one.
	              </p><p>
	                Consume <a name="%(product.product_template_action)d" type='action' tabindex="-1">components</a> and build finished products using <a name="%(mrp_bom_form_action)d" type='action' tabindex="-1">bills of materials</a>
	              </p>
			"""
        }
        return action

    def write(self, vals):

        if self.code == 'internal':  # Vérifier le type d'opération
            if vals.get('default_location_src_id'):
                self.plant_id.supply_location_src_id = vals.get('default_location_src_id')
            if vals.get('default_location_dest_id'):
                self.plant_id.supply_location_dest_id = vals.get('default_location_dest_id')

        res = super(StockPickingTypeInherit, self).write(vals)
        return res


class StockPickingInherit(models.Model):
    _inherit = "stock.picking"

    planning_id = fields.Many2one('mrp.planning', string="Planning")
