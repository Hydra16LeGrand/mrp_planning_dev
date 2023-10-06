# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class StockQuantInherit(models.Model):
	_inherit = 'stock.quant'

	# pack_of_bool = fields.Boolean(compute="_compute_pack_of_bool")
	pack_of_bool = fields.Selection([
		('true', 'True'),
		('false', 'False'),
	], compute="_compute_pack_of_bool")
	pack_of = fields.Char('Pack Of')
	package = fields.Integer('Package')
	pack = fields.Integer('Pack')

	@api.depends('pack_of')
	def _compute_pack_of_bool(self):
		for rec in self:
			if rec.pack_of:
				print(f"rec.pack_of : {rec.pack_of}")
				rec.pack_of_bool = "true"
			else:
				rec.pack_of_bool = "false"

	def finished_product_transfer(self):
		quant_lst = []

		for rec in self:
			# quant_lst = []
			if rec.location_id.unpackaged_finished_product:
				quant_lst.append(rec.id)
			elif rec.location_id.temp_stock:
				raise ValidationError(_("You cannot create a transfer from a Raw Material location."))
			elif rec.location_id.packaged_finished_product:
				raise ValidationError(_("You cannot create a transfer from a finished product location."))
			else:
				raise ValidationError(_("You cannot create a transfer from this location."))

		if quant_lst:
			action = {
				"name": "Picking Finished Product",
				"res_model": "create.picking.finished.product",
				"type": "ir.actions.act_window",
				"view_mode": "form",
				# "view_id": self.env.ref("view_create_overview_wizard_from").id,
				'target': 'new',
				"context": {
					'quant_line': quant_lst,
				},
			}
			print(f"action finished: {action}")
			return action

	def calculating_packs(self):
		quant_lst = []
		for rec in self:
			if not rec.pack_of:
				raise ValidationError(_(f"You cannot calculate the packs for product {rec.product_id.name}. Create a packaged before"))
			if not rec.location_id.packaged_finished_product:
				raise ValidationError(_(f"No packaged location found for this action"))
			quant_lst.append(rec.id)

		if quant_lst:
			action = {
				"name": "Calculating Packs",
				"res_model": "calculating.pack",
				"type": "ir.actions.act_window",
				"view_mode": "form",
				'target': 'new',
				"context": {
					'quant_line': quant_lst,
				},
			}
			print(f"action calculating: {action}")
			return action

	def make_delivery(self):

		# warehouse_id = self.env['stock.warehouse'].search([('manufacture_to_resupply', '=', True)])
		# if not warehouse_id:
		#     raise ValidationError(_("No manufacturing warehouse found. Ensure to check \"manufacture to resupply\" field in warehouse settings."))
		# # Add wharehouse
		# picking_type_id = self.env['stock.picking.type'].search(
		#     [('code', '=', 'outgoing'), ('warehouse_id', '=', warehouse_id.id)], limit=1)

		# if not picking_type_id:
		#     raise ValidationError(
		#         _("Error during Delivery creation. Cannot find operation type. Contact support."))

		# # Crée un bon de livraison (stock.picking)
		# picking_id = self.env['stock.picking'].create({
		#     'location_id': self[0].location_id.id,
		#     'location_dest_id': picking_type_id.default_location_dest_id.id,
		#     'picking_type_id': picking_type_id.id
		# })

		# self.env['stock.move'].create([{
		#         'name': f'{data.product_id.name}',
		#         'product_id': data.product_id.id,
		#         'product_uom_qty': data.quantity,  # Quantité à transférer
		#         'product_uom': data.product_uom_id.id,
		#         'location_id': data.location_id.id,
		#         'location_dest_id': picking_type_id.default_location_dest_id.id,
		#         'picking_type_id': picking_type_id.id,
		#         'picking_id': picking_id.id,
		#     } for data in self])

		# return {
		#     'type': 'ir.actions.client',
		#     'tag': 'display_notification',
		#     'params': {
		#         'type': 'success',
		#         'message': _("The delivery note has successfully created"),
		#         'next': {'type': 'ir.actions.act_window_close'},
		#     }
		# }

		action = {
			"name": "Initialize Operation",
			"res_model": "initialize.operation",
			"type": "ir.actions.act_window",
			"view_mode": "form",
			# "view_id": self.env.ref("view_create_overview_wizard_from").id,
			'target': 'new',
			"context": {
				"quant_ids": self.ids,
			},
		}
		return action
