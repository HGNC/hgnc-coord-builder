"""Shared test fixtures for the HGNC coordinate builder.

Postgres and MySQL fixtures are inherited from the root tests/conftest.py
via the session-scoped testcontainers fixtures. Import them when needed::

    from tests.conftest import postgres_db, mysql_connection

These fixtures are used for repository-layer integration tests only
(@pytest.mark.integration @pytest.mark.db).
"""
