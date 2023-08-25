from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StockLocationInherit(models.Model):
	_inherit = "stock.location"

	temp_stock = fields.Boolean(_("Temp location"))
	plant_id = fields.Many2one("mrp.plant", string=_("Plant"))
	packaged_finished_product = fields.Boolean(string=_("Packaged finished product"))


	@api.onchange('temp_stock')
	def _onchange_temp_stock(self):
		if self.temp_stock:
			temp_stock = self.search_count([('temp_stock', '=', 1), ('plant_id', '=', self.plant_id.id)])
			if temp_stock > 1:
				raise ValidationError(_("A temp location already exists. Uncheck this one before this operation."))
			else:
				# packaged_finished_product = self.search_count([('packaged_finished_product', '=', 1), ('plant_id', '=', self.plant_id.id)])
				if self.packaged_finished_product:
					raise ValidationError(_("This location can't be both a temp location and a packaged finished product location."))

	@api.onchange('packaged_finished_product')
	def _onchange_packaged_finished_product(self):
		if self.packaged_finished_product:
			packaged_finished_product = self.search_count([('packaged_finished_product', '=', 1), ('plant_id', '=', self.plant_id.id)])
			if packaged_finished_product > 1:
				raise ValidationError(_("A packaged finished product location already exists. Uncheck this one before this operation."))
			else:
				# temp_stock = self.search_count([('temp_stock', '=', 1), ('plant_id', '=', self.plant_id.id)])
				if self.temp_stock:
					raise ValidationError(_("This location can't be both a temp location and a packaged finished product location."))