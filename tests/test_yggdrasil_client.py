import pytest

from fakes import FakeYggdrasil
from repositories.yggdrasil_client import (YggdrasilClient, YggdrasilError, YggdrasilUnavailable,
                                           vod_from_json)


@pytest.fixture
def fake():
    return FakeYggdrasil()


@pytest.fixture
def client(fake):
    return YggdrasilClient("http://y:8000/", "secret", http=fake)


def test_sends_bearer_token(client, fake):
    client.list_sources()
    assert fake.requests[0][3]["Authorization"] == "Bearer secret"


def test_list_vods_follows_pages(client, fake):
    for i in range(5):
        fake.add_vod(f"v{i}", "UC1", f"2026-01-0{i + 1}T00:00:00Z")
    client.per_page = 2
    assert [v["video_id"] for v in client.list_vods()] == [f"v{i}" for i in range(5)]
    assert len([r for r in fake.requests if r[1] == "/v1/vods"]) == 3


def test_list_vods_passes_since(client, fake):
    for i in range(3):
        fake.add_vod(f"v{i}", "UC1", f"2026-01-0{i + 1}T00:00:00Z")
    assert [v["video_id"] for v in client.list_vods(since=1)] == ["v1", "v2"]
    assert fake.requests[-1][2]["since"] == 1


def test_latest_revision_uses_page_revision(client, fake):
    assert client.latest_revision() == 0
    fake.add_vod("a", "UC1", "2026-01-01T00:00:00Z", revision=4)
    fake.add_vod("b", "UC1", "2026-01-02T00:00:00Z", revision=9)
    assert client.latest_revision() == 9
    assert fake.requests[-1][2]["per_page"] == 1


def test_add_remove_sources(client, fake):
    src = client.add_source("UCabc", name="Chan")
    assert src["channel_id"] == "UCabc"
    assert client.add_source("@handle")["channel_id"] == "UChandle"
    assert {s["channel_id"] for s in client.list_sources()} == {"UCabc", "UChandle"}
    assert client.remove_source("UCabc") is True
    client.request_history("UChandle")
    assert fake.history_requests == ["UChandle"]


def test_remove_unknown_source_returns_false(client):
    assert client.remove_source("UCnope") is False


def test_connection_error_is_unavailable(client, fake):
    fake.down = True
    with pytest.raises(YggdrasilUnavailable):
        client.list_vods()


def test_5xx_is_unavailable(client, fake):
    fake.fail_status = 503
    with pytest.raises(YggdrasilUnavailable) as e:
        client.list_vods()
    assert e.value.status == 503


def test_4xx_is_yggdrasil_error_with_code(client):
    with pytest.raises(YggdrasilError) as e:
        client.add_source("nonsense")
    assert not isinstance(e.value, YggdrasilUnavailable)
    assert e.value.status == 422 and e.value.code == "validation_error"
    with pytest.raises(YggdrasilError) as e:
        client.request_history("UCunknown")
    assert e.value.status == 404


def test_get_vod_missing_is_none_and_vod_from_json(client, fake):
    assert client.get_vod("zzz") is None
    fake.add_vod("a", "UC1", "2026-01-01T00:00:00Z", players=("MkLeo", "Tweek"),
                 characters=("joker",), tournament="genesis-9", revision=3)
    vod = vod_from_json(client.get_vod("a"))
    assert vod.players == ("MkLeo", "Tweek") and vod.characters == ("joker",)
    assert vod.tournament == "genesis-9" and vod.revision == 3 and vod.youtube_channel_id == "UC1"
