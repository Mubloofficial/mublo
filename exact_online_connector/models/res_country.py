# -*- coding: utf-8 -*-
# Copyright (c) 2022 Callista BV <https://www.callista.be>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResCountry(models.Model):
    _name = "res.country"
    _inherit = ["res.country", "exact.data.mixin"]

    exact_online_code = fields.Char(compute="_compute_exact_online_code", store=True)

    @api.depends("code")
    def _compute_exact_online_code(self):
        for country in self:
            if country.code:
                country.exact_online_code = country.code.upper()
            else:
                _logger.error(
                    "Country %s does not have a code, this will give errors when "
                    "syncing with Exact Online",
                    country.display_name,
                )
                country.exact_online_code = ""
