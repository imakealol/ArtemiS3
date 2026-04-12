from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
import app.s3.index_refresh as index_module



#####################
# Mock Values
#####################


@pytest.fixture
def key_1():
    return "pigpen/venus/MagellanSAR_FMap_Mosaics/Venus_Magellan_LeftLook_mosaic_global_75m.jp2"

@pytest.fixture
def keywords_1():
    return ['mosaic', 'global', 'venus', 'LeftLook', 'pigpen', 'Magellan', 'Mosaics', 'jp2', 'MagellanSAR', 'Venus', 'FMap', '75m']

@pytest.fixture
def text_content():
    return "All data in the these downloads are within the public domain and optional credit for the data can be assigned to NASA"

@pytest.fixture
def text_keywords():
    return ['All', 'data', 'in', 'the', 'these', 'downloads', 'are', 'within', 'the', 'public', 'domain', 'and', 'optional', 'credit', 'for', 'the', 'data', 'can', 'be', 'assigned', 'to', 'NASA']


######################
# Function mocks
######################

@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    # Provide fake URLs so meilisearch.Client and psycopg.connect are constructed with deterministic args
    monkeypatch.setenv("MEILISEARCH_URL", "http://fake-meili")
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake-db")
    yield

@pytest.fixture
def fake_meili_client():
    client = MagicMock()
    # index(...).delete_document(...) should exist
    index_mock = MagicMock()
    client.index.return_value = index_mock
    yield client

@pytest.fixture
def fake_db_conn():
    # Mock connection and cursor used with context managers
    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.__enter__.return_value = conn
    # psycopg.connect(...) should return a context manager that yields conn
    return conn, cursor

@pytest.fixture
def mock_s3_success(monkeypatch):
    """
    Fixture that patches get_public_client() to return an object whose get_object
    returns a response with Body.read() -> bytes of UTF-8 text.
    """
    class MockBody:
        def __init__(self, data: bytes):
            self._data = data
        def read(self):
            return self._data

    class MockS3Client:
        def __init__(self, data: bytes):
            self._data = data
        def get_object(self, Bucket, Key):
            return {"Body": MockBody(self._data)}

    def _create(data: bytes):
        client = MockS3Client(data)
        monkeypatch.setattr(index_module, "get_public_client", lambda: client)
        return client

    return _create

@pytest.fixture
def mock_s3_failure(monkeypatch):
    """
    Fixture that patches get_public_client() to return a client whose get_object
    raises an exception to trigger the except branch.
    """
    class FailingS3Client:
        def get_object(self, Bucket, Key):
            raise RuntimeError("S3 failure")

    def _apply():
        monkeypatch.setattr(index_module, "get_public_client", lambda: FailingS3Client())
        return FailingS3Client()

    return _apply

@pytest.fixture
def spy_get_keywords(monkeypatch):
    """
    Fixture to replace get_keywords_from_key with a spy that records calls and returns a predictable list.
    Provide a helper to set return value.
    """
    calls = []
    return_value = []

    def _set_return(val):
        nonlocal return_value
        return_value = val

    def _spy(arg):
        calls.append(arg)
        # return a shallow copy to avoid mutation surprises
        return list(return_value)

    monkeypatch.setattr(index_module, "get_keywords_from_key", _spy)

    return SimpleNamespace(set_return=_set_return, calls=calls)


######################
# Mock Classes
######################

class MockPage:
    def __init__(self, text):
        self._text = text
    def get_text(self, mode):
        assert mode == "text"
        return self._text

class MockPDF:
    def __init__(self, pages):
        self._pages = pages
    def __iter__(self):
        return iter(self._pages)