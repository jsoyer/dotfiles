#!/usr/bin/env python3
"""Applique a une serie entiere la convention « Serie - SxxExx - Titre.ext ».

Un code nu ne dit rien au spectateur, et il rend un episode mal range
indetectable a l'oeil : le numero est alors le seul indice, et c'est justement
ce a quoi on ne peut pas se fier quand un import a derape. Le titre vient de
TMDb, source unique deja utilisee pour ranger la bibliotheque.

L'outil est idempotent : un fichier deja conforme est laisse tel quel. Il ne
renomme jamais vers une cible existante, et signale chaque titre introuvable
plutot que d'inventer un nom.

Sans --appliquer, rien n'est touche.
"""
import argparse
import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

CODE = re.compile(r'S(?P<s>\d{2})E(?P<e>\d{2,4})(?!\d)')
ILLEGAL = re.compile(r'[\\/:*?"<>|]')
# Les vignettes et jaquettes portent un suffixe qui fait partie de leur identite
# pour Emby : il doit survivre au renommage.
SUFFIXES_ART = ('-thumb.jpg', '-poster.jpg', '-fanart.jpg', '-banner.jpg')


def sanitize(nom):
    return re.sub(r'\s+', ' ', ILLEGAL.sub('', nom)).strip()


def titres_de_saison(tv_id, saison, cle, cache):
    if saison in cache:
        return cache[saison]
    url = (f'https://api.themoviedb.org/3/tv/{tv_id}/season/{saison}'
           f'?api_key={cle}&language=fr-FR')
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            charge = json.loads(r.read().decode())
        cache[saison] = {e['episode_number']: e['name'] for e in charge['episodes']}
    except Exception:
        # Une saison inconnue de TMDb n'est pas une erreur fatale : les episodes
        # concernes garderont leur code nu, et seront comptes comme tels.
        cache[saison] = {}
    return cache[saison]


def decouper(nom):
    """Separe le corps du nom de son suffixe (extension ou suffixe d'illustration)."""
    for suffixe in SUFFIXES_ART:
        if nom.endswith(suffixe):
            return nom[:-len(suffixe)], suffixe
    chemin = Path(nom)
    return chemin.stem, chemin.suffix


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

    cache, operations, deja, sans_titre, conflits = {}, [], 0, [], []
    for chemin in sorted(dossier.rglob('*')):
        if not chemin.is_file():
            continue
        m = CODE.search(chemin.name)
        if not m:
            continue
        saison, numero = int(m.group('s')), int(m.group('e'))
        titre = sanitize(titres_de_saison(args.tmdb_id, saison, args.cle, cache).get(numero, ''))
        corps, suffixe = decouper(chemin.name)
        base = f'S{saison:02d}E{numero:02d}'
        attendu = f'{args.serie} - {base} - {titre}' if titre else f'{args.serie} - {base}'
        if not titre:
            sans_titre.append(f'S{saison:02d}E{numero:02d}')
        if corps == attendu:
            deja += 1
            continue
        cible = chemin.with_name(f'{attendu}{suffixe}')
        if cible.exists():
            conflits.append((chemin.name, cible.name))
            continue
        operations.append((chemin, cible))

    par_episode = defaultdict(list)
    for chemin, cible in operations:
        par_episode[CODE.search(chemin.name).group(0)].append((chemin, cible))

    for code in sorted(par_episode):
        chemin, cible = par_episode[code][0]
        autres = len(par_episode[code]) - 1
        extra = f'  (+{autres} annexe(s))' if autres else ''
        print(f'  {chemin.name[:46]:<46} -> {cible.name[:58]}{extra}')
        if args.appliquer:
            for source, destination in par_episode[code]:
                source.rename(destination)

    print(f'\n  {len(par_episode)} episode(s) renomme(s), {len(operations)} fichier(s)')
    print(f'  {deja} fichier(s) deja conforme(s)')
    if sans_titre:
        uniques = sorted(set(sans_titre))
        print(f'  {len(uniques)} episode(s) sans titre chez TMDb : {", ".join(uniques[:12])}')
    for source, cible in conflits:
        print(f'  CONFLIT : {source} -> {cible} existe deja')
    return 1 if conflits else 0


if __name__ == '__main__':
    sys.exit(main())
