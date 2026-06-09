import base64
import csv
import io
import logging
from typing import Union

from markupsafe import Markup

from odoo import api, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

FORMATS = {
    "csv": ("text/csv", "csv"),
}

# Models that must never be exported regardless of user permissions.
# Prompt injection could otherwise exfiltrate credentials or secrets.
_BLOCKED_MODELS = frozenset({
    "res.users",
    "res.users.apikeys",
    "res.users.log",
    "ir.config_parameter",
    "ir.mail_server",
    "fetchmail.server",
    "ir.logging",
    "mail.notification",
    "auth.totp.device",
})

# Field name patterns that may hold secrets and must be excluded from
# the auto-detected default field list.
_BLOCKED_FIELD_NAMES = frozenset({
    "password",
    "password_crypt",
    "new_password",
    "totp_secret",
    "api_key",
    "oauth_access_token",
    "oauth_refresh_token",
    "webhook_secret",
    "private_key",
    "certificate",
    "smtp_pass",
    "proxy_pass",
})

# Characters that spreadsheet apps interpret as formula prefixes.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class LLMToolExport(models.Model):
    _inherit = "llm.tool"

    @api.model
    def _get_available_implementations(self):
        implementations = super()._get_available_implementations()
        return implementations + [("odoo_export", "Odoo Export")]

    def odoo_export_execute(
        self,
        model: str,
        fields: list[str] = [],  # noqa: B006
        domain: list[list[Union[str, int, bool, float, None]]] = [],  # noqa: B006
        limit: int = 500,
        format: str = "csv",
        mode: str = "human",
    ) -> str:
        """
        Export records from an Odoo model as a file attached to the current thread.

        Parameters:
            model: Technical name of the Odoo model to export (e.g. 'res.partner')
            fields: Fields to include. Exports all stored scalar fields if empty.
                Relational fields can be traversed with '/' (e.g. 'partner_id/country_id/name').
            domain: Filter domain (list of [field, operator, value] triples)
            limit: Maximum number of records to export (default 500)
            format: Output format — 'csv' (default). More formats coming soon.
            mode: 'human' (default) for readable labels; 'import' for Odoo-importable
                external IDs that allow the file to be re-uploaded to update records.
        """
        if format not in FORMATS:
            return f"Unsupported format '{format}'. Supported: {', '.join(FORMATS)}."

        if mode not in ("human", "import"):
            return "Unsupported mode '{mode}'. Use 'human' or 'import'."

        # [SEC] Block sensitive models before touching env
        if model in _BLOCKED_MODELS:
            return f"Export of '{model}' is not permitted."

        message = self.env.context.get("message")
        if not message or message.model != "llm.thread":
            return "Error: this tool must be called from within an LLM thread."

        thread = self.env["llm.thread"].browse(message.res_id)
        if not thread.exists():
            return "Error: thread not found."

        if model not in self.env:
            return f"Error: unknown model '{model}'."

        # [SEC] Runs as the calling user — Odoo's ACL enforces model/field/record access,
        # and export_data() additionally requires the 'base.group_allow_export' group.
        model_obj = self.env[model]

        if not fields:
            fields = self._get_default_fields(model_obj)

        import_compat = mode == "import"

        try:
            records = model_obj.search(domain, limit=limit)
            if not records:
                return f"No records found in '{model}' matching the given criteria."
            rows = records.with_context(import_compat=import_compat).export_data(fields)["datas"]
        except AccessError:
            return (
                "You don't have permission to export this data. "
                "Exporting requires the 'Allowed to export' access right."
            )
        except (UserError, ValueError) as exc:
            return f"Export failed: {exc}"

        # import mode: keep raw field paths as headers — they're what Odoo's importer expects.
        # human mode: resolve to readable labels (e.g. "Partner / Country / Name").
        headers = fields if import_compat else self._get_headers(model_obj, fields)

        mimetype, ext = FORMATS[format]
        content, encoding = self._render(headers, rows, format)
        filename = f"{model.replace('.', '_')}_export.{ext}"

        # [SEC] No sudo — attachment is created as the calling user
        attachment = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(content if isinstance(content, bytes) else content.encode(encoding)),
            "mimetype": mimetype,
            "res_model": "llm.thread",
            "res_id": thread.id,
        })

        thread.message_post(
            body=Markup("📎 Export: <b>{}</b> ({} records)").format(filename, len(records)),
            attachment_ids=[attachment.id],
            llm_role="assistant",
        )

        return (
            f"Exported {len(records)} records from '{model}' to '{filename}'. "
            f"The file has been attached to this conversation."
        )

    def _render(self, headers: list[str], rows: list[list], format: str) -> tuple:
        """Dispatch to the format-specific renderer. Returns (content, encoding)."""
        return getattr(self, f"_render_{format}")(headers, rows)

    def _render_csv(self, headers: list[str], rows: list[list]) -> tuple:
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([self._sanitize_cell(cell) for cell in row])
        return buf.getvalue(), "utf-8"

    def _sanitize_cell(self, value):
        if value is None or value is False:
            return ""
        if isinstance(value, bytes):
            value = value.decode()
        # [SEC] Prefix formula-injection characters so spreadsheets treat them as text
        if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
            return "'" + value
        return value

    def _get_headers(self, model_obj, fields: list[str]) -> list[str]:
        """Human-readable column labels, resolving '/'-separated relational paths."""
        return [self._field_path_label(model_obj, path) for path in fields]

    def _field_path_label(self, model_obj, path: str) -> str:
        labels = []
        current = model_obj
        for part in path.split("/"):
            field = current._fields.get(part)
            if field is None:
                labels.append(part)
                break
            labels.append(field.string or part)
            if field.relational:
                current = self.env[field.comodel_name]
            else:
                break
        return " / ".join(labels)

    def _get_default_fields(self, model_obj):
        """Return stored scalar field names, excluding known sensitive field names."""
        return [
            name
            for name, field in model_obj._fields.items()
            if field.store
            and field.type not in ("one2many", "many2many", "binary")
            and not name.startswith("_")
            and name not in _BLOCKED_FIELD_NAMES
        ]
