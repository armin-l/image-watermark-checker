# Bildwasserzeichen & Content Credentials Checker

Prototyp zum Prüfen von Bildern auf Wasserzeichen, C2PA-Metadaten und KI-generierte Inhalte.

## Features

- **C2PA / Content Authenticity** – Sucht nach eingebetteten Adobe C2PA-Manifests (Content Credentials)
- **Wasserzeichen-Erkennung** – Scannt Bilddaten für bekannte Watermark-Signaturen (Shutterstock, Getty Images, Canva etc.)
- **Perzeptuelle Hashes** – A-Hash, DCT-Hashes als Fingerabdruck des Bildinhalts
- **Externe Dienste** – Direkte Links zu Google Lens, TinEye, Adobe CAI Explorer, Optanomy, Glaze/NightGuard uvm.

## Installation

```bash
cd image-watermark-checker
pip install -r requirements.txt
python server.py
```

Dann im Browser öffnen: `http://localhost:5700`

Oder direkt die HTML-Datei im Browser öffnen (`file:///path/to/index.html`) – das Frontend funktioniert auch standalone mit Client-seitiger Analyse.

## Architektur

```
image-watermark-checker/
├── index.html          # Single-page WebApp (Upload + Vorschau + Ergebnisse)
├── app.py              # Kern-Analyse: C2PA, Perceptual Hashing, Watermark Detection
├── server.py           # Flask Server (optional)
└── requirements.txt    # Python Dependencies
```

## Externen Quellen

| Dienst | Typ | Kosten | Beschreibung |
|--------|-----|--------|--------------|
| **Google Lens Reverse Search** | Image Search | Kostenlos | Finde ähnliche Bilder im Google Index |
| **TinEye** | Image Search | API kostenpflichtig | Älteste reverse image search engine |
| **Adobe Content Authenticity Explorer** | Credentials Check | Kostenlos | Prüfe C2PA Content Credentials |
| **Optanomy AI Image Identifier** | AI Detection | Free tier | Erkennt ob Bild von KI generiert wurde |
| **Hive Moderation API** | AI Detection | $0.001/Bild | Deepfake/generative content detection |
| **SightEngine** | Analysis | 3000 Trial Credits | Bildanalyse-API |
| **Glaze / NightGuard** | Protection Check | Open Source | UChicago — perceptual fingerprinting |
| **Copyscape Images** | Plagiarism | Ab $5/page | Findet kopierte Bilder online |
| **Pimeyes Face Search** | Face Search | ~$27/search | Reverse image search für Gesichter |
