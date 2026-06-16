"""Tests for summarizer/locales — locale loading and locale-aware prompts."""

from __future__ import annotations

import pytest

from daily_briefing.config import OutputConfig
from daily_briefing.sources.base import SourceResult
from daily_briefing.summarizer.locales import clear_cache, list_locales, load_locale
from daily_briefing.summarizer.prompts import build_prompt


class TestLocaleLoader:
    """Locale loading and caching."""

    def clear_locale_cache(self):
        clear_cache()

    def test_load_en_locale(self):
        loc = load_locale("en")
        assert "system_instruction" in loc
        assert "format" in loc
        assert loc["format"]["generate"] == "Generate the message NOW:"
        assert loc["format"]["header"] == "TODAY'S DATA"

    def test_load_de_locale(self):
        loc = load_locale("de")
        assert loc["format"]["generate"] == "Generiere JETZT die Nachricht:"
        assert loc["format"]["header"] == "HEUTIGE DATEN"
        assert loc["format"]["error_prefix"] == "NICHT VERFÜGBAR"

    def test_unknown_locale_falls_back_to_en(self):
        loc = load_locale("xx")
        assert loc["format"]["generate"] == "Generate the message NOW:"

    def test_list_locales(self):
        langs = list_locales()
        assert "en" in langs
        assert "de" in langs

    def test_locale_caching(self):
        clear_cache()
        loc1 = load_locale("en")
        loc2 = load_locale("en")
        assert loc1 is loc2  # same object due to caching

    def test_en_locale_has_required_keys(self):
        en = load_locale("en")
        assert "system_instruction" in en
        assert "format" in en
        assert "source_labels" in en
        assert "diff" in en
        f = en["format"]
        for key in ("header", "output", "max_chars", "tone", "emoji_on",
                     "emoji_off", "structure", "no_bullets", "mention_errors",
                     "generate", "yesterday", "error_prefix"):
            assert key in f, f"Missing format key: {key}"

    def test_de_locale_has_required_keys(self):
        de = load_locale("de")
        assert "system_instruction" in de
        assert "format" in de
        assert "source_labels" in de


class TestLocaleAwarePrompts:
    """Prompt building with locale support."""

    def make_results(self) -> list[SourceResult]:
        return [
            SourceResult(name="weather", priority=10,
                         data={"location": "Berlin", "condition": "Sunny", "temperature": 22.0}),
        ]

    def test_en_prompt(self):
        results = self.make_results()
        prompt = build_prompt(results, config=OutputConfig(max_length=100), lang="en")
        assert "TODAY'S DATA" in prompt
        assert "WEATHER" in prompt
        assert "Generate the message NOW:" in prompt
        assert "Maximum 100 characters" in prompt
        assert "HEUTIGE DATEN" not in prompt

    def test_de_prompt(self):
        results = self.make_results()
        prompt = build_prompt(results, config=OutputConfig(max_length=100), lang="de")
        assert "HEUTIGE DATEN" in prompt
        assert "WETTER" in prompt
        assert "Generiere JETZT" in prompt
        assert "Maximal 100 Zeichen" in prompt

    def test_default_lang_is_en(self):
        results = self.make_results()
        prompt = build_prompt(results, config=OutputConfig(max_length=100))
        assert "Generate the message NOW:" in prompt

    def test_lang_from_config(self):
        results = self.make_results()
        config = OutputConfig(max_length=100, lang="de")
        prompt = build_prompt(results, config=config)
        assert "Generiere JETZT" in prompt

    def test_en_vs_de_differ(self):
        results = self.make_results()
        en = build_prompt(results, config=OutputConfig(), lang="en")
        de = build_prompt(results, config=OutputConfig(), lang="de")
        assert en != de

    def test_prompt_includes_error_source(self):
        results = [
            SourceResult(name="weather", priority=10,
                         data={"location": "Berlin", "condition": "Sunny"}),
            SourceResult(name="calendar", priority=20, data=None,
                         error="Calendar API error"),
        ]
        prompt = build_prompt(results, config=OutputConfig(), lang="en")
        assert "NOT AVAILABLE" in prompt or "Calendar" in prompt

    def test_prompt_source_labels(self):
        """Source names use locale labels, not raw names."""
        results = [
            SourceResult(name="bahn", priority=10,
                         data={"station": "Hauptbahnhof", "departures": []}),
        ]
        en = build_prompt(results, config=OutputConfig(), lang="en")
        assert "TRANSIT" in en

        de = build_prompt(results, config=OutputConfig(), lang="de")
        assert "BAHN" in de
