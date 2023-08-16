from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class MrpBomInherit(models.Model):
	_inherit = "mrp.bom"

	capacity = fields.Float(string=_("Capacity"), default=1)
	packing = fields.Float(string=_("Packing"), default=1)	


class MrpBomLineInherit(models.Model):
	_inherit = "mrp.bom.line"

	percentage = fields.Float(string=_("Percentage"))
	product_qty = fields.Float(default=0)

	@api.onchange('percentage')
	def _update_qty_onchange_percentage(self):
		# self = self._origin
		print("Fonc exec", self, self.percentage, self.product_qty)
		if self.percentage != 0:
			self.product_qty = self.percentage / 100
			print(self.product_qty)
		else:
			self.product_qty = 0

	@api.onchange('product_qty')
	def _update_percentage_onchange_qty(self):
		# self = self._origin
		self.percentage = self.product_qty * 100
		print("Fonc exec 2", self.percentage, self)

	@api.onchange('percentage')
	def _verif_total_percentage(self):
		print("Cerif total ok", self.bom_id.bom_line_ids)
		total = 0
		for rec in self.bom_id.bom_line_ids:
			total += rec.percentage
			if total > 100:
				raise ValidationError(_("Total percentage don't have to exceed 100%"))
