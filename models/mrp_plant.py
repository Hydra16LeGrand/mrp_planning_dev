from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class MrpPlant(models.Model):
	_name = "mrp.plant"
	_rec_name = "name"

	name = fields.Char(_("Name"), required=1)
	code = fields.Char(_("Short name"), required=1)
	company_id = fields.Many2one("res.company", _("Company"), default=lambda self: self.env.company, required=1)
	is_principal = fields.Boolean(_("Principal plant"))
	default_location_src_id = fields.Many2one("stock.location", string=_("Default components location"))
	default_location_dest_id = fields.Many2one("stock.location", string=_("Default finished products location"))

	_sql_constraints = [
        ('warehouse_code_uniq', 'unique(code, company_id)', 'The short name of the plant must be unique per company!'),
    ]

	@api.onchange('is_principal')
	def _onchange_is_principal(self):

		if self.is_principal:
			plant_id = self.search([('is_principal', '=', True)])
			print("Plant", plant_id)
			if plant_id:
				raise ValidationError(_(f"This field is already checked in other plant ({plant_id}). This field have to be checked only once"))
