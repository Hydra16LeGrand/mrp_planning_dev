from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class MrpPlant(models.Model):
	_name = "mrp.plant"
	_rec_name = "name"

	@api.depends('picking_type_id')
	def _compute_picking_type(self):
		for rec in self:
			picking_type_id = self.env['stock.picking.type'].search([('plant_id', '=', rec.id), ('code','=', 'mrp_operation')])
			rec.picking_type_id = picking_type_id[0].id if picking_type_id else False

	@api.depends('picking_type_internal')
	def _compute_picking_type_internal(self):
		for rec in self:
			picking_type_internal = self.env['stock.picking.type'].search([('plant_id', '=', rec.id), ('code', '=', 'internal')])
			rec.picking_type_internal = picking_type_internal[0].id if picking_type_internal else False

	def _compute_plant_mrp_locations(self):
		for rec in self:
			picking_type_id = self.env['stock.picking.type'].search([('plant_id', '=', rec.id), ('code','=', 'mrp_operation')])
			rec.default_location_src_id = picking_type_id.default_location_src_id.id if picking_type_id else False
			rec.default_location_dest_id = picking_type_id.default_location_dest_id.id if picking_type_id else False

	def _compute_plant_supply_locations(self):
		for rec in self:
			picking_type_id = self.env['stock.picking.type'].search([('plant_id', '=', rec.id), ('code','=', 'internal')])
			rec.supply_location_src_id = picking_type_id.default_location_src_id.id if picking_type_id else False
			rec.supply_location_dest_id = picking_type_id.default_location_dest_id.id if picking_type_id else False


	name = fields.Char(_("Name"), required=1)
	code = fields.Char(_("Short name"), required=1)
	company_id = fields.Many2one("res.company", _("Company"), default=lambda self: self.env.company, required=1)
	is_principal = fields.Boolean(_("Principal plant"), unique=True)
	default_location_src_id = fields.Many2one("stock.location", string=_("Default components location"), compute="_compute_plant_mrp_locations")
	default_location_dest_id = fields.Many2one("stock.location", string=_("Default finished products location"), compute="_compute_plant_mrp_locations")
	picking_type_id = fields.Many2one('stock.picking.type', 'Type of operation', compute='_compute_picking_type')
	picking_type_internal = fields.Many2one('stock.picking.type', 'Type of operation', compute='_compute_picking_type_internal')
	supply_location_src_id = fields.Many2one("stock.location", string=_("Default supply location"), compute="_compute_plant_supply_locations")
	supply_location_dest_id = fields.Many2one("stock.location", string=_("Default supply destination location"), compute="_compute_plant_supply_locations")

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
			if plant_id:
				raise ValidationError(_(f"This field is already checked in other plant ({plant_id}). This field have to be checked only once"))

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

	def picking_type_form_view(self):

		return {
			'type': 'ir.actions.act_window',
			'res_model': 'mrp.plant',  # Modèle de l'autre vue formulaire
			'view_mode': 'form',  # Mode d'affichage
			'view_id': False,  # ID de la vue (laisser à False pour utiliser la vue par défaut)
			'res_id': self.id,  # ID de l'enregistrement à afficher
			'target': 'current',  # Ouvrir dans la fenêtre courante
		}

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

	def action_mrp_planning_tree_name(self):
		# return {
		# 	'type': 'ir.actions.act_window',
		# 	'name': self.name,
		# 	'res_model': 'mrp.plant',
		# 	'view_mode': 'form',
		# 	'view_id': self.env.ref('mrp_planning.action_mrp_planning').id,
		# 	'res_id': self.id,
		# 	'context': {'search_default_by_plants': 1},
		# }
		action = self.env.ref('mrp_planning.action_mrp_planning').read()[0]
		action['context'] = {
			'search_default_plant_id': self.id,
		}
		action['name'] = self.name
		return action



