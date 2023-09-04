# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CreatePickingFinishedProduct(models.TransientModel):
    _name = 'create.picking.finished.product'
    _description = 'Create Picking Finished Product'

    @api.model
    def default_get(self, fields_list):
        res = super(CreatePickingFinishedProduct, self).default_get(fields_list)
        group_list = []
        if self.env.context.get('quant_line'):
            quant_line = self.env.context.get('quant_line')
            for elm in quant_line:
                quant = self.env['stock.quant'].browse(elm)
                if quant.quantity <= 0:
                    continue
                group_list.append(
                    (0, 0, {
                        'product_id': quant.product_id.id,
                        'location_id': quant.location_id.id,
                        'quantity': quant.quantity,
                        'old_quantity': quant.quantity,
                        'product_uom_id': quant.product_uom_id.id,
                    })
                )

            if not group_list:
                raise UserError(_("There can be no transfer when there is no quantity."))
            res['cp_finished_line_ids'] = group_list
        return res

    cp_finished_line_ids = fields.One2many('wizard.finished.product.line', inverse_name='cp_finished_product_id',
                                           string='CP Finished Product Line')

    # Function for packaging of products from a location to another
    def action_send(self):
        # Créez un dictionnaire pour regrouper les lignes par location
        lines_by_location = {}
        quant_lst = []

        for line in self.cp_finished_line_ids:
            location_id = line.location_id.id

            # Si la location n'est pas encore dans le dictionnaire, créez-la avec une liste vide
            if location_id not in lines_by_location:
                lines_by_location[location_id] = []

            lines_by_location[location_id].append(line)

        for location_id, lines in lines_by_location.items():

            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'internal')], limit=1)
            location_dest_id = self.env['stock.location'].search([
                ('plant_id.is_principal', '!=', False),
                ('packaged_finished_product', '=', True)
            ])

            if not location_dest_id:
                raise UserError(_("No packaged finished product location found. Check location configurations please."))

            # Créez le picking pour cette location
            stock_picking = self.env['stock.picking'].create({
                'location_id': location_id,
                'location_dest_id': location_dest_id.id,
                'picking_type_id': picking_type.id,
            })

            for line in lines:
                if not line.pack_of:
                    # Créez un mouvement de stock pour chaque ligne
                    stock_move = self.env['stock.move'].create({
                        'name': f'Send {line.product_id.name}',
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity,
                        'product_uom': line.product_uom_id.id,
                        'location_id': line.location_id.id,
                        'location_dest_id': location_dest_id.id,
                        'picking_type_id': picking_type.id,
                        'picking_id': stock_picking.id,
                    })
                else:
                    quotient = int(line.quantity) // line.pack_of
                    stock_move = self.env['stock.move'].create({
                        'name': f'Send {line.product_id.name}',
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity,
                        'product_uom': line.product_uom_id.id,
                        'location_id': line.location_id.id,
                        'location_dest_id': location_dest_id.id,
                        'picking_type_id': picking_type.id,
                        'picking_id': stock_picking.id,
                        'quantity_done': line.quantity,
                    })

                    stock_picking.sudo().action_put_in_pack()
                    print(f"stock_picking : {stock_picking}")
                    move_line = self.env['stock.move.line'].search([
                        ('move_id', '=', stock_move.id)
                    ])
                    quant_dico = {
                        'quotient': quotient,
                        'move_line': move_line,
                        'pack_of': line.pack_of,
                        # quotient: move_line
                    }
                    quant_lst.append(quant_dico)


            # Confirmez et validez le picking
            stock_picking.sudo().action_confirm()
            stock_picking.sudo().action_set_quantities_to_reservation()
            stock_picking.sudo().button_validate()

            # Ajoutez le nombre de colis dans stock_quant
            if quant_lst:
                print(f"quant_lst : {quant_lst}")
                for elm in quant_lst:
                    quant_id = self.env['stock.quant'].search([
                        ('package_id', '=', elm['move_line'].result_package_id.id)
                    ])
                    print(f'quant_id : {quant_id}')
                    pack = f"{elm['quotient']} pack of {elm['pack_of']}"
                    quant_id.pack_of = pack
                    quant_id.pack = elm['pack_of']
                    quant_id.package = elm['quotient']
                    print(f"quant_id.pack_of: {quant_id.pack_of}")
                    # print(f"key : {elm.keys()}")
                    # print(f"value : {elm.values()}")
                    # for val in elm.values():
                    #     move_line = val
                    #     print(f"move_line : {move_line}")
                    #     quant_id = self.env['stock.quant'].search([
                    #         ('package_id', '=', move_line.result_package_id.id)
                    #     ])
                    #     print(f"quant_id : {quant_id}")


        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': "The transfer of finished product has been successfully created",
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class WizardFinishedProductLine(models.TransientModel):
    _name = 'wizard.finished.product.line'
    _description = 'Wizard Finished Product Line'

    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('stock.location', string='Source location')
    quantity = fields.Float(string='Quantity', required=True)
    old_quantity = fields.Float(string='Current quantity in stock')
    product_uom_id = fields.Many2one('uom.uom', string='Unit')
    cp_finished_product_id = fields.Many2one('create.picking.finished.product', string='Create Picking Finished Product')
    pack_of = fields.Integer(string='Pack of')

    @api.onchange('quantity')
    def _onchange_qty(self):
        for rec in self:
            if rec.quantity > rec.old_quantity:
                rec.quantity = rec.old_quantity
                raise UserError(_('The transfer quantity cannot be greater than the current stock quantity.'))

    @api.onchange('pack_of')
    def _onchange_pack_of(self):
        for rec in self:
            if rec.pack_of // rec.quantity != 0 or rec.quantity < rec.pack_of:
                rec.pack_of = False
                raise UserError(_('You must put a parcel proportional to the quantity'))