from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StockLocationInherit(models.Model):
	_inherit = "stock.location"

	temp_stock = fields.Boolean(_("Temp location"))
	# rm_stock = fields.Boolean(_("Raw materiel location"))
	# end_product_

	@api.onchange('temp_stock')
	def _onchange_temp_stock(self):
		print("Onchange temp", self.temp_stock, self.env['stock.location'].search_count([('temp_stock', '=', 1)]))
		if self.temp_stock:
			temp_stock = self.env['stock.location'].search_count([('temp_stock', '=', 1)])
			if temp_stock > 0:
				raise ValidationError(_("A Temp location already exists. Uncheck this one before this operation."))