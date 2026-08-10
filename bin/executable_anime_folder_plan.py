#!/usr/bin/env python3
"""Compare les dossiers d'une bibliotheque a la convention de l'importeur.

L'importeur nomme un dossier de serie `sanitize("<nom TMDb> (<annee>)")`. Un
dossier nomme autrement fait qu'un nouvel episode cree une serie parallele au
lieu de rejoindre l'existante -- c'est ce qui a failli arriver a Pokemon.

Ce script ne renomme rien : il produit le plan et signale ce qui demande une
decision humaine (aucune correspondance TMDb, ou collision entre deux dossiers).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import media_automation as ma  # noqa: E402


def nom_attendu(dossier, config):
    """Retourne (nom_attendu, detail) ou (None, raison) si indecidable."""
    titre, annee = ma.parse_filename(dossier)
    recherche = titre or dossier
    candidat = ma.search_tmdb_tv(recherche, annee, config.tmdb_api_key, config.tmdb_language)
    if not candidat:
        return None, 'aucune correspondance TMDb'
    details = ma.get_tmdb_tv_details(candidat['id'], config.tmdb_api_key, config.tmdb_language)
    nom = details.get('name') or recherche
    premiere = ma.get_release_year(details, 'first_air_date') or annee
    attendu = ma.sanitize(f'{nom} ({premiere})') if premiere else ma.sanitize(nom)
    return attendu, f"TMDb {candidat['id']}"


def main():
    parseur = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parseur.add_argument('--liste', required=True, type=Path, help='un nom de dossier par ligne')
    parseur.add_argument('--racine', required=True, help='chemin de la bibliotheque sur l hote')
    parseur.add_argument('--config', type=Path,
                         default=Path.home() / 'bin/media_automation/media_automation.toml')
    args = parseur.parse_args()

    config = ma.load_automation_config(args.config)
    dossiers = [l.strip() for l in args.liste.read_text().splitlines() if l.strip()]

    conformes, renommages, indecis = [], [], []
    for dossier in dossiers:
        attendu, detail = nom_attendu(dossier, config)
        if attendu is None:
            indecis.append((dossier, detail))
        elif attendu == dossier:
            conformes.append(dossier)
        else:
            renommages.append((dossier, attendu, detail))

    # Deux dossiers qui viseraient le meme nom : fusion, donc decision humaine.
    cibles = {}
    for source, cible, _ in renommages:
        cibles.setdefault(cible, []).append(source)
    collisions = {c: s for c, s in cibles.items() if len(s) > 1 or c in conformes}

    print(f'  racine : {args.racine}')
    print(f'  {len(dossiers)} dossiers | conformes : {len(conformes)} | '
          f'a renommer : {len(renommages)} | indecidables : {len(indecis)}')
    if renommages:
        print('\n  ## A RENOMMER')
        for source, cible, detail in sorted(renommages):
            marque = '   ⚠ COLLISION' if cible in collisions else ''
            print(f'    {source}\n      -> {cible}   [{detail}]{marque}')
    if indecis:
        print('\n  ## INDECIDABLES (laisses tels quels)')
        for dossier, raison in indecis:
            print(f'    {dossier}   [{raison}]')
    if conformes:
        print(f'\n  ## DEJA CONFORMES ({len(conformes)})')
        for dossier in sorted(conformes):
            print(f'    {dossier}')
    return 1 if collisions else 0


if __name__ == '__main__':
    sys.exit(main())
