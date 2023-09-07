# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


# Model used to calculate packs
class CalculatingPacks(models.TransientModel):
    _name = "calculating.packs"
    _description = "Calculating packs"

    @api.model
    def default_get(self, fields_list):
        res = super(CalculatingPacks, self).default_get(fields_list)
        group_list = []
        print(f"self.env.context : {self.env.context}")
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
                print('group_list :', group_list)
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

                print(f"total_packages_by_pack : {total_packages_by_pack}")
                if total_packages_by_pack:
                    line_values = []

                    for (product_id, pack), total_packages in total_packages_by_pack.items():
                        line_values.append(
                            (0, 0, {
                                'product_id': product_id,
                                'pack_of': f"{total_packages} packs of {pack}"
                            })
                        )

                    res['calculating_packs_line'] = line_values
        return res

    calculating_packs_line = fields.One2many('calculating.packs.line', inverse_name='calculating_packs_id',
                                             string='Calculating packs line')


class CalculatingPacksLine(models.TransientModel):
    _name = "calculating.packs.line"
    _description = "Calculating Packs Line"

    product_id = fields.Many2one('product.product', string='Product')
    pack_of = fields.Char('Package')
    calculating_packs_id = fields.Many2one('calculating.packs', string='Calculating packs')

