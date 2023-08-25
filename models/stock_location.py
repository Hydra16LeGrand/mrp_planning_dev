from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StockLocationInherit(models.Model):
	_inherit = "stock.location"

	temp_stock = fields.Boolean(_("Raw material location"))
	plant_id = fields.Many2one("mrp.plant", string=_("Plant"))
	packaged_finished_product = fields.Boolean(string=_("Packaged finished product"))
	unpackaged_finished_product = fields.Boolean(string=_("Unpackaged finished product"))

	@api.onchange('temp_stock')
	def _onchange_temp_stock(self):
		if self.temp_stock:
			all_temp_stock = self.search_count([('temp_stock', '=', 1), ('plant_id', '=', self.plant_id.id)])
			
			if all_temp_stock != 0:
				raise ValidationError(_("A temp location already exists for this plant. Uncheck this one before this operation."))
			else:
				# packaged_finished_product = self.search_count([('packaged_finished_product', '=', 1), ('plant_id', '=', self.plant_id.id)])
				if self.packaged_finished_product:
					raise ValidationError(_("This location can't be both a temp location and a packaged finished product location."))
				if self.unpackaged_finished_product:
					raise ValidationError(_("This location can't be both an unpackaged finished product and a packaged finished product location."))

	@api.onchange('packaged_finished_product')
	def _onchange_packaged_finished_product(self):
		print("Seeeef", self.packaged_finished_product)
		if self.packaged_finished_product:
			all_packaged_finished_product = self.search_count([('packaged_finished_product', '=', 1), ('plant_id', '=', self.plant_id.id)])
			print("Alll loc", all_packaged_finished_product)
			if all_packaged_finished_product != 0:
				raise ValidationError(_("A packaged finished product location already exists for this plant. Uncheck this one before this operation."))
			else:
				# temp_stock = self.search_count([('temp_stock', '=', 1), ('plant_id', '=', self.plant_id.id)])
				if self.temp_stock:
					raise ValidationError(_("This location can't be both a temp location and a packaged finished product location."))
				if self.unpackaged_finished_product:
					raise ValidationError(_("This location can't be both an unpackaged finished product and a packaged finished product location."))

	@api.onchange('unpackaged_finished_product')
	def _onchange_unpackaged_finished_product(self):
		if self.unpackaged_finished_product:
			all_unpackaged_finished_product = self.search_count([('unpackaged_finished_product', '=', 1), ('plant_id', '=', self.plant_id.id)])
			if all_unpackaged_finished_product != 0:
				raise ValidationError(_("An unpackaged finished product location already exists for this plant. Uncheck this one before this operation."))
			else:
				if self.temp_stock:
					raise ValidationError(_("This location can't be both a temp location and an unpackaged finished product location."))
				if self.packaged_finished_product:
					raise ValidationError(_("This location can't be both an unpackaged finished product and a packaged finished product location."))