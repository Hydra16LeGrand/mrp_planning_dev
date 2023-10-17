# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResConfigSettingsInherit(models.TransientModel):
	_inherit = 'res.config.settings'

	code = fields.Char(_("Code"), config_parameter='mrp_planning.code')