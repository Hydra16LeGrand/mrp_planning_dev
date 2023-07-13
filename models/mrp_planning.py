from odoo import fields, models, api, _
from datetime import date, datetime
from odoo.exceptions import ValidationError


class MrpPlanning(models.Model):
	_name = "mrp.planning"
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_rec_name = "reference"
	_order = "scheduled_date desc"

	@api.onchange('scheduled_date')
	def _compute_week_of(self):
		for rec in self:
			if rec.scheduled_date:
				iso = rec.scheduled_date.isocalendar()
				from_iso_start = date.fromisocalendar(year=iso.year, week=iso.week, day=1)
				from_iso_end = date.fromisocalendar(year=iso.year, week=iso.week, day=7)

				rec.week_of = "monday {}/{} - sunday {}/{}".format(from_iso_start.day, from_iso_start.month, from_iso_end.day, from_iso_end.month)

	def _compute_internal_transfer_count(self):
		for rec in self:
			rec.internal_transfer_count = len(self.picking_ids)

	reference = fields.Char(_("Reference"), default=lambda self: _('New'))
	code = fields.Char(_("Code"), tracking=True)
	state = fields.Selection([
				('cancel', "Cancelled"),
				('draft', "Draft"),
				('confirm', "Confirmed"),
				('04_mo_generated', "Mo generate"),
				], default="draft", index=True, readonly=True, copy=False, tracking=True
			)
	scheduled_date = fields.Date(_("Schedule date"), default=lambda self: fields.Date.today(), required=True)
	week_of = fields.Char(_("Week of"), compute="_compute_week_of")
	company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company.id)

	section_ids = fields.Many2many("mrp.section", string=_("Sections"), required=True, tracking=True)
	team_ids = fields.Many2many("mrp.team", string=_("Teams"), tracking=True, required=True)
	planning_line_ids = fields.One2many("mrp.planning.line", "planning_id", string=_("Planning lines"), tracking=True)
	detailed_pl_ids = fields.One2many("mrp.detail.planning.line", "planning_id", string=_("Detailed planning lines"))

	mrp_production_ids = fields.One2many("mrp.production", "planning_id", string=_("Mrp orders"))

	picking_ids = fields.One2many('stock.picking', 'planning_id', string='Planning MRP')
	internal_transfer_count = fields.Integer(string=_("Internal transfer count"), compute='_compute_internal_transfer_count')

	@api.model
	def create(self, vals):
		print("Dans le create", vals)
		# if 'reference' in vals:
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


		for pline in self.planning_line_ids:

			# packaging_line_id = pline.packaging_line_id.ppp_ids.filtered(lambda self: self.packaging_line_id == pline.packaging_line_id)
			# for day in pline.mrp_days:
			ppp_id = self.env['mrp.packaging.pp'].search([('packaging_line_id', '=', pline.packaging_line_id.id), ('product_id', '=', pline.product_id.id)])


			detailed_lines = self.env['mrp.detail.planning.line'].create([{
					'date_char': self.get_date(day, date_char=True),
					'date': self.get_date(day, date_date=True),
					'product_id': pline.product_id.id,
					'package': pline.package,
					'qty': ppp_id.qty,
					'capacity': ppp_id.capacity,
					'packaging_line_id': pline.packaging_line_id.id,
					'planning_line_id': pline.id,
					'planning_id': pline.planning_id.id,
				} for day in pline.mrp_days])
		self.state = "confirm"

		return True

	def get_date(self, day, date_char=False, date_date=False):
		iso = self.scheduled_date.isocalendar()
		try:
			from_iso = date.fromisocalendar(year=iso.year, week=iso.week, day=day.number)
		except:
			raise ValidationError(_("Error when planning date generation. Contact support if it's persists!"))
		else:
			if date_date:
				return from_iso
			if date_char:
				return "%s %s/%s" %(day.name, from_iso.day, from_iso.month)

	# def get_date_char(day):
	# 	iso = self.scheduled_date.isocalendar()
	# 	try:
	# 		from_iso = date.fromisocalendar(year=iso.year, week=iso.week, day=day.number)
	# 	except:
	# 		raise ValidationError(_("Error when planning date generation. Contact support if it's persists!"))
	# 	else:
	# 		return "%s %s/%s" %(day.name, from_iso.day, from_iso.month)

	def action_cancel(self):

		print("Action cancel execc")
		# Cancel productions of this planning
		production_ids = self.env['mrp.production'].search([('planning_id', '=', self.id)])
		production_done = production_ids.filtered(lambda self: self.state == 'done')
		if production_done:

			raise ValidationError(_("You cannot cancel this planning because some productions are already done."))
		else:
			print("Le else", production_done, production_ids)
			production_ids.action_cancel()

		self.state = "cancel"

		return True

	def action_draft(self):

		self.state = "draft"

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
			raise ValidationError(_("No quantity found for %s in %s" %(verif_product_proportion.product_id, verif_product_proportion.packaging_line_id)))
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

		for dl in self.detailed_pl_ids:
			bom_id = self.env["mrp.bom"].search([('product_tmpl_id', '=', dl.product_id.product_tmpl_id.id)])
			bom_id = bom_id[0]
			temp_stock = self.env['stock.location'].search([('temp_stock', '=', 1)])
			if not temp_stock:
				raise ValidationError(_("No temp location find. Please configure it or contact support."))
			rm_lines = []
			# Create a line of overview for each bill of materials line's for each end product.
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
						'on_hand_qty': on_hand_qty,
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

		for line in self.detailed_pl_ids:
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
					"planning_id": line.planning_id.id,
				})

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


class MrpPlanninLine(models.Model):
	_name = "mrp.planning.line"
	_inherit = ["mail.thread", "mail.activity.mixin"]

	MRP_DAYS = [
		('monday', _("monday")),
		('tuesday', _("tuesday")),
		('wednesday', _("wednesday")),
		('thursday', _("thursday")),
		('friday', _("friday")),
		('saturday', _("saturday")),
		('sunday', _("sunday"))
	]	

	@api.depends('product_id')
	def _compute_uom_domain(self):
		print("Uon domain")
		for rec in self:

			if rec.product_id:
				print("Dans le if", self)
				rec.uom_domain = [uom_id.id for uom_id in rec.product_id.product_tmpl_id.uom_id.category_id.uom_ids]
			else:
				rec.uom_domain = []

	package = fields.Float(_("Package"))
	qty = fields.Integer(_("Quantity"))
	capacity = fields.Integer(_("Capacity"))
	employee_number = fields.Integer(_("EN"))

	product_id = fields.Many2one("product.product", string=_("Article"), required=True)
	uom_id = fields.Many2one("uom.uom", _("Unit of measure"), required=1)
	uom_domain = fields.Many2many("uom.uom", compute="_compute_uom_domain")
	packaging_line_id = fields.Many2one("mrp.packaging.line", tracking=True, required=True)
	team_id = fields.Many2one("mrp.team", tracking=True)
	section_id = fields.Many2one("mrp.section", related="packaging_line_id.section_id")
	mrp_days = fields.Many2many("mrp.planning.days", "mrp_planning_line_days_rel", "mrp_days_id", "planning_line_id", string=_("Mrp days"), default=lambda self: self.env['mrp.planning.days'].search([('number','in', [i for i in range(1,6)])]), required=True)

	planning_id = fields.Many2one("mrp.planning")


class MrpDetailPlanningLine(models.Model):
	_name = "mrp.detail.planning.line"

	date_char = fields.Char(_("Date"))
	date = fields.Date(_("Date"))
	product_ref = fields.Char(related="product_id.default_code", string=_("Article"))
	product_id = fields.Many2one("product.product", string=_("Désignation"), required=True)
	package = fields.Float(_("Package"))
	qty = fields.Integer(_("Quantity"))
	capacity = fields.Integer(_("Capacity"))
	employee_number = fields.Integer(_("EN"), default=lambda self: self.packaging_line_id.ppp_ids.search([('product_id', '=', self.product_id.id)]).employee_number)

	uom_id = fields.Many2one("uom.uom", related="planning_line_id.uom_id")
	packaging_line_id = fields.Many2one("mrp.packaging.line", tracking=True)
	planning_line_id = fields.Many2one("mrp.planning.line")
	planning_id = fields.Many2one("mrp.planning")



class MrpPlanningDays(models.Model):
	_name = "mrp.planning.days"
	_rec_name = "name"

	name = fields.Char(_("Day"))
	number = fields.Integer(_("Number"))

	@api.model
	def update_mrp_days(self):

		mrp_days = self.search([])
		if not mrp_days:
			week_days = {1:"monday", 2:"tuesday", 3:"wednesday", 4:"thursday", 5:"friday", 6:"saturday", 7:"sunday"}

			mrp_days.create([{
					'number': key,
					'name': day
				} for key, day in week_days.items()])


