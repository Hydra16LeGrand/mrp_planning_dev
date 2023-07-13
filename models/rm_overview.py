from odoo import fields, models, api, _


class RM_Overview(models.Model):
	_name = "rm.overview"

	product_id = fields.Many2one("product.product", string=_("Raw materiel"))
	required_qty = fields.Integer(_("Required qty"))
	on_hand_qty = fields.Integer(_("On hand qty"))
	missing_qty = fields.Integer(_("Missing qty"))
	uom_id = fields.Many2one("uom.uom", string=_("Unit of measure"))

	bom_id = fields.Many2one("mrp.bom", string=_("Bill of material"))
	bom_ids = fields.Many2many("mrp.bom", string=_("Bill of materials"))
	detail_line_id = fields.Many2one("mrp.detail.planning.line")
	planning_line_id = fields.Many2one(related="detail_line_id.planning_line_id", store=True)
	planning_id = fields.Many2one(related="detail_line_id.planning_id", store=True)

	def create_internal_transfer(self):

		picking_type = self.env['stock.picking.type'].search(
			[('code', '=', 'internal')], order="id desc", limit=1)
		print('le picking ', picking_type.name)

		existing_pickings = self.env['stock.picking'].search([
			('state', 'not in', ['cancel']),
			('planning_id', '=', self.planning_id.id)
		])
		existing_pickings.action_cancel()

		if not picking_type:
			raise ValidationError(
				_("Error during Delivery Note creation. Cannot find operation type. Contact support."))

		stock_tampon_location = self.env['stock.location'].search(
			[('temp_stock', '=', 'True')], limit=1)
		if not stock_tampon_location:
			raise ValidationError(
				_("Error during Internal Transfer creation. Cannot find 'Stock tampon' location."))

		stock_picking = self.env['stock.picking'].create({
			'location_id': picking_type.default_location_src_id.id,
			'location_dest_id': stock_tampon_location.id,
			'picking_type_id': picking_type.id,
			'planning_id': self.planning_id.id,

		})

		# Effectuer d'autres opérations spécifiques au transfert interne
		print("Transfert interne créé pour les éléments :",
			  [data.product_id.name for data in self])

		stock_move = []

		for data in self:
			if data.missing_qty != 0:
				stock_move.append(
					self.env['stock.move'].create({
						'name': f'Send {data.product_id.name}',
						'product_id': data.product_id.id,
								'product_uom_qty': data.missing_qty,  # Quantité à retourner
								'product_uom': data.uom_id.id,
								'location_id': picking_type.default_location_src_id.id,
								'location_dest_id': stock_tampon_location.id,
								# 'state': 'done',
								'picking_type_id': picking_type.id,
								'picking_id': stock_picking.id,
					})
				)
		print('Transfert de produits effectué')

		return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
					'type': 'success',
					'message': _("the internal transfer has been successfully completed"),
			}
		}