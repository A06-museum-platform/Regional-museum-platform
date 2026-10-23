import sys
from pathlib import Path

import pytest

# backend/ on sys.path so tests import `app.*` like the container does.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def _no_activity_log_in_fake_db_tests(request, monkeypatch):
    """Unit and permission tests run against fake sessions that only answer
    the SQL they expect. The activity log is a side effect with its own
    integration tests (tests/integration), so here it is a no-op."""
    if "integration" in Path(str(request.node.fspath)).parts:
        return
    from app.services import activity_service

    async def _skip(*_args, **_kwargs):
        return None

    monkeypatch.setattr(activity_service, "record", _skip)
