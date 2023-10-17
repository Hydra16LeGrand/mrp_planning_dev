# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class HrEmployeeInherit(models.Model):
	_inherit = "hr.employee"

	team_id = fields.Many2one("mrp.team", string=_("Team"))
