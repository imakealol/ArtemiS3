from pytest_mock import mocker
import app.s3.index_refresh as module
import collections
from tests.fixtures import *



#########################
# keywords_from_key tests
#########################


def test_keywords_from_key(key_1, keywords_1):
    keywords = module.get_keywords_from_key(key_1)
    assert collections.Counter(keywords) == collections.Counter(keywords_1)


#########################
# keywords_from_text tests
#########################


def test_keywords_from_text_happy_path(fake_s3_success, spy_get_keywords):
    text = "apple banana cherry"
    # prepare fake s3 to return the UTF-8 encoded text
    fake_s3_success(text.encode("utf-8"))
    # set the keyword extractor to return known tokens
    spy_get_keywords.set_return(["apple", "banana", "cherry"])
    res = module.get_keywords_from_text("some-bucket", "some/key.txt")
    assert res == ["apple", "banana", "cherry"]
    # verify get_keywords_from_key was called once with decoded text
    assert spy_get_keywords.calls == [text]

def test_keywords_from_text_s3_error(fake_s3_failure, spy_get_keywords, monkeypatch, capsys):
    # ensure S3 client will raise
    fake_s3_failure()
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

def test_keywords_from_text_truncate(fake_s3_success, spy_get_keywords):
    # create text that would produce more than 500 keywords; ensure extractor returns >500 items
    many = ["w" + str(i) for i in range(600)]
    fake_s3_success("dummy".encode("utf-8"))
    spy_get_keywords.set_return(many)
    res = module.get_keywords_from_text("bucket", "key")
    assert len(res) == 500
    assert res == many[:500]

def test_keywords_from_text_empty(fake_s3_success, spy_get_keywords):
    # If S3 returns empty content, ensure extractor is still called with empty string
    fake_s3_success(b"")
    spy_get_keywords.set_return(["no", "words"])
    res = module.get_keywords_from_text("b", "k")
    assert res == ["no", "words"]
    assert spy_get_keywords.calls == [""]

def test_keywords_from_text_invalid_file_type(fake_s3_success, spy_get_keywords, monkeypatch, capsys):
    # Create bytes that will cause decode to fail (invalid utf-8)
    invalid_bytes = b"\xff\xfe\xfa"
    # make FakeBody.read return invalid bytes: our fake_s3_success creates FakeBody that returns given bytes
    fake_s3_success(invalid_bytes)
    # set extractor to return something when passed the key (fallback)
    spy_get_keywords.set_return(["fallback"])
    res = module.get_keywords_from_text("bucket", "bad-key")
    # Because decode() would raise UnicodeDecodeError, function should catch exception and call extractor with key
    assert res == ["fallback"]
    assert spy_get_keywords.calls == ["bad-key"]


#########################
# keywords_from_pdf tests
#########################


def test_pdf_success_single_page(monkeypatch, fake_s3_success, spy_get_keywords):
    # Simulate PDF with one page containing text
    pages = [FakePage("page one text")]
    def fake_open(mime, stream):
        return FakePDF(pages)
    monkeypatch.setattr(module, "fitz", SimpleNamespace(open=fake_open))
    fake_s3_success(b"%PDF-FAKE")
    spy_get_keywords.set_return(["page", "one", "text"])
    res = module.get_keywords_from_pdf("bucket", "key.pdf")
    assert res == ["page", "one", "text"]
    assert spy_get_keywords.calls == ["page one text"]

def test_pdf_multiple_pages_and_truncate(monkeypatch, fake_s3_success, spy_get_keywords):
    # Simulate many pages so combined keywords exceed 500; ensure truncation and early break work
    # Each page returns two keywords
    pages = [FakePage(f"p{i}") for i in range(400)]  # 400 pages -> 800 keywords
    def fake_open(mime, stream):
        return FakePDF(pages)
    monkeypatch.setattr(module, "fitz", SimpleNamespace(open=fake_open))
    fake_s3_success(b"%PDF-FAKE")
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

def test_pdf_empty_pages_ignored(monkeypatch, fake_s3_success, spy_get_keywords):
    pages = [FakePage(""), FakePage("has text"), FakePage(None)]
    def fake_open(mime, stream):
        return FakePDF(pages)
    monkeypatch.setattr(module, "fitz", SimpleNamespace(open=fake_open))
    fake_s3_success(b"%PDF-FAKE")
    spy_get_keywords.set_return(["has", "text"])
    res = module.get_keywords_from_pdf("bucket", "mixed.pdf")
    assert res == ["has", "text"]
    # ensure extractor was only called for the non-empty page
    assert spy_get_keywords.calls == ["has text"]

def test_pdf_decode_or_open_failure_falls_back(fake_s3_failure, spy_get_keywords, capsys):
    # Force S3 get_object to raise so exception branch runs
    fake_s3_failure()
    spy_get_keywords.set_return(["fallback"])
    res = module.get_keywords_from_pdf("bucket", "broken.pdf")
    assert res == ["fallback"]
    captured = capsys.readouterr()
    assert "Error extracting text content from broken.pdf" in captured.out

def test_pdf_non_utf8_stream_but_open_called(monkeypatch, fake_s3_success, spy_get_keywords):
    # Even if bytes are arbitrary, fitz.open is called with stream; simulate pages
    pages = [FakePage("t")]
    called = {}
    def fake_open(mime, stream):
        # verify stream is the raw bytes returned by S3
        called['stream'] = stream
        return FakePDF(pages)
    monkeypatch.setattr(module, "fitz", SimpleNamespace(open=fake_open))
    b = b"\xff\xfe\x00"
    fake_s3_success(b)
    spy_get_keywords.set_return(["t"])
    res = module.get_keywords_from_pdf("bucket", "weird.pdf")
    assert res == ["t"]
    assert called['stream'] == b