#!/usr/bin/env python3
"""Applique a une serie deja rangee la convention de nommage de l'importeur.

L'importeur nomme desormais chaque arrivee d'apres son titre ; la bibliotheque
dont il a herite, elle, porte des codes nus. Cet outil applique la meme regle
apres coup, serie par serie.

La regle n'est pas reecrite ici : elle est empruntee a media_automation, seule
source de verite, deja fixee par sa batterie de tests. Une regle recopiee est
une regle qui divergera — la premiere version de cet outil reconstruisait le nom
a la main et perdait le second numero des episodes doubles, transformant
« S02E01-E02 » en « S02E01 » et faisant disparaitre un episode de la
bibliotheque.

L'outil est idempotent : un fichier deja conforme est laisse tel quel, un
passage peut donc etre repris ou relance sans plan intermediaire. Il ne renomme
jamais vers une cible existante, et un titre que TMDb ne fournit pas laisse le
code nu en place plutot que d'etre invente.

Sans --appliquer, rien n'est touche.
"""
import argparse
import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import media_automation as ma  # noqa: E402

# Le code complet, plage d'episodes doubles comprise. La garde finale evite de
# lire « S01E1109 » comme « S01E110 » sur les series longues.
CODE = re.compile(r'S(?P<s>\d{2})E(?P<e>\d{2,4})(?:-E(?P<e2>\d{2,4}))?(?!\d)')
VIDEO = ('.mkv', '.mp4', '.avi', '.wmv', '.m4v', '.mov')
# Suffixes d'illustration propres a un episode : ils font partie de ce sur quoi
# Emby apparie, et doivent suivre leur episode plutot qu'etre pris pour une
# extension.
SUFFIXES_ART = ('-thumb.jpg', '-thumb.png', '-poster.jpg', '-landscape.jpg')


def suffixe_de(nom):
    """Renvoie le suffixe complet d'un fichier, illustration d'episode comprise."""
    for suffixe in SUFFIXES_ART:
        if nom.lower().endswith(suffixe):
            return nom[-len(suffixe):]
    return Path(nom).suffix


def base_cible(serie, saison, episodes, titre):
    """Nom de base d'un episode, tel que l'importeur le construirait.

    On passe par get_episode_target_name pour que l'outil et l'importeur ne
    puissent pas diverger, puis on retire l'extension : les annexes s'y
    raccrochent ensuite avec leur propre suffixe.
    """
    nom = ma.get_episode_target_name(Path('x.mkv'), serie, saison, episodes, titre)
    return nom[:-len('.mkv')]


def titres_de_saison(tv_id, saison, cle, cache):
    if saison in cache:
        return cache[saison]
    url = (f'https://api.themoviedb.org/3/tv/{tv_id}/season/{saison}'
           f'?api_key={cle}&language=fr-FR')
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            cache[saison] = {e['episode_number']: e['name']
                             for e in json.loads(r.read().decode())['episodes']}
    except Exception:
        # Une saison inconnue de TMDb n'est pas fatale : ces episodes garderont
        # leur code nu, et seront comptes comme tels.
        cache[saison] = {}
    return cache[saison]


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('dossier', type=Path)
    p.add_argument('--tmdb-id', type=int, required=True)
    p.add_argument('--cle', required=True)
    p.add_argument('--serie', required=True, help='nom de serie a inscrire dans les fichiers')
    p.add_argument('--renommer-dossier', metavar='NOUVEAU_NOM',
                   help='renomme aussi le dossier de la serie, avant tout le reste')
    p.add_argument('--appliquer', action='store_true')
    args = p.parse_args()

    print(f"  ===== {'APPLICATION' if args.appliquer else 'SIMULATION'} =====\n")
    dossier = args.dossier

    if args.renommer_dossier:
        cible = dossier.parent / args.renommer_dossier
        if cible == dossier:
            print('  dossier : deja au bon nom')
        elif cible.exists():
            sys.exit(f'  ARRET : {cible.name} existe deja')
        else:
            print(f'  dossier : «{dossier.name}» -> «{cible.name}»')
            if args.appliquer:
                dossier.rename(cible)
                dossier = cible

    cache = {}
    groupes = defaultdict(list)
    for chemin in sorted(dossier.rglob('*')):
        if not chemin.is_file():
            continue
        m = CODE.search(chemin.name)
        if m:
            groupes[m.group(0)].append((chemin, m))

    renommes, deja, sans_titre, conflits = 0, 0, [], []
    for code in sorted(groupes):
        chemins = groupes[code]
        _, m = chemins[0]
        saison = int(m.group('s'))
        episodes = [int(m.group('e'))]
        if m.group('e2'):
            episodes.append(int(m.group('e2')))
        titre = titres_de_saison(args.tmdb_id, saison, args.cle, cache).get(episodes[0], '')
        if not titre:
            sans_titre.append(code)
        base = base_cible(args.serie, saison, episodes, titre)

        mouvements = []
        for chemin, _ in chemins:
            cible = chemin.with_name(f'{base}{suffixe_de(chemin.name)}')
            if cible == chemin:
                deja += 1
            elif cible.exists():
                conflits.append((chemin.name, cible.name))
            else:
                mouvements.append((chemin, cible))
        if not mouvements:
            continue
        principal = next((c for c, _ in mouvements if c.suffix.lower() in VIDEO),
                         mouvements[0][0])
        annexes = len(mouvements) - 1
        print(f'  {principal.name[:46]:<46} -> {base[:56]}'
              + (f'  (+{annexes} annexe(s))' if annexes else ''))
        if args.appliquer:
            for source, destination in mouvements:
                source.rename(destination)
        renommes += 1

    print(f'\n  {renommes} episode(s) renomme(s)')
    print(f'  {deja} fichier(s) deja conforme(s)')
    if sans_titre:
        print(f'  {len(sans_titre)} episode(s) sans titre chez TMDb : '
              f'{", ".join(sorted(sans_titre)[:12])}')
    for source, cible in conflits:
        print(f'  CONFLIT : {source} -> {cible} existe deja')
    return 1 if conflits else 0


if __name__ == '__main__':
    sys.exit(main())
