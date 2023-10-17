# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class MrpTeam(models.Model):
	_name = "mrp.team"
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_rec_name = "name"
	_order = "create_date desc"

	name = fields.Char(_("Name"))
	number = fields.Char(_("Number"))

	employee_ids = fields.One2many("hr.employee", "team_id", string=_("Employees"))
	planning_id = fields.Many2one("mrp.planning")