import base64
import csv
import io
import logging
from typing import Union

from markupsafe import Markup

from odoo import api, models

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
    ) -> str:
        """
        Export records from an Odoo model as a file attached to the current thread.

        Parameters:
            model: Technical name of the Odoo model to export (e.g. 'res.partner')
            fields: Fields to include. Exports all stored scalar fields if empty.
            domain: Filter domain (list of [field, operator, value] triples)
            limit: Maximum number of records to export (default 500)
            format: Output format — 'csv' (default). More formats coming soon.
        """
        if format not in FORMATS:
            return f"Unsupported format '{format}'. Supported: {', '.join(FORMATS)}."

        # [SEC] Block sensitive models before touching env
        if model in _BLOCKED_MODELS:
            return f"Export of '{model}' is not permitted."

        message = self.env.context.get("message")
        if not message or message.model != "llm.thread":
            return "Error: this tool must be called from within an LLM thread."

        thread = self.env["llm.thread"].browse(message.res_id)
        if not thread.exists():
            return "Error: thread not found."

        # [SEC] search_read runs as the calling user — Odoo's ACL enforces field/record access
        model_obj = self.env[model]

        if not fields:
            fields = self._get_default_fields(model_obj)

        records = model_obj.search_read(domain=domain, fields=fields, limit=limit)
        if not records:
            return f"No records found in '{model}' matching the given criteria."

        flat_records = [self._flatten_record(r) for r in records]

        mimetype, ext = FORMATS[format]
        content, encoding = self._render(flat_records, format)
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

    def _render(self, records: list[dict], format: str) -> tuple:
        """Dispatch to the format-specific renderer. Returns (content, encoding)."""
        return getattr(self, f"_render_{format}")(records)

    def _render_csv(self, records: list[dict]) -> tuple:
        if not records:
            return "", "utf-8"
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
        return buf.getvalue(), "utf-8"

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

    def _flatten_record(self, record: dict) -> dict:
        return {key: self._flatten_value(value) for key, value in record.items()}

    def _flatten_value(self, value):
        if value is False or value is None:
            return ""
        # many2one: [id, display_name] → id (re-importable)
        if isinstance(value, list) and len(value) == 2 and isinstance(value[0], int):
            return value[0]
        # many2many: [id, id, ...] → comma-joined ids
        if isinstance(value, list):
            return ",".join(str(v) for v in value)
        # [SEC] Prefix formula-injection characters so spreadsheets treat them as text
        if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
            return "'" + value
        return value
