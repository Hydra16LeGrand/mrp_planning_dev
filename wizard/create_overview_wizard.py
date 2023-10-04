from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from datetime import timedelta
from lxml import etree
from lxml.etree import LxmlError

class WizardOverview(models.TransientModel):
	_name = 'overview.wizard'
	_description = 'Overview Wizard'

	planning_id = fields.Many2one("mrp.planning", string=_("Planning"))
	overview_line_ids = fields.One2many("overview.wizard.line", "overview_id", string=_("Overview"))
	plant_id = fields.Many2one("mrp.plant")
	start_date = fields.Date(string=("Start date"),copy=True)
	end_date = fields.Date(string=("End date"),copy=True)

	def create_days_overview_wizard(self):

		action = {
			"name": "Raw Material Overview Of Day",
			"res_model": "overview.wizard",
			"type": "ir.actions.act_window",
			"view_mode": "form",
			'target': 'new',
			"context": {
				'start_date': self.start_date,
				'end_date':self.end_date,
			}}

		return action

	@api.model
	def default_get(self, fields_list):
		res = super(WizardOverview, self).default_get(fields_list)

		# On récupère le contexte actuel ainsi que les éléments dans le contexte
		context = self.env.context
		planning = context.get("planning_id")
		start_date = context.get("start_date", False)
		end_date = context.get("end_date", False)

		if planning:
			planning_id = self.env['mrp.planning'].browse(planning)

		elif start_date and end_date:
			planning_id = self.planning_id


		# Verif if products of planning have a bill of material
		verif_product_proportion = planning_id.verif_product_proportion()

		if verif_product_proportion:
			raise ValidationError(_("No quantity found for %s in %s"% (verif_product_proportion[0],verif_product_proportion[1],)))

		detailed_pl_ids = planning_id.detailed_pl_ids.filtered(lambda self: self.date != False)

		if start_date and not end_date:
			start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
			detailed_pl_ids = detailed_pl_ids.filtered(lambda rec: rec.date == start_date)

			for line in detailed_pl_ids:
				lines = line.date

		elif start_date and end_date:
			start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
			end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

			# if start_date < planning_id.begin_date:
			# 	raise ValidationError(_("The date entered in start date is invalid"))
			# elif end_date > planning_id.end_date:
			# 	raise ValidationError(_("The date entered in end date is invalid"))

			# Utilisez la fonction `timedelta` pour obtenir une liste de dates entre start_date et end_date, y compris ces dates
			date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
			# Filtrez les enregistrements en vérifiant si la date de chaque enregistrement est dans la plage de dates
			detailed_pl_ids = detailed_pl_ids.filtered(lambda rec: rec.date in date_range)

		# Get needs line for operation processing
		overview_line = []
		for dl in detailed_pl_ids:

			bom_id = dl.bom_id
			temp_stock = self.env["stock.location"].search([("temp_stock", "=", 1), ('plant_id','=',planning_id.plant_id.id)])
			if not temp_stock:
				raise ValidationError(
					_("No temp location find. Please configure it or contact support.")
				)

			
			for line in bom_id.bom_line_ids:

				# Get temp stock quantity
				temp_stock_quant_ids = self.env["stock.quant"].search(
					[
						("product_id", "=", line.product_id.id),
						("location_id", "=", temp_stock.id),
					]
				)
				temp_stock_quant_qty = sum(temp_stock_quant_ids.mapped('quantity'))

				# Convert qty about unit of measure. Because of each raw material can have a different unit of measure for bom and storage(same categorie)
				on_hand_qty = temp_stock_quant_ids[0].product_uom_id._compute_quantity(
					temp_stock_quant_qty, line.product_uom_id
				) if temp_stock_quant_ids else 0

				# Get reception stock quantity
				reception_stock_quant_ids = self.env['stock.quant'].search([
					('product_id', '=', line.product_id.id),
					('location_id.replenish_location', '=', True)  # 'internal' pour le stock natif
				])
				main_stock_qty = sum(reception_stock_quant_ids.mapped('quantity'))
				
				required_qty = dl.qty * line.product_qty
				on_hand_qty = on_hand_qty
				dico = {
					'product_id': line.product_id.id,
					'required_qty': required_qty,
					'on_hand_qty': on_hand_qty,
					'main_stock_qty': main_stock_qty,
					'uom_id': line.product_uom_id.id,
					'location_id': line.location_id.id,
					'bom_id': line.bom_id.id,
				}
				overview_line.append(dico)

		print("Dico", overview_line)
		# Delete duplicate lines and accumulate all of products required_qty
		product_use_ids = []
		overview_to_unlink = []
		for overview in overview_line:
			if not overview['product_id'] in product_use_ids:
				product_use_ids.append(overview['product_id'])
				ov_by_products = [ovl for ovl in overview_line if
								  ovl['product_id'] == overview['product_id']]
				required_qty = 0
				for line in ov_by_products:
					required_qty += line['required_qty']
				print('required_qty in ovl -------------', ov_by_products)
				overview['bom_ids'] = [ov['bom_id'] for ov in ov_by_products]
				overview['required_qty'] = required_qty
				if overview['on_hand_qty'] > overview['required_qty']:
					overview['missing_qty'] = 0
				elif overview['on_hand_qty'] < overview['required_qty'] and overview['on_hand_qty'] > 0:
					overview['missing_qty'] = overview['required_qty'] - overview['on_hand_qty']
				else:
					overview['missing_qty'] = overview['required_qty']
			else:
				overview_to_unlink.append(overview)

		for ov in overview_to_unlink:
			ov.clear()

		filtered_overview_line = [overview for overview in overview_line if overview]
		overview_line = filtered_overview_line

		print(".................self.overview_line_ids................",self.overview_line_ids)

		print("le overview_line",overview_line)

		for rec in self.overview_line_ids:
			print("Dans ma boucle...................",rec.product_id.detailed_type_custom)
			if rec.product_id.detailed_type_custom == 'consu':
				rec.qty_to_order = 0
			else:
				rec.qty_to_order = rec.missing_qty

		overview_lines = []
		for element in overview_line:
			overview_lines.append((0, 0, {
				'product_id': element['product_id'],
				'required_qty': element['required_qty'],
				'on_hand_qty': element['on_hand_qty'],
				'missing_qty': element['missing_qty'],
				'location_id': element["location_id"],
				'uom_id': element['uom_id'],
				'bom_id': element['bom_id'],
			}))

		res.update({
			'planning_id': planning_id.id,
			'overview_line_ids': overview_lines,
			'start_date': start_date,
			'end_date': end_date,
		})

		return res

	# Function to create supply order from raw material necessary for a planning
	def create_internal_transfer(self):

		context = self.env.context
		overview_ids = context.get("overview_ids", [])
		planning_id = self.env["mrp.planning"].browse(context.get("planning_id"))

		if not planning_id:
			raise ValidationError(_("Error during processing this action. If persist, contact support."))		

		# Recherche le type de transfert 'internal'
		picking_type = self.env['stock.picking.type'].search(
			[('code', '=', 'internal'), ('plant_id', '=', planning_id.plant_id.id)])
		if not picking_type:
			raise ValidationError(
				_("Error during Delivery Note creation. Cannot find operation type. Contact support."))

		# Annule les bons de livraison existants
		self.env['stock.picking'].search([
			('state', 'not in', ['cancel', 'done']),
			('planning_id', '=', planning_id.id)
			]).action_cancel()


		# Recherche de l'emplacement 'stock tampon'
		stock_tampon_location = self.env['stock.location'].search([('temp_stock', '=', 'True'), ('plant_id', '=', self.planning_id.plant_id.id)])
		# [('temp_stock', '=', 'True'), ('plant_id', '=', self.env['mrp.planning'].browse(planning_id).plant_id.id)])
		if not stock_tampon_location:
			raise ValidationError(
				_("Error during Internal supply order creation. Cannot find 'Stock tampon' location."))

		# Crée un bon de livraison (stock.picking)
		stock_picking = self.env['stock.picking'].create({
			'location_id': picking_type.default_location_src_id.id,
			'location_dest_id': stock_tampon_location.id,
			'picking_type_id': picking_type.id,
			'planning_id': planning_id.id,
		})

		# Calcule la quantité totale manquante (missing_qty) de toutes les lignes d'overview
		total_missing_qty = sum(self.overview_line_ids.mapped('qty_to_order'))
		if total_missing_qty <= 0:
			raise ValidationError(
				_("The supply order cannot be created. The quantity to order must exceed 0."))

		# Parcourt les IDs des éléments d'overview pour créer les mouvements de stock
		print("Les lignes de overview", self.overview_line_ids)
		for data in self.overview_line_ids:
			if not data.exists():
				continue

			if data.qty_to_order > 0 and data.product_id.product_tmpl_id.detailed_type != 'consu':
				# Crée un mouvement de stock (stock.move)
				move_to_create = {
						'name': f'Send {data.product_id.name}',
						'product_id': data.product_id.id,
						'product_uom_qty': data.qty_to_order,  # Quantité à transférer
						'product_uom': data.uom_id.id,
						'location_id': data.location_id.id,
						'location_dest_id': stock_tampon_location.id,
						'picking_type_id': picking_type.id,
						'picking_id': stock_picking.id,
					}
				if data.location_id:
					move_to_create['location_id'] = data.location_id.id
					move_id = self.env['stock.move'].create(move_to_create)

				else:
					move_id = self.env['stock.move'].create(move_to_create)
				print("MOve create -------------------", move_id)
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

	def _compute_main_stock_count(self):
		for overview in self:
			quant = self.env['stock.quant'].search([
				('product_id', '=', overview.product_id.id),
				('location_id', '=', overview.location_id.id)
			])
			main_stock = sum(quant.mapped('quantity'))
			overview.main_stock = main_stock

			# if overview.product_id.detailed_type_custom == 'consu':
			# 	overview.qty_to_order = 0
			# 	overview.on_hand_qty = overview.required_qty
			# 	overview.missing_qty = 0
			# 	overview.qty_to_order_readonly = True
			# else:
			# 	overview.qty_to_order = overview.missing_qty
			# 	overview.qty_to_order_readonly = False

	# @api.depends('required_qty', 'product_id.net_weight')
	# def _compute_required_capacity_count(self):
	# 	for overview in self:
	# 		required_capacity = overview.required_qty * overview.product_id.net_weight
	# 		print("required_capacity", required_capacity)
	# 		overview.required_capacity = required_capacity

	product_id = fields.Many2one("product.product", string=_("Raw materiel"))
	required_qty = fields.Float(_("Required qty"), digits=(16, 0))
	on_hand_qty = fields.Float(
		_("On hand qty"), compute="_compute_on_hand_qty_count", digits=(16, 0))
	missing_qty = fields.Float(_("Missing qty"), digits=(16, 0))
	uom_id = fields.Many2one("uom.uom", string=_("Unit of measure"))
	location_id = fields.Many2one('stock.location', "Location")
	bom_id = fields.Many2one("mrp.bom", string=_("Bill of material"))
	bom_ids = fields.Many2many("mrp.bom", string=_("Bill of materials"))
	overview_id = fields.Many2one("overview.wizard", string=_("Overview"))
	qty_to_order = fields.Float(_("Quantity to order"), default=lambda self: self.missing_qty, digits=(16, 0))
	# required_capacity = fields.Float(string=_("Required capacity"), compute="_compute_required_capacity_count",
	# 								 digits=(16, 0))
	main_stock = fields.Float(
		_("Main Stock"), compute="_compute_main_stock_count", digits=(16, 0))
	qty_to_order_readonly = fields.Boolean(string="Readonly Qty")
