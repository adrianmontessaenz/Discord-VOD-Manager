import json

from config import MyConfig, char_aliases
from filters import ChannelFilter
from repositories import SqliteGuildSettingsRepository


def test_get_filter_builds_from_channel(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = SqliteGuildSettingsRepository(str(tmp_path / "t.db"))
    cfg = MyConfig()
    cfg.add_player_1(1, 10, "MkLeo", db)
    cfg.add_character_2(1, 10, "Joker", db)
    cfg.enforce_player_2(1, 10, False, db)
    assert cfg.get_filter(1, 10, db) == ChannelFilter(
        players_1=("MkLeo",), characters_2=("Joker",), enforce_player_2=False)


def test_set_enforce_characters_sets_both(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = SqliteGuildSettingsRepository(str(tmp_path / "t.db"))
    cfg = MyConfig()
    cfg.set_enforce_characters(1, 10, True, db)
    f = cfg.get_filter(1, 10, db)
    assert f.enforce_character_1 and f.enforce_character_2
    assert db.load_guild_config(1)[10]["enforce_character_2"] is True


def test_channels_do_not_share_youtube_dict(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "config.json").write_text(json.dumps({"youtube_channels": {"A": "UC1"}}))
    db = SqliteGuildSettingsRepository(str(tmp_path / "t.db"))
    cfg = MyConfig()
    cfg.add_player_1(1, 10, "x", db)
    cfg.add_player_1(1, 11, "x", db)
    cfg._my_channels[10].youtube_channels["B"] = "UC2"
    assert "B" not in cfg._my_channels[11].youtube_channels


def test_char_aliases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert char_aliases() == {}
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "config.json").write_text(
        json.dumps({"char_names": {"Mario": ["マリオ", "Mario Bros"]}}), encoding="utf-8")
    assert char_aliases() == {"Mario": ("マリオ", "Mario Bros")}
