from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class WizardOverview(models.TransientModel):
    _name = 'overview.wizard'
    _description = 'Overview Wizard'

    planning_id = fields.Many2one("mrp.planning", string=_("Planning"))
    overview_line_ids = fields.One2many("overview.wizard.line", "overview_id", string=_("Overview"))

    @api.model
    def default_get(self, fields_list):
        res = super(WizardOverview, self).default_get(fields_list)

        # if self.env.context.get('active_id'):
        #     planning = self.env["mrp.planning"].browse(self.env.context.get('active_id'))
        #
        #     context = self.env.context
        #     planning_id = self.env.context.get("planning_id")
        #     print("le context", context)
        #     print("le planning_id", planning_id)
        #     print("dans le if")
        #
        #     # Supprimer les lignes d'aperçu existantes pour éviter la duplication
        #     existing_overview_lines = self.env['overview.wizard.line'].search([('overview_id', '=', planning_id)])
        #     existing_overview_lines.unlink()
        #     print("les existants a supprimer",existing_overview_lines)
        #
        #     overview_lines = []
        #     temp_stock = self.env["stock.location"].search([("temp_stock", "=", 1)])
        #     if not temp_stock:
        #         raise ValidationError(_("No temp location found. Please configure it or contact support."))
        #
        #     for dl in planning.detailed_pl_ids:
        #         bom_id = self.env["mrp.bom"].search([("product_tmpl_id", "=", dl.product_id.product_tmpl_id.id)])
        #         bom_id = bom_id[0]
        #
        #         for line in bom_id.bom_line_ids:
        #             quant = self.env["stock.quant"].search(
        #                 [("product_id", "=", line.product_id.id), ("location_id", "=", temp_stock.id)]
        #             )
        #             on_hand_qty = quant.product_uom_id._compute_quantity(
        #                 quant.available_quantity, line.product_uom_id
        #             )
        #             required_qty = dl.qty * line.product_qty
        #             missing_qty = required_qty - on_hand_qty if on_hand_qty < required_qty else 0
        #
        #             overview_lines.append(
        #                 (0, 0, {
        #                     'product_id': line.product_id.id,
        #                     'required_qty': required_qty,
        #                     'on_hand_qty': on_hand_qty,
        #                     'missing_qty': missing_qty,
        #                     'uom_id': line.product_uom_id.id,
        #                     'bom_id': bom_id.id,
        #                     'overview_id': self.id,
        #                 })
        #             )
        #
        #     res.update({
        #         'planning_id': planning.id,
        #         'overview_line_ids': overview_lines,
        #     })
        # return res


        # On récupère le contexte actuel ainsi que les éléments dans le contexte
        context = self.env.context
        overview_ids = context.get("overview_ids", [])

        # Vérifie s'il y a un ID actif dans le contexte
        if self.env.context.get('active_id'):
            # Récupère l'enregistrement du modèle 'rm.overview' correspondant à l'ID actif
            rm_overview = self.env['rm.overview'].sudo().browse(self.env.context.get('active_id'))
            print("le rm_overview:", rm_overview.id)

            if rm_overview:
                overview_lines = []
                # Parcourt les IDs des éléments du modèle 'rm.overview' du contexte
                for line in overview_ids:
                    # Récupère l'enregistrement du modèle 'rm.overview' correspondant à l'ID de chaque élément
                    data = self.env['rm.overview'].browse(line)
                    overview_lines.append((0, 0, {
                        'product_id': data.product_id.id,
                        'required_qty': data.required_qty,
                        'on_hand_qty': data.on_hand_qty,
                        'missing_qty': data.missing_qty,
                        'uom_id': data.uom_id.id,
                        'bom_ids': [(6, 0, data.bom_ids.ids)],  # Utilise '6' pour les champs many2many
                    }))
                # Met à jour les valeurs existantes avec les nouvelles lignes
                res.update({
                    'planning_id': rm_overview.id,
                    'overview_line_ids': overview_lines,
                })
        return res




    def create_internal_transfer(self):
        print("debut de la fonction appeler")

        context = self.env.context
        overview_ids = context.get("overview_ids", [])
        planning_id = context.get("planning_id", False)
        total_missing_qty = context.get("total_missing_qty",[])

        if not planning_id:
            raise ValidationError(_("No planning ID found in the context."))

        # Récupère l'enregistrement du modèle 'mrp.planning' correspondant à l'ID de planning
        planning = self.env["mrp.planning"].browse(planning_id)

        # On peut maintenant accéder aux informations du planning
        print("Planning ID:", planning.id)
        print("Planning Reference:", planning.reference)
        print("le overview_ids: ", overview_ids, type(overview_ids))
        print("le total_missing_qty: ", total_missing_qty)

        # Recherche le type de transfert 'internal'
        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'internal')], order="id desc", limit=1)
        print('le picking ', picking_type.name)

        # Recherche des bons de livraison existants liés au planning
        existing_pickings = self.env['stock.picking'].search([
            ('state', 'not in', ['cancel']),
            ('planning_id','=', planning_id)
        ])
        # Annule les bons de livraison existants
        existing_pickings.action_cancel()

        if not picking_type:
            raise ValidationError(
                _("Error during Delivery Note creation. Cannot find operation type. Contact support."))

        # Recherche de l'emplacement 'stock tampon'
        stock_tampon_location = self.env['stock.location'].search(
            [('temp_stock', '=', 'True')], limit=1)
        if not stock_tampon_location:
            raise ValidationError(
                _("Error during Internal Transfer creation. Cannot find 'Stock tampon' location."))

        # Crée un bon de livraison (stock.picking)
        stock_picking = self.env['stock.picking'].create({
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': stock_tampon_location.id,
            'picking_type_id': picking_type.id,
            'planning_id': planning_id,
        })


        # Calcule la quantité totale manquante (missing_qty) de toutes les lignes d'overview
        total_missing_qty = sum(self.env['overview.wizard.line'].browse(overview_ids).mapped('missing_qty'))
        if total_missing_qty == 0:
            raise ValidationError(_("All missing quantity are equal to zero. The internal transfer cannot be created."))

        print("le type de overview_ids", type(overview_ids))

        # Parcourt les IDs des éléments d'overview pour créer les mouvements de stock
        for overview_id in overview_ids:
            data = self.env['rm.overview'].browse(overview_id)
            if not data.exists():
                print('Data:', data)
                print("L'enregistrement avec l'ID", overview_id, "n'existe pas ou a été supprimé.")
                continue

            print('Missing_qty', data.missing_qty)
            if data.missing_qty != 0:
                print("dans le if")
                # Crée un mouvement de stock (stock.move)
                stock_move = self.env['stock.move'].create({
                    'name': f'Send {data.product_id.name}',
                    'product_id': data.product_id.id,
                    'product_uom_qty': data.missing_qty,  # Quantité à transférer
                    'product_uom': data.uom_id.id,
                    'location_id': picking_type.default_location_src_id.id,
                    'location_dest_id': stock_tampon_location.id,
                    'picking_type_id': picking_type.id,
                    'picking_id': stock_picking.id,
                })
                print("Le stock_move :", stock_move)
                print("le dico ", stock_move["name"])
                    
        print('Transfert de produits effectué')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("the internal transfer has been successfully completed"),
            }
        }
    
    
class WizardOverviewLine(models.TransientModel):
    _name = 'overview.wizard.line'
    _description = 'Overview Wizard Line'
    
    product_id = fields.Many2one("product.product", string=_("Raw materiel"))
    required_qty = fields.Integer(_("Required qty"))
    on_hand_qty = fields.Integer(
        _("On hand qty"), compute="_compute_on_hand_qty_count")
    missing_qty = fields.Integer(_("Missing qty"))
    uom_id = fields.Many2one("uom.uom", string=_("Unit of measure"))

    bom_id = fields.Many2one("mrp.bom", string=_("Bill of material"))
    bom_ids = fields.Many2many("mrp.bom", string=_("Bill of materials"))
    overview_id = fields.Many2one("overview.wizard", string=_("Overview"))
    
    def _compute_on_hand_qty_count(self):
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
            
    