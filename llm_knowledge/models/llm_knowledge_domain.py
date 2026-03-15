from odoo import api, fields, models


class LLMKnowledgeDomain(models.Model):
    _name = "llm.knowledge.domain"
    _description = "Collection Domain Filter"
    _order = "sequence, id"

    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
    )
    collection_id = fields.Many2one(
        "llm.knowledge.collection",
        string="Collection",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model_name = fields.Char(
        string="Model Name",
        related="model_id.model",
        store=True,
        readonly=True,
    )
    domain = fields.Char(
        string="Domain",
        default="[]",
        required=True,
        help="Domain filter to select records",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Order of application",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )

    @api.depends("model_id", "model_id.name")
    def _compute_name(self):
        """Compute a readable name for the domain filter"""
        for record in self:
            if record.model_id:
                record.name = f"{record.model_id.name} Domain"
            else:
                record.name = "Domain Filter"
