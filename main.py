"""
Cleanup Application for files in linux.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

HOME = Path.home()
REVIEW = HOME / "CleanupReview"
MANIFEST = REVIEW / "manifest.json"

CATEGORIES = ("temporary","old_logs","duplicates","pdfs","screenshots")

SKIP_DIRS = {
    ".cache",".local",".config",".mozilla",".var",".thunderbird",".steam",".wine","node_modules",".git","__pycache__","CleanupReview"
}

TEMP_SUFFIXES = {
    ".tmp",".temp",".part",".partial",".swp",".swo",".bak",".old",".cache"
}

REPORTED_ONLY = {
    "cache (~/.cache)": HOME / ".cache",
    "trash": HOME / ".local" / "share" / "Trash",
}

LOG_SUFFIXES = {".log"}
SCREENSHOT_WORDS = {"screenshot","screen shot","スクリーンショット"}
SCREENSHOT_DIRS = {"screenshots","screen-shots","screen_shots"}

def human(n):
    for unit in ["B","KB","MB","GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n/=1024
    return f"{n:.1f} TB"

def file_hash(path):
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None
    
def dir_size(folder):
    total = 0
    for dirpath, _, files in os.walk(folder, onerror=lambda e:None):
        for name in files:
            try:
                p = Path(dirpath) / name
                if not p.is_symlink():
                    total += p.stat().st_size
            except OSError:
                pass
    return total

def load_manifest():
    if not MANIFEST.exists():
        return {"version":1,"items":[]}
    try:
        data = json.load(MANIFEST.read_text(encoding="utf-8"))
        if data.get("version") != 1 or not isinstance(data.get("items"), list):
            raise ValueError("Unsupported Manifest Format")
        return data
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            f"Cannot read {MANIFEST}: {exc}\n"
            "Do not overwrite the manifest; inspect or backup first"
        ) from exc

def save_manifest(data):
    REVIEW.mkdir(parents=True, exist_ok = True)
    temporary_manifest = MANIFEST.with_suffix(".json.tmp")
    temporary_manifest.write_text(
        json.dump(data, indent=2, ensure_ascii = False), encoding ="utf-8"
    ) 
    os.replace(temporary_manifest, MANIFEST)

def is_inside(path, directory):
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except (ValueError, OSError):
        return False

def classify(path):
    suffix = path.suffix.lower()
    name = path.name.lower()
    parent_names = {part.lower() for part in path.parts}

    if suffix in TEMP_SUFFIXES or name.startswith("~$"):
        return "temp"

    if suffix in LOG_SUFFIXES:
        return "old_ logs"

    if suffix == ".pdf":
        return "pdf"

    if suffix in {".png",".jpg",".jpeg",".webp"}:
        if any(word in name for word in SCREENSHOT_WORDS):
            return "screenshots"

        if parent_names & SCREENSHOT_DIRS:
            return "screenshots"

    return None

def scan_files():
    for root, dirs, filenames in os.walk(
        HOME, topdown=True,followlinks=False
    ):
        root_path = Path(root)

        dirs[:] = [
            dirname for dirname in dirs
            if dirname not in SKIP_DIRS
            and not (root_path/ dirname).is_symlink()
            and not is_inside(root_path /dirname, REVIEW)
        ]

        for filename in filenames:
            path = root / filename

            try:
                if path.is_symlink() or not path.is_file():
                    continue

                stat = path.stat()
                yield path, stat.st_size, stat.st_mtime

            except OSError:
                continue
            
    
def scan():
    print("Scanning files...")
    candidates = []
    hash_groups = defaultdict(list)

    for path, size, modified in scan_files():
        category = classify(path)
        if category:
            category.append({
                "path":str(path),
                "category":category,
                "size":size,
                "modified":modified
            })

        if size <= 100 * 1024 * 1024 and size > 0:
            digest = file_hash(path)
            if digest:
                hash_groups[digest].append(modified, size, path)

    duplicate_groups = [
        group for group in hash_groups.values() if len(group) > 1
    ]

    duplicated_paths = {
        str(path)
        for group in duplicate_groups
        for path, _, _ in group[1:]
    }

    existing = {item["path"] for item in candidates}
    for group in duplicate_groups:
        for path, size, modified in group[1:]:
            if str(path) not in existing:
                candidates.append({
                    "path":str(path),
                    "category":"duplicates",
                    "size":size,
                    "modified":modified
                })

    candidates.sort(key = lambda item: (item["category"], item["path"]))
    print(f"\nFound {len(candidates)} in review candidates")
    totals = defaultdict(lambda: [0,0])
    for item in candidates:
        totals[item["category"]][0] += 1
        totals[item["category"]][0] += item["size"]
    
    for category in CATEGORIES:
        count,size = totals[category]
        if count:
            print(f"  {category:14} {count:5} files   {human(size)}")

    print("\nReported-only locations:")
    for label, folder in REPORTED_ONLY.items():
        try:
            if folder.exists():
                print(f"  {label:10} {folder}   (not moved)")
            else:
                print(f"  {label:10} not present")
        except OSError:
            print(f"  {label:10} could not be checked")
    if not candidates:
        return
    