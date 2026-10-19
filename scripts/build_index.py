
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote
import json
import re
import html

ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = ROOT / "notes"
OUTPUT_FILE = ROOT / "search-index.json"

SUBJECT_NAMES = {
    "pharmacognosy": "فارماکوگنوزی",
    "toxicology": "سم‌شناسی",
    "pharmacology": "فارماکولوژی",
    "biochemistry": "بیوشیمی",
    "bioinformatics": "بیوانفورماتیک",
    "pharmaceutics": "داروسازی صنعتی",
}

class LessonParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.text_parts = []
        self.in_title = False
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        if tag in ("script", "style", "noscript"):
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in ("script", "style", "noscript"):
            self.skip_depth = max(0, self.skip_depth - 1)

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return

        if self.in_title:
            self.title_parts.append(text)

        if not self.skip_depth:
            self.text_parts.append(text)


def clean_text(text):
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def display_name(folder):
    return SUBJECT_NAMES.get(
        folder.lower(),
        folder.replace("-", " ").replace("_", " ").title()
    )


def main():
    lessons = []

    if not NOTES_DIR.exists():
        NOTES_DIR.mkdir(parents=True)

    for file_path in sorted(NOTES_DIR.rglob("*.html")):
        # Skip subject landing pages.
        if file_path.name.lower() == "index.html":
            continue

        relative_path = file_path.relative_to(ROOT).as_posix()
        parts = file_path.relative_to(NOTES_DIR).parts

        if len(parts) < 2:
            print(f"Skipped file outside a subject folder: {relative_path}")
            continue

        subject_folder = parts[0]
        subject = display_name(subject_folder)

        try:
            source = file_path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            print(f"Could not read {relative_path}: {error}")
            continue

        parser = LessonParser()
        try:
            parser.feed(source)
        except Exception as error:
            print(f"Could not parse {relative_path}: {error}")
            continue

        title = clean_text(" ".join(parser.title_parts))

        if not title:
            title = file_path.stem.replace("-", " ").replace("_", " ")

        text = clean_text(" ".join(parser.text_parts))
        url = quote(relative_path, safe="/")

        lessons.append({
            "title": title,
            "subject": subject,
            "path": url,
            "text": text,
            "filename": file_path.name,
        })

    OUTPUT_FILE.write_text(
        json.dumps(lessons, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Indexed {len(lessons)} lessons.")
    print(f"Created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
