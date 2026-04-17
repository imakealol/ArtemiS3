import types
import app.s3.index_refresh as module
from tests.fixtures import *

def test_config_index_settings_calls_update(monkeypatch, mock_meili_client):
    idx = MagicMock()
    module.config_index_settings(idx)
    idx.update_settings.assert_called_once_with(module.INDEX_SETTINGS)


def test_get_current_s3_objects_success(monkeypatch, mock_s3_client, status_mocks):
    monkeypatch.setattr(module, "get_public_client", lambda: mock_s3_client)
    objs = module.get_current_s3_objects("bucket", prefix="pfx", s3_uri="s3://u")
    # expect two objects from paginate
    assert isinstance(objs, list)
    assert any(o["Key"] == "a.txt" for o in objs)
    module.increment_listed.assert_called()  # increment_listed called for pages


def test_get_current_s3_objects_exception(monkeypatch, mock_s3_client):
    # make paginator.paginate raise
    paginator = MagicMock()
    paginator.paginate.side_effect = Exception("boom")
    mock_s3_client.get_paginator.return_value = paginator
    monkeypatch.setattr(module, "get_public_client", lambda: mock_s3_client)
    # should not raise
    objs = module.get_current_s3_objects("bucket")
    assert objs == []


def test_refresh_meili_index_creates_index(monkeypatch, mock_s3_client, mock_meili_client, meili_helpers, status_mocks, mock_psycopg):
    # scenario: no existing index -> create new index and add files
    monkeypatch.setattr(module, "get_public_client", lambda: mock_s3_client)
    monkeypatch.setattr(module, "get_all_indexes", lambda: [])
    monkeypatch.setattr(module, "meilisearch", MagicMock(Client=MagicMock(return_value=mock_meili_client)))
    # patch add_files_to_index to observe call
    called = {}
    def mock_add(index, files, s3_uri=None):
        called['args'] = (index, files, s3_uri)
    monkeypatch.setattr(module, "add_files_to_index", mock_add)
    module.refresh_meili_index("bucket", prefix="pfx", s3_uri="s3://u")
    assert called['args'][0] == "bucket"
    assert isinstance(called['args'][1], list)
    module.start_refresh.assert_called()


def test_refresh_meili_index_existing_index(monkeypatch, mock_s3_client, mock_meili_client, meili_helpers, status_mocks, mock_psycopg):
    # scenario: index exists -> use get_all_documents path
    monkeypatch.setattr(module, "get_public_client", lambda: mock_s3_client)
    monkeypatch.setattr(module, "get_all_indexes", lambda: [{"uid": "bucket"}])
    # previous documents include one with Key 'a.txt'
    mock_doc = types.SimpleNamespace(Key="a.txt")
    monkeypatch.setattr(module, "get_all_documents", lambda bucket, prefix: [mock_doc])
    monkeypatch.setattr(module, "meilisearch", MagicMock(Client=MagicMock(return_value=mock_meili_client)))
    # patch add/remove
    called = {}
    monkeypatch.setattr(module, "add_files_to_index", lambda index, files, s3_uri=None: called.setdefault("add", files))
    monkeypatch.setattr(module, "remove_files_from_index", lambda index, files, s3_uri=None: called.setdefault("remove", files))
    module.refresh_meili_index("bucket", prefix="pfx", s3_uri="s3://u")
    # since paginate returned a.txt and dir/ and prev had a.txt, new_files should be dir/ (folder) and removed none
    assert "add" in called


def test_create_document_text_and_folder(monkeypatch, mock_s3_client, mock_meili_client, meili_helpers, mock_psycopg, status_mocks):
    monkeypatch.setattr(module, "get_public_client", lambda: mock_s3_client)
    # ensure DB tags empty
    dbTags = {}
    # file that is a folder (endswith '/')
    folder_file = {"Key": "dir/", "Size": 0, "LastModified": __import__("datetime").datetime(2020,1,2)}
    module.create_document("bucket", folder_file, mock_meili_client, dbTags, s3_uri="s3://u")
    # increment_processed called for folder early exit
    module.increment_processed.assert_called()

    # file that is regular text file
    file = {"Key": "a.txt", "Size": 10, "LastModified": __import__("datetime").datetime(2020,1,1)}
    module.create_document("bucket", file, mock_meili_client, dbTags, s3_uri="s3://u")
    # client.index(...).add_documents called
    mock_meili_client.index.assert_called_with("bucket")
    mock_meili_client.index("bucket").add_documents.assert_called()


def test_add_files_to_index_executes_create(monkeypatch, mock_s3_client, mock_meili_client, meili_helpers, mock_psycopg):
    monkeypatch.setattr(module, "get_public_client", lambda: mock_s3_client)
    monkeypatch.setattr(module, "meilisearch", MagicMock(Client=MagicMock(return_value=mock_meili_client)))
    # create a small list of files
    files = [{"Key": "f1.txt", "Size": 1, "LastModified": __import__("datetime").datetime(2021,1,1)}]
    # patch create_document to record calls
    called = []
    monkeypatch.setattr(module, "create_document", lambda index, file, meili_client, dbTags, s3_uri=None: called.append((index, file)))
    module.add_files_to_index("bucket", files, s3_uri=None)
    assert called and called[0][0] == "bucket"


def test_remove_files_from_index_deletes_and_db(monkeypatch, mock_s3_client, mock_meili_client, meili_helpers, mock_psycopg, status_mocks):
    monkeypatch.setattr(module, "meilisearch", MagicMock(Client=MagicMock(return_value=mock_meili_client)))
    # patch get_doc_id to simple hash
    monkeypatch.setattr(module, "get_doc_id", lambda k: "h-"+k)
    keys = ["a.txt", "b.txt"]
    module.remove_files_from_index("bucket", keys, s3_uri="s3://u")
    # ensure delete_document called for each
    assert mock_meili_client.index("bucket").delete_document.call_count == 2
    module.increment_processed.assert_called()


def test_get_keywords_from_key_various():
    # uses separation characters; provide a string
    s = "one/two_three-four five.six\nseven"
    kw = module.get_keywords_from_key(s)
    assert "one" in kw and "two" in kw and "three" in kw

    # empty elements removed
    s2 = "/,"
    kw2 = module.get_keywords_from_key(s2)
    assert kw2 == []


def test_get_keywords_from_text_success(monkeypatch, mock_s3_client):
    monkeypatch.setattr(module, "get_public_client", lambda: mock_s3_client)
    # s3.get_object returns body with "hello,world"
    kws = module.get_keywords_from_text("bucket", "a.txt")
    assert isinstance(kws, list)
    assert "hello" in kws or "world" in kws

def test_get_keywords_from_text_failure(monkeypatch, mock_s3_client):
    # make get_object raise
    mock = mock_s3_client
    mock.get_object.side_effect = Exception("nope")
    monkeypatch.setattr(module, "get_public_client", lambda: mock)
    kws = module.get_keywords_from_text("bucket", "a.txt")
    # should fallback to splitting key
    assert "a.txt" in kws or "a" in kws

def test_get_keywords_from_pdf_success(monkeypatch, mock_s3_client):
    monkeypatch.setattr(module, "get_public_client", lambda: mock_s3_client)
    # create a mock PDF stream - monkeypatch fitz.open to return pages with text
    class MockPage:
        def get_text(self, t):
            return "pdftext one two"
    mock_doc = [MockPage(), MockPage()]
    monkeypatch.setattr(module, "fitz", MagicMock(open=MagicMock(return_value=mock_doc)))
    kws = module.get_keywords_from_pdf("bucket", "file.pdf")
    assert isinstance(kws, list)
    assert "pdftext" in kws or "one" in kws

def test_get_keywords_from_pdf_failure(monkeypatch, mock_s3_client):
    mock = mock_s3_client
    mock.get_object.side_effect = Exception("err")
    monkeypatch.setattr(module, "get_public_client", lambda: mock)
    kws = module.get_keywords_from_pdf("bucket", "file.pdf")
    assert "file.pdf" in kws or "file" in kws