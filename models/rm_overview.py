from odoo import fields, models, api, _


class RM_Overview(models.Model):
	_name = "rm.overview"

	product_id = fields.Many2one("product.product", string=_("Raw materiel"))
	required_qty = fields.Integer(_("Required qty"))
	on_hand_qty = fields.Integer(_("On hand qty"))
	missing_qty = fields.Integer(_("Missing qty"))
	uom_id = fields.Many2one("uom.uom", string=_("Unit of measure"))

	bom_id = fields.Many2one("mrp.bom", string=_("Bill of material"))
	detail_line_id = fields.Many2one("mrp.detail.planning.line")
	planning_line_id = fields.Many2one(related="detail_line_id.planning_line_id")
	planning_id = fields.Many2one(related="detail_line_id.planning_id")