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

    # Jeton SxxExx en tete de nom, rencontre en conditions reelles sur un
    # episode depose a la main : le parseur le rejetait faute de titre devant.
    LEADING_TOKEN = [
        ('S018E30 Pokémon - Pikachu en vedette !.mp4', 'Pokémon', 18, [30]),
        ('S01E05 Breaking Bad - Un titre.mkv', 'Breaking Bad', 1, [5]),
        ('S1E5 Show - Titre.mkv', 'Show', 1, [5]),
        ('S05E01E02 Show - Double.mkv', 'Show', 5, [1, 2]),
    ]

    def test_leading_token_is_parsed(self):
        for name, title, season, episodes in self.LEADING_TOKEN:
            with self.subTest(name=name):
                self.assertEqual(ma.parse_episode_filename(name, 'peu importe'),
                                 (title, season, episodes))

    def test_leading_token_without_show_falls_back_to_parent(self):
        # "S18E30 - Titre" ne nomme pas la serie : le tiret en tete l'indique.
        parsed = ma.parse_episode_filename('S18E30 - Pikachu en vedette !.mp4', 'Pokemon')
        self.assertEqual(parsed, ('Pokemon', 18, [30]))

    def test_leading_token_does_not_swallow_the_episode_title(self):
        # Sans le garde-fou, "Pikachu en vedette" serait pris pour la serie.
        title, _, _ = ma.parse_episode_filename('S18E30 - Pikachu en vedette !.mp4', 'Pokemon')
        self.assertNotIn('Pikachu', title)

    def test_classic_naming_still_wins(self):
        # Le motif en tete ne doit pas perturber les noms de release habituels.
        self.assertEqual(ma.parse_episode_filename('Breaking.Bad.S03E07.1080p.mkv', 'x'),
                         ('Breaking Bad', 3, [7]))

    def test_season_hint_comes_from_parent_directory(self):
        parsed = ma.parse_episode_filename('Show.E05.mkv', 'Show.Season.3.1080p')
        self.assertEqual(parsed, ('Show', 3, [5]))

    def test_season_defaults_to_one_without_any_hint(self):
        self.assertEqual(ma.parse_episode_filename('Show.E05.mkv', 'Show')[1], 1)


class TmdbCandidateChoice(unittest.TestCase):
    """TMDb ne classe pas ses resultats par pertinence : il faut choisir."""

    # Reproduit le cas reel : chercher "Attack on Titan" renvoie un spin-off
    # chibi avant la vraie serie, bien plus populaire.
    RESULTATS = [
        {'id': 224499, 'name': 'ちみキャラ劇場', 'original_name': 'ちみキャラ劇場', 'popularity': 5},
        {'id': 63510, 'name': "L'Attaque des Titans - Junior High School",
         'original_name': 'Attack on Titan: Junior High', 'popularity': 9},
        {'id': 1429, 'name': "L'Attaque des Titans",
         'original_name': 'Attack on Titan', 'popularity': 29},
    ]

    def test_popularity_beats_tmdb_ordering(self):
        choisi = ma._meilleur_candidat_tv('Attack on Titan', self.RESULTATS)
        self.assertEqual(choisi['id'], 1429)

    def test_exact_title_wins_over_a_more_popular_one(self):
        resultats = [
            {'id': 1, 'name': 'Dragon Ball Z', 'original_name': 'Dragon Ball Z', 'popularity': 68},
            {'id': 2, 'name': 'Dragon Ball', 'original_name': 'Dragon Ball', 'popularity': 20},
        ]
        self.assertEqual(ma._meilleur_candidat_tv('Dragon Ball', resultats)['id'], 2)

    def test_original_title_also_counts_as_exact(self):
        resultats = [
            {'id': 1, 'name': 'Autre chose', 'original_name': 'Autre', 'popularity': 90},
            {'id': 2, 'name': "L'Attaque des Titans",
             'original_name': 'Attack on Titan', 'popularity': 29},
        ]
        self.assertEqual(ma._meilleur_candidat_tv('Attack on Titan', resultats)['id'], 2)

    def test_missing_popularity_does_not_crash(self):
        resultats = [{'id': 1, 'name': 'Sans note'}, {'id': 2, 'name': 'Autre', 'popularity': 3}]
        self.assertEqual(ma._meilleur_candidat_tv('Inconnu', resultats)['id'], 2)


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


class AbsoluteNumbering(unittest.TestCase):
    """anime_absolute_plan maps long-running anime absolute numbers onto seasons."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        path = Path(__file__).resolve().parent / 'anime_absolute_plan.py'
        spec = importlib.util.spec_from_file_location('anime_absolute_plan', path)
        cls.plan = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.plan)
        # One Piece-like shape: 61 + 16 + 14 episodes over three seasons.
        cls.table = cls.plan.build_absolute_table([
            {'season_number': 0, 'episode_count': 5},    # specials, must be skipped
            {'season_number': 1, 'episode_count': 61},
            {'season_number': 2, 'episode_count': 16},
            {'season_number': 3, 'episode_count': 14},
        ])

    EXTRACTION = [
        ('[SubsPlease] One Piece - 1100 (1080p) [A1B2C3D4].mkv', 1100),
        ('[Erai-raws] One Piece - 1050 [1080p][Multiple Subtitle].mkv', 1050),
        ('One Piece - 0587 VOSTFR 1080p.mkv', 587),
        ('One.Piece.E1050.MULTi.1080p.WEB.x264-GRP.mkv', 1050),
        ('One Piece 1080 VOSTFR 1080p x265 10bits.mkv', 1080),
        ('[HorribleSubs] One Piece - 900 [720p].mkv', 900),
        ('One Piece - Episode 1015 [1080p][AAC].mkv', 1015),
        ('One.Piece.-.061.VF.2160p.HEVC.mkv', 61),
        ('[Group] One Piece - 1000v2 [1080p][DEADBEEF].mkv', 1000),
        ('One Piece - 1050.srt', 1050),
        ('One Piece - 500 (2011) [1080p] 5.1.mkv', 500),
    ]

    def test_absolute_number_extraction(self):
        for name, expected in self.EXTRACTION:
            with self.subTest(name=name):
                self.assertEqual(self.plan.extract_absolute(name), expected)

    # Real names from a season-organised One Piece library. Numbers live in the
    # episode titles; reading them as absolute filed episodes into wrong seasons.
    SEASON_ORGANISED = [
        'Season 17/One Piece - 17x53 - Rançon de 500 millions - La cible est Usoland !.mkv',
        'Season 19/One Piece - 19x05 - Zéro et Quatre. Une confrontation avec le Germa 66 !.mkv',
        'Season 19/One Piece - 19x60 - L\'armée maléfique. La transformation des Germa 66 !.mkv',
        'Season 13/One Piece - 13x03 - La dure lutte de Brook.mkv',
        'One Piece - S13E03 - Deja au format Infuse.mkv',
    ]

    def test_season_organised_names_are_not_read_as_absolute(self):
        for name in self.SEASON_ORGANISED:
            with self.subTest(name=name):
                self.assertIsNone(self.plan.extract_absolute(name))

    def test_specials_are_excluded_from_the_table(self):
        self.assertEqual([row[0] for row in self.table], [1, 2, 3])

    def test_absolute_maps_to_the_right_season(self):
        cases = {1: (1, 1), 61: (1, 61), 62: (2, 1), 77: (2, 16), 78: (3, 1), 91: (3, 14)}
        for absolute, expected in cases.items():
            with self.subTest(absolute=absolute):
                self.assertEqual(self.plan.absolute_to_season_episode(absolute, self.table), expected)

    def test_out_of_range_is_reported_not_guessed(self):
        self.assertIsNone(self.plan.absolute_to_season_episode(92, self.table))

    def test_unparsable_names_are_reported_not_renamed(self):
        plan, unresolved = self.plan.plan_renames(
            ['One Piece - 0001.mkv', 'bande-annonce.mkv', 'lisez-moi.txt'], self.table, 'One Piece')
        self.assertEqual(len(plan), 1)
        self.assertEqual(len(unresolved), 2)

    def test_destination_follows_the_plex_convention(self):
        plan, _ = self.plan.plan_renames(['One Piece - 0062.mkv'], self.table, 'One Piece')
        self.assertEqual(plan[0][1], 'Season 02/One Piece - S02E01.mkv')

    def test_shell_quoting_survives_apostrophes(self):
        quoted = self.plan.shell_quote("L'ile.mkv")
        self.assertEqual(quoted, "'L'\\''ile.mkv'")


class AbsoluteShowRegistry(unittest.TestCase):
    """Only registered shows may reach a remote library."""

    @classmethod
    def setUpClass(cls):
        import media_absolute_shows
        cls.mod = media_absolute_shows
        cls.show = media_absolute_shows.AbsoluteShow(
            name='One Piece', destination='gdrive:Infuse/One Piece',
            mapping_file=Path('/nonexistent.json'), aliases=('One Piece', 'One.Piece'),
            lookahead=1)
        # Same shape as the real library: 23 seasons, last absolute 1172.
        cls.mapping = media_absolute_shows.build_mapping_from_listing(
            [f'Season {s:02d}/One Piece - {s}x{e:02d} - Titre.mkv'
             for s, count in [(1, 8), (2, 22), (3, 17)] for e in range(1, count + 1)])

    NOT_REGISTERED = [
        'Naruto.Shippuden.E120.VOSTFR.1080p.mkv',
        '[SubsPlease] Frieren - 28 (1080p).mkv',
        'Blade.Runner.2049.2017.MULTi.2160p.BluRay.x265-GRP.mkv',
        'Dune.Part.Two.2024.MULTi.2160p.mkv',
        'Breaking.Bad.S03E07.1080p.mkv',
    ]

    def test_unregistered_shows_never_match(self):
        for name in self.NOT_REGISTERED:
            with self.subTest(name=name):
                self.assertIsNone(self.mod.match_show(name, [self.show]))

    def test_registered_show_matches_its_aliases(self):
        for name in ['[SubsPlease] One Piece - 1173 (1080p) [A1B2C3D4].mkv',
                     'One.Piece.1173.MULTi.1080p.WEB.x264-GRP.mkv',
                     'One Piece - 1173 VOSTFR.mkv']:
            with self.subTest(name=name):
                self.assertIs(self.mod.match_show(name, [self.show]), self.show)

    def test_a_title_mentioned_mid_name_does_not_match(self):
        self.assertIsNone(
            self.mod.match_show('Documentaire sur One Piece - 03.mkv', [self.show]))

    def test_empty_registry_matches_nothing(self):
        self.assertIsNone(self.mod.match_show('One Piece - 1173.mkv', []))

    def test_mapping_is_contiguous_across_seasons(self):
        self.assertEqual(self.mapping.seasons, [(1, 1, 8), (2, 9, 30), (3, 31, 47)])
        self.assertEqual(self.mapping.last_absolute, 47)

    def test_known_absolute_resolves(self):
        self.assertEqual(self.mapping.resolve(9), (2, 1))
        self.assertEqual(self.mapping.resolve(47), (3, 17))

    def test_next_episode_extends_the_last_season(self):
        target, season, episode = self.mod.plan_episode(
            'One Piece - 0048.mkv', self.show, self.mapping)
        self.assertEqual((season, episode), (3, 18))
        self.assertEqual(target, 'Season 03/One Piece - S03E18.mkv')

    def test_jumping_past_the_library_is_refused_not_guessed(self):
        with self.assertRaises(ValueError) as caught:
            self.mod.plan_episode('One Piece - 0060.mkv', self.show, self.mapping)
        self.assertIn('nouvelle saison probable', str(caught.exception))

    def test_season_organised_names_are_refused(self):
        with self.assertRaises(ValueError):
            self.mod.plan_episode('One Piece - 3x05 - Titre.mkv', self.show, self.mapping)

    def test_push_is_a_server_side_move_with_rate_limit(self):
        command = self.mod.push_episode('/inbox/ep.mkv', 'gdrive:X/ep.mkv', dry_run=True)
        self.assertEqual(command[:2], ['rclone', 'moveto'])
        self.assertIn('--tpslimit', command)


class EpisodeFilenamesCarryTheirTitle(unittest.TestCase):
    """Imported episodes must be named like the rest of the library.

    Origin: a freshly imported episode landed as "Pokemon - S01E18.mkv" while
    every file around it carried its title. A bare code tells the viewer
    nothing, and it makes a misfiled episode impossible to spot by eye — the
    only clue that something is wrong would be the number itself, which is
    precisely what one cannot trust when the import went astray.
    """

    def target(self, suffix='.mkv', **extra):
        return ma.get_episode_target_name(
            Path(f'source{suffix}'), 'Pokemon', 8, [9], **extra)

    def test_title_is_embedded(self):
        self.assertEqual(self.target(episode_title='Le vieux loup de mer'),
                         'Pokemon - S08E09 - Le vieux loup de mer.mkv')

    def test_absent_title_falls_back_to_the_bare_code(self):
        self.assertEqual(self.target(), 'Pokemon - S08E09.mkv')

    def test_blank_title_counts_as_absent(self):
        self.assertEqual(self.target(episode_title='   '), 'Pokemon - S08E09.mkv')

    def test_illegal_characters_in_the_title_are_stripped(self):
        # TMDb titles routinely carry ':' and '?', which no filesystem accepts.
        self.assertEqual(self.target(episode_title='Qui vole un <oeuf> : la suite ?'),
                         'Pokemon - S08E09 - Qui vole un oeuf la suite.mkv')

    def test_double_episode_keeps_the_range(self):
        self.assertEqual(
            ma.get_episode_target_name(Path('x.mkv'), 'Pokemon', 2, [5, 6],
                                       episode_title='Deux en un'),
            'Pokemon - S02E05-E06 - Deux en un.mkv')

    def test_nfo_follows_the_same_convention(self):
        self.assertEqual(self.target(suffix='.nfo', episode_title='Le vieux loup de mer'),
                         'Pokemon - S08E09 - Le vieux loup de mer.nfo')

    def test_series_name_is_sanitised_like_its_directory(self):
        # import_tv_item sanitises the directory name but passed the raw one to
        # the file, so the same series carried two spellings on disk — and a
        # colon, legal on Linux but not on the SMB shares that serve it.
        self.assertEqual(
            ma.get_episode_target_name(Path('x.mkv'), 'Pokemon : Les horizons', 1, [18],
                                       episode_title='Vole Pikachu'),
            'Pokemon Les horizons - S01E18 - Vole Pikachu.mkv')

    def test_artwork_is_left_alone(self):
        # Cover art is named by its own rules; a title there would break Emby.
        self.assertEqual(
            ma.get_episode_target_name(Path('poster.jpg'), 'Pokemon', 8, [9],
                                       episode_title='Un titre'),
            ma.get_episode_target_name(Path('poster.jpg'), 'Pokemon', 8, [9]))


class SanitizeLeavesNoGapBehind(unittest.TestCase):
    """Removing an illegal character must not leave a hole in its place.

    Origin: TMDb calls the series "Pokemon : Les horizons". Dropping the colon
    left behind the two spaces that surrounded it, and the library grew a
    directory named "Pokemon  Les horizons (2023)" — indistinguishable from the
    correct name to the eye, yet a different string for every tool that
    compares paths.
    """

    def test_a_spaced_colon_does_not_leave_a_double_space(self):
        self.assertEqual(ma.sanitize('Pokemon : Les horizons'), 'Pokemon Les horizons')

    def test_an_unspaced_colon_keeps_the_single_space(self):
        self.assertEqual(ma.sanitize('Pokemon: les Origines'), 'Pokemon les Origines')

    def test_illegal_characters_are_still_removed(self):
        self.assertEqual(ma.sanitize('A/B\\C*D?E"F<G>H|I'), 'ABCDEFGHI')

    def test_surrounding_whitespace_is_still_trimmed(self):
        self.assertEqual(ma.sanitize('  Titre  '), 'Titre')

    def test_ordinary_names_are_left_untouched(self):
        self.assertEqual(ma.sanitize('Pokemon (1997)'), 'Pokemon (1997)')


if __name__ == '__main__':
    unittest.main(verbosity=2)
