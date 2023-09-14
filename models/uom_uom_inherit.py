# -*- coding: utf-8 -*-

from odoo import api, fields, tools, models, _
from decimal import Decimal, ROUND_UP
from odoo.exceptions import UserError, ValidationError


class UomUomInherit(models.Model):
    _inherit = 'uom.uom'

    class UomUomInherit(models.Model):
        _inherit = 'uom.uom'

        def _compute_quantity(self, qty, to_unit, round=True, rounding_method='UP', raise_if_failure=True):
            if not self or not qty:
                return qty
            self.ensure_one()

            if self != to_unit and self.category_id.id != to_unit.category_id.id:
                if raise_if_failure:
                    raise UserError(
                        _('The unit of measure %s defined on the order line doesn\'t belong to the same category as the unit of measure %s defined on the product. Please correct the unit of measure defined on the order line or on the product, they should belong to the same category.') % (
                            self.name, to_unit.name))
                else:
                    return qty

            if self == to_unit:
                amount = Decimal(qty)
            else:
                amount = Decimal(qty) / Decimal(self.factor)
                if to_unit:
                    amount = amount * Decimal(to_unit.factor)

            if to_unit and round:
                amount = amount.quantize(Decimal(".00001"), rounding=ROUND_UP)
            print(f"float(amount) : {float(amount)}")
            return float(amount)
