from odoo import _, fields, models
from odoo.exceptions import UserError


class LLMStoreCollection(models.AbstractModel):
    _name = "llm.store.collection"
    _description = "LLM Vector Store Collection"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, tracking=True)
    store_id = fields.Many2one(
        "llm.store",
        string="Vector Store",
        required=True,
        ondelete="restrict",
        tracking=True,
    )

    dimension = fields.Integer(
        tracking=True, help="Dimension of vectors in this collection"
    )

    vector_count = fields.Integer(
        tracking=True, help="Number of vectors in this collection"
    )

    metadata = fields.Json(string="Collection Metadata")

    description = fields.Text(tracking=True)

    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        (
            "unique_name_per_store",
            "UNIQUE(store_id, name)",
            "Collection names must be unique per store.",
        )
    ]

    def refresh_stats(self):
        """Update stats about this collection from the store"""
        # To be implemented by specific provider modules
        return True

    def delete_vectors(self, ids=None):
        """Remove all vectors from this collection"""
        if ids is None:
            ids = []
        if self.store_id:
            return self.store_id._delete_vectors(self.id, ids)
        return False

    def search_vectors(self, query_vector, limit=10, filter=None, **kwargs):
        """Search for similar vectors in this collection"""
        if self.store_id:
            return self.store_id._search_vectors(
                self.id, query_vector, limit=limit, filter=filter, **kwargs
            )
        return []

    def insert_vectors(self, vectors, metadata=None, ids=None, **kwargs):
        """Insert vectors into this collection"""
        if self.store_id:
            return self.store_id._insert_vectors(
                self.id, vectors, metadata=metadata, ids=ids, **kwargs
            )
        else:
            raise UserError(_("No store configured for this collection."))
