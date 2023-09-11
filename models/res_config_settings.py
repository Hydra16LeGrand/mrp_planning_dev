from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
class ResConfigSettingsInherit(models.TransientModel):
	_inherit = 'res.config.settings'

	code = fields.Char(_("Code"), config_parameter='mrp_planning.code')