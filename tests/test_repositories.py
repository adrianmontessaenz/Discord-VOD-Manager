from pathlib import Path

from repositories import SqliteGuildSettingsRepository, SqliteVodRepository, Vod

SRC = Path(__file__).resolve().parents[1] / "src"


def test_vod_roundtrip(tmp_path):
    repo = SqliteVodRepository(str(tmp_path / "t.db"))
    vod = Vod("abc", "MkLeo vs Tweek", "https://youtu.be/abc", "2026-01-01T10:00:00Z",
              youtube_channel_id="UC1", players=("MkLeo", "Tweek"), characters=("Joker",), tournament="Genesis")
    repo.save(vod)
    assert repo.get("abc") == vod
    assert repo.list("UC1") == [vod]
    assert repo.list("UC2") == []
    assert repo.get("missing") is None


def test_settings_and_history_are_independent_of_vods(tmp_path):
    db = str(tmp_path / "t.db")
    settings = SqliteGuildSettingsRepository(db)
    vods = SqliteVodRepository(db)
    settings.add_channel(1, 10)
    settings.add_player_1(1, 10, "MkLeo")
    settings.add_published(1, 10, "abc", "t", "https://youtu.be/abc", "2026-01-01T10:00:00Z")
    assert len(settings.get_published(1, 10)) == 1
    assert settings.load_guild_config(1)[10]["players_1"] == ["MkLeo"]
    assert vods.list() == []
    settings.clear_guild_database(1)
    assert settings.get_published(1, 10) == []


def test_only_repositories_touch_sqlite():
    for name in ("bot.py", "config.py"):
        assert "sqlite3" not in (SRC / name).read_text(encoding="utf-8"), name
