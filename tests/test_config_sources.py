import pytest

from config import MyConfig
from fakes import FakeYggdrasil
from filters import ChannelFilter
from repositories import SqliteGuildSettingsRepository, YggdrasilClient


@pytest.fixture
def fake():
    return FakeYggdrasil()


@pytest.fixture
def sources(fake):
    return YggdrasilClient("http://y", "secret", http=fake)


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no data/config.json -> no default channels
    return SqliteGuildSettingsRepository(str(tmp_path / "t.db"))


@pytest.fixture
def cfg():
    return MyConfig()


def stored(db, guild=1, channel=10):
    return db.load_guild_config(guild).get(channel, {}).get("youtube_channels", {})


def test_add_by_id_registers_and_stores_locally(cfg, sources, db, fake):
    msg = cfg.add_youtube_channel(1, 10, "UCabc", sources, db)
    assert "stored" in msg
    assert "UCabc" in fake.sources
    assert list(stored(db).values()) == ["UCabc"]


def test_add_by_handle_stores_returned_name_and_id(cfg, sources, db):
    msg = cfg.add_youtube_channel(1, 10, "@genesis", sources, db)
    assert "stored" in msg
    assert stored(db) == {"genesis": "UCgenesis"}


def test_add_invalid_format_message_and_no_call(cfg, sources, db, fake):
    msg = cfg.add_youtube_channel(1, 10, "nonsense", sources, db)
    assert "Invalid channel format" in msg
    assert fake.requests == [] and stored(db) == {}


def test_add_failure_stores_nothing(cfg, sources, db, fake):
    fake.down = True
    msg = cfg.add_youtube_channel(1, 10, "UCabc", sources, db)
    assert msg.startswith("Could not register the channel in Yggdrasil:")
    assert stored(db) == {}
    assert cfg.add_youtube_channel(1, 10, "UCabc", None, db).startswith("Could not register")


def test_add_requests_history_best_effort(cfg, sources, db, fake):
    cfg.add_youtube_channel(1, 10, "UCabc", sources, db)
    assert fake.history_requests == ["UCabc"]

    class NoHistory:
        def __init__(self, inner):
            self.inner = inner

        def add_source(self, *a, **k):
            return self.inner.add_source(*a, **k)

        def request_history(self, channel_id):
            from repositories import YggdrasilUnavailable
            raise YggdrasilUnavailable("history down")

    msg = cfg.add_youtube_channel(1, 10, "UCdef", NoHistory(sources), db)
    assert "stored" in msg and "UCdef" in stored(db).values()


def test_add_existing_is_reported_as_already_stored(cfg, sources, db, fake):
    cfg.add_youtube_channel(1, 10, "@genesis", sources, db)
    n = len(fake.requests)
    assert "already" in cfg.add_youtube_channel(1, 10, "UCgenesis", sources, db)
    assert len(fake.requests) == n  # no remote call needed for a channel this text channel has
    assert "already" in cfg.add_youtube_channel(1, 10, "@genesis", sources, db)


def test_add_known_id_from_other_text_channel_passes_name(cfg, sources, db, fake):
    cfg.add_youtube_channel(1, 10, "@genesis", sources, db)
    fake.sources.clear()  # Yggdrasil forgot it: a known local name must be sent along
    cfg.add_youtube_channel(1, 11, "UCgenesis", sources, db)
    assert fake.sources["UCgenesis"]["name"] == "genesis"
    assert stored(db, channel=11) == {"genesis": "UCgenesis"}


def test_remove_deletes_remote_only_if_unused_elsewhere(cfg, sources, db, fake):
    cfg.add_youtube_channel(1, 10, "@genesis", sources, db)
    msg = cfg.remove_youtube_channel(1, 10, "genesis", db, sources, other_users=lambda cid: True)
    assert "removed" in msg and stored(db) == {} and "UCgenesis" in fake.sources
    cfg.add_youtube_channel(1, 10, "@genesis", sources, db)
    cfg.remove_youtube_channel(1, 10, "genesis", db, sources, other_users=lambda cid: False)
    assert "UCgenesis" not in fake.sources


def test_remove_reads_id_before_popping(cfg, sources, db):
    cfg.add_youtube_channel(1, 10, "@genesis", sources, db)
    seen = []
    cfg.remove_youtube_channel(1, 10, "genesis", db, sources, other_users=lambda cid: seen.append(cid) or True)
    assert seen == ["UCgenesis"]
    assert "not found" in cfg.remove_youtube_channel(1, 10, "genesis", db, sources, lambda cid: False)


def test_list_marks_unwatched(cfg, sources, db, fake):
    cfg.add_youtube_channel(1, 10, "@a", sources, db)
    cfg.add_youtube_channel(1, 10, "@b", sources, db)
    del fake.sources["UCb"]
    assert sorted(cfg.list_youtube_channels(1, 10, db, sources)) == [
        ("a", "UCa", True), ("b", "UCb", False)]


def test_list_when_yggdrasil_down_marks_all_watched(cfg, sources, db, fake):
    cfg.add_youtube_channel(1, 10, "@a", sources, db)
    fake.down = True
    assert cfg.list_youtube_channels(1, 10, db, sources) == [("a", "UCa", True)]
    assert cfg.list_youtube_channels(1, 10, db, None) == [("a", "UCa", True)]


def test_targets_built_from_config(cfg, sources, db):
    cfg.add_youtube_channel(1, 10, "@a", sources, db)
    cfg.add_player_1(1, 10, "MkLeo", db)
    targets = cfg.targets(1, [10], db)
    assert len(targets) == 1
    t = targets[0]
    assert (t.guild_id, t.channel_id, t.youtube_channel_ids) == (1, 10, frozenset({"UCa"}))
    assert t.filter == ChannelFilter(players_1=("MkLeo",))
