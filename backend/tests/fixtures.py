from unittest.mock import MagicMock
import pytest
import app.s3.index_refresh as index_module
import app.s3.refresh_status as refresh_module
import io
from unittest.mock import MagicMock



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
# Mocks
######################


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    monkeypatch.setenv("MEILISEARCH_URL", "http://127.0.0.1:7700")
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost/db")
    yield


@pytest.fixture
def mock_s3_client():
    s3 = MagicMock()
    # paginator returns iterable pages
    paginator = MagicMock()
    s3.get_paginator.return_value = paginator

    def paginate_side(Bucket, Prefix=""):
        # simulate two pages
        yield {"Contents": [{"Key": "a.txt", "Size": 10, "LastModified": __import__("datetime").datetime(2020,1,1), "StorageClass": "STANDARD"}]}
        yield {"Contents": [{"Key": "dir/", "Size": 0, "LastModified": __import__("datetime").datetime(2020,1,2)}]}
    paginator.paginate.side_effect = paginate_side

    # head_object
    s3.head_object.return_value = {"ContentType": "text/plain"}

    # get_object for text
    body = io.BytesIO(b"hello,world test_text")
    s3.get_object.return_value = {"Body": body}

    return s3


@pytest.fixture
def mock_meili_client():
    client = MagicMock()
    idx = MagicMock()
    client.index.return_value = idx
    client.create_index.return_value = {}
    return client


@pytest.fixture
def mock_psycopg(monkeypatch):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    # fetchall returns empty tags
    cur.fetchall.return_value = []
    # context manager for connect
    monkeypatch.setattr(index_module, "psycopg", MagicMock(connect=MagicMock(return_value=conn)))
    return conn, cur


@pytest.fixture
def status_mocks(monkeypatch):
    mocks = {name: MagicMock() for name in ["start_refresh", "set_status", "increment_listed", "increment_processed", "finish_refresh", "fail_refresh"]}
    for name, mock in mocks.items():
        monkeypatch.setattr(index_module, name, mock)
    return mocks


@pytest.fixture
def meili_helpers(monkeypatch):
    # patch get_all_indexes, get_all_documents, get_doc_id, guess_mime_type and s3 utils
    monkeypatch.setattr(index_module, "get_all_indexes", lambda: [])
    monkeypatch.setattr(index_module, "get_all_documents", lambda bucket, prefix: [])
    monkeypatch.setattr(index_module, "get_doc_id", lambda key: "hash-"+key)
    monkeypatch.setattr(index_module, "guess_mime_type", lambda ext: "text/plain")
    # s3 utils
    monkeypatch.setattr(index_module, "normalize_s3_path", lambda k: k)
    monkeypatch.setattr(index_module, "key_parent_path", lambda k: "parent")
    monkeypatch.setattr(index_module, "key_filename", lambda k: "file.txt")
    monkeypatch.setattr(index_module, "parent_ancestors", lambda p: ["parent"])
    monkeypatch.setattr(index_module, "path_depth", lambda p: 1)
    return True

@pytest.fixture(autouse=True)
def clear_state():
    # reset internal state before each test
    refresh_module._status_by_uri.clear()
    yield
    refresh_module._status_by_uri.clear()