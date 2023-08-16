from odoo import fields, models, api, _


class StockPickingTypeInherit(models.Model):
	_inherit = "stock.picking.type"

	plant_id = fields.Many2one("mrp.plant", _("Plant"))

	def get_mrp_stock_picking_action_picking_type(self):
		res = super(StockPickingTypeInherit, self).get_mrp_stock_picking_action_picking_type()
		# res['context']['search_default_by_plants'] = 1
		print("Res", res['context'], type(res['context']))
		if 'context' in res:
			context = eval(res['context'])

		else:
			context = {}

		if 'default_picking_type_id' in eval(res['context']):
			context['default_picking_type_id'] = self.id

		context['search_default_group_by_planning'] = 1
		context['search_default_group_by_section'] = 1
		context['search_default_group_by_packaging_line_id'] = 1
		res['context'] = str(context)
		print("Res exec")
		return res




class StockPickingInherit(models.Model):
	_inherit = "stock.picking"

	planning_id = fields.Many2one('mrp.planning', string="Planning")