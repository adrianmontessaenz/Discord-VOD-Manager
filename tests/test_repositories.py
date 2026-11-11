from pathlib import Path

import sqlite3

from repositories import SqliteGuildSettingsRepository, SqliteVodRepository, Vod
from repositories.sync_state import SqliteSyncStateRepository

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
    assert settings.get_published(1, 10) == {"abc"}
    assert settings.load_guild_config(1)[10]["players_1"] == ["MkLeo"]
    assert vods.list() == []
    settings.clear_guild_database(1)
    assert settings.get_published(1, 10) == set()


def test_only_repositories_touch_sqlite():
    for name in ("bot.py", "config.py"):
        assert "sqlite3" not in (SRC / name).read_text(encoding="utf-8"), name


def _vod(i, rev, ch="UC1"):
    return Vod(f"v{i}", f"t{i}", f"https://youtu.be/v{i}", f"2026-01-0{i}T10:00:00Z",
               youtube_channel_id=ch, revision=rev)


def test_vod_revision_roundtrip(tmp_path):
    repo = SqliteVodRepository(str(tmp_path / "t.db"))
    repo.save(_vod(1, 7))
    assert repo.get("v1").revision == 7


def test_list_since_revision(tmp_path):
    repo = SqliteVodRepository(str(tmp_path / "t.db"))
    for i, r in ((1, 1), (2, 2), (3, 3)):
        repo.save(_vod(i, r))
    assert [v.video_id for v in repo.list(since_revision=1)] == ["v2", "v3"]
    assert [v.video_id for v in repo.list("UC1", since_revision=2)] == ["v3"]


def test_latest_revision_empty_is_zero(tmp_path):
    repo = SqliteVodRepository(str(tmp_path / "t.db"))
    assert repo.latest_revision() == 0
    repo.save(_vod(1, 4))
    repo.save(_vod(2, 9))
    assert repo.latest_revision() == 9


def test_old_database_gets_revision_column(tmp_path):
    db = str(tmp_path / "t.db")
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE vods (video_id TEXT PRIMARY KEY, title TEXT, url TEXT,
        published_at TEXT, youtube_channel_id TEXT, players TEXT, characters TEXT, tournament TEXT)""")
    conn.execute("INSERT INTO vods VALUES ('old','t','u','2025-01-01T00:00:00Z','UC1','','',NULL)")
    conn.commit()
    conn.close()
    repo = SqliteVodRepository(db)
    assert repo.get("old").revision == 0
    repo.save(_vod(1, 5))
    assert repo.get("v1").revision == 5
    SqliteVodRepository(db)  # reopening must not fail on the guarded ALTER


def test_sync_state_get_set_overwrite(tmp_path):
    st = SqliteSyncStateRepository(str(tmp_path / "t.db"))
    assert st.get("k") is None
    st.set("k", "1")
    st.set("k", "2")
    assert st.get("k") == "2"


def test_get_published_returns_video_ids(tmp_path):
    s = SqliteGuildSettingsRepository(str(tmp_path / "t.db"))
    s.add_published(1, 10, "a", "t", "u", "d")
    s.add_published(1, 10, "b", "t", "u2", "d")
    s.add_published(1, 11, "c", "t", "u3", "d")
    assert s.get_published(1, 10) == {"a", "b"}


def test_add_published_returns_true_then_false(tmp_path):
    s = SqliteGuildSettingsRepository(str(tmp_path / "t.db"))
    assert s.add_published(1, 10, "a", "t", "u", "d") is True
    assert s.add_published(1, 10, "a", "t", "u", "d") is False


def test_remove_published(tmp_path):
    s = SqliteGuildSettingsRepository(str(tmp_path / "t.db"))
    s.add_published(1, 10, "a", "t", "u", "d")
    s.remove_published(1, 10, "a")
    assert s.get_published(1, 10) == set()
    assert s.add_published(1, 10, "a", "t", "u", "d") is True


def test_auto_update_flag_and_listing(tmp_path):
    s = SqliteGuildSettingsRepository(str(tmp_path / "t.db"))
    s.add_channel(1, 10)
    s.add_channel(1, 11)
    s.set_auto_update(1, 10, True)
    s.set_auto_update(1, 99, True)  # row does not exist: creates nothing
    assert s.list_auto_update_channels() == [(1, 10)]
    s.set_auto_update(1, 10, False)
    assert s.list_auto_update_channels() == []
