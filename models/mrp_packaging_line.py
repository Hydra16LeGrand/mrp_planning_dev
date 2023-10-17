# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class MrpPackagingLine(models.Model):
	"""
	Model for product proportion in packaging line
	"""
	_name = "mrp.packaging.line"
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_rec_name = "name"
	_order = "create_date desc"

	name = fields.Char(_("Name"), required=True)
	code = fields.Char(_("Code"))

	ppp_ids = fields.One2many("mrp.packaging.pp", "packaging_line_id", string=_("Products proportions"))


class MrpPackagingPP(models.Model):
	_name = "mrp.packaging.pp"
	_description = "Mrp packaging product proportion"

	@api.depends('product_id')
	def _compute_uom(self):
		for line in self:
			if not line.uom_id or (line.product_id.uom_id.id != line.uom_id.id):
				line.uom_id = line.product_id.uom_id

	product_id = fields.Many2one('product.product', string=_("Product"), required=True)
	qty = fields.Integer(_("Quantity"))
	capacity = fields.Float(_("Max capacity per day"), required=True)
	employee_number = fields.Integer(_("EN"))

	uom_category_id = fields.Many2one(related="product_id.uom_id.category_id", depends=['product_id'])
	uom_id = fields.Many2one("uom.uom", _("Unit of measure"), compute="_compute_uom", required=1)

	packaging_line_id = fields.Many2one("mrp.packaging.line")