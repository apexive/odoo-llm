"""Lookup tools: find moves, accounts, and journals"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class AccountMoveLookup(models.Model):
    _name = "account.tool.lookup"
    _inherit = "account.tool.mixin"
    _description = "LLM tools for accounting lookups"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def account_find_moves(
        self,
        reference: Optional[str] = None,
        partner: Optional[str] = None,
        move_type: Optional[str] = None,
        state: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        payment_state: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """Find journal entries, invoices, or bills matching criteria

        Search for accounting documents using various filters. All filters
        are optional and combined with AND logic.

        Args:
            reference: Move name pattern (supports % wildcard, e.g. "INV/2025%")
            partner: Partner name, ref, or VAT
            move_type: Type filter: "invoice", "bill", "credit_note",
                       "refund", "entry", or Odoo types like "out_invoice"
            state: State filter: "draft", "posted", "cancel"
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            amount_min: Minimum total amount
            amount_max: Maximum total amount
            payment_state: Payment status: "not_paid", "partial", "paid",
                           "in_payment", "reversed"
            limit: Maximum results (default: 50)

        Returns:
            Dictionary with matching moves
        """
        from .account_move_entry import MOVE_TYPE_MAP

        domain = []

        if reference:
            if "%" in reference:
                domain.append(("name", "=like", reference))
            else:
                domain.append(("name", "=", reference))

        if partner:
            domain.append(("partner_id", "=", self._resolve_partner(partner).id))

        if move_type:
            odoo_type = MOVE_TYPE_MAP.get(move_type, move_type)
            domain.append(("move_type", "=", odoo_type))

        if state:
            domain.append(("state", "=", state))

        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))

        if amount_min is not None:
            domain.append(("amount_total", ">=", amount_min))
        if amount_max is not None:
            domain.append(("amount_total", "<=", amount_max))

        if payment_state:
            domain.append(("payment_state", "=", payment_state))

        moves = self.env["account.move"].search(
            domain, limit=limit, order="date desc, name desc"
        )

        result = []
        for move in moves:
            result.append(
                {
                    "id": move.id,
                    "name": move.name,
                    "move_type": move.move_type,
                    "state": move.state,
                    "date": str(move.date),
                    "partner": move.partner_id.name or "",
                    "journal": move.journal_id.code,
                    "ref": move.ref or "",
                    "amount_total": move.amount_total,
                    "amount_residual": move.amount_residual,
                    "payment_state": move.payment_state or "",
                }
            )

        return {
            "moves": result,
            "count": len(result),
        }

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def account_find_accounts(
        self,
        code: Optional[str] = None,
        name: Optional[str] = None,
        account_type: Optional[str] = None,
        reconcile: Optional[bool] = None,
        include_balance: bool = False,
        limit: int = 100,
    ) -> dict:
        """Find chart of accounts entries matching criteria

        Search for accounts by code pattern, name, or type. Optionally
        include current posted balance for each account.

        Args:
            code: Account code pattern (e.g. "6%" for all expense codes
                  starting with 6, or "111101" for exact match)
            name: Account name search (partial match)
            account_type: Type shortcut: "receivable", "payable", "bank",
                          "cash", "equity", "income", "expense", "asset",
                          "liability", or Odoo account_type value
            reconcile: Filter by reconcilable flag (True/False)
            include_balance: Include current posted balance (default: False)
            limit: Maximum results (default: 100)

        Returns:
            Dictionary with matching accounts
        """
        from .account_tool_mixin import ACCOUNT_TYPE_SHORTCUTS

        domain = []

        if code:
            if "%" in code:
                domain.append(("code", "=like", code))
            else:
                domain.append(("code", "=", code))

        if name:
            domain.append(("name", "ilike", name))

        if account_type:
            shortcut = account_type.lower()
            if shortcut in ACCOUNT_TYPE_SHORTCUTS:
                domain.extend(ACCOUNT_TYPE_SHORTCUTS[shortcut])
            else:
                domain.append(("account_type", "=", account_type))

        if reconcile is not None:
            domain.append(("reconcile", "=", reconcile))

        accounts = self.env["account.account"].search(domain, limit=limit, order="code")

        # Optionally compute balances
        balance_map = {}
        if include_balance and accounts:
            groups = self.env["account.move.line"]._read_group(
                domain=[
                    ("account_id", "in", accounts.ids),
                    ("parent_state", "=", "posted"),
                ],
                groupby=["account_id"],
                aggregates=["balance:sum"],
            )
            for account, balance_sum in groups:
                balance_map[account.id] = balance_sum

        result = []
        for account in accounts:
            data = {
                "id": account.id,
                "code": account.code,
                "name": account.name,
                "account_type": account.account_type,
                "reconcile": account.reconcile,
            }
            if include_balance:
                data["balance"] = balance_map.get(account.id, 0.0)
            result.append(data)

        return {
            "accounts": result,
            "count": len(result),
        }

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def account_find_journals(
        self,
        code: Optional[str] = None,
        name: Optional[str] = None,
        journal_type: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """Find accounting journals

        Search for journals by code, name, or type.

        Args:
            code: Journal code (exact match, case-insensitive)
            name: Journal name (partial match)
            journal_type: Journal type: "sale", "purchase", "cash",
                          "bank", "general"
            limit: Maximum results (default: 50)

        Returns:
            Dictionary with matching journals
        """
        domain = []

        if code:
            domain.append(("code", "=ilike", code))
        if name:
            domain.append(("name", "ilike", name))
        if journal_type:
            valid_types = ("sale", "purchase", "cash", "bank", "general")
            if journal_type.lower() not in valid_types:
                raise UserError(
                    _("Invalid journal type '%s'. Use: %s")
                    % (journal_type, ", ".join(valid_types))
                )
            domain.append(("type", "=", journal_type.lower()))

        journals = self.env["account.journal"].search(domain, limit=limit, order="code")

        result = []
        for journal in journals:
            result.append(
                {
                    "id": journal.id,
                    "code": journal.code,
                    "name": journal.name,
                    "type": journal.type,
                }
            )

        return {
            "journals": result,
            "count": len(result),
        }
