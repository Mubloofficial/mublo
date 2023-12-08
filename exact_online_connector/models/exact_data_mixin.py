# -*- coding: utf-8 -*-
# Copyright (c) 2022 Callista BV <https://www.callista.be>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ExactOnlineConnectorDataMixin(models.AbstractModel):
    _name = "exact.data.mixin"

    exact_online_code = fields.Char(
        help="The primary key used in Exact Online, this is usually a field name `Code`",
        copy=False,
    )
