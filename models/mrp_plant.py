from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class MrpPlant(models.Model):
	_name = "mrp.plant"
	_rec_name = "name"

	@api.depends('picking_type_id')
	def _compute_picking_type(self):
		self.picking_type_id = self.env['stock.picking.type'].search([('plant_id', '=', self.id)]).name
		print("le picking", self.picking_type_id)


	name = fields.Char(_("Name"), required=1)
	code = fields.Char(_("Short name"), required=1)
	company_id = fields.Many2one("res.company", _("Company"), default=lambda self: self.env.company, required=1)
	is_principal = fields.Boolean(_("Principal plant"), unique=True)
	default_location_src_id = fields.Many2one("stock.location", string=_("Default components location"))
	default_location_dest_id = fields.Many2one("stock.location", string=_("Default finished products location"))
	picking_type_id = fields.Char('Type of operation', compute='_compute_picking_type')

	_sql_constraints = [
        ('warehouse_code_uniq', 'unique(code, company_id)', 'The short name of the plant must be unique per company!'),
    ]

	count_mrp_planning_draft = fields.Integer(compute='_compute_mrp_planning_count')
	count_mrp_planning_confirm = fields.Integer(compute='_compute_mrp_planning_count')
	count_mrp_planning = fields.Integer(compute='_compute_mrp_planning_count')
	count_mrp_planning_generated = fields.Integer(compute='_compute_mrp_planning_count')
	count_mrp_planning_cancel = fields.Integer(compute='_compute_mrp_planning_count')

	def _compute_mrp_planning_count(self):
		domains = {
			'count_mrp_planning_draft': [('state', '=', 'draft')],
			'count_mrp_planning_confirm': [('state', '=', 'confirm')],
			'count_mrp_planning_generated': [('state', '=', '04_mo_generated')],
			'count_mrp_planning': [('state', 'in', ('confirm', 'confirm', '04_mo_generated'))],
			'count_mrp_planning_cancel': [('state', '=', 'cancel')],
		}

		for field in domains:
			data = self.env['mrp.planning'].read_group(domains[field] + [('plant_id', 'in', self.ids)], ['plant_id'], ['plant_id'])
			count = {
				x['plant_id'][0]: x['plant_id_count']
				for x in data if x['plant_id']
			}
			for record in self:
				record[field] = count.get(record.id, 0)

	@api.onchange('is_principal')
	def _onchange_is_principal(self):

		if self.is_principal:
			plant_id = self.search([('is_principal', '=', True)])
			print("Plant", plant_id)
			if plant_id:
				raise ValidationError(_(f"This field is already checked in other plant ({plant_id}). This field have to be checked only once"))



	@api.model
	def create(self, vals):

		# Create a picking type for this plant
		picking_type = {
			'name': _(f"{vals.get('name')} manufacturing"),
			'code': "mrp_operation",
			'sequence_code': "MO",
			'default_location_src_id': vals.get('default_location_src_id', False),
			'default_location_dest_id': vals.get('default_location_dest_id', False),
		}

		res = super().create(vals)

		picking_type['plant_id'] = res.id

		picking_type_id = self.env['stock.picking.type'].create(picking_type)

		return res


	def write(self, vals):

		res = super(MrpPlant, self).write(vals)
		if self:
			picking_type_id = self.env['stock.picking.type'].search([('plant_id', '=', self.id)])

			if picking_type_id:
				if len(picking_type_id) == 1:
					if vals.get('default_location_src_id', False):
						picking_type_id.default_location_src_id = vals.get('default_location_src_id')
					if vals.get('default_location_dest_id', False):
						picking_type_id.default_location_dest_id = vals.get('default_location_dest_id')
				else:
					raise ValidationError(_(""))

		return res

	def get_mrp_planning_action(self):
		action = self.env.ref('mrp_planning.action_mrp_planning').read()[0]
		action['context'] = {
			'search_default_plant_id': self.id,
		}
		return action

	def get_plant_configuration(self):
		action = self.env.ref('mrp_planning.action_mrp_plant_conf').read()[0]
		action['context'] = {
			'search_default_name': self.name,
		}
		return action

	def get_action_mrp_planning_tree_draft(self):
		action = self.env.ref('mrp_planning.action_mrp_planning').read()[0]
		action['context'] = {
			'search_default_plant_id': self.id,
		}
		action['domain'] = [('state','=','draft')]
		return action

	def get_action_mrp_planning_confirm(self):
		action = self.env.ref('mrp_planning.action_mrp_planning').read()[0]
		action['context'] = {
			'search_default_plant_id': self.id,
		}
		action['domain'] = [('state','=','confirm')]
		return action

	def get_action_mrp_planning_tree_generated(self):
		action = self.env.ref('mrp_planning.action_mrp_planning').read()[0]
		action['context'] = {
			'search_default_plant_id': self.id,
		}
		action['domain'] = [('state','=','04_mo_generated')]
		return action

	def get_action_mrp_planning_tree_cancel(self):
		action = self.env.ref('mrp_planning.action_mrp_planning').read()[0]
		action['context'] = {
			'search_default_plant_id': self.id,
		}
		action['domain'] = [('state','=','cancel')]
		return action

