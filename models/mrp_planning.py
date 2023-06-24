from odoo import fields, models, api, _
from datetime import date
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

				rec.week_of = "monday %s/%s - sunday %s/%s" %(from_iso_start.day, from_iso_start.month, from_iso_end.day, from_iso_end.month)

	reference = fields.Char(_("Reference"), default=lambda self: _('New'))
	code = fields.Char(_("Code"), tracking=True)
	state = fields.Selection([
				('cancel', "Cancelled"),
				('draft', "Draft"),
				('confirm', "Confirmed"),
				], default="draft", index=True, readonly=True, copy=False, tracking=True
			)
	scheduled_date = fields.Date(_("Schedule date"))
	week_of = fields.Char(_("Week of"), compute="_compute_week_of")
	company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company.id)

	section_ids = fields.Many2many("mrp.section", string=_("Sections"), tracking=True)
	team_ids = fields.Many2many("mrp.team", string=_("Teams"), tracking=True)
	planning_line_ids = fields.One2many("mrp.planning.line", "planning_id", string=_("Planning lines"), tracking=True)
	detailed_pl_ids = fields.One2many("mrp.detail.planning.line", "planning_id", string=_("Detailed planning lines"))

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
		print("dans le action confirm", self)
		detailed_lines_to_delete = self.env['mrp.detail.planning.line'].search([('planning_id', '=', self.id)]).unlink()

		def get_date(day):
			iso = self.scheduled_date.isocalendar()
			try:
				from_iso = iso.fromisocalendar(year=iso.year, week=iso.week, day=day.number)
			except:
				raise ValidationError(_("Error when planning date generation. Contact support if it's persists!"))
			else:
				return "%s %s/%s" %(day.name, from_iso.day, from_iso.month)

		for pline in self.planning_line_ids:

			# packaging_line_id = pline.packaging_line_id.ppp_ids.filtered(lambda self: self.packaging_line_id == pline.packaging_line_id)
			# for day in pline.mrp_days:
			ppp_id = self.env['mrp.packaging.pp'].search([('packaging_line_id', '=', pline.packaging_line_id.id), ('product_id', '=', pline.product_id.id)])


			detailed_lines = self.env['mrp.detail.planning.line'].create([{
					'date': get_date(day),
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

	def action_cancel(self):

		self.state = "cancel"

		return True

	def action_draft(self):

		self.state = "draft"

		return True

	def view_rm_overview(self):

		verif_bom = self.verif_bom()
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

		self.env['rm.overview'].search([('planning_id', '=', self.id)]).unlink()
		overview_lines = []
		# for pl in self.planning_line_ids:
		# 	detail_line = self.env["mrp.detail.planning.line"].search([('packaging_line_id', '=', pl.packaging_line_id.id), ('product_id', '=', pl.product_id.id)])
		# 	print("Les lignes", bom_id, bom_id.bom_line_ids)
		for dl in self.detailed_pl_ids:
			bom_id = self.env["mrp.bom"].search([('product_tmpl_id', '=', dl.product_id.product_tmpl_id.id)])
			rm_lines = []
			for line in bom_id.bom_line_ids:
				rm_lines = self.env['rm.overview'].create([{
						'product_id': line.product_id.id,
						'required_qty': dl.qty,
						'on_hand_qty': 0,
						'missing_qty': dl.qty,
						'uom_id': line.product_uom_id.id,
						'bom_id': bom_id.id,
						'detail_line_id': dl.id,
					}])

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
				overview.required_qty = required_qty
			else:
				overview_to_unlink.append(overview)

		for ov in overview_to_unlink:
			ov.unlink()




		action["domain"] = [('planning_id', '=', self.id)]
		print("Le retour", overview_lines)
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

	package = fields.Float(_("Package"))
	qty = fields.Integer(_("Quantity"))
	capacity = fields.Integer(_("Capacity"))
	employee_number = fields.Integer(_("EN"))

	product_id = fields.Many2one("product.product", string=_("Article"), required=True)
	packaging_line_id = fields.Many2one("mrp.packaging.line", tracking=True)
	team_id = fields.Many2one("mrp.team", tracking=True)
	section_id = fields.Many2one("mrp.section", related="packaging_line_id.section_id")
	mrp_days = fields.Many2many("mrp.planning.days", "mrp_planning_line_days_rel", "mrp_days_id", "planning_line_id", string=_("Mrp days"), default=lambda self: self.env['mrp.planning.days'].search([('number','in', [i for i in range(1,6)])]), required=True)

	planning_id = fields.Many2one("mrp.planning")


class MrpDetailPlanningLine(models.Model):
	_name = "mrp.detail.planning.line"

	date = fields.Char(_("Date"))
	product_id = fields.Many2one("product.product", string=_("Article"), required=True)
	product_designation = fields.Char(related="product_id.name")
	package = fields.Float(_("Package"))
	qty = fields.Integer(_("Quantity"))
	capacity = fields.Integer(_("Capacity"))
	employee_number = fields.Integer(_("EN"), default=lambda self: self.packaging_line_id.ppp_ids.search([('product_id', '=', self.product_id.id)]).employee_number)

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


