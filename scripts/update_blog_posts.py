#!/usr/bin/env python3
"""Fetch latest blog posts from RSS feed and update README.md"""

import re
import xml.etree.ElementTree as ET
from urllib.request import urlopen

FEED_URL = "https://ryanmroth.com/feed.xml"
README_PATH = "README.md"
MAX_POSTS = 5


def fetch_posts(feed_url: str, max_posts: int) -> list[dict]:
    """Fetch posts from RSS feed."""
    with urlopen(feed_url) as response:
        tree = ET.parse(response)

    root = tree.getroot()
    result = []

    # Handle both RSS and Atom feeds
    if root.tag == "rss":
        items = root.findall(".//item")
        for item in items[:max_posts]:
            title = item.find("title").text
            link = item.find("link").text
            result.append({"title": title, "url": link})
    else:
        # Atom feed
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//atom:entry", ns)
        for item in items[:max_posts]:
            title = item.find("atom:title", ns).text
            link = item.find("atom:link", ns).get("href")
            result.append({"title": title, "url": link})

    return result


def update_readme(post_list: list[dict]) -> bool:
    """Update README.md with posts between markers. Returns True if changed."""
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Build post list
    post_lines = [f"- [{p['title']}]({p['url']})" for p in post_list]
    new_content = "\n".join(post_lines)

    # Replace content between markers
    pattern = r"(<!-- BLOG-POST-LIST:START -->).*?(<!-- BLOG-POST-LIST:END -->)"
    replacement = f"\\1\n{new_content}\n\\2"

    updated = re.sub(pattern, replacement, content, flags=re.DOTALL)

    if updated == content:
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    return True


if __name__ == "__main__":
    posts = fetch_posts(FEED_URL, MAX_POSTS)
    changed = update_readme(posts)
    print(
        f"Found {len(posts)} posts, README {'updated' if changed else 'unchanged'}")
