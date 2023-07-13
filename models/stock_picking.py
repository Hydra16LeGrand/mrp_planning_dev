from odoo import fields, models, api


class StockPickingInherit(models.Model):
  _inherit = "stock.picking"

  planning_id = fields.Many2one('mrp.planning', string="Planning")