from odoo import fields, models, api, _
from odoo.exceptions import UserError


# Model use for replacement of a product in a manufacturing order by a planning
class ReplaceProduct(models.TransientModel):
    _name = "replace.product"
    _description = "Replace product in a planning"

    @api.depends("product_to_replace")
    def _compute_product_to_replace_domain(self):
        for rec in self:
            if rec.planning_id:
                product_ids = []
                production_ids = self.get_draft_production_orders()
                for lines in production_ids:
                    product_ids.append(lines.product_id.id)
                rec.product_to_replace_domain = list(set(product_ids))

    @api.depends("product_to_replace", 'line', 'planning_id', 'section')
    def _compute_replacement_days(self):
        for rec in self:
            if rec.planning_id:
                days = []
                production_ids = self.get_draft_production_order()
                for production in production_ids:
                    days.append(rec.get_day_from_date(production.date_planned_start.date()))
                rec.replacement_days_domain = list(set(days))
            else:
                rec.replacement_days_domain = []

    def get_draft_production_orders(self):
        return self.planning_id.mrp_production_ids.filtered(lambda self: self.state not in ['done', 'cancel'])

    @api.depends('product_to_replace', 'line', 'planning_id', 'section')
    def get_draft_production_order(self):
        for rec in self:
            if rec.line:
                end_line_id = self.env['mrp.detail.planning.line'].search([
                    ('id', '>', rec.line.id),
                    ('display_type', '=', 'line_note'),
                    ('planning_id', '=', rec.planning_id.id)
                ], limit=1)
                if end_line_id:
                    mrp_detail_line = self.env['mrp.detail.planning.line'].search([
                        ('display_type', 'not in', ['line_section', 'line_note']),
                        ('planning_id', '=', rec.planning_id.id),
                        ('id', '>', rec.line.id),
                        ('id', '<', end_line_id.id),
                    ])
                else:
                    mrp_detail_line = self.env['mrp.detail.planning.line'].search([
                        ('display_type', 'not in', ['line_section', 'line_note']),
                        ('planning_id', '=', rec.planning_id.id),
                        ('id', '>', rec.line.id),
                    ])
            else:
                mrp_detail_line = self.env['mrp.detail.planning.line'].search([
                    ('display_type', 'not in', ['line_section', 'line_note']),
                    ('planning_id', '=', rec.planning_id.id),
                ])

            mrp_detail_lst = [mrp.id for mrp in mrp_detail_line]
            mrp_production = self.env['mrp.production'].sudo().search([
                ('planning_id', '=', rec.planning_id.id),
                ('detailed_pl_id', 'in', mrp_detail_lst),
                ('state', 'not in', ['done', 'cancel'])
            ])
            # mrp_list = [mrp for mrp in mrp_production if mrp.detailed_pl_id.product_id.id == rec.product_to_replace.id]
            end_section_id = self.env['mrp.detail.planning.line'].search([
                ('id', '>', rec.section.id),
                ('display_type', '=', 'line_section'),
                ('planning_id', '=', rec.planning_id.id)
            ], limit=1)


            mrp_list = [
                mrp for mrp in mrp_production
                if mrp.detailed_pl_id.product_id.id == rec.product_to_replace.id and (
                        (end_section_id and rec.section.id < mrp.detailed_pl_id.id < end_section_id.id) or
                        (not end_section_id and mrp.detailed_pl_id.id > rec.section.id)
                )
            ]

            return mrp_list

    def get_day_from_date(self, production_date):
        # iso = production_date.isocalendar()
        day = self.env['mrp.planning.days'].search([('date', '=', production_date)])
        return day.id


    @api.depends('section', 'product_to_replace')
    def _compute_line_domain(self):
        for rec in self:
            if rec.section:
                end_section_id = self.env['mrp.detail.planning.line'].search([
                    ('id', '>', rec.section.id),
                    ('display_type', '=', 'line_section'),
                    ('planning_id', '=', rec.planning_id.id)
                ], limit=1)

                if end_section_id:
                    mrp_detail = self.env['mrp.detail.planning.line'].search(
                        [('display_type', 'not in', ['line_section', 'line_note']),
                         ('planning_id', '=', rec.planning_id.id),
                         ('product_id', '=', rec.product_to_replace.id),
                         ('id', '>', rec.section.id),
                         ('id', '<', end_section_id.id),
                    ])
                    line_ids = self.env['mrp.detail.planning.line'].search(
                        [('display_type', '=', 'line_note'),
                         ('planning_id', '=', rec.planning_id.id),
                         ('id', '>', rec.section.id),
                         ('id', '<', end_section_id.id),
                    ])
                else:
                    mrp_detail = self.env['mrp.detail.planning.line'].search(
                        [('display_type', 'not in', ['line_section', 'line_note']),
                         ('planning_id', '=', rec.planning_id.id),
                         ('product_id', '=', rec.product_to_replace.id),
                         ('id', '>', rec.section.id),
                    ])
                    line_ids = self.env['mrp.detail.planning.line'].search(
                        [('display_type', '=', 'line_note'),
                         ('planning_id', '=', rec.planning_id.id),
                         ('id', '>', rec.section.id),
                    ])
                product = [prod.id for prod in mrp_detail if prod.state not in ['done']]
                line_lst = [line.id for line in line_ids]

                if len(line_lst) == 1:
                    rec.line_domain = line_lst
                else:
                    ls = sorted(line_lst)
                    lst = []
                    for i in range(len(ls) - 1):
                        for p in product:
                            if ls[i] < p < ls[i + 1]:
                                lst.append(ls[i])
                            if p > ls[-1]:
                                lst.append(ls[-1])
                    rec.line_domain = list(set(lst))
            else:
                rec.line_domain = False

    @api.depends('line_domain')
    def _compute_packaging_line_domain(self):
        for rec in self:
            if rec.line_domain:
                pack_lst = [line.packaging_line_id.id for line in rec.line_domain]
                rec.packaging_line_domain = list(set(pack_lst))
            else:
                rec.packaging_line_domain = False

    @api.depends('section', 'packaging_line', 'product_to_replace')
    def _compute_line(self):
        for rec in self:
            if rec.packaging_line:
                end_section_id = self.env['mrp.detail.planning.line'].search([
                    ('id', '>', rec.section.id),
                    ('display_type', '=', 'line_section'),
                    ('planning_id', '=', rec.planning_id.id)
                ], limit=1)
                line_ids = self.get_planning_line()
                if end_section_id:
                    mrp_detail = self.env['mrp.detail.planning.line'].search([
                        ('planning_id', '=', rec.planning_id.id),
                        ('display_type', 'not in', ['line_section', 'line_note']),
                        ('packaging_line_id', '=', rec.packaging_line.id),
                        ('product_id', '=', rec.product_to_replace.id),
                        ('id', '>', rec.section.id),
                        ('id', '<', end_section_id.id),
                    ])
                else:
                    mrp_detail = self.env['mrp.detail.planning.line'].search([
                        ('planning_id', '=', rec.planning_id.id),
                        ('display_type', 'not in', ['line_section', 'line_note']),
                        ('packaging_line_id', '=', rec.packaging_line.id),
                        ('product_id', '=', rec.product_to_replace.id),
                        ('id', '>', rec.section.id),
                    ])
                mrp_detail_lst = [mrp.id for mrp in mrp_detail if mrp.state not in ['done', 'cancel']]
                line_lst = [line.id for line in line_ids]
                if len(line_lst) == 1:
                    rec.line = line_lst
                else:
                    lst = []
                    ls = sorted(line_lst)
                    for i in range(len(ls) - 1):
                        for p in mrp_detail_lst:
                            if ls[i] < p < ls[i + 1]:
                                lst.append(ls[i])
                            if p > ls[-1]:
                                lst.append(ls[-1])
                    lst2 = list(set(lst))
                    rec.line = self.env['mrp.detail.planning.line'].search([
                        ('id', '=', lst2)
                    ])

            else:
                rec.line = False


    @api.depends('product_to_replace')
    def _compute_section_to_replace_domain(self):
        for rec in self:
            section_ids = self.env['mrp.detail.planning.line'].search(
                [('display_type', '=', 'line_section'), ('planning_id', '=', rec.planning_id.id)])
            mrp_detail = self.env['mrp.detail.planning.line'].search(
                [('display_type', 'not in', ['line_section', 'line_note']),
                 ('planning_id', '=', rec.planning_id.id),
                 ('product_id', '=', rec.product_to_replace.id),
            ])

            product = [prod.id for prod in mrp_detail if prod.state not in ['done']]
            section = [sect.id for sect in section_ids]

            if len(section) == 1:
                rec.section_domain = section
            else:
                sect_lst = []
                for i in range(len(section) - 1):
                    for p in product:
                        if section[i] < p < section[i + 1]:
                            sect_lst.append(section[i])
                        if p > section[-1]:
                            sect_lst.append(section[-1])
                rec.section_domain = list(set(sect_lst))

    def get_planning_line(self):
        return self.env['mrp.detail.planning.line'].search(
            [('display_type', '=', 'line_note'), ('planning_id', '=', self.planning_id.id)])

    @api.depends("product_to_replace", 'line', 'planning_id', 'section')
    def _compute_packaging_line(self):
        for rec in self:
            if rec.line and rec.line.packaging_line_id:
                rec.packaging_line = rec.line.packaging_line_id
            else:
                rec.packaging_line = False

    @api.onchange('product_to_replace')
    def _onchange_product_to_replace(self):
        for rec in self:
            rec.replacement_product = False
            rec.section = False

    @api.onchange('section')
    def _onchange_section(self):
        for rec in self:
            rec.packaging_line = False

    @api.onchange('packaging_line')
    def _onchange_line(self):
        for rec in self:
            rec.replacement_days = False


    product_to_replace = fields.Many2one("product.product", string=_("Product to replace"), required=True)
    product_to_replace_domain = fields.Many2many("product.product", compute="_compute_product_to_replace_domain")
    replacement_product = fields.Many2one("product.product", string=_("Replacement product"), required=True)
    replacement_days_domain = fields.Many2many("mrp.planning.days", compute="_compute_replacement_days")
    replacement_days = fields.Many2many("mrp.planning.days", string=_("Replacement days"))
    line = fields.Many2one('mrp.detail.planning.line', string=_('Line to replace'), compute="_compute_line")
    line_domain = fields.Many2many('mrp.detail.planning.line', compute="_compute_line_domain")
    # line_domain = fields.Many2many('mrp.detail.planning.line', compute="_compute_line_to_replace_domain")
    packaging_line = fields.Many2one('mrp.packaging.line', string=_('Packaging Line'))
    packaging_line_domain = fields.Many2many('mrp.packaging.line', compute="_compute_packaging_line_domain")
    section = fields.Many2one('mrp.detail.planning.line', string=_('Section to replace'), required=True)
    section_domain = fields.Many2many('mrp.detail.planning.line', compute="_compute_section_to_replace_domain")
    qty = fields.Integer(string=_("Quantity"))

    planning_id = fields.Many2one("mrp.planning", string=_("Planning"))

    def action_replace_product(self):
        for rec in self:
            day_list = [day.name for day in rec.replacement_days]
            if rec.line:
                end_line_id = self.env['mrp.detail.planning.line'].search([
                    ('id', '>', rec.line.id),
                    ('display_type', '=', 'line_note'),
                    ('planning_id', '=', rec.planning_id.id)
                ], limit=1)
                if end_line_id:
                    mrp_detail_line = self.env['mrp.detail.planning.line'].search([
                        ('display_type', 'not in', ['line_section', 'line_note']),
                        ('planning_id', '=', rec.planning_id.id),
                        ('id', '>', rec.line.id),
                        ('id', '<', end_line_id.id),
                    ])
                else:
                    mrp_detail_line = self.env['mrp.detail.planning.line'].search([
                        ('display_type', 'not in', ['line_section', 'line_note']),
                        ('planning_id', '=', rec.planning_id.id),
                        ('id', '>', rec.line.id),
                    ])

                mrp_detail_lst = [mrp.id for mrp in mrp_detail_line]
                mrp_production = self.env['mrp.production'].sudo().search([
                    ('planning_id', '=', rec.planning_id.id),
                    ('detailed_pl_id', 'in', mrp_detail_lst),
                    ('state', 'not in', ['done', 'cancel'])
                ])
                mrp_list = [mrp for mrp in mrp_production.detailed_pl_id if any(
                    day in mrp.date_char and mrp.product_id.id == rec.product_to_replace.id for day in day_list)]
                production_list = [mrp for mrp in mrp_production if mrp.detailed_pl_id in mrp_list]

                if production_list:
                    for production in production_list:
                        if production.state not in ['done', 'cancel']:
                            for line in production.detailed_pl_id:
                                if any(day in line.date_char for day in day_list):
                                    line.product_id = rec.replacement_product.id
                                    if rec.qty:
                                        line.qty = rec.qty

                            bom_id = self.env["mrp.bom"].search(
                                [('product_tmpl_id', '=', rec.replacement_product.product_tmpl_id.id)])
                            if bom_id:
                                old_qty = production.product_qty
                                old_move_raw_ids = production.move_raw_ids
                                production.bom_id = bom_id
                                production.product_id = rec.replacement_product.id
                                if rec.qty:
                                    production.product_qty = rec.qty
                                else:
                                    production.product_qty = old_qty
                                for move in production.move_raw_ids:
                                    for old_move in old_move_raw_ids:
                                        if move == old_move:
                                            if move.state in ['draft', 'cancel']:
                                                move.unlink()
                            else:
                                raise UserError(
                                    _("You can't select this product as a replacement because it doesn't have a bill of materials"))
                else:
                    raise UserError(_("There are no manufacturing orders for this product for these days."))

                # post message at chatter
                if rec.qty:
                    message = f"<p><b> <em> (Detailed planning lines)</em> {rec.product_to_replace.name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{rec.replacement_product.name}</span> for section {rec.section.name}, line {rec.packaging_line.name} and days : </b></p><ul>"
                    msg = ""
                    for day in rec.replacement_days:
                        msg += f"<li><p><b>{day.name}</b></p></li>"
                    message += msg
                    message += f"<li><p><b>new quantity <span style='color: #0182b6;'>{rec.qty}</span></b></p></li>"
                    rec.planning_id.message_post(body=message)
                else:
                    message = f"<p><b> <em> (Detailed planning lines)</em> {rec.product_to_replace.name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{rec.replacement_product.name}</span> for section {rec.section.name}, line {rec.packaging_line.name} and days : </b></p><ul>"
                    msg = ""
                    for day in rec.replacement_days:
                        msg += f"<li><p><b>{day.name}</b></p></li>"
                    message += msg
                    rec.planning_id.message_post(body=message)
            else:
                end_section_id = self.env['mrp.detail.planning.line'].search([
                    ('id', '>', rec.section.id),
                    ('display_type', '=', 'line_section'),
                    ('planning_id', '=', rec.planning_id.id)
                ], limit=1)

                if end_section_id:
                    mrp_detail_lines = self.env['mrp.detail.planning.line'].search([
                        ('display_type', 'not in', ['line_section', 'line_note']),
                        ('planning_id', '=', rec.planning_id.id),
                        ('id', '>', rec.section.id),
                        ('id', '<', end_section_id.id),
                    ])
                else:
                    mrp_detail_lines = self.env['mrp.detail.planning.line'].search([
                        ('display_type', 'not in', ['line_section', 'line_note']),
                        ('planning_id', '=', rec.planning_id.id),
                        ('id', '>', rec.section.id),
                    ])
                mrp_detail_lst = [mrp.id for mrp in mrp_detail_lines]
                mrp_production = self.env['mrp.production'].sudo().search([
                    ('planning_id', '=', rec.planning_id.id),
                    ('detailed_pl_id', 'in', mrp_detail_lst),
                    ('state', 'not in', ['done', 'cancel'])
                ])
                mrp_list = [mrp for mrp in mrp_production.detailed_pl_id if mrp.product_id.id == rec.product_to_replace.id]
                production_list = [mrp for mrp in mrp_production if mrp.detailed_pl_id in mrp_list]
                if production_list:
                    for production in production_list:
                        if production.state not in ['done', 'cancel']:
                            for line in production.detailed_pl_id:
                                line.product_id = rec.replacement_product.id
                                if rec.qty:
                                    line.qty = rec.qty

                            bom_id = self.env["mrp.bom"].search(
                                [('product_tmpl_id', '=', rec.replacement_product.product_tmpl_id.id)])
                            if bom_id:
                                old_qty = production.product_qty
                                old_move_raw_ids = production.move_raw_ids
                                production.bom_id = bom_id
                                production.product_id = rec.replacement_product.id
                                if rec.qty:
                                    production.product_qty = rec.qty
                                else:
                                    production.product_qty = old_qty
                                for move in production.move_raw_ids:
                                    for old_move in old_move_raw_ids:
                                        if move == old_move:
                                            if move.state in ['draft', 'cancel']:
                                                move.unlink()
                            else:
                                raise UserError(
                                    _("You can't select this product as a replacement because it doesn't have a bill of materials"))
                else:
                    raise UserError(_("There are no manufacturing orders for this product"))

                # post message at chatter
                if not rec.qty:
                    message = f"<p><b> <em> (Detailed planning lines)</em> {rec.product_to_replace.name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{rec.replacement_product.name}</span> for section {rec.section.name}</b></p><ul>"
                    rec.planning_id.message_post(body=message)
                else:
                    message = f"<p><b> <em> (Detailed planning lines)</em> {rec.product_to_replace.name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{rec.replacement_product.name}</span> for section {rec.section.name} with new quantity <span style='color: #0182b6;'>{rec.qty}</span></b></p><ul>"
                    rec.planning_id.message_post(body=message)

