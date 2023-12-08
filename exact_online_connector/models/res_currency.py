# -*- coding: utf-8 -*-
# Copyright (c) 2022 Callista BV <https://www.callista.be>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCurrency(models.Model):
    _name = "res.currency"
    _inherit = ["res.currency", "exact.data.mixin"]

    exact_online_code = fields.Char("Exact Online Code", related="name")
