#!/usr/bin/env python3
# coding: utf-8

import re
import sys
import json
import os
import glob

from clint.textui import progress
import requests

OUTPUT_DIR = "clyp_downloads"


# ========= filename sanitizing =========

def sanitize_filename(name, max_length=150):
    """
    Make a safe filename for Windows:
    - Replace forbidden characters with '_'
    - Strip whitespace
    - Fallback to 'clyp_track' if empty
    - Optionally truncate to avoid crazy-long names
    """
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = name.strip()
    if not name:
        name = "clyp_track"
    if len(name) > max_length:
        name = name[:max_length]
    return name


# ========= downloading logic =========

def download(mp3_url, title, index=None, auto_number=False):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    safe_title = sanitize_filename(title)

    if auto_number and index is not None:
        prefix = "%03d - " % index
    else:
        prefix = ""

    filename = prefix + safe_title + ".mp3"
    full_path = os.path.join(OUTPUT_DIR, filename)

    # SKIP if the file already exists
    if os.path.exists(full_path):
        print("{i} File already exists, skipping: %s" % full_path)
        return

    print("{*} Saving file to %s" % full_path)
    try:
        r = requests.get(url=mp3_url, stream=True)
        r.raise_for_status()

        total_length = r.headers.get("content-length")

        with open(full_path, "wb") as f:
            if total_length is None:
                # no content-length: just stream
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        f.flush()
            else:
                total_length = int(total_length)
                for chunk in progress.bar(
                    r.iter_content(chunk_size=1024),
                    expected_size=(total_length // 1024) + 1,
                ):
                    if chunk:
                        f.write(chunk)
                        f.flush()
    except Exception as e:
        print(
            "{-} Something has gone horribly wrong! Please report on the github issue tracker with the following backtrace: \n%s"
            % e
        )
    print("{*} Done!")


def get_mp3_url(url):
    content_id = url.replace("https://clyp.it/", "").strip()
    try:
        r = requests.get(url="https://api.clyp.it/%s" % content_id)
    except Exception as e:
        print(
            "{-} Network error talking to Clyp API for %s:\n%s"
            % (url, e)
        )
        return None, None

    if r.status_code == 404:
        print("{-} 404 Not Found for %s, skipping." % url)
        return None, None

    try:
        r.raise_for_status()
    except Exception as e:
        print(
            "{-} HTTP error from Clyp API for %s:\n%s"
            % (url, e)
        )
        return None, None

    try:
        data = json.loads(r.text)
    except Exception as e:
        print("{-} Failed to parse JSON for %s:\n%s" % (url, e))
        return None, None

    song_title = data.get("Title", "clyp_track")
    mp3_url = data.get("Mp3Url")

    if not mp3_url:
        print("{-} No Mp3Url field for %s, skipping." % url)
        return None, None

    if data.get("Status") == "DownloadDisabled":
        print("{i} Uploader has disabled downloading. Who fucking cares.")

    print("{*} Got song title: %s" % song_title)
    print("{*} Got mp3 url: %s" % mp3_url)
    return song_title, mp3_url


# ========= HTML extraction logic =========

def extract_urls_from_html(output_file="clyp_song_urls.txt"):
    """
    Scan all .html files in the current folder and extract clyp.it URLs,
    filter out non-song links, dedupe, and save to output_file.
    """
    pattern = re.compile(r"https://clyp\.it/[a-zA-Z0-9]+")

    remove_list = {
        "https://clyp.it/notifications",
        "https://clyp.it/premium",
        "https://clyp.it/privacy",
        "https://clyp.it/subscription",
        "https://clyp.it/user",
    }

    all_urls = set()

    html_files = glob.glob("*.html")
    if not html_files:
        print("{-} No .html files found in this folder.")
        print("    Save your Clyp profile page as HTML in this folder and try again.")
        return None

    for filename in html_files:
        print("Scanning %s..." % filename)
        with open(filename, "r", encoding="utf8", errors="ignore") as f:
            data = f.read()

        urls = pattern.findall(data)
        all_urls.update(urls)

    filtered = sorted([u for u in all_urls if u not in remove_list])

    with open(output_file, "w", encoding="utf8") as f:
        for url in filtered:
            f.write(url + "\n")

    print("\nDone! Extracted %d valid URLs into %s" % (len(filtered), output_file))
    return output_file


# ========= list processing =========

def process_url_list(list_path, auto_number=False):
    """
    Read URLs from a text file (one per line) and download each.
    """
    if not os.path.exists(list_path):
        print("{-} URL list file not found: %s" % list_path)
        return

    index = 1
    with open(list_path, encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if not url:
                continue
            print("\n=== Downloading: %s ===" % url)
            title, mp3 = get_mp3_url(url)
            if not title or not mp3:
                print("!!! Skipping %s\n" % url)
                continue
            download(mp3, title, index=index, auto_number=auto_number)
            index += 1


# ========= main =========

def print_usage():
    print("Usage:")
    print("  python clypdown.py <url> [--number|-n]")
    print("  python clypdown.py urls.txt [--number|-n]")
    print("  python clypdown.py page.html [--number|-n]")
    print("")
    print("Notes:")
    print("  - If you pass a .txt file, it will download all URLs in it.")
    print("  - If you pass a .html file, it will extract Clyp links from all")
    print("    .html files in the folder into clyp_song_urls.txt, then ask")
    print("    if you want to download them.")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    auto_number = False
    non_flag_args = []

    for arg in sys.argv[1:]:
        if arg in ("--number", "-n"):
            auto_number = True
        else:
            non_flag_args.append(arg)

    if len(non_flag_args) != 1:
        print_usage()
        sys.exit(1)

    target = non_flag_args[0]

    # .txt: URL list
    if target.lower().endswith(".txt"):
        process_url_list(target, auto_number=auto_number)
        return

    # .html: extract then ask to download
    if target.lower().endswith(".html") or target.lower().endswith(".htm"):
        print("HTML mode selected.")
        print("Make sure you have:")
        print("- Opened your Clyp profile in a browser")
        print("- Scrolled all the way down until all tracks are loaded")
        print("- Saved the page as an .html file in this folder\n")

        out_file = extract_urls_from_html("clyp_song_urls.txt")
        if out_file:
            ans = input("\nDownload all extracted tracks from %s now? [y/N]: " % out_file).strip().lower()
            if ans in ("y", "yes"):
                process_url_list(out_file, auto_number=auto_number)
            else:
                print("OK, not downloading. You can run:\n  python clypdown.py %s%s" %
                      (out_file, " --number" if auto_number else ""))
        return

    # Assume single URL
    url = target
    title, mp3 = get_mp3_url(url)
    if not title or not mp3:
        print("Could not download %s" % url)
        sys.exit(1)
    download(mp3, title, index=1, auto_number=auto_number)


if __name__ == "__main__":
    main()
