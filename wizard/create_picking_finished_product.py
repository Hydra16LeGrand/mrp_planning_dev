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
        print(f'self.env.context : {self.env.context}')
        if self.env.context.get('quant_line'):
            quant_line = self.env.context.get('quant_line')
            for elm in quant_line:
                quant = self.env['stock.quant'].browse(elm)
                if quant.quantity <= 0:
                    continue
                group_list.append(
                    (0, 0, {
                        'product_id': quant.product_id.id,
                        'product_domain': quant.product_id.id,
                        'location_id': quant.location_id.id,
                        'location_domain': quant.location_id.id,
                        'quantity': quant.quantity,
                        'old_quantity': quant.quantity,
                        'product_uom_id': quant.product_uom_id.id,
                        'product_uom_domain': quant.product_uom_id.id,
                    })
                )

            print(f"group_list : {group_list}")
            if not group_list:
                raise UserError(_("There can be no transfer when there is no quantity."))
            res['cp_finished_line_ids'] = group_list
        return res

    cp_finished_line_ids = fields.One2many('wizard.finished.product.line', inverse_name='cp_finished_product_id',
                                           string='CP Finished Product Line')

    def action_send(self):
        print(f'self.env.context : {self.env.context}')
        # print(f'self.cp_finished_line_ids : {self.cp_finished_line_ids}')
        for line in self.cp_finished_line_ids:
            # for line in rec.cp_finished_line_ids:
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'internal')], order="id desc", limit=1)
            location_dest_id = self.env['stock.location'].search([
                ('plant_id.is_principal', '!=', False),
                ('temp_stock', '=', True)
            ])
            print(f"line.product_id : {line.product_id.id}")
            print(f"line.location_id : {line.location_id.id}")
            print(f"line.product_uom_id : {line.product_uom_id}")
            print(f"line.quantity : {line.quantity}")
            stock_picking = self.env['stock.picking'].create({
                'location_id': line.location_id.id,
                'location_dest_id': location_dest_id.id,
                'picking_type_id': picking_type.id,
            })

            stock_move = self.env['stock.move'].create({
                'name': f'Send {line.product_id.name}',
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,  # Quantité à transférer
                'product_uom': line.product_uom_id.id,
                'location_id': line.location_id.id,
                'location_dest_id': location_dest_id.id,
                'picking_type_id': picking_type.id,
                'picking_id': stock_picking.id,
            })
            stock_picking.sudo().action_confirm()
            stock_picking.sudo().action_set_quantities_to_reservation()
            stock_picking.sudo().button_validate()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("The transfer of finished product has been successfully created"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class WizardFinishedProductLine(models.TransientModel):
    _name = 'wizard.finished.product.line'
    _description = 'Wizard Finished Product Line'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_domain = fields.Many2one('product.product')
    location_id = fields.Many2one('stock.location', string='Location', required=True)
    location_domain = fields.Many2one('stock.location')
    quantity = fields.Float(string='Quantity')
    old_quantity = fields.Float(string='Current quantity in stock')
    product_uom_id = fields.Many2one('uom.uom', string='Unit', required=True)
    product_uom_domain = fields.Many2one('uom.uom')
    cp_finished_product_id = fields.Many2one('create.picking.finished.product', string='Create Picking Finished Product')

    @api.onchange('quantity')
    def _onchange_qty(self):
        for rec in self:
            if rec.quantity > rec.old_quantity:
                rec.quantity = rec.old_quantity
                raise UserError(_('The transfer quantity cannot be greater than the current stock quantity.'))
