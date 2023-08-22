from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class MrpProductionInherit(models.Model):
	_inherit = "mrp.production"

	package = fields.Float(_("Package"))
	qty = fields.Integer(_("Quantity"))
	capacity = fields.Integer(_("Capacity"))
	employee_number = fields.Integer(_("EN"))

	product_ref = fields.Char(string=_("Article"))

	detailed_pl_id = fields.Many2one("mrp.detail.planning.line", string=_("Detailed planning lines"))
	packaging_line_id = fields.Many2one("mrp.packaging.line")
	section_id = fields.Many2one("mrp.section")
	planning_line_id = fields.Many2one("mrp.planning.line")
	planning_id = fields.Many2one("mrp.planning")
	plant_id = fields.Many2one("mrp.plant", string="Plant")


	def action_view_planning(self):

		action = {
			"name": "Mrp planning",
			"res_model": "mrp.planning",
			"type": "ir.actions.act_window",
			"view_mode": "form",
			"res_id": self.planning_id.id,
			"view_id": self.env.ref("mrp_planning.mrp_planning_form").id,
		}

		return action
	
	def write(self, vals):
		for rec in self:
			old_qty = rec.product_qty
			old_move_raw_ids = rec.move_raw_ids
			old_product_id = rec.product_id
			old_state = rec.state
			res = super(MrpProductionInherit, rec).write(vals)
			print(f'vals : {vals}')
			if rec.planning_id:
				if 'product_id' in vals:
					product_id = self.env['product.product'].search([('id', '=', vals['product_id'])])
					bom_id = self.env['mrp.bom'].search([('product_tmpl_id', '=', product_id.product_tmpl_id.id)])
					if bom_id:
						rec.detailed_pl_id.write({'product_id': vals['product_id']})
						rec.product_qty = old_qty
						rec.bom_id = bom_id
						message = f"<p><b> <em> (Detailed planning lines)</em> {old_product_id.name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{product_id.name}</span> for section {rec.section_id.name}, line {rec.packaging_line_id.name} and day {rec.detailed_pl_id.date_char} </b></p><ul>"
						rec.planning_id.message_post(body=message)
				if 'state' in vals:
					message = f"<p><b> <em> (Detailed planning lines)</em> {old_state} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{vals['state']}</span> for section {rec.section_id.name}, line {rec.packaging_line_id.name} and day {rec.detailed_pl_id.date_char} </b></p><ul>"
					rec.planning_id.message_post(body=message)
					# for move in rec.move_raw_ids:
					# 	for old_move in old_move_raw_ids:
					# 		if move == old_move:
					# 			move.unlink()



		return True


	# def _compute_state(self):

	# 	for rec in self:
	# 		super(MrpProductionInherit, rec)._compute_state()
	# 		rec.detailed_pl_id.state = rec.state
