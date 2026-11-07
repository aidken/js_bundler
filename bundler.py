
"""
bundle.py — Inline JS Bundler for SharePoint SPAs
==================================================
Reads HTML files from src/, replaces <script src="..."> tags with inlined
<script> blocks using local library files from libs/, and writes
self-contained HTML to dist/.

Usage:
    python bundle.py              # bundle all .html in src/
    python bundle.py report.html  # bundle a single file

Libraries referenced via CDN URLs are resolved using a mapping (see
LIB_MAP below). Local relative paths (e.g. libs/chart.js) are resolved
directly from the filesystem.

Requirements: Python 3 (no external packages)
"""

import os
import re
import sys
import shutil

# ── Configuration ──────────────────────────────────────────────────────

SRC_DIR  = "src"
DIST_DIR = "dist"
LIBS_DIR = "libs"

# Map CDN URL patterns to local filenames in LIBS_DIR.
# Add entries here when you adopt a new library.
LIB_MAP = {
    "chart.js":      "chart.umd.min.js",
    "apexcharts":    "apexcharts.min.js",
    # "d3":          "d3.min.js",
    # "lodash":      "lodash.min.js",
}

# ── Core logic ─────────────────────────────────────────────────────────

SCRIPT_TAG_RE = re.compile(
    r'<script\s+[^>]*src\s*=\s*["\']([^"\']+)["\'][^>]*>\s*</script>',
    re.IGNORECASE,
)


def resolve_lib(src_attr: str) -> str | None:
    """Return the local file path for a <script src="..."> value, or None."""
    # 1. Check CDN mapping
    for keyword, local_file in LIB_MAP.items():
        if keyword in src_attr:
            path = os.path.join(LIBS_DIR, local_file)
            if os.path.isfile(path):
                return path
            print(f"  WARNING: mapped file not found: {path}")
            return None

    # 2. Check as a relative path (e.g. libs/chart.js)
    if not src_attr.startswith(("http://", "https://", "//")):
        if os.path.isfile(src_attr):
            return src_attr
        path = os.path.join(LIBS_DIR, os.path.basename(src_attr))
        if os.path.isfile(path):
            return path

    return None


def inline_scripts(html: str, filename: str) -> str:
    """Replace external <script src> tags with inlined <script> blocks."""
    def replacer(match):
        full_tag = match.group(0)
        src_attr = match.group(1)
        local_path = resolve_lib(src_attr)

        if local_path is None:
            print(f"  SKIP (no local file): {src_attr}")
            return full_tag  # leave the original tag untouched

        with open(local_path, "r", encoding="utf-8") as f:
            js_content = f.read()

        size_kb = len(js_content) / 1024
        print(f"  INLINE: {src_attr} → {local_path} ({size_kb:.0f} KB)")
        return f"<script>/* {os.path.basename(local_path)} */\n{js_content}\n</script>"

    return SCRIPT_TAG_RE.sub(replacer, html)


def bundle_file(filename: str):
    """Bundle a single HTML file from SRC_DIR to DIST_DIR."""
    src_path  = os.path.join(SRC_DIR, filename)
    dist_path = os.path.join(DIST_DIR, filename)

    if not os.path.isfile(src_path):
        print(f"ERROR: {src_path} not found")
        return False

    print(f"\nBundling: {filename}")

    with open(src_path, "r", encoding="utf-8") as f:
        html = f.read()

    result = inline_scripts(html, filename)

    os.makedirs(DIST_DIR, exist_ok=True)
    with open(dist_path, "w", encoding="utf-8") as f:
        f.write(result)

    src_size  = os.path.getsize(src_path) / 1024
    dist_size = os.path.getsize(dist_path) / 1024
    print(f"  Output: {dist_path} ({src_size:.0f} KB → {dist_size:.0f} KB)")
    return True


def main():
    if not os.path.isdir(SRC_DIR):
        print(f"ERROR: source directory '{SRC_DIR}' not found")
        sys.exit(1)

    if not os.path.isdir(LIBS_DIR):
        print(f"ERROR: library directory '{LIBS_DIR}' not found")
        sys.exit(1)

    # Determine which files to bundle
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = sorted(f for f in os.listdir(SRC_DIR) if f.lower().endswith(".html"))

    if not files:
        print(f"No .html files found in {SRC_DIR}/")
        sys.exit(1)

    print(f"Libraries directory: {LIBS_DIR}/")
    print(f"Available libs: {', '.join(sorted(os.listdir(LIBS_DIR)))}")

    success = 0
    for f in files:
        if bundle_file(f):
            success += 1

    print(f"\nDone: {success}/{len(files)} file(s) bundled → {DIST_DIR}/")


if __name__ == "__main__":
    main()
