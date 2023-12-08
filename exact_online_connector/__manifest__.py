# -*- coding: utf-8 -*-
# Copyright (c) 2022 Callista BV <https://www.callista.be>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Exact Online Connector",
    "version": "14.0.1.1.0",
    "summary": "Sync Exact Online with Odoo",
    "category": "Accounting",
    "author": "Callista BV",
    "website": "https://www.callista.be",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "data/ir_cron_data.xml",
        "data/ir_config_parameter_data.xml",
        "data/mail_activity_data.xml",
        "security/res_groups_data.xml",
        "security/ir.model.access.csv",
        "views/menu_views.xml",
        "views/account_journal_views.xml",
        "views/account_payment_term_views.xml",
        "views/account_tax_views.xml",
        "views/exact_transaction_views.xml",
        "views/res_company_views.xml",
        "views/res_country_views.xml",
        "views/res_partner_views.xml",
        "wizards/exact_initial_sync_views.xml",
    ],
    "images": [
        "static/description/images/thumbnail.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
