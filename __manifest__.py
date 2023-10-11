# -*- coding: utf-8 -*-
{
    'name': "mrp_planning",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'mrp',
        'hr',
        'stock',
        'stock_manager',
        'mrp_bom',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        'data/ir_sequence_data.xml',
        'data/planning_print.xml',

        'reports/planning_detail_template.xml',

        'wizard/replace_product_views.xml',
        'wizard/create_overview_wizard_view.xml',
        'wizard/mrp_immediate_production_inherit.xml',
        'wizard/create_picking_finished_product.xml',
        'wizard/calculating_packs_view.xml',
        'wizard/validate_production.xml',
        'wizard/initialize_operation_views.xml',

        'views/mrp_planning.xml',
        'views/mrp_section.xml',
        'views/mrp_team.xml',
        'views/mrp_packaging_line.xml',
        'views/stock_location_views.xml',
        'views/mrp_production_views.xml',

        'views/mrp_bom_views.xml',
        'views/mrp_plant.xml',
        'views/stock_picking_type_views.xml',
        'views/stock_quant_package_inherit.xml',
        'views/res_config_settings.xml',
        # 'views/menu_inheritance.xml',

    ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
