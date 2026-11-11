from filters import ChannelFilter, tokenize, vod_matches
from repositories import Vod


def vod(title="Genesis: MkLeo vs Tweek", players=(), characters=()):
    return Vod("v", title, "https://youtu.be/v", "2026-01-01T00:00:00Z",
               youtube_channel_id="UC1", players=players, characters=characters)


def test_tokenize_strips_accents_and_case():
    assert tokenize("Él Fóx_vs  Ñandú!") == ["el", "fox", "vs", "nandu"]


def test_empty_filter_matches_everything():
    assert vod_matches(vod(), ChannelFilter())


def test_player_in_title():
    assert vod_matches(vod(), ChannelFilter(players_1=("MkLeo",)))
    assert not vod_matches(vod(), ChannelFilter(players_1=("Zackray",)))


def test_player_from_detected_players():
    v = vod(title="Grand Finals", players=("Zackray", "Sparg0"))
    assert vod_matches(v, ChannelFilter(players_1=("zackray",)))


def test_player_whole_token_not_substring():
    assert not vod_matches(vod(title="Foxy vs Tweek"), ChannelFilter(players_1=("Fox",)))
    assert vod_matches(vod(title="Fox vs Tweek"), ChannelFilter(players_1=("Fox",)))


def test_accents_and_case_insensitive():
    assert vod_matches(vod(title="JOSÉ vs Tweek"), ChannelFilter(players_1=("jose",)))
    assert vod_matches(vod(title="jose vs Tweek"), ChannelFilter(players_1=("José",)))


def test_both_player_sides_required_when_enforced():
    flt = ChannelFilter(players_1=("MkLeo",), players_2=("Zackray",))
    assert not vod_matches(vod(), flt)
    assert vod_matches(vod(title="MkLeo vs Zackray"), flt)


def test_enforce_player_false_ignores_list():
    flt = ChannelFilter(players_1=("Zackray",), enforce_player_1=False)
    assert vod_matches(vod(), flt)


def test_characters_ignored_when_not_enforced():
    assert vod_matches(vod(), ChannelFilter(characters_1=("Mario",)))


def test_characters_required_when_enforced():
    flt = ChannelFilter(characters_1=("Mario",), enforce_character_1=True)
    assert not vod_matches(vod(), flt)
    assert vod_matches(vod(title="MkLeo (Mario) vs Tweek"), flt)


def test_character_matches_translation_alias():
    flt = ChannelFilter(characters_1=("Mario",), enforce_character_1=True)
    v = vod(title="MkLeo マリオ vs Tweek")
    assert not vod_matches(v, flt)
    assert vod_matches(v, flt, {"Mario": ("マリオ",)})


def test_character_matches_detected_id():
    flt = ChannelFilter(characters_1=("Donkey Kong",), enforce_character_1=True)
    assert vod_matches(vod(characters=("donkey_kong",)), flt)
    assert not vod_matches(vod(characters=("joker",)), flt)


def test_player_and_character_lists_are_independent_per_side():
    flt = ChannelFilter(players_1=("MkLeo",), players_2=("Tweek",),
                        characters_1=("Joker",), characters_2=("Sora",),
                        enforce_character_1=True, enforce_character_2=True)
    assert vod_matches(vod(title="MkLeo vs Tweek Joker Sora"), flt)
    assert not vod_matches(vod(title="MkLeo vs Tweek Joker"), flt)
    assert not vod_matches(vod(title="MkLeo vs Tweek Sora"), flt)
