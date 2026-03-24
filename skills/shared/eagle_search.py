#!/usr/bin/env python3
"""Eagle library search utility for the /figure skill.

Usage:
  python3 eagle_search.py search --tags "tag1,tag2" [--match any|all]
  python3 eagle_search.py list-tags
  python3 eagle_search.py read --id IMAGE_ID
"""

import argparse
import json
import glob
import os
import sys

EAGLE_LIBRARY = "/Users/zylen/Library/CloudStorage/Dropbox/Apps/Eagle/research.library"


def load_all_images(library_path):
    """Load all non-deleted image metadata from the Eagle library."""
    images = []
    pattern = os.path.join(library_path, "images", "*.info", "metadata.json")
    for meta_path in sorted(glob.glob(pattern)):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("isDeleted", False):
            continue
        folder = os.path.dirname(meta_path)
        filename = f"{meta['name']}.{meta['ext']}"
        meta["image_path"] = os.path.join(folder, filename)
        meta["thumbnail_path"] = os.path.join(
            folder, f"{meta['name']}_thumbnail.{meta['ext']}"
        )
        images.append(meta)
    return images


def cmd_search(args):
    """Search images by tags."""
    library = args.library or EAGLE_LIBRARY
    if not os.path.isdir(library):
        print(f"ERROR: Eagle library not found at {library}", file=sys.stderr)
        print("=== VERIFY: FAIL ===")
        sys.exit(1)

    images = load_all_images(library)
    query_tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    match_mode = args.match  # "any" or "all"

    results = []
    for img in images:
        img_tags = img.get("tags", [])
        if not img_tags:
            continue
        img_tags_lower = [t.lower() for t in img_tags]
        query_lower = [t.lower() for t in query_tags]

        if match_mode == "all":
            matched = all(
                any(q in it for it in img_tags_lower) for q in query_lower
            )
        else:  # "any"
            matched = any(
                any(q in it for it in img_tags_lower) for q in query_lower
            )

        if matched:
            results.append(
                {
                    "id": img["id"],
                    "name": img["name"],
                    "tags": img.get("tags", []),
                    "annotation": img.get("annotation", "").strip(),
                    "ext": img["ext"],
                    "width": img.get("width", 0),
                    "height": img.get("height", 0),
                    "image_path": img["image_path"],
                    "thumbnail_path": img["thumbnail_path"],
                    "palettes": img.get("palettes", []),
                }
            )

    # Sort: more tag matches first, then by recency (mtime desc)
    def sort_key(r):
        tag_hits = sum(
            1
            for q in query_tags
            for t in r["tags"]
            if q.lower() in t.lower()
        )
        return (-tag_hits, -images[0].get("mtime", 0))

    results.sort(key=sort_key)

    # Collect all available tags for reference
    all_tags = set()
    for img in images:
        all_tags.update(img.get("tags", []))

    output = {
        "query": query_tags,
        "match_mode": match_mode,
        "results": results,
        "total": len(results),
        "available_tags": sorted(all_tags),
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))

    if results:
        print(f"\n=== VERIFY: PASS ({len(results)} results) ===")
    else:
        print(f"\n=== VERIFY: FAIL (0 results) ===")
        print(f"Available tags: {', '.join(sorted(all_tags))}")
        sys.exit(1)


def cmd_list_tags(args):
    """List all tags with usage counts."""
    library = args.library or EAGLE_LIBRARY
    if not os.path.isdir(library):
        print(f"ERROR: Eagle library not found at {library}", file=sys.stderr)
        print("=== VERIFY: FAIL ===")
        sys.exit(1)

    images = load_all_images(library)
    tag_counts = {}
    for img in images:
        for tag in img.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    print("=== EAGLE TAG LIST ===")
    print(f"{'Tag':<30} {'Count':>5}")
    print("-" * 37)
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        print(f"{tag:<30} {count:>5}")
    print(f"\nTotal images: {len(images)}")
    print(f"Total unique tags: {len(tag_counts)}")
    print(f"\n=== VERIFY: PASS ===")


def cmd_read(args):
    """Read full metadata for a specific image."""
    library = args.library or EAGLE_LIBRARY
    images = load_all_images(library)

    target = None
    for img in images:
        if img["id"] == args.id:
            target = img
            break

    if not target:
        print(f"ERROR: Image ID '{args.id}' not found", file=sys.stderr)
        print("=== VERIFY: FAIL ===")
        sys.exit(1)

    print(json.dumps(target, ensure_ascii=False, indent=2))
    print(f"\n=== VERIFY: PASS ===")


def main():
    parser = argparse.ArgumentParser(description="Eagle library search utility")
    parser.add_argument(
        "--library", default=None, help="Eagle library path (default: hardcoded)"
    )
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="Search by tags")
    p_search.add_argument("--tags", required=True, help="Comma-separated tags")
    p_search.add_argument(
        "--match", default="any", choices=["any", "all"], help="Match mode"
    )

    sub.add_parser("list-tags", help="List all tags")

    p_read = sub.add_parser("read", help="Read image metadata by ID")
    p_read.add_argument("--id", required=True, help="Image ID")

    args = parser.parse_args()
    if args.command == "search":
        cmd_search(args)
    elif args.command == "list-tags":
        cmd_list_tags(args)
    elif args.command == "read":
        cmd_read(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
