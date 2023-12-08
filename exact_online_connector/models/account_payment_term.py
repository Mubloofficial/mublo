# -*- coding: utf-8 -*-
# Copyright (c) 2022 Callista BV <https://www.callista.be>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountPaymentTerm(models.Model):
    _name = "account.payment.term"
    _inherit = ["account.payment.term", "exact.data.mixin"]
