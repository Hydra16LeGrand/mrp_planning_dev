from odoo import fields, models, api, _
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict


class MrpPlanning(models.Model):
    _name = "mrp.planning"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "reference"
    _order = "begin_date desc"

    # today_date = fields.Date.today()
    # iso = today_date.isocalendar()
    #
    # monday = date.fromisocalendar(year=iso[0], week=iso[1], day=1)
    # tuesday = date.fromisocalendar(year=iso[0], week=iso[1], day=2)
    # wednesday = date.fromisocalendar(year=iso[0], week=iso[1], day=3)
    # thursday = date.fromisocalendar(year=iso[0], week=iso[1], day=4)
    # friday = date.fromisocalendar(year=iso[0], week=iso[1], day=5)
    #
    # # Global variable for date format (Eg: monday 14/08)
    # week_days = [
    #     'monday {}/{}'.format(monday.strftime('%d'), monday.month),
    #     'tuesday {}/{}'.format(tuesday.strftime('%d'), tuesday.month),
    #     'wednesday {}/{}'.format(wednesday.strftime('%d'), wednesday.month),
    #     'thursday {}/{}'.format(thursday.strftime('%d'), thursday.month),
    #     'friday {}/{}'.format(friday.strftime('%d'), friday.month),
    # ]
    #
    # def _get_default_week_of(self):
    #     iso = self.today_date.isocalendar()
    #     monday = date.fromisocalendar(year=iso[0], week=iso[1], day=1)
    #     tuesday = date.fromisocalendar(year=iso[0], week=iso[1], day=2)
    #     wednesday = date.fromisocalendar(year=iso[0], week=iso[1], day=3)
    #     thursday = date.fromisocalendar(year=iso[0], week=iso[1], day=4)
    #     friday = date.fromisocalendar(year=iso[0], week=iso[1], day=5)
    #
    #     current_week_days = [
    #         (0, 0, {'name': 'monday {}/{}'.format(monday.strftime('%d'), monday.month), 'date': monday}),
    #         (0, 0, {'name': 'tuesday {}/{}'.format(tuesday.strftime('%d'), tuesday.month), 'date': tuesday}),
    #         (0, 0, {'name': 'wednesday {}/{}'.format(wednesday.strftime('%d'), wednesday.month), 'date': wednesday}),
    #         (0, 0, {'name': 'thursday {}/{}'.format(thursday.strftime('%d'), thursday.month), 'date': thursday}),
    #         (0, 0, {'name': 'friday {}/{}'.format(friday.strftime('%d'), friday.month), 'date': friday}),
    #     ]
    #
    #     week_of_records = []
    #     for day in current_week_days:
    #         day_record = self.env['mrp.planning.days'].search(
    #             [('name', '=', day[2]['name']), ('date', '=', day[2]['date'])], limit=1)
    #         if not day_record:
    #             day_record = self.env['mrp.planning.days'].create(day[2])
    #         week_of_records.append((4, day_record.id, 0))
    #
    #     return week_of_records

    def _compute_internal_transfer_count(self):
        for rec in self:
            rec.internal_transfer_count = len(self.picking_ids)

    @api.onchange('product_id')
    def _get_default_plant(self):
        plant_id = self.env['mrp.plant'].search([('is_principal', '=', True)])
        return plant_id.id if plant_id else False

    reference = fields.Char(_("Reference"), default=lambda self: _('New'), tracking=True)
    code = fields.Char(_("Code"), default=lambda self: self.env['ir.config_parameter'].sudo().get_param('mrp_planning.code'), tracking=True)
    state = fields.Selection([
        ('cancel', "Cancelled"),
        ('draft', "Draft"),
        ('confirm', "Confirmed"),
        ('04_mo_generated', "Mo generate"),
    ], default="draft", index=True, readonly=True, copy=False, tracking=True
    )
    # scheduled_date = fields.Date(_("Add a date"), default=lambda self: fields.Date.today(), required=True)
    #
    # week_of = fields.Many2many('mrp.planning.days', string='Scheduled dates', default=_get_default_week_of,
    #                            domain=lambda self: [('name', 'in', self.week_days)], copy=True)

    begin_date = fields.Date(_('Begin Date'), copy=True, tracking=True)
    end_date = fields.Date(_('End Date'), copy=True, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
                                 default=lambda self: self.env.company.id)
    section_ids = fields.Many2one("mrp.section", string=_("Sections"), required=True, tracking=5)

    # team_ids = fields.Many2many("mrp.team", string=_("Teams"), tracking=True, required=True)

    planning_line_ids = fields.One2many("mrp.planning.line", "planning_id", string=_("Planning lines"), tracking=5)
    detailed_pl_ids = fields.One2many("mrp.detail.planning.line", "planning_id", string=_("Detailed planning lines"),
                                      tracking=4)
    mrp_production_ids = fields.One2many("mrp.production", "planning_id", string=_("Mrp orders"), copy=False,
                                         tracking=4)
    picking_ids = fields.One2many('stock.picking', 'planning_id', string='Planning MRP', tracking=True)
    internal_transfer_count = fields.Integer(string=_("Supply count"),
                                             compute='_compute_internal_transfer_count')
    plant_id = fields.Many2one("mrp.plant", string=_("Plant"), default=_get_default_plant, tracking=2)
    section_first = fields.Many2one('mrp.section', compute='_compute_section_first')
    detailed_pl_done_state = fields.Boolean(copy=False, compute='_compute_detailed_pl_done_state')

    # @api.depends('section_ids')
    # def _compute_section_first(self):
    #     for rec in self:
    #         if rec.section_ids:
    #
    #             ls = [sect.id for sect in rec.section_ids]
    #             ls = [sect.id for sect in rec.section_ids]
    #             rec.section_first = ls[0]
    #         else:
    #             rec.section_first = False

    @api.depends('section_ids')
    def _compute_section_first(self):
        for rec in self:
            if rec.section_ids:
                rec.section_first = rec.section_ids.id
            else:
                rec.section_first = False

    @api.depends('detailed_pl_ids.state')
    def _compute_detailed_pl_done_state(self):
        for rec in self:
            rec.detailed_pl_done_state = False  # Initialisez d'abord à False
            if rec.detailed_pl_ids:
                mrp_detail_states = [detail.state for detail in rec.detailed_pl_ids if
                                     detail.display_type == False]

                mrp_state = list(set(mrp_detail_states))
                if len(mrp_state) == 1 and mrp_state[0] == 'done':
                    rec.detailed_pl_done_state = True
                    message = (f"<p><b><em> (Detailed planning lines)</em> State :</b></p><ul>"
                               f"<li><p><b> Confirmed <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Done</span></b></p></li>")
                    planning = self.env['mrp.planning'].browse(self.id)
                    planning.message_post(body=message)

        # self.env.cr.commit()

    @api.model
    def create(self, vals):

        seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(fields.Datetime.now()))
        vals['reference'] = self.env['ir.sequence'].next_by_code("mrp.planning", sequence_date=seq_date) or _("New")

        res = super().create(vals)

        return res

    # def create_detail_planning_line(self, element):
    #     ppp_id = self.env['mrp.packaging.pp'].search(
    #         [('packaging_line_id', '=', element['packaging_line_id'].id),
    #          ('product_id', '=', element['product_id'].id)], limit=1)
    #
    #     self.env['mrp.detail.planning.line'].create([
    #         {
    #             'date_char': day['name'],
    #             'date': day['date'],
    #             'product_id': element['product_id'].id,
    #             'package': element['package'],
    #             'qty': element['qty'],
    #             'capacity': element['capacity'],
    #             'packaging_line_id': element['packaging_line_id'].id,
    #             'planning_line_id': element['planning_line_id'],
    #             'section_id': element['section_id'].id,
    #             'planning_id': element['planning_id'],
    #             'employee_number': ppp_id.employee_number if ppp_id else 0,
    #         } for day in element['mrp_days']])

        self.env['mrp.detail.planning.line'].create([
            {
                'date_char': day['name'],
                'date': day['date'],
                'product_id': element['product_id'].id,
                'package': element['package'],
                'qty': element['qty'],
                'capacity': element['capacity'],
                'packaging_line_id': element['packaging_line_id'].id,
                'planning_line_id': element['planning_line_id'],
                # 'section_id': element['section_id'].id,
                'planning_id': element['planning_id'],
                'employee_number': ppp_id.employee_number if ppp_id else 0,
            } for day in element['mrp_days']])


    def create_lines_or_sections(self, element):
        # self.env['mrp.detail.planning.line'].create([{
        #     'display_type': "line_section",
        #     'name': element['date'].strftime('%d-%m-%y'),
        #     'product_id': element['product_id'],
        #     'planning_line_id': element['planning_line_id'],
        #     'section_id': element['section_id'],
        #     'planning_id': element['planning_id'],
        #     'package': element['package'],
        #     'qty': element['qty'],
        #     'capacity': element['capacity'],
        #     'packaging_line_id': element['packaging_line_id'],
        #     'date': date.today(),
        # }])

        self.env['mrp.detail.planning.line'].create([{
            'display_type': "line_section",
            'name': element['date_char'],
            'product_id': element['product_id'],
            'planning_line_id': element['planning_line_id'],
            # 'section_id': element['section_id'].id,
            'planning_id': element['planning_id'],
            'package': element['package'],
            'qty': element['qty'],
            'capacity': element['capacity'],
            'packaging_line_id': element['packaging_line_id'],
            'date': date.today(),
        }])

    def group_by_key(self, list_of_dicts, key):
        dict_of_lists = {}
        for dictionary in list_of_dicts:
            dict_key = dictionary.get(key)
            if dict_key in dict_of_lists:
                dict_of_lists[dict_key].append(dictionary)
            else:
                dict_of_lists[dict_key] = [dictionary]
        return dict_of_lists

    # This function generate detailed planning lines and regroup them by sections and by packaging line.
    # Each detailed planning line will be related to a production order
    def action_confirm(self):

        if not self.planning_line_ids:
            raise ValidationError(_("You have to give at least one planning line"))

        detailed_lines_to_delete = self.env['mrp.detail.planning.line'].search([('planning_id', '=', self.id)]).unlink()
        section_id_lst = []
        value_planning_line = []

        try:
            for pline in self.planning_line_ids:
                val = {
                    'package': pline.package,
                    'qty': pline.qty,
                    'capacity': pline.capacity,
                    'product_id': pline.product_id,
                    'packaging_line_id': pline.packaging_line_id,
                    # 'section_id': pline.section_id,
                    'mrp_days': pline.mrp_days,
                    'planning_id': self.id,
                    'planning_line_id': pline.id,
                }
                value_planning_line.append(val)

            if value_planning_line:
                # dict_dictionnaires = self.group_by_key(value_planning_line, 'section_ids') #, 'section_id')
                #
                # # Extraction des dictionnaires avec la même section_id
                # liste_meme_planning_line = [dictionnaires for dictionnaires in dict_dictionnaires.values() if
                all_detailed_line = []
                for val in value_planning_line:
                    ppp_id = self.env['mrp.packaging.pp'].search(
                        [('packaging_line_id', '=', val['packaging_line_id'].id),
                         ('product_id', '=', val['product_id'].id)], limit=1)
                    for day in val['mrp_days']:
                        detailed_line = {
                            'date_char': day['name'],
                            'date': day['date'],
                            'product_id': val['product_id'].id,
                            'package': val['package'],
                            'qty': val['qty'],
                            'capacity': val['capacity'],
                            'packaging_line_id': val['packaging_line_id'].id,
                            'planning_line_id': val['planning_line_id'],
                            'section_id': val['section_id'].id,
                            'planning_id': val['planning_id'],
                            'employee_number': ppp_id.employee_number if ppp_id else 0,
                        }
                        all_detailed_line.append(detailed_line)
                # print(f"all_detailed_line : {all_detailed_line}")
                dict_dictionnaires = self.group_by_key(all_detailed_line, 'date')

                # Extraction des dictionnaires avec la même section_id
                liste_meme_date_id = [dictionnaires for dictionnaires in dict_dictionnaires.values() if
                                         len(dictionnaires) > 1]

                # Extraction des dictionnaires restants
                liste_autres_dictionnaires = [dictionnaires[0] for dictionnaires in dict_dictionnaires.values() if
                                              len(dictionnaires) == 1]

                if liste_meme_date_id:
                    for element in liste_meme_date_id:
                        date_element = element[0]
                        self.create_lines_or_sections(date_element)
                        self.env['mrp.detail.planning.line'].create(element)
                        # dico = self.group_by_key(element, 'packaging_line_id')

                if liste_autres_dictionnaires:
                    for element in liste_autres_dictionnaires:
                        self.create_lines_or_sections(element)
                        self.env['mrp.detail.planning.line'].create(element)

        except Exception as e:
            raise e
        else:
            self.state = "confirm"

        return True

    def action_cancel(self):

        # Check if at least one of productions orders is done
        for line in self.detailed_pl_ids:
            if line.state == 'done':
                raise ValidationError(
                    _("You cannot cancel a planning which have one of it's manufacturing order done."))
        # Cancel productions of this planning
        production_ids = self.env['mrp.production'].search([('planning_id', '=', self.id)])
        production_done = production_ids.filtered(lambda self: self.state == 'done')
        if production_done:
            raise ValidationError(_("You cannot cancel this planning because some productions are already done."))
        else:
            production_ids.action_cancel()

        self.state = "cancel"

        return True

    def action_draft(self):

        self.state = "draft"
        return True

    def create_overview_wizard(self):

        action = {
            "name": "Raw Material Overview",
            "res_model": "overview.wizard",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            # "view_id": self.env.ref("view_create_overview_wizard_from").id,
            'target': 'new',
            "context": {
                "planning_id": self.id,
                "overview_ids": self.env["overview.wizard"].search([("planning_id", "=", self.id)]).ids,
            },
        }
        return action

    def verif_bom(self):
        for pl in self.planning_line_ids:
            if not self.env["mrp.bom"].search([('product_tmpl_id', '=', pl.product_id.product_tmpl_id.id)]):
                return pl.product_id

        return False

    def verif_product_proportion(self):
        for pl in self.planning_line_ids:
            if not self.env["mrp.packaging.pp"].search(
                    [('packaging_line_id', '=', pl.packaging_line_id.id), ('product_id', '=', pl.product_id.id)]):
                return pl.product_id, pl.packaging_line_id

        return False

    # Generate a manufacturing order for each detailed planning line
    def generate_mo(self):

        # Verif if products of planning have a bill of material
        verif_bom = self.verif_bom()
        picking_type_id = self.env['stock.picking.type'].search(
            [('plant_id', '=', self.plant_id.id), ('code', '=', 'mrp_operation')])
        if verif_bom:
            raise ValidationError(_("No bill of material find for %s. Please create a one." % verif_bom.name))

        if not picking_type_id.default_location_src_id or not picking_type_id.default_location_dest_id:
            raise ValidationError(
                _(f"Please configure the picking type '{picking_type_id.name}' locations before this action."))

        for line in self.detailed_pl_ids:
            if line.display_type == False:
                bom_id = self.env["mrp.bom"].search([('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)])
                bom_id = bom_id[0]
                qty = line.uom_id._compute_quantity(line.qty, bom_id.product_uom_id)
                production = self.env['mrp.production'].create({
                    "product_id": line.product_id.id,
                    "product_ref": line.product_id.name,
                    "bom_id": bom_id.id,
                    "product_qty": qty,
                    "product_uom_id": line.uom_id.id,
                    "date_planned_start": datetime.combine(line.date, datetime.min.time()),
                    "packaging_line_id": line.packaging_line_id.id,
                    # "section_id": line.section_id.id,
                    "planning_line_id": line.planning_line_id.id,
                    "detailed_pl_id": line.id,
                    "planning_id": self.id,
                    "plant_id": self.plant_id.id,
                    "location_src_id": picking_type_id.default_location_src_id.id,
                    "location_dest_id": picking_type_id.default_location_dest_id.id,
                })
                production.action_confirm()

        # Update state
        self.state = "04_mo_generated"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Manufacturing orders create with success!"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def view_mrp_orders(self):

        return {
            "name": f"{self.reference} manufacturing orders",
            "type": "ir.actions.act_window",
            "res_model": "mrp.production",
            "view_mode": "tree,form",
            "domain": [('planning_id', '=', self.id), ('state', '!=', "cancel")],
            "context": {
                'search_default_todo': True,
                # 'search_default_group_by_planning': 1,
                'search_default_group_by_section': 1,
                'search_default_group_by_packaging_line_id': 1,
            },
        }

    # Action for supply orders checking
    def view_internal_transfer(self):
        internal_transfer = self.env['stock.picking'].search([
            ('picking_type_code', '=', 'internal'), ('planning_id', '=', self.id)
        ])

        if internal_transfer:
            if len(internal_transfer) == 1:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'stock.picking',
                    'res_id': internal_transfer.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'stock.picking',
                    'view_mode': 'tree,form',
                    'name': _('List of supply orders'),
                    'domain': [('id', 'in', internal_transfer.ids)],
                    'target': 'current',
                }

    # Action for replace a product into another in a planning
    def action_product_replacement(self):
        if self.state != '04_mo_generated':
            raise ValidationError(_("You cannot replace a product when mrp orders are not generated."))
        if self.detailed_pl_done_state:
            raise ValidationError(_("You cannot replace a product when products are manufacted."))

        action = {
            "name": f"Replace product in {self.reference}",
            "type": "ir.actions.act_window",
            "res_model": "replace.product",
            "view_mode": "form",
            "context": {'default_planning_id': self.id},
            "target": "new",
        }

        return action

    # Prepare printing data
    def regroup_for_report(self):
        for rec in self:
            print(f"rec.state : {rec.state}")
            if rec.state == 'draft':
                raise UserError(_("You cannot print a planning in draft state. Confirm it before."))
            else:
                grouped_lines = defaultdict(lambda: defaultdict(list))

                for detailed_planning_line in rec.detailed_pl_ids:
                    if detailed_planning_line.display_type == False:
                        section = rec.section_ids
                        packaging_line = detailed_planning_line.packaging_line_id

                        grouped_lines[section][packaging_line].append(detailed_planning_line)

                # Convertir le résultat en un dictionnaire Python
                result_dict = {}
                for section, packaging_lines in grouped_lines.items():
                    section_dict = {}
                    for packaging_line, detailed_planning_lines in packaging_lines.items():
                        section_dict[packaging_line] = detailed_planning_lines
                    result_dict[section] = section_dict

                return result_dict

    # Action to confirm productions orders of current planning
    # def action_confirm_productions(self):
    #     for dpl in self.detailed_pl_ids:
    #         production_id = self.env['mrp.production'].search(
    #             [['detailed_pl_id', '=', dpl.id], ['state', 'in', ['draft']]])
    #         production_id.action_confirm() if production_id else False
    #
    #     self.mrp_production_general_state = "confirm"
    #     message = (f"<p><b><em> (Detailed planning lines)</em> State :</b></p><ul>"
    #                f"<li><p><b> Draft <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Confirmed</span></b></p></li>")
    #     mrp_planning = self.env['mrp.planning'].browse(self.id)
    #     mrp_planning.message_post(body=message)
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'type': 'success',
    #             'message': _("Manufacturing orders confirm with success!"),
    #             'next': {'type': 'ir.actions.act_window_close'},
    #         }
    #     }

    # Action to finalize planning's products manufacturing
    # def action_mark_productions_as_done(self):
    #     if self.detailed_pl_ids.filtered(lambda self: self.state == 'progress'):
    #         raise ValidationError(_("You have to manage line(s) in progress state before this action."))
    #
    #     productions = []
    #     for dpl in self.detailed_pl_ids:
    #         production_id = self.env['mrp.production'].search(
    #             [['detailed_pl_id', '=', dpl.id], ['state', 'in', ['confirmed', 'progress', 'to_close']]])
    #         if production_id:
    #             productions.append(production_id.id)
    #
    #     production_ids = self.env['mrp.production'].browse(productions)
    #     result = production_ids.button_mark_done()
    #     return result

    # Dupliquer le formulaire de planning avec les données qui doivent etre gardé dans le nouveau
    def copy(self, default=None):
        if default is None:
            default = {}

        if self.planning_line_ids:
            new_planning_line_ids = [(0, 0, {
                'package': line.package,
                # 'qty_compute': line.qty_compute,
                'qty': line.qty,
                'capacity': line.capacity,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,
                'uom_domain': [(6, 0, line.uom_domain.ids)],
                'packaging_line_id': line.packaging_line_id.id,
                'packaging_line_domain': [(6, 0, line.packaging_line_domain.ids)],
                # 'section_id': line.section_id.id,
                'mrp_days': [(6, 0, line.mrp_days.ids)],
                'begin_date': line.begin_date,
                'end_date': line.end_date,
                'planning_id': self.id,
            }) for line in self.planning_line_ids]
            default['planning_line_ids'] = new_planning_line_ids

        return super().copy(default)

    # Function to add a date in scheduled dates
    # @api.onchange('scheduled_date')
    # def _onchange_scheduled_date(self):
    #
    #     if self.scheduled_date != self.today_date:
    #         iso = self.scheduled_date.isocalendar()
    #
    #         monday = date.fromisocalendar(year=iso[0], week=iso[1], day=1)
    #         tuesday = date.fromisocalendar(year=iso[0], week=iso[1], day=2)
    #         wednesday = date.fromisocalendar(year=iso[0], week=iso[1], day=3)
    #         thursday = date.fromisocalendar(year=iso[0], week=iso[1], day=4)
    #         friday = date.fromisocalendar(year=iso[0], week=iso[1], day=5)
    #         saturday = date.fromisocalendar(year=iso[0], week=iso[1], day=6)
    #         sunday = date.fromisocalendar(year=iso[0], week=iso[1], day=7)
    #
    #         if iso[2] == 1:
    #             day_name = 'monday {}/{}'.format(monday.strftime('%d'), monday.month)
    #         elif iso[2] == 2:
    #             day_name = 'tuesday {}/{}'.format(tuesday.strftime('%d'), tuesday.month)
    #         elif iso[2] == 3:
    #             day_name = 'wednesday {}/{}'.format(wednesday.strftime('%d'), wednesday.month)
    #         elif iso[2] == 4:
    #             day_name = 'thursday {}/{}'.format(thursday.strftime('%d'), thursday.month)
    #         elif iso[2] == 5:
    #             day_name = 'friday {}/{}'.format(friday.strftime('%d'), friday.month)
    #         elif iso[2] == 6:
    #             day_name = 'saturday {}/{}'.format(saturday.strftime('%d'), saturday.month)
    #         elif iso[2] == 7:
    #             day_name = 'sunday {}/{}'.format(sunday.strftime('%d'), sunday.month)
    #
    #         for day in self.week_of:
    #             if day_name in day.name:
    #                 raise UserError(_("This day already exists in the week"))
    #
    #             # day_iso = day.date.isocalendar()
    #
    #             # if iso.year < day_iso.year:
    #             #
    #             #     raise UserError(_("The date must not be less than the current week's dates."))
    #             # elif self.scheduled_date.month < day.date.month:
    #             #
    #             #     raise UserError(_("The date must not be less than the current week's dates."))
    #             # elif iso.week < day_iso.week:
    #             #     if self.scheduled_date.month <= day.date.month:
    #             #         if iso.year <= day_iso.year:
    #             #             raise UserError(_("The date must not be less than the current week's dates."))
    #
    #         day_in_week_of = self.env['mrp.planning.days'].search([
    #             ('name', '=', day_name)
    #         ])
    #         if day_in_week_of:
    #             # Récupérer les valeurs actuelles du champ Many2many self.week_of
    #             existing_week_of = self.week_of.ids
    #
    #             # Ajouter l'ID de day_record à la liste des valeurs existantes
    #             existing_week_of.append(day_in_week_of.id)
    #
    #             # Écrire la liste mise à jour dans le champ Many2many self.week_of
    #             self.week_of = [(6, 0, existing_week_of)]
    #             self._get_week_of_domain(day_name)
    #         else:
    #             day_record = self.env['mrp.planning.days'].create({
    #                 'name': day_name,
    #                 'date': self.scheduled_date
    #             })
    #             # Récupérer les valeurs actuelles du champ Many2many self.week_of
    #             existing_week_of = self.week_of.ids
    #             # Ajouter l'ID de day_record à la liste des valeurs existantes
    #             existing_week_of.append(day_record.id)
    #             # Écrire la liste mise à jour dans le champ Many2many self.week_of
    #             self.week_of = [(6, 0, existing_week_of)]
    #             self._get_week_of_domain(day_name)
    #
    # def _get_week_of_domain(self, day_name):
    #
    #     return self.week_days.append(day_name)

    def unlink(self):

        records_to_delete = self.filtered(lambda rec: rec.state not in ['confirm', '04_mo_generated'])
        if records_to_delete:
            res = super(MrpPlanning, records_to_delete).unlink()
        else:
            raise UserError(_("You cannot delete confirmed schedules or generated schedules"))

        return res

    def _get_pl_message(self, pls, label):
        if not pls:
            return ""
        message = f"<p><em> {label} : </em></p><ul>"

        for elm in pls:
            product = self.env['product.product'].browse(elm['product_id'])
            section = self.env['mrp.section'].browse(elm['section_id'])
            packaging_line = self.env['mrp.packaging.line'].browse(elm['packaging_line_id'])

            message += f"<li>{product.name}, packaging line {packaging_line.name}, section {section.name}</li>"

        return message

    def get_line_dl_id(self, env, dl_id):
        return self.env[env].browse(dl_id)

    def print_message(self, mrp_planning, env, dl_id, detail, format_string, extra_info):
        line_dl_id = self.get_line_dl_id(env, dl_id)
        message = (
            f"<ul><li><p><b>{detail['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style = 'color: #0182b6;' > {line_dl_id.name} </span></b><em> {extra_info} </em></p></li>")
        mrp_planning.message_post(body=message)

    # Optimize tracking during planning edition
    def write(self, vals):
        for rec in self:
            # Récupérer le planning associé
            mrp_planning = self._get_mrp_planning(rec)


            old_planning_line = self._get_old_planning_lines(rec)
            old_detail_planning_line = self._get_old_detail_planning_lines(rec)
            res = super(MrpPlanning, rec).write(vals)

            # self._process_section_changes(vals, old_sect_name, mrp_planning)

            self.process_planning_line_ids(vals, old_planning_line, mrp_planning)
            self.process_detailed_pl_ids(vals, old_detail_planning_line, mrp_planning)

        return res

    def _get_mrp_planning(self, rec):
        params = self.env.context.get('params')
        return self.env['mrp.planning'].browse(params.get('id')) if params else rec.env['mrp.planning'].browse(rec.id)

    def _get_old_planning_lines(self, rec):
        return [{
            'id': pl.id,
            'product_id': pl.product_id,
            'packaging_line_id': pl.packaging_line_id,
            'qty': pl.qty,
            # 'section_id': pl.section_id,
            'mrp_days': pl.mrp_days,
            'uom_id': pl.uom_id,
        } for pl in rec.planning_line_ids]

    def _get_old_detail_planning_lines(self, rec):
        return [{
            'id': dl.id,
            'display_type': dl.display_type,
            'name': dl.name,
            'date': dl.date,
            'product_id': dl.product_id,
            'qty': dl.qty,
            'packaging_line_id': dl.packaging_line_id,
            # 'section_id': dl.section_id.id,
        } for dl in rec.detailed_pl_ids]

    # def _process_section_changes(self, vals, old_sect_name, mrp_planning):
    #     if 'section_ids' in vals:
    #         new_sect_name = self._get_new_section_names(vals)
    #         formatted_old_sect_name = ', '.join(map(str, old_sect_name))
    #         formatted_new_sect_name = ', '.join(map(str, new_sect_name))
    #         message_to_sect = f"<p><b> {formatted_old_sect_name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{formatted_new_sect_name}</span></b><em> (Sections)</em></p>"
    #         mrp_planning.message_post(body=message_to_sect)
    #
    # def _get_new_section_names(self, vals):
    #     new_sect_id = [sect for val in vals['section_ids'] for sect in val[2]]
    #     new_sect_name = [self.env['mrp.section'].browse(nsn).name for nsn in new_sect_id]
    #     return new_sect_name

    def _process_section_changes(self, vals, old_sect_name, mrp_planning):
        if 'section_ids' in vals:
            new_sect_name = self._get_new_section_name(vals)
            formatted_old_sect_name = old_sect_name
            formatted_new_sect_name = new_sect_name
            message_to_sect = f"<p><b> {formatted_old_sect_name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{formatted_new_sect_name}</span></b><em> (Sections)</em></p>"
            mrp_planning.message_post(body=message_to_sect)

    def _get_new_section_name(self, vals):
        new_sect_id = vals.get('section_ids')
        if new_sect_id:
            new_sect_name = self.env['mrp.section'].browse(new_sect_id).name
            return new_sect_name
        return False



    def process_planning_line_ids(self, vals, old_planning_line, mrp_planning):
        if 'planning_line_ids' in vals:

            add_pl = [val[2] for val in vals['planning_line_ids'] if val[0] == 0]
            delete_pl = [val[1] for val in vals['planning_line_ids'] if val[0] == 2]

            update_pl = [{
                'id': val[1],
                'value': val[2]
            } for val in vals['planning_line_ids'] if val[0] == 1]


            self.process_update_pl(update_pl, old_planning_line, mrp_planning)
            self.process_delete_pl(delete_pl, old_planning_line, mrp_planning)


            message_to_add_pl = self._get_pl_message(add_pl, "Planning lines added are")
            if message_to_add_pl:
                mrp_planning.message_post(body=message_to_add_pl)

    def process_update_pl(self, update_pl, old_planning_line, mrp_planning):
        if not update_pl:
            return

        update_pl_id = [pl['id'] for pl in update_pl]


        for pl in update_pl:
            for planning in old_planning_line:
                if pl['id'] == planning['id']:
                    position = update_pl_id.index(pl['id'])
                    value = update_pl[position]['value']
                    if 'product_id' in value:
                        msg = ""

                        message_to_update_pl = f"<p><b><em> (Planning lines)</em> Packaging Line {planning['packaging_line_id']['name']}, Section {planning['section_id']['name']} : </b></p><ul>"
                        new_prod = self.env['product.product'].browse(value['product_id'])
                        msg += f"<li><p><b>{planning['product_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{new_prod.name}</span></b></p></li>"
                        message_to_update_pl += msg
                        if 'packaging_line_id' in value:
                            new_pack = self.env['mrp.packaging.line'].browse(value['packaging_line_id'])
                            msg += f"<li><p><b>Packaging line {planning['packaging_line_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Packaging line {new_pack.name}</span></b></p></li>"

                        if 'qty' in value:
                            msg += f"<li><p><b>Quantity {planning['qty']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Quantity {value['qty']}</span></b></p></li>"

                        # if 'section_id' in value:
                        #     new_sect = self.env['mrp.section'].browse(value['section_id'])
                        #     msg += f"<li><p><b>Section {planning['section_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Section {new_sect.name}</span></b></p></li>"
                        #
                        # if 'mrp_days' in value:
                        #
                        #     old_day_name = [day['name'] for day in planning['mrp_days']]
                        #     new_day_id = [day for dy in value['mrp_days'] for day in dy[2]]
                        #
                        #     new_day_name = []
                        #     for ndi in new_day_id:
                        #         ndi_name = self.env['mrp.planning.days'].browse(ndi)
                        #         new_day_name.append(ndi_name.name)

                            msg += f"<li><p><b>{old_day_name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{new_day_name}</span></b></p></li>"
                        if 'uom_id' in value:
                            new_uom = self.env['uom.uom'].browse(value['uom_id'])
                            msg += f"<li><p><b>{planning['uom_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{new_uom.name}</span></b></p></li>"

                        message_to_update_pl += f"{msg}"

                        mrp_planning.message_post(body=message_to_update_pl)

                    message_to_update_pl = f"<p><b><em> (Planning lines)</em> {planning['product_id']['name']} : </b></p><ul>" if 'product_id' not in value else f"<p><b><em> (Planning lines)</em> {self.env['product.product'].browse(value['product_id']).name} : </b></p><ul>"
                    msg = ""
                    if 'packaging_line_id' in value:
                        new_pack = self.env['mrp.packaging.line'].browse(value['packaging_line_id'])
                        msg += f"<li><p><b>Packaging line {planning['packaging_line_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Packaging line {new_pack.name}</span></b></p></li>"

                    if 'qty' in value:
                        msg += f"<li><p><b>Quantity {planning['qty']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Quantity {value['qty']}</span></b></p></li>"

                    if 'section_id' in value:
                        new_sect = self.env['mrp.section'].browse(value['section_id'])
                        msg += f"<li><p><b>Section {planning['section_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Section {new_sect.name}</span></b></p></li>"

                    if 'mrp_days' in value:

                        old_day_name = [day['name'] for day in planning['mrp_days']]
                        new_day_id = [day for dy in value['mrp_days'] for day in dy[2]]

                        new_day_name = []
                        for ndi in new_day_id:
                            ndi_name = self.env['mrp.planning.days'].browse(ndi)
                            new_day_name.append(ndi_name.name)

                        msg += f"<li><p><b>{old_day_name} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{new_day_name}</span></b></p></li>"
                    if 'uom_id' in value:
                        new_uom = self.env['uom.uom'].browse(value['uom_id'])
                        msg += f"<li><p><b>{planning['uom_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{new_uom.name}</span></b></p></li>"

                    message_to_update_pl += f"{msg}"

                    mrp_planning.message_post(body=message_to_update_pl)

    def process_delete_pl(self, delete_pl, old_planning_line, mrp_planning):
        if delete_pl:
            message_to_delete_pl = "<p><em>Planning lines removed are :</em></p><ul>"

            for pl in delete_pl:
                for planning in old_planning_line:
                    if pl == planning['id']:
                        # message_to_delete_pl += f"<li><p><b>{planning['product_id']['name']}, section {planning['section_id']['name']}, packaging line {planning['packaging_line_id']['name']}</b></p></li>"
                        message_to_delete_pl += f"<li><p><b>{planning['product_id']['name']}, packaging line {planning['packaging_line_id']['name']}</b></p></li>"
            mrp_planning.message_post(body=message_to_delete_pl)

    def process_detailed_pl_ids(self, vals, old_detail_planning_line, mrp_planning):
        if 'detailed_pl_ids' in vals:
            # Fabrication
            print(f"vals : {vals}")
            detail_id = []
            for val in vals['detailed_pl_ids']:
                if val[2]:
                    for elm in val[2]:
                        if elm == 'qty_done':
                            print('yes')
                            detail_id.append(val[1])
            # detail_id = [val[1] for val in vals['detailed_pl_ids'] for elm in val[2] if elm == 'qty_done']
            if detail_id:
                # print(f"detail_id : {detail_id}")
                for detail in detail_id:
                    rec = self.env['mrp.detail.planning.line'].browse(detail)
                    if rec.qty_done > rec.qty:
                        rec.qty_done = False
                        raise UserError(_('The quantity made cannot be greater than the planned quantity'))
                    elif rec.qty == rec.qty_done:
                        if rec.mrp_production_id.reservation_state == 'assigned':
                            rec.mrp_production_id.qty_producing = rec.qty_done
                            for move in rec.mrp_production_id.move_raw_ids:
                                move.quantity_done = move.should_consume_qty
                            rec.mrp_production_id.button_mark_done()
                        else:
                            raise UserError(_('Unavailability of components, please create supply orders'))
                    elif rec.qty_done < rec.qty:
                        if rec.mrp_production_id.reservation_state == 'assigned':
                            rec.mrp_production_id.qty_producing = rec.qty_done
                            for move in rec.mrp_production_id.move_raw_ids:
                                move.quantity_done = move.should_consume_qty
                            rec.mrp_production_id.with_context(skip_backorder=True).button_mark_done()
                        else:
                            raise UserError(_('Unavailability of components, please create supply orders'))

            # Tracabilité
            new_dl_id = [val[1] for val in vals['detailed_pl_ids'] if val[0] > 2]
            delete_dl = [val[1] for val in vals['detailed_pl_ids'] if val[0] == 2]
            update_dl = [{'id': val[1], 'value': val[2]} for val in vals['detailed_pl_ids'] if val[0] == 1]

            ids = self.env['mrp.detail.planning.line'].browse(new_dl_id)
            section_dl = [dl.id for dl in ids if dl.display_type == 'line_section']
            line_dl = [dl.id for dl in ids if dl.display_type == 'line_note']
            section_dls = sorted(section_dl)
            line_dls = sorted(line_dl)

            self.process_update_dl(update_dl, old_detail_planning_line, mrp_planning, section_dls, line_dls)
            self.process_delete_dl(delete_dl, old_detail_planning_line, mrp_planning, section_dls, line_dls)

    def process_update_dl(self, update_dl, old_detail_planning_line, mrp_planning, section_dls, line_dls):
        if update_dl:

            update_dl_id = [dl['id'] for dl in update_dl]

            for dl in update_dl:
                for detail in old_detail_planning_line:
                    if dl['id'] == detail['id']:
                        if dl['id'] in section_dls:
                            self.print_message(mrp_planning, 'mrp.detail.planning.line', dl['id'], detail, "",
                                               " (Detailed planning lines Large Sections)")

                        elif dl['id'] in line_dls:
                            self.print_message(mrp_planning, 'mrp.detail.planning.line', dl['id'], detail, "",
                                               " (Detailed planning lines Large Line)")

                        else:
                            # Récupérer la lign et la section de l'éléments modifié
                            sect_dl = max([sect_id for sect_id in section_dls if sect_id < dl['id']],
                                          default=None)
                            line_dl = max([line_id for line_id in line_dls if line_id < dl['id']],
                                          default=None)

                            large_section = self.env['mrp.detail.planning.line'].browse(sect_dl)
                            large_line = self.env['mrp.detail.planning.line'].browse(line_dl)

                            position = update_dl_id.index(dl['id'])
                            value = update_dl[position]['value']

                            if 'date' in value:
                                msg = ""
                                message_to_update_dl = f"<p><b><em> (Detailed planning lines)</em> Large Section {large_section.name}, Large Line {large_line.name} : </b></p><ul>"
                                msg += f"<li><p><b>{detail['date']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{dl['date']}</span></b></p></li>"
                                message_to_update_dl += msg
                                mrp_planning.message_post(body=message_to_update_dl)

                            message_to_update_dl = f"<p><b><em> (Detailed planning lines)</em> Large Section {large_section.name}, Large Line {large_line.name}, Date {detail['date'].strftime('%d/%m/%Y')} : </b></p><ul>" if 'date' not in value else f"<p><b><em> (Detailed planning lines)</em> Large Section {large_section.name}, Large Line {large_line.name}, Date {dl['date']} : </b></p><ul>"
                            msg = ""
                            if 'product_id' in value:
                                new_prod = self.env['product.product'].browse(value['product_id'])
                                msg += f"<li><p><b>{detail['product_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{new_prod.name}</span></b></p></li>"

                            if 'packaging_line_id' in value:
                                new_pack = self.env['mrp.packaging.line'].browse(value['packaging_line_id'])
                                msg += f"<li><p><b>Packaging line {detail['packaging_line_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Packaging line {new_pack.name}</span></b></p></li>"

                            if 'section_id' in value:
                                new_sect = self.env['mrp.section'].browse(value['section_id'])
                                msg += f"<li><p><b>Small Section {detail['section_id']['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Section {new_sect.name}</span></b></p></li>"

                            if 'qty' in value:
                                msg += f"<li><p><b>Quantity {detail['qty']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>Quantity {value['qty']}</span></b></p></li>"

                            message_to_update_dl += f"{msg}"

                            mrp_planning.message_post(body=message_to_update_dl)

    def process_delete_dl(self, delete_dl, old_detail_planning_line, mrp_planning, section_dls, line_dls):
        if delete_dl:
            message_to_delete_dl = "<p><em>Detailed planning lines removed are :</em></p><ul>"

            for dl in delete_dl:
                for detail in old_detail_planning_line:
                    if dl == detail['id']:
                        if dl in section_dls:
                            new_sect = self.env['mrp.detail.planning.line'].browse(dl['id'])
                            message_to_delete_dl += (f"<li><p><b>"
                                                     f"{detail['name']} <span style='font-size: "
                                                     f"1.5em;'>&#8594;</span> <span style='color: #0182b6;'>"
                                                     f"{new_sect.name}</span></b><em>(Large Section)</em></p></li>")
                            mrp_planning.message_post(body=message_to_delete_dl)

                        elif dl in line_dls:
                            new_line = self.env['mrp.detail.planning.line'].browse(dl['id'])
                            message_to_delete_dl += f"<li><p><b>{detail['name']} <span style='font-size: 1.5em;'>&#8594;</span> <span style='color: #0182b6;'>{new_line.name}</span></b><em>(Large Line)</em></p></li>"
                            mrp_planning.message_post(body=message_to_delete_dl)

                        else:
                            sect_dl = max([sect_id for sect_id in section_dls if sect_id < dl],
                                          default=None)
                            line_dl = max([line_id for line_id in line_dls if line_id < dl],
                                          default=None)
                            large_section = self.env['mrp.detail.planning.line'].browse(sect_dl)
                            large_line = self.env['mrp.detail.planning.line'].browse(line_dl)
                            message_to_delete_dl += f"<li><p><b>{detail['product_id']['name']}, large section {large_section.name}, large line {large_line.name}</b></p></li>"
                            mrp_planning.message_post(body=message_to_delete_dl)


class MrpPlanninLine(models.Model):
    _name = "mrp.planning.line"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    @api.depends('product_id')
    def _compute_uom_domain(self):
        for rec in self:
            if rec.product_id:
                rec.uom_domain = [uom_id.id for uom_id in rec.product_id.product_tmpl_id.uom_id.category_id.uom_ids]
            else:
                rec.uom_domain = []

    @api.onchange('product_id')
    def _compute_default_uom_id(self):
        for rec in self:
            if rec.product_id:
                if not rec.uom_id and rec.uom_domain:
                    rec.uom_id = rec.uom_domain[0]._origin.id

    @api.depends('product_id', 'packaging_line_id')
    def _compute_qty(self):

        for rec in self:
            if rec.product_id and rec.packaging_line_id:
                ppp_id = self.env['mrp.packaging.pp'].search(
                    [('product_id', '=', rec.product_id.id), ('packaging_line_id', '=', rec.packaging_line_id.id)],
                    limit=1)
                rec.qty = ppp_id.capacity
                rec.recent_qty = rec.qty
                # rec.qty_compute = rec.qty
            else:
                rec.qty = 0

    @api.depends('product_id')
    def _compute_packaging_line_domain(self):

        for rec in self:
            if rec.product_id:
                ppp_ids = self.env['mrp.packaging.pp'].search([('product_id', '=', rec.product_id.id)])
                l = [ppp_id.packaging_line_id.id for ppp_id in ppp_ids]
                rec.packaging_line_domain = l
            else:
                rec.packaging_line_domain = []

    @api.onchange('product_id')
    def _get_default_packaging_line(self):
        ppp_id = self.env['mrp.packaging.pp'].search([('product_id', '=', self.product_id.id)], limit=1)
        self.packaging_line_id = ppp_id.id if ppp_id else False

    @api.depends('product_id')
    def _compute_bill_of_material_domain(self):
        for rec in self:
            if rec.product_id:
                boms = self.env['mrp.bom'].search([('product_tmpl_id', '=', rec.product_id.id)])
                rec.bom_domain = [bom.id for bom in boms]
                print("le boms", rec.bom_domain)
            else:
                rec.bom_domain = []

    @api.onchange('product_id')
    def _get_default_bill_of_material(self):
        code = self.env['ir.config_parameter'].sudo().get_param('mrp_planning.code')
        # code = self.env.ref('mrp_planning.code')
        print('le code',code)
        for rec in self:
            if rec.product_id:
                bom_ids = self.env['mrp.bom'].search([('product_tmpl_id', '=', self.product_id.id)])
                if bom_ids:
                    rec.bom_id = bom_ids[0]

    @api.onchange('qty')
    def _update_quantity_variants_onchange_qty(self):
        for rec in self:
            if rec.product_id and rec.packaging_line_id and rec.bom_id:
                rec.recent_qty = rec.qty
                rec.package = rec.qty / rec.bom_id.packing if rec.bom_id.packing != 0 else 0
                rec.capacity = rec.qty * rec.bom_id.net_weight
            else:
                rec.recent_qty, rec.package, rec.capacity = 0, 0, 0

    @api.onchange('capacity')
    def _update_quantity_variants_onchange_capacity(self):
        for rec in self:
            if rec.product_id and rec.packaging_line_id and rec.bom_id:
                # print("Affectation qty 2", rec.recent_qty, rec.qty)
                if rec.qty != rec.recent_qty:
                    rec.qty = rec.capacity / rec.bom_id.net_weight if rec.bom_id.net_weight != 0 else 0
                    rec.package = rec.qty / rec.bom_id.packing if rec.bom_id.packing != 0 else 0
            else:
                rec.package, rec.qty = 0, 0

    @api.onchange('package')
    def _update_quantity_variants_onchange_package(self):
        for rec in self:
            if rec.product_id and rec.packaging_line_id and rec.bom_id:
                if rec.recent_qty != rec.qty:
                    rec.qty = rec.package * rec.bom_id.packing
                    rec.capacity = rec.qty * rec.bom_id.net_weight
            else:
                rec.capacity, rec.qty = 0, 0

    @api.depends('begin_date', 'end_date')
    def _compute_mrp_days(self):
        for rec in self:
            if rec.begin_date and rec.end_date:
                current_date = rec.begin_date
                day_dico = {
                    1: 'monday',
                    2: 'tuesday',
                    3: 'wednesday',
                    4: 'thursday',
                    5: 'friday',
                    6: 'saturday',
                    7: 'sunday',
                }
                mrp_days = []
                while current_date <= rec.end_date:
                    iso = current_date.isocalendar()
                    day = day_dico[iso.weekday]
                    name = '{} {}/{}'.format(day, current_date.strftime('%d'), current_date.strftime('%m'))
                    day_record = self.env['mrp.planning.days'].search([
                        ('name', '=', name),
                        ('date', '=', current_date)
                    ])
                    if not day_record:
                        day_record = self.env['mrp.planning.days'].create({
                            'name': name,
                            'date': current_date
                        })
                    mrp_days.append((4, day_record.id, 0))
                    current_date = current_date + timedelta(days=1)
                rec.mrp_days = mrp_days

    package = fields.Float(_("Package"))
    # qty_compute = fields.Integer(_("Qty per day"))
    recent_qty = fields.Integer()
    qty = fields.Float(_("Qty per day"), compute="_compute_qty", store=True, readonly=False)
    capacity = fields.Float(_("Capacity"))
    employee_number = fields.Integer(_("EN"))

    product_id = fields.Many2one("product.product", string=_("Article"), required=True)
    uom_id = fields.Many2one("uom.uom", _("Unit of measure"), required=1)
    uom_domain = fields.Many2many("uom.uom", compute="_compute_uom_domain")
    packaging_line_domain = fields.Many2many("mrp.packaging.line", compute="_compute_packaging_line_domain")
    packaging_line_first = fields.Many2one("mrp.packaging.line")
    packaging_line_id = fields.Many2one("mrp.packaging.line", tracking=True, required=True)

    mrp_days = fields.Many2many('mrp.planning.days', string='Mrp Days', compute="_compute_mrp_days")
    begin_date = fields.Date(_('Begin Date'))
    end_date = fields.Date(_('End Date'))
    planning_id = fields.Many2one("mrp.planning")
    bom_domain = fields.Many2many("mrp.bom", compute="_compute_bill_of_material_domain")
    bom_id = fields.Many2one("mrp.bom", string=_("Bill of material"), required=1)


class MrpDetailPlanningLine(models.Model):
    _name = "mrp.detail.planning.line"

    def _compute_state(self):
        for rec in self:
            production_id = self.env['mrp.production'].search([('detailed_pl_id', '=', rec.id)])
            rec.state = production_id.state

    @api.depends('product_id')
    def _compute_packaging_line_domain(self):
        for rec in self:
            if rec.product_id:
                ppp_ids = self.env['mrp.packaging.pp'].search([('product_id', '=', rec.product_id.id)])
                l = [ppp_id.packaging_line_id.id for ppp_id in ppp_ids]

                rec.packaging_line_domain = l
            else:
                rec.packaging_line_domain = []

    def _compute_mrp_production_id(self):
        for line in self:
            mrp_productions = self.env['mrp.production'].search([('detailed_pl_id', '=', line.id)]).id
            line.mrp_production_id = mrp_productions

    @api.onchange('qty')
    def _update_quantity_variants_onchange_qty(self):
        for rec in self:
            bom_ids = self.env['mrp.bom'].search([('product_tmpl_id', '=', self.product_id.id)])
            if bom_ids:
                rec.bom_id = bom_ids[0]
            if rec.product_id and rec.packaging_line_id and rec.bom_id:
                rec.recent_qty = rec.qty
                rec.package = rec.qty / rec.bom_id.packing if rec.bom_id.packing != 0 else 0
                rec.capacity = rec.qty * rec.bom_id.net_weight
            else:
                rec.recent_qty, rec.package, rec.capacity = 0, 0, 0

    @api.onchange('capacity')
    def _update_quantity_variants_onchange_capacity(self):
        for rec in self:
            bom_ids = self.env['mrp.bom'].search([('product_tmpl_id', '=', self.product_id.id)])
            if bom_ids:
                rec.bom_id = bom_ids[0]
            if rec.product_id and rec.packaging_line_id and rec.bom_id:
                # print("Affectation qty 2", rec.recent_qty, rec.qty)
                if rec.qty != rec.recent_qty:
                    rec.qty = rec.capacity / rec.bom_id.net_weight if rec.bom_id.net_weight != 0 else 0
                    rec.package = rec.qty / rec.bom_id.packing if rec.bom_id.packing != 0 else 0
            else:
                rec.package, rec.qty = 0, 0

    @api.onchange('package')
    def _update_quantity_variants_onchange_package(self):
        for rec in self:
            bom_ids = self.env['mrp.bom'].search([('product_tmpl_id', '=', self.product_id.id)])
            if bom_ids:
                rec.bom_id = bom_ids[0]
            if rec.product_id and rec.packaging_line_id and rec.bom_id:
                if rec.recent_qty != rec.qty:
                    rec.qty = rec.package * rec.bom_id.packing
                    rec.capacity = rec.qty * rec.bom_id.net_weight
            else:
                rec.capacity, rec.qty = 0, 0

    date_char = fields.Char(_("Date"))
    date = fields.Date(_("Date"), required=1)
    product_ref = fields.Char(related="product_id.default_code", string=_("Article"))
    product_id = fields.Many2one("product.product", string=_("Désignation"), required=True)
    package = fields.Float(_("Package"),digits=(16, 2))
    qty = fields.Float(_("Quantity"), required=1)
    capacity = fields.Float(_("Capacity"),digits=(16, 2))
    recent_qty = fields.Integer()
    bom_id = fields.Many2one("mrp.bom", string=_("Bill of material"))
    state = fields.Selection([
        ('draft', _("Draft")),
        ('confirmed', _("Confirmed")),
        ('progress', _("In progress")),
        ('done', _("Done")),
        ('to_close', _("To close")),
        ('cancel', _("Cancelled")),
    ], string=_("Production order state"), compute="_compute_state")

    employee_number = fields.Integer(_("EN"), default=lambda self: self.packaging_line_id.ppp_ids.search(
        [('product_id', '=', self.product_id.id)]).employee_number)

    uom_id = fields.Many2one("uom.uom", related="planning_line_id.uom_id")
    packaging_line_id = fields.Many2one("mrp.packaging.line", required=1, tracking=True)
    planning_line_id = fields.Many2one("mrp.planning.line")
    # section_id = fields.Many2one("mrp.section", required=True)
    planning_id = fields.Many2one("mrp.planning")
    packaging_line_domain = fields.Many2many("mrp.packaging.line", compute="_compute_packaging_line_domain")
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False)
    name = fields.Text()
    mrp_production_id = fields.Many2one("mrp.production", compute="_compute_mrp_production_id")
    qty_done = fields.Integer(_("Quantity done"))

    def action_manage_production(self):
        production_id = self.env['mrp.production'].search([('detailed_pl_id', '=', self.id)])
        action = {
            "name": f"Manufacturing order",
            "type": "ir.actions.act_window",
            "res_model": "mrp.production",
            "view_mode": "form",
            "res_id": production_id.id,
            "views": [(self.env.ref('mrp.mrp_production_form_view').id, 'form')],
            "target": "new",
        }
        return action

    def unlink(self):
        for rec in self:
            if self.env['mrp.production'].search(
                    [('detailed_pl_id', '=', rec.id), ('state', 'not in', ['draft', 'cancel'])]):
                raise ValidationError(
                    _(f"Impossible to delete the detailed planning line {rec.id} because an actif production order is related to it."))
        return super(MrpDetailPlanningLine, self).unlink()

    def action_replace_product_from_planning(self):
        action = self.env.ref('mrp_planning.action_replace_product').read()[0]
        val = {
            'planning_id': self.planning_id,
            'product_to_replace': self.product_id.id,
            # 'section': self.section_id,
            'packaging_line': self.packaging_line_id,
            'replacement_days': self.env['mrp.planning.days'].search([
                ('date', '=', self.date)
            ])
        }
        action['context'] = {
            'replace_product_from_detailed_planning': self.id
        }
        return action

    # @api.onchange('qty_done')
    # def _onchange_qty_done(self):
    #     for rec in self:
    #         if rec.qty_done > rec.qty:
    #             rec.qty_done = False
    #             raise UserError(_('The quantity made cannot be greater than the planned quantity'))
    #         elif rec.qty == rec.qty_done:
    #             if rec.mrp_production_id.reservation_state == 'assigned':
    #                 rec.mrp_production_id.qty_producing = rec.qty_done
    #                 for move in rec.mrp_production_id.move_raw_ids:
    #                     move.quantity_done = move.should_consume_qty
    #                 print(f"rec.id : {rec.id}")
    #                 self.env['mrp.planning'].search([
    #                     ('id', '=', rec.planning_id.id)
    #                 ]).save()
    #                 # rec.planning_id.save()
    #                 rec.mrp_production_id.button_mark_done()
    #             else:
    #                 raise UserError(_('Unavailability of components, please create supply orders'))
    #         elif rec.qty_done < rec.qty:
    #             if rec.mrp_production_id.reservation_state == 'assigned':
    #                 rec.mrp_production_id.qty_producing = rec.qty_done
    #                 for move in rec.mrp_production_id.move_raw_ids:
    #                     move.quantity_done = move.should_consume_qty
    #                 # stock_scrap = self.env['stock.scrap'].create({
    #                 #     'product_id': rec.product_id.id,
    #                 #     'scrap_qty': rec.qty - rec.qty_done,
    #                 # })
    #                 # stock_scrap.action_validate()
    #                 # self.save()
    #                 rec.mrp_production_id.button_mark_done()
    #             else:
    #                 raise UserError(_('Unavailability of components, please create supply orders'))


class MrpPlanningDays(models.Model):
    _name = "mrp.planning.days"
    _rec_name = "name"

    name = fields.Char(_("Day"))
    date = fields.Date(_("Full Date"))