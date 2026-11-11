import asyncio

import pytest

from fakes import FakeYggdrasil
from filters import ChannelFilter
from repositories import (SqliteGuildSettingsRepository, SqliteSyncStateRepository, SqliteVodRepository,
                          Vod, YggdrasilClient, YggdrasilUnavailable, YggdrasilVodRepository)
from vod_sync import CURSOR_KEY, ChannelTarget, format_vod, publish_new_vods, urls_in_message


class Env:
    """Repositories on files in tmp_path; `reopen()` simulates a bot restart."""

    def __init__(self, tmp_path, fake):
        self.db = str(tmp_path / "bot.db")
        self.fake = fake
        self.sent = []
        self.reopen()

    def reopen(self):
        self.source = YggdrasilVodRepository(YggdrasilClient("http://y", "secret", http=self.fake))
        self.state = SqliteSyncStateRepository(self.db)
        self.settings = SqliteGuildSettingsRepository(self.db)
        self.cache = SqliteVodRepository(self.db)

    async def send(self, guild_id, channel_id, text):
        self.sent.append((guild_id, channel_id, text))
        return True

    async def run(self, targets, send=None, **kw):
        return await publish_new_vods(source=self.source, state=self.state, settings=self.settings,
                                      cache=self.cache, targets=targets, send=send or self.send,
                                      delay=0, **kw)


@pytest.fixture
def fake():
    return FakeYggdrasil()


@pytest.fixture
def env(tmp_path, fake):
    return Env(tmp_path, fake)


def target(channel_id=10, yt=("UC1",), flt=None, guild=1):
    return ChannelTarget(guild, channel_id, frozenset(yt), flt or ChannelFilter())


def run(coro):
    return asyncio.run(coro)


def test_first_sync_initialises_cursor_and_posts_nothing(env, fake):
    fake.add_vod("old", "UC1", "2026-01-01T00:00:00Z")
    res = run(env.run([target()]))
    assert res.initialised and env.sent == []
    assert env.state.get(CURSOR_KEY) == "1"


def test_new_vod_goes_only_to_the_matching_channel(env, fake):
    run(env.run([]))
    fake.add_vod("n", "UC1", "2026-02-01T00:00:00Z", title="MkLeo vs Tweek")
    targets = [target(10, flt=ChannelFilter(players_1=("MkLeo",))),
               target(11, flt=ChannelFilter(players_1=("Zackray",))),
               target(12, yt=("UC2",))]
    res = run(env.run(targets))
    assert [s[1] for s in env.sent] == [10] and res.published == 1
    assert "MkLeo vs Tweek" in env.sent[0][2]


def test_restart_does_not_post_twice(env, fake):
    run(env.run([]))
    fake.add_vod("n", "UC1", "2026-02-01T00:00:00Z")
    run(env.run([target()]))
    assert len(env.sent) == 1
    env.reopen()
    env.state.set(CURSOR_KEY, "0")
    run(env.run([target()]))
    assert len(env.sent) == 1


def test_catch_up_after_downtime_posts_everything_since_cursor_oldest_first(env, fake):
    run(env.run([]))
    fake.add_vod("late", "UC1", "2026-03-02T00:00:00Z")
    fake.add_vod("early", "UC1", "2026-03-01T00:00:00Z")
    run(env.run([target()]))
    assert [("early" in s[2], "late" in s[2]) for s in env.sent] == [(True, False), (False, True)]


def test_revision_bump_of_posted_vod_not_reposted(env, fake):
    run(env.run([]))
    fake.add_vod("n", "UC1", "2026-02-01T00:00:00Z")
    run(env.run([target()]))
    fake.add_vod("n", "UC1", "2026-02-01T00:00:00Z", title="fixed title", revision=50)
    res = run(env.run([target()]))
    assert len(env.sent) == 1 and res.published == 0
    assert env.state.get(CURSOR_KEY) == "50"


def test_yggdrasil_down_keeps_cursor_and_retries(env, fake):
    run(env.run([]))
    fake.add_vod("n", "UC1", "2026-02-01T00:00:00Z")
    fake.down = True
    with pytest.raises(YggdrasilUnavailable):
        run(env.run([target()]))
    assert env.state.get(CURSOR_KEY) == "0" and env.sent == []
    fake.down = False
    run(env.run([target()]))
    assert len(env.sent) == 1


def test_send_exception_releases_claim_and_keeps_cursor(env, fake):
    run(env.run([]))
    fake.add_vod("a", "UC1", "2026-02-01T00:00:00Z")
    fake.add_vod("b", "UC1", "2026-02-02T00:00:00Z")
    calls = []

    async def flaky(g, c, text):
        calls.append(text)
        if len(calls) == 2:
            raise RuntimeError("discord blew up")
        return True

    with pytest.raises(RuntimeError):
        run(env.run([target()], send=flaky))
    assert env.state.get(CURSOR_KEY) == "0"
    run(env.run([target()]))
    assert len(env.sent) == 1 and "/watch?v=b" in env.sent[0][2]


def test_unreachable_discord_channel_is_skipped(env, fake):
    run(env.run([]))
    fake.add_vod("n", "UC1", "2026-02-01T00:00:00Z")

    async def send(g, c, text):
        if c == 10:
            return False
        env.sent.append((g, c, text))
        return True

    res = run(env.run([target(10), target(11)], send=send))
    assert [s[1] for s in env.sent] == [11] and res.published == 1
    assert env.state.get(CURSOR_KEY) == "1"
    assert env.settings.get_published(1, 10) == set()
    assert env.settings.get_published(1, 11) == {"n"}


def test_empty_filter_gets_all_vods_of_its_channels(env, fake):
    run(env.run([]))
    fake.add_vod("a", "UC1", "2026-02-01T00:00:00Z", title="anything")
    fake.add_vod("b", "UC2", "2026-02-02T00:00:00Z", title="other channel")
    run(env.run([target(10, yt=("UC1",))]))
    assert len(env.sent) == 1 and "anything" in env.sent[0][2]


def test_target_without_youtube_channels_gets_none(env, fake):
    run(env.run([]))
    fake.add_vod("a", "UC1", "2026-02-01T00:00:00Z")
    run(env.run([target(10, yt=())]))
    assert env.sent == []


def test_vods_are_cached_in_sqlite(env, fake):
    run(env.run([]))
    fake.add_vod("a", "UC1", "2026-02-01T00:00:00Z", players=("MkLeo",))
    run(env.run([]))
    cached = env.cache.get("a")
    assert cached.players == ("MkLeo",) and cached.revision == 1


def test_urls_in_message_extracts_all_links():
    text = "x (2026-01-01 10:00): https://youtu.be/a, and <https://www.youtube.com/watch?v=b>. end"
    assert urls_in_message(text) == ["https://youtu.be/a", "https://www.youtube.com/watch?v=b"]
    assert urls_in_message("no links") == []


def test_format_vod():
    v = Vod("a", "MkLeo vs Tweek", "https://youtu.be/a", "2026-01-02T15:30:00Z")
    assert format_vod(v) == "MkLeo vs Tweek (2026-01-02 15:30): https://youtu.be/a"
