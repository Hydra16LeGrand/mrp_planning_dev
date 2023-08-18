from odoo import fields, models, api, _
from datetime import date, datetime
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict


class MrpPlanning(models.Model):
	_name = "mrp.planning"
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_rec_name = "reference"
	_order = "scheduled_date desc"

	today_date = fields.Date.today()
	iso = today_date.isocalendar()

	monday = date.fromisocalendar(year=iso[0], week=iso[1], day=1)
	tuesday = date.fromisocalendar(year=iso[0], week=iso[1], day=2)
	wednesday = date.fromisocalendar(year=iso[0], week=iso[1], day=3)
	thursday = date.fromisocalendar(year=iso[0], week=iso[1], day=4)
	friday = date.fromisocalendar(year=iso[0], week=iso[1], day=5)

	week_days = [
        'monday {}/{}'.format(monday.strftime('%d'), monday.month),
        'tuesday {}/{}'.format(tuesday.strftime('%d'), tuesday.month),
        'wednesday {}/{}'.format(wednesday.strftime('%d'), wednesday.month),
        'thursday {}/{}'.format(thursday.strftime('%d'), thursday.month),
        'friday {}/{}'.format(friday.strftime('%d'), friday.month),
    ]


	def _get_default_week_of(self):
		today_date = fields.Date.today()
		iso = today_date.isocalendar()
		monday = date.fromisocalendar(year=iso[0], week=iso[1], day=1)
		tuesday = date.fromisocalendar(year=iso[0], week=iso[1], day=2)
		wednesday = date.fromisocalendar(year=iso[0], week=iso[1], day=3)
		thursday = date.fromisocalendar(year=iso[0], week=iso[1], day=4)
		friday = date.fromisocalendar(year=iso[0], week=iso[1], day=5)

		current_week_days = [
			(0, 0, {'name': 'monday {}/{}'.format(monday.strftime('%d'), monday.month), 'date': monday}),
			(0, 0, {'name': 'tuesday {}/{}'.format(tuesday.strftime('%d'), tuesday.month), 'date': tuesday}),
			(0, 0, {'name': 'wednesday {}/{}'.format(wednesday.strftime('%d'), wednesday.month), 'date': wednesday}),
			(0, 0, {'name': 'thursday {}/{}'.format(thursday.strftime('%d'), thursday.month), 'date': thursday}),
			(0, 0, {'name': 'friday {}/{}'.format(friday.strftime('%d'), friday.month), 'date': friday}),
		]

		week_of_records = []
		for day in current_week_days:
			day_record = self.env['mrp.planning.days'].search([('name', '=', day[2]['name']), ('date', '=', day[2]['date'])], limit=1)
			if not day_record:
				day_record = self.env['mrp.planning.days'].create(day[2])
			week_of_records.append((4, day_record.id, 0))

		return week_of_records
	

	def _compute_internal_transfer_count(self):
		for rec in self:
			rec.internal_transfer_count = len(self.picking_ids)


	def _get_default_plant(self):
		plant_id = self.env['mrp.plant'].search([('is_principal', '=', True)])
		return plant_id.id if plant_id else False



	reference = fields.Char(_("Reference"), default=lambda self: _('New'), tracking=True)
	code = fields.Char(_("Code"), tracking=True)
	state = fields.Selection([
				('cancel', "Cancelled"),
				('draft', "Draft"),
				('confirm', "Confirmed"),
				('04_mo_generated', "Mo generate"),
				], default="draft", index=True, readonly=True, copy=False, tracking=True
			)
	scheduled_date = fields.Date(_("Add a date"), default=lambda self: fields.Date.today(), required=True)

	week_of = fields.Many2many('mrp.planning.days', string='Scheduled dates', default=_get_default_week_of, domain=lambda self: [('name', 'in', self.week_days)], copy=True)

	company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company.id)
	mrp_production_general_state = fields.Selection([
			['draft', "Draft"],
			['confirm', "Confirmed"],
			['done', "Done"],
			['cancel', "Cancelled"],
		], default="draft", copy=False)


	section_ids = fields.Many2many("mrp.section", string=_("Sections"), required=True, tracking=5)
	# team_ids = fields.Many2many("mrp.team", string=_("Teams"), tracking=True, required=True)

	planning_line_ids = fields.One2many("mrp.planning.line", "planning_id", string=_("Planning lines"), tracking=5)
	detailed_pl_ids = fields.One2many("mrp.detail.planning.line", "planning_id", string=_("Detailed planning lines"), tracking=4)
	mrp_production_ids = fields.One2many("mrp.production", "planning_id", string=_("Mrp orders"), copy=False, tracking=4)
	picking_ids = fields.One2many('stock.picking', 'planning_id', string='Planning MRP', tracking=True)
	internal_transfer_count = fields.Integer(string=_("Internal transfer count"), compute='_compute_internal_transfer_count')
	plant_id = fields.Many2one("mrp.plant", string=_("Plant"), default=_get_default_plant, tracking=2)


	def change_mrp_production_general_state_in_done(self):
		print('yes change')
		self.mrp_production_general_state = "done"

	@api.model
	def create(self, vals):

		seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(fields.Datetime.now()))
		vals['reference'] = self.env['ir.sequence'].next_by_code("mrp.planning", sequence_date=seq_date) or _("New")
		print("La reference", vals['reference'])
		res = super().create(vals)
		print("Res", res)
		return res

	def action_confirm(self):

		if not self.planning_line_ids:
			raise ValidationError(_("Yo have to give at least one planning line"))

		detailed_lines_to_delete = self.env['mrp.detail.planning.line'].search([('planning_id', '=', self.id)]).unlink()

		section_id_lst = []

		value_planning_line = []

		try:
			for pline in self.planning_line_ids:
				val = {
					'package': pline.package,
					'qty_compute': pline.qty_compute,
					'qty': pline.qty,
					'capacity': pline.capacity,
					'product_id': pline.product_id,
					'packaging_line_id': pline.packaging_line_id,
					'section_id': pline.section_id,
					'mrp_days': pline.mrp_days,
					'planning_id': self.id,
					'planning_line_id': pline.id,
				}
				value_planning_line.append(val)

			dict_dictionnaires = {}
			if value_planning_line:
				for dictionnaire in value_planning_line:
					section_id = dictionnaire.get('section_id')
					if section_id in dict_dictionnaires:
						dict_dictionnaires[section_id].append(dictionnaire)
					else:
						dict_dictionnaires[section_id] = [dictionnaire]

				# Extraction des dictionnaires avec la même section_id
				liste_meme_section_id = [dictionnaires for dictionnaires in dict_dictionnaires.values() if
									  len(dictionnaires) > 1]

				# Extraction des dictionnaires restants
				liste_autres_dictionnaires = [dictionnaires[0] for dictionnaires in dict_dictionnaires.values() if
											  len(dictionnaires) == 1]

				if liste_meme_section_id:
					for element in liste_meme_section_id:
						section_element = element[0]
						self.env['mrp.detail.planning.line'].create([{
							'display_type': 'line_section',
							'name': section_element['section_id'].name,
							'product_id': section_element['product_id'].id,
							'planning_line_id': section_element['planning_line_id'],
							'planning_id': section_element['planning_id'],
							'qty': section_element['qty'],
							'packaging_line_id': section_element['packaging_line_id'].id,
							'date': date.today(),
						}])

						dico = {}
						for dictionnaire in element:
							packaging_line_id = dictionnaire.get('packaging_line_id')
							if packaging_line_id in dico:
								dico[packaging_line_id].append(dictionnaire)
							else:
								dico[packaging_line_id] = [dictionnaire]

						# Extraction des dictionnaires avec le même packaging line
						liste_meme_packaging_line_id = [dictionnaires for dictionnaires in dico.values() if
												 len(dictionnaires) > 1]

						# Extraction des dictionnaires restants
						liste_autres_dico = [dictionnaires[0] for dictionnaires in
													  dico.values() if
													  len(dictionnaires) == 1]

						if liste_meme_packaging_line_id:
							for elm in liste_meme_packaging_line_id:
								print(f'elm : {elm}')
								packaging_element = elm[0]
								print(f"packaging_element {packaging_element}")
								self.env['mrp.detail.planning.line'].create([{
									'display_type': 'line_note',
									'name': '       ' + packaging_element['packaging_line_id'].name,
									'product_id': packaging_element['product_id'].id,
									'planning_line_id': packaging_element['planning_line_id'],
									'planning_id': packaging_element['planning_id'],
									'qty': packaging_element['qty'],
									'packaging_line_id': packaging_element['packaging_line_id'].id,
									'date': date.today(),
								}])
								for value in elm:
									print(f"value : {value}")
									ppp_id = self.env['mrp.packaging.pp'].search(
										[('packaging_line_id', '=', value['packaging_line_id'].id),
										 ('product_id', '=', value['product_id'].id)], limit=1)

									self.env['mrp.detail.planning.line'].create([{
										'date_char': day['name'],
										'date': day['date'],
										'product_id': value['product_id'].id,
										'package': value['package'],
										# 'qty': bom_id.packing * pline.package if bom_id else pline.package,
										# 'capacity': bom_id.capacity * pline.package if bom_id else pline.package,
										'qty': value['qty'],
										'capacity': ppp_id.capacity if ppp_id else 0,
										'packaging_line_id': value['packaging_line_id'].id,
										'planning_line_id': value['planning_line_id'],
										'planning_id': value['planning_id'],
										'employee_number': ppp_id.employee_number if ppp_id else 0,
									} for day in value['mrp_days']])

						if liste_autres_dico:
							for value in liste_autres_dico:
								print(f"value de liste_autres_dico : {value}")
								self.env['mrp.detail.planning.line'].create([{
									'display_type': 'line_note',
									'name': '       ' + value['packaging_line_id'].name,
									'product_id': value['product_id'].id,
									'planning_line_id': value['planning_line_id'],
									'planning_id': value['planning_id'],
									'qty': value['qty'],
									'packaging_line_id': value['packaging_line_id'].id,
									'date': date.today(),
								}])

								ppp_id = self.env['mrp.packaging.pp'].search(
									[('packaging_line_id', '=', value['packaging_line_id'].id),
									 ('product_id', '=', value['product_id'].id)], limit=1)

								self.env['mrp.detail.planning.line'].create([{
									'date_char': day['name'],
									'date': day['date'],
									'product_id': value['product_id'].id,
									'package': value['package'],
									# 'qty': bom_id.packing * pline.package if bom_id else pline.package,
									# 'capacity': bom_id.capacity * pline.package if bom_id else pline.package,
									'qty': value['qty'],
									'capacity': ppp_id.capacity if ppp_id else 0,
									'packaging_line_id': value['packaging_line_id'].id,
									'planning_line_id': value['planning_line_id'],
									'planning_id': value['planning_id'],
									'employee_number': ppp_id.employee_number if ppp_id else 0,
								} for day in value['mrp_days']])

				if liste_autres_dictionnaires:
					for element in liste_autres_dictionnaires:
						self.env['mrp.detail.planning.line'].create([{
							'display_type': 'line_section',
							'name': element['section_id'].name,
							'product_id': element['product_id'].id,
							'planning_line_id': element['planning_line_id'],
							'planning_id': element['planning_id'],
							'qty': element['qty'],
							'packaging_line_id': element['packaging_line_id'].id,
							'date': date.today(),
						}])

						self.env['mrp.detail.planning.line'].create([{
							'display_type': 'line_note',
							'name': '       ' + element['packaging_line_id'].name,
							'product_id': element['product_id'].id,
							'planning_line_id': element['planning_line_id'],
							'planning_id': element['planning_id'],
							'qty': element['qty'],
							'packaging_line_id': element['packaging_line_id'].id,
							'date': date.today(),
						}])

						ppp_id = self.env['mrp.packaging.pp'].search(
							[('packaging_line_id', '=', element['packaging_line_id'].id),
							 ('product_id', '=', element['product_id'].id)], limit=1)
						self.env['mrp.detail.planning.line'].create([{
							'date_char': day['name'],
							'date': day['date'],
							'product_id': element['product_id'].id,
							'package': element['package'],
							# 'qty': bom_id.packing * pline.package if bom_id else pline.package,
							# 'capacity': bom_id.capacity * pline.package if bom_id else pline.package,
							'qty': element['qty'],
							'capacity': ppp_id.capacity if ppp_id else 0,
							'packaging_line_id': element['packaging_line_id'].id,
							'planning_line_id': element['planning_line_id'],
							'planning_id': element['planning_id'],
							'employee_number': ppp_id.employee_number if ppp_id else 0,
						} for day in element['mrp_days']])
		except Exception as e:
			raise e
		else:
			self.state = "confirm"

		return True

	

	def action_cancel(self):

		# Check if at least one of productions orders is done
		for line in self.detailed_pl_ids:
			if line.state == 'done':
				raise ValidationError(_("You cannot cancel a planning which have one of it's manufacturing order done."))
		# Cancel productions of this planning
		production_ids = self.env['mrp.production'].search([('planning_id', '=', self.id)])
		production_done = production_ids.filtered(lambda self: self.state == 'done')
		if production_done:
			raise ValidationError(_("You cannot cancel this planning because some productions are already done."))
		else:
			production_ids.action_cancel()

		self.state = "cancel"
		self.mrp_production_general_state = "cancel"

		return True

	def action_draft(self):

		self.state = "draft"
		self.mrp_production_general_state = "draft"
		return True


	# Function to obtain an overview for raw materials that will be used
	def view_rm_overview(self):

		# Verif if products of planning have a bill of material
		verif_bom = self.verif_bom()
		# Verif if products of planning have all qty informations necessary
		verif_product_proportion = self.verif_product_proportion()
		if verif_bom:
			raise ValidationError(_("No bill of material find for %s. Please create a one." % verif_bom.name))
		if verif_product_proportion:
			raise ValidationError(_("No quantity found for %s in %s" %(verif_product_proportion[0], verif_product_proportion[1])))
		action = {
			"name": "Raw material to use",
			"res_model": "rm.overview",
			"type": "ir.actions.act_window",
			"view_mode": "tree",
			"view_id": self.env.ref("mrp_planning.rm_overview_tree").id,
		}

		# Delete old overview informations
		self.env['rm.overview'].search([('planning_id', '=', self.id)]).unlink()
		overview_lines = []

		print('before for')
		for dl in self.detailed_pl_ids:
			print(f'dl.state : {dl.state}')
			if dl.state == "draft":
				bom_id = self.env["mrp.bom"].search([('product_tmpl_id', '=', dl.product_id.product_tmpl_id.id)])
				bom_id = bom_id[0]
				temp_stock = self.env['stock.location'].search([('temp_stock', '=', 1), ('plant_id', '=', self.plant_id.id)])
				if not temp_stock:
					raise ValidationError(_("No temp location find. Please configure it or contact support."))
				rm_lines = []
				# Create a line of overview for each bill of materials line's for each end product.
				print(f'bom_id.bom_line_ids : {bom_id.bom_line_ids}')
				for line in bom_id.bom_line_ids:
					quant = self.env['stock.quant'].search([
						('product_id', '=', line.product_id.id),
						('location_id', '=', temp_stock.id)
						])
					# Convert qty about unit of measure. Because of each raw material can have a different unit of measure for bom and storage(same categorie)
					on_hand_qty = quant.product_uom_id._compute_quantity(quant.available_quantity, line.product_uom_id)
					rm_lines = self.env['rm.overview'].create([{
							'product_id': line.product_id.id,
							'required_qty': dl.qty * line.product_qty,
							# 'on_hand_qty': on_hand_qty,
							'uom_id': line.product_uom_id.id,
							'bom_id': bom_id.id,
							'detail_line_id': dl.id,
						}])

		# Delete duplicate lines and accumulate all of products required_qty
		overview_lines = self.env['rm.overview'].search([('planning_id', '=', self.id)])
		product_use_ids = []
		overview_to_unlink = []
		for overview in overview_lines:
			if not overview.product_id.id in product_use_ids:
				product_use_ids.append(overview.product_id.id)
				ov_by_products = overview_lines.filtered(lambda self: self.product_id.id == overview.product_id.id)
				required_qty = 0
				for line in ov_by_products:
					required_qty += line.required_qty

				overview.bom_ids = [ov.bom_id.id for ov in ov_by_products]
				overview.required_qty = required_qty
				overview.missing_qty = overview.required_qty - overview.on_hand_qty if overview.on_hand_qty < overview.required_qty else 0
			else:
				overview_to_unlink.append(overview)

		for ov in overview_to_unlink:
			ov.unlink()

		action["domain"] = [('planning_id', '=', self.id)]
		return action

	def create_overview_wizard(self):

		action = {
			"name": "Raw Material Overview",
			"res_model": "overview.wizard",
			"type": "ir.actions.act_window",
			"view_mode": "form",
			# "view_id": self.env.ref("view_create_overview_wizard_from").id,
			'target': 'new',
			"context": {
				"planning_id": self.id,
				"overview_ids": self.env["overview.wizard"].search([("planning_id", "=", self.id)]).ids,
				# "total_missing_qty": sum(
				# 	self.env['rm.overview'].search([("planning_id", "=", self.id)]).mapped('missing_qty'))
			},
		}
		return action

	def verif_bom(self):

		for pl in self.planning_line_ids:
			if not self.env["mrp.bom"].search([('product_tmpl_id', '=', pl.product_id.product_tmpl_id.id)]):
				return pl.product_id

		return False

	def verif_product_proportion(self):

		for pl in self.planning_line_ids:

			if not self.env["mrp.packaging.pp"].search([('packaging_line_id', '=', pl.packaging_line_id.id), ('product_id', '=', pl.product_id.id)]):
				return pl.product_id, pl.packaging_line_id

		return False


	def generate_mo(self):

		# Verif if products of planning have a bill of material
		verif_bom = self.verif_bom()
		if verif_bom:
			raise ValidationError(_("No bill of material find for %s. Please create a one." % verif_bom.name))
		if not self.plant_id.default_location_src_id or not self.plant_id.default_location_dest_id:
			raise ValidationError(_(f"Please configure {self.plant_id.name} locations before this action."))
		# if self.mrp_production_general_state == "draft":
		for line in self.detailed_pl_ids:
			if line.display_type == False:
				bom_id = self.env["mrp.bom"].search([('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)])
				bom_id = bom_id[0]
				qty = line.uom_id._compute_quantity(line.qty, bom_id.product_uom_id)
				self.env['mrp.production'].create({
						"product_id": line.product_id.id,
						"product_ref": line.product_id.name,
						"bom_id": bom_id.id,
						"product_qty": qty,
						"product_uom_id": line.uom_id.id,
						"date_planned_start": datetime.combine(line.date, datetime.min.time()),
						"packaging_line_id": line.packaging_line_id.id,
						"section_id": line.planning_line_id.section_id.id,
						"planning_line_id": line.planning_line_id.id,
						"detailed_pl_id": line.id,
						"planning_id": self.id,
						"plant_id": self.plant_id.id,
						"location_src_id": self.plant_id.default_location_src_id.id,
						"location_dest_id": self.plant_id.default_location_dest_id.id,
						})

		# else:
		# 	raise ValidationError(_(""))

		# Update state
		self.state = "04_mo_generated"

		return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'type': 'success',
				'message': _("Manufacturing orders create with success!"),
				'next': {'type': 'ir.actions.act_window_close'},
			}
		}

	def view_mrp_orders(self):

		return {
			"name": f"{self.reference} manufacturing orders",
			"type": "ir.actions.act_window",
			"res_model": "mrp.production",
			"view_mode": "tree,form",
			"domain": [('planning_id', '=', self.id), ('state', '!=', "cancel")],
			"context": {
				'search_default_todo': True,
				'search_default_group_by_planning': 1,
				'search_default_group_by_section': 1,
				'search_default_group_by_packaging_line_id': 1,
			},
		}


	def view_internal_transfer(self):

		internal_transfer = self.env['stock.picking'].search([
			('picking_type_code', '=', 'internal'), ('planning_id', '=', self.id)
		])

		if internal_transfer:
			if len(internal_transfer) == 1:
				return {
					'type': 'ir.actions.act_window',
					'res_model': 'stock.picking',
					'res_id': internal_transfer.id,
					'view_mode': 'form',
					'target': 'current',
				}
			else:
				return {
					'type': 'ir.actions.act_window',
					'res_model': 'stock.picking',
					'view_mode': 'tree,form',
					'name': 'List of internal transfers',
					'domain': [('id', 'in', internal_transfer.ids)],
					'target': 'current',
				}

	def action_product_replacement(self):


		if self.state != '04_mo_generated':
			raise ValidationError(_("You cannot replace a product when mrp orders are not generated."))
		if self.mrp_production_general_state == 'done':
			raise ValidationError(_("You cannot replace a product when products are manufacted."))

		action = {
			"name": f"Replace product in {self.reference}",
			"type": "ir.actions.act_window",
			"res_model": "replace.product",
			"view_mode": "form",
			"context": {'default_planning_id': self.id},
			"target": "new",
		}

		return action

	def regroup_for_report(self):

		if self.state == 'draft':
			raise ValidationError(_("You cannot print a planning in draft state. Confirm it before."))
		grouped_lines = defaultdict(lambda: defaultdict(list))

		for detailed_planning_line in self.detailed_pl_ids:
			if detailed_planning_line.display_type == False:
				section = detailed_planning_line.planning_line_id.section_id
				packaging_line = detailed_planning_line.packaging_line_id

				grouped_lines[section][packaging_line].append(detailed_planning_line)

		# Convertir le résultat en un dictionnaire Python
		result_dict = {}
		for section, packaging_lines in grouped_lines.items():
			section_dict = {}
			for packaging_line, detailed_planning_lines in packaging_lines.items():
				section_dict[packaging_line] = detailed_planning_lines
			result_dict[section] = section_dict

		return result_dict


	# Action to confirm productions orders of current planning
	def action_confirm_productions(self):
		for dpl in self.detailed_pl_ids:
			production_id = self.env['mrp.production'].search([['detailed_pl_id', '=', dpl.id], ['state', 'in', ['draft']]])
			production_id.action_confirm() if production_id else False

		self.mrp_production_general_state = "confirm"
		return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'type': 'success',
				'message': _("Manufacturing orders confirm with success!"),
				'next': {'type': 'ir.actions.act_window_close'},
			}
		}

	# Finish products manufacturing action
	def action_mark_productions_as_done(self):
		if self.detailed_pl_ids.filtered(lambda self: self.state == 'progress'):
			raise ValidationError(_("You have to manage line(s) in progress state before this action."))

		productions = []
		for dpl in self.detailed_pl_ids:
			production_id = self.env['mrp.production'].search([['detailed_pl_id', '=', dpl.id], ['state', 'in', ['confirmed', 'progress', 'to_close']]])
			if production_id:
				productions.append(production_id.id)

		production_ids = self.env['mrp.production'].browse(productions)

		result = production_ids.button_mark_done()
		
		# self.mrp_production_general_state = "done"
		return result

	
	# Dupliquer le modele avec toutes les données qu'il contient
	def copy(self, default=None):
		if default is None:
			default = {}
		print(f'default : {default}')
		if self.planning_line_ids:
			new_planning_line_ids = [(0, 0, {
				'package': line.package,
				'qty_compute': line.qty_compute,
				'qty': line.qty,
				'capacity': line.capacity,
				'product_id': line.product_id.id,
				'uom_id': line.uom_id.id,
				'uom_domain': [(6, 0, line.uom_domain.ids)],
				'packaging_line_id': line.packaging_line_id.id,
				'packaging_line_domain': [(6, 0, line.packaging_line_domain.ids)],
				'section_id': line.section_id.id,
				'mrp_days': [(6, 0, line.mrp_days.ids)],
				'planning_id': self.id,
			}) for line in self.planning_line_ids]
			default['planning_line_ids'] = new_planning_line_ids
		print(f'default after : {default}')
		return super().copy(default)

	@api.onchange('scheduled_date')
	def _onchange_scheduled_date(self):
		print(f"self.scheduled_date : {self.scheduled_date}")
		if self.scheduled_date != self.today_date:
			iso = self.scheduled_date.isocalendar()
			print(f"iso : {iso}")
			print(f"iso[2] : {iso[2]}")
			monday = date.fromisocalendar(year=iso[0], week=iso[1], day=1)
			tuesday = date.fromisocalendar(year=iso[0], week=iso[1], day=2)
			wednesday = date.fromisocalendar(year=iso[0], week=iso[1], day=3)
			thursday = date.fromisocalendar(year=iso[0], week=iso[1], day=4)
			friday = date.fromisocalendar(year=iso[0], week=iso[1], day=5)
			saturday = date.fromisocalendar(year=iso[0], week=iso[1], day=6)
			sunday = date.fromisocalendar(year=iso[0], week=iso[1], day=7)

			if iso[2] == 1:
				day_name = 'monday {}/{}'.format(monday.strftime('%d'), monday.month)
			elif iso[2] == 2:
				day_name = 'tuesday {}/{}'.format(tuesday.strftime('%d'), tuesday.month)
			elif iso[2] == 3:
				day_name = 'wednesday {}/{}'.format(wednesday.strftime('%d'), wednesday.month)
			elif iso[2] == 4:
				day_name = 'thursday {}/{}'.format(thursday.strftime('%d'), thursday.month)
			elif iso[2] == 5:
				day_name = 'friday {}/{}'.format(friday.strftime('%d'), friday.month)
			elif iso[2] == 6:
				day_name = 'saturday {}/{}'.format(saturday.strftime('%d'), saturday.month)
			elif iso[2] == 7:
				day_name = 'sunday {}/{}'.format(sunday.strftime('%d'), sunday.month)
			print(f"day_name : {day_name}")
			print(f"self.week_of : {self.week_of}")

			for day in self.week_of:
				if day_name in day.name:
					raise UserError(_("This day already exists in the week"))

				day_iso = day.date.isocalendar()
				print(f'day_iso : {day_iso}')
				if iso.year < day_iso.year:
					print("year")
					raise UserError(_("The date must not be less than the current week's dates."))
				elif self.scheduled_date.month < day.date.month:
					print("month")
					raise UserError(_("The date must not be less than the current week's dates."))
				elif iso.week < day_iso.week:
					if self.scheduled_date.month <= day.date.month:
						if iso.year <= day_iso.year:
							print("day")
							raise UserError(_("The date must not be less than the current week's dates."))

			day_in_week_of = self.env['mrp.planning.days'].search([
				('name', '=', day_name)
			])
			if day_in_week_of:
				# Récupérer les valeurs actuelles du champ Many2many self.week_of
				existing_week_of = self.week_of.ids

				# Ajouter l'ID de day_record à la liste des valeurs existantes
				existing_week_of.append(day_in_week_of.id)

				# Écrire la liste mise à jour dans le champ Many2many self.week_of
				self.week_of = [(6, 0, existing_week_of)]
				self._get_week_of_domain(day_name)
			else:
				day_record = self.env['mrp.planning.days'].create({
					'name': day_name,
					'date': self.scheduled_date
				})
				print(f'day_record : {day_record}')
				# Récupérer les valeurs actuelles du champ Many2many self.week_of
				existing_week_of = self.week_of.ids

				# Ajouter l'ID de day_record à la liste des valeurs existantes
				existing_week_of.append(day_record.id)

				# Écrire la liste mise à jour dans le champ Many2many self.week_of
				self.week_of = [(6, 0, existing_week_of)]
				self._get_week_of_domain(day_name)
				print(f"self.week_of after : {self.week_of}")

	def _get_week_of_domain(self, day_name):
		print(f'self.week_days : {self.week_days}')
		return self.week_days.append(day_name)

	def view_internal_transfer(self):
		internal_transfer = self.env["stock.picking"].search(
			[("picking_type_code", "=", "internal"), ("planning_id", "=", self.id)]
		)

		if internal_transfer:
			if len(internal_transfer) == 1:
				return {
					"type": "ir.actions.act_window",
					"res_model": "stock.picking",
					"res_id": internal_transfer.id,
					"view_mode": "form",
					"target": "current",
				}
			else:
				return {
					"type": "ir.actions.act_window",
					"res_model": "stock.picking",
					"view_mode": "tree,form",
					"name": "List of internal transfers",
					"domain": [("id", "in", internal_transfer.ids)],
					"target": "current",
				}

	def unlink(self):
		print('delete')
		records_to_delete = self.filtered(lambda rec: rec.state not in ['confirm', '04_mo_generated'])
		if records_to_delete:
			super(MrpPlanning, records_to_delete).unlink()
		else:
			raise UserError(_("You cannot delete confirmed schedules or generated schedules"))


	def _get_unique_ids(self, old_ids, new_ids):
		old_set = set(old_ids)
		new_set = set(new_ids)
		added = list(new_set - old_set)
		deleted = list(old_set - new_set)
		return added, deleted

	def _get_section_message(self, sections, label):
		if not sections:
			return ""
		message = f"<p>{label} :</p><ul>"
		for elm in sections:
			section = self.env['mrp.section'].browse(elm)
			message += f"<li>{section.name}</li>"
		return message

	def _get_day_message(self, days, label):
		if not days:
			return ""
		message = f"<p>{label} :</p><ul>"
		for elm in days:
			day = self.env['mrp.planning.days'].browse(elm)
			message += f"<li>{day.name}</li>"
		return message

	def _get_pl_message(self, pls, label):
		if not pls:
			return ""
		message = f"<p>{label} :</p><ul>"
		print(f'pls : {pls}')
		for elm in pls:
			print(f"elm : {elm}")
			product = self.env['product.product'].browse(elm['product_id'])
			section = self.env['mrp.section'].browse(elm['section_id'])
			packaging_line = self.env['mrp.packaging.line'].browse(elm['packaging_line_id'])
			print(f"{product}")
			message += f"<li>{product.name}, packaging line {packaging_line.name}, section {section.name}</li>"
			print(f"message : {message}")
		return message
	
	def write(self, vals):
		for rec in self:
			print(f'self.env.context : {self.env.context}')
			params = self.env.context.get('params')
			if params:
				mrp_planning = self.env['mrp.planning'].browse(params.get('id'))
			else:
				mrp_planning = self.env['mrp.planning'].browse(rec.id)

			old_sect_name = [sect.name for sect in rec.section_ids]
			old_day_name = [day.name for day in rec.week_of]
			old_planning_line = [{
				'id': pl.id,
				'product_id': pl.product_id,
				'packaging_line_id': pl.packaging_line_id,
				'qty': pl.qty,
				'section_id': pl.section_id,
				'mrp_days': pl.mrp_days,
				'uom_id': pl.uom_id,
			} for pl in rec.planning_line_ids]
			print(f"old_planning_line : {old_planning_line}")

			super(MrpPlanning, rec).write(vals)

			print(f"vals : {vals}")

			if 'section_ids' in vals:
				new_sect_id = [sect for val in vals['section_ids'] for sect in val[2]]
				new_sect_name = []
				for nsn in new_sect_id:
					nsn_name = self.env['mrp.section'].browse(nsn)
					new_sect_name.append(nsn_name.name)

				formatted_old_sect_name = ', '.join(map(str, old_sect_name))
				formatted_new_sect_name = ', '.join(map(str, new_sect_name))
				message_to_sect = f"<p><b> {formatted_old_sect_name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{formatted_new_sect_name}</span></b><em> (Sections)</em></p>"

				mrp_planning.message_post(body=message_to_sect)

			if 'week_of' in vals:
				new_day_id = [day for val in vals['week_of'] for day in val[2]]
				new_week_of_name = []
				for day in new_day_id:
					day_name = self.env['mrp.planning.days'].browse(day)
					new_week_of_name.append(day_name.name)

				formatted_old_week_of_name = ', '.join(map(str, old_day_name))
				formatted_new_week_of_name = ', '.join(map(str, new_week_of_name))
				message_to_day = f"<p><b> {formatted_old_week_of_name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{formatted_new_week_of_name}</span></b><em> (Week of)</em></p>"

				mrp_planning.message_post(body=message_to_day)

			if 'planning_line_ids' in vals:
				new_pl_id = [val[1] for val in vals['planning_line_ids']]
				print(f'new_pl_id : {new_pl_id}')
				add_pl = [val[2] for val in vals['planning_line_ids'] if val[0] == 0]
				delete_pl = [val[1] for val in vals['planning_line_ids'] if val[0] == 2]
				update_pl = []
				for val in vals['planning_line_ids']:
					if val[0] == 1:
						val = {
							'id': val[1],
							'value': val[2]
						}
						update_pl.append(val)

				if update_pl:
					update_pl_id = [pl['id'] for pl in update_pl]
					print(f'update_pl : {update_pl}')
					for pl in update_pl:
						print(f"pl : {pl['id']}")
						for planning in old_planning_line:
							print(f"planning : {planning['id']}")
							if pl['id'] == planning['id']:

								position = update_pl_id.index(pl['id'])
								value = update_pl[position]['value']
								print(f'value : {value}')
								if 'product_id' in value:
									msg = ""
									message_to_update_pl = f"<p><b> Packaging Line {planning['packaging_line_id']['name']}, Section {planning['section_id']['name']}<em> (Planning lines)</em> : </b></p><ul>"
									new_prod = self.env['product.product'].browse(value['product_id'])
									msg += f"<li><p><b>{planning['product_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{new_prod.name}</span></b></p></li>"
									message_to_update_pl += msg
									mrp_planning.message_post(body=message_to_update_pl)

								message_to_update_pl = f"<p><b> {planning['product_id']['name']}<em> (Planning lines)</em> : </b></p><ul>" if 'product_id' not in value else f"<p><b> {self.env['product.product'].browse(value['product_id']).name}<em> (Planning lines)</em> : </b></p><ul>"
								msg = ""
								if 'packaging_line_id' in value:
									new_pack = self.env['mrp.packaging.line'].browse(value['packaging_line_id'])
									msg += f"<li><p><b>Packaging line {planning['packaging_line_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Packaging line {new_pack.name}</span></b></p></li>"

								if 'qty' in value:
									msg += f"<li><p><b>Quantity {planning['qty']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Quantity {value['qty']}</span></b></p></li>"

								if 'section_id' in value:
									new_sect = self.env['mrp.section'].browse(value['section_id'])
									msg += f"<li><p><b>Section {planning['section_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Section {new_sect.name}</span></b></p></li>"

								if 'mrp_days' in value:

									old_day_name = [day['name'] for day in planning['mrp_days']]
									new_day_id = [day for dy in value['mrp_days'] for day in dy[2]]
									print(f'old_day_name : {old_day_name}')
									new_day_name = []
									for ndi in new_day_id:
										ndi_name = self.env['mrp.planning.days'].browse(ndi)
										new_day_name.append(ndi_name.name)
									print(f'new_day_name : {new_day_name}')
									msg += f"<li><p><b>{old_day_name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{new_day_name}</span></b></p></li>"
								if 'uom_id' in value:
									new_uom = self.env['uom.uom'].browse(value['uom_id'])
									msg += f"<li><p><b>{planning['uom_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{new_uom.name}</span></b></p></li>"

								message_to_update_pl += f"{msg}"

								mrp_planning.message_post(body=message_to_update_pl)

				if delete_pl:
					message_to_delete_pl = "<p> Planning lines removed are <em>(Planning line)</em>: </p><ul>"
					for dl in delete_pl:
						for planning in old_planning_line:
							if dl == planning['id']:
								message_to_delete_pl += f"<li><p><b>{planning['product_id']['name']}, section {planning['section_id']['name']}, packaging line {planning['packaging_line_id']['name']}</b></p></li>"

					mrp_planning.message_post(body=message_to_delete_pl)

				message_to_add_pl = self._get_pl_message(add_pl, "Planning lines added to planning_line_ids are")
				if message_to_add_pl:
					mrp_planning.message_post(body=message_to_add_pl)

class MrpPlanninLine(models.Model):
	_name = "mrp.planning.line"
	_inherit = ["mail.thread", "mail.activity.mixin"]

	@api.depends('product_id')
	def _compute_uom_domain(self):
		for rec in self:
			if rec.product_id:
				rec.uom_domain = [uom_id.id for uom_id in rec.product_id.product_tmpl_id.uom_id.category_id.uom_ids]
			else:
				rec.uom_domain = []

	@api.onchange('product_id')
	def _compute_default_uom_id(self):
		for rec in self:
			if rec.product_id:
				if not rec.uom_id and rec.uom_domain:
					rec.uom_id = rec.uom_domain[0]._origin.id

	@api.depends('product_id', 'packaging_line_id')
	def _compute_qty(self):
		print("COmpute qtyyyyyyyyyyuk", self)
		for rec in self:
			if rec.product_id and rec.packaging_line_id:
				ppp_id = self.env['mrp.packaging.pp'].search([('product_id', '=', rec.product_id.id), ('packaging_line_id', '=', rec.packaging_line_id.id)], limit=1)
				rec.qty = ppp_id.capacity
				rec.qty_compute = rec.qty
			else:
				rec.qty, rec.qty_compute = 0, 0


	@api.depends('product_id')
	def _compute_packaging_line_domain(self):
		print("Selffff", self._origin)
		for rec in self:
			if rec.product_id:
				ppp_ids = self.env['mrp.packaging.pp'].search([('product_id', '=', rec.product_id.id)])
				l = [ppp_id.packaging_line_id.id for ppp_id in ppp_ids]
				print("Test", l)
				rec.packaging_line_domain = l
			else:
				rec.packaging_line_domain = []

	package = fields.Float(_("Package"))
	qty_compute = fields.Integer(_("Qty per day"), compute="_compute_qty", store=True)
	qty = fields.Integer(_("Qty per day"))
	capacity = fields.Integer(_("Capacity"))
	employee_number = fields.Integer(_("EN"))

	product_id = fields.Many2one("product.product", string=_("Article"), required=True)
	uom_id = fields.Many2one("uom.uom", _("Unit of measure"), required=1)
	uom_domain = fields.Many2many("uom.uom", compute="_compute_uom_domain")
	packaging_line_id = fields.Many2one("mrp.packaging.line", tracking=True, required=True)
	packaging_line_domain = fields.Many2many("mrp.packaging.line", compute="_compute_packaging_line_domain")
	# team_id = fields.Many2one("mrp.team", tracking=True)
	section_id = fields.Many2one("mrp.section", required=1)
	mrp_days = fields.Many2many('mrp.planning.days', string='Mrp Days', required=True)

	planning_id = fields.Many2one("mrp.planning")




class MrpDetailPlanningLine(models.Model):
	_name = "mrp.detail.planning.line"

	def _compute_state(self):
		for rec in self:
			production_id = self.env['mrp.production'].search([('detailed_pl_id', '=', rec.id)])
			rec.state = production_id.state

			print(f"rec.state : {rec.state}")
			if rec.state == 'done':
				mrp = self.env['mrp.planning'].search([
					('id', '=', rec.planning_id.id)
				])
				mrp_detail_states = [detail.state for detail in mrp.detailed_pl_ids if
									 detail.display_type == False]
				print(f'mrp_detail_states : {mrp_detail_states}')
				mrp_state = list(set(mrp_detail_states))
				print(f'mrp_state : {mrp_state}')
				if len(mrp_state) == 1:
					# rec.planning_id.mrp_production_general_state = "done"
					print(f"rec.planning_id.mrp_production_general_state before : {rec.planning_id.change_mrp_production_general_state_in_done}")
					# rec.planning_id.write({
					# 	'change_mrp_production_general_state_in_done': True
					# })
					rec.planning_id.change_mrp_production_general_state_in_done()
					print(
						f"rec.planning_id.mrp_production_general_state after : {rec.planning_id.change_mrp_production_general_state_in_done}")

	date_char = fields.Char(_("Date"))
	date = fields.Date(_("Date"), required=1)
	product_ref = fields.Char(related="product_id.default_code", string=_("Article"))
	product_id = fields.Many2one("product.product", string=_("Désignation"), required=True)
	package = fields.Float(_("Package"))
	qty = fields.Integer(_("Quantity"), required=1)
	capacity = fields.Integer(_("Capacity"))
	state = fields.Selection([
							('draft', _("Draft")),
							('confirmed', _("Confirmed")),
							('progress', _("In progress")),
							('done', _("Done")),
							('to_close', _("To close")),
							('cancel', _("Cancelled")),
							], string=_("Production order state"), compute="_compute_state")

	employee_number = fields.Integer(_("EN"), default=lambda self: self.packaging_line_id.ppp_ids.search([('product_id', '=', self.product_id.id)]).employee_number)

	uom_id = fields.Many2one("uom.uom", related="planning_line_id.uom_id")
	packaging_line_id = fields.Many2one("mrp.packaging.line", required=1, tracking=True)
	planning_line_id = fields.Many2one("mrp.planning.line")
	planning_id = fields.Many2one("mrp.planning")
	display_type = fields.Selection(
		selection=[
			('line_section', "Section"),
			('line_note', "Note"),
		],
		default=False)
	name = fields.Text()


	# @api.onchange('state')
	# def mark_done(self):
	# 	for rec in self:
	# 		print(f'state : {rec.state}')
	# 		if rec.state == 'done':
	# 			mrp = self.env['mrp.planning'].search([
	# 				('id', '=', rec.planning_id)
	# 			])
	# 			mrp_detail_states = [detail.state for detail in mrp.detailed_pl_ids if mrp.detailed_pl_ids.display_type == False]
	# 			print(f'mrp_detail_states : {mrp_detail_states}')
	# 			mrp_state = list(set(mrp_detail_states))
	# 			print(f'mrp_state : {mrp_state}')


	def action_manage_production(self):

		production_id = self.env['mrp.production'].search([('detailed_pl_id', '=', self.id)])
		action = {
			"name": f"Manufacturing order",
			"type": "ir.actions.act_window",
			"res_model": "mrp.production",
			"view_mode": "form",
			"res_id": production_id.id,
			"views": [(self.env.ref('mrp.mrp_production_form_view').id, 'form')],
			"target": "new",

		}

		return action

	def unlink(self):

		for rec in self:
			if self.env['mrp.production'].search([('detailed_pl_id', '=', rec.id), ('state', 'not in', ['draft', 'cancel'])]):
				raise ValidationError(_(f"Impossible to delete the detailed planning line {rec.id} because an actif production order is related to it."))
		return super(MrpDetailPlanningLine, self).unlink()


class MrpPlanningDays(models.Model):
	_name = "mrp.planning.days"
	_rec_name = "name"

	name = fields.Char(_("Day"))
	date = fields.Date(_("Full Date"))



