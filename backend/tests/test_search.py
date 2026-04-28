import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# import your module (adjust path if needed)
import app.s3.search as search


# ---------------------------
# Helper Function Tests
# ---------------------------

def test_facet_map_normal():
    result = {
        "facetDistribution": {
            "Ancestors": {"a": 1, "b": "2"}
        }
    }
    out = search._facet_map(result, "Ancestors")
    assert out == {"a": 1, "b": 2}


def test_folder_name():
    assert search._folder_name("a/b/c") == "c"
    assert search._folder_name("") == ""


def test_is_same_or_descendant():
    assert search._is_same_or_descendant("a/b", "a")
    assert search._is_same_or_descendant("a", "a")
    assert not search._is_same_or_descendant("b", "a")


def test_is_direct_child():
    assert search._is_direct_child("a", "a/b")
    assert not search._is_direct_child("a", "a/b/c")
    assert search._is_direct_child("", "root")
    assert not search._is_direct_child("", "a/b")


def test_breadcrumbs():
    with patch("app.s3.search.normalize_s3_path", return_value="a/b/c"):
        crumbs = search._breadcrumbs("a/b/c")
        assert crumbs == [
            {"path": "a", "name": "a"},
            {"path": "a/b", "name": "b"},
            {"path": "a/b/c", "name": "c"},
        ]


def test_to_last_modified():
    ts = int(datetime.now().timestamp())
    assert isinstance(search._to_last_modified(ts), datetime)

    iso = datetime.now().isoformat()
    assert isinstance(search._to_last_modified(iso), datetime)

    assert search._to_last_modified("bad") is None
    assert search._to_last_modified(None) is None


# ---------------------------
# filter_s3_objects
# ---------------------------

def test_filter_s3_objects_basic():
    now = datetime.now()

    assert search.filter_s3_objects("file.txt", 100)
    assert not search.filter_s3_objects("file.txt", 100, contains="abc")
    assert not search.filter_s3_objects("file.txt", 100, suffixes=[".jpg"])
    assert not search.filter_s3_objects("file.txt", 50, min_size=100)
    assert not search.filter_s3_objects("file.txt", 200, max_size=100)
    assert not search.filter_s3_objects("file.txt", 100, storage_class="A", storage_classes=["B"])

    assert not search.filter_s3_objects(
        "file.txt",
        100,
        last_modified=now - timedelta(days=2),
        modified_after=now - timedelta(days=1),
    )

    assert not search.filter_s3_objects(
        "file.txt",
        100,
        last_modified=now + timedelta(days=2),
        modified_before=now + timedelta(days=1),
    )


# ---------------------------
# iter_s3_objects
# ---------------------------

def test_iter_s3_objects_basic():
    mock_s3 = MagicMock()

    mock_paginator = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator

    now = datetime.now()

    mock_paginator.paginate.return_value = [
        {
            "Contents": [
                {"Key": "a.txt", "Size": 10, "LastModified": now, "StorageClass": "STANDARD"},
                {"Key": "b.txt", "Size": 20, "LastModified": now, "StorageClass": "STANDARD"},
            ]
        }
    ]

    results = list(search.iter_s3_objects("bucket", "", limit=1, s3=mock_s3))
    assert len(results) == 1
    assert results[0]["key"] == "a.txt"


def test_iter_s3_objects_error():
    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator

    from botocore.exceptions import BotoCoreError
    mock_paginator.paginate.side_effect = BotoCoreError()

    with pytest.raises(RuntimeError):
        list(search.iter_s3_objects("bucket", "", s3=mock_s3))


# ---------------------------
# search_from_meili
# ---------------------------

@patch("app.s3.search.meilisearch.Client")
@patch("app.s3.search.normalize_s3_path", return_value="prefix")
@patch("app.s3.search.build_subtree_filter", return_value="filter_expr")
def test_search_from_meili(mock_filter, mock_norm, mock_client):
    mock_index = MagicMock()
    mock_client.return_value.index.return_value = mock_index

    now_ts = int(datetime.now().timestamp())

    mock_index.search.return_value = {
        "hits": [
            {
                "Key": "a.txt",
                "Size": 10,
                "LastModified": now_ts,
                "StorageClass": "STANDARD",
                "Tags": {}
            }
        ]
    }

    results = search.search_from_meili(
        bucket="bucket",
        prefix="prefix",
        contains="a",
        limit=5,
        sort_by="Size"
    )

    assert len(results) == 1
    assert results[0]["key"] == "a.txt"
    assert isinstance(results[0]["last_modified"], datetime)


# ---------------------------
# search_folders_from_meili
# ---------------------------

@patch("app.s3.search.meilisearch.Client")
@patch("app.s3.search.normalize_s3_path", side_effect=lambda x: x)
@patch("app.s3.search.path_depth", return_value=1)
def test_search_folders(mock_depth, mock_norm, mock_client):
    mock_index = MagicMock()
    mock_client.return_value.index.return_value = mock_index

    mock_index.search.return_value = {
        "facetDistribution": {
            "Ancestors": {
                "a": 5,
                "a/b": 3
            }
        }
    }

    results = search.search_folders_from_meili("bucket", prefix="")

    assert len(results) == 2
    assert results[0]["matched_count"] >= results[1]["matched_count"]


# ---------------------------
# list_folder_children_from_meili
# ---------------------------

@patch("app.s3.search.meilisearch.Client")
@patch("app.s3.search.normalize_s3_path", side_effect=lambda x: x or "")
@patch("app.s3.search.path_depth", return_value=1)
def test_list_folder_children(mock_depth, mock_norm, mock_client):
    mock_index = MagicMock()
    mock_client.return_value.index.return_value = mock_index

    # First call = facet search
    mock_index.search.side_effect = [
        {
            "facetDistribution": {
                "Ancestors": {
                    "a/b": 5,
                    "a/c": 3,
                    "a/b/d": 2
                }
            }
        },
        {
            "hits": [
                {
                    "Key": "a/file.txt",
                    "Size": 10,
                    "LastModified": int(datetime.now().timestamp()),
                    "StorageClass": "STANDARD"
                }
            ]
        }
    ]

    result = search.list_folder_children_from_meili(
        bucket="bucket",
        prefix="a",
        path="a"
    )

    assert result["path"] == "a"
    assert len(result["children"]) == 2  # b and c
    assert len(result["files"]) == 1


def test_list_folder_children_invalid_path():
    with patch("app.s3.search.normalize_s3_path", side_effect=lambda x: x):
        with pytest.raises(ValueError):
            search.list_folder_children_from_meili(
                bucket="bucket",
                prefix="a",
                path="b"
            )