import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class LLMKnowledgeCollection(models.Model):
    _inherit = "llm.knowledge.collection"

    automated_sync = fields.Boolean(
        string="Automated Sync",
        default=False,
        help="When enabled, automated actions will be created to keep this collection "
        "synchronized with its domain filters.",
    )

    automation_ids = fields.One2many(
        "base.automation",
        "llm_collection_id",
        string="Automated Actions",
        help="Automated actions that keep this collection synchronized.",
    )

    auto_process_resources = fields.Boolean(
        string="Auto-Process Resources",
        default=True,
        help="Automatically process newly created resources through the RAG pipeline.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        collections = super().create(vals_list)
        for collection in collections:
            if collection.automated_sync and collection.domain_ids:
                collection.sync_automated_actions()
        return collections

    def write(self, vals):
        result = super().write(vals)

        # If automated_sync or domain_ids changed, sync automated actions
        sync_needed = (
            "automated_sync" in vals
            or "domain_ids" in vals
            or any(key.startswith("domain_ids.") for key in vals)
        )

        if sync_needed:
            for collection in self:
                if collection.automated_sync:
                    collection.sync_automated_actions()
                elif collection.automation_ids:
                    collection.automation_ids.unlink()

        return result

    def sync_automated_actions(self):
        """
        Create, update, or remove automated actions based on the collection's domain filters.
        """
        self.ensure_one()

        # If automated sync is not enabled, remove all automated actions and return
        if not self.automated_sync:
            if self.automation_ids:
                self.automation_ids.unlink()
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Automation Disabled"),
                        "message": _(
                            "All automated actions for this collection have been removed."
                        ),
                        "type": "info",
                    },
                }
            return

        created_count = 0
        updated_count = 0
        removed_count = 0

        # Get all active domain filters
        domain_filters = self.domain_ids.filtered(lambda d: d.active)

        # Define which triggers we'll create for each domain filter
        triggers = ["on_create", "on_write", "on_unlink"]

        # Track existing automations to find which ones to keep
        existing_automations = {
            (auto.model_id.id, auto.trigger): auto for auto in self.automation_ids
        }

        # Create/update automations for each domain filter and trigger
        for domain_filter in domain_filters:
            model_id = domain_filter.model_id.id

            for trigger in triggers:
                key = (model_id, trigger)

                # Prepare values for the automation
                vals = {
                    "name": _("RAG: %(collection)s - %(model)s (%(trigger)s)")
                    % {
                        "collection": self.name,
                        "model": domain_filter.model_id.name,
                        "trigger": dict(
                            self.env["base.automation"]._fields["trigger"].selection
                        )[trigger],
                    },
                    "model_id": model_id,
                    "trigger": trigger,
                    "state": "llm_update",
                    "llm_collection_id": self.id,
                    "filter_domain": "[]"
                    if trigger == "on_create"
                    else domain_filter.domain,
                    "active": domain_filter.active,
                    "llm_auto_process": self.auto_process_resources,
                }

                if key in existing_automations:
                    # Update existing automation
                    existing_automations[key].write(vals)
                    updated_count += 1
                    # Remove from the dict to track which ones to keep
                    del existing_automations[key]
                else:
                    # Create new automation
                    self.env["base.automation"].create(vals)
                    created_count += 1

        # Remove automations that no longer correspond to active domain filters
        if existing_automations:
            self.env["base.automation"].browse(
                [auto.id for auto in existing_automations.values()]
            ).unlink()
            removed_count = len(existing_automations)

        # Return notification with results
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Automated Actions Synchronized"),
                "message": _(
                    "Created: %(created)d, Updated: %(updated)d, Removed: %(removed)d"
                )
                % {
                    "created": created_count,
                    "updated": updated_count,
                    "removed": removed_count,
                },
                "type": "success",
            },
        }
