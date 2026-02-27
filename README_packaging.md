# VideoPress — Instructions de packaging

## Ce qu'il faut installer (sur ton poste de dev)

```
pip install pyinstaller
```

Python 3.x suffit — tkinter est inclus par défaut.

---

## Récupérer FFmpeg

1. Va sur https://www.gyan.dev/ffmpeg/builds/
2. Télécharge **ffmpeg-release-essentials.zip**
3. Décompresse et copie **ffmpeg.exe** (dans le dossier `bin/`) à côté de `video_compressor.py`

---

## Packager en .exe

Place-toi dans le dossier du projet, puis :

```bash
pyinstaller --onefile --windowed --add-binary "ffmpeg.exe;." --name "VideoPress" video_compressor.py
```

Le `.exe` final apparaît dans le dossier `dist/`.
Tu peux envoyer uniquement ce fichier à ta collègue — il est 100% autonome.

---

## Structure du projet avant packaging

```
ton_dossier/
├── video_compressor.py
└── ffmpeg.exe          ← téléchargé depuis gyan.dev
```

---

## Ce que fait l'outil

- Sélectionner une vidéo source (MP4, MKV, AVI, MOV, WEBM, WMV…)
- Choisir la qualité : Haute / Moyenne / Faible
- Conserver le format original **ou** choisir un nouveau format parmi MP4, MKV, AVI, MOV, WEBM
- Barre de progression en temps réel
- Le fichier compressé est sauvegardé dans le même dossier, avec le suffixe `_compressé`

---

## Notes

- Le `.exe` pèse ~80-100 Mo (FFmpeg bundlé)
- Aucune installation requise pour ta collègue
- Compatible Windows 10/11
