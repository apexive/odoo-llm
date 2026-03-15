import logging

from psycopg2.errors import UndefinedObject

_logger = logging.getLogger(__name__)


def pre_init_hook(env):
    """
    Initialize pgvector extension in PostgreSQL before module installation
    """
    _logger.info("Checking and installing pgvector extension...")

    # Get cursor from environment
    cr = env.cr

    # Try to check for the vector extension
    try:
        cr.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        if not cr.fetchone():
            try:
                _logger.info("Installing pgvector extension...")
                cr.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cr.commit()  # Commit the transaction to make this change permanent
                _logger.info("pgvector extension successfully installed")
            except Exception as e:
                _logger.error("Failed to create pgvector extension: %s", str(e))
                _logger.error(
                    "Please ensure pgvector is installed on your PostgreSQL server"
                )
                _logger.error(
                    "See: https://github.com/pgvector/pgvector for installation instructions"
                )
                raise Exception(
                    "Failed to install pgvector extension. "
                    "Is the pgvector extension installed on your PostgreSQL server? "
                    "See https://github.com/pgvector/pgvector for installation."
                ) from e
        else:
            _logger.info("pgvector extension is already installed")

        # Test if the vector type is actually available with proper syntax
        # Use a valid vector format (a simple 2D vector)
        try:
            cr.execute("SELECT '[1,2]'::vector")
            _logger.info("Vector type is working correctly")
        except UndefinedObject as e:
            _logger.error(
                "Vector type not available even though extension is installed"
            )
            raise Exception(
                "Vector type not available. Something is wrong with the pgvector installation."
            ) from e

    except Exception as e:
        if not isinstance(e, UndefinedObject):
            _logger.error("Unexpected error checking pgvector: %s", str(e))
            raise Exception(f"Unexpected error checking pgvector: {str(e)}") from e
        else:
            _logger.error("Vector extension is not available in the database")
            _logger.error(
                "Please install pgvector: https://github.com/pgvector/pgvector"
            )
            raise Exception(
                "Vector extension is not available. Please ensure pgvector is installed "
                "on your PostgreSQL server before installing this module."
            ) from e
