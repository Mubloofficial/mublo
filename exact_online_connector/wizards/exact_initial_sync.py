# -*- coding: utf-8 -*-
# Copyright (c) 2022 Callista BV <https://www.callista.be>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


# This is not a transient model to keep the state of the initial sync when the
# users want to do it in multiple steps
class ExactInitialSync(models.Model):
    _name = "exact.initial_sync"
    _description = "Exact Online initial sync"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self._context.get("active_id"),
    )
    subscription_level = fields.Selection(
        related="company_id.exact_online_subscription_level", readonly=True
    )
    master = fields.Selection(
        [("odoo", "Odoo"), ("exact", "Exact Online")], default="odoo"
    )
    state = fields.Selection(
        [
            ("intro", "Intro"),
            ("journals", "Journals"),
            ("accounts", "Accounts"),
            ("taxes", "Taxes"),
            ("payment_terms", "Payment terms"),
            ("contacts", "Contacts"),
            ("moves", "Moves"),
            ("moves_initial", "Moves initial sync"),
            ("done", "Done"),
        ],
        "Status",
        default="intro",
        required=True,
    )
    line_ids = fields.One2many("exact.initial_sync.line", "sync_id")
    valid_line_ids = fields.One2many(
        "exact.initial_sync.line", "sync_id", domain=[("invalid", "=", False)]
    )
    valid_count = fields.Integer(
        compute="_compute_valid_count",
        help="The total number of valid records that exist in Odoo",
    )
    invalid_line_ids = fields.One2many(
        "exact.initial_sync.line", "sync_id", domain=[("invalid", "=", True)]
    )
    invalid_count = fields.Integer(
        compute="_compute_invalid_count",
        help="The total number of invalid records found in Odoo/Exact Online",
    )

    sync_start_date = fields.Date(default=fields.Date.context_today)
    journals_to_sync = fields.Many2many(
        "account.journal",
        string="Journals to sync with Exact Online",
        domain=[("type", "!=", "bank")],
    )
    moves_to_sync = fields.Integer(compute="_compute_moves_to_sync", readonly=True)
    moves_synced = fields.Boolean(readonly=True)

    can_update_invalid = fields.Boolean(compute="_compute_available_actions")
    can_archive_invalid = fields.Boolean(compute="_compute_available_actions")
    can_remove_invalid = fields.Boolean(compute="_compute_available_actions")
    can_import_invalid = fields.Boolean(compute="_compute_available_actions")
    can_export_invalid = fields.Boolean(compute="_compute_available_actions")
    can_go_to_next_step = fields.Boolean(compute="_compute_available_actions")
    can_do_initial_move_sync = fields.Boolean(compute="_compute_available_actions")

    @api.depends("valid_line_ids")
    def _compute_valid_count(self):
        for wizard in self:
            wizard.valid_count = len(wizard.valid_line_ids)

    @api.depends("invalid_line_ids")
    def _compute_invalid_count(self):
        for wizard in self:
            wizard.invalid_count = len(wizard.invalid_line_ids)

    @api.depends(
        "state",
        "invalid_line_ids",
        "invalid_line_ids.reason",
        "invalid_line_ids.in_odoo",
        "sync_start_date",
    )
    def _compute_available_actions(self):
        for wizard in self:
            update_available = False
            archive_available = False
            remove_available = False
            import_available = False
            export_available = False
            next_step_available = False
            initial_move_sync_available = False
            if any(
                wizard.invalid_line_ids.mapped(
                    lambda i: i.exact_online_code
                    and (
                        i.reason in ["no_code"]
                        or (
                            i.reason in ["not_odoo", "not_exact"]
                            and any(
                                getattr(i, f)
                                for f in [
                                    "journal_id",
                                    "tax_id",
                                    "payment_term_id",
                                    "partner_id",
                                ]
                            )
                        )
                    )
                )
            ):
                # Accounts are mapped on their actual code, so the user must update
                # the code of the account manually to be sure we do not alter the
                # accounting scheme automatically
                if wizard.state not in ["accounts"]:
                    update_available = True
            if any(
                wizard.invalid_line_ids.mapped(
                    lambda i: i.reason == "no_code" or i.reason == "not_exact"
                )
            ):
                # Accounts cannot be archived since they do not have an active field
                if wizard.state not in ["accounts"]:
                    archive_available = True
                remove_available = True
            if not any(wizard.invalid_line_ids.mapped(lambda i: i.in_odoo)):
                next_step_available = True
            if wizard.state in ["contacts"]:
                import_available = True
                if any(
                    wizard.invalid_line_ids.mapped(
                        lambda i: i.reason == "no_code" or i.reason == "not_exact"
                    )
                ):
                    export_available = True
            if wizard.state in ["init", "moves", "moves_initial"]:
                next_step_available = True
            if wizard.state == "done":
                next_step_available = False
            if wizard.state == "moves_initial":
                if (
                    wizard.sync_start_date <= fields.Date.today()
                    and wizard.journals_to_sync
                ):
                    initial_move_sync_available = True
            wizard.can_update_invalid = update_available
            wizard.can_archive_invalid = archive_available
            wizard.can_remove_invalid = remove_available
            wizard.can_import_invalid = import_available
            wizard.can_export_invalid = export_available
            wizard.can_go_to_next_step = next_step_available
            wizard.can_do_initial_move_sync = initial_move_sync_available

    @api.depends(
        "company_id",
        "journals_to_sync.sync_with_exact_online",
        "company_id.exact_online_sync_from",
    )
    def _compute_moves_to_sync(self):
        for wizard in self:
            wizard.moves_to_sync = self.env["account.move"].search_count(
                wizard.get_initial_move_sync_domain()
            )

    @api.model
    def get_step_order(self):
        return [s[0] for s in self._fields["state"].selection]

    def action_update_invalid(self):
        self.ensure_one()
        # We can only update the invalids since you can only enter a code for those
        self.invalid_line_ids.action_update()
        return self.load_step()

    def action_archive_invalid(self):
        self.ensure_one()
        self.invalid_line_ids.action_archive()
        return self.load_step()

    def action_remove_invalid(self):
        self.ensure_one()
        self.invalid_line_ids.action_remove()
        return self.load_step()

    def action_import_invalid(self):
        self.ensure_one()
        self.invalid_line_ids.action_import()
        return self.load_step()

    def action_export_invalid(self):
        self.ensure_one()
        self.invalid_line_ids.action_export()
        return self.load_step()

    def action_reload(self):
        return {
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "exact.initial_sync",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }

    def action_previous(self):
        self.ensure_one()
        order = self.get_step_order()
        index = order.index(self.state)
        if 0 < index:
            previous_step = order[index - 1]
        else:
            previous_step = "intro"
        return self.load_step(previous_step)

    def action_next(self):
        self.ensure_one()
        order = self.get_step_order()
        index = order.index(self.state)
        if index < len(order):
            next_step = order[index + 1]
        else:
            next_step = "done"
        return self.load_step(next_step)

    def action_recheck(self):
        return self.load_step()

    def load_step(self, next_step=False):
        self.ensure_one()
        if not next_step:
            next_step = self.state
        if self.state == "moves":
            self.company_id.exact_online_sync_from = self.sync_start_date
            self.journals_to_sync.write({"sync_with_exact_online": True})
        self.env.cr.commit()  # Prevent hang up when we update the state externally
        self.state = next_step
        if (
            self.state in ["moves", "moves_initial"]
            and self.company_id.exact_online_sync_from
        ):
            AccountJournal = self.env["account.journal"]
            journal_domain = AccountJournal.exact_get_subscription_level_domain(
                self.company_id
            )
            self.sync_start_date = self.company_id.exact_online_sync_from
            self.journals_to_sync = AccountJournal.search(
                journal_domain + [("sync_with_exact_online", "=", True)]
            )
        self.valid_line_ids = None
        self.invalid_line_ids = None
        if self.state in ["journals", "accounts", "taxes", "payment_terms", "contacts"]:
            self.determine_valid_invalid()
        if self.state == "done":
            response = self.company_id.call_exact(
                {
                    "model": "exact.init_done",
                }
            )
            if response.status_code in [502, 503, 504]:
                raise ValidationError(
                    _("The connector is temporarily offline, please try again later")
                )
        return self.action_reload()

    def get_initial_move_sync_domain(self):
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "posted"),
            ("journal_id.sync_with_exact_online", "=", True),
            ("exact_online_state", "=", "no"),
        ]
        if self.company_id.exact_online_sync_from:
            domain += [("date", ">=", self.company_id.exact_online_sync_from)]
        return domain

    def action_do_initial_move_sync(self):
        self.ensure_one()
        self.company_id.exact_online_sync_from = self.sync_start_date
        self.journals_to_sync.write({"sync_with_exact_online": True})
        self.env.cr.commit()  # Prevent hang up when we update the state externally
        # Search in chronological order, transactions should be created chronologically
        self.env["account.move"].search(
            self.get_initial_move_sync_domain(), order="date asc"
        ).exact_create_transaction(initial=True)
        self.moves_synced = True
        return self.action_reload()

    def get_relevant_model(self):
        if self.state == "journals":
            return "account.journal"
        elif self.state == "accounts":
            return "account.account"
        elif self.state == "taxes":
            return "account.tax"
        elif self.state == "payment_terms":
            return "account.payment.term"
        elif self.state == "contacts":
            return "res.partner"

    def get_relevant_domain(self):
        return []

    def get_data_in_odoo(self):
        return (
            self.env[self.get_relevant_model()]
            .with_company(self.company_id.id)
            .search(self.get_relevant_domain())
        )

    def get_data_from_exact(self):
        response = self.company_id.call_exact(
            {
                "model": "exact.{}".format(self.get_relevant_model()),
                "domain": self.get_relevant_domain(),
            }
        )
        if response.status_code == 200:
            result = json.loads(response.content.decode("utf-8"))
            if result and "result" in result:
                result = result["result"]
            if result.get("success", False):
                return result["data"]
            elif result.get("message"):
                raise ValidationError(result.get("message"))
            else:
                raise ValidationError(
                    result.get("error", {})
                    .get("data", {})
                    .get(
                        "message",
                        _("Something went wrong trying to contact Exact Online"),
                    )
                )
        if response.status_code in [502, 503, 504]:
            raise ValidationError(
                _("The connector is temporarily offline, please try again later")
            )
        raise ValidationError(
            _(
                "Could not get data from Exact Online, if your Connector is already connected, "
                "try again later. If not, connect it first"
            )
        )

    def determine_valid_invalid(self):
        in_exact = self.get_data_from_exact()
        in_odoo = self.get_data_in_odoo()
        existing_codes = []
        not_existing_codes = []
        non_existing_records = []
        create_vals = []
        for record in in_odoo:
            vals = {
                "sync_id": self.id,
                "name_in_odoo": record.display_name,
                "in_odoo": True,
                "in_exact": False,
                "exact_online_code": record.exact_online_code,
            }
            if self.state == "journals":
                vals["journal_id"] = record.id
                # Set the
                if record.type == "sale":
                    if self.subscription_level in ["standard", "advanced"]:
                        record.sync_with_exact_online = True
                elif record.type == "purchase":
                    if self.subscription_level in ["standard", "advanced"]:
                        record.sync_with_exact_online = True
            elif self.state == "accounts":
                vals["account_id"] = record.id
            elif self.state == "taxes":
                vals["tax_id"] = record.id
            elif self.state == "payment_terms":
                vals["payment_term_id"] = record.id
            elif self.state == "contacts":
                vals["partner_id"] = record.id
            if record.exact_online_code in in_exact.keys():
                vals.update(
                    {
                        "name_in_exact": in_exact[record.exact_online_code]["name"],
                        "in_exact": True,
                    }
                )
                create_vals.append(vals)
                existing_codes.append(record.exact_online_code)
            # Contacts may be queued for sync or the syncing might be in progress so
            # only flag records as invalid if they are in the 'no' state.
            elif (
                self.state in ["contacts"]
                and record.exact_online_state
                and record.exact_online_state != "no"
            ):
                vals.update(
                    {
                        "name_in_exact": _("Will be synced"),
                        "in_exact": True,
                    }
                )
                create_vals.append(vals)
            else:
                vals["invalid"] = True
                if record.exact_online_code:
                    vals["reason"] = "not_exact"
                else:
                    vals["reason"] = "no_code"
                self.invalid_line_ids |= self.invalid_line_ids.new(vals)
                non_existing_records.append(record)
        for code in in_exact:
            if code not in existing_codes:
                vals = {
                    "sync_id": self.id,
                    "name_in_exact": in_exact[code]["name"],
                    "exact_online_code": code,
                    "in_exact": True,
                    "in_odoo": False,
                    "invalid": True,
                    "reason": "not_odoo",
                    "data": json.dumps(in_exact[code]),
                }
                create_vals.append(vals)
                not_existing_codes.append(code)
        self.env["exact.initial_sync.line"].create(create_vals)
        self.valid_count = len(existing_codes)
        self.invalid_count = len(non_existing_records) + len(not_existing_codes)
        # TODO: maybe not do this for every possible state since it potentially
        #  takes a long time for accounts and customers/suppliers as well
        self.line_ids.filtered(lambda l: l.invalid).action_try_match()
        self.invalid_line_ids = self.line_ids.filtered(lambda l: l.invalid)
        self.valid_line_ids = self.line_ids.filtered(lambda l: not l.invalid)

    def action_open_records_tree(self):
        action = {}
        if self.state == "journals":
            action = self.env["ir.actions.actions"]._for_xml_id(
                "account.action_account_journal_form"
            )
        elif self.state == "accounts":
            action = self.env["ir.actions.actions"]._for_xml_id(
                "account.action_account_form"
            )
        elif self.state == "taxes":
            action = self.env["ir.actions.actions"]._for_xml_id(
                "account.action_tax_form"
            )
        elif self.state == "payment_terms":
            action = self.env["ir.actions.actions"]._for_xml_id(
                "account.action_payment_term_form"
            )
        elif self.state == "contacts":
            action = self.env["ir.actions.actions"]._for_xml_id(
                "base.action_partner_form"
            )
        if not action:
            return self.action_reload()
        action["domain"] = [("id", "in", self.invalid_line_ids.get_ids())]
        return action
