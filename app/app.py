import json
import os
import subprocess
import difflib
import shutil
import re
import unicodedata
import time
import requests
from pathlib import Path
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, url_for
from urllib.parse import parse_qs, urlparse

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

LIDARR_URL = os.environ["LIDARR_URL"].rstrip("/")
LIDARR_API_KEY = os.environ["LIDARR_API_KEY"]
DOWNLOAD_DIR = Path(os.environ["DOWNLOAD_DIR"])
YOUTUBE_COOKIES_FILE = Path(
    os.getenv(
        "YOUTUBE_COOKIES_FILE",
        "/config/secrets/youtube-cookies.txt",
    )
)
YOUTUBE_COOKIES_MAX_SIZE = 2 * 1024 * 1024

QUEUE_FILE = Path("/app/queue.json")
PROCESSED_FILE = Path("/app/processed.json")
CACHE_FILE = Path("/app/cache.json")
SETTINGS_FILE = Path("/app/settings.json")
DOWNLOADS_FILE = Path("/app/downloads.json")
FAILED_FILE = Path("/app/failed.json")
PLAYLISTS_FILE = Path("/app/playlists.json")

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
        "audio_files_found": "Audio files found",
        "import_success": "Import completed",
        "import_moved_files": "{count} audio file(s) imported.",
        "import_skipped_files": "{count} file(s) skipped.",
        "import_no_files": "No audio files were imported.",
        "lidarr_scan_started": "Lidarr refresh started.",
        "lidarr_scan_failed": "Files were imported, but the Lidarr refresh failed.",
        "metadata_failed_files": "{count} file(s) could not be processed because metadata normalization failed.",
        "track_match_failed_files": "{count} file(s) could not be matched to a Lidarr track.",
        "review_metadata": "Review metadata",
        "metadata_review": "Metadata review",
        "current_metadata": "Current metadata",
        "suggested_metadata": "Suggested metadata",
        "artist": "Artist",
        "album_artist": "Album artist",
        "album": "Album",
        "track_title": "Track title",
        "track_number": "Track number",
        "disc_number": "Disc number",
        "year": "Year",
        "genre": "Genre",
        "filename": "Filename",
        "apply_metadata": "Apply metadata",
        "metadata_apply_success": "Metadata was updated successfully.",
        "metadata_apply_failed": "Metadata could not be updated.",
        "no_source_files_title": "Nothing to prepare",
        "no_source_files_message": "No downloaded audio files are available for this album yet. Add a missing track to the queue and complete the download first.",
        "target": "Target",
        "lidarr_import_check": "Lidarr import check",
        "lidarr_candidates_found": "Import candidates found",
        "lidarr_rejections": "Lidarr rejected this candidate",
        "lidarr_candidate_ready": "Lidarr considers this candidate ready for import.",
        "no_lidarr_candidates": "Lidarr did not return any import candidates.",
        "show_raw_response": "Show technical details",
        "lidarr_candidates_filtered": "{shown} of {total} candidates belong to this album.",
        "manual_override_required": "Lidarr did not automatically select this album. A manual album and track override has been prepared.",
        "manual_override_preview": "Manual import mapping",
        "lidarr_import_accepted": "Lidarr heeft de importopdracht geaccepteerd. De verwerking wordt nog gecontroleerd.",
        "go_to_downloads": "Go to downloads",
        "import_via_lidarr": "Import via Lidarr",
        "review_import_downloads": "Review and import downloads",
        "review_import_downloads_help": (
            "Review downloaded audio files, correct metadata, "
            "match them to Lidarr tracks and import them through Lidarr."
        ),
        "import_workflow": "Download review and import",
        "import_workflow_help": (
            "Review downloaded files, correct their metadata and import them "
            "into the selected Lidarr album."
        ),
        "lidarr_import_completed": (
            "Import completed: {filename} was imported by Lidarr."
        ),
        "lidarr_import_failed": (
            "The Lidarr import failed."
        ),
        "lidarr_import_completed_source_remaining": (
            "Lidarr completed the import command, but the source file "
            "is still present in the download folder."
        ),
        "lidarr_import_still_processing": (
            "Lidarr is still processing the import. Refresh this page in a few seconds."
        ),
        "track_already_exists": (
            "A matching file already exists in the Lidarr album folder. "
            "The file may already be linked to the track, or Lidarr may still need to recognize it."
        ),
        "replace_existing_file": (
            "Replace the existing file in the album folder during individual import"
        ),
        "batch_import_title": "Import multiple tracks",
        "batch_import_help": (
            "Import all selected and reviewed tracks one by one. "
            "Existing tracks will not be replaced automatically."
        ),
        "batch_import_ready_count": "Tracks ready for batch import",
        "batch_import_button": "Import selected tracks",
        "include_in_batch_import": "Include in batch import",
        "batch_existing_track_excluded": (
            "A matching file already exists in the Lidarr album folder. "
            "This track is therefore not automatically included in the batch. "
            "Import the track individually and select 'Replace existing file' "
            "if you want to overwrite the current file."
        ),
        "batch_metadata_not_ready": (
            "Apply the suggested metadata before including this track "
            "in the batch import."
        ),
        "batch_import_no_files_selected": (
            "No tracks were selected for batch import."
        ),
        "batch_import_completed": (
            "Batch import completed: {imported} imported, "
            "{skipped} skipped and {failed} failed."
        ),
        "batch_import_no_files_imported": (
            "No tracks were imported. "
            "{skipped} skipped and {failed} failed."
        ),
        "batch_import_primary_title": "Import ready tracks as a batch",
        "batch_import_primary_help": (
            "Select the reviewed tracks you want to import as a batch. "
            "Tracks with mismatched metadata or an existing file in the destination "
            "folder are excluded."
        ),
        "batch_selected_count": "{count} track(s) selected",
        "batch_import_selected": "Import selected tracks via Lidarr",
        "metadata_ready": "Metadata is ready",
        "metadata_needs_changes": "Metadata needs to be applied",
        "edit_metadata": "Edit metadata",
        "apply_metadata_and_prepare": "Apply metadata",
        "ready_for_batch_import": "Ready for batch import",
        "not_ready_for_batch_import": "Not ready for batch import",
        "individual_import": "Import individually",
        "individual_import_help": (
            "This action is performed separately. Select the replace option "
            "to safely remove the existing file before importing the new file."
        ),
        "playlists": "Playlists",
        "playlist_management": "Playlist management",
        "playlist_management_help": (
            "Save YouTube and YouTube Music playlists and manually add them "
            "to the download queue."
        ),
        "add_playlist": "Add playlist",
        "playlist_name": "Name",
        "playlist_name_placeholder": "For example: Discover Weekly",
        "playlist_url": "YouTube / YouTube Music playlist URL",
        "playlist_url_placeholder": "Paste a playlist URL",
        "playlist_target": "Optional target folder",
        "playlist_target_placeholder": (
            "Leave empty to use the normal download folder"
        ),
        "saved_playlists": "Saved playlists",
        "no_saved_playlists": "No playlists have been saved yet.",
        "add_to_queue": "Add to queue",
        "delete": "Delete",
        "playlist_name_url_required": (
            "A playlist name and URL are required."
        ),
        "playlist_invalid_url": "Enter a valid playlist URL.",
        "playlist_already_exists": (
            "A playlist with this URL has already been saved."
        ),
        "playlist_added": "Playlist saved.",
        "playlist_not_found": "Playlist not found.",
        "playlist_already_queued": (
            "This playlist is already in the download queue."
        ),
        "playlist_added_to_queue": (
            "Playlist added to the download queue."
        ),
        "playlist_deleted": "Playlist deleted: {name}",
        "optional": "Optional",
        "playlist_name_placeholder": "Leave empty to retrieve the playlist name",
        "playlist_url_required": "A playlist URL is required.",
        "playlist_title_lookup_failed": (
            "The playlist name could not be retrieved. Enter a name manually."
        ),
        "playlist_title_generic": (
            "YouTube Music returned only a generic mix name. "
            "Enter the desired playlist name manually."
        ),
        "add_all_playlists_to_queue": "Add all playlists to queue",
        "playlists_added_to_queue": (
            "{added} playlist(s) added to the queue. "
            "{skipped} playlist(s) skipped."
        ),
        "all_playlists_already_queued": (
            "All saved playlists are already in the download queue."
        ),
        "playlist_deleted_with_queue": (
            "Playlist deleted and removed from the download queue: {name}"
        ),
        "playlist_watch_url_hint": (
            "This YouTube Music mix cannot be downloaded using the playlist URL.\n\n"
            "Open the mix, click one of the tracks so the URL becomes:\n"
            "https://music.youtube.com/watch?v=...&list=...\n\n"
            "Then add that watch URL instead.\n"
        ),
        "clear_queue": "Clear queue",
        "playlist_max_items": "Maximum number of tracks",
        "downloaded_new": "Newly downloaded",
        "available_total": "Total available",
        # ------------------------------------------------------------------
        # YouTube cookies
        # ------------------------------------------------------------------

        "youtube_cookies": "YouTube session",
        "youtube_cookies_help": (
            "Upload a cookies.txt file exported from your browser to "
            "allow downloading private or personalized YouTube Music playlists."
        ),
        "youtube_cookies_consent": (
            "I understand that this file grants access to my YouTube session "
            "and I allow Lidarr YouTube Helper to store and use it locally."
        ),
        "youtube_cookies_upload": "Upload cookies",
        "youtube_cookies_delete": "Delete cookies",
        "youtube_cookies_file": "cookies.txt file",
        "youtube_cookies_status_present": "A cookies file is configured.",
        "youtube_cookies_status_missing": "No cookies file configured.",

        "youtube_cookies_consent_required":
            "You must agree before uploading a cookies file.",
        "youtube_cookies_file_required":
            "Please select a cookies.txt file.",
        "youtube_cookies_upload_success":
            "Cookies uploaded successfully.",
        "youtube_cookies_upload_failed":
            "The cookies file could not be saved.",
        "youtube_cookies_delete_success":
            "Cookies deleted successfully.",
        "youtube_cookies_delete_failed":
            "The cookies file could not be deleted.",

        "youtube_cookies_empty":
            "The uploaded file is empty.",
        "youtube_cookies_too_large":
            "The uploaded file is too large.",
        "youtube_cookies_invalid_encoding":
            "The uploaded file is not valid UTF-8.",
        "youtube_cookies_invalid_format":
            "The uploaded file is not a valid Netscape cookies file.",
        "youtube_cookies_no_cookies":
            "No cookies were found in the uploaded file.",
        "youtube_cookies_no_youtube_cookies":
            "The uploaded file does not contain YouTube cookies.",

        "youtube_cookies_required_hint":
            "This playlist requires a signed-in YouTube session. Upload a cookies.txt file in Settings.",
        "youtube_cookies_expired_hint":
            "The stored YouTube session has expired. Upload a new cookies.txt file in Settings.",
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
        "audio_files_found": "Audiobestanden gevonden",
        "import_success": "Import voltooid",
        "import_moved_files": "{count} audiobestand(en) geïmporteerd.",
        "import_skipped_files": "{count} bestand(en) overgeslagen.",
        "import_no_files": "Er zijn geen audiobestanden geïmporteerd.",
        "lidarr_scan_started": "Lidarr-verversing is gestart.",
        "lidarr_scan_failed": "De bestanden zijn geïmporteerd, maar de Lidarr-verversing is mislukt.",
        "metadata_failed_files": "{count} bestand(en) konden niet worden verwerkt doordat de metadata-aanpassing mislukte.",
        "track_match_failed_files": "{count} bestand(en) konden niet aan een Lidarr-track worden gekoppeld.",
        "review_metadata": "Metadata controleren",
        "metadata_review": "Metadata controleren",
        "current_metadata": "Huidige metadata",
        "suggested_metadata": "Voorgestelde metadata",
        "artist": "Artiest",
        "album_artist": "Albumartiest",
        "album": "Album",
        "track_title": "Tracktitel",
        "track_number": "Tracknummer",
        "disc_number": "Discnummer",
        "year": "Jaar",
        "genre": "Genre",
        "filename": "Bestandsnaam",
        "apply_metadata": "Metadata toepassen",
        "metadata_apply_success": "De metadata is succesvol bijgewerkt.",
        "metadata_apply_failed": "De metadata kon niet worden bijgewerkt.",
        "no_source_files_title": "Niets om voor te bereiden",
        "no_source_files_message": "Er zijn nog geen gedownloade audiobestanden voor dit album. Voeg eerst een ontbrekend nummer toe aan de wachtrij en rond de download af.",
        "target": "Doel",
        "lidarr_import_check": "Lidarr-importcontrole",
        "lidarr_candidates_found": "Importkandidaten gevonden",
        "lidarr_rejections": "Lidarr heeft deze kandidaat afgewezen",
        "lidarr_candidate_ready": "Lidarr beschouwt deze kandidaat als gereed voor import.",
        "no_lidarr_candidates": "Lidarr heeft geen importkandidaten teruggegeven.",
        "show_raw_response": "Technische details tonen",
        "lidarr_candidates_filtered": "{shown} van de {total} kandidaten horen bij dit album.",
        "manual_override_required": "Lidarr heeft dit album niet automatisch geselecteerd. Er is een handmatige album- en trackkoppeling voorbereid.",
        "manual_override_preview": "Handmatige importkoppeling",
        "lidarr_import_accepted": "Lidarr accepted the import request. Processing still needs to be verified.",
        "go_to_downloads": "Naar downloads",
        "import_via_lidarr": "Importeren via Lidarr",
        "review_import_downloads": "Downloads controleren en importeren",
        "review_import_downloads_help": (
            "Controleer gedownloade audiobestanden, pas metadata aan, "
            "koppel ze aan Lidarr-tracks en importeer ze via Lidarr."
        ),
        "import_workflow": "Downloads controleren en importeren",
        "import_workflow_help": (
            "Controleer gedownloade bestanden, corrigeer de metadata en "
            "importeer ze in het geselecteerde Lidarr-album."
        ),
        "lidarr_import_completed": (
            "Import voltooid: {filename} is door Lidarr geïmporteerd."
        ),
        "lidarr_import_failed": (
            "De Lidarr-import is mislukt."
        ),
        "lidarr_import_completed_source_remaining": (
            "Lidarr heeft de importopdracht voltooid, maar het bronbestand "
            "staat nog in de downloadmap."
        ),
        "lidarr_import_still_processing": (
            "Lidarr verwerkt de import nog. Vernieuw deze pagina over enkele seconden."
        ),
        "track_already_exists": (
            "Er staat al een passend bestand in de Lidarr-albummap. "
            "Het bestand kan al gekoppeld zijn, of nog door Lidarr herkend moeten worden."
        ),
        "replace_existing_file": (
        "Bij individuele import het bestaande bestand in de albummap vervangen"
        ),
        "batch_import_title": "Meerdere tracks importeren",
        "batch_import_help": (
            "Importeer alle geselecteerde, gecontroleerde tracks achter elkaar. "
            "Bestaande tracks worden niet automatisch vervangen."
        ),
        "batch_import_ready_count": "Tracks gereed voor batchimport",
        "batch_import_button": "Geselecteerde tracks importeren",
        "include_in_batch_import": "Meenemen in batchimport",
        "batch_existing_track_excluded": (
            "Er staat al een passend bestand in de Lidarr-albummap. "
            "Deze track wordt daarom niet automatisch in de batch opgenomen. "
            "Importeer de track individueel en vink 'Bestaand bestand vervangen' aan "
            "als je het huidige bestand wilt overschrijven."
        ),
        "batch_metadata_not_ready": (
            "Pas eerst de voorgestelde metadata toe voordat deze track "
            "in de batch kan worden opgenomen."
        ),
        "batch_import_no_files_selected": (
            "Er zijn geen tracks geselecteerd voor batchimport."
        ),
        "batch_import_completed": (
            "Batchimport afgerond: {imported} geïmporteerd, "
            "{skipped} overgeslagen en {failed} mislukt."
        ),
        "batch_import_no_files_imported": (
            "Er zijn geen tracks geïmporteerd. "
            "{skipped} overgeslagen en {failed} mislukt."
        ),
        "batch_import_primary_title": "Gereedstaande tracks als batch importeren",
        "batch_import_primary_help": (
            "Selecteer de gecontroleerde tracks die je wilt importeren als batch. "
            "Tracks met afwijkende metadata of een bestaand bestand in de doelmap "
            "worden uitgesloten."
        ),
        "batch_selected_count": "{count} track(s) geselecteerd",
        "batch_import_selected": "Geselecteerde tracks importeren via Lidarr",
        "metadata_ready": "Metadata is gereed",
        "metadata_needs_changes": "Metadata moet nog worden toegepast",
        "edit_metadata": "Metadata bewerken",
        "apply_metadata_and_prepare": "Metadata toepassen",
        "ready_for_batch_import": "Gereed voor batchimport",
        "not_ready_for_batch_import": "Niet gereed voor batchimport",
        "individual_import": "Individueel importeren",
        "individual_import_help": (
            "Gebruik dit alleen om een bestand te testen, opnieuw te proberen "
            "of een bestaand bestand te vervangen."
        ),
        "playlists": "Playlists",
        "playlist_management": "Playlistbeheer",
        "playlist_management_help": (
            "Sla YouTube- en YouTube Music-playlists op en voeg ze "
            "handmatig toe aan de downloadwachtrij."
        ),
        "add_playlist": "Playlist toevoegen",
        "playlist_name": "Naam",
        "playlist_name_placeholder": "Bijvoorbeeld: Discover Weekly",
        "playlist_url": "YouTube / YouTube Music-playlist-URL",
        "playlist_url_placeholder": "Plak hier een playlist-URL",
        "playlist_target": "Optionele doelmap",
        "playlist_target_placeholder": (
            "Laat leeg om de normale downloadmap te gebruiken"
        ),
        "saved_playlists": "Opgeslagen playlists",
        "no_saved_playlists": "Er zijn nog geen playlists opgeslagen.",
        "add_to_queue": "Aan wachtrij toevoegen",
        "delete": "Verwijderen",
        "playlist_name_url_required": (
            "Een playlistnaam en URL zijn verplicht."
        ),
        "playlist_invalid_url": "Voer een geldige playlist-URL in.",
        "playlist_already_exists": (
            "Er is al een playlist met deze URL opgeslagen."
        ),
        "playlist_added": "Playlist opgeslagen.",
        "playlist_not_found": "Playlist niet gevonden.",
        "playlist_already_queued": (
            "Deze playlist staat al in de downloadwachtrij."
        ),
        "playlist_added_to_queue": (
            "Playlist is aan de downloadwachtrij toegevoegd."
        ),
        "playlist_deleted": "Playlist verwijderd: {name}",
        "optional": "Optioneel",
        "playlist_name_placeholder": (
            "Laat leeg om de playlistnaam automatisch op te halen"
        ),
        "playlist_url_required": "Een playlist-URL is verplicht.",
        "playlist_title_lookup_failed": (
            "De playlistnaam kon niet worden opgehaald. Vul de naam handmatig in."
        ),
        "playlist_title_generic": (
            "YouTube Music gaf alleen een algemene mixnaam terug. "
            "Vul de gewenste playlistnaam handmatig in."
        ),
        "add_all_playlists_to_queue": "Alle playlists aan wachtrij toevoegen",
        "playlists_added_to_queue": (
            "{added} playlist(s) aan de wachtrij toegevoegd. "
            "{skipped} playlist(s) overgeslagen."
        ),
        "all_playlists_already_queued": (
            "Alle opgeslagen playlists staan al in de downloadwachtrij."
        ),
        "playlist_deleted_with_queue": (
            "Playlist verwijderd en uit de downloadwachtrij gehaald: {name}"
        ),
        "playlist_watch_url_hint": (
            "Deze YouTube Music-mix kan niet worden gedownload met de playlist-URL.\n\n"
            "Open de mix, klik op een nummer zodat de URL verandert naar:\n"
            "https://music.youtube.com/watch?v=...&list=...\n\n"
            "Voeg vervolgens die watch-URL toe.\n"
        ),
        "clear_queue": "Wachtrij wissen",
        "playlist_max_items": "Maximum aantal nummers",
        "downloaded_new": "Nieuw gedownload",
        "available_total": "Totaal aanwezig",
        # ------------------------------------------------------------------
        # YouTube-cookies
        # ------------------------------------------------------------------

        "youtube_cookies": "YouTube-sessie",
        "youtube_cookies_help": (
            "Upload een uit je browser geëxporteerd cookies.txt-bestand om "
            "privé- of gepersonaliseerde YouTube Music-playlists te kunnen downloaden."
        ),
        "youtube_cookies_consent": (
            "Ik begrijp dat dit bestand toegang geeft tot mijn YouTube-sessie "
            "en geef Lidarr YouTube Helper toestemming om dit lokaal op te slaan en te gebruiken."
        ),
        "youtube_cookies_upload": "Cookies uploaden",
        "youtube_cookies_delete": "Cookies verwijderen",
        "youtube_cookies_file": "cookies.txt-bestand",
        "youtube_cookies_status_present": "Er is een cookiesbestand geconfigureerd.",
        "youtube_cookies_status_missing": "Er is geen cookiesbestand geconfigureerd.",

        "youtube_cookies_consent_required":
            "Je moet eerst akkoord gaan voordat je een cookiesbestand kunt uploaden.",
        "youtube_cookies_file_required":
            "Selecteer een cookies.txt-bestand.",
        "youtube_cookies_upload_success":
            "Cookies succesvol geüpload.",
        "youtube_cookies_upload_failed":
            "Het cookiesbestand kon niet worden opgeslagen.",
        "youtube_cookies_delete_success":
            "Cookies succesvol verwijderd.",
        "youtube_cookies_delete_failed":
            "Het cookiesbestand kon niet worden verwijderd.",

        "youtube_cookies_empty":
            "Het geüploade bestand is leeg.",
        "youtube_cookies_too_large":
            "Het geüploade bestand is te groot.",
        "youtube_cookies_invalid_encoding":
            "Het geüploade bestand is geen geldig UTF-8-bestand.",
        "youtube_cookies_invalid_format":
            "Het geüploade bestand is geen geldig Netscape-cookiesbestand.",
        "youtube_cookies_no_cookies":
            "Er zijn geen cookies gevonden in het geüploade bestand.",
        "youtube_cookies_no_youtube_cookies":
            "Het geüploade bestand bevat geen YouTube-cookies.",

        "youtube_cookies_required_hint":
            "Voor deze playlist is een aangemelde YouTube-sessie vereist. Upload een cookies.txt-bestand via Instellingen.",
        "youtube_cookies_expired_hint":
            "De opgeslagen YouTube-sessie is verlopen. Upload een nieuw cookies.txt-bestand via Instellingen.",
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
        "audio_files_found": "Lydfiler funnet",
        "import_success": "Import fullført",
        "import_moved_files": "{count} lydfil(er) importert.",
        "import_skipped_files": "{count} fil(er) hoppet over.",
        "import_no_files": "Ingen lydfiler ble importert.",
        "lidarr_scan_started": "Lidarr-oppdatering startet.",
        "lidarr_scan_failed": "Filene ble importert, men Lidarr-oppdateringen mislyktes.",
        "metadata_failed_files": "{count} fil(er) kunne ikke behandles fordi metadataoppdateringen mislyktes.",
        "track_match_failed_files": "{count} fil(er) kunne ikke kobles til et Lidarr-spor.",
        "review_metadata": "Kontroller metadata",
        "metadata_review": "Metadatakontroll",
        "current_metadata": "Nåværende metadata",
        "suggested_metadata": "Foreslått metadata",
        "artist": "Artist",
        "album_artist": "Albumartist",
        "album": "Album",
        "track_title": "Sportittel",
        "track_number": "Spornummer",
        "disc_number": "Platenummer",
        "year": "År",
        "genre": "Sjanger",
        "filename": "Filnavn",
        "apply_metadata": "Bruk metadata",
        "metadata_apply_success": "Metadata ble oppdatert.",
        "metadata_apply_failed": "Metadata kunne ikke oppdateres.",
        "no_source_files_title": "Ingenting å klargjøre",
        "no_source_files_message": "Det finnes ingen nedlastede lydfiler for dette albumet ennå. Legg først et manglende spor i køen og fullfør nedlastingen.",
        "target": "Mål",
        "lidarr_import_check": "Lidarr-importkontroll",
        "lidarr_candidates_found": "Importkandidater funnet",
        "lidarr_rejections": "Lidarr avviste denne kandidaten",
        "lidarr_candidate_ready": "Lidarr vurderer kandidaten som klar for import.",
        "no_lidarr_candidates": "Lidarr returnerte ingen importkandidater.",
        "show_raw_response": "Vis tekniske detaljer",
        "lidarr_candidates_filtered": "{shown} av {total} kandidater tilhører dette albumet.",
        "manual_override_required": "Lidarr valgte ikke dette albumet automatisk. En manuell album- og sporkobling er klargjort.",
        "manual_override_preview": "Manuell importkobling",
        "lidarr_import_accepted": "Lidarr godtok importforespørselen. Behandlingen må fortsatt kontrolleres.",
        "go_to_downloads": "Gå til nedlastinger",
        "import_via_lidarr": "Importer via Lidarr",
        "review_import_downloads": "Kontroller og importer nedlastinger",
        "review_import_downloads_help": (
            "Kontroller nedlastede lydfiler, korriger metadata, "
            "koble dem til Lidarr-spor og importer dem via Lidarr."
        ),
        "import_workflow": "Kontroller og importer nedlastinger",
        "import_workflow_help": (
            "Kontroller nedlastede filer, korriger metadata og importer dem "
            "til det valgte Lidarr-albumet."
        ),
        "lidarr_import_completed": (
            "Import fullført: {filename} ble importert av Lidarr."
        ),
        "lidarr_import_failed": (
            "Lidarr-importen mislyktes."
        ),
        "lidarr_import_completed_source_remaining": (
            "Lidarr fullførte importkommandoen, men kildefilen "
            "finnes fortsatt i nedlastingsmappen."
        ),
        "lidarr_import_still_processing": (
            "Lidarr behandler fortsatt importen. Oppdater siden om noen sekunder."
        ),
        "track_already_exists": (
            "Det finnes allerede en passende fil i Lidarr-albummappen. "
            "Filen kan allerede være koblet til sporet, eller Lidarr må fortsatt gjenkjenne den."
        ),
        "replace_existing_file": (
            "Erstatt den eksisterende filen i albummappen ved individuell import"
        ),
        "batch_import_title": "Importer flere spor",
        "batch_import_help": (
            "Importer alle valgte og kontrollerte spor ett etter ett. "
            "Eksisterende spor erstattes ikke automatisk."
        ),
        "batch_import_ready_count": "Spor klare for masseimport",
        "batch_import_button": "Importer valgte spor",
        "include_in_batch_import": "Ta med i masseimport",
        "batch_existing_track_excluded": (
            "Det finnes allerede en samsvarende fil i Lidarr-albummappen. "
            "Dette sporet blir derfor ikke automatisk inkludert i gruppeimporten. "
            "Importer sporet individuelt og velg 'Erstatt eksisterende fil' "
            "hvis du vil overskrive den nåværende filen."
        ),
        "batch_metadata_not_ready": (
            "Bruk de foreslåtte metadataene før sporet kan tas med "
            "i masseimporten."
        ),
        "batch_import_no_files_selected": (
            "Ingen spor ble valgt for masseimport."
        ),
        "batch_import_completed": (
            "Masseimport fullført: {imported} importert, "
            "{skipped} hoppet over og {failed} mislyktes."
        ),
        "batch_import_no_files_imported": (
            "Ingen spor ble importert. "
            "{skipped} hoppet over og {failed} mislyktes."
        ),
        "batch_import_primary_title": "Importer klare spor som en gruppe",
        "batch_import_primary_help": (
            "Velg de kontrollerte sporene du vil importere som en gruppe. "
            "Spor med avvikende metadata eller en eksisterende fil i målmappen "
            "blir utelatt."
        ),
        "batch_selected_count": "{count} spor valgt",
        "batch_import_selected": "Importer valgte spor via Lidarr",
        "metadata_ready": "Metadata er klar",
        "metadata_needs_changes": "Metadata må brukes først",
        "edit_metadata": "Rediger metadata",
        "apply_metadata_and_prepare": "Bruk metadata",
        "ready_for_batch_import": "Klar for masseimport",
        "not_ready_for_batch_import": "Ikke klar for masseimport",
        "individual_import": "Importer individuelt",
        "individual_import_help": (
            "Denne handlingen utføres separat. Velg erstatningsalternativet "
            "for å fjerne den eksisterende filen på en sikker måte før den nye filen importeres."
        ),
        "playlists": "Spillelister",
        "playlist_management": "Spillelisteadministrasjon",
        "playlist_management_help": (
            "Lagre spillelister fra YouTube og YouTube Music og legg dem "
            "manuelt til i nedlastingskøen."
        ),
        "add_playlist": "Legg til spilleliste",
        "playlist_name": "Navn",
        "playlist_name_placeholder": "For eksempel: Discover Weekly",
        "playlist_url": "URL til YouTube / YouTube Music-spilleliste",
        "playlist_url_placeholder": "Lim inn en spilleliste-URL",
        "playlist_target": "Valgfri målmappe",
        "playlist_target_placeholder": (
            "La feltet stå tomt for å bruke den vanlige nedlastingsmappen"
        ),
        "saved_playlists": "Lagrede spillelister",
        "no_saved_playlists": "Ingen spillelister er lagret ennå.",
        "add_to_queue": "Legg til i kø",
        "delete": "Slett",
        "playlist_name_url_required": (
            "Navn og URL for spillelisten er påkrevd."
        ),
        "playlist_invalid_url": "Oppgi en gyldig spilleliste-URL.",
        "playlist_already_exists": (
            "En spilleliste med denne URL-en er allerede lagret."
        ),
        "playlist_added": "Spillelisten er lagret.",
        "playlist_not_found": "Spillelisten ble ikke funnet.",
        "playlist_already_queued": (
            "Denne spillelisten ligger allerede i nedlastingskøen."
        ),
        "playlist_added_to_queue": (
            "Spillelisten er lagt til i nedlastingskøen."
        ),
        "playlist_deleted": "Spilleliste slettet: {name}",
        "optional": "Valgfritt",
        "playlist_name_placeholder": (
            "Laat leeg om de playlistnaam automatisch op te halen"
        ),
        "playlist_url_required": "Een playlist-URL is verplicht.",
        "playlist_title_lookup_failed": (
            "De playlistnaam kon niet worden opgehaald. Vul de naam handmatig in."
        ),
        "playlist_title_generic": (
            "YouTube Music returnerte bare et generisk miksnavn. "
            "Skriv inn ønsket spillelistenavn manuelt."
        ),
        "add_all_playlists_to_queue": "Legg alle spillelister til i køen",
        "playlists_added_to_queue": (
            "{added} spilleliste(r) lagt til i køen. "
            "{skipped} spilleliste(r) hoppet over."
        ),
        "all_playlists_already_queued": (
            "Alle lagrede spillelister ligger allerede i nedlastingskøen."
        ),
        "playlist_deleted_with_queue": (
            "Spillelisten ble slettet og fjernet fra nedlastingskøen: {name}"
        ),
        "playlist_watch_url_hint": (
            "Denne YouTube Music-miksen kan ikke lastes ned med spillelisteadressen.\n\n"
            "Åpne miksen og klikk på et spor slik at adressen blir:\n"
            "https://music.youtube.com/watch?v=...&list=...\n\n"
            "Legg deretter til denne watch-adressen.\n"
        ),
        "clear_queue": "Tøm kø",
        "playlist_max_items": "Maksimalt antall spor",
        "downloaded_new": "Nylig lastet ned",
        "available_total": "Totalt tilgjengelig",
        # ------------------------------------------------------------------
        # YouTube-informasjonskapsler
        # ------------------------------------------------------------------

        "youtube_cookies": "YouTube-økt",
        "youtube_cookies_help": (
            "Last opp en cookies.txt-fil eksportert fra nettleseren din for å "
            "kunne laste ned private eller personlige YouTube Music-spillelister."
        ),
        "youtube_cookies_consent": (
            "Jeg forstår at denne filen gir tilgang til YouTube-økten min "
            "og gir Lidarr YouTube Helper tillatelse til å lagre og bruke den lokalt."
        ),
        "youtube_cookies_upload": "Last opp informasjonskapsler",
        "youtube_cookies_delete": "Slett informasjonskapsler",
        "youtube_cookies_file": "cookies.txt-fil",
        "youtube_cookies_status_present": "En informasjonskapselfil er konfigurert.",
        "youtube_cookies_status_missing": "Ingen informasjonskapselfil er konfigurert.",

        "youtube_cookies_consent_required":
            "Du må godta før du kan laste opp en informasjonskapselfil.",
        "youtube_cookies_file_required":
            "Velg en cookies.txt-fil.",
        "youtube_cookies_upload_success":
            "Informasjonskapslene ble lastet opp.",
        "youtube_cookies_upload_failed":
            "Informasjonskapselfilen kunne ikke lagres.",
        "youtube_cookies_delete_success":
            "Informasjonskapslene ble slettet.",
        "youtube_cookies_delete_failed":
            "Informasjonskapselfilen kunne ikke slettes.",

        "youtube_cookies_empty":
            "Den opplastede filen er tom.",
        "youtube_cookies_too_large":
            "Den opplastede filen er for stor.",
        "youtube_cookies_invalid_encoding":
            "Den opplastede filen er ikke gyldig UTF-8.",
        "youtube_cookies_invalid_format":
            "Den opplastede filen er ikke en gyldig Netscape-informasjonskapselfil.",
        "youtube_cookies_no_cookies":
            "Ingen informasjonskapsler ble funnet i den opplastede filen.",
        "youtube_cookies_no_youtube_cookies":
            "Den opplastede filen inneholder ingen YouTube-informasjonskapsler.",

        "youtube_cookies_required_hint":
            "Denne spillelisten krever en innlogget YouTube-økt. Last opp en cookies.txt-fil under Innstillinger.",
        "youtube_cookies_expired_hint":
            "Den lagrede YouTube-økten har utløpt. Last opp en ny cookies.txt-fil under Innstillinger.",
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

    artist_id = album.get("artistId")
    artist_value = album.get("artist")

    if isinstance(artist_value, dict):
        artist_data = artist_value
    else:
        artist_data = get_artist_by_id(artist_id)

    if not artist_data:
        print(
            f"[MATCH] No artist found for artistId: {artist_id}",
            flush=True,
        )
        return []

    artist_name = artist_data.get("artistName", "Unknown Artist")
    artist_path = Path(artist_data.get("path", ""))

    album_title = album.get("title", "Unknown Album")
    release_year = (album.get("releaseDate") or "")[:4]

    print(f"[MATCH] Artist ID: {artist_id}", flush=True)
    print(f"[MATCH] Artist name: {artist_name}", flush=True)
    print(f"[MATCH] Artist path: {artist_path}", flush=True)
    print(f"[MATCH] Album title: {album_title}", flush=True)
    print(f"[MATCH] Artist path exists: {artist_path.exists()}", flush=True)

    if not artist_path.exists():
        print(
            f"[MATCH] Artist path does not exist: {artist_path}",
            flush=True,
        )
        return []

    try:
        folders = [path for path in artist_path.iterdir() if path.is_dir()]
    except OSError as exc:
        print(
            f"[MATCH] Could not read artist path {artist_path}: {exc}",
            flush=True,
        )
        return []

    search_names = [
        album_title,
        (
            f"{album_title} ({release_year})"
            if release_year
            else album_title
        ),
        f"{artist_name} - {album_title}",
    ]

    print(f"[MATCH] Search names: {search_names}", flush=True)

    scored = []
    normalized_album_title = album_title.lower()
    artist_album_name = f"{artist_name} - {album_title}".lower()

    for folder in folders:
        folder_name = folder.name.lower()

        base_score = max(
            difflib.SequenceMatcher(
                None,
                folder_name,
                search_name.lower(),
            ).ratio()
            for search_name in search_names
        )

        bonus = 0.0

        if (
            release_year
            and f"({release_year})" in folder.name
            and normalized_album_title in folder_name
        ):
            bonus += 0.20

        if folder_name.startswith(normalized_album_title):
            bonus += 0.10

        if folder_name.startswith(artist_album_name):
            bonus += 0.05

        final_score = base_score + bonus

        print(
            f"[MATCH] {folder.name} -> "
            f"base {round(base_score * 100, 1)}%, "
            f"bonus {round(bonus * 100, 1)}%, "
            f"final {round(final_score * 100, 1)}%",
            flush=True,
        )

        if final_score >= 0.90:
            scored.append({
                "path": str(folder),
                "name": folder.name,
                "score": round(final_score * 100, 1),
                "base_score": round(base_score * 100, 1),
                "bonus": round(bonus * 100, 1),
            })

    return sorted(
        scored,
        key=lambda item: item["score"],
        reverse=True,
    )

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

def is_generic_playlist_title(title):
    if not title:
        return True

    generic_patterns = [
        r"^My Mix \d+$",
        r"^Mijn mix \d+$",
        r"^Mix \d+$",
    ]

    return any(
        re.match(pattern, title, re.IGNORECASE)
        for pattern in generic_patterns
    )

def get_playlist_title(url):
    if not url:
        return None

    cmd = [
        "yt-dlp",
        "--yes-playlist",
        "--flat-playlist",
        "--playlist-end",
        "1",
        "--print",
        "%(playlist_title)s",
    ]

    cookies_file = get_youtube_cookies_file()

    if cookies_file is not None:
        cmd.extend([
            "--cookies",
            str(cookies_file),
        ])

        print(
            f"[PLAYLIST TITLE] Using YouTube cookies: "
            f"{cookies_file}",
            flush=True,
        )

    cmd.append(url)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print(
            f"[PLAYLIST TITLE] Timeout while reading: {url}",
            flush=True,
        )
        return None

    if result.returncode != 0:
        print(
            f"[PLAYLIST TITLE] yt-dlp failed for {url}: "
            f"{result.stderr[-1000:]}",
            flush=True,
        )
        return None

    titles = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
        and line.strip().upper() not in {
            "NA",
            "NONE",
            "NULL",
        }
    ]

    if not titles:
        return None

    return titles[0] 

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

@app.route("/playlists")
def playlists():
    saved_playlists = load_json(PLAYLISTS_FILE, [])
    queue = load_json(QUEUE_FILE, [])

    queued_playlist_urls = {
        item.get("url")
        for item in queue
        if item.get("mode") == "playlist"
    }

    return render_template(
        "playlists.html",
        playlists=saved_playlists,
        queued_playlist_urls=queued_playlist_urls,
        tr=t(),
        lidarr_url=LIDARR_URL,
    )

def is_music_mix_playlist_url(url):
    parsed = urlparse(url)

    if parsed.hostname != "music.youtube.com":
        return False

    playlist_id = parse_qs(parsed.query).get("list", [""])[0]

    return playlist_id.startswith("RD")

@app.route("/playlists/add", methods=["POST"])
def add_playlist():
    tr = t()

    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    target = request.form.get("target", "").strip()

    max_items_raw = request.form.get("max_items", "20").strip()

    try:
        max_items = int(max_items_raw)
    except ValueError:
        max_items = 20

    max_items = max(1, min(max_items, 200))

    if not url:
        flash(tr["playlist_url_required"], "error")
        return redirect(url_for("playlists"))

    parsed_url = urlparse(url)

    allowed_hosts = {
        "youtube.com",
        "www.youtube.com",
        "music.youtube.com",
        "youtu.be",
    }

    if (
        parsed_url.scheme not in {"http", "https"}
        or parsed_url.hostname not in allowed_hosts
    ):
        flash(tr["playlist_invalid_url"], "error")
        return redirect(url_for("playlists"))

    if not name:
        detected_name = get_playlist_title(url)

        if is_generic_playlist_title(detected_name):
            flash(tr["playlist_title_generic"], "warning")
            return redirect(url_for("playlists"))

        name = detected_name

    if not name:
        flash(tr["playlist_title_lookup_failed"], "error")
        return redirect(url_for("playlists"))

    saved_playlists = load_json(PLAYLISTS_FILE, [])

    duplicate = any(
        playlist.get("url", "").strip() == url
        for playlist in saved_playlists
    )

    if duplicate:
        flash(tr["playlist_already_exists"], "warning")
        return redirect(url_for("playlists"))

    saved_playlists.append({
        "name": name,
        "url": url,
        "target": target,
        "max_items": max_items,
    })

    save_json(PLAYLISTS_FILE, saved_playlists)

    flash(tr["playlist_added"], "success")
    return redirect(url_for("playlists"))


@app.route(
    "/playlists/<int:playlist_index>/queue",
    methods=["POST"],
)
def queue_playlist(playlist_index):
    tr = t()
    saved_playlists = load_json(PLAYLISTS_FILE, [])

    if not 0 <= playlist_index < len(saved_playlists):
        flash(tr["playlist_not_found"], "error")
        return redirect(url_for("playlists"))

    playlist = saved_playlists[playlist_index]
    queue = load_json(QUEUE_FILE, [])

    queue_item = {
        "key": playlist["name"],
        "url": playlist["url"],
        "mode": "playlist",
        "target": playlist.get("target", ""),
        "max_items": playlist.get("max_items", 20),
    }

    already_queued = any(
        item.get("url") == queue_item["url"]
        and item.get("mode") == "playlist"
        for item in queue
    )

    if already_queued:
        flash(tr["playlist_already_queued"], "warning")
        return redirect(url_for("playlists"))

    queue.append(queue_item)
    save_json(QUEUE_FILE, queue)

    flash(tr["playlist_added_to_queue"], "success")
    return redirect(url_for("playlists"))


@app.route(
    "/playlists/<int:playlist_index>/delete",
    methods=["POST"],
)
def delete_playlist(playlist_index):
    tr = t()
    saved_playlists = load_json(PLAYLISTS_FILE, [])

    if not 0 <= playlist_index < len(saved_playlists):
        flash(tr["playlist_not_found"], "error")
        return redirect(url_for("playlists"))

    deleted_playlist = saved_playlists.pop(playlist_index)
    deleted_url = deleted_playlist.get("url", "").strip()

    save_json(PLAYLISTS_FILE, saved_playlists)

    queue = load_json(QUEUE_FILE, [])

    filtered_queue = [
        item
        for item in queue
        if not (
            item.get("mode") == "playlist"
            and item.get("url", "").strip() == deleted_url
        )
    ]

    removed_from_queue = len(queue) - len(filtered_queue)

    if removed_from_queue:
        save_json(QUEUE_FILE, filtered_queue)

        flash(
            tr["playlist_deleted_with_queue"].format(
                name=deleted_playlist.get("name", ""),
            ),
            "success",
        )
    else:
        flash(
            tr["playlist_deleted"].format(
                name=deleted_playlist.get("name", ""),
            ),
            "success",
        )

    return redirect(url_for("playlists"))

@app.route("/playlists/queue-all", methods=["POST"])
def queue_all_playlists():
    tr = t()

    saved_playlists = load_json(PLAYLISTS_FILE, [])
    queue = load_json(QUEUE_FILE, [])

    queued_playlist_urls = {
        item.get("url")
        for item in queue
        if item.get("mode") == "playlist"
    }

    added = 0
    skipped = 0

    for playlist in saved_playlists:
        playlist_url = playlist.get("url", "").strip()

        if not playlist_url:
            skipped += 1
            continue

        if playlist_url in queued_playlist_urls:
            skipped += 1
            continue

        queue.append({
            "key": playlist.get("name", "Playlist"),
            "url": playlist_url,
            "mode": "playlist",
            "target": playlist.get("target", ""),
            "max_items": playlist.get("max_items", 20),
        })

        queued_playlist_urls.add(playlist_url)
        added += 1

    if added:
        save_json(QUEUE_FILE, queue)

        flash(
            tr["playlists_added_to_queue"].format(
                added=added,
                skipped=skipped,
            ),
            "success",
        )
    else:
        flash(tr["all_playlists_already_queued"], "warning")

    return redirect(url_for("playlists"))   

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
        lidarr_url=LIDARR_URL,
        youtube_cookies_configured=(
            get_youtube_cookies_file() is not None
        ),
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

def get_youtube_playlist_id(url):
    if not url:
        return ""

    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        return query.get("list", [""])[0].strip()
    except (TypeError, ValueError):
        return ""


def is_youtube_mix_url(url):
    playlist_id = get_youtube_playlist_id(url)

    return playlist_id.startswith("RD")


def is_youtube_mix_watch_url(url):
    if not is_youtube_mix_url(url):
        return False

    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        return bool(query.get("v", [""])[0].strip())
    except (TypeError, ValueError):
        return False

@app.route(
    "/settings/youtube-cookies/upload",
    methods=["POST"],
)
def upload_youtube_cookies():
    consent_given = (
        request.form.get("youtube_cookies_consent")
        == "yes"
    )

    if not consent_given:
        flash(
            t()["youtube_cookies_consent_required"],
            "error",
        )
        return redirect(url_for("settings"))

    uploaded_file = request.files.get(
        "youtube_cookies_file"
    )

    if (
        uploaded_file is None
        or not uploaded_file.filename
    ):
        flash(
            t()["youtube_cookies_file_required"],
            "error",
        )
        return redirect(url_for("settings"))

    try:
        content = uploaded_file.read(
            YOUTUBE_COOKIES_MAX_SIZE + 1
        )
    except OSError as exc:
        print(
            f"[YOUTUBE COOKIES] Could not read upload: "
            f"{exc}",
            flush=True,
        )

        flash(
            t()["youtube_cookies_upload_failed"],
            "error",
        )
        return redirect(url_for("settings"))

    is_valid, error_code = (
        validate_youtube_cookies_content(content)
    )

    if not is_valid:
        translation_key = {
            "empty": "youtube_cookies_empty",
            "too_large": "youtube_cookies_too_large",
            "invalid_encoding":
                "youtube_cookies_invalid_encoding",
            "invalid_format":
                "youtube_cookies_invalid_format",
            "no_cookies":
                "youtube_cookies_no_cookies",
            "no_youtube_cookies":
                "youtube_cookies_no_youtube_cookies",
        }.get(
            error_code,
            "youtube_cookies_upload_failed",
        )

        flash(
            t()[translation_key],
            "error",
        )
        return redirect(url_for("settings"))

    if not ensure_youtube_cookies_directory():
        flash(
            t()["youtube_cookies_upload_failed"],
            "error",
        )
        return redirect(url_for("settings"))

    temporary_file = (
        YOUTUBE_COOKIES_FILE.parent
        / f".{YOUTUBE_COOKIES_FILE.name}.tmp"
    )

    try:
        temporary_file.write_bytes(content)
        temporary_file.chmod(0o600)
        temporary_file.replace(
            YOUTUBE_COOKIES_FILE
        )
        YOUTUBE_COOKIES_FILE.chmod(0o600)

    except OSError as exc:
        print(
            f"[YOUTUBE COOKIES] Could not save cookies: "
            f"{exc}",
            flush=True,
        )

        try:
            temporary_file.unlink(
                missing_ok=True
            )
        except OSError:
            pass

        flash(
            t()["youtube_cookies_upload_failed"],
            "error",
        )
        return redirect(url_for("settings"))

    print(
        "[YOUTUBE COOKIES] Cookies file saved",
        flush=True,
    )

    flash(
        t()["youtube_cookies_upload_success"],
        "success",
    )

    return redirect(url_for("settings"))

@app.route(
    "/settings/youtube-cookies/delete",
    methods=["POST"],
)
def delete_youtube_cookies():
    try:
        YOUTUBE_COOKIES_FILE.unlink(
            missing_ok=True
        )

    except OSError as exc:
        print(
            f"[YOUTUBE COOKIES] Could not delete cookies: "
            f"{exc}",
            flush=True,
        )

        flash(
            t()["youtube_cookies_delete_failed"],
            "error",
        )
        return redirect(url_for("settings"))

    print(
        "[YOUTUBE COOKIES] Cookies file removed",
        flush=True,
    )

    flash(
        t()["youtube_cookies_delete_success"],
        "success",
    )

    return redirect(url_for("settings"))   


@app.route("/album/<album_id>")
def album_details(album_id):
    album, tracks = get_album_details(album_id)

    print(
        f"[IMPORT] Requested albumId={album_id}; "
        f"track albumIds={sorted(set(str(track.get('albumId')) for track in tracks))}",
        flush=True,
    )

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

def read_audio_metadata(file_path):
    command = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_entries",
        "format_tags",
        str(file_path),
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        print(
            f"[METADATA READ] ffprobe failed for {file_path}: "
            f"{exc.stderr.strip()}",
            flush=True,
        )
        return {}
    except subprocess.TimeoutExpired:
        print(
            f"[METADATA READ] ffprobe timed out for {file_path}",
            flush=True,
        )
        return {}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(
            f"[METADATA READ] Invalid ffprobe JSON for {file_path}",
            flush=True,
        )
        return {}

    tags = data.get("format", {}).get("tags", {})

    # ffprobe kan verschillende hoofdlettervarianten teruggeven.
    normalized_tags = {
        str(key).lower(): value
        for key, value in tags.items()
    }

    return {
        "title": normalized_tags.get("title", ""),
        "artist": normalized_tags.get("artist", ""),
        "album_artist": (
            normalized_tags.get("album_artist")
            or normalized_tags.get("albumartist")
            or ""
        ),
        "album": normalized_tags.get("album", ""),
        "track": normalized_tags.get("track", ""),
        "disc": normalized_tags.get("disc", ""),
        "year": (
            normalized_tags.get("date")
            or normalized_tags.get("year")
            or ""
        ),
        "genre": normalized_tags.get("genre", ""),
        "comment": normalized_tags.get("comment", ""),
    }

def build_suggested_metadata(album, track, file_path):
    artist_value = album.get("artist")

    if isinstance(artist_value, dict):
        artist_name = artist_value.get(
            "artistName",
            "Unknown Artist",
        )
    else:
        artist_name = str(
            artist_value or "Unknown Artist"
        )

    album_title = album.get(
        "title",
        "Unknown Album",
    )

    release_year = (
        album.get("releaseDate") or ""
    )[:4]

    track_number = get_track_number(track)

    track_title = str(
        track.get("title") or file_path.stem
    ).strip()

    disc_number = (
        track.get("mediumNumber")
        or track.get("discNumber")
        or 1
    )

    if track_number is not None:
        filename = (
            f"{track_number:02d}. "
            f"{track_title}"
            f"{file_path.suffix.lower()}"
        )
    else:
        filename = file_path.name

    return {
        "artist": artist_name,
        "album_artist": artist_name,
        "album": album_title,
        "title": track_title,
        "track": track_number or "",
        "disc": disc_number,
        "year": release_year,
        "genre": "",
        "filename": filename,
    }

@app.route(
    "/album/<int:album_id>/manual-import-execute",
    methods=["POST"],
)
def manual_import_execute(album_id):
    album, tracks = get_album_details(album_id)

    if not album:
        return "Album not found", 404

    filename = request.form.get("filename", "").strip()
    replace_existing = request.form.get("replace_existing") == "1"

    existing_track_file_id_value = request.form.get(
        "existing_track_file_id",
        "",
    ).strip()

    existing_track_file_id = None

    if existing_track_file_id_value:
        try:
            existing_track_file_id = int(
                existing_track_file_id_value
            )
        except ValueError:
            flash(
                "De bestaande Lidarr-trackfile-ID is ongeldig.",
                "error",
            )

            return redirect(
                url_for(
                    "album_import_preview",
                    album_id=album_id,
                )
            )

    if not filename:
        return "Filename missing", 400

    artist_value = album.get("artist")

    if isinstance(artist_value, dict):
        artist_name = artist_value.get("artistName", "Unknown Artist")
    else:
        artist_name = str(artist_value or "Unknown Artist")
        
    album_title = album.get("title") or "Unknown Album"

    source_path = (
        DOWNLOAD_DIR
        / f"{artist_name} - {album_title}"
        / filename
    )

    if not source_path.exists():
        flash(
            f"Bronbestand niet gevonden: {source_path}",
            "error",
        )
        return redirect(
            url_for(
                "album_import_preview",
                album_id=album_id,
            )
        )

    track = find_track_for_file(source_path, tracks)

    if not track:
        flash(
            "Het bestand kon niet aan een Lidarr-track worden gekoppeld.",
            "error",
        )

        return redirect(
            url_for(
                "album_import_preview",
                album_id=album_id,
            )
        )

    existing_track_file = None

    if existing_track_file_id is not None:
        existing_track_file = find_matching_existing_track_file(
            album_id=album_id,
            track=track,
            requested_track_file_id=existing_track_file_id,
        )

        if not existing_track_file:
            flash(
                "De opgegeven bestaande Lidarr-trackfile kon niet "
                "veilig aan deze track worden gekoppeld.",
                "error",
            )

            return redirect(
                url_for(
                    "album_import_preview",
                    album_id=album_id,
                )
            )
        
    if replace_existing:
        existing_track_file_id = existing_track_file["id"]

        try:
            delete_lidarr_track_file(
                existing_track_file_id
            )

        except requests.RequestException as exc:
            print(
                f"[TRACK FILE DELETE] Failed: {exc}",
                flush=True,
            )

            flash(
                f"Het bestaande Lidarr-bestand kon niet "
                f"worden verwijderd: {exc}",
                "error",
            )

            return redirect(
                url_for(
                    "album_import_preview",
                    album_id=album_id,
                )
            )        

    print(
        f"[MANUAL IMPORT EXECUTE] "
        f"replace_existing={replace_existing}, "
        f"existing_track_file_id={existing_track_file_id}, "
        f"validated_track_file_id="
        f"{existing_track_file.get('id') if existing_track_file else None}",
        flush=True,
    )

    if replace_existing and not existing_track_file:
        flash(
            "Vervangen is aangevinkt, maar er is geen geldige "
            "bestaande Lidarr-trackfile gevonden.",
            "error",
        )

        return redirect(
            url_for(
                "album_import_preview",
                album_id=album_id,
            )
        )

    all_candidates = get_lidarr_manual_import_candidates(
        source_path.parent
    )
    if replace_existing and not existing_track_file:
        flash(
            "Vervangen is aangevinkt, maar er is geen geldige "
            "bestaande Lidarr-trackfile gevonden.",
            "error",
        )

        return redirect(
            url_for(
                "album_import_preview",
                album_id=album_id,
            )
        )

    manual_override = build_manual_import_override(
        candidates=all_candidates,
        album=album,
        track=track,
        source_path=source_path,
        replace_existing=replace_existing,
    )

    if not manual_override:
        flash(
            "Er kon geen handmatige Lidarr-import worden opgebouwd.",
            "error",
        )

        return redirect(
            url_for(
                "album_import_preview",
                album_id=album_id,
            )
        )

    try:
        updated_items = update_lidarr_manual_import(
            manual_override
        )

        command = start_lidarr_manual_import(
            updated_items=updated_items,
            import_mode="Move",
        )

        command_id = command.get("id")

        if not command_id:
            raise ValueError(
                "Lidarr returned no command ID for the manual import"
            )

        print(
            f"[MANUAL IMPORT COMMAND] Started commandId={command_id}",
            flush=True,
        )

        import_result = wait_for_lidarr_import(
            command_id=command_id,
            source_path=source_path,
        )

    except (requests.RequestException, ValueError, KeyError) as exc:
        print(
            f"[MANUAL IMPORT EXECUTE] Failed: {exc}",
            flush=True,
        )

        flash(
            f"Lidarr-import mislukt: {exc}",
            "error",
        )

        return redirect(
            url_for(
                "album_import_preview",
                album_id=album_id,
            )
        )

    translation = t()
    result_status = import_result["status"]

    if result_status == "completed":
        flash(
            translation["lidarr_import_completed"].format(
                filename=filename
            ),
            "success",
        )

    elif result_status == "failed":
        error_message = (
            import_result.get("command", {}).get("message")
            or translation["lidarr_import_failed"]
        )

        flash(
            error_message,
            "error",
        )

    elif result_status == "completed_source_remaining":
        flash(
            translation["lidarr_import_completed_source_remaining"],
            "warning",
        )

    else:
        flash(
            translation["lidarr_import_still_processing"],
            "warning",
        )

    return redirect(
        url_for(
            "album_import_preview",
            album_id=album_id,
        )
    )

def wait_for_lidarr_command(
    command_id,
    timeout_seconds=120,
    poll_interval=2,
):
    deadline = (
        time.monotonic()
        + timeout_seconds
    )

    last_command = {}

    while time.monotonic() < deadline:
        try:
            last_command = get_lidarr_command(
                command_id
            )

        except requests.RequestException as exc:
            print(
                "[LIDARR COMMAND STATUS] "
                f"Could not read command "
                f"{command_id}: {exc}",
                flush=True,
            )

            time.sleep(poll_interval)
            continue

        status = str(
            last_command.get("status", "")
        ).lower()

        print(
            "[LIDARR COMMAND STATUS] "
            f"commandId={command_id}, "
            f"status={status or 'unknown'}",
            flush=True,
        )

        if status in {
            "completed",
            "failed",
        }:
            return last_command

        time.sleep(poll_interval)

    return {
        **last_command,
        "status": "timeout",
    }    

def get_album_destination_folder(
    album,
    track_files,
):
    album_path_value = album.get("path")

    if album_path_value:
        album_path = Path(album_path_value)

        print(
            "[DIRECT IMPORT] "
            f"Album destination from album.path: "
            f"{album_path}",
            flush=True,
        )

        return album_path

    for track_file in track_files:
        track_file_path_value = track_file.get("path")

        if not track_file_path_value:
            continue

        album_path = Path(
            track_file_path_value
        ).parent

        print(
            "[DIRECT IMPORT] "
            f"Album destination from track file: "
            f"{album_path}",
            flush=True,
        )

        return album_path

    raise ValueError(
        "Could not determine Lidarr album destination folder"
    )

def move_track_to_album_folder(
    destination_folder,
    source_path,
    destination_filename,
    replace_existing=False,
):
    destination_folder = Path(
        destination_folder
    )

    if not destination_folder.exists():
        raise ValueError(
            f"Album destination folder does not exist: "
            f"{destination_folder}"
        )

    safe_filename = Path(
        destination_filename
    ).name

    if not safe_filename:
        raise ValueError(
            "Destination filename is empty"
        )

    destination_path = (
        destination_folder
        / safe_filename
    )

    if destination_path.exists():
        if not replace_existing:
            return {
                "status": "exists",
                "source_path": source_path,
                "destination_path": destination_path,
            }

        destination_path.unlink()

    print(
        "[DIRECT IMPORT] "
        f"Moving {source_path} "
        f"to {destination_path}",
        flush=True,
    )

    shutil.move(
        str(source_path),
        str(destination_path),
    )

    if source_path.exists():
        raise OSError(
            f"Source file still exists after move: "
            f"{source_path}"
        )

    if not destination_path.exists():
        raise OSError(
            f"Destination file was not created: "
            f"{destination_path}"
        )

    return {
        "status": "moved",
        "source_path": source_path,
        "destination_path": destination_path,
    }


def refresh_lidarr_artist(album):
    artist = album.get("artist") or {}
    artist_id = artist.get("id")

    if not artist_id:
        raise ValueError(
            "Album has no valid Lidarr artist ID"
        )

    payload = {
        "name": "RefreshArtist",
        "artistId": artist_id,
    }

    response = requests.post(
        f"{LIDARR_URL}/api/v1/command",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    print(
        "[DIRECT IMPORT] "
        f"RefreshArtist response: "
        f"{response.status_code}",
        flush=True,
    )

    if not response.ok:
        print(
            "[DIRECT IMPORT] "
            f"RefreshArtist body: "
            f"{response.text[:2000]}",
            flush=True,
        )

    response.raise_for_status()

    return response.json()    

@app.route(
    "/album/<int:album_id>/manual-import-batch",
    methods=["POST"],
)
def manual_import_batch(album_id):
    album, tracks = get_album_details(
        album_id
    )

    if not album:
        return "Album not found", 404

    selected_filenames = [
        Path(filename).name
        for filename in request.form.getlist(
            "filenames"
        )
        if filename
    ]

    if not selected_filenames:
        flash(
            t()["batch_import_no_files_selected"],
            "warning",
        )

        return redirect(
            url_for(
                "album_import_preview",
                album_id=album_id,
            )
        )

    artist_value = album.get("artist")

    if isinstance(artist_value, dict):
        artist_name = artist_value.get(
            "artistName",
            "Unknown Artist",
        )
    else:
        artist_name = str(
            artist_value
            or "Unknown Artist"
        )

    album_title = album.get(
        "title",
        "Unknown Album",
    )

    source_folder = (
        DOWNLOAD_DIR
        / f"{artist_name} - {album_title}"
    )

    imported = 0
    skipped = 0
    failed = 0

    track_files = get_lidarr_track_files(
        album_id
    )

    try:
        all_candidates = (
            get_lidarr_manual_import_candidates(
                source_folder
            )
        )

    except requests.RequestException as exc:
        print(
            "[BATCH IMPORT] "
            f"Could not load Lidarr candidates: "
            f"{exc}",
            flush=True,
        )

        flash(
            f"Lidarr-kandidaten konden niet "
            f"worden geladen: {exc}",
            "error",
        )

        return redirect(
            url_for(
                "album_import_preview",
                album_id=album_id,
            )
        )

    for filename in selected_filenames:
        source_path = (
            source_folder
            / filename
        )

        if not source_path.exists():
            print(
                "[BATCH IMPORT] "
                f"Source missing: {source_path}",
                flush=True,
            )

            failed += 1
            continue

        track = find_track_for_file(
            file_path=source_path,
            tracks=tracks,
            album_id=album_id,
        )

        if not track:
            print(
                "[BATCH IMPORT] "
                f"No track match: {filename}",
                flush=True,
            )

            skipped += 1
            continue

        existing_track_file = (
            find_matching_existing_track_file(
                album_id=album_id,
                track=track,
                track_files=track_files,
            )
        )

        if existing_track_file:
            print(
                "[BATCH IMPORT] "
                f"Existing Lidarr track file "
                f"skipped: {filename}, "
                f"trackFileId="
                f"{existing_track_file.get('id')}",
                flush=True,
            )

            skipped += 1
            continue

        existing_album_file = (
            find_existing_album_file(
                album=album,
                track=track,
            )
        )

        if existing_album_file:
            print(
                "[BATCH IMPORT] "
                f"Existing physical album file "
                f"skipped: {filename}, "
                f"path={existing_album_file}",
                flush=True,
            )

            skipped += 1
            continue

        current_metadata = read_audio_metadata(
            source_path
        )

        suggested_metadata = (
            build_suggested_metadata(
                album=album,
                track=track,
                file_path=source_path,
            )
        )

        if not suggested_metadata:
            print(
                "[BATCH IMPORT] "
                f"No suggested metadata: "
                f"{filename}",
                flush=True,
            )

            failed += 1
            continue

        if not metadata_matches_suggestion(
            current=current_metadata,
            suggested=suggested_metadata,
        ):
            print(
                "[BATCH IMPORT] "
                f"Metadata not ready: "
                f"{filename}",
                flush=True,
            )

            skipped += 1
            continue

        matching_candidates = (
            [
                candidate
                for candidate in all_candidates
                if Path(
                    candidate.get("path", "")
                ) == source_path
            ]
        )

        if not matching_candidates:
            print(
                "[BATCH IMPORT] "
                f"No Lidarr candidate for exact path: "
                f"{source_path}",
                flush=True,
            )

            failed += 1
            continue

        manual_override = (
            build_manual_import_override(
                candidates=matching_candidates,
                album=album,
                track=track,
                source_path=source_path,
                replace_existing=False,
            )
        )

        if not manual_override:
            print(
                "[BATCH IMPORT] "
                f"Could not build override: "
                f"{filename}",
                flush=True,
            )

            failed += 1
            continue

        try:
            updated_items = (
                update_lidarr_manual_import(
                    manual_override
                )
            )

            command = (
                start_lidarr_manual_import(
                    updated_items=updated_items,
                    import_mode="Move",
                )
            )

            command_id = command.get("id")

            if not command_id:
                raise ValueError(
                    "Lidarr returned no command ID"
                )

            print(
                "[BATCH IMPORT] "
                f"Started filename={filename}, "
                f"commandId={command_id}",
                flush=True,
            )

            result = wait_for_lidarr_import(
                command_id=command_id,
                source_path=source_path,
            )

            result_status = result.get(
                "status"
            )

            if result_status not in {
                "completed",
                "completed_source_remaining",
            }:
                failed += 1

                command_data = (
                    result.get("command")
                    or {}
                )

                print(
                    "[BATCH IMPORT] "
                    f"Import command did not complete: "
                    f"{filename}, "
                    f"status={result_status}, "
                    f"message="
                    f"{command_data.get('message')}",
                    flush=True,
                )

                continue

            refreshed_track_files = (
                get_lidarr_track_files(
                    album_id
                )
            )

            imported_track_file = (
                find_matching_existing_track_file(
                    album_id=album_id,
                    track=track,
                    track_files=(
                        refreshed_track_files
                    ),
                )
            )

            if imported_track_file:
                imported += 1
                track_files = (
                    refreshed_track_files
                )

                print(
                    "[BATCH IMPORT] "
                    f"Verified import: "
                    f"{filename}, "
                    f"trackFileId="
                    f"{imported_track_file.get('id')}, "
                    f"path="
                    f"{imported_track_file.get('path')}",
                    flush=True,
                )

            else:
                failed += 1

                print(
                    "[BATCH IMPORT] "
                    f"Command completed but no "
                    f"Lidarr trackFile was found: "
                    f"{filename}, "
                    f"sourceExists="
                    f"{source_path.exists()}",
                    flush=True,
                )

        except (
            requests.RequestException,
            ValueError,
            KeyError,
        ) as exc:
            failed += 1

            print(
                "[BATCH IMPORT] "
                f"Failed for {filename}: {exc}",
                flush=True,
            )

    translation = t()

    if imported:
        flash(
            translation[
                "batch_import_completed"
            ].format(
                imported=imported,
                skipped=skipped,
                failed=failed,
            ),
            (
                "success"
                if failed == 0
                else "warning"
            ),
        )

    else:
        flash(
            translation[
                "batch_import_no_files_imported"
            ].format(
                skipped=skipped,
                failed=failed,
            ),
            "warning",
        )

    return redirect(
        url_for(
            "album_import_preview",
            album_id=album_id,
        )
    )

def apply_custom_metadata(file_path, metadata):
    temp_path = file_path.with_name(
        f".{file_path.stem}.metadata-temp"
        f"{file_path.suffix}"
    )

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(file_path),
        "-map",
        "0",
        "-c",
        "copy",
        "-map_metadata",
        "-1",
    ]

    metadata_fields = {
        "title": metadata.get("title"),
        "artist": metadata.get("artist"),
        "album_artist": metadata.get(
            "album_artist"
        ),
        "album": metadata.get("album"),
        "track": metadata.get("track"),
        "disc": metadata.get("disc"),
        "date": metadata.get("year"),
        "genre": metadata.get("genre"),
    }

    for key, value in metadata_fields.items():
        if value not in (None, ""):
            command.extend([
                "-metadata",
                f"{key}={value}",
            ])

    command.append(str(temp_path))

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )

        temp_path.replace(file_path)

        print(
            f"[METADATA APPLY] Updated {file_path}",
            flush=True,
        )

        return True

    except subprocess.CalledProcessError as exc:
        print(
            f"[METADATA APPLY] ffmpeg failed: "
            f"{exc.stderr.strip()}",
            flush=True,
        )

    except subprocess.TimeoutExpired:
        print(
            f"[METADATA APPLY] ffmpeg timed out: "
            f"{file_path}",
            flush=True,
        )

    finally:
        if temp_path.exists():
            temp_path.unlink()

    return False

def get_tag_number(value):
    match = re.search(r"\d+", str(value or ""))
    return int(match.group()) if match else None


def metadata_matches_suggestion(current, suggested):
    if not current or not suggested:
        return False

    text_fields = (
        "artist",
        "album_artist",
        "album",
        "title",
    )

    for field in text_fields:
        current_value = normalize_match_text(
            current.get(field, "")
        )
        suggested_value = normalize_match_text(
            suggested.get(field, "")
        )

        if current_value != suggested_value:
            return False

    current_track = get_tag_number(
        current.get("track")
    )
    suggested_track = get_tag_number(
        suggested.get("track")
    )

    if current_track != suggested_track:
        return False

    current_disc = get_tag_number(
        current.get("disc")
    )
    suggested_disc = get_tag_number(
        suggested.get("disc")
    )

    if suggested_disc is not None and current_disc != suggested_disc:
        return False

    current_year = get_tag_number(
        current.get("year")
    )
    suggested_year = get_tag_number(
        suggested.get("year")
    )

    if suggested_year is not None and current_year != suggested_year:
        return False

    return True

@app.route(
    "/album/<int:album_id>/manual-import-apply",
    methods=["POST"],
)
def manual_import_apply(album_id):
    album, tracks = get_album_details(album_id)

    if not album:
        return "Album not found", 404

    artist_value = album.get("artist")

    if isinstance(artist_value, dict):
        album_artist_name = artist_value.get(
            "artistName",
            "Unknown Artist",
        )
    else:
        album_artist_name = str(
            artist_value or "Unknown Artist"
        )

    album_title = album.get(
        "title",
        "Unknown Album",
    )

    filename = Path(
        request.form["filename"]
    ).name

    source_path = (
        DOWNLOAD_DIR
        / f"{album_artist_name} - {album_title}"
        / filename
    )

    if not source_path.exists():
        flash(
            f"Audio file not found: {source_path}",
            "error",
        )

        return redirect(
            url_for(
                "album_import_preview",
                album_id=album_id,
            )
        )

    metadata = {
        "artist": request.form.get(
            "artist",
            "",
        ).strip(),
        "album_artist": request.form.get(
            "album_artist",
            "",
        ).strip(),
        "album": request.form.get(
            "album",
            "",
        ).strip(),
        "title": request.form.get(
            "title",
            "",
        ).strip(),
        "track": request.form.get(
            "track",
            "",
        ).strip(),
        "disc": request.form.get(
            "disc",
            "",
        ).strip(),
        "year": request.form.get(
            "year",
            "",
        ).strip(),
        "genre": request.form.get(
            "genre",
            "",
        ).strip(),
    }

    success = apply_custom_metadata(
        file_path=source_path,
        metadata=metadata,
    )

    if not success:
        flash(
            t()["metadata_apply_failed"],
            "error",
        )

        return redirect(
            url_for(
                "album_import_preview",
                album_id=album_id,
            )
        )

    flash(
        t()["metadata_apply_success"],
        "success",
    )

    return redirect(
        url_for(
            "album_import_preview",
            album_id=album_id,
        )
    )

def get_lidarr_track_files(album_id):
    try:
        response = requests.get(
            f"{LIDARR_URL}/api/v1/trackfile",
            headers=HEADERS,
            params={"albumId": album_id},
            timeout=30,
        )

        response.raise_for_status()

        track_files = response.json()

        if not isinstance(track_files, list):
            return []

        return track_files

    except (requests.RequestException, ValueError) as exc:
        print(
            f"[TRACK FILES] Could not load track files "
            f"for albumId={album_id}: {exc}",
            flush=True,
        )
        return []
    
def find_matching_existing_track_file(
    album_id,
    track,
    requested_track_file_id=None,
    track_files=None,
):
    if track_files is None:
        track_files = get_lidarr_track_files(
            album_id
        )

    expected_track_number = get_track_number(
        track
    )

    expected_title = normalize_match_text(
        track.get("title", "")
    )

    for track_file in track_files:
        track_file_id = track_file.get("id")

        if (
            requested_track_file_id is not None
            and str(track_file_id)
            != str(requested_track_file_id)
        ):
            continue

        track_file_path_value = track_file.get(
            "path"
        )

        if not track_file_path_value:
            continue

        track_file_path = Path(
            track_file_path_value
        )

        normalized_filename = normalize_match_text(
            track_file_path.stem
        )

        number_matches = False

        if expected_track_number is not None:
            track_number_pattern = re.compile(
                rf"(?:^|\s|-)0*{expected_track_number}(?:\s|-|$)"
            )

            number_matches = bool(
                track_number_pattern.search(
                    normalized_filename
                )
            )

        title_matches = bool(
            expected_title
            and expected_title
            in normalized_filename
        )

        if number_matches and title_matches:
            print(
                "[TRACK FILE CHECK] "
                f"Existing file matched: "
                f"{track_file_path}",
                flush=True,
            )

            return track_file

    return None

def delete_lidarr_track_file(track_file_id):
    response = requests.delete(
        f"{LIDARR_URL}/api/v1/trackfile/{track_file_id}",
        headers=HEADERS,
        params={
            "deleteFile": "true",
        },
        timeout=30,
    )

    print(
        f"[TRACK FILE DELETE] "
        f"trackFileId={track_file_id}, "
        f"status={response.status_code}",
        flush=True,
    )

    if not response.ok:
        print(
            f"[TRACK FILE DELETE] Error response: "
            f"{response.text[:2000]}",
            flush=True,
        )

    response.raise_for_status() 

@app.route("/album/<int:album_id>/import-preview")
def album_import_preview(album_id):
    print(
        "[IMPORT PREVIEW] route called",
        flush=True,
    )

    album, tracks = get_album_details(album_id)

    if not album:
        return "Album not found", 404

    artist_value = album.get("artist")

    if isinstance(artist_value, dict):
        artist_name = artist_value.get(
            "artistName",
            "Unknown Artist",
        )
    else:
        artist_name = str(
            artist_value or "Unknown Artist"
        )

    album_title = album.get(
        "title",
        "Unknown Album",
    )

    source_path = (
        DOWNLOAD_DIR
        / f"{artist_name} - {album_title}"
    )

    audio_files = get_audio_files(
        source_path
    )

    import_items = []

    track_files = get_lidarr_track_files(
        album_id
    )

    print(
        f"[TRACK FILES] "
        f"albumId={album_id}, "
        f"count={len(track_files)}",
        flush=True,
    )

    all_lidarr_candidates = []

    if audio_files:
        all_lidarr_candidates = (
            get_lidarr_manual_import_candidates(
                source_path
            )
        )

    for file_path in audio_files:
        track = find_track_for_file(
            file_path=file_path,
            tracks=tracks,
            album_id=album_id,
        )

        existing_track_file = None
        existing_album_file = None
        track_file_id = 0
        track_already_imported = False

        if track:
            existing_track_file = (
                find_matching_existing_track_file(
                    album_id=album_id,
                    track=track,
                    track_files=track_files,
                )
            )

            existing_album_file = (
                find_existing_album_file(
                    album=album,
                    track=track,
                )
            )

        if existing_track_file:
            track_file_id = (
                existing_track_file.get("id")
                or 0
            )

            print(
                "[IMPORT PREVIEW] "
                f"Existing Lidarr track file found: "
                f"{existing_track_file.get('path')}",
                flush=True,
            )

        elif existing_album_file:
            print(
                "[IMPORT PREVIEW] "
                f"Existing physical album file found: "
                f"{existing_album_file}",
                flush=True,
            )

        track_already_imported = bool(
            existing_track_file
            or existing_album_file
        )

        current_metadata = read_audio_metadata(
            file_path
        )

        suggested_metadata = None
        manual_override = None
        matching_candidates = []

        if track:
            suggested_metadata = (
                build_suggested_metadata(
                    album=album,
                    track=track,
                    file_path=file_path,
                )
            )

            if (
                existing_track_file
                or existing_album_file
            ):
                print(
                    "[IMPORT PREVIEW] "
                    f"Normal manual import disabled because "
                    f"a target file already exists: "
                    f"{file_path.name}",
                    flush=True,
                )

            else:
                matching_candidates = (
                    filter_manual_import_candidates(
                        candidates=all_lidarr_candidates,
                        album_id=album_id,
                        file_path=file_path,
                    )
                )

                if matching_candidates:
                    manual_override = (
                        matching_candidates[0]
                    )

                elif all_lidarr_candidates:
                    manual_override = (
                        build_manual_import_override(
                            candidates=all_lidarr_candidates,
                            album=album,
                            track=track,
                            source_path=file_path,
                            replace_existing=False,
                        )
                    )

        metadata_ready = (
            metadata_matches_suggestion(
                current=current_metadata,
                suggested=suggested_metadata,
            )
        )

        batch_ready = bool(
            track
            and manual_override
            and metadata_ready
            and not existing_track_file
            and not existing_album_file
        )

        print(
            "[IMPORT PREVIEW STATUS] "
            f"file={file_path.name}, "
            f"trackMatched={bool(track)}, "
            f"metadataReady={metadata_ready}, "
            f"existingTrackFile="
            f"{bool(existing_track_file)}, "
            f"existingAlbumFile="
            f"{bool(existing_album_file)}, "
            f"manualOverride={bool(manual_override)}, "
            f"batchReady={batch_ready}",
            flush=True,
        )

        import_items.append({
            "filename": file_path.name,
            "path": str(file_path),
            "track": track,
            "current": current_metadata,
            "suggested": suggested_metadata,
            "manual_override": manual_override,
            "candidate_count": len(
                matching_candidates
            ),
            "track_file_id": track_file_id,
            "track_already_imported": (
                track_already_imported
            ),
            "existing_album_file": (
                str(existing_album_file)
                if existing_album_file
                else None
            ),
            "metadata_ready": metadata_ready,
            "batch_ready": batch_ready,
        })

    batch_ready_count = sum(
        1
        for item in import_items
        if item.get("batch_ready")
    )

    print(
        f"[IMPORT PREVIEW] "
        f"batchReadyCount={batch_ready_count}",
        flush=True,
    )

    return render_template(
        "import_preview.html",
        tr=t(),
        album=album,
        artist=artist_name,
        album_title=album_title,
        source_path=str(source_path),
        source_exists=source_path.exists(),
        audio_files=audio_files,
        import_items=import_items,
        batch_ready_count=batch_ready_count,
        lidarr_url=LIDARR_URL,
    )

def trigger_lidarr_artist_scan(artist_id):
    if not artist_id:
        print("[LIDARR SCAN] No artistId available", flush=True)
        return None

    response = requests.post(
        f"{LIDARR_URL}/api/v1/command",
        headers=HEADERS,
        json={
            "name": "RefreshArtist",
            "artistId": int(artist_id),
        },
        timeout=30,
    )

    response.raise_for_status()

    command = response.json()

    print(
        f"[LIDARR SCAN] RefreshArtist started for artistId {artist_id}, "
        f"commandId={command.get('id')}",
        flush=True,
    )

    return command

def get_track_number(track):
    """Haal een bruikbaar tracknummer uit een Lidarr-trackobject."""
    value = (
        track.get("trackNumber")
        or track.get("absoluteTrackNumber")
        or track.get("mediumNumber")
    )

    if value is None:
        return None

    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def get_filename_track_number(file_path):
    """Herken bijvoorbeeld 16 uit '16. Fluffy Intro.m4a'."""
    match = re.match(r"^\s*(\d{1,3})[\s._-]+", file_path.stem)
    return int(match.group(1)) if match else None


def normalize_match_text(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()

    # Veelvoorkomende YouTube-uitbreidingen verwijderen
    noise_phrases = [
        "official soundtrack",
        "original soundtrack",
        "video game soundtrack",
        "game soundtrack",
        "ost",
        "audio",
        "official audio",
    ]

    for phrase in noise_phrases:
        value = value.replace(phrase, " ")

    value = re.sub(r"[\[\](){}\"“”'‘’]+", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


def find_track_for_file(file_path, tracks, album_id=None):
    """
    Zoek de juiste Lidarr-track voor een audiobestand.

    Eerst worden tracks beperkt tot het huidige album.
    Daarna worden tracknummer en titel samen beoordeeld.
    """
    album_tracks = tracks

    if album_id is not None:
        filtered_tracks = [
            track
            for track in tracks
            if str(track.get("albumId")) == str(album_id)
        ]

        if filtered_tracks:
            album_tracks = filtered_tracks

    filename_number = get_filename_track_number(file_path)

    filename_title = re.sub(
        r"^\s*\d{1,3}[\s._-]+",
        "",
        file_path.stem,
    ).strip()

    # Verwijder extra album-/soundtracktekst na de tracktitel
    filename_title = re.sub(
        r"\s+-\s+.*(?:soundtrack|ost).*$",
        "",
        filename_title,
        flags=re.IGNORECASE,
    ).strip()

    normalized_filename_title = normalize_match_text(filename_title)

    best_track = None
    best_score = 0.0

    for track in album_tracks:
        track_title = str(track.get("title") or "").strip()

        if not track_title:
            continue

        normalized_track_title = normalize_match_text(track_title)

        title_score = difflib.SequenceMatcher(
            None,
            normalized_filename_title,
            normalized_track_title,
        ).ratio()

        if (
            normalized_track_title
            and normalized_track_title in normalized_filename_title
        ):
            title_score = max(title_score, 0.95)

        track_number = get_track_number(track)

        number_matches = (
            filename_number is not None
            and track_number is not None
            and filename_number == track_number
        )

        # Titel is het belangrijkst.
        score = title_score

        # Alleen bonus geven voor tracknummer als de titel ook enigszins matcht.
        if number_matches and title_score >= 0.45:
            score += 0.25

        print(
            f"[TRACK MATCH] {file_path.name} -> "
            f"{track_number or '?'} - {track_title}: "
            f"title={title_score:.1%}, "
            f"number_match={number_matches}, "
            f"final={score:.1%}",
            flush=True,
        )

        if score > best_score:
            best_score = score
            best_track = track

    if best_track and best_score >= 0.70:
        print(
            f"[TRACK MATCH] Selected for {file_path.name}: "
            f"{get_track_number(best_track)} - {best_track.get('title')} "
            f"({round(best_score * 100, 1)}%)",
            flush=True,
        )
        return best_track

    print(
        f"[TRACK MATCH] No reliable match for {file_path.name}; "
        f"best score was {best_score:.1%}",
        flush=True,
    )

    return None


def normalize_audio_metadata(
    file_path,
    artist_name,
    album_title,
    release_year,
    track,
):
    """
    Schrijf Lidarr-vriendelijke metadata met ffmpeg.
    De audiostream wordt niet opnieuw gecodeerd.
    """
    track_number = get_track_number(track)
    track_title = str(track.get("title") or file_path.stem).strip()

    temp_path = file_path.with_name(
        f".{file_path.stem}.metadata-temp{file_path.suffix}"
    )

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(file_path),

        # Neem alle audio-, video- en coverstreams mee.
        "-map",
        "0",

        # Geen hercodering.
        "-c",
        "copy",

        # Verwijder eerst de bestaande YouTube-metadata.
        "-map_metadata",
        "-1",

        "-metadata",
        f"title={track_title}",
        "-metadata",
        f"artist={artist_name}",
        "-metadata",
        f"album_artist={artist_name}",
        "-metadata",
        f"album={album_title}",
    ]

    if track_number is not None:
        command.extend([
            "-metadata",
            f"track={track_number}",
        ])

    if release_year:
        command.extend([
            "-metadata",
            f"date={release_year}",
        ])

    command.append(str(temp_path))

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )

        temp_path.replace(file_path)

        print(
            f"[METADATA] Updated {file_path.name}: "
            f"{track_number or '?'} - {track_title}",
            flush=True,
        )

        return True

    except subprocess.CalledProcessError as exc:
        print(
            f"[METADATA] ffmpeg failed for {file_path}: "
            f"{exc.stderr.strip()}",
            flush=True,
        )

    except subprocess.TimeoutExpired:
        print(
            f"[METADATA] ffmpeg timed out for {file_path}",
            flush=True,
        )

    finally:
        if temp_path.exists():
            temp_path.unlink()

    return False

def get_lidarr_manual_import_candidates(folder_path):
    params = {
        "folder": str(folder_path),
        "filterExistingFiles": "true",
        "replaceExistingFiles": "false",
    }

    try:
        response = requests.get(
            f"{LIDARR_URL}/api/v1/manualimport",
            headers=HEADERS,
            params=params,
            timeout=60,
        )
        response.raise_for_status()

        candidates = response.json()

        if not isinstance(candidates, list):
            print(
                f"[MANUAL IMPORT] Unexpected response type: "
                f"{type(candidates).__name__}",
                flush=True,
            )
            return []

        print(
            f"[MANUAL IMPORT] Lidarr returned "
            f"{len(candidates)} candidate(s) for {folder_path}",
            flush=True,
        )

        return candidates

    except (requests.RequestException, ValueError, KeyError) as exc:
        print(
            f"[MANUAL IMPORT] Request failed for {folder_path}: {exc}",
            flush=True,
        )
        return []

    except ValueError as exc:
        print(
            f"[MANUAL IMPORT] Invalid JSON returned by Lidarr: {exc}",
            flush=True,
        )
        return []

def filter_manual_import_candidates(candidates, album_id, file_path=None):
    matching = []

    for candidate in candidates:
        candidate_album = candidate.get("album") or {}
        candidate_album_id = candidate_album.get("id")

        if str(candidate_album_id) != str(album_id):
            continue

        if file_path is not None:
            candidate_path = candidate.get("path")

            if candidate_path and Path(candidate_path) != Path(file_path):
                continue

        matching.append(candidate)

    print(
        f"[MANUAL IMPORT] Filtered {len(candidates)} candidate(s) "
        f"to {len(matching)} candidate(s) for albumId={album_id}",
        flush=True,
    )

    return matching
    
def build_manual_import_override(
    candidates,
    album,
    track,
    source_path,
    replace_existing=False,
):
    source_path = Path(source_path)

    source_candidate = next(
        (
            candidate
            for candidate in candidates
            if Path(
                candidate.get("path", "")
            ) == source_path
        ),
        None,
    )

    if not source_candidate:
        print(
            "[MANUAL IMPORT OVERRIDE] "
            f"No candidate found for source path: "
            f"{source_path}",
            flush=True,
        )

        return None

    releases = album.get("releases") or []

    selected_release = next(
        (
            release
            for release in releases
            if release.get("monitored")
        ),
        releases[0] if releases else None,
    )

    if not selected_release:
        print(
            "[MANUAL IMPORT OVERRIDE] "
            f"No album release available for "
            f"albumId={album.get('id')}",
            flush=True,
        )

        return None

    track_number = get_track_number(track)

    override = {
        "id": source_candidate.get("id"),
        "path": str(source_path),
        "name": (
            source_candidate.get("name")
            or source_path.name
        ),
        "size": (
            source_candidate.get("size")
            or source_path.stat().st_size
        ),
        "quality": source_candidate.get(
            "quality"
        ),
        "audioTags": source_candidate.get(
            "audioTags"
        ),
        "artist": album.get("artist"),
        "album": album,
        "albumId": album.get("id"),
        "albumReleaseId": (
            selected_release.get("id")
        ),
        "tracks": [
            {
                "id": track.get("id"),
                "title": track.get("title"),
                "trackNumber": (
                    str(track_number)
                    if track_number is not None
                    else ""
                ),
                "albumId": (
                    track.get("albumId")
                    or album.get("id")
                ),
                "artistId": (
                    track.get("artistId")
                    or (
                        album.get("artist")
                        or {}
                    ).get("id")
                ),
            }
        ],
        "replaceExistingFiles": (
            replace_existing
        ),
        "rejections": [],
    }

    print(
        "[MANUAL IMPORT OVERRIDE] "
        f"Prepared override for "
        f"path={source_path}, "
        f"albumId={album.get('id')}, "
        f"albumReleaseId="
        f"{override['albumReleaseId']}, "
        f"trackId={track.get('id')}, "
        f"replaceExistingFiles="
        f"{replace_existing}",
        flush=True,
    )

    return override

def find_existing_album_file(
    album,
    track,
):
    album_path_value = album.get("path")

    if not album_path_value:
        return None

    album_path = Path(album_path_value)

    if not album_path.exists():
        return None

    expected_track_number = get_track_number(track)
    expected_title = normalize_match_text(
        track.get("title", "")
    )

    audio_extensions = {
        ".mp3",
        ".m4a",
        ".flac",
        ".ogg",
        ".opus",
        ".wav",
    }

    for file_path in album_path.iterdir():
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in audio_extensions:
            continue

        normalized_filename = normalize_match_text(
            file_path.stem
        )

        number_matches = False

        if expected_track_number is not None:
            track_number_pattern = re.compile(
                rf"(?:^|\s)0*"
                rf"{expected_track_number}"
                rf"(?:\s|$)"
            )

            number_matches = bool(
                track_number_pattern.search(
                    normalized_filename
                )
            )

        title_matches = bool(
            expected_title
            and expected_title in normalized_filename
        )

        if number_matches and title_matches:
            print(
                "[ALBUM FILE CHECK] "
                f"Existing physical file matched: "
                f"{file_path}",
                flush=True,
            )

            return file_path

    return None

def update_lidarr_manual_import(manual_override):
    response = requests.post(
        f"{LIDARR_URL}/api/v1/manualimport",
        headers=HEADERS,
        json=[manual_override],
        timeout=30,
    )

    print(
        "[MANUAL IMPORT UPDATE] "
        f"Response status: {response.status_code}",
        flush=True,
    )

    if not response.ok:
        print(
            "[MANUAL IMPORT UPDATE] "
            f"Response body: {response.text[:2000]}",
            flush=True,
        )

    response.raise_for_status()

    response_items = response.json()

    if not isinstance(response_items, list):
        raise ValueError(
            "Lidarr returned an unexpected "
            "manual-import response"
        )

    requested_path = Path(
        manual_override.get("path", "")
    )

    updated_items = [
        item
        for item in response_items
        if Path(item.get("path", ""))
        == requested_path
    ]

    if not updated_items:
        raise ValueError(
            "Lidarr did not return the requested "
            "manual-import item"
        )

    for item in updated_items:
        # Lidarr voert na POST /manualimport opnieuw
        # automatische matching uit en kan daardoor
        # onze handmatige selectie overschrijven.
        #
        # Herstel daarom expliciet de handmatige
        # artist/album/release/track-koppeling.

        item["artist"] = manual_override.get(
            "artist"
        )

        item["album"] = manual_override.get(
            "album"
        )

        item["albumId"] = manual_override.get(
            "albumId"
        )

        item["albumReleaseId"] = (
            manual_override.get(
                "albumReleaseId"
            )
        )

        item["tracks"] = manual_override.get(
            "tracks",
            [],
        )

        item["replaceExistingFiles"] = (
            manual_override.get(
                "replaceExistingFiles",
                False,
            )
        )

        # Automatische rejections van Lidarr horen
        # niet mee naar de ManualImport command nadat
        # de gebruiker/helper de koppeling handmatig
        # heeft bevestigd.
        item["rejections"] = []

        print(
            "[MANUAL IMPORT UPDATE RESULT] "
            f"path={item.get('path')}, "
            f"albumId="
            f"{(item.get('album') or {}).get('id')}, "
            f"albumReleaseId="
            f"{item.get('albumReleaseId')}, "
            f"trackIds="
            f"{[
                track.get('id')
                for track
                in item.get('tracks', [])
            ]}, "
            f"replaceExistingFiles="
            f"{item.get('replaceExistingFiles')}, "
            f"rejections="
            f"{[
                rejection.get('reason')
                for rejection
                in item.get('rejections', [])
            ]}",
            flush=True,
        )

    return updated_items

def get_youtube_cookies_file():
    """
    Return the configured YouTube cookies file when it exists
    and contains data.

    Returns:
        Path | None: The usable cookies file, or None when no
        cookies file is available.
    """
    try:
        if not YOUTUBE_COOKIES_FILE.is_file():
            return None

        if YOUTUBE_COOKIES_FILE.stat().st_size <= 0:
            return None

        return YOUTUBE_COOKIES_FILE

    except OSError as exc:
        print(
            f"[YOUTUBE COOKIES] Could not inspect cookies file: {exc}",
            flush=True,
        )
        return None    

def ensure_youtube_cookies_directory():
    """
    Ensure that the parent directory for the YouTube cookies
    file exists.
    """
    try:
        YOUTUBE_COOKIES_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        return True

    except OSError as exc:
        print(
            f"[YOUTUBE COOKIES] Could not create cookies directory: {exc}",
            flush=True,
        )
        return False
    
def validate_youtube_cookies_content(content):
    """
    Validate an uploaded Netscape cookies.txt file.

    Returns:
        tuple[bool, str]: Validation result and error code.
    """
    if not content:
        return False, "empty"

    if len(content) > YOUTUBE_COOKIES_MAX_SIZE:
        return False, "too_large"

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return False, "invalid_encoding"

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return False, "empty"

    header_found = any(
        line.lower().startswith(
            "# netscape http cookie file"
        )
        for line in lines[:10]
    )

    if not header_found:
        return False, "invalid_format"

    cookie_lines = [
        line
        for line in lines
        if not line.startswith("#")
    ]

    if not cookie_lines:
        return False, "no_cookies"

    valid_cookie_line_found = False
    youtube_cookie_found = False

    for line in cookie_lines:
        parts = line.split("\t")

        if len(parts) != 7:
            continue

        valid_cookie_line_found = True

        domain = parts[0].lower().lstrip(".")

        if (
            domain == "youtube.com"
            or domain.endswith(".youtube.com")
        ):
            youtube_cookie_found = True

    if not valid_cookie_line_found:
        return False, "invalid_format"

    if not youtube_cookie_found:
        return False, "no_youtube_cookies"

    return True, ""    

def start_lidarr_manual_import(
    updated_items,
    import_mode="Move",
):
    files = []

    for item in updated_items:
        artist = item.get("artist") or {}
        album = item.get("album") or {}
        tracks = item.get("tracks") or []

        artist_id = (
            item.get("artistId")
            or artist.get("id")
            or 0
        )

        album_id = (
            item.get("albumId")
            or album.get("id")
            or 0
        )

        album_release_id = (
            item.get("albumReleaseId")
            or 0
        )

        track_ids = [
            track.get("id")
            for track in tracks
            if track.get("id")
        ]

        if not artist_id:
            raise ValueError(
                f"No artistId available for {item.get('path')}"
            )

        if not album_id:
            raise ValueError(
                f"No albumId available for {item.get('path')}"
            )

        if not album_release_id:
            raise ValueError(
                f"No albumReleaseId available for {item.get('path')}"
            )

        if not track_ids:
            raise ValueError(
                f"No trackIds available for {item.get('path')}"
            )

        import_file = {
            "path": item["path"],
            "artistId": int(artist_id),
            "albumId": int(album_id),
            "albumReleaseId": int(
                album_release_id
            ),
            "trackIds": [
                int(track_id)
                for track_id in track_ids
            ],
            "quality": item["quality"],
            "indexerFlags": item.get(
                "indexerFlags",
                0,
            ),
            "disableReleaseSwitching": item.get(
                "disableReleaseSwitching",
                False,
            ),
        }

        files.append(import_file)

        print(
            "[MANUAL IMPORT COMMAND ITEM] "
            f"path={import_file['path']}, "
            f"artistId={import_file['artistId']}, "
            f"albumId={import_file['albumId']}, "
            f"albumReleaseId="
            f"{import_file['albumReleaseId']}, "
            f"trackIds={import_file['trackIds']}",
            flush=True,
        )

    replace_existing = any(
        bool(item.get("replaceExistingFiles"))
        for item in updated_items
    )

    payload = {
        "name": "ManualImport",
        "files": files,
        "importMode": import_mode,
        "replaceExistingFiles": replace_existing,
    }

    response = requests.post(
        f"{LIDARR_URL}/api/v1/command",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    print(
        "[MANUAL IMPORT COMMAND] "
        f"Response status: {response.status_code}",
        flush=True,
    )

    if not response.ok:
        print(
            "[MANUAL IMPORT COMMAND] "
            f"Response body: {response.text[:2000]}",
            flush=True,
        )

    response.raise_for_status()

    return response.json()

def get_lidarr_command(command_id):
    response = requests.get(
        f"{LIDARR_URL}/api/v1/command/{command_id}",
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()
    return response.json()

def wait_for_lidarr_import(
    command_id,
    source_path,
    timeout_seconds=30,
    poll_interval=1,
):
    deadline = time.monotonic() + timeout_seconds
    last_command = {}

    while time.monotonic() < deadline:
        try:
            last_command = get_lidarr_command(
                command_id
            )

        except requests.RequestException as exc:
            print(
                f"[MANUAL IMPORT STATUS] "
                f"Could not read command "
                f"{command_id}: {exc}",
                flush=True,
            )

            time.sleep(poll_interval)
            continue

        status = str(
            last_command.get("status", "")
        ).lower()

        source_exists = source_path.exists()

        print(
            f"[MANUAL IMPORT STATUS] "
            f"commandId={command_id}, "
            f"status={status or 'unknown'}, "
            f"source_exists={source_exists}",
            flush=True,
        )

        if status == "failed":
            print(
                "[MANUAL IMPORT FAILED] "
                f"message={last_command.get('message')}, "
                f"errorMessage="
                f"{last_command.get('errorMessage')}, "
                f"exception="
                f"{last_command.get('exception')}",
                flush=True,
            )

            print(
                "[MANUAL IMPORT FAILED COMMAND] "
                f"{last_command}",
                flush=True,
            )

            return {
                "status": "failed",
                "command": last_command,
                "source_exists": source_exists,
            }

        if status == "completed":
            command_body = last_command.get("body") or {}

            print(
                "[MANUAL IMPORT COMPLETED COMMAND] "
                f"files={command_body.get('files')}, "
                f"importMode={command_body.get('importMode')}, "
                f"replaceExistingFiles="
                f"{command_body.get('replaceExistingFiles')}",
                flush=True,
            )

            return {
                "status": (
                    "completed_source_remaining"
                    if source_exists
                    else "completed"
                ),
                "command": last_command,
                "source_exists": source_exists,
            }

        # Lidarr kan het bestand al verplaatst hebben voordat
        # de commandstatus zichtbaar naar completed verandert.
        if not source_exists:
            return {
                "status": "completed",
                "command": last_command,
                "source_exists": False,
            }

        time.sleep(poll_interval)

    final_status = str(
        last_command.get("status", "")
    ).lower()

    source_exists = source_path.exists()

    return {
        "status": (
            "completed_source_remaining"
            if final_status == "completed"
            and source_exists
            else "timeout"
        ),
        "command": last_command,
        "source_exists": source_exists,
    }


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

def get_youtube_download_source(item):
    url = str(item.get("url") or "").strip()

    if not url:
        return None

    mode = str(item.get("mode") or "video").strip()

    # Opgeslagen playlists moeten altijd met hun volledige URL
    # aan yt-dlp worden doorgegeven.
    if mode == "playlist":
        return url

    # Dynamische YouTube-mixen werken alleen correct met de volledige
    # watch-URL. Een playlist?list=RD...-URL geeft vaak:
    # "The playlist does not exist".
    if is_youtube_mix_watch_url(url):
        return url

    parsed = urlparse(url)

    # Normale video-URL's kunnen rechtstreeks worden gedownload.
    if parsed.hostname in {
        "youtube.com",
        "www.youtube.com",
        "music.youtube.com",
        "youtu.be",
    } and parsed.path not in {"/results"}:
        return url

    artist = str(item.get("artist") or "").strip()
    album = str(item.get("album") or "").strip()

    key = str(item.get("key") or "").strip()
    track_title = key.rsplit(" - ", 1)[-1].strip()

    original_query = parse_qs(parsed.query).get(
        "search_query",
        [""],
    )[0].strip()

    search_parts = [
        artist,
        album,
        track_title,
        "soundtrack",
    ]

    search_query = " ".join(
        part
        for part in search_parts
        if part
    ).strip()

    if not search_query:
        search_query = original_query

    if not search_query:
        return None

    return f"ytsearch1:{search_query}"

@app.route("/download", methods=["POST"])
def download_queue():
    queue = load_json(QUEUE_FILE, [])
    processed = load_json(PROCESSED_FILE, [])
    remaining = []

    print(
        f"[DOWNLOAD QUEUE] Starting queue with {len(queue)} item(s)",
        flush=True,
    )

    for index, item in enumerate(queue, start=1):
        key = item["key"]
        mode = item.get("mode", "video")
        max_items = None
        target_name = item.get("target", "").strip() or key
        target = DOWNLOAD_DIR / target_name

        target.mkdir(
            parents=True,
            exist_ok=True,
        )

        download_source = get_youtube_download_source(item)

        if not download_source:
            print(
                f"[DOWNLOAD QUEUE] Missing URL for {key}",
                flush=True,
            )

            record = {
                "timestamp": datetime.now().isoformat(),
                "key": key,
                "mode": mode,
                "url": item.get("url", ""),
                "path": str(target),
                "returncode": -1,
                "stdout": "",
                "stderr": "Missing download URL.",
            }

            remaining.append(item)

            add_download_record(
                FAILED_FILE,
                record,
            )

            continue

        print(
            f"[DOWNLOAD QUEUE] Starting item "
            f"{index}/{len(queue)}: {key}",
            flush=True,
        )

        print(
            f"[DOWNLOAD QUEUE] Source: {download_source}",
            flush=True,
        )

        files_before = {
            path.resolve()
            for pattern in (
                "*.m4a",
                "*.mp3",
                "*.opus",
                "*.flac",
                "*.ogg",
            )
            for path in target.glob(pattern)
        }

        common_options = [
            "--socket-timeout",
            "30",
            "--retries",
            "3",
            "--fragment-retries",
            "3",
            "-f",
            "bestaudio[ext=m4a]/bestaudio/best",
            "--embed-thumbnail",
            "--add-metadata",
        ]

        if mode == "playlist":
            output_template = (
                "%(playlist_index,track_number|)02d - "
                "%(title)s.%(ext)s"
            )

            max_items = item.get("max_items")

            cmd = [
                "yt-dlp",
                "--yes-playlist",
                "--ignore-errors",
                "--no-abort-on-error",
            ]

            if max_items is not None:
                try:
                    max_items = int(max_items)
                except (TypeError, ValueError):
                    max_items = 20

                max_items = max(
                    1,
                    min(max_items, 200),
                )

                cmd.extend(
                    [
                        "--playlist-items",
                        f"1:{max_items}",
                    ]
                )

            cmd.extend(
                [
                    *common_options,
                    "-o",
                    str(target / output_template),
                ]
            )

        else:
            output_template = "%(title)s.%(ext)s"

            cmd = [
                "yt-dlp",
                "--no-playlist",
                *common_options,
                "-o",
                str(target / output_template),
            ]

        cookies_file = get_youtube_cookies_file()

        if cookies_file is not None:
            cmd.extend(
                [
                    "--cookies",
                    str(cookies_file),
                ]
            )

            print(
                f"[DOWNLOAD] Using YouTube cookies: "
                f"{cookies_file}",
                flush=True,
            )

        cmd.append(download_source)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

        except subprocess.TimeoutExpired as exc:
            stdout = (
                exc.stdout
                if isinstance(exc.stdout, str)
                else ""
            )

            stderr = (
                exc.stderr
                if isinstance(exc.stderr, str)
                else ""
            )

            print(
                f"[DOWNLOAD QUEUE] Timeout for "
                f"{index}/{len(queue)}: {key}",
                flush=True,
            )

            record = {
                "timestamp": datetime.now().isoformat(),
                "key": key,
                "mode": mode,
                "url": item.get("url", ""),
                "download_source": download_source,
                "path": str(target),
                "returncode": -1,
                "stdout": stdout[-4000:],
                "stderr": (
                    stderr[-4000:]
                    or "Download timed out after 300 seconds."
                ),
            }

            remaining.append(item)

            add_download_record(
                FAILED_FILE,
                record,
            )

            continue

        print(
            f"[DOWNLOAD QUEUE] Finished item "
            f"{index}/{len(queue)}: {key}, "
            f"returncode={result.returncode}",
            flush=True,
        )

        files_after = {
            path.resolve()
            for pattern in (
                "*.m4a",
                "*.mp3",
                "*.opus",
                "*.flac",
                "*.ogg",
            )
            for path in target.glob(pattern)
        }

        new_files = sorted(
            files_after - files_before
        )

        existing_audio_files = sorted(
            path.resolve()
            for pattern in (
                "*.m4a",
                "*.mp3",
                "*.opus",
                "*.flac",
                "*.ogg",
            )
            for path in target.glob(pattern)
            if (
                path.is_file()
                and path.stat().st_size > 0
            )
        )

        stderr = result.stderr[-4000:]

        already_downloaded = (
            "has already been downloaded" in result.stdout
            or "[download] 100%" in result.stdout
        )

        if (
            mode == "playlist"
            and result.returncode != 0
            and is_music_mix_playlist_url(download_source)
            and "The playlist does not exist" in stderr
        ):
            stderr = (
                t()["playlist_watch_url_hint"]
                + "\n\n"
                + "----------------------------------------"
                + "\n\n"
                + stderr
            )

        record = {
            "timestamp": datetime.now().isoformat(),
            "key": key,
            "mode": mode,
            "url": item.get("url", ""),
            "download_source": download_source,
            "path": str(target),
            "downloaded_files": [
                str(path)
                for path in new_files
            ],
            "available_files": [
                str(path)
                for path in existing_audio_files
            ],
            "max_items": max_items,
            "new_file_count": len(new_files),
            "available_file_count": len(
                existing_audio_files
            ),
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": stderr,
        }

        if mode == "playlist":
            # Een playlist is geslaagd zodra er bruikbare bestanden zijn
            # gedownload. yt-dlp kan returncode 1 geven wanneer enkele
            # playlist-items verwijderd, privé of niet beschikbaar zijn.
            download_succeeded = bool(
                new_files
                or (
                    already_downloaded
                    and existing_audio_files
                )
            )
        else:
            download_succeeded = bool(
                result.returncode == 0
                and existing_audio_files
            )

        if download_succeeded:
            processed.append(key)

            add_download_record(
                DOWNLOADS_FILE,
                record,
            )

            if result.returncode != 0:
                print(
                    f"[DOWNLOAD QUEUE] Playlist completed with "
                    f"{len(new_files)} new file(s), but one or more "
                    f"playlist items were unavailable",
                    flush=True,
                )
            elif new_files:
                print(
                    f"[DOWNLOAD QUEUE] Downloaded "
                    f"{len(new_files)} new file(s) for {key}",
                    flush=True,
                )
            else:
                print(
                    f"[DOWNLOAD QUEUE] No new files created for {key}, "
                    f"but {len(existing_audio_files)} audio file(s) "
                    f"are already available in staging",
                    flush=True,
                )

        else:
            remaining.append(item)

            add_download_record(
                FAILED_FILE,
                record,
            )

            print(
                f"[DOWNLOAD QUEUE] Failed or no usable "
                f"audio file available for {key}",
                flush=True,
            )

    successful_count = (
        len(queue) - len(remaining)
    )

    print(
        f"[DOWNLOAD QUEUE] Finished queue: "
        f"{successful_count} successful, "
        f"{len(remaining)} remaining",
        flush=True,
    )

    save_json(
        PROCESSED_FILE,
        sorted(set(processed)),
    )

    save_json(
        QUEUE_FILE,
        remaining,
    )

    return redirect(
        url_for("downloads")
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8999)
