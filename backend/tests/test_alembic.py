import os
from pathlib import Path
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.base import Base


def test_alembic_config_exists():
    """Verifies that alembic.ini exists and resolves the migration script directory."""
    backend_dir = Path(__file__).resolve().parent.parent
    ini_path = backend_dir / "alembic.ini"
    assert ini_path.exists(), "alembic.ini does not exist in backend/"

    config = Config(str(ini_path))
    script_dir = ScriptDirectory.from_config(config)
    assert script_dir is not None
    assert Path(script_dir.dir).resolve() == (backend_dir / "alembic").resolve()


def test_alembic_metadata_contains_base():
    """Verifies that target_metadata in Alembic is bound to the KISANQUEUE Base metadata."""
    assert Base.metadata is not None
    assert hasattr(Base.metadata, "tables")
