import dwgmagic
from dwgmagic import update


def test_check_for_update_detects_newer_release(monkeypatch):
    monkeypatch.setattr(
        update,
        "fetch_latest_release",
        lambda repo=None: {
            "tag_name": "v99.0.0",
            "html_url": "https://example.test/release",
            "body": "notes",
        },
    )
    info = update.check_for_update()
    assert info is not None
    assert info.latest == "99.0.0"
    assert info.current == dwgmagic.__version__
    assert info.url == "https://example.test/release"


def test_check_for_update_ignores_current_or_older(monkeypatch):
    monkeypatch.setattr(
        update,
        "fetch_latest_release",
        lambda repo=None: {"tag_name": f"v{dwgmagic.__version__}"},
    )
    assert update.check_for_update() is None

    monkeypatch.setattr(
        update, "fetch_latest_release", lambda repo=None: {"tag_name": "v0.0.1"}
    )
    assert update.check_for_update() is None


def test_check_for_update_survives_bad_payloads(monkeypatch):
    monkeypatch.setattr(update, "fetch_latest_release", lambda repo=None: None)
    assert update.check_for_update() is None

    monkeypatch.setattr(
        update, "fetch_latest_release", lambda repo=None: {"tag_name": "not-a-version"}
    )
    assert update.check_for_update() is None
