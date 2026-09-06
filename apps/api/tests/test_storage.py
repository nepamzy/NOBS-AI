from app.storage import to_url


def test_to_url_strips_local_storage_root_prefix():
    # settings.local_storage_root defaults to "./storage/local"
    assert to_url("./storage/local/abc/assembly/final.mp4") == "/storage/abc/assembly/final.mp4"


def test_to_url_returns_none_for_none_or_empty_path():
    assert to_url(None) is None
    assert to_url("") is None


def test_to_url_handles_a_path_without_the_root_prefix_gracefully():
    # defensive: still produces a servable-looking URL rather than crashing
    assert to_url("some/other/path.mp4") == "/storage/some/other/path.mp4"
