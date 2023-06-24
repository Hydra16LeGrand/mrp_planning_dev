# -*- coding: utf-8 -*-

from . import models
from odoo import api, SUPERUSER_ID

# def update_mrp_days():
# 	print("Update mrp_days exec")
# 	env = api.Environment(cr, SUPERUSER_ID, {})

# 	mrp_days = env['mrp.planning.days'].search([])
# 	if not mrp_days:
# 		week_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# 		mrp_days.create([{
# 				'name': day
# 			} for day in week_days])
# 		print("Days", mrp_days)