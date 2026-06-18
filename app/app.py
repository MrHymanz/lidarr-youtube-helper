import json
import os
import subprocess
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

@app.route("/download", methods=["POST"])
def download_queue():
    queue = load_json(QUEUE_FILE, [])
    processed = load_json(PROCESSED_FILE, [])
    remaining = []

    for item in queue:
        key = item["key"]
        mode = item.get("mode", "video")
        target = DOWNLOAD_DIR / key
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
