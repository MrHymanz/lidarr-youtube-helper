import json
import os
import subprocess
import difflib
import shutil
from pathlib import Path
from datetime import datetime

import requests
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

LIDARR_URL = os.environ["LIDARR_URL"].rstrip("/")
LIDARR_API_KEY = os.environ["LIDARR_API_KEY"]
DOWNLOAD_DIR = Path(os.environ["DOWNLOAD_DIR"])

QUEUE_FILE = Path("/app/queue.json")
PROCESSED_FILE = Path("/app/processed.json")
CACHE_FILE = Path("/app/cache.json")
SETTINGS_FILE = Path("/app/settings.json")
DOWNLOADS_FILE = Path("/app/downloads.json")
FAILED_FILE = Path("/app/failed.json")

HEADERS = {"X-Api-Key": LIDARR_API_KEY}


TRANSLATIONS = {
    "en": {
        "language_name": "English",
        "library": "Library",
        "activity": "Activity",
        "wanted": "Wanted",
        "settings": "Settings",
        "title": "Lidarr YouTube Helper",
        "how_to_use": "How to use this",
        "full_album_video": "Full Album Video",
        "full_album_desc": "Downloads one YouTube video as a single .m4a file.",
        "playlist_tracks": "Playlist / Album Tracks",
        "playlist_desc": "Downloads all tracks from a YouTube Music album or playlist as separate files. This is usually the best option for importing into Lidarr.",
        "recommended": "Recommended workflow:",
        "recommended_desc": "open the YouTube Music search link, find the album or playlist, paste its URL below, then select Playlist / Album Tracks.",
        "scan": "⟳ Scan Lidarr + search YouTube",
        "download_queue": "⬇ Download queue",
        "queue": "Queue",
        "queue_empty": "Queue is empty.",
        "review": "Review missing albums",
        "automatic_query": "Automatic search query:",
        "open_ytm": "Open YouTube Music search",
        "open_yt": "Open YouTube search",
        "automatic_results": "Automatic YouTube results",
        "best_video": "Usually best suited for Full Album Video mode.",
        "custom_url": "Custom YouTube / YouTube Music URL",
        "custom_placeholder": "Paste a YouTube Music album or playlist link here",
        "custom_hint": "Usually use Playlist / Album Tracks for this.",
        "download_mode": "Download mode",
        "single_video": "Full Album Video / single video",
        "single_video_hint": "One large audio file.",
        "playlist_hint": "Separate tracks. Best for YouTube Music albums/playlists and Lidarr import.",
        "skip": "Skip / mark as processed",
        "add_queue": "Add to queue",
        "settings_title": "Settings",
        "language": "Language",
        "save": "Save settings",
        "back": "Back",
        "incomplete_albums": "Incomplete Albums",
        "downloads": "Downloads",
        "completed": "Completed",
        "failed": "Failed",
        "queued": "Queued",
        "clear_completed": "Clear Completed",
        "clear_failed": "Clear Failed",
        "no_incomplete": "No incomplete albums found.",
        "partially_downloaded": "Partially downloaded albums",
        "tracks_present": "tracks present",
        "missing": "missing",
        "open_music_search": "Open YouTube Music search",
        "open_youtube_search": "Open YouTube search",
        "no_queued_downloads": "No queued downloads.",
        "no_completed_downloads": "No completed downloads yet.",
        "no_failed_downloads": "No failed downloads.",
        "mode": "Mode",
        "path": "Path",
        "error_details": "Error details",
        "partially_downloaded_albums": "Partially downloaded albums",
        "incomplete_help_1": "This page shows albums that already have some tracks, but are not complete yet.",
        "incomplete_help_2": "Albums with 0 tracks are ignored because they already appear in Lidarr Wanted / Missing.",
        "tracks": "Tracks",
        "track_status": "Track status",
        "track_status_help_1": "This page shows which tracks Lidarr already has and which tracks are missing.",
        "track_status_help_2": "Missing tracks include YouTube and YouTube Music search links.",
        "back_to_incomplete_albums": "Back to incomplete albums",
        "manual_track_url": "Paste YouTube / YouTube Music track URL",
        "add_track_to_queue": "Add track to queue",
        "import_preview": "Import Preview",
        "manual_track_url": "Paste YouTube / YouTube Music track URL",
        "add_track_to_queue": "Add track to queue",
        "import_preview": "Import Preview",
        "import_preview_help": "This page checks where downloaded tracks could be imported before moving anything.",
        "source_folder": "Source folder",
        "source_found": "Source folder found.",
        "source_not_found": "Source folder not found.",
        "target_candidates": "Target candidates",
        "match_score": "Match score",
        "auto_selected_target": "Only one target folder was found. This folder would be used automatically.",
        "no_target_candidates": "No target folders found.",
        "back": "Back",
        "best_match": "Best Match",
        "recommended": "Recommended",
        "import_recommended_folder": "Import to recommended folder",
        "import_this_folder": "Import to this folder",
        "audio_files_found": "Audio files found",
    },
    "nl": {
        "language_name": "Nederlands",
        "library": "Bibliotheek",
        "activity": "Activiteit",
        "wanted": "Gezocht",
        "settings": "Instellingen",
        "title": "Lidarr YouTube Helper",
        "how_to_use": "Hoe gebruik je dit?",
        "full_album_video": "Full Album Video",
        "full_album_desc": "Downloadt één YouTube-video als één .m4a-bestand.",
        "playlist_tracks": "Playlist / Album Tracks",
        "playlist_desc": "Downloadt alle tracks uit een YouTube Music album of playlist als losse bestanden. Dit is meestal de beste keuze voor importeren in Lidarr.",
        "recommended": "Aanbevolen workflow:",
        "recommended_desc": "open de YouTube Music zoeklink, zoek het album of de playlist, plak de URL hieronder en kies Playlist / Album Tracks.",
        "scan": "⟳ Scan Lidarr + zoek YouTube",
        "download_queue": "⬇ Download queue",
        "queue": "Queue",
        "queue_empty": "Queue is leeg.",
        "review": "Missende albums beoordelen",
        "automatic_query": "Automatische zoekopdracht:",
        "open_ytm": "Open YouTube Music zoekopdracht",
        "open_yt": "Open YouTube zoekopdracht",
        "automatic_results": "Automatische YouTube-resultaten",
        "best_video": "Meestal geschikt voor Full Album Video.",
        "custom_url": "Eigen YouTube / YouTube Music URL",
        "custom_placeholder": "Plak hier een YouTube Music album- of playlistlink",
        "custom_hint": "Gebruik hiervoor meestal Playlist / Album Tracks.",
        "download_mode": "Downloadmodus",
        "single_video": "Full Album Video / enkele video",
        "single_video_hint": "Eén groot audiobestand.",
        "playlist_hint": "Losse nummers. Beste keuze voor YouTube Music albums/playlists en Lidarr-import.",
        "skip": "Overslaan / markeer als verwerkt",
        "add_queue": "Toevoegen aan queue",
        "settings_title": "Instellingen",
        "language": "Taal",
        "save": "Instellingen opslaan",
        "back": "Terug",
        "incomplete_albums": "Onvolledige Albums",
        "downloads": "Downloads",
        "completed": "Voltooid",
        "failed": "Mislukt",
        "queued": "In Wachtrij",
        "clear_completed": "Voltooide Wissen",
        "clear_failed": "Mislukte Wissen",
        "no_incomplete": "Geen onvolledige albums gevonden.",
        "partially_downloaded": "Gedeeltelijk gedownloade albums",
        "tracks_present": "tracks aanwezig",
        "missing": "ontbrekend",
        "open_music_search": "Open YouTube Music zoekopdracht",
        "open_youtube_search": "Open YouTube zoekopdracht",
        "no_queued_downloads": "Geen downloads in de wachtrij.",
        "no_completed_downloads": "Nog geen voltooide downloads.",
        "no_failed_downloads": "Geen mislukte downloads.",
        "mode": "Modus",
        "path": "Pad",
        "error_details": "Foutdetails",
        "partially_downloaded_albums": "Gedeeltelijk gedownloade albums",
        "incomplete_help_1": "Deze pagina toont albums waarvan al enkele nummers aanwezig zijn, maar die nog niet compleet zijn.",
        "incomplete_help_2": "Albums met 0 nummers worden genegeerd omdat deze al zichtbaar zijn in Lidarr Wanted / Missing.",
        "tracks": "Nummers",
        "track_status": "Trackstatus",
        "track_status_help_1": "Deze pagina toont welke nummers Lidarr al heeft en welke nummers nog ontbreken.",
        "track_status_help_2": "Ontbrekende nummers bevatten directe zoeklinks naar YouTube en YouTube Music.",
        "back_to_incomplete_albums": "Terug naar onvolledige albums",
        "manual_track_url": "Plak YouTube / YouTube Music track-URL",
        "add_track_to_queue": "Track toevoegen aan queue",
        "import_preview": "Importvoorbeeld",
        "manual_track_url": "Plak YouTube / YouTube Music track-URL",
        "add_track_to_queue": "Track toevoegen aan queue",
        "import_preview": "Importvoorbeeld",
        "import_preview_help": "Deze pagina controleert waar gedownloade nummers geïmporteerd kunnen worden voordat er iets wordt verplaatst.",
        "source_folder": "Bronmap",
        "source_found": "Bronmap gevonden.",
        "source_not_found": "Bronmap niet gevonden.",
        "target_candidates": "Doelmap-kandidaten",
        "match_score": "Matchscore",
        "auto_selected_target": "Er is maar één doelmap gevonden. Deze map zou automatisch gebruikt worden.",
        "no_target_candidates": "Geen doelmappen gevonden.",
        "back": "Terug",
        "best_match": "Beste match",
        "recommended": "Aanbevolen",
        "import_recommended_folder": "Importeer naar aanbevolen map",
        "import_this_folder": "Importeer naar deze map",
        "audio_files_found": "Audiobestanden gevonden",
    },
    "no": {
        "language_name": "Norsk",
        "library": "Bibliotek",
        "activity": "Aktivitet",
        "wanted": "Ønsket",
        "settings": "Innstillinger",
        "title": "Lidarr YouTube Helper",
        "how_to_use": "Slik bruker du dette",
        "full_album_video": "Full Album Video",
        "full_album_desc": "Laster ned én YouTube-video som én .m4a-fil.",
        "playlist_tracks": "Playlist / Album Tracks",
        "playlist_desc": "Laster ned alle spor fra et YouTube Music-album eller en spilleliste som separate filer. Dette er vanligvis best for import i Lidarr.",
        "recommended": "Anbefalt arbeidsflyt:",
        "recommended_desc": "åpne YouTube Music-søket, finn albumet eller spillelisten, lim inn URL-en nedenfor og velg Playlist / Album Tracks.",
        "scan": "⟳ Skann Lidarr + søk YouTube",
        "download_queue": "⬇ Last ned kø",
        "queue": "Kø",
        "queue_empty": "Køen er tom.",
        "review": "Gå gjennom manglende album",
        "automatic_query": "Automatisk søk:",
        "open_ytm": "Åpne YouTube Music-søk",
        "open_yt": "Åpne YouTube-søk",
        "automatic_results": "Automatiske YouTube-resultater",
        "best_video": "Vanligvis best egnet for Full Album Video.",
        "custom_url": "Egen YouTube / YouTube Music URL",
        "custom_placeholder": "Lim inn en YouTube Music album- eller spillelistelenke her",
        "custom_hint": "Bruk vanligvis Playlist / Album Tracks for dette.",
        "download_mode": "Nedlastingsmodus",
        "single_video": "Full Album Video / enkeltvideo",
        "single_video_hint": "Én stor lydfil.",
        "playlist_hint": "Separate spor. Best for YouTube Music-album/spillelister og Lidarr-import.",
        "skip": "Hopp over / merk som behandlet",
        "add_queue": "Legg til i kø",
        "settings_title": "Innstillinger",
        "language": "Språk",
        "save": "Lagre innstillinger",
        "back": "Tilbake",
        "incomplete_albums": "Ufullstendige Album",
        "downloads": "Nedlastinger",
        "completed": "Fullført",
        "failed": "Mislykket",
        "queued": "I Kø",
        "clear_completed": "Tøm Fullførte",
        "clear_failed": "Tøm Mislykkede",
        "no_incomplete": "Ingen ufullstendige album funnet.",
        "partially_downloaded": "Delvis nedlastede album",
        "tracks_present": "spor tilgjengelig",
        "missing": "mangler",
        "open_music_search": "Åpne YouTube Music-søk",
        "open_youtube_search": "Åpne YouTube-søk",
        "no_queued_downloads": "Ingen nedlastinger i kø.",
        "no_completed_downloads": "Ingen fullførte nedlastinger ennå.",
        "no_failed_downloads": "Ingen mislykkede nedlastinger.",
        "mode": "Modus",
        "path": "Sti",
        "error_details": "Feildetaljer",
        "partially_downloaded_albums": "Delvis nedlastede album",
        "incomplete_help_1": "Denne siden viser album som allerede har noen spor, men som ennå ikke er komplette.",
        "incomplete_help_2": "Album med 0 spor ignoreres fordi de allerede vises i Lidarr Wanted / Missing.",
        "tracks": "Spor",
        "track_status": "Sporstatus",
        "track_status_help_1": "Denne siden viser hvilke spor Lidarr allerede har og hvilke som mangler.",
        "track_status_help_2": "Manglende spor inkluderer søkelenker til YouTube og YouTube Music.",
        "back_to_incomplete_albums": "Tilbake til ufullstendige album",
        "manual_track_url": "Lim inn YouTube / YouTube Music spor-URL",
        "add_track_to_queue": "Legg spor i kø",
        "import_preview": "Importforhåndsvisning",
        "manual_track_url": "Lim inn YouTube / YouTube Music spor-URL",
        "add_track_to_queue": "Legg spor til i kø",
        "import_preview_help": "Denne siden sjekker hvor nedlastede spor kan importeres før noe flyttes.",
        "source_folder": "Kildemappe",
        "source_found": "Kildemappe funnet.",
        "source_not_found": "Kildemappe ikke funnet.",
        "target_candidates": "Målmappekandidater",
        "match_score": "Treffscore",
        "auto_selected_target": "Bare én målmappe ble funnet. Denne ville blitt brukt automatisk.",
        "no_target_candidates": "Ingen målmapper funnet.",
        "best_match": "Beste treff",
        "recommended": "Anbefalt",
        "import_recommended_folder": "Importer til anbefalt mappe",
        "import_this_folder": "Importer til denne mappen",
        "audio_files_found": "Lydfiler funnet",
    },
}


def load_json(path, default):
    if not path.exists():
        return default

    try:
        content = path.read_text().strip()
        if not content:
            return default

        return json.loads(content)
    except json.JSONDecodeError:
        return default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def add_download_record(path, record):
    data = load_json(path, [])
    data.insert(0, record)
    save_json(path, data[:200])    

def get_settings():
    settings = load_json(SETTINGS_FILE, {"language": "en"})
    if settings.get("language") not in TRANSLATIONS:
        settings["language"] = "en"
    return settings

def t():
    return TRANSLATIONS[get_settings()["language"]]

def get_missing(limit=50):
    r = requests.get(
        f"{LIDARR_URL}/api/v1/wanted/missing?page=1&pageSize={limit}",
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("records", [])

def yt_search(query):
    cmd = [
        "yt-dlp",
        f"ytsearch3:{query}",
        "--simulate",
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)

    items = []
    for line in result.stdout.splitlines():
        try:
            data = json.loads(line)
            url = data.get("webpage_url") or data.get("url")
            if url and not url.startswith("http"):
                url = f"https://www.youtube.com/watch?v={url}"
            items.append({"title": data.get("title"), "url": url, "duration": data.get("duration")})
        except Exception:
            pass
    return items

def get_artist_by_id(artist_id):
    r = requests.get(
        f"{LIDARR_URL}/api/v1/artist",
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()

    return next(
        (artist for artist in r.json() if str(artist.get("id")) == str(artist_id)),
        None,
    )


def find_album_target_candidates(album):
    print("[MATCH] function called", flush=True)
    artist = album.get("artist") or get_artist_by_id(get_artist_by_id(artist_id))

    if not artist:
        print(f"[MATCH] No artist found for artistId: {album.get('artistId')}", flush=True)
        return []

    artist_path = Path(artist.get("path", ""))
    album_title = album.get("title", "")
    release_year = (album.get("releaseDate") or "")[:4]

    if not artist_path.exists():
        return []

    folders = [p for p in artist_path.iterdir() if p.is_dir()]

    search_names = [
        album_title,
        f"{album_title} ({release_year})" if release_year else album_title,
        f"{artist.get('artistName')} - {album_title}",
    ]

    scored = []

    print(f"[MATCH] Artist path: {artist_path}", flush=True)
    print(f"[MATCH] Album title: {album_title}", flush=True)
    print(f"[MATCH] Search names: {search_names}", flush=True)
    print(f"[MATCH] Artist path exists: {artist_path.exists()}", flush=True)

    for folder in folders:
        folder_name = folder.name.lower()

        base_score = max(
            difflib.SequenceMatcher(None, folder_name, name.lower()).ratio()
            for name in search_names
        )

        bonus = 0

        # Lidarr album folders met jaartal zijn meestal betrouwbaarder
        if (
            release_year
            and f"({release_year})" in folder.name
            and album_title.lower() in folder_name
        ):
            bonus += 0.20

        # Folder begint exact met albumtitel: sterke match
        if folder_name.startswith(album_title.lower()):
            bonus += 0.10

        # Folder begint met artist - album: ook goed, maar iets minder sterk
        artist_album_name = f"{artist.get('artistName')} - {album_title}".lower()
        if folder_name.startswith(artist_album_name):
            bonus += 0.05

        final_score = base_score + bonus

        print(
            f"[MATCH] {folder.name} -> base {round(base_score * 100, 1)}%, "
            f"bonus {round(bonus * 100, 1)}%, final {round(final_score * 100, 1)}%",
            flush=True
        )

        if final_score >= 0.90:
            scored.append({
                "path": str(folder),
                "name": folder.name,
                "score": round(final_score * 100, 1),
                "base_score": round(base_score * 100, 1),
                "bonus": round(bonus * 100, 1),
            })

    return sorted(scored, key=lambda item: item["score"], reverse=True)

@app.route("/")
def index():
    queue = load_json(QUEUE_FILE, [])
    processed = load_json(PROCESSED_FILE, [])
    cache = load_json(CACHE_FILE, [])

    albums = [
        item for item in cache
        if item["key"] not in processed
        and not any(q["key"] == item["key"] for q in queue)
    ]

    return render_template(
        "index.html",
        albums=albums,
        queue=queue,
        tr=t(),
        lidarr_url=LIDARR_URL
    )

@app.route("/downloads")
def downloads():
    queue = load_json(QUEUE_FILE, [])
    completed = load_json(DOWNLOADS_FILE, [])
    failed = load_json(FAILED_FILE, [])

    return render_template(
        "downloads.html",
        tr=t(),
        queue=queue,
        completed=completed,
        failed=failed,
        lidarr_url=LIDARR_URL,
    )

def get_incomplete_albums():
    r = requests.get(
        f"{LIDARR_URL}/api/v1/album",
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()

    albums = []

    for album in r.json():
        stats = album.get("statistics", {})

        track_count = stats.get("trackCount", 0)
        file_count = stats.get("trackFileCount", 0)

        if file_count > 0 and file_count < track_count:
            artist = album.get("artist", {}).get("artistName", "Unknown Artist")
            title = album.get("title", "Unknown Album")
            year = (album.get("releaseDate") or "")[:4]

            search_query = f"{artist} {title} {year}"
            music_search_url = "https://music.youtube.com/search?q=" + requests.utils.quote(search_query)
            youtube_search_url = "https://www.youtube.com/results?search_query=" + requests.utils.quote(search_query)

            albums.append({
                "id": album.get("id"),
                "artist": artist,
                "album": title,
                "year": year,
                "track_count": track_count,
                "file_count": file_count,
                "missing_count": track_count - file_count,
                "percent": stats.get("percentOfTracks", 0),
                "music_search_url": music_search_url,
                "youtube_search_url": youtube_search_url,
            })

    return albums


@app.route("/incomplete")
def incomplete():
    albums = get_incomplete_albums()

    return render_template(
        "incomplete.html",
        tr=t(),
        albums=albums,
        lidarr_url=LIDARR_URL,
    )

@app.route("/downloads/clear-completed", methods=["POST"])
def clear_completed():
    save_json(DOWNLOADS_FILE, [])
    return redirect(url_for("downloads"))


@app.route("/downloads/clear-failed", methods=["POST"])
def clear_failed():
    save_json(FAILED_FILE, [])
    return redirect(url_for("downloads"))

@app.route("/settings", methods=["GET", "POST"])
def settings():
    current = get_settings()

    if request.method == "POST":
        language = request.form.get("language", "en")
        if language not in TRANSLATIONS:
            language = "en"
        save_json(SETTINGS_FILE, {"language": language})
        return redirect(url_for("settings"))

    return render_template(
        "settings.html",
        tr=t(),
        current_language=current["language"],
        languages=TRANSLATIONS,
        lidarr_url=LIDARR_URL
    )
def get_album_details(album_id):
    albums = requests.get(
        f"{LIDARR_URL}/api/v1/album",
        headers=HEADERS,
        timeout=30,
    )
    albums.raise_for_status()

    album = next(
        (a for a in albums.json() if str(a.get("id")) == str(album_id)),
        None,
    )

    if not album:
        return None, []

    tracks = requests.get(
        f"{LIDARR_URL}/api/v1/track?albumId={album_id}",
        headers=HEADERS,
        timeout=30,
    )
    tracks.raise_for_status()

    return album, tracks.json()


@app.route("/album/<album_id>")
def album_details(album_id):
    album, tracks = get_album_details(album_id)

    if not album:
        return "Album not found", 404

    artist = album.get("artist", {}).get("artistName", "Unknown Artist")
    album_title = album.get("title", "Unknown Album")

    queue = load_json(QUEUE_FILE, [])
    queued_keys = {q.get("key") for q in queue}

    formatted_tracks = []

    for track in tracks:
        title = track.get("title", "Unknown Track")
        track_number = track.get("trackNumber", "")
        has_file = bool(track.get("trackFileId"))

        search_query = f"{artist} {title}"
        music_search_url = "https://music.youtube.com/search?q=" + requests.utils.quote(search_query)
        youtube_search_url = "https://www.youtube.com/results?search_query=" + requests.utils.quote(search_query)

        queue_key = f"{artist} - {album_title} - {title}"

        formatted_tracks.append({
            "title": title,
            "track_number": track_number,
            "has_file": has_file,
            "is_queued": queue_key in queued_keys,
            "music_search_url": music_search_url,
            "youtube_search_url": youtube_search_url,
        })

    return render_template(
        "album.html",
        tr=t(),
        album=album,
        artist=artist,
        album_title=album_title,
        tracks=formatted_tracks,
        lidarr_url=LIDARR_URL,
    )

def get_audio_files(path):
    audio_extensions = {".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wav"}

    if not path.exists():
        return []

    return sorted(
        [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in audio_extensions],
        key=lambda p: p.name.lower(),
    )

@app.route("/album/<album_id>/import-preview")
def album_import_preview(album_id):
    print("[IMPORT PREVIEW] route called", flush=True)
    album, tracks = get_album_details(album_id)

    if not album:
        return "Album not found", 404

    artist = album.get("artist", {}).get("artistName", "Unknown Artist")
    album_title = album.get("title", "Unknown Album")

    source_path = DOWNLOAD_DIR / f"{artist} - {album_title}"
    audio_files = get_audio_files(source_path)
    candidates = find_album_target_candidates(album)

    return render_template(
        "import_preview.html",
        tr=t(),
        album=album,
        artist=artist,
        album_title=album_title,
        source_path=str(source_path),
        source_exists=source_path.exists(),
        audio_files=audio_files,
        candidates=candidates,
        lidarr_url=LIDARR_URL,
    )

@app.route("/album/<int:album_id>/import", methods=["POST"])
def album_import(album_id):
    album, tracks = get_album_details(album_id)

    if not album:
        return "Album not found", 404

    artist = album.get("artist", {}).get("artistName", "Unknown Artist")
    album_title = album.get("title", "Unknown Album")

    source_path = DOWNLOAD_DIR / f"{artist} - {album_title}"
    target_path = Path(request.form["target_path"])

    if not source_path.exists():
        return f"Source folder not found: {source_path}", 404

    if not target_path.exists():
        return f"Target folder not found: {target_path}", 404

    audio_extensions = {".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wav"}

    moved = []

    for file in source_path.iterdir():
        if not file.is_file():
            continue

        if file.suffix.lower() not in audio_extensions:
            continue

        destination = target_path / file.name

        if destination.exists():
            print(f"[IMPORT] Skipping existing file: {destination}", flush=True)
            continue

        shutil.move(str(file), str(destination))
        moved.append(file.name)

    print(
        f"[IMPORT] Moved {len(moved)} files from {source_path} to {target_path}",
        flush=True,
    )

    return redirect(url_for("album_import_preview", album_id=album_id))

@app.route("/scan", methods=["POST"])
def scan():
    missing = get_missing(limit=50)
    cache = []

    for item in missing:
        artist = item.get("artist", {}).get("artistName", "Unknown Artist")
        album = item.get("title", "Unknown Album")
        year = (item.get("releaseDate") or "")[:4]
        key = f"{artist} - {album}"

        query = f"{artist} {album} {year} full album"
        results = yt_search(query)

        music_search_query = f"{artist} {album} {year}"
        music_search_url = "https://music.youtube.com/search?q=" + requests.utils.quote(music_search_query)
        youtube_search_url = "https://www.youtube.com/results?search_query=" + requests.utils.quote(music_search_query)

        cache.append({
            "key": key,
            "artist": artist,
            "album": album,
            "year": year,
            "query": query,
            "music_search_url": music_search_url,
            "youtube_search_url": youtube_search_url,
            "results": results,
        })

    save_json(CACHE_FILE, cache)
    return redirect(url_for("index"))

@app.route("/queue", methods=["POST"])
def add_queue():
    queue = load_json(QUEUE_FILE, [])
    processed = load_json(PROCESSED_FILE, [])

    key = request.form["key"]
    artist = request.form["artist"]
    album = request.form["album"]

    custom_url = request.form.get("custom_url", "").strip()
    selected_url = request.form.get("url", "").strip()
    mode = request.form.get("mode", "video")

    url = custom_url if custom_url else selected_url

    if url == "skip":
        processed.append(key)
        save_json(PROCESSED_FILE, sorted(set(processed)))
        return redirect(url_for("index"))

    if url and not any(q["key"] == key for q in queue):
        queue.append({"key": key, "artist": artist, "album": album, "url": url, "mode": mode})
        save_json(QUEUE_FILE, queue)

    return redirect(url_for("index"))

@app.route("/queue/remove", methods=["POST"])
def remove_queue_item():
    queue = load_json(QUEUE_FILE, [])
    key = request.form.get("key")

    queue = [item for item in queue if item["key"] != key]
    save_json(QUEUE_FILE, queue)

    return redirect(url_for("index"))

@app.route("/queue/clear", methods=["POST"])
def clear_queue():
    save_json(QUEUE_FILE, [])
    return redirect(url_for("index"))

@app.route("/queue/move", methods=["POST"])
def move_queue_item():
    queue = load_json(QUEUE_FILE, [])
    key = request.form.get("key")
    direction = request.form.get("direction")

    index = next((i for i, item in enumerate(queue) if item["key"] == key), None)

    if index is not None:
        if direction == "up" and index > 0:
            queue[index - 1], queue[index] = queue[index], queue[index - 1]

        if direction == "down" and index < len(queue) - 1:
            queue[index + 1], queue[index] = queue[index], queue[index + 1]

    save_json(QUEUE_FILE, queue)

    return redirect(url_for("index"))

@app.route("/track/queue", methods=["POST"])
def add_missing_track_to_queue():
    queue = load_json(QUEUE_FILE, [])

    artist = request.form.get("artist", "").strip()
    album = request.form.get("album", "").strip()
    track = request.form.get("track", "").strip()
    url = request.form.get("url", "").strip()

    if not url:
        return redirect(request.referrer or url_for("incomplete"))

    album_key = f"{artist} - {album}"
    queue_key = f"{artist} - {album} - {track}"

    if not any(q["key"] == queue_key for q in queue):
        queue.append({
            "key": queue_key,
            "target": album_key,
            "artist": artist,
            "album": album,
            "url": url,
            "mode": "video",
        })
        save_json(QUEUE_FILE, queue)

    return redirect(request.referrer or url_for("downloads"))

@app.route("/download", methods=["POST"])
def download_queue():
    queue = load_json(QUEUE_FILE, [])
    processed = load_json(PROCESSED_FILE, [])
    remaining = []

    for item in queue:
        key = item["key"]
        mode = item.get("mode", "video")
        target = DOWNLOAD_DIR / item.get("target", key)
        target.mkdir(parents=True, exist_ok=True)

        if mode == "playlist":
            output_template = "%(playlist_index,track_number|)02d - %(title)s.%(ext)s"
            cmd = [
                "yt-dlp",
                item["url"],
                "--yes-playlist",
                "--ignore-errors",
                "--no-abort-on-error",
                "-f", "bestaudio[ext=m4a]/bestaudio/best",
                "--embed-thumbnail",
                "--add-metadata",
                "-o", str(target / output_template),
            ]
        else:
            cmd = [
                "yt-dlp",
                item["url"],
                "--no-playlist",
                "-f", "bestaudio[ext=m4a]/bestaudio/best",
                "--embed-thumbnail",
                "--add-metadata",
                "-o", str(target / "%(title)s.%(ext)s"),
            ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        downloaded_files = (
            list(target.glob("*.m4a")) +
            list(target.glob("*.mp3")) +
            list(target.glob("*.opus"))
        )

        record = {
            "timestamp": datetime.now().isoformat(),
            "key": key,
            "mode": mode,
            "url": item["url"],
            "path": str(target),
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
        }

        if result.returncode == 0 or downloaded_files:
            processed.append(key)
            add_download_record(DOWNLOADS_FILE, record)
        else:
            remaining.append(item)
            add_download_record(FAILED_FILE, record)

    save_json(PROCESSED_FILE, sorted(set(processed)))
    save_json(QUEUE_FILE, remaining)

    return redirect(url_for("downloads"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8999)
