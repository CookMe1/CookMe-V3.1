#!/usr/bin/env python3
"""Shrink recipe photos to web size and keep the full-size originals safe.
  python3 scripts/compress_images.py            # compresses frontend/public/recipe-images in place
Before changing anything, each full-size file is copied to originals/recipe-images/ (never overwritten), so you can upload the
originals to cloud storage later. Files already small are skipped, so it is safe to re-run after more photos are added.
Result: longest side 1000 px, JPEG quality 80 -> usually 60-150 KB instead of 500 KB - 5 MB."""
import shutil, sys
from pathlib import Path
from PIL import Image, ImageOps
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT/"frontend"/"public"/"recipe-images"; KEEP = ROOT/"originals"/"recipe-images"
MAX_SIDE, QUALITY, SKIP_UNDER = 1000, 80, 150_000

def main():
    KEEP.mkdir(parents=True, exist_ok=True)
    done = skipped = 0; before = after = 0
    for f in sorted(SRC.glob("*.jpg")):
        size = f.stat().st_size
        if size < SKIP_UNDER:
            skipped += 1; continue
        orig = KEEP/f.name
        if not orig.exists():
            shutil.copy2(f, orig)
        im = ImageOps.exif_transpose(Image.open(orig)).convert("RGB")      # always shrink from the original
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        im.save(f, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        before += size; after += f.stat().st_size; done += 1
    print(f"compressed {done}, already small {skipped}. {before/1e6:.0f} MB -> {after/1e6:.0f} MB. Originals kept in {KEEP}")

if __name__ == "__main__":
    main()
