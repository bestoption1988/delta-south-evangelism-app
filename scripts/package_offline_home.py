#!/usr/bin/env python3
"""Download the live diocesan homepage and package its same-origin assets for Android."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import hashlib
import mimetypes
import html as html_lib
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_URL = "https://mcn-delta-south.naijacloud.app/"
HOST = urlparse(BASE_URL).netloc
VERIFY_ONLY = "--verify-only" in sys.argv
ARGS = [arg for arg in sys.argv[1:] if arg != "--verify-only"]
DEST = Path(ARGS[0] if ARGS else "android/app/src/main/assets/offline-home")
DEST.mkdir(parents=True, exist_ok=True)

# Keep original absolute URLs in the HTML. Android's WebView interceptor maps
# same-origin requests to offline-home/<URL path>. Do not use --convert-links:
# it rewrites URLs to query-string filenames that do not match WebView request paths.
if not VERIFY_ONLY:
    cmd = [
        "wget", "--quiet", "--show-progress", "--page-requisites",
        "--no-host-directories", "--execute", "robots=off",
        "--timeout=12", "--tries=1", "--read-timeout=12", "--max-redirect=5", "--domains=" + HOST,
        "--directory-prefix=" + str(DEST), BASE_URL,
    ]
    try:
        result = subprocess.run(cmd, check=False, timeout=300)
    except subprocess.TimeoutExpired:
        raise SystemExit("Homepage download exceeded the 5-minute safety limit; use the last verified offline bundle.")
    if result.returncode not in (0, 8):
        raise SystemExit(f"Homepage download failed (wget exit {result.returncode})")

# Wget stores cache-busted files as e.g. public_home.css?v=123. WebView asks
# for /static/public_home.css (the query is not part of the asset path), so
# normalize the on-disk filename to the URL path used by MainActivity.
if not VERIFY_ONLY:
    for source in sorted(DEST.rglob("*")):
        if not source.is_file() or "?" not in source.name:
            continue
        clean_name = source.name.split("?", 1)[0]
        if not clean_name:
            continue
        target = source.with_name(clean_name)
        if target.exists():
            if target.stat().st_size == source.stat().st_size:
                source.unlink()
                continue
            # A later cache-busted copy of the same URL path is the current one.
            target.unlink()
        source.replace(target)

index = DEST / "index.html"
if not index.is_file() or index.stat().st_size < 1000:
    raise SystemExit("The live homepage HTML was not downloaded correctly.")
html = index.read_text(encoding="utf-8", errors="replace")
if "METHODIST CHURCH NIGERIA" not in html or "DELTA SOUTH DIOCESE" not in html:
    raise SystemExit("Downloaded page is not the official Delta South Diocese homepage.")

# A file:// page resolves leading-slash resources to file:///static.
# Rewrite root-relative URLs to the live same-origin host so MainActivity's
# WebView interceptor can serve those requests from assets/offline-home.
# Do not add a <base> tag: it would turn #section links into network navigations.
def absolute_same_origin(match):
    return match.group(1) + match.group(2) + BASE_URL + match.group(3)

html = re.sub(
    r"""(\b(?:src|href|poster)\s*=\s*)(["'])/(?!/)([^"']*)""",
    absolute_same_origin,
    html,
    flags=re.I,
)
def rewrite_srcset(match):
    quote = match.group(2)
    value = match.group(3)
    parts = []
    for item in value.split(","):
        bits = item.strip().split()
        if bits and bits[0].startswith("/") and not bits[0].startswith("//"):
            bits[0] = BASE_URL.rstrip("/") + bits[0]
        parts.append(" ".join(bits))
    return match.group(1) + quote + ", ".join(parts) + quote

html = re.sub(r"""(\bsrcset\s*=\s*)(["'])(.*?)\2""", rewrite_srcset, html, flags=re.I | re.S)
# Signed leadership/gallery photos often live on Supabase rather than the
# diocesan host. Copy those image bytes into the APK and point the HTML at the
# packaged file, so expired signatures or Airplane Mode cannot break photos.
external_image_urls: set[str] = set()
for attribute in re.finditer(r"""(?:src|poster|srcset)\s*=\s*(["'])(.*?)\1""", html, flags=re.I | re.S):
    for candidate in re.findall(r"https?://[^\s,]+", attribute.group(2)):
        candidate = html_lib.unescape(candidate).rstrip(")")
        parsed = urlparse(candidate)
        if parsed.netloc and parsed.netloc != HOST:
            external_image_urls.add(candidate)

packaged_external_images = 0
for image_url in sorted(external_image_urls)[:40]:
    parsed = urlparse(image_url)
    ext = Path(unquote(parsed.path)).suffix.lower()
    if ext and ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif", ".ico"}:
        continue
    try:
        request = urllib.request.Request(
            image_url,
            headers={"User-Agent": "Mozilla/5.0 MCN-Delta-South-Offline-Packager"},
        )
        with urllib.request.urlopen(request, timeout=6) as response:
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if not content_type.startswith("image/"):
                continue
            if not ext:
                ext = mimetypes.guess_extension(content_type) or ".img"
                if ext == ".jpe":
                    ext = ".jpg"
            target = DEST / "_external" / (hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:24] + ext)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(response.read())
        # Use a same-origin URL so the offline WebView asset interceptor and
        # package verifier resolve this file exactly like every other asset.
        local_url = BASE_URL.rstrip("/") + "/_external/" + target.name
        html = html.replace(image_url, local_url)
        html = html.replace(image_url.replace("&", "&amp;"), local_url)
        packaged_external_images += 1
    except Exception as error:
        print(f"Could not package external homepage image {image_url[:100]}: {error}")

print(f"Packaged {packaged_external_images} external homepage images for offline viewing.")
index.write_text(html, encoding="utf-8")

def local_path(value: str) -> str | None:
    value = (value or "").strip()
    if not value or value.startswith(("data:", "blob:", "javascript:", "#")):
        return None
    parsed = urlparse(value)
    if parsed.scheme == "file":
        prefix = "/android_asset/offline-home/"
        if parsed.path.startswith(prefix):
            return unquote(parsed.path[len(prefix):])
        return None
    if parsed.scheme and parsed.netloc and parsed.netloc != HOST:
        return None
    path = unquote(parsed.path).lstrip("/")
    return path or None

class HTMLAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths: list[str] = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "img", "source", "video", "audio", "iframe", "embed", "track"):
            p = local_path(a.get("src", ""))
            if p: self.paths.append(p)
        if tag == "video":
            p = local_path(a.get("poster", ""))
            if p: self.paths.append(p)
        if tag == "link" and any(x in a.get("rel", "").lower().split()
                                 for x in ("stylesheet", "icon", "preload", "modulepreload")):
            p = local_path(a.get("href", ""))
            if p: self.paths.append(p)
        if tag == "img" and a.get("srcset"):
            for candidate in a["srcset"].split(","):
                p = local_path(candidate.strip().split()[0])
                if p: self.paths.append(p)

parser = HTMLAssets()
parser.feed(html)
required = set(parser.paths)
# CSS url(...) and @import assets are also part of the homepage render tree.
css_pattern = re.compile(r"""url\(\s*['"]?([^)'"]+)['"]?\s*\)|@import\s+['"]([^'"]+)['"]""", re.I)
pending = [p for p in required if p.lower().endswith(".css")]
seen_css: set[str] = set()
while pending:
    css_path = pending.pop()
    if css_path in seen_css:
        continue
    seen_css.add(css_path)
    css_file = DEST / css_path
    if not css_file.is_file():
        continue
    css = css_file.read_text(encoding="utf-8", errors="replace")
    for match in css_pattern.finditer(css):
        value = match.group(1) or match.group(2) or ""
        p = local_path(value)
        if p:
            required.add(p)
            if p.lower().endswith(".css") and p not in seen_css:
                pending.append(p)

missing = sorted(p for p in required if not (DEST / p).is_file())
if missing:
    print("Required homepage assets missing from offline package:")
    for p in missing:
        print(" - " + p)
    raise SystemExit(1)

file_count = sum(1 for p in DEST.rglob("*") if p.is_file())
total_bytes = sum(p.stat().st_size for p in DEST.rglob("*") if p.is_file())
if file_count < 5 or total_bytes < 100_000:
    raise SystemExit(f"Homepage package is suspiciously small: {file_count} files, {total_bytes} bytes")
print(f"Verified official homepage: {file_count} files, {total_bytes:,} bytes")
print(f"Verified {len(required)} same-origin HTML/CSS resources.")
