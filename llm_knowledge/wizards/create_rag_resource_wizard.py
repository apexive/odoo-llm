from odoo import api, fields, models


class CreateRAGResourceWizard(models.TransientModel):
    _name = (
        "llm.create.rag.resource.wizard"  # Keep original name or rename if preferred
    )
    _description = "Create RAG Resources Wizard"

    record_count = fields.Integer(
        string="Records",
        readonly=True,
        compute="_compute_record_count",
    )
    # Field renamed for clarity to match view
    resource_name_template = fields.Char(
        string="Resource Name Template",
        default="{record_name}",
        help="Template for resource names. Use {record_name}, {model_name}, and {id} as placeholders.",
        required=True,
    )
    process_immediately = fields.Boolean(
        string="Process Immediately",
        default=False,
        help="If checked, resources will be immediately processed through the RAG pipeline",
    )
    state = fields.Selection(
        [
            ("confirm", "Confirm"),
            ("done", "Done"),
        ],
        default="confirm",
    )
    # Field renamed for clarity and target model changed
    created_resource_ids = fields.Many2many(
        "llm.resource",  # Target llm.resource
        string="Created Resources",
    )
    created_count = fields.Integer(string="Created", compute="_compute_created_count")

    @api.depends("created_resource_ids")
    def _compute_created_count(self):
        for wizard in self:
            wizard.created_count = len(wizard.created_resource_ids)

    @api.depends(
        "record_count"
    )  # Dependency should be correct, just checking context below
    def _compute_record_count(self):
        for wizard in self:
            active_ids = self.env.context.get("active_ids", [])
            wizard.record_count = len(active_ids)

    # Method renamed for clarity
    def action_create_resources(self):
        """Create RAG resources for selected records"""
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])

        if not active_model or not active_ids:
            return {"type": "ir.actions.act_window_close"}

        records = self.env[active_model].browse(active_ids)
        # Renamed variable
        model_desc = (
            self.env[active_model]._description
            or active_model.replace(".", " ").title()
        )

        # Get the ir.model record for this model
        # Renamed variable
        model_id_rec = self.env["ir.model"].search(
            [("model", "=", active_model)], limit=1
        )
        if not model_id_rec:
            # Consider raising UserError for better feedback
            return {"type": "ir.actions.act_window_close"}
        model_id = model_id_rec.id

        created_resources = self.env["llm.resource"]  # Target llm.resource

        for record in records:
            # Get record name - try different common name fields
            record_name = record.display_name
            if not record_name and hasattr(record, "name"):
                record_name = record.name
            if not record_name:
                record_name = f"{model_desc} #{record.id}"  # Use renamed variable

            # Format resource name using template
            # Use renamed field
            resource_name = self.resource_name_template.format(
                record_name=record_name,
                model_name=model_desc,  # Use renamed variable
                id=record.id,
            )

            create_vals = {
                "name": resource_name,
                "model_id": model_id,
                "res_id": record.id,
                # Collections are typically added via Upload or Domains,
                # but could be added here via context or wizard field if needed.
            }
            # Check context if action was triggered from a collection view
            if self.env.context.get("default_collection_id"):
                create_vals["collection_ids"] = [
                    (4, self.env.context.get("default_collection_id"))
                ]

            # Create RAG resource (llm.resource)
            resource = self.env["llm.resource"].create(
                create_vals
            )  # Target llm.resource

            # Process resource if requested (will trigger full RAG pipeline)
            if self.process_immediately:
                resource.process_resource()  # This method is overridden in llm_knowledge

            created_resources |= resource

        self.write(
            {
                "state": "done",
                "created_resource_ids": [
                    (6, 0, created_resources.ids)
                ],  # Use renamed field
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,  # Use self._name for correct wizard model
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }

    # Method renamed for clarity
    def action_view_resources(self):
        """Open the created resources"""
        return {
            "name": "Created RAG Resources",
            "type": "ir.actions.act_window",
            "res_model": "llm.resource",  # Target llm.resource
            "view_mode": "list,form,kanban",
            "domain": [
                ("id", "in", self.created_resource_ids.ids)
            ],  # Use renamed field
            # Use the specific views defined in llm_knowledge for llm.resource
            "view_ids": [
                (5, 0, 0),
                (
                    0,
                    0,
                    {
                        "view_mode": "kanban",
                        "view_id": self.env.ref(
                            "llm_knowledge.view_llm_resource_kanban"
                        ).id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "view_mode": "list",
                        "view_id": self.env.ref(
                            "llm_knowledge.view_llm_resource_tree"
                        ).id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "view_mode": "form",
                        "view_id": self.env.ref(
                            "llm_knowledge.view_llm_resource_form"
                        ).id,
                    },
                ),
            ],
            "search_view_id": [
                self.env.ref("llm_knowledge.view_llm_resource_search").id
            ],
        }
