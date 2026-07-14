# Fach- und Hausarztpraxis Dres. Ertl – Website

Statische Neuimplementierung der Website der Fach- und Hausarztpraxis Dres. Ertl.

## Struktur

- `src/content/`: Textinhalte (YAML-Dateien), gegliedert nach Bereichen (Aktuelles, Leistungen, Ärzte, Team, Seiten).
- `src/uploads/`: Original-Bilder und Medien.
- `src/styles/`: CSS-Dateien und lokale Webfonts (Open Sans & Roboto).
- `templates/`: Jinja2/Twig-Templates für das Layout.
- `build.py`: Python-Build-Skript, das die responsive Bildgenerierung, CSS-Minifizierung und das HTML-Rendering durchführt.
- `public/`: Der generierte, fertige Build-Ordner (wird per Skript erstellt).

## Lokale Entwicklung

### 1. Abhängigkeiten installieren
Für das Build-Skript wird Python 3.7+ sowie die Bibliothek `Pillow`, `PyYAML`, `Jinja2` und `markdown` benötigt:
```bash
pip install Pillow PyYAML Jinja2 markdown
```

### 2. Website generieren/bauen
Um die statischen HTML-Seiten und komprimierten Bilder im `public/`-Ordner zu erzeugen, führen Sie das Build-Skript aus:
```bash
python build.py
```

### 3. Lokalen Webserver starten
Da die Website relative Pfade ohne explicit `.html` verwendet (Clean URLs), müssen die Seiten über einen lokalen Webserver aufgerufen werden:
```bash
python -m http.server 8080 -d public
```
Rufen Sie anschließend **`http://localhost:8080`** in Ihrem Browser auf.
