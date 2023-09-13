from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class WizardOverview(models.TransientModel):
	_name = 'overview.wizard'
	_description = 'Overview Wizard'

	planning_id = fields.Many2one("mrp.planning", string=_("Planning"))
	overview_line_ids = fields.One2many("overview.wizard.line", "overview_id", string=_("Overview"))
	plant_id = fields.Many2one("mrp.plant")


	@api.model
	def default_get(self, fields_list):
		res = super(WizardOverview, self).default_get(fields_list)

		# On récupère le contexte actuel ainsi que les éléments dans le contexte
		context = self.env.context
		overview_ids = context.get("overview_ids", [])
		planning = context.get("planning_id")

		# Vérifie s'il y a un ID actif dans le contexte
		if self.env.context.get('active_id'):
			# Récupère l'enregistrement du modèle 'mrp.planning' correspondant à l'ID actif
			planning = self.env['mrp.planning'].browse(self.env.context.get('active_id'))

			# Verif if products of planning have a bill of material
			verif_bom = planning.verif_bom()
			# Verif if products of planning have all qty informations necessary
			verif_product_proportion = planning.verif_product_proportion()
			if verif_bom:
				raise ValidationError(
					_(
						"No bill of material find for %s. Please create a one."
						% verif_bom.name
					)
				)

			if verif_product_proportion:
				raise ValidationError(
					_(
						"No quantity found for %s in %s"
						% (
							verif_product_proportion[0],
							verif_product_proportion[1],
						)
					)
				)

		overview_line = []
		for dl in planning.detailed_pl_ids:
			bom_id = self.env["mrp.bom"].search(
				[("product_tmpl_id", "=", dl.product_id.product_tmpl_id.id)]
			)
			bom_id = bom_id[0]
			temp_stock = self.env["stock.location"].search([("temp_stock", "=", 1), ('plant_id', '=', planning.plant_id.id)])
			if not temp_stock:
				raise ValidationError(
					_("No temp location find. Please configure it or contact support.")
				)

			for line in bom_id.bom_line_ids:
				quant = self.env["stock.quant"].search(
					[
						("product_id", "=", line.product_id.id),
						("location_id", "=", temp_stock.id),
					]
				)
				# Convert qty about unit of measure. Because of each raw material can have a different unit of measure for bom and storage(same categorie)
				on_hand_qty = quant.product_uom_id._compute_quantity(
					quant.available_quantity, line.product_uom_id
				)

				product_id = line.product_id.id
				required_qty = dl.qty * line.product_qty / bom_id.product_qty
				on_hand_qty = on_hand_qty

				if line.location_id.id:
					location_id = line.location_id.id
				else:
					location_id = False

				dico = {
					'product_id': product_id,
					'location_id': location_id,
					'required_qty': required_qty,
					'on_hand_qty': on_hand_qty,
					'uom_id': line.product_uom_id.id,
					'bom_id': line.bom_id.id,
				}
				overview_line.append(dico)


		# Delete duplicate lines and accumulate all of products required_qty
		product_use_ids = []
		overview_to_unlink = []
		for overview in overview_line:
			if not overview['product_id'] in product_use_ids:
				product_use_ids.append(overview['product_id'])
				ov_by_products = [planning for planning in overview_line if
								  planning['product_id'] == overview['product_id']]
				required_qty = 0
				for line in ov_by_products:
					required_qty += line['required_qty']

				overview['bom_ids'] = [ov['bom_id'] for ov in ov_by_products]
				overview['required_qty'] = required_qty
				overview['missing_qty'] = (
					overview['required_qty'] - overview['on_hand_qty']
					if overview['on_hand_qty'] < overview['required_qty']
					else 0
				)
			else:
				overview_to_unlink.append(overview)

		for ov in overview_to_unlink:
			ov.clear()

		filtered_overview_line = [overview for overview in overview_line if overview]
		overview_line = filtered_overview_line


		overview_lines = []
		for element in overview_line:
			overview_lines.append((0, 0, {
				'product_id': element['product_id'],
				'location_id': element["location_id"],
				'required_qty': element['required_qty'],
				'on_hand_qty': element['on_hand_qty'],
				'missing_qty': element['missing_qty'],
				'uom_id': element['uom_id'],
				'bom_id': element['bom_id'],
				# 'ordered_qty': element['missing_qty'],
			}))

		total_missing_qty = (line['missing_qty'] for line in self.overview_line_ids)

		res.update({
			'planning_id': planning.id,
			'overview_line_ids': overview_lines,
		})

		return res

	# Function to create supply order from raw material necessary for a planning
	def create_internal_transfer(self):

		context = self.env.context
		overview_ids = context.get("overview_ids", [])
		planning_id = context.get("planning_id", False)
		total_missing_qty = context.get("total_missing_qty", [])

		if not planning_id:
			raise ValidationError(_("No planning ID found in the context."))

		# Récupère l'enregistrement du modèle 'mrp.planning' correspondant à l'ID de planning
		planning = self.env["mrp.planning"].browse(planning_id)

		# On peut maintenant accéder aux informations du planning

		# Recherche le type de transfert 'internal'
		picking_type = self.env['stock.picking.type'].search(
			[('code', '=', 'internal'), ('plant_id', '=', planning.plant_id.id)])


		# Recherche des bons de livraison existants liés au planning
		existing_pickings = self.env['stock.picking'].search([
			('state', 'not in', ['cancel', 'done']),
			('planning_id', '=', planning_id)
		])
		# Annule les bons de livraison existants
		existing_pickings.action_cancel()

		if not picking_type:
			raise ValidationError(
				_("Error during Delivery Note creation. Cannot find operation type. Contact support."))

		# Recherche de l'emplacement 'stock tampon'
		stock_tampon_location = self.env['stock.location'].search(
			[('temp_stock', '=', 'True'), ('plant_id', '=', self.env['mrp.planning'].browse(planning_id).plant_id.id)])
		if not stock_tampon_location:
			raise ValidationError(
				_("Error during Internal supply order creation. Cannot find 'Stock tampon' location."))

		# Crée un bon de livraison (stock.picking)
		stock_picking = self.env['stock.picking'].create({
			'location_id': picking_type.default_location_src_id.id,
			'location_dest_id': stock_tampon_location.id,
			'picking_type_id': picking_type.id,
			'planning_id': planning_id,
		})

		# Calcule la quantité totale manquante (missing_qty) de toutes les lignes d'overview
		total_missing_qty = sum(self.overview_line_ids.mapped('missing_qty'))
		if total_missing_qty == 0:
			raise ValidationError(
				_("The supply order cannot be created. The raw materials are in sufficient quantity in the stock."))


		# Parcourt les IDs des éléments d'overview pour créer les mouvements de stock
		for data in self.overview_line_ids:
			if not data.exists():
				continue

			if data.missing_qty != 0:
				# Crée un mouvement de stock (stock.move)
				if data.location_id:
					print(f"data.location_id : {data.location_id}")
					stock_move = self.env['stock.move'].create({
						'name': f'Send {data.product_id.name}',
						'product_id': data.product_id.id,
						'product_uom_qty': data.qty_to_order,  # Quantité à transférer
						'product_uom': data.uom_id.id,
						'location_id': data.location_id.id,
						'location_dest_id': stock_tampon_location.id,
						'picking_type_id': picking_type.id,
						'picking_id': stock_picking.id,
					})

				else:
					print(f"No data.location_id")
					stock_move = self.env['stock.move'].create({
						'name': f'Send {data.product_id.name}',
						'product_id': data.product_id.id,
						'product_uom_qty': data.qty_to_order,  # Quantité à transférer
						'product_uom': data.uom_id.id,
						'location_id': picking_type.default_location_src_id.id,
						'location_dest_id': stock_tampon_location.id,
						'picking_type_id': picking_type.id,
						'picking_id': stock_picking.id,
					})

		return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'type': 'success',
				'message': _("the supply order has been successfully created"),
				'next': {'type': 'ir.actions.act_window_close'},
			}
		}
	
	
class WizardOverviewLine(models.TransientModel):
	_name = 'overview.wizard.line'
	_description = 'Overview Wizard Line'
	
	product_id = fields.Many2one("product.product", string=_("Raw materiel"))
	location_id = fields.Many2one('stock.location', "Location")
	required_qty = fields.Float(_("Required qty"), digits=(16, 0))
	on_hand_qty = fields.Float(
		_("On hand qty"), compute="_compute_on_hand_qty_count", digits=(16, 0))
	missing_qty = fields.Float(_("Missing qty"), digits=(16, 0))
	uom_id = fields.Many2one("uom.uom", string=_("Unit of measure"))

	bom_id = fields.Many2one("mrp.bom", string=_("Bill of material"))
	bom_ids = fields.Many2many("mrp.bom", string=_("Bill of materials"))
	overview_id = fields.Many2one("overview.wizard", string=_("Overview"))
	qty_to_order = fields.Float(_("Quantity to order"), default=lambda self: self.missing_qty, digits=(16, 0))
	required_capacity = fields.Float(string=_("Required capacity"), compute="_compute_required_capacity_count",digits=(16, 0))

	
	def _compute_on_hand_qty_count(self):
		temp_stock = self.env['stock.location'].search(
			[('temp_stock', '=', 1), ('plant_id', '=', self.overview_id.planning_id.plant_id.id)])
		if not temp_stock:
			raise ValidationError(
				_("No temp location found. Please configure it or contact support."))

		for overview in self:
			quant = self.env['stock.quant'].search([
				('product_id', '=', overview.product_id.id),
				('location_id', '=', temp_stock.id)
			])
			on_hand_qty = sum(quant.mapped('quantity'))
			overview.on_hand_qty = on_hand_qty

	@api.depends('required_qty', 'product_id.net_weight')
	def _compute_required_capacity_count(self):
		for overview in self:
			required_capacity = overview.required_qty * overview.product_id.net_weight
			print("required_capacity",required_capacity)
			overview.required_capacity = required_capacity
