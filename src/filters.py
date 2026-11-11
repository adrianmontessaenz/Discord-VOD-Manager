"""Per-channel VOD filters. Pure logic: no Discord, no storage."""
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from repositories.models import Vod


def tokenize(text: str) -> List[str]:
    """NFKD, strip accents, lowercase, split on non-word characters and underscores."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
    return [t for t in re.split(r"[\W_]+", stripped) if t]


@dataclass(frozen=True)
class ChannelFilter:
    players_1: Tuple[str, ...] = ()
    players_2: Tuple[str, ...] = ()
    characters_1: Tuple[str, ...] = ()
    characters_2: Tuple[str, ...] = ()
    enforce_player_1: bool = True
    enforce_player_2: bool = True
    enforce_character_1: bool = False
    enforce_character_2: bool = False


def _contains_tokens(haystack: Sequence[str], needle: Sequence[str]) -> bool:
    n = len(needle)
    return n > 0 and any(list(haystack[i:i + n]) == list(needle) for i in range(len(haystack) - n + 1))


def _is_non_ascii_only(name: str) -> bool:
    letters = [c for c in name if c.isalnum()]
    return bool(letters) and all(ord(c) > 127 for c in letters)


def _name_matches(name: str, title_tokens: List[str], detected: Iterable[str]) -> bool:
    tokens = tokenize(name)
    if not tokens:
        return False
    if _is_non_ascii_only(name):
        if "".join(tokens) in "".join(title_tokens):
            return True
    elif _contains_tokens(title_tokens, tokens):
        return True
    joined = "".join(tokens)
    return any("".join(tokenize(d)) == joined for d in detected)


def _satisfied(entries: Sequence[str], enforce: bool, title_tokens: List[str],
               detected: Iterable[str], aliases: Optional[Dict[str, Tuple[str, ...]]] = None) -> bool:
    if not entries or not enforce:
        return True
    detected = list(detected)
    for entry in entries:
        names = [entry] + list((aliases or {}).get(entry, ()))
        if any(_name_matches(n, title_tokens, detected) for n in names):
            return True
    return False


def vod_matches(vod: Vod, flt: ChannelFilter,
                char_aliases: Optional[Dict[str, Tuple[str, ...]]] = None) -> bool:
    """A criterion holds when its list is empty, its enforce flag is off, or one entry matches."""
    title = tokenize(vod.title)
    return (
        _satisfied(flt.players_1, flt.enforce_player_1, title, vod.players)
        and _satisfied(flt.players_2, flt.enforce_player_2, title, vod.players)
        and _satisfied(flt.characters_1, flt.enforce_character_1, title, vod.characters, char_aliases)
        and _satisfied(flt.characters_2, flt.enforce_character_2, title, vod.characters, char_aliases)
    )
