from odoo import fields, models, api, _


class StockPickingTypeInherit(models.Model):
	_inherit = "stock.picking.type"

	plant_id = fields.Many2one("mrp.plant", _("Plant"))

	def get_mrp_stock_picking_action_picking_type(self):
		# res = super(StockPickingTypeInherit, self).get_mrp_stock_picking_action_picking_type()
		# # res['context']['search_default_by_plants'] = 1
		# print("Res", res['context'], type(res['context']))
		# if 'context' in res:
		# 	context = eval(res['context'])

		# else:
		# 	context = {}

		# if 'default_picking_type_id' in eval(res['context']):
		# 	context['default_picking_type_id'] = self.id

		# context['search_default_group_by_planning'] = 1
		# context['search_default_group_by_section'] = 1
		# context['search_default_group_by_packaging_line_id'] = 1
		# res['context'] = str(context)
		# print("Res exec")

		action = {
			'name': "Manufacturing Orders",
			'type': "ir.actions.act_window",
			'res_model': "mrp.production",
			'view_mode': "tree,kanban,form,calendar,pivot,graph",
			'search_view_id': self.env.ref('mrp.view_mrp_production_filter').id,
			'context': {
				'search_default_todo': True,
			  'default_company_id': self.env.company.id,

			  # 'search_default_by_plants': 1,
			  'search_default_group_by_planning':1,
			  'search_default_group_by_section':1,
			  'search_default_group_by_packaging_line_id':1,
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




class StockPickingInherit(models.Model):
	_inherit = "stock.picking"

	planning_id = fields.Many2one('mrp.planning', string="Planning")