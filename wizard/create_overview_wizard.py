from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from datetime import timedelta



class WizardOverview(models.TransientModel):
    _name = 'overview.wizard'
    _description = 'Overview Wizard'

    planning_id = fields.Many2one("mrp.planning", string=_("Planning"))
    overview_line_ids = fields.One2many("overview.wizard.line", "overview_id", string=_("Overview"))
    plant_id = fields.Many2one("mrp.plant")
    start_date = fields.Date(string=("Start date"),copy=True)
    end_date = fields.Date(string=("End date"),copy=True)



    def create_days_overview_wizard(self):
        print("le self", self)
        print("Le planning",self.planning_id.id)
        action = {
            "name": "Raw Material Overview Of Day",
            "res_model": "overview.wizard",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            # "view_id": self.env.ref("mrp_planning.view_create_overview_wizard_from").id,
            'target': 'new',
            "context": {
                'start_date': self.start_date,
                'end_date':self.end_date,
            }

        }
        return action


    @api.model
    def default_get(self, fields_list):
        res = super(WizardOverview, self).default_get(fields_list)

        # On récupère le contexte actuel ainsi que les éléments dans le contexte
        context = self.env.context
        planning = context.get("planning_id")
        start_date = context.get("start_date", False)
        end_date = context.get("end_date", False)
        print("Planning_ids",self.env.context)

        if planning:
            planning_id = self.env['mrp.planning'].browse(planning)

        elif start_date:
            planning_id = self.planning_id
            print("la deucieme action", planning_id)



        # Vérifie s'il y a un ID actif dans le contexte

        # Verif if products of planning have a bill of material
        verif_bom = planning_id.verif_bom()
        # Verif if products of planning have all qty informations necessary
        verif_product_proportion = planning_id.verif_product_proportion()
        if verif_bom:
            raise ValidationError(_("No bill of material find for %s. Please create a one."% verif_bom.name))

        if verif_product_proportion:
            raise ValidationError(_("No quantity found for %s in %s"% (verif_product_proportion[0],verif_product_proportion[1],)))

        overview_line = []
        detailed_pl_ids = planning_id.detailed_pl_ids

        if start_date and not end_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            print("detailed_pl_ids avant", detailed_pl_ids)
            detailed_pl_ids = detailed_pl_ids.filtered(lambda rec: rec.date == start_date)
            print("detailed_pl_ids apres", detailed_pl_ids)

            for line in detailed_pl_ids:
                lines = line.date
                print("les dates planning line deatils",line.name, line.id )

        elif start_date and end_date:
            print("dans le elif")
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            if start_date < planning_id.begin_date:
                raise ValidationError(_("The date entered in start date is invalid"))
            elif end_date > planning_id.end_date:
                raise ValidationError(_("The date entered in end date is invalid"))

            # Utilisez la fonction `timedelta` pour obtenir une liste de dates entre start_date et end_date, y compris ces dates
            date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

            # Filtrez les enregistrements en vérifiant si la date de chaque enregistrement est dans la plage de dates
            detailed_pl_ids = detailed_pl_ids.filtered(lambda rec: rec.date in date_range)

            print("detailed_pl_ids entre start_date et end_date inclusivement:", detailed_pl_ids)

        #Dans le elif j'aimerais filtered le element qui sont compris entre strart_date et end_date sachant que entre les deux date il peut il avoir. donc veut filtrer pour tout les jours de start_date jusqua end_date

        for dl in detailed_pl_ids:
            bom_id = self.env["mrp.bom"].search(
                [("product_tmpl_id", "=", dl.product_id.product_tmpl_id.id)]
            )
            print("le bom",bom_id)
            bom_id = bom_id[0]
            temp_stock = self.env["stock.location"].search([("temp_stock", "=", 1), ('plant_id','=',planning_id.plant_id.id)])
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

                quant_ids = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id.usage', '=', 'internal')  # 'internal' pour le stock natif
                ])
                main_stock = sum(quant_ids.mapped('quantity'))

                # Convert qty about unit of measure. Because of each raw material can have a different unit of measure for bom and storage(same categorie)
                on_hand_qty = quant.product_uom_id._compute_quantity(
                    quant.available_quantity, line.product_uom_id
                )

                product_id = line.product_id.id
                required_qty = dl.qty * line.product_qty
                on_hand_qty = on_hand_qty

                print("la valeur du champ main_stock:", main_stock)

                dico = {
                    'product_id': product_id,
                    'required_qty': required_qty,
                    'on_hand_qty': on_hand_qty,
                    'main_stock': main_stock,
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
                print('Operation', overview['required_qty'] - (overview['on_hand_qty'] + overview['main_stock']))
                overview['missing_qty'] = (
                    overview['required_qty'] - overview['on_hand_qty'] + overview['main_stock']
                    if overview['on_hand_qty'] + overview['main_stock'] < overview['required_qty']
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
                'required_qty': element['required_qty'],
                'on_hand_qty': element['on_hand_qty'],
                'missing_qty': element['missing_qty'],
                'uom_id': element['uom_id'],
                'bom_id': element['bom_id'],
            }))

        res.update({
            'planning_id': planning_id.id,
            'overview_line_ids': overview_lines,
        })

        return res

    # Function to create supply order from raw material necessary for a planning
    def create_internal_transfer(self):

        context = self.env.context
        overview_ids = context.get("overview_ids", [])
        planning_id = context.get("planning_id", False)

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
        stock_tampon_location = self.env['stock.location'].search([('temp_stock', '=', 'True')])
        # [('temp_stock', '=', 'True'), ('plant_id', '=', self.env['mrp.planning'].browse(planning_id).plant_id.id)])
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

    def _compute_on_hand_qty_count(self):
        # temp_stock = self.env['stock.location'].search(
        # 	[('temp_stock', '=', 1), ('plant_id', '=', self.overview_id.planning_id.plant_id.id)])

        temp_stock = self.env['stock.location'].search(
            [('temp_stock', '=', 1)])
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
                ('location_id.usage', '=', 'internal')  # 'internal' pour le stock natif
            ])

            main_stock = sum(quant.mapped('quantity'))
            overview.main_stock = main_stock

    @api.depends('required_qty', 'product_id.net_weight')
    def _compute_required_capacity_count(self):
        for overview in self:
            required_capacity = overview.required_qty * overview.product_id.net_weight
            print("required_capacity", required_capacity)
            overview.required_capacity = required_capacity

    product_id = fields.Many2one("product.product", string=_("Raw materiel"))
    required_qty = fields.Float(_("Required qty"), digits=(16, 0))
    on_hand_qty = fields.Float(
        _("On hand qty"), compute="_compute_on_hand_qty_count", digits=(16, 0))
    missing_qty = fields.Float(_("Missing qty"), digits=(16, 0))
    uom_id = fields.Many2one("uom.uom", string=_("Unit of measure"))

    bom_id = fields.Many2one("mrp.bom", string=_("Bill of material"))
    bom_ids = fields.Many2many("mrp.bom", string=_("Bill of materials"))
    overview_id = fields.Many2one("overview.wizard", string=_("Overview"))
    qty_to_order = fields.Float(_("Quantity to order"), default=lambda self: self.missing_qty, digits=(16, 0))
    required_capacity = fields.Float(string=_("Required capacity"), compute="_compute_required_capacity_count",
                                     digits=(16, 0))
    main_stock = fields.Float(
        _("Main Stock"), compute="_compute_main_stock_count", digits=(16, 0))

