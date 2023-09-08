from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class MrpBom(models.Model):
    _inherit = "mrp.bom"

    packing = fields.Float(string=("Packing"))


