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
import pathlib as Path

HOME = Path.home()
REVIEW = HOME / "CleanupReview"
MANIFEST = REVIEW / "manifest.json"

TIER = {
    "leftovers":"safe",
    "old_logs":"safe",
    "screenshots":"review",
    "pdfs":"review",
    "duplicates":"review"
}

REPORTED_ONLY = {
    "cache (~/.cache)": HOME / ".cache",
    "trash": HOME / ".local" / "share" / "Trash",
}

def human(n):
    for unit in ["B","KB","MB","GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n/=1024
    return f"{n:.1f} TB"