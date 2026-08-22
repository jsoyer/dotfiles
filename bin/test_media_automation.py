#!/usr/bin/env python3
"""Regression tests for media_automation filename parsing.

Uses the stdlib `unittest` on purpose: the NAS hosts have no pytest, so these
must run anywhere with just `python3 ~/bin/test_media_automation.py`.

Origin: a season-less release (Space.Adventure.Cobra.1982.TV.Series.E01) was
parsed as a movie and 31 episodes were filed into the movie library. These
tests pin the parsing contract so that regression cannot come back silently.
"""
import contextlib
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


class TheBulkRenamerSpeaksTheImportersLanguage(unittest.TestCase):
    """The library-wide renamer must build the exact name the importer would.

    Origin: its first version reconstructed the name by hand instead of calling
    the importer, and silently dropped the second number of a double episode --
    'S02E01-E02' became 'S02E01', which makes an episode vanish from the
    library without anything looking wrong. A rule copied is a rule that drifts;
    these tests pin the two to a single source.
    """

    @classmethod
    def setUpClass(cls):
        import serie_renommer
        cls.outil = serie_renommer

    def test_base_name_matches_the_importer(self):
        attendu = ma.get_episode_target_name(Path('x.mkv'), 'Serie', 1, [1], 'Un titre')
        self.assertEqual(self.outil.base_cible('Serie', 1, [1], 'Un titre') + '.mkv',
                         attendu)

    def test_double_episode_keeps_both_numbers(self):
        self.assertEqual(self.outil.base_cible('Serie', 2, [5, 6], 'Double'),
                         'Serie - S02E05-E06 - Double')

    def test_series_name_is_sanitised_by_the_shared_rule(self):
        self.assertEqual(self.outil.base_cible('Ma : Serie', 1, [1], 'Titre'),
                         'Ma Serie - S01E01 - Titre')

    def test_the_range_is_captured_not_truncated(self):
        found = self.outil.CODE.search('Serie - S02E05-E06 - Double.mkv')
        self.assertEqual((found.group('s'), found.group('e'), found.group('e2')),
                         ('02', '05', '06'))

    def test_long_running_numbering_survives(self):
        found = self.outil.CODE.search('Detective Conan S01E1109.mkv')
        self.assertEqual(found.group('e'), '1109')

    def test_episode_thumbnail_suffix_is_preserved(self):
        self.assertEqual(self.outil.suffixe_de('X - S01E01-thumb.jpg'), '-thumb.jpg')

    def test_a_plain_extension_is_returned_otherwise(self):
        self.assertEqual(self.outil.suffixe_de('X - S01E01.mkv'), '.mkv')


class AYearFromASeasonFolderMustNotHideTheSeries(unittest.TestCase):
    """A release folder names the season's year, not the series' first year.

    Origin: 'Saison 21 (2016) - VOSTFR - YakuboEncodes' handed the importer 2016
    as a first-air-date hint for Detective Conan, which began in 1996. TMDb
    answered with an empty list, search_tmdb_tv gave up before trying anything
    else, and 119 episodes were rejected as 'no TMDb TV match' -- a total
    rejection that reported zero errors, so nothing looked broken.

    A year is a hint, never a requirement: when it yields nothing, the search
    must be retried without it.
    """

    def rejouer(self, annee, reponses):
        """Substitue une couche reseau deterministe le temps d'un appel."""
        appels = []

        def faux_request(path, api_key, params):
            appels.append(dict(params))
            return reponses('first_air_date_year' in params)

        original = ma.tmdb_request
        ma.tmdb_request = faux_request
        try:
            return ma.search_tmdb_tv('Detective Conan', annee, 'cle', 'fr-FR'), appels
        finally:
            ma.tmdb_request = original

    CONAN = {'id': 30983, 'name': 'Détective Conan', 'popularity': 50.0,
             'first_air_date': '1996-01-08'}

    def test_a_year_that_finds_nothing_is_retried_without_it(self):
        trouve, appels = self.rejouer(
            '2016', lambda avec_annee: {'results': [] if avec_annee else [self.CONAN]})
        self.assertIsNotNone(trouve, "la serie doit etre retrouvee sans l'annee")
        self.assertEqual(trouve['id'], 30983)
        self.assertEqual(len(appels), 2, 'une seconde recherche, sans annee, est attendue')
        self.assertNotIn('first_air_date_year', appels[1])

    def test_a_year_that_works_is_not_retried(self):
        trouve, appels = self.rejouer('1996', lambda _: {'results': [self.CONAN]})
        self.assertEqual(trouve['id'], 30983)
        self.assertEqual(len(appels), 1, 'aucune recherche superflue quand la premiere aboutit')

    def test_a_genuinely_unknown_title_still_returns_nothing(self):
        trouve, appels = self.rejouer('2016', lambda _: {'results': []})
        self.assertIsNone(trouve)
        self.assertEqual(len(appels), 2)

    def test_without_a_year_a_single_search_is_made(self):
        trouve, appels = self.rejouer(None, lambda _: {'results': [self.CONAN]})
        self.assertEqual(trouve['id'], 30983)
        self.assertEqual(len(appels), 1)


class LongRunningSeriesMustNotBeTruncated(unittest.TestCase):
    """A four-digit episode number must be read whole, or episodes collide.

    Origin: Detective Conan was converted to absolute numbering, and the
    importer read 'S01E1157' as episode 115, dropping the trailing digit. Ten
    episodes of the 1190s all became 'E119'; eight files landed on numbers that
    already existed and were filed as '(2)', '(3)'... under someone else's
    title. Nothing failed, nothing was logged: the library simply lost episodes
    while its file count stayed right.

    The same guard already protects the audit tools. It was missing where it
    mattered most.
    """

    def parse(self, nom, parent=None):
        return ma.parse_episode_filename(nom, parent)

    def test_four_digit_episode_is_read_whole(self):
        self.assertEqual(self.parse('Détective Conan - S01E1157 - Enquête à Ishikawa.mkv'),
                         ('Détective Conan', 1, [1157]))

    def test_the_highest_numbers_do_not_collapse(self):
        for numero in (1190, 1199, 1200, 1209):
            with self.subTest(numero=numero):
                self.assertEqual(
                    self.parse(f'Détective Conan - S01E{numero} - Titre.mkv')[2], [numero])

    def test_three_digit_numbers_are_unaffected(self):
        self.assertEqual(self.parse('Détective Conan - S01E115 - Titre.mkv')[2], [115])

    def test_two_digit_numbers_are_unaffected(self):
        self.assertEqual(self.parse('Pokemon - S08E09 - Titre.mkv')[2], [9])

    def test_one_piece_absolute_numbering_survives(self):
        self.assertEqual(self.parse('One Piece - S01E1109 - Titre.mkv')[2], [1109])

    def test_double_episode_still_parses(self):
        self.assertEqual(self.parse('Mr. Robot - S02E01-E02 - Titre.mkv')[2], [1, 2])

    def test_a_leading_token_also_reads_four_digits(self):
        self.assertEqual(self.parse('S01E1157 - Enquête à Ishikawa.mkv', 'Détective Conan'),
                         ('Détective Conan', 1, [1157]))


class MoviesDeserveTheSameCareAsSeries(unittest.TestCase):
    """A movie search must pick the film, not whatever TMDb lists first.

    Origin: searching 'X-Men' with year 2000 returns 'X-Men: The Mutant Watch',
    a making-of, ahead of the film itself. Series already had this protection --
    an obscure chibi spin-off once outranked Attack on Titan -- but movies never
    got it, so an import could file a feature under its own documentary.
    """

    FILM = {'id': 36657, 'title': 'X-Men', 'popularity': 40.0,
            'release_date': '2000-07-13'}
    MAKING_OF = {'id': 447399, 'title': 'X-Men : The Mutant Watch',
                 'popularity': 1.2, 'release_date': '2000-11-21'}

    def chercher(self, resultats, annee=None):
        original = ma.tmdb_request
        ma.tmdb_request = lambda path, api_key, params: {'results': resultats}
        try:
            return ma.search_tmdb_movie('X-Men', annee, 'cle', 'fr-FR')
        finally:
            ma.tmdb_request = original

    def test_the_film_wins_over_a_documentary_listed_first(self):
        trouve = self.chercher([self.MAKING_OF, self.FILM], annee=2000)
        self.assertEqual(trouve['id'], 36657)

    def test_exact_title_beats_a_more_popular_neighbour(self):
        bruyant = {'id': 99, 'title': 'X-Men Origins', 'popularity': 900.0,
                   'release_date': '2000-01-01'}
        self.assertEqual(self.chercher([bruyant, self.FILM], annee=2000)['id'], 36657)

    def test_without_an_exact_match_popularity_decides(self):
        a = {'id': 1, 'title': 'Autre chose', 'popularity': 3.0}
        b = {'id': 2, 'title': 'Encore autre chose', 'popularity': 50.0}
        self.assertEqual(self.chercher([a, b])['id'], 2)

    def test_an_empty_result_stays_empty(self):
        self.assertIsNone(self.chercher([]))

    def test_missing_popularity_does_not_crash(self):
        muet = {'id': 7, 'title': 'Sans popularite'}
        self.assertEqual(self.chercher([muet])['id'], 7)


class AYearInTheTitleIsNotAReleaseYear(unittest.TestCase):
    """A four-digit number is only a year if it could plausibly be one.

    Origin: 'Ghost.In.The.Shell.SAC.2045.Sustainable.War.2021...' was read as
    the film 'Ghost In The Shell SAC' released in 2045. The title was truncated
    at the first four digits it met, and TMDb naturally knew nothing of a film
    released twenty years hence -- so the import was skipped.
    """

    def test_a_future_year_is_kept_in_the_title(self):
        titre, annee = ma.parse_filename(
            'Ghost.In.The.Shell.SAC.2045.Sustainable.War.2021.MULTi.1080p.H264-LiHDL.mkv')
        self.assertEqual(annee, '2021')
        self.assertIn('2045', titre)
        self.assertIn('Sustainable War', titre)

    def test_an_ordinary_release_still_parses(self):
        self.assertEqual(ma.parse_filename('Matrix.1999.MULTi.1080p.BluRay.mkv'),
                         ('Matrix', '1999'))

    def test_the_parenthesised_form_is_untouched(self):
        self.assertEqual(ma.parse_filename('Un Film (2002).mkv'), ('Un Film', '2002'))

    def test_a_lone_implausible_year_is_not_taken_as_one(self):
        titre, annee = ma.parse_filename('Blade.Runner.2049.2017.MULTi.1080p.mkv')
        self.assertEqual(annee, '2017')
        self.assertIn('2049', titre)


class ABracketedReleaseGroupMustNotDefeatTheParser(unittest.TestCase):
    """Tags in square brackets are noise around the title, not the title.

    Origin: '[Delivroozzi] Détective Conan - Le Cauchemar Noir de Jais [Film 20]
    [VOSTFR BD x264 1080p]' produced no title at all, and the film was skipped --
    a film that happened to fill a gap the collection audit had reported.
    """

    NOM = ('[Delivroozzi] Détective Conan - Le Cauchemar Noir de Jais '
           '[Film 20] [VOSTFR BD x264 10bits 1080p TrueHD].mkv')

    def test_a_title_is_recovered(self):
        titre, _ = ma.parse_filename(self.NOM)
        self.assertIsNotNone(titre, 'un titre doit être extrait malgré les crochets')
        self.assertIn('Détective Conan', titre)

    def test_the_bracketed_noise_is_gone(self):
        titre, _ = ma.parse_filename(self.NOM)
        for bruit in ('Delivroozzi', 'VOSTFR', '1080p', 'TrueHD'):
            self.assertNotIn(bruit, titre)

    def test_a_bracketed_name_with_a_year_keeps_it(self):
        titre, annee = ma.parse_filename('[Groupe] Un Film (1998) [1080p].mkv')
        self.assertEqual(annee, '1998')
        self.assertIn('Un Film', titre)



class UneReleaseNeDonneJamaisLeTitreSeul(unittest.TestCase):
    """Le nom de fichier porte le titre, mais entoure de marques de release.

    Trois films ont ete ecartes le meme jour avec « no TMDb movie match » : deux
    Dragon Ball Z et un Fullmetal Alchemist, tous trois pourtant absents de la
    collection et donc attendus. Aucun n'etait introuvable — c'est le titre
    soumis a TMDb qui ne ressemblait a rien.
    """

    def test_le_groupe_de_release_ferme_le_nom(self):
        variantes = ma._variantes_titre('Les Mercenaires de L espace - KHAYA')
        self.assertIn('Les Mercenaires de L espace', variantes)

    def test_l_elision_perdue_est_retablie(self):
        # Un systeme de fichiers refuse l'apostrophe ; elle devient un souligne,
        # puis une espace. « L espace » ne se cherche plus.
        self.assertIn("Les Mercenaires de L'espace",
                      ma._variantes_titre('Les Mercenaires de L espace'))

    def test_le_nom_de_saga_et_son_rang_finissent_par_tomber(self):
        variantes = ma._variantes_titre(
            'Dragon Ball Z - FiLM x - Les Mercenaires de L espace - KHAYA')
        self.assertIn("Les Mercenaires de L'espace", variantes)

    def test_un_rang_isole_au_milieu_du_titre_est_retire(self):
        self.assertIn('Fullmetal Alchemist The Revenge of Scar',
                      ma._variantes_titre('Fullmetal Alchemist 2 The Revenge of Scar'))

    def test_la_forme_integrale_est_toujours_essayee_la_premiere(self):
        # Sans quoi un titre raccourci attraperait un homonyme plus populaire.
        for titre in ('Toy Story 2', 'Karate Kid II', 'Dragon Ball Z - Broly'):
            self.assertEqual(ma._variantes_titre(titre)[0], titre)

    def test_une_suite_legitime_ne_perd_pas_son_numero(self):
        # « Toy Story 2 » se trouve des la premiere forme : les variantes qui
        # suivent ne sont jamais atteintes, et le titre reste intact.
        self.assertEqual(ma._variantes_titre('Toy Story 2'), ['Toy Story 2'])

    def test_un_titre_deja_propre_ne_produit_qu_une_forme(self):
        self.assertEqual(ma._variantes_titre('Independence Day'), ['Independence Day'])


class UneSagaNEstPasUnFilm(unittest.TestCase):
    """Deux films d'une meme saga, sortis la meme annee, ne sont pas doublons.

    La phase de fusion des dossiers reunissait « Baddack contre Freezer », « Le
    Combat fratricide » et « Le Robot des glaces » — trois longs metrages
    distincts de 1990 — dans un seul dossier, ou le serveur de medias n'en
    montrait plus qu'un. La cause tenait a un alias tronque : « Dragon Ball Z »,
    la portion qui precede le tiret, nomme la saga et non le film.
    """

    def test_l_alias_tronque_ne_sert_pas_de_cle(self):
        alias = ma._alias_discriminants('Dragon Ball Z - Baddack contre Freezer')
        self.assertNotIn('dragon ball z', alias)
        self.assertIn('dragon ball z baddack contre freezer', alias)

    def test_deux_films_d_une_saga_ne_partagent_aucune_cle(self):
        for gauche, droite in (
            ('Dragon Ball Z - Baddack contre Freezer',
             'Dragon Ball Z - Le Combat fratricide'),
            ('Psycho-Pass - Case 1 - Crime et Châtiment',
             'Psycho-Pass - Case 3 - Par-delà l’amour et la haine'),
        ):
            self.assertFalse(
                ma._alias_discriminants(gauche) & ma._alias_discriminants(droite),
                f'{gauche} et {droite} passeraient pour un seul film')

    def test_un_alias_contenu_dans_un_autre_est_ecarte(self):
        # « Dragon Ball Z - Fusions » produisait l'alias « z », qui ne prefixe
        # aucun autre alias mais figure dans tous : deux films de 1995 se
        # retrouvaient ainsi declares doublons, et fusionnes cinq minutes plus
        # tard par le cron.
        alias = ma._alias_discriminants('Dragon Ball Z - Fusions')
        self.assertNotIn('z', alias)
        self.assertEqual(alias, {'dragon ball z fusions'})

    def test_deux_films_d_une_saga_meme_annee_restent_distincts(self):
        gauche = ma._alias_discriminants('Dragon Ball Z - Fusions')
        droite = ma._alias_discriminants('Dragon Ball Z - L’Attaque du dragon')
        self.assertFalse(gauche & droite)

    def test_une_suite_ne_se_confond_pas_avec_son_premier_volet(self):
        self.assertFalse(ma._alias_discriminants('Dune')
                         & ma._alias_discriminants('Dune - Deuxième partie'))

    def test_un_titre_sans_tiret_garde_son_alias(self):
        self.assertEqual(ma._alias_discriminants('Independence Day'),
                         {'independence day'})

    def test_le_meme_titre_reste_un_doublon(self):
        # La fusion doit continuer de reunir deux dossiers du meme film.
        self.assertTrue(ma._alias_discriminants('Dragon Ball Z - Fusions')
                        & ma._alias_discriminants('Dragon Ball Z - Fusions'))


class UnTitrePeutSuivreLAnnee(unittest.TestCase):
    """Certaines releases placent le titre apres l'annee, derriere un rang.

    « Lupin.III.Special.01.1989.Goodbye.Lady.Liberty.1080p… » ne donnait que
    « Lupin III Special 01 », que TMDb ne connait sous aucun nom : deux films de
    la saga Lupin III — la plus incomplete de la bibliotheque — etaient ecartes
    a chaque passage.
    """

    def test_le_titre_place_apres_l_annee_est_recupere(self):
        titre, annee = ma.parse_filename(
            'Lupin.III.Special.01.1989.Goodbye.Lady.Liberty.1080p.Bluray.x264-Notag.mkv')
        self.assertEqual(titre, 'Lupin III Goodbye Lady Liberty')
        self.assertEqual(annee, '1989')

    def test_le_prefixe_de_saga_est_conserve(self):
        # « From Russia with love » seul ramene le James Bond de 1963 ; le
        # prefixe est ce qui distingue le Lupin III de 1992.
        titre, _ = ma.parse_filename(
            'Lupin.III.Special.04.1992.From.Russia.with.love.1080p.Bluray.x264-Notag.mkv')
        self.assertTrue(titre.startswith('Lupin III'))
        self.assertIn('From Russia with love', titre)

    def test_sans_rang_le_titre_reste_celui_qui_precede(self):
        # Ce qui suit l'annee n'est alors que du bruit de release.
        for nom, attendu in (
            ('Toy Story 2 (1999) MULTi 1080p BluRay x264.mkv', 'Toy Story 2'),
            ('Independence Day (1996) MULTi 1080p.mkv', 'Independence Day'),
            ('Le Parrain 1972 MULTi 1080p BluRay.mkv', 'Le Parrain'),
        ):
            self.assertEqual(ma.parse_filename(nom)[0], attendu)

    def test_un_rang_sans_titre_derriere_ne_change_rien(self):
        titre, _ = ma.parse_filename('Serie Special 02 1990 1080p BluRay x264.mkv')
        self.assertEqual(titre, 'Serie Special 02')


class UnTrouNeDoitPasFausserLeDernierNumero(unittest.TestCase):
    """Le dernier episode connu se lit sur ce qui est present, pas sur le compte.

    Le garde-fou de numerotation absolue deduisait le dernier numero du nombre
    de fichiers. Chaque episode manquant abaissait donc l'estimation d'autant, et
    l'episode suivant se voyait refuse comme « depassant la bibliotheque » : One
    Piece, a qui il manquait un episode, a vu son 1174e ecarte alors qu'il etait
    parfaitement legitime.
    """

    def setUp(self):
        import media_absolute_shows
        self.module = media_absolute_shows

    def test_le_compte_sous_estime_quand_la_serie_a_un_trou(self):
        table = self.module.Mapping(seasons=[(1, 1, 10), (2, 11, 20)], offset=0)
        presents = ({(1, e) for e in range(1, 11) if e != 5}
                    | {(2, e) for e in range(1, 9)})
        self.assertEqual(len(presents), 17)          # ce que comptait l'ancien calcul
        self.assertEqual(table.dernier_present(presents), 18)   # le vrai dernier

    def test_sans_trou_les_deux_lectures_coincident(self):
        table = self.module.Mapping(seasons=[(1, 1, 12)], offset=0)
        presents = {(1, e) for e in range(1, 13)}
        self.assertEqual(table.dernier_present(presents), len(presents))

    def test_le_decalage_de_numerotation_est_respecte(self):
        # One Piece derive d'une unite : le crossover Toriko compte pour la
        # release mais pas pour le referentiel.
        table = self.module.Mapping(seasons=[(1, 1, 10)], offset=1)
        self.assertEqual(table.dernier_present({(1, 10)}), 11)

    def test_une_bibliotheque_vide_ne_promet_rien(self):
        table = self.module.Mapping(seasons=[(1, 1, 10)], offset=0)
        self.assertEqual(table.dernier_present(set()), 0)


class UnNumeroNuApresUnTiret(unittest.TestCase):
    """Les fansubs numerotent « Serie - 124 », sans lettre pour l'annoncer.

    Treize episodes de Pokemon Horizons ont ete ecartes le meme jour avec « no
    TMDb movie match » : faute de code reconnu, l'importeur les prenait pour des
    films. La forme est ambigue — « Blade Runner - 2049 (2017) » lui ressemble —
    d'ou les deux garde-fous.
    """

    def test_la_forme_fansub_est_reconnue(self):
        titre, saison, episodes = ma.parse_episode_filename(
            '[Pokémon Fansub] Pokémon Horizons - 124 (VOSTFR-FR 1920x1080 H264 AAC).mp4')
        self.assertEqual(titre, 'Pokémon Horizons')
        self.assertEqual(saison, 1)
        self.assertEqual(episodes, [124])

    def test_l_etiquette_du_groupe_ne_fait_pas_partie_du_titre(self):
        titre, _, _ = ma.parse_episode_filename(
            '[Kaerizaki-Fansub] One Piece - 1174 (VOSTFR).mp4')
        self.assertEqual(titre, 'One Piece')

    def test_une_marque_de_reedition_ne_fait_pas_echouer_la_lecture(self):
        # « …H264 AAC)v2.mp4 » : deux caracteres apres la parenthese suffisaient
        # a renvoyer trois episodes dans le tas des films.
        for nom, numero in (
            ('[Pokémon Fansub] Pokémon Horizons - 139 (VOSTFR-FR 1920x1080 H264 AAC)v2.mp4', 139),
            ('Serie - 12 (VOSTFR) FINAL.mkv', 12),
            ('Serie - 8 (VOSTFR) repack.mkv', 8),
        ):
            titre, _, episodes = ma.parse_episode_filename(nom)
            self.assertIsNotNone(titre, nom)
            self.assertEqual(episodes, [numero])

    def test_un_millesime_ne_devient_pas_un_numero_d_episode(self):
        # « Blade Runner - 2049 » n'est pas le 2049e episode de Blade Runner :
        # le nombre pourrait etre une annee, et ce qui suit en est une.
        for nom in ('Blade Runner - 2049 (2017).mkv',
                    'Le Parrain - 2 (1974).mkv'):
            self.assertEqual(ma.parse_episode_filename(nom), (None, None, []))

    def test_les_formes_habituelles_restent_prioritaires(self):
        self.assertEqual(
            ma.parse_episode_filename('Detective Conan - S01E1085 - Rencontre.mkv'),
            ('Detective Conan', 1, [1085]))
        self.assertEqual(
            ma.parse_episode_filename('[SubsPlease] Serie - S02E03.mkv'),
            ('Serie', 2, [3]))


class UnEnvoiNtfyViseLeBonSujet(unittest.TestCase):
    """L'emetteur ntfy doit viser le bon serveur et porter le corps intact.

    Ces tests interceptent urlopen : rien ne part sur le reseau. On verifie la
    requete construite, pas la reponse du serveur.
    """

    def _capturer(self, settings, message, titre=None):
        """Retourne la liste des requetes qu'un envoi aurait emises."""
        envoyees = []

        def faux_urlopen(request, timeout=None):
            envoyees.append(request)
            return contextlib.nullcontext()

        with mock.patch.object(ma.urllib.request, 'urlopen', faux_urlopen):
            ma.send_ntfy_message(settings, message, titre)
        return envoyees

    def test_desactive_n_emet_rien(self):
        settings = ma.NtfyConfig(enabled=False, server='https://n.test',
                                 topic='infra-nice')
        self.assertEqual(self._capturer(settings, 'coucou'), [])

    def test_sans_sujet_n_emet_rien(self):
        # Un sujet vide produirait une URL visant la racine du serveur.
        settings = ma.NtfyConfig(enabled=True, server='https://n.test', topic=None)
        self.assertEqual(self._capturer(settings, 'coucou'), [])

    def test_vise_le_serveur_et_le_sujet(self):
        settings = ma.NtfyConfig(enabled=True, server='https://n.test/',
                                 topic='infra-nice')
        requete, = self._capturer(settings, 'coucou')
        # La barre finale du serveur ne doit pas produire un double slash.
        self.assertEqual(requete.full_url, 'https://n.test/infra-nice')

    def test_le_corps_est_le_message(self):
        settings = ma.NtfyConfig(enabled=True, server='https://n.test',
                                 topic='infra-nice')
        requete, = self._capturer(settings, 'trois episodes ecartes')
        self.assertEqual(requete.data.decode('utf-8'), 'trois episodes ecartes')

    def test_le_corps_accepte_les_accents_et_les_emoji(self):
        # Le corps part en UTF-8 : contrairement aux en-tetes, il n'a pas de
        # contrainte latin-1.
        settings = ma.NtfyConfig(enabled=True, server='https://n.test',
                                 topic='infra-nice')
        requete, = self._capturer(settings, '⚠️ episode ecarte : deja present')
        self.assertEqual(requete.data.decode('utf-8'),
                         '⚠️ episode ecarte : deja present')

    def test_le_jeton_devient_un_entete_bearer(self):
        settings = ma.NtfyConfig(enabled=True, server='https://n.test',
                                 topic='infra-nice', token='tk_essai')
        requete, = self._capturer(settings, 'coucou')
        self.assertEqual(requete.get_header('Authorization'), 'Bearer tk_essai')

    def test_sans_jeton_aucun_entete_authorization(self):
        settings = ma.NtfyConfig(enabled=True, server='https://n.test',
                                 topic='infra-nice')
        requete, = self._capturer(settings, 'coucou')
        self.assertIsNone(requete.get_header('Authorization'))

    def test_la_priorite_est_transmise(self):
        settings = ma.NtfyConfig(enabled=True, server='https://n.test',
                                 topic='infra-nice', priority=4)
        requete, = self._capturer(settings, 'coucou')
        self.assertEqual(requete.get_header('Priority'), '4')

    def test_un_titre_non_latin1_est_ecarte(self):
        # http.client encode les en-tetes en latin-1 : un titre accentue ou
        # emoji ferait echouer l'envoi au moment du socket, loin d'ici. On
        # prefere perdre le titre que la notification.
        settings = ma.NtfyConfig(enabled=True, server='https://n.test',
                                 topic='infra-nice')
        requete, = self._capturer(settings, 'corps', '⚠️ import media')
        self.assertIsNone(requete.get_header('Title'))

    def test_un_titre_simple_est_conserve(self):
        settings = ma.NtfyConfig(enabled=True, server='https://n.test',
                                 topic='infra-nice')
        requete, = self._capturer(settings, 'corps', 'media')
        self.assertEqual(requete.get_header('Title'), 'media')

    def test_un_message_multiligne_est_decoupe(self):
        settings = ma.NtfyConfig(enabled=True, server='https://n.test',
                                 topic='infra-nice')
        message = '\n'.join(f'ligne {i}' for i in range(1000))
        requetes = self._capturer(settings, message)
        self.assertGreater(len(requetes), 1)
        recompose = '\n'.join(r.data.decode('utf-8') for r in requetes)
        self.assertEqual(recompose, message)

    def test_une_ligne_unique_trop_longue_est_coupee(self):
        # Le decoupeur herite de Telegram coupe aux sauts de ligne : une ligne
        # unique tres longue en ressort intacte. ntfy refuse les corps au-dela
        # de sa limite, il faut donc une coupe franche en dernier recours.
        settings = ma.NtfyConfig(enabled=True, server='https://n.test',
                                 topic='infra-nice')
        requetes = self._capturer(settings, 'x' * 9000)
        self.assertGreater(len(requetes), 1)
        for requete in requetes:
            self.assertLessEqual(len(requete.data), ma.NTFY_TAILLE_MAX)
        self.assertEqual(''.join(r.data.decode('utf-8') for r in requetes),
                         'x' * 9000)

    def test_un_agent_explicite_est_annonce(self):
        # Le serveur est derriere Cloudflare, qui refuse la signature par
        # defaut d'urllib par une erreur 1010 — un 403 qu'on prendrait pour un
        # probleme d'autorisation. Le jeton, lui, etait valide.
        settings = ma.NtfyConfig(enabled=True, server='https://n.test',
                                 topic='infra-nice')
        requete, = self._capturer(settings, 'coucou')
        agent = requete.get_header('User-agent') or ''
        self.assertTrue(agent)
        self.assertNotIn('Python-urllib', agent)

    def test_une_panne_reseau_ne_remonte_pas(self):
        # Une notification qui echoue ne doit jamais interrompre un import.
        settings = ma.NtfyConfig(enabled=True, server='https://n.test',
                                 topic='infra-nice')

        def urlopen_qui_echoue(request, timeout=None):
            raise OSError('serveur injoignable')

        with mock.patch.object(ma.urllib.request, 'urlopen', urlopen_qui_echoue):
            ma.send_ntfy_message(settings, 'coucou')  # ne doit rien lever


class UneNotificationSertLesCanauxActives(unittest.TestCase):
    """Le point de dispatch unique decide seul des canaux a servir."""

    def _config(self, telegram_actif, ntfy_actif):
        config = mock.Mock()
        config.telegram = ma.TelegramConfig(
            enabled=telegram_actif, bot_token='b', chat_id='c')
        config.ntfy = ma.NtfyConfig(
            enabled=ntfy_actif, server='https://n.test', topic='infra-nice')
        return config

    def _servis(self, config):
        servis = []
        with mock.patch.object(ma, 'send_telegram_message',
                               lambda s, m: servis.append('telegram')), \
             mock.patch.object(ma, 'send_ntfy_message',
                               lambda s, m, t=None: servis.append('ntfy')):
            ma.notifier(config, 'coucou')
        return servis

    def test_les_deux_canaux_actifs_sont_servis(self):
        self.assertEqual(sorted(self._servis(self._config(True, True))),
                         ['ntfy', 'telegram'])

    def test_ntfy_seul(self):
        self.assertEqual(self._servis(self._config(False, True)), ['ntfy'])

    def test_telegram_seul(self):
        self.assertEqual(self._servis(self._config(True, False)), ['telegram'])

    def test_aucun_canal_actif_ne_leve_pas(self):
        self.assertEqual(self._servis(self._config(False, False)), [])


class LaConfigurationLitLaSectionNtfy(unittest.TestCase):
    """La bascule doit se jouer dans le TOML, pas dans le code."""

    GABARIT = """
[inbox]
path = "{racine}/inbox"

[routes]
movies = "{racine}/films"
series = "{racine}/series"
anime = "{racine}/animes"

[ntfy]
enabled = true
server = "https://n.test"
topic = "infra-nice"
token = "tk_essai"
priority = 4
"""

    def _charger(self, corps):
        with tempfile.TemporaryDirectory() as racine:
            chemin = Path(racine) / 'config.toml'
            chemin.write_text(corps.format(racine=racine), encoding='utf-8')
            return ma.load_automation_config(chemin)

    def test_la_section_est_lue(self):
        config = self._charger(self.GABARIT)
        self.assertTrue(config.ntfy.enabled)
        self.assertEqual(config.ntfy.server, 'https://n.test')
        self.assertEqual(config.ntfy.topic, 'infra-nice')
        self.assertEqual(config.ntfy.token, 'tk_essai')
        self.assertEqual(config.ntfy.priority, 4)

    def test_une_configuration_sans_section_ntfy_reste_valide(self):
        # Les deux NAS tourneront un moment avec l'ancien TOML : l'absence de
        # section ne doit pas empecher le demarrage, seulement laisser ntfy muet.
        sans_ntfy = self.GABARIT.split('[ntfy]')[0]
        config = self._charger(sans_ntfy)
        self.assertFalse(config.ntfy.enabled)


class AucunAppelDirectNeContourneLeDispatch(unittest.TestCase):
    """Un appel direct a un emetteur contournerait la bascule par le TOML.

    C'est l'oubli qui a failli passer : le dispatcher existait, mais les sept
    appelants s'adressaient toujours a Telegram en direct, et activer [ntfy]
    n'aurait rien produit.
    """

    def test_seul_le_dispatch_appelle_les_emetteurs(self):
        source = Path(ma.__file__).read_text(encoding='utf-8')
        # On isole le corps de notifier(), seul autorise a appeler un emetteur.
        avant, _, reste = source.partition('def notifier(')
        corps_notifier, _, apres = reste.partition('\n\n\n')
        dehors = avant + apres
        for emetteur in ('send_telegram_message(', 'send_ntfy_message('):
            appels = [l for l in dehors.splitlines()
                      if emetteur in l and not l.lstrip().startswith('def ')]
            self.assertEqual(appels, [], f'{emetteur} appele hors de notifier()')

class UneRessemblanceNeContreditPasUneIdentite(unittest.TestCase):
    """Deux dossiers d'identifiants TMDb differents ne fusionnent jamais.

    Origine : « Dragon Ball Z - Fusions » et « Dragon Ball Z - L'Attaque du
    dragon » ont ete reunis parce qu'ils partageaient un alias de titre, alors
    que leurs NFO declaraient deux films distincts. L'union-find traitait la
    ressemblance et l'identite a egalite.

    Les fixtures font porter la ressemblance par le titre du NFO plutot que par
    le nom du dossier : la cle en depend directement, sans passer par les
    subtilites de l'alias.
    """

    def _dossier(self, racine, nom, titre, annee='2000', tmdbid=None):
        # is_proper_dir exige un nom finissant par (YYYY).
        d = racine / f'{nom} ({annee})' / '1080p'
        d.mkdir(parents=True)
        ident = f'<tmdbid>{tmdbid}</tmdbid>' if tmdbid else ''
        (d / f'{nom}.nfo').write_text(
            f'<movie><title>{titre}</title><year>{annee}</year>{ident}</movie>',
            encoding='utf-8')
        (d / f'{nom}.mkv').write_bytes(b'x')
        return racine / f'{nom} ({annee})'

    def test_des_identifiants_differents_empechent_la_fusion(self):
        with tempfile.TemporaryDirectory() as brut:
            racine = Path(brut)
            self._dossier(racine, 'Fusions', 'Dragon Ball Z', tmdbid='39103')
            self._dossier(racine, 'Attaque du dragon', 'Dragon Ball Z',
                          tmdbid='39104')
            self.assertEqual(ma.get_duplicate_groups(racine), [])

    def test_un_identifiant_commun_fusionne_toujours(self):
        with tempfile.TemporaryDirectory() as brut:
            racine = Path(brut)
            self._dossier(racine, 'Le Parrain', 'Le Parrain', tmdbid='238')
            self._dossier(racine, 'The Godfather', 'The Godfather', tmdbid='238')
            groupes = ma.get_duplicate_groups(racine)
            self.assertEqual(len(groupes), 1)
            self.assertEqual(len(groupes[0]), 2)

    def test_sans_identifiant_la_ressemblance_decide_encore(self):
        # Le garde-fou ne doit pas rendre l'outil aveugle : sans identifiant
        # declare, rien ne contredit la ressemblance.
        with tempfile.TemporaryDirectory() as brut:
            racine = Path(brut)
            self._dossier(racine, 'Copie A', 'Le Parrain')
            self._dossier(racine, 'Copie B', 'Le Parrain')
            self.assertEqual(len(ma.get_duplicate_groups(racine)), 1)

    def test_un_identifiant_face_a_un_silence_fusionne(self):
        with tempfile.TemporaryDirectory() as brut:
            racine = Path(brut)
            self._dossier(racine, 'Copie A', 'Le Parrain', tmdbid='238')
            self._dossier(racine, 'Copie B', 'Le Parrain')
            self.assertEqual(len(ma.get_duplicate_groups(racine)), 1)

    def test_la_contradiction_est_verifiee_sur_le_groupe_entier(self):
        # A et B partagent l'identifiant 1, C leur ressemble mais declare 2.
        # Unir C mettrait 1 et 2 dans le meme groupe : c'est interdit, meme si
        # C pris isolement ne contredit personne directement.
        with tempfile.TemporaryDirectory() as brut:
            racine = Path(brut)
            self._dossier(racine, 'Alpha', 'Meme Film', tmdbid='1')
            self._dossier(racine, 'Beta', 'Meme Film', tmdbid='1')
            self._dossier(racine, 'Gamma', 'Meme Film', tmdbid='2')
            groupes = ma.get_duplicate_groups(racine)
            self.assertEqual(len(groupes), 1)
            self.assertEqual(len(groupes[0]), 2)
            self.assertNotIn(racine / 'Gamma (2000)', groupes[0])


class UnDossierOccupeNAccueillePasUnAutreFilm(unittest.TestCase):
    """Avant de deverser dans un dossier existant, on verifie a qui il est."""

    def _preparer(self, racine, nom, ident, avec_video):
        d = racine / nom / '1080p'
        d.mkdir(parents=True)
        (d / f'{nom}.nfo').write_text(
            f'<movie><title>{nom}</title><tmdbid>{ident}</tmdbid></movie>',
            encoding='utf-8')
        if avec_video:
            (d / f'{nom}.mkv').write_bytes(b'x')
        return racine / nom

    def test_un_dossier_absent_ne_pose_aucun_probleme(self):
        with tempfile.TemporaryDirectory() as brut:
            self.assertIsNone(
                ma.identite_du_dossier_diverge(Path(brut) / 'inexistant', 238))

    def test_le_meme_identifiant_laisse_passer(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._preparer(Path(brut), 'Le Parrain (1972)', '238', True)
            self.assertIsNone(ma.identite_du_dossier_diverge(d, 238))

    def test_un_identifiant_en_texte_reste_comparable(self):
        # TMDb renvoie un entier, le NFO porte du texte : cette seule
        # difference ne doit pas faire conclure a une divergence.
        with tempfile.TemporaryDirectory() as brut:
            d = self._preparer(Path(brut), 'Le Parrain (1972)', '238', True)
            self.assertIsNone(ma.identite_du_dossier_diverge(d, '238'))

    def test_un_dossier_muet_laisse_passer(self):
        with tempfile.TemporaryDirectory() as brut:
            d = Path(brut) / 'Sans NFO (1972)' / '1080p'
            d.mkdir(parents=True)
            (d / 'film.mkv').write_bytes(b'x')
            self.assertIsNone(ma.identite_du_dossier_diverge(d.parent, 238))

    def test_un_nfo_perime_sans_video_est_signale_comme_tel(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._preparer(Path(brut), 'Parti ailleurs (1972)', '999', False)
            self.assertEqual(ma.identite_du_dossier_diverge(d, 238), 'perime')

    def test_un_dossier_habite_par_un_autre_film_est_occupe(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._preparer(Path(brut), 'Un autre film (1972)', '999', True)
            self.assertEqual(ma.identite_du_dossier_diverge(d, 238), 'occupe')

class UnNomDeVersionSuitLaConventionEmby(unittest.TestCase):
    """Emby reconnait plusieurs versions d'un film au ' - ' dans le nom.

    « Chaque version doit commencer par le nom du dossier, suivi de ' - ' » ;
    ce qui suit le tiret devient le libelle affiche dans l'application.
    """

    def test_la_qualite_suit_un_tiret_entoure_d_espaces(self):
        self.assertEqual(ma.nom_de_version('300 (2006)', '1080p'),
                         '300 (2006) - 1080p')

    def test_le_nom_du_dossier_ouvre_toujours_le_nom_de_fichier(self):
        dossier = "L'Attaque des Titans (2020)"
        self.assertTrue(
            ma.nom_de_version(dossier, '2160p').startswith(dossier + ' - '))


class UnDossierDeQualiteSAplatit(unittest.TestCase):
    """Les fichiers remontent d'un cran, la qualite passe dans leur nom."""

    def _film(self, racine, nom, qualites):
        d = racine / nom
        for q, fichiers in qualites.items():
            (d / q).mkdir(parents=True)
            for f in fichiers:
                (d / q / f).write_bytes(b'x')
        return d

    def test_un_seul_sous_dossier_remonte(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._film(Path(brut), 'Le Parrain (1972)',
                           {'1080p': ['Le Parrain (1972).mkv',
                                      'Le Parrain (1972).nfo',
                                      'poster.jpg']})
            ma.aplatir_dossier_qualite(d)
            restants = sorted(f.name for f in d.iterdir())
            self.assertEqual(restants, ['Le Parrain (1972) - 1080p.mkv',
                                        'Le Parrain (1972) - 1080p.nfo',
                                        'poster.jpg'])
            self.assertFalse((d / '1080p').exists())

    def test_deux_qualites_cohabitent_sans_se_marcher_dessus(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._film(Path(brut), 'Avatar (2009)', {
                '1080p': ['Avatar (2009).mkv', 'poster.jpg'],
                '2160p': ['Avatar (2009).mkv', 'poster.jpg'],
            })
            ma.aplatir_dossier_qualite(d)
            videos = sorted(f.name for f in d.iterdir()
                            if f.suffix.lower() == '.mkv')
            self.assertEqual(videos, ['Avatar (2009) - 1080p.mkv',
                                      'Avatar (2009) - 2160p.mkv'])
            # Un seul visuel : les deux etaient homonymes, le second n'ecrase
            # pas le premier et ne se transforme pas en doublon numerote.
            self.assertEqual([f.name for f in d.iterdir()
                              if f.suffix.lower() == '.jpg'], ['poster.jpg'])
            self.assertFalse((d / '1080p').exists())
            self.assertFalse((d / '2160p').exists())

    def test_un_dossier_deja_plat_reste_intact(self):
        with tempfile.TemporaryDirectory() as brut:
            d = Path(brut) / 'Deja plat (2000)'
            d.mkdir()
            (d / 'Deja plat (2000) - 1080p.mkv').write_bytes(b'x')
            avant = sorted(f.name for f in d.iterdir())
            ma.aplatir_dossier_qualite(d)
            self.assertEqual(sorted(f.name for f in d.iterdir()), avant)

    def test_l_operation_est_idempotente(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._film(Path(brut), 'Le Parrain (1972)',
                           {'1080p': ['Le Parrain (1972).mkv']})
            ma.aplatir_dossier_qualite(d)
            premier = sorted(f.name for f in d.iterdir())
            ma.aplatir_dossier_qualite(d)
            self.assertEqual(sorted(f.name for f in d.iterdir()), premier)

    def test_un_essai_a_blanc_ne_touche_a_rien(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._film(Path(brut), 'Le Parrain (1972)',
                           {'1080p': ['Le Parrain (1972).mkv']})
            ma.aplatir_dossier_qualite(d, dry_run=True)
            self.assertTrue((d / '1080p' / 'Le Parrain (1972).mkv').exists())

class AucunePhaseNeCreuseDeSousDossierDeQualite(unittest.TestCase):
    """La qualite vit dans le nom ; plus aucun chemin ne doit la creuser.

    Quatre sites la composaient encore apres le passage a plat, dont trois sur
    le chemin de la tache cron : la fusion de doublons, la phase 1 pour les
    films multi-versions, et la phase 3 quand un dossier mal nomme rejoint un
    dossier existant. Ce test les empeche de revenir par megarde.
    """

    MOTIFS = ('/ quality', '/ group_quality', 'joinpath(*parts)')

    def test_aucun_chemin_ne_compose_un_sous_dossier_de_qualite(self):
        source = Path(ma.__file__).read_text(encoding='utf-8')
        for motif in self.MOTIFS:
            fautives = [l.strip() for l in source.splitlines()
                        if motif in l and not l.strip().startswith('#')]
            self.assertEqual(fautives, [],
                             f'« {motif} » compose encore un sous-dossier')

class UneEtiquetteDeVersionSeLitDansLeNom(unittest.TestCase):
    """La partie qui suit « - » designe la version, au sens d'Emby."""

    DOSSIER = 'Le Parrain (1972)'

    def test_la_qualite_est_l_etiquette(self):
        self.assertEqual(
            ma.etiquette_de_version(Path(f'{self.DOSSIER} - 1080p.mkv'),
                                    self.DOSSIER), '1080p')

    def test_un_nom_nu_n_a_pas_d_etiquette(self):
        self.assertIsNone(
            ma.etiquette_de_version(Path(f'{self.DOSSIER}.mkv'), self.DOSSIER))

    def test_le_suffixe_de_copie_ne_fait_pas_une_version(self):
        # « (2) » vient d'une collision de noms, pas d'une edition differente :
        # deux fichiers ainsi nommes sont bien deux copies de la meme version.
        self.assertIsNone(
            ma.etiquette_de_version(Path(f'{self.DOSSIER} (2).mkv'), self.DOSSIER))
        self.assertEqual(
            ma.etiquette_de_version(Path(f'{self.DOSSIER} - 1080p (2).mkv'),
                                    self.DOSSIER), '1080p')

    def test_une_edition_est_une_etiquette_comme_une_autre(self):
        self.assertEqual(
            ma.etiquette_de_version(Path(f'{self.DOSSIER} - directors cut.mkv'),
                                    self.DOSSIER), 'directors cut')

    def test_un_nom_etranger_au_dossier_n_a_pas_d_etiquette(self):
        self.assertIsNone(
            ma.etiquette_de_version(Path('Autre chose.mkv'), self.DOSSIER))


class UnDossierPeutCacherSesPropresDoublons(unittest.TestCase):
    """Deux videos de meme version dans un dossier sont un doublon.

    Origine : trois cas trouves le meme jour — Pokemon, Ghost in the Shell 2.0
    et L'Attaque des Titans Chronicles — tous invisibles pour la detection par
    dossier, qui ne compare que des dossiers entre eux.
    """

    def _dossier(self, racine, nom, fichiers):
        d = racine / nom
        d.mkdir(parents=True)
        for f in fichiers:
            (d / f).write_bytes(b'x')
        return d

    def test_deux_versions_distinctes_ne_sont_pas_un_doublon(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._dossier(Path(brut), 'Avatar (2009)',
                              ['Avatar (2009) - 1080p.mkv',
                               'Avatar (2009) - 2160p.mkv'])
            self.assertEqual(ma.doublons_internes(d), [])

    def test_deux_fichiers_de_meme_etiquette_sont_un_doublon(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._dossier(Path(brut), 'Avatar (2009)',
                              ['Avatar (2009) - 1080p.mkv',
                               'Avatar (2009) - 1080p (2).mkv'])
            groupes = ma.doublons_internes(d)
            self.assertEqual(len(groupes), 1)
            self.assertEqual(len(groupes[0]), 2)

    def test_deux_fichiers_nus_sont_un_doublon(self):
        # Le cas Chronicles : « Titre (2020).mkv » et « Titre (2020).mp4 »,
        # meme radical, extensions differentes.
        with tempfile.TemporaryDirectory() as brut:
            d = self._dossier(Path(brut), 'Chronicles (2020)',
                              ['Chronicles (2020).mkv', 'Chronicles (2020).mp4'])
            self.assertEqual(len(ma.doublons_internes(d)), 1)

    def test_une_seule_video_ne_signale_rien(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._dossier(Path(brut), 'Seul (2000)',
                              ['Seul (2000) - 1080p.mkv', 'poster.jpg',
                               'Seul (2000) - 1080p.nfo'])
            self.assertEqual(ma.doublons_internes(d), [])

    def test_les_annexes_ne_comptent_pas_comme_des_videos(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._dossier(Path(brut), 'Seul (2000)',
                              ['Seul (2000) - 1080p.mkv', 'fanart.jpg',
                               'poster.jpg', 'logo.png'])
            self.assertEqual(ma.doublons_internes(d), [])

    def test_un_fichier_hors_convention_est_signale_a_part(self):
        # Emby ne peut pas le rattacher comme version : son nom ne commence pas
        # par celui du dossier.
        with tempfile.TemporaryDirectory() as brut:
            d = self._dossier(Path(brut), 'Avatar (2009)',
                              ['Avatar (2009) - 1080p.mkv', 'video quelconque.mkv'])
            self.assertEqual(ma.doublons_internes(d), [])
            hors = ma.videos_hors_convention(d)
            self.assertEqual([f.name for f in hors], ['video quelconque.mkv'])

    def test_un_dossier_conforme_n_a_rien_hors_convention(self):
        with tempfile.TemporaryDirectory() as brut:
            d = self._dossier(Path(brut), 'Avatar (2009)',
                              ['Avatar (2009) - 1080p.mkv',
                               'Avatar (2009) - 2160p.mkv'])
            self.assertEqual(ma.videos_hors_convention(d), [])

class UnVocabulaireDeTitreSeDegageDuBruit(unittest.TestCase):
    """Le nom d'une release doit se reduire aux mots qui identifient l'oeuvre."""

    def test_le_bruit_de_release_disparait(self):
        mots = ma.mots_signifiants(
            "[KURISU_]Demon Slayer Kimetsu No Yaiba - Le train de l'infini "
            "S02 - FILM - MULTI 1080P WebRIP X265")
        self.assertIn('demon', mots)
        self.assertIn('slayer', mots)
        self.assertIn('infini', mots)
        for bruit in ('1080p', 'x265', 'webrip', 'multi', 'kurisu'):
            self.assertNotIn(bruit, mots)

    def test_les_accents_et_la_casse_ne_comptent_pas(self):
        self.assertEqual(ma.mots_signifiants("L'Infini"),
                         ma.mots_signifiants('l infini'))

    def test_les_mots_outils_sont_ecartes(self):
        self.assertNotIn('le', ma.mots_signifiants('Le train de la mort'))
        self.assertIn('train', ma.mots_signifiants('Le train de la mort'))


class UnMemeFilmPeutVivreDansDeuxRacines(unittest.TestCase):
    """Deux copies d'un film peuvent se cacher dans des racines differentes.

    Origine : le film Demon Slayer existait dans « movies », correctement
    identifie, et une seconde fois a la racine du dossier de la serie dans
    « animes », deguise en episode. Ni la detection par dossier ni celle par
    fichier ne pouvaient le voir.

    La duree tranche : deux films distincts partagent rarement leur minutage a
    la minute pres tout en partageant leur vocabulaire.
    """

    FILM = ('/data/movies/Demon Slayer - Le train de l Infini (2020)/'
            'Demon Slayer - Le train de l Infini (2020) - 1080p.mkv')
    EGARE = ('/data/animes/Demon Slayer (2019)/'
             "[KURISU_]Demon Slayer - Le train de l'infini S02 - FILM 1080P X265.mkv")

    def test_meme_duree_et_meme_vocabulaire_forment_un_groupe(self):
        groupes = ma.doublons_inter_racines(
            [(Path(self.FILM), 116.8), (Path(self.EGARE), 116.8)])
        self.assertEqual(len(groupes), 1)
        self.assertEqual(len(groupes[0]), 2)

    def test_une_minute_d_ecart_reste_le_meme_film(self):
        groupes = ma.doublons_inter_racines(
            [(Path(self.FILM), 116.8), (Path(self.EGARE), 117.6)])
        self.assertEqual(len(groupes), 1)

    def test_des_durees_eloignees_ne_forment_pas_de_groupe(self):
        groupes = ma.doublons_inter_racines(
            [(Path(self.FILM), 116.8), (Path(self.EGARE), 95.0)])
        self.assertEqual(groupes, [])

    def test_des_titres_etrangers_ne_forment_pas_de_groupe(self):
        autre = '/data/movies/Le Parrain (1972)/Le Parrain (1972) - 1080p.mkv'
        groupes = ma.doublons_inter_racines(
            [(Path(self.FILM), 116.8), (Path(autre), 116.8)])
        self.assertEqual(groupes, [])

    def test_deux_fichiers_du_meme_dossier_ne_sont_pas_du_ressort(self):
        # C'est le travail de doublons_internes ; ici on cherche ce qui se
        # cache dans deux dossiers differents.
        a = '/data/movies/Avatar (2009)/Avatar (2009) - 1080p.mkv'
        b = '/data/movies/Avatar (2009)/Avatar (2009) - 2160p.mkv'
        self.assertEqual(
            ma.doublons_inter_racines([(Path(a), 162.0), (Path(b), 162.0)]), [])

    def test_une_duree_inconnue_est_ignoree(self):
        groupes = ma.doublons_inter_racines(
            [(Path(self.FILM), 116.8), (Path(self.EGARE), None)])
        self.assertEqual(groupes, [])

    def test_trois_copies_forment_un_seul_groupe(self):
        troisieme = ('/data/animes/Demon Slayer Films (2020)/'
                     'Demon Slayer Le train de l Infini - 1080p.mkv')
        groupes = ma.doublons_inter_racines([
            (Path(self.FILM), 116.8),
            (Path(self.EGARE), 116.8),
            (Path(troisieme), 116.8),
        ])
        self.assertEqual(len(groupes), 1)
        self.assertEqual(len(groupes[0]), 3)

class UneSuiteNEstPasUnDoublonDeSonPremierVolet(unittest.TestCase):
    """Faux positifs releves par le premier audit reel, figes en tests.

    Le rang d'une saga — « 3 », « II » — est exactement ce qui distingue deux
    films. L'ecarter comme du bruit technique fait passer « Toy Story 5 » pour
    une copie de « Toy Story 3 ». L'annee, elle, ne distingue rien : deux films
    sortis la meme annee ne se ressemblent pas pour autant.
    """

    def _couple(self, a, b, duree=100.0):
        return ma.doublons_inter_racines([(Path(a), duree), (Path(b), duree)])

    def test_un_rang_chiffre_distingue_deux_films(self):
        self.assertEqual(self._couple(
            '/m/Toy Story 3 (2010)/Toy Story 3 (2010) - 1080p.mkv',
            '/m/Toy Story 5 (2026)/Toy Story 5 (2026) - 1080p.mkv'), [])

    def test_un_rang_romain_distingue_deux_films(self):
        self.assertEqual(self._couple(
            '/m/Rocky (1976)/Rocky (1976) - 1080p.mkv',
            '/m/Rocky II  La Revanche (1979)/Rocky II  La Revanche (1979) - 1080p.mkv'), [])

    def test_un_volet_sans_rang_ne_vaut_pas_le_volet_numerote(self):
        self.assertEqual(self._couple(
            '/m/Very Bad Trip (2009)/Very Bad Trip (2009) - 1080p.mkv',
            '/m/Very Bad Trip 3 (2013)/Very Bad Trip 3 (2013) - 1080p.mkv'), [])

    def test_l_annee_commune_ne_rapproche_pas_deux_films(self):
        self.assertEqual(self._couple(
            '/m/Ralph 2.0 (2018)/Ralph 2.0 (2018) - 1080p.mkv',
            '/m/Venom (2018)/Venom (2018) - 1080p.mkv'), [])

    def test_un_sous_titre_commun_ne_suffit_pas(self):
        # « A Star Wars Story » est partage par deux films distincts.
        self.assertEqual(self._couple(
            '/m/Rogue One  A Star Wars Story (2016)/Rogue One  A Star Wars Story (2016) - 1080p.mkv',
            '/m/Solo A Star Wars Story (2018)/Solo A Star Wars Story (2018) - 1080p.mkv'), [])

    def test_un_seul_mot_commun_ne_suffit_pas(self):
        self.assertEqual(self._couple(
            '/m/Tintin au Tibet (1992)/Tintin au Tibet (1992) - 1080p.mkv',
            "/m/Tintin et les Picaros (1992)/Tintin et les Picaros (1992) - 1080p.mkv"), [])

    def test_deux_volets_d_une_trilogie_restent_distincts(self):
        self.assertEqual(self._couple(
            '/m/Psycho-Pass Sinners of the System - Case 1 (2019)/a - 1080p.mkv',
            '/m/Psycho-Pass Sinners of the System - Case 2 (2019)/b - 1080p.mkv'), [])

class UnTitreInclusDansUnAutreNEstPasUneCopie(unittest.TestCase):
    """Deuxieme serie de faux positifs reels, figee en tests.

    Quand le premier volet n'a pas de sous-titre, son titre est entierement
    contenu dans celui de sa suite. Diviser par le plus petit vocabulaire donne
    alors un score parfait a une simple inclusion — le piege qui avait deja fait
    recouvrir « Les Indestructibles » et « Les Indestructibles 2 ».

    Le recouvrement se mesure donc sur la reunion des deux vocabulaires, ou ce
    qui manque a l'un compte autant que ce qu'ils partagent.
    """

    def _couple(self, a, b, duree=100.0):
        return ma.doublons_inter_racines([(Path(a), duree), (Path(b), duree)])

    def test_une_suite_sous_titree_ne_recouvre_pas_son_premier_volet(self):
        self.assertEqual(self._couple(
            '/m/Austin Powers (1997)/Austin Powers (1997) - 1080p.mkv',
            "/m/Austin Powers  L'Espion qui m'a tiree (1999)/"
            "Austin Powers  L'Espion qui m'a tiree (1999) - 1080p.mkv"), [])

    def test_un_dessin_anime_et_sa_suite_restent_distincts(self):
        self.assertEqual(self._couple(
            "/m/L'Age de glace (2002)/L'Age de glace (2002) - 1080p.mkv",
            "/m/L'Age de glace  Les Aventures de Buck Wild (2022)/"
            "L'Age de glace  Les Aventures de Buck Wild (2022) - 1080p.mkv"), [])

    def test_un_titre_de_saga_ne_vaut_pas_pour_toute_la_saga(self):
        self.assertEqual(self._couple(
            '/m/Les Animaux Fantastiques (2016)/Les Animaux Fantastiques (2016) - 1080p.mkv',
            '/m/Les Animaux Fantastiques  Les Crimes de Grindelwald (2018)/'
            'Les Animaux Fantastiques  Les Crimes de Grindelwald (2018) - 1080p.mkv'), [])

    def test_du_bruit_supplementaire_n_empeche_pas_de_reconnaitre_une_copie(self):
        # La copie egaree porte des mots que la copie rangee n'a pas ; le
        # critere doit rester assez tolerant pour la reconnaitre quand meme.
        self.assertEqual(len(self._couple(
            '/data/movies/Demon Slayer - Le train de l Infini (2020)/'
            'Demon Slayer - Le train de l Infini (2020) - 1080p.mkv',
            '/data/animes/Demon Slayer (2019)/'
            "[KURISU_]Demon Slayer - Le train de l'infini S02 - FILM 1080P X265.mkv")), 1)

class UnSeulMotPeutSeparerDeuxFilms(unittest.TestCase):
    """Troisieme faux positif reel, et le plus retors, fige en test.

    « Qu'est-ce qu'on a encore fait au Bon Dieu ? » et « Qu'est-ce qu'on a tous
    fait au Bon Dieu ? » ne different que par un mot dans un titre tres long :
    le recouvrement reste eleve alors que les films sont distincts.

    D'ou la regle : au plus un mot d'ecart entre les deux vocabulaires. Elle se
    lit sans calcul et resiste aux titres longs comme aux titres courts.
    """

    def _couple(self, a, b, duree=100.0):
        return ma.doublons_inter_racines([(Path(a), duree), (Path(b), duree)])

    def test_deux_mots_d_ecart_separent_deux_films(self):
        self.assertEqual(self._couple(
            "/m/Qu est-ce qu on a encore fait au Bon Dieu (2019)/"
            "Qu est-ce qu on a encore fait au Bon Dieu (2019) - 1080p.mkv",
            "/m/Qu est-ce qu on a tous fait au Bon Dieu (2021)/"
            "Qu est-ce qu on a tous fait au Bon Dieu (2021) - 1080p.mkv"), [])

    def test_un_seul_mot_d_ecart_reste_une_copie_possible(self):
        # Une copie egaree porte souvent un mot de plus que la copie rangee ;
        # le critere doit rester assez tolerant pour la reconnaitre. Il faut un
        # titre assez fourni : sur deux mots, un mot d'ecart change tout.
        self.assertEqual(len(self._couple(
            '/data/movies/Le Seigneur des Anneaux La Communaute de l Anneau (2001)/'
            'Le Seigneur des Anneaux La Communaute de l Anneau (2001) - 1080p.mkv',
            '/data/animes/Le Seigneur des Anneaux La Communaute de l Anneau (2001)/'
            'Le Seigneur des Anneaux La Communaute de l Anneau remastered - 1080p.mkv')), 1)

    def test_une_copie_au_vocabulaire_identique_reste_reconnue(self):
        self.assertEqual(len(self._couple(
            '/data/movies/Demon Slayer - Le train de l Infini (2020)/'
            'Demon Slayer - Le train de l Infini (2020) - 1080p.mkv',
            '/data/animes/Demon Slayer (2019)/'
            "[KURISU_]Demon Slayer - Le train de l'infini S02 - FILM 1080P X265.mkv")), 1)

class UnMotDEcartNEstTolereQuePourUneEdition(unittest.TestCase):
    """Quatrieme faux positif reel : le mot d'ecart etait le titre lui-meme.

    « Qu'est-ce qu'on a fait au Bon Dieu ? » et « ... a tous fait ... » ne
    different que par « tous » — et c'est precisement ce mot qui distingue les
    deux films. Tolerer un mot d'ecart au hasard ne pouvait pas marcher.

    Un ecart n'est donc admis que s'il porte sur un mot d'edition : ceux-la
    qualifient une copie, jamais une oeuvre.
    """

    def _couple(self, a, b, duree=100.0):
        return ma.doublons_inter_racines([(Path(a), duree), (Path(b), duree)])

    def test_un_mot_du_titre_separe_deux_films(self):
        self.assertEqual(self._couple(
            "/m/Qu est-ce qu on a fait au Bon Dieu (2014)/"
            "Qu est-ce qu on a fait au Bon Dieu (2014) - 1080p.mkv",
            "/m/Qu est-ce qu on a tous fait au Bon Dieu (2021)/"
            "Qu est-ce qu on a tous fait au Bon Dieu (2021) - 1080p.mkv"), [])

    def test_un_mot_d_edition_ne_separe_pas_deux_copies(self):
        self.assertEqual(len(self._couple(
            '/data/movies/Blade Runner (1982)/Blade Runner (1982) - 1080p.mkv',
            '/data/animes/Blade Runner (1982)/'
            'Blade Runner final cut - 1080p.mkv')), 1)

    def test_deux_mots_d_edition_restent_toleres(self):
        self.assertEqual(len(self._couple(
            '/data/movies/Blade Runner (1982)/Blade Runner (1982) - 1080p.mkv',
            '/data/animes/Blade Runner (1982)/'
            'Blade Runner directors cut remastered - 1080p.mkv')), 1)

if __name__ == '__main__':
    unittest.main(verbosity=2)
