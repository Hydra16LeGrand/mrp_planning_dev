from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class MrpProductionInherit(models.Model):
	_inherit = "mrp.production"

	package = fields.Float(_("Package"))
	qty = fields.Integer(_("Quantity"))
	capacity = fields.Integer(_("Capacity"))
	employee_number = fields.Integer(_("EN"))

	product_ref = fields.Char(string=_("Article"))

	detailed_pl_id = fields.Many2one("mrp.detail.planning.line", string=_("Detailed planning lines"))
	packaging_line_id = fields.Many2one("mrp.packaging.line")
	section_id = fields.Many2one("mrp.section")
	planning_line_id = fields.Many2one("mrp.planning.line")
	planning_id = fields.Many2one("mrp.planning")


	def action_view_planning(self):

		action = {
			"name": "Mrp planning",
			"res_model": "mrp.planning",
			"type": "ir.actions.act_window",
			"view_mode": "form",
			"res_id": self.planning_id.id,
			"view_id": self.env.ref("mrp_planning.mrp_planning_form").id,
		}

		return action