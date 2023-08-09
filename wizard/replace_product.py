from odoo import fields, models, api, _
from odoo.exceptions import UserError


# Model use for replacement of a product in a manufacturing order by a planning
class ReplaceProduct(models.TransientModel):
	_name = "replace.product"
	_description = "Replace product in a planning"

	@api.depends("product_to_replace")
	def _compute_product_to_replace_domain(self):
		for rec in self:
			if rec.planning_id:
				product_ids = []
				production_ids = self.get_draft_production_orders()
				for line in production_ids:
					product_ids.append(line.product_id.id) 
				rec.product_to_replace_domain = list(set(product_ids))

	@api.depends("product_to_replace")
	def _compute_replacement_days(self):
		for rec in self:
			if rec.planning_id:
				days = []
				production_ids = self.get_draft_production_orders()
				for production in production_ids:
					days.append(rec.get_day_from_date(production.date_planned_start.date()))
				rec.replacement_days_domain = list(set(days))
			else:
				rec.replacement_days_domain = []

	def get_draft_production_orders(self):
		return self.planning_id.mrp_production_ids.filtered(lambda self: self.state not in ['done', 'cancel'])

	def get_day_from_date(self, production_date):
		# iso = production_date.isocalendar()
		day = self.env['mrp.planning.days'].search([('date', '=', production_date)])
		return day.id

	product_to_replace = fields.Many2one("product.product", string=_("Product to replace"), required=True)
	product_to_replace_domain = fields.Many2many("product.product", compute="_compute_product_to_replace_domain")
	replacement_product = fields.Many2one("product.product", string=_("Replacement product"), required=True)
	replacement_days_domain = fields.Many2many("mrp.planning.days", compute="_compute_replacement_days")
	replacement_days = fields.Many2many("mrp.planning.days", string=_("Replacement days"), required=True)

	planning_id = fields.Many2one("mrp.planning", string=_("Planning"))


	def action_replace_product(self):
		for rec in self:
			day_list = [day.name for day in rec.replacement_days]
			mrp_production = self.env['mrp.production'].sudo().search([
				('planning_id', '=', rec.planning_id.id)
			])
			mrp_list = [mrp for mrp in mrp_production.detailed_pl_id if any(
				day in mrp.date_char and mrp.product_id.id == rec.product_to_replace.id for day in day_list)]
			production_list = [mrp for mrp in mrp_production if mrp.detailed_pl_id in mrp_list]
			print(f'production_list : {production_list}')

			if production_list:
				for production in production_list:
					if production.state not in ['done', 'cancel']:
						for line in production.detailed_pl_id:
							if any(day in line.date_char for day in day_list):
								line.product_id = rec.replacement_product.id

						bom_id = self.env["mrp.bom"].search([('product_tmpl_id', '=', rec.replacement_product.product_tmpl_id.id)])
						if bom_id:
							old_qty = production.product_qty
							old_move_raw_ids = production.move_raw_ids
							production.bom_id = bom_id
							production.product_id = rec.replacement_product.id
							production.product_qty = old_qty
							for move in production.move_raw_ids:
								for old_move in old_move_raw_ids:
									if move == old_move:
										move.unlink()
						else:
							raise UserError(_("You can't select this product as a replacement because it doesn't have a bill of materials"))
			else:
				raise UserError(_("There are no manufacturing orders for this product for these days."))

