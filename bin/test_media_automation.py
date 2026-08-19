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

if __name__ == '__main__':
    unittest.main(verbosity=2)
