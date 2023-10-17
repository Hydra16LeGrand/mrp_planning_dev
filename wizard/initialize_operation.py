# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class InitialiseOperation(models.TransientModel):
    _name = "initialize.operation"

    io_line_ids = fields.One2many('initialize.operation.line', inverse_name='io_id')

    @api.model
    def default_get(self, fields_list):

        res = super(InitialiseOperation, self).default_get(fields_list)
        quant_ids = self.env['stock.quant'].browse(self._context.get('quant_ids', False))
        io_lines = [(0, 0, {
            'product_id': quant.product_id.id,
            'location_id': quant.location_id.id,
            'on_hand_qty': quant.quantity,
            'product_uom_id': quant.product_uom_id.id,
        }) for quant in quant_ids]

        res.update({'io_line_ids': io_lines})
        return res

    def intiliaze_operation(self):

        warehouse_id = self.env['stock.warehouse'].search([('manufacture_to_resupply', '=', True)])
        if not warehouse_id:
            raise ValidationError(
                _("No manufacturing warehouse found. Ensure to check \"manufacture to resupply\" field in warehouse settings."))
        # Add wharehouse
        picking_type_id = self.env['stock.picking.type'].search(
            [('code', '=', 'outgoing'), ('warehouse_id', '=', warehouse_id.id)], limit=1)

        if not picking_type_id:
            raise ValidationError(
                _("Error during Delivery creation. Cannot find operation type. Contact support."))
        # Crée un bon de livraison (stock.picking)
        picking_id = self.env['stock.picking'].create({
            'location_id': self.io_line_ids[0].location_id.id,
            'location_dest_id': picking_type_id.default_location_dest_id.id,
            'picking_type_id': picking_type_id.id
        })

        self.env['stock.move'].create([{
            'name': f'{data.product_id.name}',
            'product_id': data.product_id.id,
            'product_uom_qty': data.to_send_qty,  # Quantité à transférer
            'product_uom': data.product_uom_id.id,
            'location_id': data.location_id.id,
            'location_dest_id': picking_type_id.default_location_dest_id.id,
            'picking_type_id': picking_type_id.id,
            'picking_id': picking_id.id,
        } for data in self.io_line_ids])

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("The delivery note has successfully created"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class InitializeOperationLine(models.TransientModel):
    _name = "initialize.operation.line"

    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('stock.location', string='Source location')
    on_hand_qty = fields.Float(string='In stock')
    to_send_qty = fields.Float(string='To send', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit')

    io_id = fields.Many2one('initialize.operation')
