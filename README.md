# praxis-dr-ertl.de

Statische Neuimplementierung der Website der Fach- und Hausarztpraxis Dres. Ertl
(vorher WordPress + Elementor) mit [Astro](https://astro.build) und
[Decap CMS](https://decapcms.org). Gehostet auf Netlify, Inhalte in diesem
Git-Repository (GitLab).

## Struktur

| Pfad | Inhalt |
| --- | --- |
| `src/content/aktuelles/` | Einträge der Startseite (je eine Markdown-Datei, `sichtbar: false` blendet aus) |
| `src/content/leistungen/` | Die 10 Leistungen mit Icon, Bild und Aufzählung |
| `src/content/aerzte/` | Ärzteteam inkl. Lebenslauf-Stationen (eigene Unterseite je Ärztin/Arzt) |
| `src/content/team/` | Praxisteam (Name, Rolle, Foto) |
| `src/content/seiten/` | Impressum und Datenschutzerklärung |
| `src/data/praxis.yaml` | Kontaktdaten, Sprechzeiten, Terminland-Link, oranger Balken |
| `src/data/ueber-uns.yaml` | Galerie, Zähler, Willkommenstext, Info-Boxen |
| `public/uploads/` | Alle Bilder (Medienordner des CMS) |
| `public/admin/` | Decap CMS (erreichbar unter `/admin/`) |

Seiten: `/` (Aktuelles), `/ueber-uns/`, `/praxisteam/`, `/praxisteam/<name>/`
(Lebensläufe), `/leistungen/`, `/kontakt/`, `/impressum/`, `/datenschutz/`.

## Lokal entwickeln

```bash
npm install
npm run dev          # http://localhost:4321
```

CMS lokal ohne GitLab-Login testen: in `public/admin/config.yml` die Zeile
`local_backend: true` aktivieren und zusätzlich `npx decap-server` starten.

## Einmalige Einrichtung (Deployment)

### 1. GitLab

1. Neues Projekt anlegen (z. B. `praxis-dr-ertl`) und dieses Repo pushen:
   ```bash
   git remote add origin git@gitlab.com:<gruppe>/praxis-dr-ertl.git
   git push -u origin main
   ```
2. In `public/admin/config.yml` das Feld `repo:` auf den GitLab-Pfad setzen.

### 2. GitLab-Login für das CMS (PKCE — kein eigener Auth-Server nötig)

1. GitLab → User Settings (oder Group Settings) → **Applications** → neue Application:
   - **Name:** Praxis CMS
   - **Redirect URI:** `https://praxis-dr-ertl.de/admin/` (bzw. die Netlify-URL)
   - **Scopes:** `api`
   - **Confidential:** NICHT ankreuzen
2. Die angezeigte **Application ID** in `public/admin/config.yml` bei `app_id:` eintragen.
3. Redakteure brauchen ein GitLab-Konto mit mindestens **Developer**-Rechten auf dem Repo.
   Login dann einfach über `https://praxis-dr-ertl.de/admin/`.

> Hinweis: Netlify Identity wird bewusst nicht verwendet — der Dienst ist
> veraltet und für neue Sites geschlossen. Die Anmeldung läuft direkt über GitLab.

### 3. Netlify

1. „Add new site“ → „Import an existing project“ → GitLab-Repo wählen.
   Build-Einstellungen kommen automatisch aus `netlify.toml`
   (`npm run build`, Publish-Verzeichnis `dist`).
2. **Formular (Online-Rezeptformular):** Netlify erkennt das Formular
   `rezeptformular` automatisch beim ersten Deploy. Unter
   *Site → Forms → Notifications* eine E-Mail-Benachrichtigung an die Praxis
   einrichten. Achtung: Gesundheitsdaten — Aufbewahrung in Netlify Forms unter
   *Forms → Verified submissions* regelmäßig löschen (die Praxis löscht laut
   Einwilligung nach 3 Monaten).
3. Domain `praxis-dr-ertl.de` unter *Domain management* verbinden.

## Inhalte pflegen

Alles Redaktionelle geht über `https://<domain>/admin/`:

- **Aktuelles:** Einträge anlegen/ausblenden (Schalter „Sichtbar“ — ideal für
  Urlaubs-Hinweise, die jedes Jahr wiederkommen), Reihenfolge per Zahl.
- **Leistungen / Ärzteteam / Praxisteam:** Einträge mit Bildern und Listen.
- **Einstellungen:** Sprechzeiten, Telefonnummern, oranger Termin-Balken.
- Jede Änderung erzeugt einen Git-Commit; Netlify baut und veröffentlicht
  automatisch (ca. 1–2 Minuten).

## Bewusste Abweichungen vom Original

- Kein Cookie-Banner: Die Seite setzt keine Tracking-Cookies mehr, daher ist
  keine Einwilligung nötig. Google Maps lädt weiterhin erst nach Klick
  (Datenschutz bleibt gewahrt).
- Google Fonts werden lokal ausgeliefert (DSGVO-konform, kein Request an Google).
- Footer-Zeile zeigt „© Jahr Praxisname“ statt des WordPress-Theme-Hinweises.
- URLs der Lebensläufe: `/praxisteam/dr-katharina-ertl/` statt
  `/lebenslauf-dr-katharina-ertl/`.
