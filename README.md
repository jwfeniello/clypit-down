Clyp has basically made their platform useless, but I wanted to download all of my old tracks.  
The original script from **https://github.com/0x27** (shoutout to them) was written for Python 2 and broke with newer Clyp API changes.

I used it as a basis and added some stuff and fixed it.

## Changes
- Batch downloading from a `.txt` list
- Updated to Python 3
- Extracting Clyp links from saved `.html` pages
- Optional auto-numbering
- All downloads go into `clyp_downloads/`

---


## Setup
```
pip install -r requirements.txt
```


## Usage

**Single track:**
```
    python clypdown.py https://clyp.it/abcd1234
```
**From a text file:**
```
    python clypdown.py urls.txt
```
With numbering:
```
    python clypdown.py urls.txt --number
```

**From a saved HTML profile page:**
1. Open your Clyp profile and scroll all the way down
2. Save the page as `.html`
3. Run:
       python clypdown.py page.html

This creates `clyp_song_urls.txt` and asks if you want to download them.

---

All MP3s are saved into `clyp_downloads/`.

---
