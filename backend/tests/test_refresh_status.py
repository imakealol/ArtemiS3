from tests.fixtures import *
import app.s3.refresh_status as module

def test_now_iso_format_is_utc():
    s = module._now_iso_format()
    assert s.endswith("Z")
    # parseable RFC-like structure
    assert "T" in s


def test_start_refresh_creates_status():
    uri = "s3://bucket/p"
    module.start_refresh(uri, total=5, status="listing")
    st = module._status_by_uri.get(uri)
    assert st is not None
    assert st.status == "listing"
    assert st.total == 5
    assert st.processed == 0
    assert st.listed == 0
    assert st.started_at is not None


def test_set_status_updates_and_resets_processed():
    uri = "s3://bucket/p2"
    module.start_refresh(uri, total=10, status="listing")
    # set status and reset processed
    module.increment_processed(uri, 3)
    module.set_status(uri, status="running", total=20, reset_processed=True)
    st = module._status_by_uri[uri]
    assert st.status == "running"
    assert st.total == 20
    assert st.processed == 0
    assert st.percent == 0

def test_set_status_creates_when_missing():
    uri = "s3://new/none"
    # bug in original code uses get("s3_uri") — this test ensures we still set given uri
    module.set_status(uri, status="running", total=2, reset_processed=False)
    st = module._status_by_uri.get(uri)
    assert st is not None
    assert st.status == "running"
    assert st.total == 2

def test_increment_listed_and_no_op_when_missing():
    uri = "s3://no/one"
    # no status yet -> should be no-op
    module.increment_listed(uri, 3)
    assert uri not in module._status_by_uri

    # with status
    module.start_refresh(uri, total=1)
    module.increment_listed(uri, 4)
    assert module._status_by_uri[uri].listed == 4

def test_increment_processed_and_percent_calculation():
    uri = "s3://calc/percent"
    module.start_refresh(uri, total=4)
    module.increment_processed(uri, 1)
    assert module._status_by_uri[uri].processed == 1
    assert module._status_by_uri[uri].percent == 25

    # increment more than total
    module.increment_processed(uri, 4)
    assert module._status_by_uri[uri].processed == 5
    assert module._status_by_uri[uri].percent == int((5 / 4) * 100)

def test_finish_refresh_sets_done_and_percent():
    uri = "s3://finish/it"
    module.start_refresh(uri, total=2)
    module.increment_processed(uri, 2)
    module.finish_refresh(uri)
    st = module._status_by_uri[uri]
    assert st.status == "done"
    assert st.finished_at is not None
    assert st.percent == 100

    # when total is zero percent should be 0
    uri2 = "s3://finish/zero"
    module.start_refresh(uri2, total=0)
    module.finish_refresh(uri2)
    assert module._status_by_uri[uri2].percent == 0

def test_fail_refresh_sets_error_and_message():
    uri = "s3://fail/one"
    module.start_refresh(uri, total=3)
    module.fail_refresh(uri, "boom")
    st = module._status_by_uri[uri]
    assert st.status == "error"
    assert st.message == "boom"
    assert st.finished_at is not None

    # calling fail_refresh when missing should still create an entry
    uri2 = "s3://fail/new"
    module.fail_refresh(uri2, "ohno")
    st2 = module._status_by_uri[uri2]
    assert st2.status == "error"
    assert st2.message == "ohno"

def test_get_status_returns_idle_when_missing():
    uri = "s3://not/exists"
    res = module.get_status(uri)
    assert res["status"] == "idle"
    assert res["processed"] == 0
    assert res["total"] == 0
    assert res["percent"] == 0

def test_get_status_returns_dict_of_status():
    uri = "s3://exists"
    module.start_refresh(uri, total=7, status="running")
    module.increment_listed(uri, 2)
    module.increment_processed(uri, 1)
    out = module.get_status(uri)
    assert out["status"] == "running"
    assert out["listed"] == 2
    assert out["processed"] == 1
    assert out["total"] == 7
    assert "started_at" in out