# -*- coding: utf-8 -*-
# Copyright (c) 2022 Callista BV <https://www.callista.be>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountAccount(models.Model):
    _name = "account.account"
    _inherit = ["account.account", "exact.data.mixin"]

    exact_online_code = fields.Char("Exact Online Code", related="code")
