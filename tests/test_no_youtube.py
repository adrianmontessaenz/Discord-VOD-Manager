from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_youtube_references_in_src():
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "googleapiclient" not in text, path
        assert "YOUTUBE_API_KEY" not in text, path


def test_requirements_have_no_google_client():
    assert "google-api-python-client" not in (ROOT / "requirements.txt").read_text(encoding="utf-8")
