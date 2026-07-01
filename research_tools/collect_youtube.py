import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research" / "youtube-transcripts"

CHANNELS = {
    "matt-diggity": {
        "expert": "Matt Diggity",
        "channel_id": "UCP5A5lVxaT7cO_LehpxjTZg",
        "source": "Official YouTube channel RSS and public YouTube caption tracks",
        "limit": 5,
    },
    "nathan-gotch": {
        "expert": "Nathan Gotch",
        "channel_id": "UCNEsahyXxNJvYNsMhru-UzQ",
        "source": "Official YouTube channel RSS and public YouTube caption tracks",
        "limit": 5,
    },
    "aleyda-solis": {
        "expert": "Aleyda Solis",
        "channel_id": "UCnLvZaTgyA-rMQQO14KX4Yw",
        "source": "Official YouTube channel RSS and public YouTube caption tracks",
        "limit": 0,
    },
    "gael-breton": {
        "expert": "Gael Breton",
        "channel_id": "UCTvgSAxisCh58hjzlMdED0A",
        "source": "Official Authority Hacker YouTube channel RSS and public YouTube caption tracks",
        "limit": 3,
    },
    "mark-webster": {
        "expert": "Mark Webster",
        "channel_id": "UCTvgSAxisCh58hjzlMdED0A",
        "source": "Official Authority Hacker YouTube channel RSS and public YouTube caption tracks",
        "limit": 3,
    },
    "mike-king": {
        "expert": "Mike King",
        "channel_id": "UCbMMGk3z1nUfOS7gqOu5rAw",
        "source": "Official iPullRank YouTube channel RSS and public YouTube caption tracks",
        "limit": 0,
    },
    "bernard-huang": {
        "expert": "Bernard Huang",
        "channel_id": "UCi24ZhSPbVbZrXMar_HS1eA",
        "source": "Official Clearscope YouTube channel RSS and public YouTube caption tracks",
        "limit": 5,
    },
    "cyrus-shepard": {
        "expert": "Cyrus Shepard",
        "channel_id": "UCI3n2oEaEbx0-eny-rmEA9w",
        "source": "Official Cyrus Shepard YouTube channel RSS and public YouTube caption tracks",
        "limit": 0,
    },
}

SEARCHES = {
    "aleyda-solis": {
        "expert": "Aleyda Solis",
        "source": "YouTube public search results and public YouTube caption tracks",
        "required_terms": ["aleyda"],
        "queries": [
            "Aleyda Solis AI search SEO 2025",
            "Aleyda Solis AI SEO",
        ],
        "limit": 5,
    },
    "koray-tugberk-gubur": {
        "expert": "Koray Tugberk Gubur",
        "source": "YouTube public search results and public YouTube caption tracks",
        "required_terms": ["koray"],
        "queries": [
            "Koray Tugberk Gubur topical authority semantic SEO",
            "Koray Tugberk Gubur AI SEO",
        ],
        "limit": 5,
    },
    "lily-ray": {
        "expert": "Lily Ray",
        "source": "YouTube public search results and public YouTube caption tracks",
        "required_terms": ["lily"],
        "queries": [
            "Lily Ray AI SEO Google Search",
            "Lily Ray SEO conference AI",
        ],
        "limit": 5,
    },
    "mike-king": {
        "expert": "Mike King",
        "source": "YouTube public search results and public YouTube caption tracks",
        "required_terms": ["mike"],
        "queries": [
            "Mike King AI SEO",
            "Mike King Google AI Overviews SEO",
        ],
        "limit": 5,
    },
    "cyrus-shepard": {
        "expert": "Cyrus Shepard",
        "source": "YouTube public search results and public YouTube caption tracks",
        "required_terms": ["cyrus"],
        "queries": [
            "Cyrus Shepard AI SEO",
            "Cyrus Shepard Google AI search",
        ],
        "limit": 5,
    },
}


def get(url):
    response = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 research-bot"},
    )
    response.raise_for_status()
    return response.text


def get_bytes(url):
    response = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 research-bot"},
    )
    response.raise_for_status()
    return response.content


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:80] or "untitled"


def rss_items(channel_id):
    xml_text = get(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}")
    root = ET.fromstring(xml_text)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    items = []
    for entry in root.findall("atom:entry", ns):
        video_id = entry.findtext("yt:videoId", namespaces=ns)
        title = entry.findtext("atom:title", namespaces=ns)
        published = entry.findtext("atom:published", namespaces=ns)
        author = entry.findtext("atom:author/atom:name", namespaces=ns)
        items.append(
            {
                "video_id": video_id,
                "title": title,
                "published": (published or "")[:10],
                "author": author,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
        )
    return items


def search_videos(query, limit):
    text = get(f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}")
    ids = []
    for match in re.finditer(r'"videoId":"([^"]+)".{0,600}?"title":\{"runs":\[\{"text":"([^"]+)"', text):
        video_id, title = match.groups()
        if video_id not in [item["video_id"] for item in ids]:
            ids.append({"video_id": video_id, "title": title})
        if len(ids) >= limit:
            break
    return ids


def page_metadata(video_id, fallback_title=None):
    text = get(f"https://www.youtube.com/watch?v={video_id}")
    title = fallback_title
    published = ""
    author = ""
    title_match = re.search(r'<meta name="title" content="([^"]+)"', text)
    if title_match:
        title = html.unescape(title_match.group(1))
    date_match = re.search(r'"publishDate":"([^"]+)"', text) or re.search(r'"datePublished":"([^"]+)"', text)
    if date_match:
        published = date_match.group(1)[:10]
    author_match = re.search(r'<link itemprop="name" content="([^"]+)"', text)
    if author_match:
        author = html.unescape(author_match.group(1))
    return text, {
        "video_id": video_id,
        "title": title or video_id,
        "published": published,
        "author": author,
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }


def extract_caption_url(page_text):
    match = re.search(r'"captionTracks":(\[.*?\])', page_text)
    if not match:
        return None
    raw = match.group(1)
    raw = raw.replace(r"\/", "/")
    try:
        tracks = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not tracks:
        return None
    english = [
        track
        for track in tracks
        if track.get("languageCode", "").startswith("en")
    ]
    track = english[0] if english else tracks[0]
    return unquote(track["baseUrl"]) + "&fmt=json3"


def innertube_caption_url(video_id, page_text):
    key_match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', page_text)
    client_match = re.search(r'"INNERTUBE_CONTEXT_CLIENT_VERSION":"([^"]+)"', page_text)
    if not key_match or not client_match:
        return None
    key = key_match.group(1)
    clients = [
        {
            "clientName": "IOS",
            "clientVersion": "20.10.4",
            "deviceMake": "Apple",
            "deviceModel": "iPhone16,2",
            "osName": "iOS",
            "osVersion": "18.3.2",
        },
        {
            "clientName": "ANDROID",
            "clientVersion": "20.10.38",
            "androidSdkVersion": 35,
            "osName": "Android",
            "osVersion": "15",
        },
        {"clientName": "WEB", "clientVersion": client_match.group(1)},
    ]
    for client in clients:
        payload = {
            "context": {"client": client},
            "videoId": video_id,
            "contentCheckOk": True,
            "racyCheckOk": True,
        }
        response = requests.post(
            f"https://www.youtube.com/youtubei/v1/player?key={key}",
            headers={
                "User-Agent": "Mozilla/5.0 research-bot",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=30,
        )
        if response.status_code != 200:
            continue
        data = response.json()
        tracks = (
            data.get("captions", {})
            .get("playerCaptionsTracklistRenderer", {})
            .get("captionTracks", [])
        )
        english = [track for track in tracks if track.get("languageCode", "").startswith("en")]
        if english or tracks:
            return (english[0] if english else tracks[0])["baseUrl"] + "&fmt=json3"
    return None


def caption_text(caption_url):
    text = get(caption_url)
    try:
        data = json.loads(text)
        lines = []
        for event in data.get("events", []):
            parts = event.get("segs") or []
            line = "".join(part.get("utf8", "") for part in parts).strip()
            if line:
                lines.append(line)
        return "\n".join(lines)
    except json.JSONDecodeError:
        pass

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return ""
    lines = []
    for node in root.findall(".//text"):
        line = "".join(node.itertext()).strip()
        if line:
            lines.append(html.unescape(line))
    return "\n".join(lines)


def transcript_for_video(video_id):
    page_text, meta = page_metadata(video_id)
    caption_url = extract_caption_url(page_text)
    transcript = caption_text(caption_url) if caption_url else ""
    if not transcript:
        caption_url = innertube_caption_url(video_id, page_text)
        transcript = caption_text(caption_url) if caption_url else ""
    return meta, transcript


def write_markdown(expert_slug, item, transcript):
    folder = OUT / expert_slug
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{item['published'] or 'undated'}-{slugify(item['title'])}.md"
    path = folder / filename
    original = transcript or "Transcript unavailable from public YouTube caption tracks at collection time."
    path.write_text(
        "\n".join(
            [
                f"Title: {item['title']}",
                f"Author: {item.get('author') or item['expert']}",
                f"Published: {item.get('published') or 'Unknown'}",
                f"URL: {item['url']}",
                f"Source: {item.get('source') or 'YouTube'}",
                f"Collection Method: {item.get('collection_method') or 'Official YouTube RSS + YouTube caption/Innertube extraction'}",
                "",
                "## Metadata",
                f"- Expert: {item['expert']}",
                f"- Video ID: {item.get('video_id') or 'Unknown'}",
                f"- Channel/Author: {item.get('author') or 'Unknown'}",
                f"- Captions Available: {'Yes' if transcript else 'No'}",
                "",
                "## Summary",
                f"This official or expert-relevant YouTube resource was collected for {item['expert']}'s perspective on AI-assisted SEO, content production, search quality, topical authority, or organic growth workflows.",
                "",
                "## Key Takeaways",
                "- Review the transcript for concrete workflow details, strategic claims, examples, prompts, tools, and cautions.",
                "- Use this source as raw evidence for the later AI SEO playbook rather than as a final recommendation.",
                "",
                "## Original Content",
                original,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def collect_channels():
    written = []
    for slug, config in CHANNELS.items():
        for item in rss_items(config["channel_id"])[: config["limit"]]:
            item["expert"] = config["expert"]
            item["source"] = config["source"]
            item["collection_method"] = "Official YouTube RSS feed for metadata; public YouTube timedtext caption endpoint with Innertube player metadata fallback for transcript"
            meta, transcript = transcript_for_video(item["video_id"])
            item.update({key: value for key, value in meta.items() if value})
            written.append(write_markdown(slug, item, transcript))
    return written


def collect_searches():
    written = []
    for slug, config in SEARCHES.items():
        seen = set()
        for query in config["queries"]:
            for found in search_videos(query, config["limit"]):
                if found["video_id"] in seen:
                    continue
                page_text, meta = page_metadata(found["video_id"], found["title"])
                haystack = f"{meta.get('title', '')} {meta.get('author', '')}".lower()
                if not all(term in haystack for term in config.get("required_terms", [])):
                    continue
                seen.add(found["video_id"])
                caption_url = extract_caption_url(page_text)
                transcript = ""
                if caption_url:
                    transcript = caption_text(caption_url)
                if not transcript:
                    caption_url = innertube_caption_url(found["video_id"], page_text)
                    transcript = caption_text(caption_url) if caption_url else ""
                meta["expert"] = config["expert"]
                meta["source"] = config["source"]
                meta["collection_method"] = "YouTube public search results for discovery; public YouTube timedtext caption endpoint with Innertube player metadata fallback for transcript"
                written.append(write_markdown(slug, meta, transcript))
                if len(seen) >= config["limit"]:
                    break
            if len(seen) >= config["limit"]:
                break
    return written


if __name__ == "__main__":
    for folder in OUT.glob("*"):
        if folder.is_dir():
            for file_path in folder.glob("*.md"):
                file_path.unlink()
    paths = collect_channels()
    paths.extend(collect_searches())
    print(f"Wrote {len(paths)} YouTube transcript files")
    for path in paths:
        print(path.relative_to(ROOT))
