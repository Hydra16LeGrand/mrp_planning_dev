# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class MrpImmediateProductionLineInherit(models.TransientModel):
    _inherit = 'mrp.immediate.production.line'

    date_planned_start = fields.Date(_("Date"))
    section_id = fields.Many2one("mrp.section", string=_("Section"))
    packaging_line_id = fields.Many2one("mrp.packaging.line", string=_("Packaging Line"))
    product_id = fields.Many2one('product.product', 'Product')
    qty = fields.Integer(_("Quantity"))


class MrpImmediateProductionInherit(models.TransientModel):
    _inherit = 'mrp.immediate.production'

    @api.model
    def default_get(self, fields):
        # res = super().default_get(fields)
        print(f'self.env.context : {self.env.context}')
        res = super().default_get(fields)
        if 'immediate_production_line_ids' in fields:
            if self.env.context.get('default_mo_ids'):
                res['mo_ids'] = self.env.context['default_mo_ids']
                res['immediate_production_line_ids'] = [(0, 0, {
                    'to_immediate': True,
                    'production_id': mo_id[1],
                    'date_planned_start': self.env['mrp.production'].browse(mo_id[1]).date_planned_start,
                    'section_id': self.env['mrp.production'].browse(mo_id[1]).section_id,
                    'packaging_line_id': self.env['mrp.production'].browse(mo_id[1]).packaging_line_id,
                    'product_id': self.env['mrp.production'].browse(mo_id[1]).product_id,
                    'qty': self.env['mrp.production'].browse(mo_id[1]).product_qty,
                }) for mo_id in res['mo_ids']]
        return res