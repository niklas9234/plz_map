import os

import pytest

from app.database import create_database_engine
from app.models import Base


def pytest_generate_tests(metafunc):
    if "database_engine" in metafunc.fixturenames:
        urls = [("sqlite", "sqlite+pysqlite:///:memory:")]
        if os.environ.get("TEST_POSTGRESQL_URL"):
            urls.append(("postgresql", os.environ["TEST_POSTGRESQL_URL"]))
        metafunc.parametrize("database_engine", [url for _, url in urls], ids=[name for name, _ in urls], indirect=True)


@pytest.fixture
def database_engine(request):
    engine = create_database_engine(request.param)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()
