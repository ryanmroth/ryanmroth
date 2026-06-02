#!/usr/bin/env python3
"""Fetch latest blog posts from an RSS/Atom feed and update README.md."""
import re
import xml.etree.ElementTree as ET
from urllib.request import urlopen

FEED_URL = "https://ryanmroth.com/feed.xml"
README_PATH = "README.md"
MAX_POSTS = 5
TIMEOUT = 30  # seconds; avoids a hung feed stalling the runner

START = "<!-- BLOG-POST-LIST:START -->"
END = "<!-- BLOG-POST-LIST:END -->"


def _text(el) -> str | None:
    """Stripped text of an element, or None if absent/empty.

    The feed's generator ('RSS for Node') pads every CDATA field with
    surrounding spaces, so stripping is required, not cosmetic.
    """
    if el is None or el.text is None:
        return None
    return el.text.strip() or None


def fetch_posts(feed_url: str, max_posts: int) -> list[dict]:
    """Fetch posts from an RSS or Atom feed."""
    with urlopen(feed_url, timeout=TIMEOUT) as response:
        root = ET.parse(response).getroot()

    posts: list[dict] = []

    if root.tag == "rss":
        for item in root.findall(".//item")[:max_posts]:
            title = _text(item.find("title"))
            link = _text(item.find("link"))
            if title and link:
                posts.append({"title": title, "url": link})
    else:
        # Atom fallback (not used by the current feed, kept for resilience).
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//atom:entry", ns)[:max_posts]:
            title = _text(entry.find("atom:title", ns))
            # Prefer the alternate link. NOTE: don't use `a or b` on Elements —
            # an Element with no children is falsy in ElementTree, so a found
            # <link> would wrongly evaluate False. Check `is None` explicitly.
            link_el = entry.find("atom:link[@rel='alternate']", ns)
            if link_el is None:
                link_el = entry.find("atom:link", ns)
            href = link_el.get("href") if link_el is not None else None
            link = href.strip() if href else None
            if title and link:
                posts.append({"title": title, "url": link})

    return posts


def update_readme(post_list: list[dict]) -> bool:
    """Update README.md between markers. Returns True if changed.

    Raises SystemExit if the markers are missing, so a malformed README
    fails the job loudly instead of silently committing nothing.
    """
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        rf"({re.escape(START)}).*?({re.escape(END)})", re.DOTALL
    )
    if not pattern.search(content):
        raise SystemExit(
            f"Markers not found in {README_PATH}: expected "
            f"'{START}' ... '{END}'"
        )

    block = "\n".join(f"- [{p['title']}]({p['url']})" for p in post_list)
    # Function replacement: treats `block` literally, so a title containing
    # a backslash or \<digit> can't be misread as a group reference.
    updated = pattern.sub(lambda m: f"{m.group(1)}\n{block}\n{m.group(2)}", content)

    if updated == content:
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)
    return True


if __name__ == "__main__":
    posts = fetch_posts(FEED_URL, MAX_POSTS)
    if not posts:
        raise SystemExit("No posts parsed from feed; aborting.")
    changed = update_readme(posts)
    print(f"Found {len(posts)} posts, README {'updated' if changed else 'unchanged'}")
