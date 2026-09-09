import os
import time
import json
from pathlib import Path
from ytmusicapi import YTMusic
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai

CATEGORIES_FILE = Path("data/categories.json")
TRACKS_FILE = Path("data/categorized_tracks.jsonl")

# 1. Setup YTMusic authentication (Environment Secret vs. Local File)
ytm_secret = os.getenv("YTM_BROWSER_JSON")
local_auth_file = Path("browser.json")

if ytm_secret:
    # Initialize directly from the secret in memory
    ytm = YTMusic(ytm_secret)
elif local_auth_file.exists():
    # Initialize from local browser.json file
    ytm = YTMusic(str(local_auth_file))
else:
    raise FileNotFoundError(
        "YouTube Music authentication missing. "
        "Set the YTM_BROWSER_JSON environment variable or ensure 'browser.json' exists locally."
    )
# 2. Load Categories
with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
    categories_data = json.load(f)["categories"]

category_ids = [c["id"] for c in categories_data]
category_map = {c["id"]: c["name"] for c in categories_data}

taxonomy_prompt = "\n".join([
    f"- ID: '{c['id']}' | Name: {c['name']} | Rationale: {c.get('rationale', c.get('theme', ''))}"
    for c in categories_data
])

# 3. Load Existing Categorized Tracks
existing_tracks = []
existing_keys = set()

if TRACKS_FILE.exists():
    with open(TRACKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                record = json.loads(line.strip())
                existing_tracks.append(record)
                existing_keys.add(f"{record.get('title')}-{record.get('artist')}")

print(f"Loaded {len(existing_tracks)} existing tracks.")

# 4. Fetch Recent Liked Songs from YTMusic
print("Fetching recent liked tracks from YouTube Music...")
liked_songs = ytm.get_liked_songs(limit=100).get("tracks", [])

new_tracks = []
for song in liked_songs:
    title = song.get("title")
    artists = ", ".join([a["name"] for a in song.get("artists", []) if "name" in a])
    key = f"{title}-{artists}"

    if key not in existing_keys:
        new_track = {
            "id": song.get("videoId"),
            "title": title,
            "artist": artists,
            "album": song.get("album", {}).get("name") if song.get("album") else None,
            "category_id": None
        }
        new_tracks.append(new_track)
        existing_keys.add(key)

print(f"Found {len(new_tracks)} new tracks to process.")

# 5. Categorize Uncategorized/New Tracks via Gemini 3.5 Flash-Lite
tracks_to_classify = new_tracks + [t for t in existing_tracks if not t.get("category_id")]

if tracks_to_classify:
    print(f"Categorizing {len(tracks_to_classify)} tracks using Gemini 3.5 Flash-Lite...")
    client = genai.Client()

    class TrackClassification(BaseModel):
        index: int = Field(description="The index of the track in the provided input list.")
        category_id: Optional[str] = Field(default=None)

    class BatchClassificationResult(BaseModel):
        classifications: List[TrackClassification]

    BATCH_SIZE = 50
    for i in range(0, len(tracks_to_classify), BATCH_SIZE):
        batch = tracks_to_classify[i:i + BATCH_SIZE]
        batch_list = [
            {"index": idx, "title": t.get("title"), "artist": t.get("artist")}
            for idx, t in enumerate(batch)
        ]

        prompt = f"""
You are an expert music curator. Categorize each track into AT MOST ONE category ID:

TAXONOMY:
{taxonomy_prompt}

VALID CATEGORY IDs:
{category_ids}

TRACKS:
{json.dumps(batch_list, indent=2)}

Assign category_id from the valid list above, or return null if uncertain.
"""
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': BatchClassificationResult,
                }
            )
            result = json.loads(response.text)
            cls_map = {item['index']: item.get('category_id') for item in result.get('classifications', [])}

            for idx, track in enumerate(batch):
                cat = cls_map.get(idx)
                track["category_id"] = cat if cat in category_ids else None

        except Exception as e:
            print(f"Batch failed starting index {i}: {e}")

        time.sleep(2)

    # Combine updated existing tracks and new tracks
    all_tracks = existing_tracks + new_tracks
else:
    all_tracks = existing_tracks

# 6. Save Updated JSONL
TRACKS_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(TRACKS_FILE, "w", encoding="utf-8") as f:
    for track in all_tracks:
        f.write(json.dumps(track, ensure_ascii=False) + "\n")

print(f"Saved total {len(all_tracks)} tracks to {TRACKS_FILE}.")

# 7. Update YouTube Music Playlists
print("Syncing playlists with YouTube Music...")

# Fetch all playlists from your authenticated library
user_playlists = ytm.get_library_playlists(limit=100)
playlist_map = {p["title"]: p["playlistId"] for p in user_playlists}

# Group videoIds by category
categorized_groups = {}
for track in all_tracks:
    cat_id = track.get("category_id")
    video_id = track.get("id")
    if cat_id and video_id:
        categorized_groups.setdefault(cat_id, []).append(video_id)

for cat_id, video_ids in categorized_groups.items():
    playlist_name = category_map.get(cat_id, cat_id)
    
    # Get or create playlist
    if playlist_name not in playlist_map:
        print(f"Creating {playlist_name}...")
        playlist_id = ytm.create_playlist(
            title=playlist_name, 
            description=f"Auto playlist for {playlist_name}"
        )
        playlist_map[playlist_name] = playlist_id
    else:
        print(f"Playlist {playlist_name} already existing")
        playlist_id = playlist_map[playlist_name]

    # If it's a brand new playlist, we know it's empty. Otherwise, fetch existing tracks.
    existing_vids = set()
    try:
        playlist_data = ytm.get_playlist(playlist_id, limit=1000)
        playlist_items = playlist_data.get("tracks", [])
        existing_vids = {item.get("videoId") or item.get("id") for item in playlist_items if item}
    except Exception as e:
        print(f"Warning: Could not fetch tracks for existing playlist '{playlist_name}': {e}")
            
    new_vids = [vid for vid in video_ids if vid not in existing_vids]
    if new_vids:
        # Chunk additions into batches of 50 to prevent API rejection/timeouts on large lists
        BATCH_SIZE = 50
        added_count = 0
        for i in range(0, len(new_vids), BATCH_SIZE):
            chunk = new_vids[i:i + BATCH_SIZE]
            try:
                ytm.add_playlist_items(playlist_id, chunk)
                added_count += len(chunk)
                time.sleep(1)
            except Exception as e:
                print(f"Error adding batch to '{playlist_name}': {e}")
        print(f"Added {added_count} new tracks to playlist '{playlist_name}'.")

print("Pipeline execution complete.")
