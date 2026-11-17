#!/usr/bin/env python3
"""Conservative organisation-name resolution shared by Signal North builders.

Purpose: let a headline that names an organisation exactly as an official
source lists it (FINTRAC notice, CIRO case, OSFI register, sanctions list, ...)
link to that organisation's record.

Safety rules (a name match is never evidence of wrongdoing):
* Only organisations are indexed, never natural persons.
* Matching is whole-phrase on word boundaries after removing legal suffixes
  ("Inc.", "Ltd", "Limited", "N.A.") and accents. No fuzzy or substring guessing.
* Single-word names are only matched when they come from the curated alias list.
* Names made only of generic words ("First National Bank") are never matched.
* A phrase that resolves to more than one distinct entity is dropped entirely.
"""
from __future__ import annotations

import re
import unicodedata

LEGAL_SUFFIXES = {
    "inc", "incorporated", "ltd", "ltee", "limited", "limitee", "corp",
    "corporation", "co", "company", "llc", "llp", "lp", "plc", "sa", "ag",
    "gmbh", "bv", "nv", "pte", "pty", "sarl", "srl", "spa", "ulc", "the",
    "na", "fsb", "ssb", "sas", "ab", "oy", "as", "kk", "jsc", "ojsc", "pjsc",
    "ooo", "zao", "fzco", "fze", "fzc", "dmcc", "wll", "sdn", "bhd",
    "ou", "sia", "uab", "kft", "doo", "ltda", "lda", "sl", "spolka", "aps",
    "asa", "oyj", "sro", "tov", "pllc", "lc", "ltd", "pvt", "private",
}
# "N.A." / "National Association" designate a US national bank charter.
SUFFIX_PHRASES = ("national association", "n a", "sp z o o", "s r o", "s a de c v", "private limited", "pvt ltd")

GENERIC = {
    "bank", "banks", "banque", "national", "first", "community", "savings",
    "trust", "credit", "union", "unions", "caisse", "populaire", "federal",
    "state", "financial", "finance", "citizens", "farmers", "peoples",
    "people", "security", "american", "united", "home", "city", "county",
    "group", "holdings", "holding", "services", "service", "capital",
    "investments", "investment", "international", "global", "of", "and",
    "canada", "canadian", "america", "us", "usa", "new", "north", "south",
    "east", "west", "central", "commerce", "commercial", "merchants",
    "valley", "mutual", "insurance", "exchange", "money", "the", "de", "du",
    "des", "la", "le", "et", "corporation", "realty", "real", "estate",
    "securities", "partners", "management", "general", "standard", "royal",
    "heritage", "pacific", "atlantic", "northern", "southern", "western",
    "eastern", "metro", "city", "town", "country", "village", "summit",
    "liberty", "premier", "pioneer", "century", "frontier", "guaranty",
    "home", "building", "society", "employees", "teachers", "educators",
    "police", "fire", "postal", "health", "school", "church", "church's",
    "trading", "technology", "technologies", "solutions", "systems",
    "consulting", "enterprises", "ventures", "industries", "import",
    "export", "foundation", "association", "agency", "centre", "center",
    "small", "business", "armed", "forces", "st", "saint", "san", "santa",
    "los", "las", "el", "del", "open", "digital", "online", "direct",
    "private", "public", "family", "great", "lake", "river", "bay", "island",
    "county", "township", "coast", "shore", "valley", "mountain", "plains",
}
CURATED_TOO_GENERIC = {"national bank", "first national bank", "united bank"}
# Words that may legitimately appear lower-case inside a proper name.
CONNECTORS = {"of", "and", "de", "du", "des", "la", "le", "et", "the", "for", "d", "l"}
# A match immediately followed by one of these is the front part of a longer,
# different organisation name ("Nova Scotia Securities Commission").
ORG_HEADS = {
    "commission", "commissioner", "authority", "regulator", "council",
    "university", "college", "police", "department", "ministry", "agency",
    "board", "court", "tribunal", "office", "service", "association", "union",
    "securities", "bank", "group", "foundation", "institute", "society",
}
# Trailing words that may be omitted in headlines ("Wells Fargo" for
# "Wells Fargo Bank"). Only used when what remains is still distinctive.
BRAND_TRAILERS = {
    "bank", "financial", "group", "holdings", "holding", "trust", "company",
    "bancorp", "bancshares", "corporation", "services", "securities",
}
ORG_MARKERS = re.compile(
    r"\b(bank|banque|ltd|limited|limit[eé]e|inc|llc|llp|plc|pte|pty|corp|"
    r"corporation|company|society|group|trust|capital|securities|financial|"
    r"services|exchange|holdings|credit union|caisse|n\.?a\.?|ag|s\.?a\.?|"
    r"gmbh|partners|fund|investments?|markets|insurance|assurance|payments?|"
    r"realty|casino|lottery|gaming|foundation|association|council|"
    r"authority|ministry|church)\b",
    re.I,
)
INDIVIDUAL_MARKERS = re.compile(r"\b(individuals?|persons?|people|directors?|mr|mrs|ms|dr)\b", re.I)


def fold(text) -> str:
    """Lowercase, strip accents and punctuation; 'Ltée' -> 'ltee'."""
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.casefold().replace("&", " and ").replace("'", "")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def core_name(text) -> str:
    """Folded name without leading 'the' or trailing legal-form suffixes."""
    s = fold(text)
    s = re.sub(r"^the ", "", s)
    s = re.sub(r" the$", "", s)  # OSFI style "Bank of Nova Scotia (The)"
    changed = True
    while changed and s:
        changed = False
        for phrase in SUFFIX_PHRASES:
            if s.endswith(" " + phrase):
                s = s[: -len(phrase) - 1].strip()
                changed = True
        parts = s.split()
        if len(parts) > 1 and parts[-1] in LEGAL_SUFFIXES:
            s = " ".join(parts[:-1])
            changed = True
    return s


def looks_like_organisation(name) -> bool:
    raw = str(name or "")
    if not raw.strip() or INDIVIDUAL_MARKERS.search(raw):
        return False
    return bool(ORG_MARKERS.search(raw)) or bool(re.match(r"^\d{5,}", raw.strip()))


def distinctive(phrase: str, curated: bool = False) -> bool:
    tokens = phrase.split()
    if not tokens or len(phrase) < 3:
        return False
    if len(tokens) == 1:
        # Single words (e.g. "Tangerine", "Meridian") are only trusted when curated.
        return curated and len(phrase) >= 3 and not phrase.isdigit()
    if curated:
        # Human-reviewed alias ("Bank of America"); only a few bare generic
        # phrases stay unmatchable because they occur inside other names.
        return phrase not in CURATED_TOO_GENERIC
    if len(phrase) < 6:
        return False
    return any(t not in GENERIC and not t.isdigit() for t in tokens)


def brand_variant(core: str):
    """'wells fargo bank' -> 'wells fargo'. Every remaining word must be
    distinctive, so 'south georgia bank' never becomes 'south georgia'."""
    tokens = core.split()
    trimmed = list(tokens)
    while len(trimmed) > 2 and trimmed[-1] in BRAND_TRAILERS:
        trimmed.pop()
    if len(trimmed) >= 2 and trimmed[-1] in BRAND_TRAILERS:
        trimmed.pop()
    variant = " ".join(trimmed)
    if (variant != core and len(trimmed) >= 2 and distinctive(variant)
            and all(t not in GENERIC and not t.isdigit() for t in trimmed)):
        return variant
    return None


class EntityMatcher:
    """Phrase dictionary -> entity key, with ambiguity removal."""

    MAX_TOKENS = 10

    def __init__(self):
        self._curated = {}
        self._exact = {}
        self._variant = {}
        self.names = {}
        self._compiled = None

    def add(self, key, name, curated=False, allow_variant=True):
        if not key or not name:
            return
        core = core_name(name)
        if distinctive(core, curated=curated):
            (self._curated if curated else self._exact).setdefault(core, set()).add(key)
            self.names.setdefault(key, str(name).strip())
        if allow_variant and not curated:
            variant = brand_variant(core)
            if variant:
                self._variant.setdefault(variant, set()).add(key)
                self.names.setdefault(key, str(name).strip())
        self._compiled = None

    def compile(self):
        table = {}
        # Human-curated aliases win over register names that reduce to the same
        # phrase (e.g. FDIC "TD Bank, N.A." vs curated "TD Bank").
        for phrase, keys in self._curated.items():
            if len(keys) == 1:
                table[phrase] = (next(iter(keys)), "curated_alias")
        for phrase, keys in self._exact.items():
            if phrase in table:
                continue
            if len(keys) == 1:
                table[phrase] = (next(iter(keys)), "exact_official_name")
        for phrase, keys in self._variant.items():
            if phrase in table or phrase in self._exact or len(keys) != 1:
                continue  # never let a shortened brand collide with a full name
            table[phrase] = (next(iter(keys)), "official_name_without_legal_or_bank_suffix")
        self._compiled = table
        self.ambiguous = sorted(p for p, k in self._exact.items() if len(k) > 1)
        return table

    @staticmethod
    def tokenize(text):
        """Folded tokens plus whether each was written as a proper noun."""
        raw = str(text or "")
        shouting = raw.upper() == raw
        tokens, caps = [], []
        for word in re.findall(r"[^\W_]+(?:['’][^\W_]+)*|&", raw):
            for t in fold(word).split():
                tokens.append(t)
                caps.append(shouting or word[0].isupper() or word[0].isdigit() or word == "&")
        return tokens, caps

    def _proper(self, tokens, caps, i, n):
        if not all(caps[j] or tokens[j] in CONNECTORS for j in range(i, i + n)):
            return False
        nxt = i + n
        if nxt < len(tokens) and caps[nxt] and tokens[nxt] in ORG_HEADS:
            return False
        return True

    def find(self, text):
        """Longest non-overlapping proper-noun phrase matches in a headline."""
        table = self._compiled if self._compiled is not None else self.compile()
        tokens, caps = self.tokenize(text)
        hits = []
        i = 0
        while i < len(tokens):
            matched = None
            for n in range(min(self.MAX_TOKENS, len(tokens) - i), 0, -1):
                phrase = " ".join(tokens[i:i + n])
                if phrase in table and self._proper(tokens, caps, i, n):
                    matched = (n, phrase, *table[phrase])
                    break
            if matched:
                n, phrase, key, basis = matched
                hits.append({"key": key, "phrase": phrase, "basis": basis})
                i += n
            else:
                i += 1
        seen = set()
        return [h for h in hits if not (h["key"] in seen or seen.add(h["key"]))]
