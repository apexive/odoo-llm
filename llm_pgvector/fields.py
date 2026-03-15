import logging

import numpy as np
from pgvector import Vector
from pgvector.psycopg2 import register_vector

from odoo import fields, tools

# v17: SENTINEL doesn't exist, use a simple sentinel object
class _Sentinel:
    pass

SENTINEL = _Sentinel()

_logger = logging.getLogger(__name__)


class PgVector(fields.Field):
    """PgVector field for Odoo, using pgvector extension for PostgreSQL.

    This field stores vector embeddings in PostgreSQL using the pgvector extension.

    :param int dimension: Optional dimension of the vector. If provided, the column
                          will be created with the specified dimension constraint.
    """

    type = "pgvector"
    column_type = ("vector", "vector")

    _slots = {
        "dimension": None,  # Vector dimensions
    }

    def __init__(
        self, string=SENTINEL, dimension=None, **kwargs
    ):
        super().__init__(string=string, dimension=dimension, **kwargs)

    def convert_to_column(self, value, record, values=None, validate=True):
        """Convert Python value to database format using pgvector.Vector."""
        if value is None:
            return None

        # Ensure the value is properly formatted for pgvector
        try:
            # Use Vector._to_db method from pgvector
            return Vector._to_db(value, self.dimension)
        except (ValueError, TypeError) as e:
            _logger.warning(f"Error converting vector: {e}. Returning NULL.")
            return None

    def convert_to_cache(self, value, record, validate=True):
        """Convert database value to cache format."""
        if value is None:
            return None

        # Handle case where value is already a list or numpy array
        if isinstance(value, list) or isinstance(value, np.ndarray):
            return value

        # Safely convert from database format
        try:
            # Use Vector._from_db method from pgvector for string values
            return Vector._from_db(value)
        except (ValueError, TypeError) as e:
            _logger.warning(f"Error converting vector from DB: {e}. Returning None.")
            return None

    def create_column(self, cr, table, column, **kwargs):
        """Create a vector column in the database."""
        # Register vector with this cursor
        register_vector(cr)

        # Specify dimensions if provided
        dim_spec = f"({self.dimension})" if self.dimension else ""

        # Create the column with appropriate vector dimensions
        cr.execute(f"""
            ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} vector{dim_spec}
        """)

        # Update the column format to match the dimensions
        tools.set_column_type(cr, table, column, f"vector{dim_spec}")
