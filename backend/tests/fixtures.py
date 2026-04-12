from types import SimpleNamespace

import pytest
import app.s3.index_refresh as index_module

@pytest.fixture
def key_1():
    return "pigpen/venus/MagellanSAR_FMap_Mosaics/Venus_Magellan_LeftLook_mosaic_global_75m.jp2"

@pytest.fixture
def keywords_1():
    return ['mosaic', 'global', 'venus', 'LeftLook', 'pigpen', 'Magellan', 'Mosaics', 'jp2', 'MagellanSAR', 'Venus', 'FMap', '75m']

@pytest.fixture
def fake_s3_success(monkeypatch):
    """
    Fixture that patches get_public_client() to return an object whose get_object
    returns a response with Body.read() -> bytes of UTF-8 text.
    """
    class FakeBody:
        def __init__(self, data: bytes):
            self._data = data
        def read(self):
            return self._data

    class FakeS3Client:
        def __init__(self, data: bytes):
            self._data = data
        def get_object(self, Bucket, Key):
            return {"Body": FakeBody(self._data)}

    def _create(data: bytes):
        client = FakeS3Client(data)
        monkeypatch.setattr(index_module, "get_public_client", lambda: client)
        return client

    return _create

@pytest.fixture
def fake_s3_failure(monkeypatch):
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

class FakePage:
    def __init__(self, text):
        self._text = text
    def get_text(self, mode):
        assert mode == "text"
        return self._text

class FakePDF:
    def __init__(self, pages):
        self._pages = pages
    def __iter__(self):
        return iter(self._pages)