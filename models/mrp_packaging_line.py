from odoo import fields, models, api, _


class MrpPackagingLine(models.Model):
	_name = "mrp.packaging.line"
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_rec_name = "name"
	_order = "create_date desc"

	name = fields.Char(_("Name"), required=True)
	code = fields.Char(_("Code"))

	ppp_ids = fields.One2many("mrp.packaging.pp", "packaging_line_id", string=_("Products proportions"))
	section_id = fields.Many2one("mrp.section", string=_("Section"))


class MrpPackagingPP(models.Model):
	_name = "mrp.packaging.pp"
	_description = "Mrp packaging product proportion"

	product_id = fields.Many2one('product.product', string=_("Product"), required=True)
	qty = fields.Integer(_("Quantity"), required=True)
	capacity = fields.Float(_("Capacity"), required=True)
	employee_number = fields.Integer(_("EN"))

	packaging_line_id = fields.Many2one("mrp.packaging.line")