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
			res = super(MrpProductionInherit, rec).write(vals)
			print(f'vals : {vals}')
			if 'product_id' in vals:
				product_id = self.env['product.product'].search([('id', '=', vals['product_id'])])
				bom_id = self.env['mrp.bom'].search([('product_tmpl_id', '=', product_id.product_tmpl_id.id)])
				if bom_id:
					rec.detailed_pl_id.write({'product_id': vals['product_id']})
					rec.product_qty = old_qty
					rec.bom_id = bom_id

					# for move in rec.move_raw_ids:
					# 	for old_move in old_move_raw_ids:
					# 		if move == old_move:
					# 			move.unlink()


		return True


	# def _compute_state(self):

	# 	for rec in self:
	# 		super(MrpProductionInherit, rec)._compute_state()
	# 		rec.detailed_pl_id.state = rec.state
