from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ModelLine(models.TransientModel):
    _name = "llm.fetch.models.line"
    _description = "LLM Model Import Line"
    _rec_name = "name"

    wizard_id = fields.Many2one(
        "llm.fetch.models.wizard",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        string="Model Name",
        required=True,
    )
    model_use = fields.Selection(
        selection="_get_available_model_usages",
        required=True,
        default="chat",
    )
    status = fields.Selection(
        [
            ("new", "New"),
            ("existing", "Existing"),
            ("modified", "Modified"),
        ],
        required=True,
        default="new",
    )
    selected = fields.Boolean(default=True)
    details = fields.Json()
    existing_model_id = fields.Many2one("llm.model")

    _sql_constraints = [
        (
            "unique_model_per_wizard",
            "UNIQUE(wizard_id, name)",
            "Each model can only be listed once per import.",
        )
    ]

    @api.model
    def _get_available_model_usages(self):
        return self.env["llm.model"]._get_available_model_usages()


class FetchModelsWizard(models.TransientModel):
    _name = "llm.fetch.models.wizard"
    _description = "Import LLM Models"

    provider_id = fields.Many2one(
        "llm.provider",
        required=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        "llm.fetch.models.line",
        "wizard_id",
        string="Models",
    )
    model_count = fields.Integer(
        compute="_compute_model_count",
        string="Models Found",
    )
    new_count = fields.Integer(
        compute="_compute_model_count",
        string="New Models",
    )
    modified_count = fields.Integer(
        compute="_compute_model_count",
        string="Modified Models",
    )

    @api.depends("line_ids", "line_ids.status")
    def _compute_model_count(self):
        """Compute various model counts for display"""
        for wizard in self:
            wizard.model_count = len(wizard.line_ids)
            wizard.new_count = len(
                wizard.line_ids.filtered(lambda record: record.status == "new")
            )
            wizard.modified_count = len(
                wizard.line_ids.filtered(lambda record: record.status == "modified")
            )

    def action_confirm(self):
        """Process selected models and create/update records"""
        self.ensure_one()
        Model = self.env["llm.model"]

        selected_lines = self.line_ids.filtered(
            lambda record: record.selected and record.name
        )
        if not selected_lines:
            raise UserError(_("Please select at least one model to import."))

        for line in selected_lines:
            values = {
                "name": line.name.strip(),
                "provider_id": self.provider_id.id,
                "model_use": line.model_use,
                "details": line.details,
                "active": True,
            }

            if line.existing_model_id:
                line.existing_model_id.write(values)
            else:
                Model.create(values)

        # Return success message
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _(
                    "%d models have been imported/updated.", len(selected_lines)
                ),
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
