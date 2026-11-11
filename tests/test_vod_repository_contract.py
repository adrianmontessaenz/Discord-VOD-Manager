"""The same behaviour is expected from the SQLite cache and the Yggdrasil-backed repository."""
import pytest

from fakes import FakeYggdrasil
from repositories import SqliteVodRepository, Vod
from repositories.yggdrasil_client import YggdrasilClient, YggdrasilVodRepository

VODS = [
    # (video_id, channel, published_at, players, characters, tournament, revision)
    ("b", "UC2", "2026-01-02T00:00:00Z", ("Tweek",), ("sora",), None, 2),
    ("a", "UC1", "2026-01-01T00:00:00Z", ("MkLeo", "Tweek"), ("joker",), "genesis-9", 1),
    ("c", "UC1", "2026-01-03T00:00:00Z", (), (), None, 3),
]


@pytest.fixture(params=["sqlite", "yggdrasil"])
def repo(request, tmp_path):
    if request.param == "sqlite":
        r = SqliteVodRepository(str(tmp_path / "c.db"))
        for vid, ch, pub, pl, chars, tour, rev in VODS:
            r.save(Vod(vid, f"title {vid}", f"https://www.youtube.com/watch?v={vid}", pub,
                       youtube_channel_id=ch, players=pl, characters=chars, tournament=tour, revision=rev))
        return r
    fake = FakeYggdrasil()
    for vid, ch, pub, pl, chars, tour, rev in VODS:
        fake.add_vod(vid, ch, pub, title=f"title {vid}", players=pl, characters=chars,
                     tournament=tour, revision=rev)
    return YggdrasilVodRepository(YggdrasilClient("http://y", "secret", http=fake))


def test_get_existing_and_missing(repo):
    assert repo.get("a").title == "title a"
    assert repo.get("zzz") is None


def test_list_all_ordered_by_published_at(repo):
    assert [v.video_id for v in repo.list()] == ["a", "b", "c"]


def test_list_by_channel(repo):
    assert [v.video_id for v in repo.list("UC1")] == ["a", "c"]
    assert repo.list("UC9") == []


def test_list_since_revision(repo):
    assert [v.video_id for v in repo.list(since_revision=1)] == ["b", "c"]
    assert [v.video_id for v in repo.list("UC1", since_revision=1)] == ["c"]


def test_latest_revision(repo):
    assert repo.latest_revision() == 3


def test_players_characters_tournament_roundtrip(repo):
    v = repo.get("a")
    assert (v.players, v.characters, v.tournament, v.revision, v.youtube_channel_id) == (
        ("MkLeo", "Tweek"), ("joker",), "genesis-9", 1, "UC1")
