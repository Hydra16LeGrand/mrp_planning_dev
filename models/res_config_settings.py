from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
class ResConfigSettingsInherit(models.Model):
	_inherit = 'res.config.settings'

	code = fields.Char(String=("Code"))