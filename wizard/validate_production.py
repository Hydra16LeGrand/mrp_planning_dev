# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ValidateProduction(models.TransientModel):
    _name = 'validate.production'
    _description = "Validate Production"

    @api.model
    def default_get(self, fields_list):
        res = super(ValidateProduction, self).default_get(fields_list)
        group_lst = []
        print(f"self.env.context : {self.env.context}")
        if self.env.context.get('dpl'):
            for elm in self.env.context.get('dpl'):
                dpl = self.env['mrp.detail.planning.line'].browse(elm)
                val = {
                    'product_id': dpl.product_id.id,
                    'packaging_line_id': dpl.packaging_line_id.id,
                    'qty': dpl.qty,
                    'qty_done': dpl.qty_done,
                    'date': dpl.date,
                    'production_id': dpl.mrp_production_id,
                }
                group_lst.append((0, 0, val))
            res['validate_production_line_ids'] = group_lst
        return res

    validate_production_line_ids = fields.One2many('validate.production.line', inverse_name='validate_production_id',
                                                   string="Validate Production Line")
    # count_to_be_processed = fields.Integer(compute='_compute_count_to_be_processed')
    #
    # def _compute_count_to_be_processed(self):
    #     if self.validate_production_line_ids:
    #         count = 0
    #         for rec in self:
    #             for line in rec.validate_production_line_ids:
    #                 if line.to_be_processed:
    #                     count += 1
    #
    #             rec.count_to_be_processed = count

    def validate(self):
        for rec in self.validate_production_line_ids:
            if rec.to_be_processed:
                rec.production_id.action_assign()
                print("Assignation ----", rec.production_id.reservation_state)
                if rec.qty == rec.qty_done:
                    if rec.production_id.reservation_state == 'assigned':
                        for move in rec.production_id.move_raw_ids:
                            move.quantity_done = move.should_consume_qty
                        rec.production_id.button_mark_done()
                    else:
                        print("Le else")
                        raise UserError(_('Unavailability of components, please create supply orders'))
                elif rec.qty_done < rec.qty:
                    if rec.production_id.reservation_state == 'assigned':
                        for move in rec.production_id.move_raw_ids:
                            move.quantity_done = move.should_consume_qty
                        # rec.production_id.with_context(default_mrp_production_ids=None, skip_consumption=True).button_mark_done()
                        rec.production_id.with_context(skip_backorder=True).button_mark_done()
                    else:
                        raise UserError(_('Unavailability of components, please create supply orders'))


class ValidateProductionLine(models.TransientModel):
    _name = 'validate.production.line'
    _description = 'Validate Production Line'

    product_id = fields.Many2one('product.product', 'Product')
    packaging_line_id = fields.Many2one("mrp.packaging.line", string=_("Packaging Line"))
    qty = fields.Integer(_("Quantity"))
    qty_done = fields.Integer(_("Quantity done"))
    date = fields.Date(_("Date"))
    production_id = fields.Many2one("mrp.production", "Production")
    to_be_processed = fields.Boolean(default=True)
    validate_production_id = fields.Many2one('validate.production')
