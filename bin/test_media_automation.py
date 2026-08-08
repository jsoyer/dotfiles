#!/usr/bin/env python3
"""Regression tests for media_automation filename parsing.

Uses the stdlib `unittest` on purpose: the NAS hosts have no pytest, so these
must run anywhere with just `python3 ~/bin/test_media_automation.py`.

Origin: a season-less release (Space.Adventure.Cobra.1982.TV.Series.E01) was
parsed as a movie and 31 episodes were filed into the movie library. These
tests pin the parsing contract so that regression cannot come back silently.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import media_automation as ma  # noqa: E402

# Year hint fallback used by import_tv_item for season-less releases.
FILE_YEAR_RE = re.compile(r'(?:^|[.\s_-])\(?((?:19|20)\d{2})\)?(?=[.\s_-])')


class MoviesMustNotParseAsEpisodes(unittest.TestCase):
    """Movie releases must never be mistaken for episodes."""

    NAMES = [
        'Dune.Part.Two.2024.MULTi.2160p.UHD.BluRay.x265.10bit.HDR-GRP.mkv',
        'Blade.Runner.2049.2017.MULTi.2160p.BluRay.x265-GRP.mkv',
        'E.T.the.Extra-Terrestrial.1982.1080p.BluRay.x264.mkv',
        'Se7en.1995.1080p.BluRay.mkv',
        'Ocean.s.Eleven.2001.1080p.mkv',
        'Star.Wars.Episode.IV.A.New.Hope.1977.1080p.BluRay.mkv',
        'The.Matrix.1999.MULTi.1080p.BluRay.x264-AAA.mkv',
        'Cobra.1986.MULTi.1080p.BluRay.x264-XXX.mkv',
        'Interstellar.2014.MULTi.VFF.2160p.HDR.x265.DTS-HD.MA.5.1.mkv',
        'Le.Cinquieme.Element.1997.MULTi.1080p.BluRay.x264-AAA.mkv',
        'Mission.Impossible.Fallout.2018.MULTi.1080p.mkv',
        'Fast.and.Furious.9.2021.TRUEFRENCH.1080p.WEB-DL.x264.mkv',
    ]

    def test_movies_are_not_episodes(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                title, season, episodes = ma.parse_episode_filename(name, name)
                self.assertIsNone(title, f'{name} was parsed as S{season} {episodes}')


class EpisodesMustParse(unittest.TestCase):
    """Episode releases must yield the right title, season and episode list."""

    CASES = [
        # Classic SxxExx
        ('Breaking.Bad.S03E07.1080p.BluRay.x264-GRP.mkv', 'Breaking Bad', 3, [7]),
        ('The.Wire.S01E01E02.1080p.mkv', 'The Wire', 1, [1, 2]),
        ('S.W.A.T.2017.S01E03.1080p.mkv', 'S W A T', 1, [3]),
        # NxNN
        ('Friends.2x05.720p.mkv', 'Friends', 2, [5]),
        # Season-less — the bug that started all this
        ('Space.Adventure.Cobra.1982.TV.Series.E01.MULTi.1080p.BluRay.x265.10bits-NSP.mkv',
         'Space Adventure Cobra', 1, [1]),
        ('Space.Adventure.Cobra.1982.TV.Series.E31.FiNAL.MULTi.1080p.BluRay.x265.10bits-NSP.mkv',
         'Space Adventure Cobra', 1, [31]),
        ('Show.Name.-.Ep07.1080p.mkv', 'Show Name', 1, [7]),
        ('Some.Anime.E05-E06.MULTi.1080p.mkv', 'Some Anime', 1, [5, 6]),
        # Season advertised outside the episode token
        ('Naruto.Shippuden.Saison.5.E12.VOSTFR.1080p.WEB-DL.x264.mkv',
         'Naruto Shippuden', 5, [12]),
    ]

    def test_episodes_parse_correctly(self):
        for name, title, season, episodes in self.CASES:
            with self.subTest(name=name):
                self.assertEqual(ma.parse_episode_filename(name, name), (title, season, episodes))

    def test_season_hint_comes_from_parent_directory(self):
        parsed = ma.parse_episode_filename('Show.E05.mkv', 'Show.Season.3.1080p')
        self.assertEqual(parsed, ('Show', 3, [5]))

    def test_season_defaults_to_one_without_any_hint(self):
        self.assertEqual(ma.parse_episode_filename('Show.E05.mkv', 'Show')[1], 1)


class TitleCleaning(unittest.TestCase):
    """Release noise must be stripped before querying TMDb."""

    def test_release_noise_is_removed(self):
        cleaned = ma.clean_series_title('Space.Adventure.Cobra.1982.TV.Series')
        self.assertEqual(cleaned, 'Space Adventure Cobra')

    def test_season_marker_is_removed(self):
        self.assertEqual(ma.clean_series_title('Naruto Shippuden Saison 5'), 'Naruto Shippuden')

    def test_quality_and_codec_noise_is_removed(self):
        cleaned = ma.clean_series_title('Some Show MULTi 1080p BluRay x265 10bits')
        self.assertEqual(cleaned, 'Some Show')


class YearHint(unittest.TestCase):
    """import_tv_item derives a year hint used to disambiguate TMDb matches."""

    CASES = [
        ('Doctor.Who.(2005).S01E01.1080p', '2005'),
        ('Show.1982.TV.Series.E01.MULTi.1080p', '1982'),
        ('Space.Adventure.Cobra.1982.TV.Series.E01.MULTi.1080p.BluRay.x265.10bits-NSP', '1982'),
    ]

    def test_year_is_extracted_with_and_without_parentheses(self):
        for stem, expected in self.CASES:
            with self.subTest(stem=stem):
                match = FILE_YEAR_RE.search(stem)
                self.assertIsNotNone(match, f'no year found in {stem}')
                self.assertEqual(match.group(1), expected)


class EpisodeCode(unittest.TestCase):
    """Destination filenames must stay Kodi-friendly."""

    def test_single_episode(self):
        self.assertEqual(ma.build_episode_code(1, [1]), 'S01E01')

    def test_double_episode(self):
        self.assertEqual(ma.build_episode_code(2, [5, 6]), 'S02E05-E06')


if __name__ == '__main__':
    unittest.main(verbosity=2)
