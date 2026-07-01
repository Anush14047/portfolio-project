import re
import sys

import requests


def fetch(url):
    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 research-bot"},
    )
    response.raise_for_status()
    return response.text


def channel_id_for_handle(handle):
    url = handle if handle.startswith("http") else f"https://www.youtube.com/@{handle}/videos"
    text = fetch(url)
    match = (
        re.search(r'"channelId":"(UC[^"]+)"', text)
        or re.search(r'"externalId":"(UC[^"]+)"', text)
        or re.search(r"channel_id=(UC[^&\"']+)", text)
        or re.search(r'"browseId":"(UC[^"]+)"', text)
    )
    return match.group(1) if match else None


if __name__ == "__main__":
    for handle in sys.argv[1:]:
        try:
            print(f"{handle}\t{channel_id_for_handle(handle)}")
        except Exception as exc:
            print(f"{handle}\tERROR: {exc}")
