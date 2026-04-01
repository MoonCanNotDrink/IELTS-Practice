import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


VERSIONS_DIR = Path(__file__).resolve().parent / "alembic" / "versions"


class FakeInspector:
    def __init__(self, tables=None, columns=None, indexes=None):
        self.tables = set(tables or [])
        self.columns = columns or {}
        self.indexes = indexes or {}

    def has_table(self, table_name):
        return table_name in self.tables

    def get_columns(self, table_name):
        return [{"name": name} for name in self.columns.get(table_name, [])]

    def get_indexes(self, table_name):
        return [{"name": name} for name in self.indexes.get(table_name, [])]


def load_migration(filename: str, module_name: str):
    fake_alembic = types.ModuleType("alembic")
    fake_alembic.op = MagicMock()

    previous = sys.modules.get("alembic")
    sys.modules["alembic"] = fake_alembic
    try:
        spec = importlib.util.spec_from_file_location(module_name, VERSIONS_DIR / filename)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            del sys.modules["alembic"]
        else:
            sys.modules["alembic"] = previous


class AlembicMigrationTests(unittest.TestCase):
    def test_auth_migration_creates_missing_schema_objects(self):
        module = load_migration(
            "20260327_0001_auth_email_password_reset.py",
            "migration_auth_create",
        )
        module.op = MagicMock()
        module.op.get_bind.return_value = object()
        inspector = FakeInspector(tables={"users"}, columns={"users": []}, indexes={"users": []})

        with patch.object(module.sa, "inspect", return_value=inspector):
            module.upgrade()

        self.assertEqual(module.op.add_column.call_count, 3)
        module.op.create_table.assert_called_once()
        self.assertEqual(module.op.create_index.call_count, 4)

    def test_auth_migration_skips_existing_schema_objects(self):
        module = load_migration(
            "20260327_0001_auth_email_password_reset.py",
            "migration_auth_skip",
        )
        module.op = MagicMock()
        module.op.get_bind.return_value = object()
        inspector = FakeInspector(
            tables={"users", "password_reset_tokens"},
            columns={
                "users": ["email", "email_verified_at", "token_version"],
            },
            indexes={
                "users": ["ix_users_email"],
                "password_reset_tokens": [
                    "ix_password_reset_tokens_user_id",
                    "ix_password_reset_tokens_expires_at",
                    "ix_password_reset_tokens_token_hash",
                ],
            },
        )

        with patch.object(module.sa, "inspect", return_value=inspector):
            module.upgrade()

        module.op.add_column.assert_not_called()
        module.op.create_table.assert_not_called()
        module.op.create_index.assert_not_called()

    def test_auth_migration_noops_without_legacy_users_table(self):
        module = load_migration(
            "20260327_0001_auth_email_password_reset.py",
            "migration_auth_legacy_missing",
        )
        module.op = MagicMock()
        module.op.get_bind.return_value = object()
        inspector = FakeInspector()

        with patch.object(module.sa, "inspect", return_value=inspector):
            module.upgrade()

        module.op.add_column.assert_not_called()
        module.op.create_table.assert_not_called()
        module.op.create_index.assert_not_called()

    def test_learning_loop_migration_skips_existing_columns(self):
        module = load_migration(
            "20260331_0002_recording_learning_loop_fields.py",
            "migration_learning_skip",
        )
        module.op = MagicMock()
        module.op.get_bind.return_value = object()
        inspector = FakeInspector(
            tables={"recordings"},
            columns={
                "recordings": [
                    "prompt_match_type",
                    "prompt_match_key",
                    "prompt_source",
                    "weakness_tags",
                    "coaching_payload",
                    "analysis_version",
                ]
            },
        )

        with patch.object(module.sa, "inspect", return_value=inspector):
            module.upgrade()

        module.op.add_column.assert_not_called()


if __name__ == "__main__":
    unittest.main()
