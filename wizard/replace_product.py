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

    # @api.depends("product_to_replace", "line")
    # def _compute_product_to_replace_domain(self):
    # 	for rec in self:
    # 		if rec.planning_id:
    # 			product_ids = []
    # 			detail_lst = []
    # 			product_ids_final = []
    # 			end_line_id = self.env['mrp.detail.planning.line'].search([
    # 				('id', '>', rec.line.id),
    # 				('display_type', '=', 'line_note'),
    # 				('planning_id', '=', rec.planning_id.id)
    # 			], limit=1)
    # 			print(f'end_line_id : {end_line_id}')
    #
    # 			if end_line_id:
    # 				mrp_detail_line = self.env['mrp.detail.planning.line'].search([
    # 					('display_type', 'not in', ['line_section', 'line_note']),
    # 					('planning_id', '=', rec.planning_id.id),
    # 					('id', '>', rec.line.id),
    # 					('id', '<', end_line_id.id),
    # 				])
    # 				print(f'mrp_detail_line : {mrp_detail_line}')
    # 			else:
    # 				mrp_detail_line = self.env['mrp.detail.planning.line'].search([
    # 					('display_type', 'not in', ['line_section', 'line_note']),
    # 					('planning_id', '=', rec.planning_id.id),
    # 					('id', '>', rec.line.id),
    # 				])
    # 				print(f'mrp_detail_line : {mrp_detail_line}')
    #
    # 			for detail in mrp_detail_line:
    # 				detail_lst.append(detail.product_id.id)
    # 			details_lst = list(set(detail_lst))
    # 			print(f'details_lst : {details_lst}')
    #
    # 			production_ids = self.get_draft_production_orders()
    # 			for lines in production_ids:
    # 				product_ids.append(lines.product_id.id)
    # 			products_ids = list(set(product_ids))
    #
    # 			for elm in products_ids:
    # 				if elm in details_lst:
    # 					product_ids_final.append(elm)
    #
    # 			rec.product_to_replace_domain = list(set(product_ids_final))

    @api.depends("product_to_replace", 'line', 'planning_id', 'section')
    def _compute_replacement_days(self):
        for rec in self:
            if rec.planning_id:
                days = []
                production_ids = self.get_draft_production_order()
                # print(f'production_ids : {production_ids}')
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
                    # print(f'mrp_detail_line : {mrp_detail_line}')
                else:
                    mrp_detail_line = self.env['mrp.detail.planning.line'].search([
                        ('display_type', 'not in', ['line_section', 'line_note']),
                        ('planning_id', '=', rec.planning_id.id),
                        ('id', '>', rec.line.id),
                    ])
                    # print(f'mrp_detail_line : {mrp_detail_line}')
            else:
                mrp_detail_line = self.env['mrp.detail.planning.line'].search([
                    ('display_type', 'not in', ['line_section', 'line_note']),
                    ('planning_id', '=', rec.planning_id.id),
                ])
                # print(f'mrp_detail_line : {mrp_detail_line}')

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

            # mrp_list = []
            # for mrp in mrp_production:
            #     if mrp.detailed_pl_id.product_id.id == rec.product_to_replace.id:
            #         if end_section_id:
            #             print(f"{rec.section.id} < {mrp.detailed_pl_id.id} < {end_section_id.id}")
            #             if rec.section.id < mrp.detailed_pl_id.id < end_section_id.id:
            #                 mrp_list.append(mrp)
            #         else:
            #             print(f"{mrp.detailed_pl_id.id} > {rec.section.id}")
            #             if mrp.detailed_pl_id.id > rec.section.id:
            #                 mrp_list.append(mrp)

            return mrp_list

    def get_day_from_date(self, production_date):
        # iso = production_date.isocalendar()
        day = self.env['mrp.planning.days'].search([('date', '=', production_date)])
        return day.id

    # @api.depends('section', 'product_to_replace')
    # def _compute_line_to_replace_domain(self):
    #     for rec in self:
    #         # if not rec.section:
    #         # 	raise UserError(_("Please select the section before selecting the line."))
    #
    #         section_ids = self.env['mrp.detail.planning.line'].search(
    #             [('display_type', '=', 'line_section'), ('planning_id', '=', rec.planning_id.id)])
    #         # end_section_id = None
    #         # print(f"section_ids : {section_ids}")
    #         # print(f"rec.section : {rec.section}")
    #         # for section_id in section_ids:
    #         #     if section_id > rec.section:
    #         #         end_section_id = section_id
    #         #         # print(f'end_section_id : {end_section_id}')
    #         #         break
    #         end_section_id = self.env['mrp.detail.planning.line'].search([
    #             ('id', '>', rec.section.id),
    #             ('display_type', '=', 'line_section'),
    #             ('planning_id', '=', rec.planning_id.id)
    #         ], limit=1)
    #
    #         if end_section_id:
    #             print('if end_section_id')
    #             sect = []
    #             line_ids = self.get_planning_line()
    #             for line in line_ids:
    #                 if rec.section.id < line.id < end_section_id.id:
    #                     sect.append(line.id)
    #             mrp_detail = self.env['mrp.detail.planning.line'].search(
    #                 [('display_type', 'not in', ['line_section', 'line_note']),
    #                  ('planning_id', '=', rec.planning_id.id),
    #                  ('product_id', '=', rec.product_to_replace.id),
    #                  ('id', '>', rec.section.id),
    #                  ('id', '<', end_section_id.id),
    #             ])
    #         else:
    #             mrp_detail = self.env['mrp.detail.planning.line'].search(
    #                 [('display_type', 'not in', ['line_section', 'line_note']),
    #                  ('planning_id', '=', rec.planning_id.id),
    #                  ('product_id', '=', rec.product_to_replace.id),
    #                  ('id', '<', rec.section.id),
    #             ])
    #             print('else')
    #             sect = []
    #             line_ids = self.get_planning_line()
    #             if len(section_ids) == 1:
    #                 for line in line_ids:
    #                     if line.id > rec.section.id:
    #                         sect.append(line.id)
    #             else:
    #                 section = [sect.id for sect in section_ids]
    #                 # print(f"section : {section}")
    #                 position = section.index(rec.section.id)
    #                 for line in line_ids:
    #                     if section[position] != section[-1]:
    #                         if section[position] < line.id < section[position + 1]:
    #                             sect.append(line.id)
    #                     else:
    #                         if line.id > section[position]:
    #                             sect.append(line.id)
    #         line_lst = list(set(sect))
    #         print(f'line_lst : {line_lst}')
    #         # rec.line_domain = [(6, 0, line_lst)]
    #
    #         print(f'mrp_detail : {mrp_detail}')
    #         product = [prod.id for prod in mrp_detail if prod.state not in ['done']]
    #         print(f"product : {product}")
    #
    #         if len(line_lst) == 1:
    #             print(f"line_lst : {line_lst}")
    #             rec.line_domain = line_lst
    #         else:
    #             lst = []
    #             ls = sorted(line_lst)
    #             print(f"ls : {ls}")
    #             for i in range(len(ls) - 1):
    #                 for p in product:
    #                     if ls[i] < p < ls[i + 1]:
    #                         print(f"{ls[i]} < {p} < {ls[i + 1]}")
    #                         lst.append(ls[i])
    #                     if p > ls[-1]:
    #                         print(f"{p} > {ls[-1]}")
    #                         lst.append(ls[-1])
    #             print(f"list(set(lst)) : {list(set(lst))}")
    #             rec.line_domain = list(set(lst))

    @api.depends('section', 'product_to_replace')
    def _compute_line_domain(self):
        for rec in self:
            print(f"rec.section : {rec.section}")
            if rec.section:
                end_section_id = self.env['mrp.detail.planning.line'].search([
                    ('id', '>', rec.section.id),
                    ('display_type', '=', 'line_section'),
                    ('planning_id', '=', rec.planning_id.id)
                ], limit=1)

                if end_section_id:
                    print('if end_section_id')
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
                    print('else de if end_section_id')
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
                print(f'mrp_detail : {mrp_detail}')
                print(f'line_ids : {line_ids}')
                product = [prod.id for prod in mrp_detail if prod.state not in ['done']]
                print(f"product : {product}")
                line_lst = [line.id for line in line_ids]
                print(f"line_lst : {line_lst}")

                if len(line_lst) == 1:
                    rec.line_domain = line_lst
                else:
                    ls = sorted(line_lst)
                    print(f"ls : {ls}")
                    lst = []
                    for i in range(len(ls) - 1):
                        for p in product:
                            if ls[i] < p < ls[i + 1]:
                                print(f"{ls[i]} < {p} < {ls[i + 1]}")
                                lst.append(ls[i])
                            if p > ls[-1]:
                                print(f"{p} > {ls[-1]}")
                                lst.append(ls[-1])
                    print(f"list(set(lst)) : {list(set(lst))}")
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
        # print("_compute_line")
        for rec in self:
            # print(f'rec.packaging_line : {rec.packaging_line}')
            # print(f'rec.section : {rec.section}')
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
                # print(f"mrp_detail_lst : {mrp_detail_lst}")
                # print(f"line_ids : {line_ids}")
                line_lst = [line.id for line in line_ids]
                if len(line_lst) == 1:
                    rec.line = line_lst
                    # print(f"rec.line de line_lst : {rec.line}")
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
                    # print(f"lst2 : {lst2}")
                    rec.line = self.env['mrp.detail.planning.line'].search([
                        ('id', '=', lst2)
                    ])
                    # print(f'lines : {lines}')
                    # rec.line = lines.id
                    print(f"rec.line de lst2 : {rec.line}")

            else:
                rec.line = False


    @api.depends('product_to_replace')
    def _compute_section_to_replace_domain(self):
        for rec in self:
            section_ids = self.env['mrp.detail.planning.line'].search(
                [('display_type', '=', 'line_section'), ('planning_id', '=', rec.planning_id.id)])
            # print(f'section_ids : {section_ids}')
            mrp_detail = self.env['mrp.detail.planning.line'].search(
                [('display_type', 'not in', ['line_section', 'line_note']),
                 ('planning_id', '=', rec.planning_id.id),
                 ('product_id', '=', rec.product_to_replace.id),
            ])
            # print(f'mrp_detail : {mrp_detail}')

            product = [prod.id for prod in mrp_detail if prod.state not in ['done']]
            # print(f"product : {product}")
            section = [sect.id for sect in section_ids]
            # print(f"section : {section}")

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
                # print(f"sect_lst : {sect_lst}")
                rec.section_domain = list(set(sect_lst))

    def get_planning_line(self):
        return self.env['mrp.detail.planning.line'].search(
            [('display_type', '=', 'line_note'), ('planning_id', '=', self.planning_id.id)])

    @api.depends("product_to_replace", 'line', 'planning_id', 'section')
    def _compute_packaging_line(self):
        for rec in self:
            # print('yes')
            # print(f'rec.line : {rec.line}')
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
    replacement_days = fields.Many2many("mrp.planning.days", string=_("Replacement days"), required=True)
    line = fields.Many2one('mrp.detail.planning.line', string=_('Line to replace'), compute="_compute_line")
    line_domain = fields.Many2many('mrp.detail.planning.line', compute="_compute_line_domain")
    # line_domain = fields.Many2many('mrp.detail.planning.line', compute="_compute_line_to_replace_domain")
    packaging_line = fields.Many2one('mrp.packaging.line', required=True, string=_('Packaging Line'))
    packaging_line_domain = fields.Many2many('mrp.packaging.line', compute="_compute_packaging_line_domain")
    section = fields.Many2one('mrp.detail.planning.line', string=_('Section to replace'), required=True)
    section_domain = fields.Many2many('mrp.detail.planning.line', compute="_compute_section_to_replace_domain")

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
                    # print(f'mrp_detail_line : {mrp_detail_line}')
                else:
                    mrp_detail_line = self.env['mrp.detail.planning.line'].search([
                        ('display_type', 'not in', ['line_section', 'line_note']),
                        ('planning_id', '=', rec.planning_id.id),
                        ('id', '>', rec.line.id),
                    ])
                    # print(f'mrp_detail_line : {mrp_detail_line}')
            else:
                mrp_detail_line = self.env['mrp.detail.planning.line'].search([
                    ('display_type', 'not in', ['line_section', 'line_note']),
                    ('planning_id', '=', rec.planning_id.id),
                ])
                # print(f'mrp_detail_line : {mrp_detail_line}')

            mrp_detail_lst = [mrp.id for mrp in mrp_detail_line]
            mrp_production = self.env['mrp.production'].sudo().search([
                ('planning_id', '=', rec.planning_id.id),
                ('detailed_pl_id', 'in', mrp_detail_lst),
                ('state', 'not in', ['done', 'cancel'])
            ])
            mrp_list = [mrp for mrp in mrp_production.detailed_pl_id if any(
                day in mrp.date_char and mrp.product_id.id == rec.product_to_replace.id for day in day_list)]
            production_list = [mrp for mrp in mrp_production if mrp.detailed_pl_id in mrp_list]
            # print(f'production_list : {production_list}')

            if production_list:
                for production in production_list:
                    if production.state not in ['done', 'cancel']:
                        for line in production.detailed_pl_id:
                            if any(day in line.date_char for day in day_list):
                                line.product_id = rec.replacement_product.id

                        bom_id = self.env["mrp.bom"].search(
                            [('product_tmpl_id', '=', rec.replacement_product.product_tmpl_id.id)])
                        if bom_id:
                            old_qty = production.product_qty
                            old_move_raw_ids = production.move_raw_ids
                            production.bom_id = bom_id
                            production.product_id = rec.replacement_product.id
                            production.product_qty = old_qty
                            for move in production.move_raw_ids:
                                for old_move in old_move_raw_ids:
                                    if move == old_move:
                                        # print(f"move.state replace product : {move.state}")
                                        if move.state in ['draft', 'cancel']:
                                            move.unlink()
                        else:
                            raise UserError(
                                _("You can't select this product as a replacement because it doesn't have a bill of materials"))
            else:
                raise UserError(_("There are no manufacturing orders for this product for these days."))

            # post message at chatter
            message = f"<p><b> <em> (Detailed planning lines)</em> {rec.product_to_replace.name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{rec.replacement_product.name}</span> for section {rec.section.name}, line {rec.packaging_line.name} and days : </b></p><ul>"
            msg = ""
            for day in rec.replacement_days:
                msg += f"<li><p><b>{day.name}</b></p></li>"
            message += msg
            rec.planning_id.message_post(body=message)
