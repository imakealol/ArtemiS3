import pytest
import app.s3.utils as module 

def test_parse_s3_uri_valid():
    bucket, key = module.parse_s3_uri("s3://nasa-missions/artemis/data.json")
    assert bucket == "nasa-missions"
    assert key == "artemis/data.json"

def test_normalize_s3_path():
    assert module.normalize_s3_path("  missions//nasa/artemis///") == "missions/nasa/artemis"
    assert module.normalize_s3_path("") == ""

def test_key_parent_path():
    path = "root/subfolder/file.txt"
    assert module.key_parent_path(path) == "root/subfolder"

def test_key_filename():
    assert module.key_filename("missions/artemis/log.txt") == "log.txt"

def test_path_depth():
    assert module.path_depth("a/b/c/d") == 4
    assert module.path_depth("root") == 1

def test_build_subtree_filter():
    """Checks the Meilisearch filter string generation."""
    path = "missions/nasa"
    expected = "(Ancestors = 'missions/nasa' OR ParentPath = 'missions/nasa')"
    assert module.build_subtree_filter(path) == expected

def test_parent_ancestors():
    """Checks if we get the full breadcrumb list."""
    path = "a/b/c"
    expected = ["a", "a/b", "a/b/c"]
    assert module.parent_ancestors(path) == expected