"""Convert all logo files in public/logos/ to JPG format.

Renames {domain}.{ext} → {domain}.jpg for all non-JPG files.
Removes the original after successful conversion.
Deletes logos.json manifest (no longer needed).
"""

from pathlib import Path
from PIL import Image

LOGOS_DIR = Path(__file__).resolve().parent.parent / "public" / "logos"
MANIFEST = Path(__file__).resolve().parent.parent / "public" / "logos.json"


def convert_to_jpg(src: Path) -> bool:
    dst = src.with_suffix(".jpg")
    if dst.exists() and src != dst:
        # Already have a JPG version — just delete the old one
        src.unlink()
        return True
    try:
        img = Image.open(src)
        # Convert to RGB (JPG doesn't support alpha/palette modes)
        if img.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(dst, "JPEG", quality=85)
        if src != dst:
            src.unlink()
        return True
    except Exception as e:
        print(f"  FAILED: {src.name} — {e}")
        return False


def main():
    files = sorted(LOGOS_DIR.iterdir())
    converted = 0
    skipped = 0
    failed = 0

    for f in files:
        if not f.is_file():
            continue
        if f.suffix.lower() == ".jpg":
            skipped += 1
            continue
        if convert_to_jpg(f):
            converted += 1
        else:
            failed += 1

    print(f"Done: {converted} converted, {skipped} already JPG, {failed} failed")
    print(f"Total JPG files: {len(list(LOGOS_DIR.glob('*.jpg')))}")

    if MANIFEST.exists():
        MANIFEST.unlink()
        print("Deleted logos.json manifest")


if __name__ == "__main__":
    main()
