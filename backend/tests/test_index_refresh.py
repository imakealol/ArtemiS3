from pytest_mock import mocker
import app.s3.index_refresh as module
import collections
from tests.fixtures import *


#########################
# add_files_to_index tests
#########################


def test_add_files_to_index_reads_db_and_calls_create_document(monkeypatch, fake_meili_client, fake_db_conn):
    conn, cursor = fake_db_conn

    # Simulate fetchall return for SELECT
    cursor.fetchall.return_value = [("tag1", "val1"), ("tag2", "val2")]

    # Patch external dependencies: meilisearch.Client, psycopg.connect, and create_document
    monkeypatch.setattr("app.s3.index_refresh.meilisearch", MagicMock(Client=MagicMock(return_value=fake_meili_client)))
    monkeypatch.setattr("app.s3.index_refresh.psycopg", MagicMock(connect=MagicMock(return_value=conn)))
    created = []
    def fake_create_document(index, file_obj, meili_client=None, dbTags=None, s3_uri=None):
        # record what was called for assertions
        created.append((index, file_obj, dbTags, s3_uri))
    monkeypatch.setattr("app.s3.index_refresh.create_document", fake_create_document)

    # Call with two fake file objects
    files = [{"key": "a"}, {"key": "b"}]
    module.add_files_to_index("my_index", files, s3_uri="s3://bucket")

    # Ensure DB SELECT executed and dbTags passed to create_document
    cursor.execute.assert_called_with("""SELECT * FROM file_tags WHERE bucket=%s""", ("my_index",))
    assert len(created) == 2
    for call in created:
        assert call[0] == "my_index"
        assert call[1] in files
        assert isinstance(call[2], dict)
    # s3_uri passed through
    assert all(call[3] == "s3://bucket" for call in created)


#########################
# remove_files_from_index tests
#########################


def test_remove_files_from_index_deletes_and_updates_db(monkeypatch, fake_meili_client, fake_db_conn):
    conn, cursor = fake_db_conn

    # Prepare meili client to capture delete_document calls
    index_mock = fake_meili_client.index.return_value
    index_mock.delete_document.return_value = None

    # Patch meilisearch.Client and psycopg.connect
    monkeypatch.setattr("app.s3.index_refresh.meilisearch", MagicMock(Client=MagicMock(return_value=fake_meili_client)))
    monkeypatch.setattr("app.s3.index_refresh.psycopg", MagicMock(connect=MagicMock(return_value=conn)))

    # Patch increment_processed to avoid any external calls
    monkeypatch.setattr("app.s3.index_refresh.increment_processed", MagicMock())

    monkeypatch.setattr("app.s3.index_refresh.get_doc_id", lambda k: f"hashed-{k}")

    removed = ["file1.png", "dir/file2.txt"]
    module.remove_files_from_index("my_index", removed, s3_uri="s3://bucket")

    # Ensure delete_document called with hashed ids
    expected_calls = [((f"hashed-{k}",),) for k in removed]
    # Check that meili index() was called with the index name for every removal
    assert fake_meili_client.index.call_count == len(removed)
    # Ensure delete_document called with each hashed key
    called_args = [call.args[0] for call in index_mock.delete_document.call_args_list]
    assert called_args == [f"hashed-{k}" for k in removed]

    # Ensure corresponding DB DELETE executed for each hashed_key
    # Last executed call should be DELETE FROM file_tags WHERE hashed_key=%s
    # cursor.execute gets called once per removed item
    assert cursor.execute.call_count == len(removed)
    for i, k in enumerate(removed):
        cursor.execute.assert_any_call("""DELETE FROM file_tags WHERE hashed_key=%s""", (f"hashed-{k}",))


#########################
# keywords_from_key tests
#########################


def test_keywords_from_key(key_1, keywords_1):
    keywords = module.get_keywords_from_key(key_1)
    assert collections.Counter(keywords) == collections.Counter(keywords_1)


#########################
# keywords_from_text tests
#########################


def test_keywords_from_text_happy_path(mock_s3_success, spy_get_keywords, text_content, text_keywords):
    text = text_content
    # prepare mock s3 to return the UTF-8 encoded text
    mock_s3_success(text.encode("utf-8"))
    # set the keyword extractor to return known tokens
    spy_get_keywords.set_return(text_keywords)
    res = module.get_keywords_from_text("some-bucket", "some/key.txt")
    assert res == text_keywords
    # verify get_keywords_from_key was called once with decoded text
    assert spy_get_keywords.calls == [text]

def test_keywords_from_text_s3_error(mock_s3_failure, spy_get_keywords, monkeypatch, capsys):
    # ensure S3 client will raise
    mock_s3_failure()
    # set extractor return
    spy_get_keywords.set_return(["from_key"])
    key_value = "the-key-name-or-text"
    res = module.get_keywords_from_text("bucket", key_value)
    assert res == ["from_key"]
    # verify extractor was called with the raw key string
    assert spy_get_keywords.calls == [key_value]
    # Optionally assert that an error message was printed
    captured = capsys.readouterr()
    assert "Error extracting text content from" in captured.out

def test_keywords_from_text_truncate(mock_s3_success, spy_get_keywords):
    # create text that would produce more than 500 keywords; ensure extractor returns >500 items
    many = ["w" + str(i) for i in range(600)]
    mock_s3_success("dummy".encode("utf-8"))
    spy_get_keywords.set_return(many)
    res = module.get_keywords_from_text("bucket", "key")
    assert len(res) == 500
    assert res == many[:500]

def test_keywords_from_text_empty(mock_s3_success, spy_get_keywords):
    # If S3 returns empty content, ensure extractor is still called with empty string
    mock_s3_success(b"")
    spy_get_keywords.set_return(["no", "words"])
    res = module.get_keywords_from_text("b", "k")
    assert res == ["no", "words"]
    assert spy_get_keywords.calls == [""]

def test_keywords_from_text_invalid_file_type(mock_s3_success, spy_get_keywords, monkeypatch, capsys):
    # Create bytes that will cause decode to fail (invalid utf-8)
    invalid_bytes = b"\xff\xfe\xfa"
    # make MockBody.read return invalid bytes: our mock_s3_success creates MockBody that returns given bytes
    mock_s3_success(invalid_bytes)
    # set extractor to return something when passed the key (fallback)
    spy_get_keywords.set_return(["fallback"])
    res = module.get_keywords_from_text("bucket", "bad-key")
    # Because decode() would raise UnicodeDecodeError, function should catch exception and call extractor with key
    assert res == ["fallback"]
    assert spy_get_keywords.calls == ["bad-key"]


#########################
# keywords_from_pdf tests
#########################


def test_keywords_from_pdf_happy_path(monkeypatch, mock_s3_success, spy_get_keywords):
    # Simulate PDF with one page containing text
    pages = [MockPage("page one text")]
    def mock_open(mime, stream):
        return MockPDF(pages)
    monkeypatch.setattr(module, "fitz", SimpleNamespace(open=mock_open))
    mock_s3_success(b"%PDF-FAKE")
    spy_get_keywords.set_return(["page", "one", "text"])
    res = module.get_keywords_from_pdf("bucket", "key.pdf")
    assert res == ["page", "one", "text"]
    assert spy_get_keywords.calls == ["page one text"]

def test_keywords_from_pdf_truncate(monkeypatch, mock_s3_success):
    # Simulate many pages so combined keywords exceed 500; ensure truncation and early break work
    # Each page returns two keywords
    pages = [MockPage(f"p{i}") for i in range(400)]  # 400 pages -> 800 keywords
    def mock_open(mime, stream):
        return MockPDF(pages)
    monkeypatch.setattr(module, "fitz", SimpleNamespace(open=mock_open))
    mock_s3_success(b"%PDF-FAKE")
    # extractor returns two words per page text
    def extractor(text):
        return [text + "_a", text + "_b"]
    monkeypatch.setattr(module, "get_keywords_from_key", extractor)
    res = module.get_keywords_from_pdf("bucket", "many_pages.pdf")
    assert len(res) == 500
    # first items correspond to the first 250 pages (2 keywords each)
    assert res[0] == "p0_a"
    assert res[1] == "p0_b"
    assert res[498] == "p249_a"
    assert res[499] == "p249_b"

def test_keywords_from_pdf_error(mock_s3_failure, spy_get_keywords, capsys):
    # Force S3 get_object to raise so exception branch runs
    mock_s3_failure()
    spy_get_keywords.set_return(["fallback"])
    res = module.get_keywords_from_pdf("bucket", "broken.pdf")
    assert res == ["fallback"]
    captured = capsys.readouterr()
    assert "Error extracting text content from broken.pdf" in captured.out