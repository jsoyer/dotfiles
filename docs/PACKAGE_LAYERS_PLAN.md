# Plan : trois couches de paquets sur macOS, Linux et Windows

Date : 14 novembre 2026. Référence examinée : `da8ee005`.

Objectif : une nouvelle machine reçoit un socle limité, un usage facultatif et
ses propres ajouts. Le MacBook Neo doit pouvoir utiliser les dotfiles sans
hériter des applications des autres Macs.

Le sélecteur, les couches des trois OS, les wrappers et la migration locale sont
implémentés. Le guide opérationnel est [PACKAGE_LAYERS.md](PACKAGE_LAYERS.md).
Les listes historiques sont conservées pour les machines non migrées ; leur
répartition définitive et le retrait de la compatibilité attendent un inventaire
sur ces machines. Aucun déploiement sur un Mac physique n'est supposé effectué.

## Modèle retenu

```text
Base adaptée à la plateforme
        +
Usage facultatif : personnel / professionnel / serveur
        +
Ajouts propres à cette machine
        =
Paquets demandés pour cette machine
```

Les dépendances nécessaires restent installées par les gestionnaires de paquets.
La taille du socle désigne ses entrées explicites, pas toutes leurs dépendances.

| Donnée | Rôle | Décision |
| --- | --- | --- |
| OS, distribution, architecture | Disponibilité et mode d'installation des paquets | Détection technique conservée |
| `machine_profile` | Configuration système, serveur/bureau, contraintes du Mac professionnel | Conserver les valeurs existantes pendant la migration |
| `package_profile` | Choix des paquets : `base`, `personal`, `professional`, `server` | Nouvelle donnée persistée ; `base` signifie aucun usage supplémentaire |
| Identifiant de machine | Sélection de son propre fichier de paquets | Réutiliser le nom d'hôte court actuel, calculé de façon identique dans les templates et wrappers |

On évite ainsi de multiplier les profils techniques pour toutes les combinaisons
OS × usage × architecture. Le libellé « mac-base » correspond à un Mac dont
`package_profile = "base"`, sans remplacer son profil technique.

Pour une installation neuve, proposer la base par défaut et enregistrer le choix
avant toute installation. Une configuration existante conserve son comportement
jusqu'à sa migration explicite. L'absence du nouveau champ ne suffit pas à
conclure qu'une machine est neuve.

## État de départ vérifié

- macOS possède déjà `Brewfile_macos`, `Brewfile_personal` / `Brewfile_pro`, puis
  `Brewfile_<hostname>`. Un nouveau Mac est cependant classé `mac-personal`, et
  les branches d'installation chargent personnel pour tout profil autre que pro.
- Le socle macOS contient 18 formules explicites. Le fichier personnel contient
  343 formules, 82 casks et d'autres entrées, dont des outils Go.
- Linux sélectionne des listes par distribution et rôle serveur/bureau, puis
  des ajouts par machine. La séparation base/usage reste à extraire.
- Windows installe le seul `Scoopfile.json`. `scoopw` y réexporte l'état installé
  de la machine, ce qui mélange les besoins de toutes les machines Windows.
- Plusieurs wrappers Unix écrivent déjà les ajouts par machine. `yayw` écrit
  encore dans `Pacfile_aur_desktop`. `breww` peut modifier une liste de profil
  lors d'une suppression et calcule son delta à partir d'un seul fichier partagé.
- Les scripts annexes et mise peuvent installer des outils indépendamment des
  listes principales. Les seules modifications des Brewfiles ne suffisent pas.
- `dot_private/packages.yaml` se présente comme une source génératrice, mais
  aucune référence à ce fichier n'a été trouvée dans les scripts, outils ou CI
  examinés. Les listes par gestionnaire restent la référence de cette migration.

## 1. Inventorier et figer le comportement actuel

Travail :

- Recenser les listes, scripts, wrappers, configurations mise et options
  `install_*` qui installent des paquets ou activent des services.
- Établir la correspondance entre les machines connues, leurs profils et leurs
  fichiers. Signaler les noms ambigus ou anciens sans les fusionner automatiquement.
- Produire pour chaque machine connue la liste déclarée résultante actuelle.
  Distinguer cette liste de l'inventaire réellement installé, à relever quand
  la machine est disponible.
- Classer les paquets : socle indispensable, usage partagé, besoin de machine,
  dépendance ou entrée obsolète à examiner.
- Clarifier le statut de `packages.yaml` et corriger la documentation qui décrit
  encore un autre fonctionnement ; ne pas introduire un second générateur.

Livrable : inventaire et références permettant une comparaison avant/après.
Les décisions de classement incertaines restent visibles pour examen.

## 2. Définir une sélection commune et vérifiable

Travail :

- Ajouter `package_profile` à l'initialisation et à la configuration persistée.
  Prévoir un choix explicite utilisable aussi sans interaction.
- Faire calculer les fichiers actifs par une logique commune aux installateurs
  et aux wrappers, avec une interface adaptée à Bash, Python et PowerShell.
- Conserver les formats natifs : Brewfile, listes apt/dnf/pacman/Flatpak et JSON
  Scoop. Ajouter les fichiers de base et d'usage manquants, sans renommer tous
  les fichiers des machines pendant cette première migration.
- Fusionner base + usage choisi + machine avec déduplication par gestionnaire,
  type et identité du paquet. Signaler les options incompatibles plutôt que
  perdre silencieusement une version, un bucket ou une option d'installation.
- Vérifier les valeurs et l'identifiant de machine. Un profil inconnu doit
  produire une erreur claire ; il ne doit jamais sélectionner personnel par défaut.
- Ajouter une prévisualisation sans installation : fichiers retenus, origine de
  chaque paquet, options actives et nombre d'entrées explicites.
- Inclure tous les fichiers actifs dans les empreintes `run_onchange`, y compris
  le fichier de la machine. Une modification d'une liste inactive ne doit pas
  lancer un autre profil d'installation.

Validation : base seule, usage choisi et absence de fichier machine donnent des
résultats déterministes ; aucun fichier d'une autre machine n'est chargé.

## 3. Rendre le MacBook Neo utilisable avec la base

Travail :

- Adapter `.chezmoi.toml.tmpl`, `Brewfile.tmpl`, le script `brew bundle` et le
  bootstrap pour utiliser la sélection définie à l'étape 2.
- Partir des 18 entrées de `Brewfile_macos` et expliciter les prérequis réellement
  nécessaires aux dotfiles et à leurs wrappers.
- Avec `package_profile = "base"`, charger ce socle et uniquement l'éventuel
  `Brewfile_<hostname>` de la machine.
- Conditionner les installations annexes : applications 1Password/Codex, plugins
  IA, outils npm/Go/Cargo, runtimes, Docker/Colima et applications App Store.
  Les options supplémentaires sont désactivées au départ ; leur activation
  doit être explicite et apparaître dans la prévisualisation.
- Faire respecter les couches à mise. L'architecture Intel ne doit pas activer
  à elle seule tous les langages et outils de développement en mode base.
- Vérifier que shell et complétions supportent les outils optionnels absents.
  Tout outil requis via un shim doit avoir une version effectivement sélectionnée.
- Conserver les contraintes du Mac professionnel, notamment les droits limités.

Premier jalon : sur un Mac neuf, le choix base est enregistré avant `apply`, la
prévisualisation exclut personnel/pro et une nouvelle application reste locale
à cette machine. Les autres Macs gardent leurs listes actuelles à ce stade.

## 4. Appliquer les couches sous Linux

Travail :

- Extraire les bases des listes apt, dnf, pacman et rpm-ostree, puis isoler les
  usages actuellement mêlés aux profils desktop/server.
- Appliquer la même sélection à Linuxbrew, AUR, Flatpak et Snap. La présence
  d'un environnement graphique ne doit pas déclencher un ensemble d'applications
  personnelles lorsque seule la base a été choisie.
- Adapter les wrappers existants pour soustraire toutes les couches partagées
  actives lors des exports, puis écrire les ajouts dans le fichier machine.
- Corriger `yayw` pour utiliser `Pacfile_aur_<hostname>`.
- Préserver les règles propres à Fedora Atomic, Toolbox, OmArchy, aux serveurs
  et au Raspberry Pi, notamment architecture, droits et portée user/system.

Jalon : une nouvelle machine Linux en base n'hérite ni des applications desktop,
ni des paquets particuliers d'une autre machine de la même distribution.

## 5. Appliquer les couches sous Windows

Travail :

- Séparer le contenu actuel en base Scoop, usages et fichiers par machine.
  Conserver une voie de compatibilité pour les installations existantes pendant
  que leurs besoins propres sont identifiés.
- Adapter l'installateur pour fusionner les fichiers choisis, applications et
  buckets compris. Un fichier machine absent représente zéro ajout.
- Remplacer l'export global de `scoopw` par un delta tenant compte de toutes les
  couches partagées actives et des exclusions existantes.
- Aligner les installations complémentaires, notamment 1Password et Docker,
  sur les choix explicites. Ne pas supposer que Windows bénéficie du script
  d'installation mise utilisé sous Unix.

Jalon : installer une application sur Windows A ne l'ajoute pas à Windows B.

## 6. Garantir la portée des opérations des wrappers

Ces règles sont définies à l'étape 2 et livrées avec chaque OS :

- Une installation ponctuelle modifie le fichier de la machine par défaut.
- Une promotion vers l'usage ou la base demande une portée explicite et montre
  les machines concernées. Ne pas déduire cette portée du seul paquet installé.
- Une suppression locale ne réécrit jamais une liste partagée. Pour un paquet
  hérité, prévoir un retrait explicite propre à la machine, appliqué par le même
  sélecteur, afin d'éviter une réinstallation au prochain `apply`.
- Les exports dédupliquent base et usage, conservent les identités/options
  pertinentes et n'effacent pas les déclarations non gérées par leur dumper
  (notamment npm, Go et Cargo dans les Brewfiles).
- Un échec d'installation ou d'export ne publie pas un état partiel ou vide.
  Les commits et pushes restent limités aux fichiers effectivement modifiés
  par le wrapper, sans changement de la politique Git globale.

## 7. Alléger les usages et migrer les machines existantes

Travail :

- Construire des listes personnel/professionnel limitées aux besoins réellement
  partagés. L'utilisation sur un seul Mac ne suffit pas à rendre un paquet commun.
- Reporter les extras dans les fichiers des machines concernées à partir de
  l'inventaire et de la correspondance validée, sans attribuer arbitrairement
  tous les anciens paquets à toutes les machines.
- Migrer chaque configuration persistée vers un `package_profile` explicite,
  sans écraser les autres réglages locaux.
- Comparer les ensembles déclarés avant/après, y compris options et canaux
  d'installation. Tout ajout ou retrait doit être expliqué ; garder la
  compatibilité pour les machines dont la répartition n'est pas encore connue.
- Retirer la compatibilité seulement quand toutes les machines concernées ont
  une migration documentée. Les nouvelles machines ne doivent jamais l'hériter.

La réorganisation des listes ne désinstalle pas automatiquement les logiciels
déjà présents et ne lance pas de purge de toolchains. Les mises à jour continuent
à couvrir les logiciels installés, même retirés des listes, et à signaler les
échecs ou reports : le choix d'une base ne doit pas masquer des paquets obsolètes.

## 8. Valider et déployer progressivement

| Vérification | Résultat attendu |
| --- | --- |
| Installation neuve sans choix d'usage | Base et éventuels ajouts de cette machine uniquement |
| Profil inconnu | Erreur avant installation, sans repli vers personnel |
| Configuration existante sans nouveau champ | Compatibilité conservée jusqu'à migration explicite |
| Installation via chaque wrapper | Aucun fichier d'une autre machine ou partagé modifié |
| Promotion ou retrait local d'un paquet hérité | Portée explicite et résultat persistant au prochain `apply` |
| Fichier machine absent ou nouvelle entrée | Cas supporté, y compris création et suivi Git du nouveau fichier |
| Liste inactive modifiée | Aucun paquet de cet usage installé |
| Mise, plugins et scripts annexes | Aucun ensemble supplémentaire activé implicitement en base |
| Deux applications successives | Sélection et fichiers stables, pas de réinstallation provoquée par une divergence de listes |
| Mise à jour d'un paquet installé hors listes actives | Mise à jour tentée et échec signalé s'il reste obsolète |

Étendre les tests existants `test_breww.py`, `test_mise_scope.py`, les contrôles
de cohérence et de santé des mises à jour. Tester les wrappers avec de faux
gestionnaires pour vérifier les fichiers écrits et les erreurs sans installer
de logiciels. Ajouter les tests de sélection des couches et leur intégration CI.

La matrice doit couvrir macOS Apple Silicon/Intel, les distributions Linux déjà
prises en charge (dont RPi/Atomic/Toolbox/OmArchy) et Windows. Compléter les rendus
simulés par des vérifications natives Bash/PowerShell et des essais ciblés sur
les machines accessibles ; un rendu Linux simulant macOS ne constitue pas à lui
seul une validation sur Mac.

Ordre de déploiement : prévisualisation et tests, Neo en base, un Mac existant,
un poste Linux, Windows, puis les autres machines et serveurs. À chaque étape,
vérifier les fichiers sélectionnés, le démarrage du shell et la santé des mises
à jour avant d'élargir le déploiement.

Mettre à jour `README.md`, `docs/ARCHITECTURE.md`, `docs/ONBOARDING.md` et
`dot_private/README.md` avec le choix de la base, les promotions et la migration.
Le retour arrière doit couvrir à la fois les fichiers du dépôt et les valeurs
locales ajoutées dans `chezmoi.toml`, à partir des sauvegardes de migration.

## Ordre des livraisons

1. Inventaire et tests de référence.
2. Sélection des couches et compatibilité, sans bascule générale.
3. macOS, wrappers et scripts annexes : premier objectif utilisable pour le Neo.
4. Linux et ses wrappers.
5. Windows et Scoop.
6. Répartition des anciens paquets et migration progressive des machines.
7. Retrait de la compatibilité devenue inutile et documentation finale.

Les tests de portée accompagnent chaque livraison. La migration des machines
existantes dépend de leur inventaire ; elle ne bloque pas le jalon Neo en base.
