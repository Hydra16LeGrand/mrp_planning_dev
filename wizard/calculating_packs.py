# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


# Model used to calculate packs
class CalculatingPack(models.TransientModel):
    _name = "calculating.pack"
    _description = "Calculating packs"

    @api.model
    def default_get(self, fields_list):
        res = super(CalculatingPack, self).default_get(fields_list)

        group_list = []
        if self.env.context.get('quant_line'):
            quant_line = self.env.context.get('quant_line')
            for elm in quant_line:
                quant = self.env['stock.quant'].browse(elm)
                if not quant.package or not quant.pack:
                    continue
                group_list.append(
                    {
                        'product_id': quant.product_id.id,
                        'package': quant.package,
                        'pack': quant.pack,
                    }
                )

            if group_list:
                total_packages_by_pack = {}
                for rec in group_list:
                    product = rec['product_id']
                    pack = rec['pack']
                    package = rec['package']

                    product_key = (product, pack)  # Utiliser une clé composée de l'ID du produit et du pack pour identifier le produit

                    if product_key in total_packages_by_pack:
                        total_packages_by_pack[product_key] += package
                    else:
                        total_packages_by_pack[product_key] = package

                if total_packages_by_pack:
                    line_values = []

                    for (product_id, pack), total_packages in total_packages_by_pack.items():
                        line_values.append(
                            (0, 0, {
                                'product_id': product_id,
                                'pack_of': f"{total_packages} packs of {pack}"
                            })
                        )

                    res['cal_packs_line_ids'] = line_values
        return res

    cal_packs_line_ids = fields.One2many('calculating.pack.line', inverse_name='calculating_packs_id',
                                             string='Calculating packs line')


class CalculatingPackLine(models.TransientModel):
    _name = "calculating.pack.line"
    _description = "Calculating Packs Line"

    product_id = fields.Many2one('product.product', string='Product')
    pack_of = fields.Char('Package')
    calculating_packs_id = fields.Many2one('calculating.pack', string='Calculating packs')

