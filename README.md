# VideoPress

Un outil de compression vidéo simple et efficace, par jdcproduction.

![Platform](https://img.shields.io/badge/platform-Windows-blue) ![Python](https://img.shields.io/badge/python-3.11-green) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Fonctionnalités

- Glisser-déposer plusieurs vidéos (ou sélection via bouton)
- File d'attente avec statut en temps réel (en cours, terminé, erreur)
- Choix de la qualité : Haute / Moyenne / Faible
- Choix de la résolution : Originale / 1080p / 720p / 480p
- Choix du format de sortie : MP4, MKV, AVI, MOV, WEBM
- Deux barres de progression (vidéo en cours + progression globale)
- Fichiers compressés sauvegardés dans le même dossier que les originaux

---

## Utilisation (Windows)

Télécharge le `.exe` depuis la section [Releases](../../releases) ou [Actions](../../actions) et double-clique dessus. Aucune installation requise.

---

## Structure du projet

```
Sanvicomp/
├── video_compressor.py       # Script principal
├── ffmpeg.exe                # Binaire FFmpeg Windows (bundlé dans le .exe)
├── fonts/
│   ├── Nunito-Regular.ttf
│   └── Nunito-Bold.ttf
└── .github/
    └── workflows/
        └── build.yml         # Compilation automatique Windows via GitHub Actions
```

---

## Compilation

Le `.exe` Windows est généré automatiquement via GitHub Actions à chaque push sur `main`.

Pour compiler manuellement sur Windows :

```bash
pip install pyinstaller tkinterdnd2
pyinstaller --onefile --windowed \
  --add-binary "ffmpeg.exe;." \
  --add-data "fonts;fonts" \
  --hidden-import tkinterdnd2 \
  --collect-data tkinterdnd2 \
  --name "VideoPress" video_compressor.py
```

Le `.exe` final se trouve dans `dist/VideoPress.exe`.

---

## Tester sur Mac

```bash
brew install ffmpeg
pip install tkinterdnd2
python video_compressor.py
```

---

## Dépendances

- [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) — traitement vidéo
- [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) — drag & drop
- [Nunito](https://fonts.google.com/specimen/Nunito) — police Google Fonts (OFL)