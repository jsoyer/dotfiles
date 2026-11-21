# Inventaire des manifestes de paquets

État relevé le 21 novembre 2026 dans `dot_private/` et
`dot_local/bin/package_layers.py`.

## Comptage

Le dépôt contient 83 fichiers dont le nom commence par un préfixe de manifeste.
Ce total comprend le modèle généré `Brewfile.tmpl`, le contrôle
`Brewfile_blacklist` et les deux listes de reports de mises à niveau
`Brewfile_cu_skip_*`. Il reste 79 manifestes de paquets concrets.

| Gestionnaire / famille | Fichiers concrets | Particularités |
| --- | ---: | --- |
| Homebrew | 25 | macOS, Linuxbrew, compatibilité, outils Go/npm/Cargo |
| APT | 12 | Debian, Ubuntu, RPi et couches base/usage |
| DNF | 9 | Fedora, Toolbox et couches base/usage |
| Pacman | 7 | Arch/Omarchy et couches usage |
| AUR | 6 | Manifestes `Pacfile_aur_*` |
| rpm-ostree | 3 | Fedora Atomic |
| Flatpak | 8 | bases de bureau historiques, RPi vide, usages |
| Snap | 5 | Ubuntu et usages |
| Scoop | 4 | JSON, dont le manifeste historique `Scoopfile.json` |
| **Total** | **79** | Hors modèle et fichiers de contrôle Homebrew |

Les fichiers par gestionnaire sont des formats indépendants. Une machine Linux
peut donc sélectionner à la fois un `Aptfile_<hôte>` et un
`Brewfile_<hôte>` ; ils ne sont jamais fusionnés dans un même fichier.

## Couches déclarées dans le catalogue

`dot_private/package-layers.json` est le catalogue lu par les templates chezmoi
et par le moteur Python. Il définit 14 profils techniques :

`mac-personal`, `mac-pro`, `ubuntu-desktop`, `ubuntu-server`, `debian`, `rpi`,
`fedora-desktop`, `fedora-server`, `toolbox`, `fedora-atomic`, `arch-desktop`,
`arch-server`, `omarchy`, `windows`.

Les gestionnaires configurés sont Homebrew, APT, DNF, Pacman, AUR, rpm-ostree,
Flatpak, Snap et Scoop. Pour les profils modernes, la résolution est :

```text
manifestes de base du profil technique
+ manifestes de l'usage choisi (base, personal, professional, server)
+ manifeste(s) du hostname pour chaque gestionnaire concerné
- exclusions propres à la machine
```

Les manifestes machine sont facultatifs. Le catalogue les cherche par
gestionnaire et hostname court : `Brewfile_<hôte>`, `Aptfile_<hôte>`,
`Dnffile_<hôte>`, `Pacfile_<hôte>`, `Pacfile_aur_<hôte>`,
`Rpmfile_<hôte>`, `Flatpakfile_<hôte>`, `Snapfile_<hôte>` et
`Scoopfile_<hôte>.json`.

Aujourd'hui, 21 manifestes correspondent à cette convention machine :

- Homebrew (15) : `Brewfile_Jerome-Soyers-Mac-Mini-M6`,
  `Brewfile_Jerome-Soyers-Mac-mini-M4`,
  `Brewfile_Jerome-Soyers-MacBook-Pro-14`,
  `Brewfile_Jerome-Soyers-MacMini-Intel`, `Brewfile_Jerome-Soyers-MacMini-M4`,
  `Brewfile_JeromeSacMiniM6`, `Brewfile_JeromeSrsMiniM6`, `Brewfile_Mac`,
  `Brewfile_MacBookPro`, `Brewfile_MacMiniIntel`, `Brewfile_diabolo`,
  `Brewfile_fedora-pve`, `Brewfile_jsoyer-macOS`, `Brewfile_looping`,
  `Brewfile_synapse`.
- APT (4) : `Aptfile_bbh-network`, `Aptfile_diabolo`, `Aptfile_looping`,
  `Aptfile_penelope`.
- DNF (2) : `Dnffile_fedora-pve`, `Dnffile_synapse`.
- Les autres gestionnaires n'ont actuellement aucun overlay machine nommé selon
  cette convention.

La présence d'un manifeste machine ne prouve pas qu'il est utilisé par la
machine dont le nom semble correspondre. Les anciens alias (`Mac`, `MacBookPro`,
`MacMiniIntel`), les changements de hostname et les hôtes réellement actifs
doivent être rapprochés avec les données de chaque machine avant fusion,
renommage ou suppression.

## Compatibilité et écarts de modèle

- `package_profile` absent sélectionne encore `legacy`. Les listes historiques
  (`Brewfile_personal`, `Brewfile_pro`, anciennes listes de distribution et
  `Scoopfile.json`) restent donc actives pour les machines non migrées.
- `legacy_brew_host_prefixes` donne à `omv-*` et `bbh-network*` des fichiers
  Linuxbrew dédiés (`Brewfile_brew_only`, `Brewfile_rpi`) au lieu du simple
  `Brewfile_<hostname>`.
- `packages.yaml` est un inventaire historique ; il n'est pas la source des
  listes installées. Les formats gérés restent les fichiers par gestionnaire.
- Le modèle `Brewfile.tmpl` assemble une sélection Homebrew pour `brew bundle`.
  Les installateurs et wrappers ont aussi des sources hors manifeste : scripts
  d'installation Linux, mise, options `install_*`, outils Go/npm/Cargo et
  applications App Store. Un éditeur de manifestes ne doit pas prétendre
  représenter ces installations tant qu'elles ne sont pas modélisées.
- `Brewfile_blacklist` et `Brewfile_cu_skip_*` sont des fichiers de contrôle,
  pas des listes d'installation. L'outil doit les identifier comme tels.
- `Flatpakfile_rpi` est vide ; les applications graphiques d'un Pi doivent être
  déclarées dans le manifeste Flatpak de l'hôte. La classification serveur ou
  bureau ne découle pas automatiquement de `machine_profile = rpi`.
- Le catalogue accepte `rpi/debian` comme alias de `rpi`.
- Aucun profil BSD n'est encore défini dans le catalogue ; l'éditeur expose
  uniquement les profils réellement résolus et ne propose donc pas encore BSD.

## Conséquences pour l'éditeur

1. Ne pas renommer ni déplacer massivement les manifestes pendant la première
   version. Les profils `legacy` sont une dépendance de compatibilité réelle.
2. L'éditeur travaille par machine et gestionnaire ; il peut présenter une vue
   fusionnée, mais enregistre une modification dans un seul manifeste ciblé.
3. Pour un paquet hérité, l'ajout/retrait local utilise les wrappers ou le
   fichier d'exclusions ; ne pas copier arbitrairement les couches partagées
   dans le fichier machine.
4. La création d'une machine ne doit pas inventer un hostname ou déduire que
   deux fichiers historiques désignent la même machine. Elle prévisualise les
   nouveaux noms de fichiers et signale les collisions.
5. La vue doit séparer les manifestes installables des listes de contrôle et
   signaler les installations supplémentaires provenant de scripts ou de mise
   comme hors du périmètre des manifestes.

## Capacités de l'outil existant

`package-plan` et `package_layers.py` résolvent déjà les sélections, affichent
les déclarations avec leurs fichiers sources, ajoutent/suppriment via wrappers,
gèrent les exclusions, promeuvent explicitement des paquets et migrent une
machine en mode aperçu par défaut. `package-plan create` enregistre le profil et
l'usage d'une nouvelle machine dans `package-machines.json` ; `package-plan tui`
permet d'ajouter ou retirer des paquets après aperçu du diff et confirmation.
L'outil reste au-dessus des manifestes existants. BSD et les sources d'installation
hors manifestes restent à intégrer ou présenter explicitement comme hors périmètre.
