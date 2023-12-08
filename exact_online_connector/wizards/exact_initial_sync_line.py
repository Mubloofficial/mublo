# -*- coding: utf-8 -*-
# Copyright (c) 2022 Callista BV <https://www.callista.be>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json

from odoo import _, fields, models
from odoo.exceptions import UserError


# This is not a transient model to keep the state of the initial sync when the
# users want to do it in multiple steps
class ExactInitialSyncLineValid(models.Model):
    _name = "exact.initial_sync.line"
    _description = "Exact online initial sync line"
    _order = (
        "in_odoo desc, journal_id, account_id, tax_id, payment_term_id, "
        "partner_id, exact_online_code"
    )

    sync_id = fields.Many2one("exact.initial_sync", required=True, ondelete="cascade")
    journal_id = fields.Many2one("account.journal")
    account_id = fields.Many2one("account.account")
    tax_id = fields.Many2one("account.tax")
    payment_term_id = fields.Many2one("account.payment.term")
    partner_id = fields.Many2one("res.partner")
    name_in_odoo = fields.Char(readonly=True)
    name_in_exact = fields.Char(readonly=True)
    in_odoo = fields.Boolean(readonly=True)
    in_exact = fields.Boolean(readonly=True)
    exact_online_code = fields.Char()
    invalid = fields.Boolean()
    reason = fields.Selection(
        [
            ("no_code", "No Exact Online Code defined"),
            ("not_odoo", "Not in Odoo"),
            ("not_exact", "Not in Exact Online"),
        ],
        readonly=True,
    )
    data = fields.Text()

    def action_update(self):
        """Updates invalid lines with the entered Exact Online Code"""
        for line in self.filtered(lambda i: i.invalid):
            line = line.with_company(line.sync_id.company_id.id)
            if (
                line.reason in ["no_code", "not_odoo", "not_exact"]
                and line.exact_online_code
            ):
                if line.journal_id and (
                    line.reason in ["no_code", "not_odoo"]
                    or (
                        line.reason == "not_exact"
                        and line.journal_id.exact_online_code != line.exact_online_code
                    )
                ):
                    line.journal_id.exact_online_code = line.exact_online_code
                    line.invalid = False
                elif line.tax_id and (
                    line.reason in ["no_code", "not_odoo"]
                    or (
                        line.reason == "not_exact"
                        and line.tax_id.exact_online_code != line.exact_online_code
                    )
                ):
                    line.tax_id.exact_online_code = line.exact_online_code
                    line.invalid = False
                elif line.payment_term_id and (
                    line.reason in ["no_code", "not_odoo"]
                    or (
                        line.reason == "not_exact"
                        and line.payment_term_id.exact_online_code
                        != line.exact_online_code
                    )
                ):
                    line.payment_term_id.exact_online_code = line.exact_online_code
                    line.invalid = False
                elif line.partner_id and (
                    line.reason in ["no_code", "not_odoo"]
                    or (
                        line.reason == "not_exact"
                        and line.partner_id.exact_online_code != line.exact_online_code
                    )
                ):
                    line.partner_id.exact_online_code = line.exact_online_code
                    line.invalid = False

    def action_archive(self):
        for line in self.filtered(lambda i: i.invalid):
            if line.reason in ["no_code", "not_exact"]:
                if line.journal_id:
                    line.journal_id.toggle_active()
                    line.invalid = line.journal_id.active
                elif line.account_id:
                    line.account_id.toggle_active()
                    line.invalid = line.account_id.active
                elif line.tax_id:
                    line.tax_id.toggle_active()
                    line.invalid = line.tax_id.active
                elif line.payment_term_id:
                    line.payment_term_id.toggle_active()
                    line.invalid = line.payment_term_id.active
                elif line.partner_id:
                    line.partner_id.toggle_active()
                    line.invalid = line.partner_id.active

    def action_remove(self):
        for line in self.filtered(lambda i: i.invalid):
            if line.reason in ["no_code", "not_exact"]:
                if line.journal_id:
                    line.journal_id.unlink()
                    line.unlink()
                elif line.account_id:
                    line.account_id.unlink()
                    line.unlink()
                elif line.tax_id:
                    line.tax_id.unlink()
                    line.unlink()
                elif line.payment_term_id:
                    line.payment_term_id.unlink()
                    line.unlink()
                elif line.partner_id:
                    line.partner_id.unlink()
                    line.unlink()

    def action_try_match(self):
        # TODO: performance, searching for each individual line takes a long time,
        #  maybe read everything first > potential memory problem
        Journals = self.env["account.journal"]
        Accounts = self.env["account.account"]
        Taxes = self.env["account.tax"]
        PaymentTerms = self.env["account.payment.term"]
        Partners = self.env["res.partner"]
        domain = []
        if self:
            domain = self[0].sync_id.get_relevant_domain()
        for line in self.filtered(lambda i: i.invalid):
            if line.reason in "not_odoo":
                if line.name_in_exact:
                    if line.sync_id.state == "journals":
                        line.journal_id = Journals.search(
                            domain
                            + [
                                "|",
                                ("name", "ilike", line.name_in_exact),
                                ("code", "ilike", line.name_in_exact),
                            ],
                            limit=1,
                        )
                        if line.journal_id in line.sync_id.valid_line_ids.mapped(
                            "journal_id"
                        ):
                            line.journal_id = None
                        if line.journal_id:
                            line.action_update()
                    elif line.sync_id.state == "accounts":
                        line.account_id = Accounts.search(
                            domain + [("name", "ilike", line.name_in_exact)], limit=1
                        )
                        if line.account_id in line.sync_id.valid_line_ids.mapped(
                            "account_id"
                        ):
                            line.account_id = None
                        if line.account_id:
                            line.action_update()
                    elif line.sync_id.state == "taxes":
                        line.tax_id = Taxes.search(
                            domain
                            + [
                                ("name", "ilike", line.name_in_exact),
                                ("exact_online_code", "=", False),
                            ],
                            limit=1,
                        )
                        if line.tax_id in line.sync_id.valid_line_ids.mapped("tax_id"):
                            line.tax_id = None
                        if line.tax_id:
                            line.action_update()
                    elif line.sync_id.state == "payment_terms":
                        line.payment_term_id = PaymentTerms.search(
                            domain
                            + [
                                ("name", "=", line.name_in_exact),
                                ("exact_online_code", "=", False),
                            ],
                            limit=1,
                        )
                        if line.payment_term_id:
                            line.action_update()
                    elif line.sync_id.state == "contacts":
                        line.partner_id = Partners.search(
                            domain
                            + [
                                ("name", "=", line.name_in_exact),
                                ("exact_online_code", "=", False),
                            ],
                            limit=1,
                        )
                        if line.partner_id:
                            line.action_update()

    def action_import(self):
        partners_to_create = []
        Country = self.env["res.country"]
        Currency = self.env["res.currency"]
        Partner = self.env["res.partner"]
        country_mapping = {}
        currency_mapping = {}
        available_langs = [l[0] for l in self.env["res.lang"].get_installed()]
        for line in self:
            if line.reason == "not_odoo" and line.exact_online_code:
                if line.sync_id.state in ["contacts"]:
                    vals = json.loads(line.data)
                    if vals.get("country_id.exact_online_code"):
                        if vals["country_id.exact_online_code"] not in country_mapping:
                            country_mapping[
                                vals["country_id.exact_online_code"]
                            ] = Country.search(
                                [
                                    (
                                        "exact_online_code",
                                        "=",
                                        vals["country_id.exact_online_code"],
                                    )
                                ],
                                limit=1,
                            )
                        vals["country_id"] = country_mapping[
                            vals["country_id.exact_online_code"]
                        ].id
                        del vals["country_id.exact_online_code"]
                    if vals.get("currency_id.exact_online_code"):
                        if (
                            vals["currency_id.exact_online_code"]
                            not in currency_mapping
                        ):
                            currency_mapping[
                                vals["currency_id.exact_online_code"]
                            ] = Currency.search(
                                [
                                    (
                                        "exact_online_code",
                                        "=",
                                        vals["currency_id.exact_online_code"],
                                    )
                                ],
                                limit=1,
                            )
                        vals["currency_id"] = currency_mapping[
                            vals["currency_id.exact_online_code"]
                        ].id
                        del vals["currency_id.exact_online_code"]
                    if vals.get("lang"):
                        if vals["lang"] not in available_langs:
                            vals["lang"] = self.env.user.lang
                    if vals.get("customer") or vals.get("customer_rank"):
                        vals["customer_rank"] = 1
                    if vals.get("supplier") or vals.get("supplier_rank"):
                        vals["supplier_rank"] = 1
                    names_to_remove = []
                    for field_name in vals.keys():
                        if field_name not in Partner._fields:
                            names_to_remove.append(field_name)
                    for field_name in names_to_remove:
                        del vals[field_name]
                    partners_to_create.append(vals)
        if partners_to_create:
            Partner.with_context(exact_no_sync=True).create(partners_to_create)

    def action_export(self):
        # TODO: fine tune this, transactions will be queued but this won't mean that
        #  the next time we check everything these records will already be in Exact
        #  (maybe provide some sort of "forced mechanism"?)
        for line in self:
            if line.reason in ["no_code", "no_exact"] and not line.exact_online_code:
                if line.partner_id:
                    line.partner_id.exact_create_transaction(
                        companies=line.sync_id.company_id, initial=True
                    )

    def get_ids(self):
        sync_ids = self.mapped("sync_id")
        if len(sync_ids) != 1:
            raise UserError(_("Can only get ids of a single initial sync"))
        if sync_ids.state == "journals":
            return self.mapped("journal_id").ids
        elif sync_ids.state == "accounts":
            return self.mapped("account_id").ids
        elif sync_ids.state == "taxes":
            return self.mapped("tax_id").ids
        elif sync_ids.state == "payment_terms":
            return self.mapped("payment_term_id").ids
        elif sync_ids.state == "contacts":
            return self.mapped("partner_id").ids
        return []
