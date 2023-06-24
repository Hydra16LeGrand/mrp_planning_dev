from odoo import fields, models, api, _


class MrpSection(models.Model):
	_name = "mrp.section"
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_rec_name = "name"
	_order = "create_date desc"

	name = fields.Char(_("Name"))

	planning_id = fields.Many2one("mrp.planning")