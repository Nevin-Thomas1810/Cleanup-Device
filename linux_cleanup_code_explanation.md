# Linux Cleanup Application --- Complete Code Explanation

This guide explains the reconstructed `cleanup.py` application from top
to bottom: imports, initial variables, dictionaries, sets, tuples,
functions, control flow, and limitations.

> This explanation corresponds to the reconstructed version created in
> this conversation. It is a learning guide, not a guarantee that the
> application is production-safe. Test with disposable files or backups
> before using it on important data.

------------------------------------------------------------------------

# 1. What the application does

The application scans the user's home directory and identifies potential
cleanup candidates:

-   Temporary files
-   Log files
-   PDFs
-   Screenshots
-   Duplicate files

It displays candidates and lets the user choose which ones to move into
`~/CleanupReview`. A JSON manifest records where each file came from so
it can later be restored or permanently deleted.

The cache and Trash directories are reported separately; they are not
automatically moved.

## Overall workflow

1.  Initialize paths and configuration.
2.  Walk through the home directory.
3.  Classify files.
4.  Calculate hashes to find duplicates.
5.  Display a report and ask which files to stage.
6.  Move selected files into `CleanupReview`.
7.  Record their original and new paths in `manifest.json`.
8.  Let the user review, restore, or purge staged files.

------------------------------------------------------------------------

# 2. Imports

``` python
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
```

  -----------------------------------------------------------------------
  Import                              Purpose
  ----------------------------------- -----------------------------------
  `argparse`                          Reads commands such as `scan`,
                                      `review`, `restore`, and `purge`
                                      from the terminal.

  `hashlib`                           Calculates SHA-256 hashes for
                                      duplicate detection.

  `json`                              Reads and writes the manifest file.

  `os`                                Provides directory walking and
                                      filesystem operations.

  `shutil`                            Moves files.

  `sys`                               Writes errors to standard error and
                                      exits with a status code.

  `time`                              Records when a file was staged.

  `defaultdict`                       A dictionary that automatically
                                      creates a default value for missing
                                      keys.

  `Path`                              Provides convenient filesystem path
                                      operations.
  -----------------------------------------------------------------------

## Why `pathlib.Path`?

``` python
from pathlib import Path

HOME = Path.home()
```

`Path.home()` returns the current user's home directory, such as
`/home/nevin`.

Using `Path` makes it easy to join paths:

``` python
HOME / "Documents"
```

This produces `/home/nevin/Documents` on a typical Linux system. The `/`
operator is overloaded by `Path` to join path components.

------------------------------------------------------------------------

# 3. Initial variables and configuration

``` python
HOME = Path.home()
REVIEW = HOME / "CleanupReview"
MANIFEST = REVIEW / "manifest.json"
```

These are global variables because they are defined outside functions.

-   `HOME`: the user's home directory.
-   `REVIEW`: the folder where selected files are staged for review.
-   `MANIFEST`: the JSON file that records information about staged
    files.

For a user whose home directory is `/home/nevin`, these resolve to:

``` text
/home/nevin
/home/nevin/CleanupReview
/home/nevin/CleanupReview/manifest.json
```

Defining these paths once avoids repeating hard-coded paths throughout
the program.

## CATEGORIES tuple

``` python
CATEGORIES = (
    "temporary",
    "old_logs",
    "screenshots",
    "pdfs",
    "duplicates"
)
```

A tuple is an ordered collection that cannot be modified after creation.

It is suitable for a fixed list of categories. You can read values using
indexes, such as `CATEGORIES[0]`, but you cannot assign a new value to
an existing position.

## SKIP_DIRS set

``` python
SKIP_DIRS = {
    ".cache", ".local", ".config", ".mozilla",
    ".var", ".thunderbird", ".steam", ".wine",
    "node_modules", ".git", "__pycache__",
    "CleanupReview",
}
```

A set stores unique elements and supports fast membership checks.

The scanner excludes these directory names. This is a conservative
choice: application data, configuration, development dependencies, and
the review folder should not be swept up by the normal scan.

A set is useful for checks such as:

``` python
if dirname in SKIP_DIRS:
    ...
```

Set order is not guaranteed, and duplicate elements are automatically
removed.

## File-detection sets and tuple

``` python
TEMP_SUFFIXES = {
    ".tmp", ".temp", ".part", ".partial", ".swp",
    ".swo", ".bak", ".old", ".cache",
}

LOG_SUFFIXES = {".log"}

SCREENSHOT_WORDS = (
    "screenshot",
    "screen shot",
    "スクリーンショット"
)

SCREENSHOT_DIRS = {
    "screenshots",
    "screen-shots",
    "screen_shots"
}
```

-   `TEMP_SUFFIXES`: filename extensions or suffixes often associated
    with temporary or backup files.
-   `LOG_SUFFIXES`: extensions used to recognize log files.
-   `SCREENSHOT_WORDS`: text patterns that may appear in screenshot
    filenames.
-   `SCREENSHOT_DIRS`: common names for screenshot directories.

These are heuristics. They do not prove that a file is unnecessary. A
`.bak`, `.log`, or `.tmp` file may still be important.

## REPORTED_ONLY dictionary

``` python
REPORTED_ONLY = {
    "cache": HOME / ".cache",
    "trash": HOME / ".local" / "share" / "Trash",
}
```

A dictionary stores key-value pairs.

Here, the keys are labels and the values are filesystem paths:

-   `"cache"` points to the user's cache directory.
-   `"trash"` points to the user's Trash directory.

The application reports whether these locations exist, but does not
automatically move their contents.

------------------------------------------------------------------------

# 4. Utility functions

## `human(size)`

``` python
def human(size):
    size = float(size)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"

        size /= 1024
```

**Purpose:** Converts a byte count into a readable size.

The loop checks units from bytes through terabytes. If the current value
is at least 1024, it divides by 1024 and tries the next unit.

`:.1f` in the f-string formats the number to one decimal place.

Example:

``` python
print(human(1024))       # 1.0 KB
print(human(1048576))    # 1.0 MB
print(human(1073741824)) # 1.0 GB
```

Strictly, 1024 bytes is 1 KiB, but this application uses the familiar
`KB` label.

## `file_hash(path)`

``` python
def file_hash(path):
    digest = hashlib.sha256()

    try:
        with path.open("rb") as stream:
            for chunk in iter(
                lambda: stream.read(1024 * 1024), b""
            ):
                digest.update(chunk)

        return digest.hexdigest()

    except OSError:
        return None
```

**Purpose:** Calculates a SHA-256 fingerprint of a file's contents.

-   `hashlib.sha256()` creates a SHA-256 hashing object.
-   `path.open("rb")` opens the file in binary-read mode. Binary mode is
    needed for PDFs, images, and other non-text files.
-   `with` ensures the file is closed when the block ends.
-   `stream.read(1024 * 1024)` reads up to 1 MiB at a time.
-   `iter(function, sentinel)` repeatedly calls the function until it
    returns the sentinel, here `b""`, which means end-of-file.
-   `digest.update(chunk)` adds each chunk to the running hash.
-   `hexdigest()` returns the final digest as hexadecimal text.
-   `except OSError` handles unreadable or inaccessible files by
    returning `None`.

Reading in chunks avoids loading a whole large file into memory.

Files with identical contents should have identical SHA-256 hashes.
Hashes are an excellent duplicate-detection tool, though a
high-assurance tool can additionally compare file contents after
matching hashes.

## `dir_size(folder)`

The original code supplied by the user included this function:

``` python
def dir_size(folder):
    total = 0
    for dirpath, _, files in os.walk(folder, onerror=lambda e: None):
        for name in files:
            try:
                p = Path(dirpath) / name
                if not p.is_symlink():
                    total += p.stat().st_size
            except OSError:
                pass
    return total
```

**Purpose:** Calculates the total size of regular, non-symlink files
under a directory.

-   `total = 0` initializes the running total.
-   `os.walk()` recursively visits directories.
-   `_` is a conventional variable name for a value that the code does
    not need (the directory list).
-   `Path(dirpath) / name` constructs a path to each file.
-   `is_symlink()` excludes symbolic links.
-   `stat().st_size` retrieves the file's size in bytes.
-   `except OSError: pass` skips files that cannot be inspected.
-   `return total` returns the accumulated byte count.

**Important:** This function appeared in the original snippet but was
not included in the reconstructed 456-line `cleanup.py` file.

------------------------------------------------------------------------

# 5. Manifest and path-safety functions

## `load_manifest()`

``` python
def load_manifest():
    if not MANIFEST.exists():
        return {"version": 1, "items": []}

    try:
        data = json.loads(
            MANIFEST.read_text(encoding="utf-8")
        )

        if data.get("version") != 1 or not isinstance(data.get("items"), list):
            raise ValueError("Unsupported manifest format")

        return data

    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            f"Cannot read {MANIFEST}: {exc}\n"
            "Do not overwrite the manifest; inspect or back it up first."
        ) from exc
```

**Purpose:** Loads the manifest from disk into Python.

If the manifest does not exist, it returns a new empty structure:

``` python
{"version": 1, "items": []}
```

`read_text()` reads the JSON file as text. `json.loads()` converts JSON
text into Python objects such as dictionaries and lists.

The function checks that:

1.  The manifest version is supported.
2.  `items` is a list.

`.get()` retrieves a dictionary value without raising `KeyError` when
the key is absent. `isinstance(value, list)` checks the value's type.

The exception handler catches filesystem errors, invalid JSON, and
invalid manifest structure. It raises a clearer `RuntimeError` rather
than silently replacing potentially important recovery information.

## `save_manifest(data)`

``` python
def save_manifest(data):
    REVIEW.mkdir(parents=True, exist_ok=True)

    temporary_manifest = MANIFEST.with_suffix(".json.tmp")

    temporary_manifest.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    os.replace(temporary_manifest, MANIFEST)
```

**Purpose:** Writes the manifest to disk.

-   `mkdir(parents=True, exist_ok=True)` creates the review directory
    and any missing parent directories. It does not fail just because
    the directory already exists.
-   `with_suffix()` changes the filename suffix to create a temporary
    manifest path.
-   `json.dumps()` converts Python objects into JSON text.
-   `indent=2` makes the JSON readable.
-   `ensure_ascii=False` keeps Unicode characters readable.
-   `os.replace()` replaces the old manifest with the newly written
    temporary file.

Writing a temporary file and then replacing the old one helps avoid
leaving a partially written manifest if the program is interrupted
during the write. For stronger durability, a production application can
also flush and synchronize the file and its directory.

## `is_inside(path, directory)`

``` python
def is_inside(path, directory):
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except (ValueError, OSError):
        return False
```

**Purpose:** Checks whether one path is inside another directory.

-   `resolve()` makes a path absolute and resolves symlinks where
    possible.
-   `relative_to()` succeeds when the path is inside the specified
    directory.
-   If it is outside, `relative_to()` raises `ValueError`.
-   Filesystem problems can raise `OSError`.

The function returns `True` or `False`.

This is used as a path-boundary check before staging, restoring, and
deleting files. It is a useful safeguard, but path checks alone do not
eliminate every symlink or race-condition risk.

------------------------------------------------------------------------

# 6. File classification

## `classify(path)`

``` python
def classify(path):
    suffix = path.suffix.lower()
    name = path.name.lower()
    parent_names = {part.lower() for part in path.parts}

    if suffix in TEMP_SUFFIXES or name.startswith("~$"):
        return "temporary"

    if suffix in LOG_SUFFIXES:
        return "old_logs"

    if suffix == ".pdf":
        return "pdfs"

    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        if any(word in name for word in SCREENSHOT_WORDS):
            return "screenshots"

        if parent_names & SCREENSHOT_DIRS:
            return "screenshots"

    return None
```

**Purpose:** Examines a file path and returns a category, without moving
the file.

-   `path.suffix` returns the extension, such as `.PDF`.
-   `.lower()` normalizes the extension and filename to lowercase.
-   `path.name` returns the filename.
-   `path.parts` splits the path into components.
-   The set comprehension creates a lowercase set of path components.

The conditions then classify files:

1.  A known temporary suffix or a filename beginning with `~$` becomes
    `"temporary"`.
2.  A `.log` file becomes `"old_logs"`.
3.  A `.pdf` file becomes `"pdfs"`.
4.  A PNG, JPG, JPEG, or WEBP image becomes `"screenshots"` if its name
    contains a screenshot word or one of its path components matches a
    known screenshot directory.

`any()` returns `True` if at least one item in its iterable is true.

The `&` operator between sets calculates their intersection. If
`parent_names & SCREENSHOT_DIRS` is non-empty, the path contains a
recognized screenshot directory name.

If no rule matches, the function returns `None`.

**Limitation:** This is filename-based heuristic detection, not
intelligent content recognition. It can miss screenshots with unrelated
names and can classify ordinary images in a screenshot folder as
screenshots.

------------------------------------------------------------------------

# 7. Scanning the home directory

## `scan_files()`

``` python
def scan_files():
    for root, dirs, filenames in os.walk(
        HOME, topdown=True, followlinks=False
    ):
        root_path = Path(root)

        dirs[:] = [
            dirname for dirname in dirs
            if dirname not in SKIP_DIRS
            and not (root_path / dirname).is_symlink()
            and not is_inside(root_path / dirname, REVIEW)
        ]

        for filename in filenames:
            path = root_path / filename

            try:
                if path.is_symlink() or not path.is_file():
                    continue

                stat = path.stat()
                yield path, stat.st_size, stat.st_mtime

            except OSError:
                continue
```

**Purpose:** Recursively visits the home directory and yields
information about eligible files.

`os.walk()` produces three values:

-   `root`: the current directory.
-   `dirs`: directories inside the current directory.
-   `filenames`: files inside the current directory.

`topdown=True` means parent directories are processed before
subdirectories. `followlinks=False` prevents walking through directory
symlinks.

The `dirs[:] = [...]` statement modifies the existing directory list in
place. This matters because `os.walk()` uses that list to decide which
subdirectories to visit next.

The list comprehension keeps only directories that:

-   Are not named in `SKIP_DIRS`.
-   Are not symlinks.
-   Are not inside the review directory.

The inner loop processes filenames.

-   `root_path / filename` creates a complete path.
-   `is_symlink()` excludes symbolic links.
-   `is_file()` checks that the path is a regular file.
-   `stat()` retrieves filesystem metadata.
-   `st_size` is the file size in bytes.
-   `st_mtime` is the last modification timestamp.

### Why `yield`?

`yield` makes `scan_files()` a generator. Instead of building a huge
list of all file information, it produces one result at a time.

The caller can unpack each result:

``` python
for path, size, modified in scan_files():
    ...
```

`continue` skips the current file if it is unsuitable or inaccessible.

------------------------------------------------------------------------

# 8. Main scanning and candidate selection

## `scan()`

**Purpose:** Coordinates the scan, classification, duplicate detection,
reporting, and user selection.

### Initialize collections

``` python
candidates = []
hash_groups = defaultdict(list)
```

`candidates` is a list of dictionaries describing files that might be
staged.

`hash_groups` groups files by SHA-256 digest. `defaultdict(list)`
automatically creates an empty list when a previously unseen hash is
used as a key.

### Scan and classify files

``` python
for path, size, modified in scan_files():
    category = classify(path)

    if category:
        candidates.append({
            "path": str(path),
            "category": category,
            "size": size,
            "modified": modified,
        })
```

For each file, the program asks `classify()` for a category. If a
category is returned, it appends a dictionary to `candidates`.

`str(path)` converts a `Path` object into a string, which can be stored
in JSON later.

### Hash files for duplicate detection

``` python
if size <= 100 * 1024 * 1024 and size > 0:
    digest = file_hash(path)

    if digest:
        hash_groups[digest].append((path, size, modified))
```

Only non-empty files up to 100 MiB are hashed in this version.

Each hash maps to a list of tuples. Each tuple contains the path, size,
and modification timestamp.

Files with the same hash are candidates for being duplicates.

### Find groups with multiple files

``` python
duplicate_groups = [
    group for group in hash_groups.values()
    if len(group) > 1
]
```

`hash_groups.values()` returns the dictionary's lists. A group with more
than one file is treated as a duplicate group.

### Unused variable in this version

``` python
duplicate_paths = {
    str(path)
    for group in duplicate_groups
    for path, _, _ in group[1:]
}
```

This creates a set of duplicate paths, excluding the first file in each
group. However, the variable is never used later in the program. It is
unnecessary and can be removed.

The underscores in `for path, _, _` indicate tuple values that the code
does not need.

### Avoid adding a file twice

``` python
existing = {item["path"] for item in candidates}
```

This creates a set of paths already present in the candidate list.

Then:

``` python
for group in duplicate_groups:
    for path, size, modified in group[1:]:
        if str(path) not in existing:
            candidates.append({
                "path": str(path),
                "category": "duplicates",
                "size": size,
                "modified": modified,
            })
```

`group[1:]` selects all files after the first file in the group. The
program treats the first one as the copy to keep and adds the remaining
ones as duplicate candidates, unless they are already in another
category.

This is a policy choice, not proof that the first file is the best copy.

### Sort candidates

``` python
candidates.sort(
    key=lambda item: (item["category"], item["path"])
)
```

Sorts candidates by category and then path.

`lambda` creates a small anonymous function. This expression is
equivalent to:

``` python
def sort_key(item):
    return (item["category"], item["path"])
```

### Calculate category totals

``` python
totals = defaultdict(lambda: [0, 0])

for item in candidates:
    totals[item["category"]][0] += 1
    totals[item["category"]][1] += item["size"]
```

The `defaultdict` creates `[0, 0]` for a category that has not been
seen.

For each category:

-   Index `0` stores the number of files.
-   Index `1` stores their combined size.

A `lambda: [0, 0]` is used because each new category needs its own new
list.

### Report cache and Trash

``` python
for label, folder in REPORTED_ONLY.items():
    if folder.exists():
        print(f"{label:10} {folder} (not moved)")
```

`.items()` returns key-value pairs from the dictionary. The program
checks whether each location exists and reports it. These locations are
not automatically staged.

### Display candidates

``` python
for number, item in enumerate(candidates, 1):
    print(...)
```

`enumerate()` provides both an index and an item. The second argument,
`1`, makes numbering start at one, which is convenient for user
selection.

### Read the selection

``` python
choice = input("\nSelection: ").strip().lower()
```

-   `input()` reads text from the user.
-   `strip()` removes surrounding whitespace.
-   `lower()` makes the input lowercase.

The user can enter:

-   `all`
-   A category such as `pdfs`
-   Comma-separated numbers such as `1,3,5`
-   `none`

For numbered selection:

``` python
numbers = {
    int(value.strip())
    for value in choice.split(",")
}
```

`split(",")` separates the input at commas. `int()` converts each number
from text into an integer. The set comprehension stores the selected
numbers.

The code validates the numbers before selecting the corresponding
candidate records.

Finally, the program asks for confirmation. If the user confirms with
`y`, it calls:

``` python
stage_files(selected)
```

------------------------------------------------------------------------

# 9. Moving files safely

## `unique_destination(destination)`

``` python
def unique_destination(destination):
    if not destination.exists():
        return destination

    counter = 1

    while True:
        candidate = destination.with_name(
            f"{destination.stem}__{counter}{destination.suffix}"
        )

        if not candidate.exists():
            return candidate

        counter += 1
```

**Purpose:** Avoids using a destination filename that already exists.

For `notes.pdf`:

-   `destination.stem` is `notes`.
-   `destination.suffix` is `.pdf`.

The function tries `notes__1.pdf`, `notes__2.pdf`, and so on until it
finds an unused name.

`while True` creates a loop that continues until a `return` exits the
function.

## `stage_files(items)`

**Purpose:** Moves selected files into the review folder and records
their original locations.

### Set up

``` python
REVIEW.mkdir(parents=True, exist_ok=True)
manifest = load_manifest()
moved = 0
```

Creates the review directory if necessary, loads existing records, and
initializes a counter.

### Process each selected item

``` python
for item in items:
    source = Path(item["path"])
```

Each `item` is a dictionary describing a candidate. The source string is
converted back into a `Path`.

### Recheck the source

``` python
if not source.is_file() or source.is_symlink():
    continue
```

The file might have disappeared or changed since the scan. The function
checks again before moving it.

### Check the path boundary

``` python
if not is_inside(source, HOME) or is_inside(source, REVIEW):
    continue
```

The source must be inside the home directory and must not already be
inside the review directory.

### Preserve the original directory structure

``` python
relative = source.relative_to(HOME)
```

For `/home/nevin/Documents/notes.pdf`, this produces
`Documents/notes.pdf`.

Then:

``` python
destination = unique_destination(
    REVIEW / item["category"] / relative
)
```

Constructs a destination such as:

``` text
/home/nevin/CleanupReview/pdfs/Documents/notes.pdf
```

The category folder organizes the file, while the relative path
preserves its original location beneath that category.

### Create destination directories and move

``` python
destination.parent.mkdir(parents=True, exist_ok=True)
shutil.move(str(source), str(destination))
```

Creates the parent directories and moves the file.

`shutil.move()` can move across filesystems, using a copy-and-remove
approach when a simple filesystem rename is not possible.

### Record the move

``` python
manifest["items"].append({
    "id": len(manifest["items"]) + 1,
    "category": item["category"],
    "original": str(source),
    "stored": str(destination),
    "size": item["size"],
    "staged_at": time.time(),
    "status": "staged",
})
```

Each record stores:

  Key           Meaning
  ------------- -----------------------------------
  `id`          Record number
  `category`    Candidate category
  `original`    Original location
  `stored`      Current review-folder location
  `size`        Recorded size in bytes
  `staged_at`   Unix timestamp when staged
  `status`      Current state, initially `staged`

The `original` path is essential for restoring a file.

`time.time()` returns the current Unix timestamp: seconds since January
1, 1970 UTC.

The function increments `moved` after a successful move and saves the
manifest at the end.

**Important reliability limitation:** The manifest is saved after the
moves. If the program crashes after moving a file but before saving its
record, the file could be left without a restoration record. A more
robust design should record an intended operation before moving and then
update its status after success.

------------------------------------------------------------------------

# 10. Reviewing staged files

## `review()`

``` python
def review():
    manifest = load_manifest()

    active = [
        item for item in manifest["items"]
        if item["status"] == "staged"
    ]

    if not active:
        print("There are no staged files to review.")
        return

    print(f"{'ID':>4}  {'CATEGORY':14} {'SIZE':>10}  FILE")
    print("-" * 85)

    for item in active:
        print(
            f"{item['id']:4}  {item['category']:14} "
            f"{human(item['size']):>10}  {item['stored']}"
        )
```

**Purpose:** Displays files that are still staged and awaiting a
decision.

The list comprehension filters manifest records to those whose status is
`"staged"`.

If the list is empty, the function prints a message and returns.

Otherwise, it prints a table-like report. `human()` converts sizes into
readable units.

The formatting expressions such as `:>4` right-align values in a field
of four characters.

------------------------------------------------------------------------

# 11. Restoring files

## `restore()`

**Purpose:** Moves selected staged files back to their original
locations.

First, it loads the manifest and selects records whose status is
`"staged"`. It displays their IDs and stored paths.

The user can enter `all` or comma-separated IDs such as `1,3,5`.

For numbered selection:

``` python
ids = {int(value.strip()) for value in choice.split(",")}
selected = [
    item for item in active
    if item["id"] in ids
]
```

This converts the input into a set of integers and finds matching
records.

After confirmation, each record supplies two paths:

``` python
stored = Path(item["stored"])
original = Path(item["original"])
```

The function then:

1.  Checks that the staged file exists.
2.  Checks that the stored path is inside `REVIEW`.
3.  Checks that the original path is inside `HOME`.
4.  Refuses to overwrite an existing original file.
5.  Recreates the original parent directory if necessary.
6.  Moves the staged file back.
7.  Changes the status to `"restored"`.

The move operation is:

``` python
shutil.move(str(stored), str(original))
```

The status update is:

``` python
item["status"] = "restored"
```

Finally, `save_manifest(manifest)` persists the updated record.

The overwrite check is important: the program should not silently
replace a file that the user created after the original was staged.

------------------------------------------------------------------------

# 12. Permanently deleting staged files

## `purge()`

**Purpose:** Permanently removes selected staged files from the review
folder.

The function loads the manifest and selects staged records. It displays
the available files and asks for IDs or `all`.

Before deletion, it requires the user to type the exact word `DELETE`.
This is a stronger confirmation than a simple `y`, because the operation
is permanent.

For each selected record:

``` python
stored = Path(item["stored"])
```

The program checks that the path is inside the review directory and is
not the manifest itself.

Then:

``` python
if stored.is_file() and not stored.is_symlink():
    stored.unlink()
    item["status"] = "deleted"
```

`unlink()` removes a file from the filesystem. Unlike moving a file to
Trash, this does not provide a built-in recovery operation.

The manifest is saved after processing.

**Important limitations:** The current version does not remove empty
directories left behind in the review folder. It also does not verify
that the staged file's contents still match the original scan before
deleting it. A production version should compare recorded metadata and
preferably a stored hash before purging.

------------------------------------------------------------------------

# 13. Command-line entry point

## `main()`

``` python
def main():
    parser = argparse.ArgumentParser(
        description="Scan, review, restore, and selectively delete files."
    )

    parser.add_argument(
        "command",
        choices=("scan", "review", "restore", "purge"),
        help="operation to perform",
    )

    args = parser.parse_args()

    try:
        if args.command == "scan":
            scan()
        elif args.command == "review":
            review()
        elif args.command == "restore":
            restore()
        elif args.command == "purge":
            purge()

    except (OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0
```

**Purpose:** Decides which operation to run based on the terminal
command.

`argparse.ArgumentParser()` creates a command-line argument parser.

`add_argument()` defines a required positional argument named `command`.
The `choices` tuple restricts it to four accepted commands.

`parse_args()` reads the actual command-line input.

For example:

``` bash
python3 cleanup.py scan
```

Then `args.command` is `"scan"`.

The `if`/`elif` chain calls the matching function.

The `try`/`except` block catches selected operational errors.
`sys.stderr` is the conventional output stream for error messages.

The function returns `0` when it finishes successfully and `1` when one
of the caught errors occurs.

## The final two lines

``` python
if __name__ == "__main__":
    raise SystemExit(main())
```

Python sets the special variable `__name__` to `"__main__"` when a file
is executed directly.

This condition means the application starts when you run:

``` bash
python3 cleanup.py scan
```

But if another Python file imports it:

``` python
import cleanup
```

the command-line application does not automatically start.

`SystemExit(main())` exits the program using the return code from
`main()`.

------------------------------------------------------------------------

# 14. Data structures used throughout the project

  -----------------------------------------------------------------------
  Structure               Example                 Purpose
  ----------------------- ----------------------- -----------------------
  String                  `"temporary"`           Stores text

  Integer                 `moved = 0`             Stores whole numbers

  Float                   `time.time()`           Stores decimal numbers

  Tuple                   `CATEGORIES`            Ordered, immutable
                                                  collection

  List                    `candidates`            Ordered, mutable
                                                  collection

  Dictionary              `REPORTED_ONLY`         Key-value pairs

  Set                     `SKIP_DIRS`             Unique values and
                                                  membership checks

  `defaultdict`           `hash_groups`           Dictionary with
                                                  automatic default
                                                  values

  Generator               `scan_files()`          Produces results
                                                  incrementally

  JSON                    `manifest.json`         Persists records
                                                  between runs
  -----------------------------------------------------------------------

## How they work together

1.  `scan_files()` generates file paths and metadata.
2.  `classify()` assigns a category.
3.  `candidates` stores dictionaries describing candidate files.
4.  `hash_groups` groups files by content hash.
5.  `scan()` presents the candidate list.
6.  `stage_files()` moves selected files and adds manifest dictionaries.
7.  `save_manifest()` writes those dictionaries to JSON.
8.  `restore()` and `purge()` update the records later.

------------------------------------------------------------------------

# 15. Important improvements to make

The reconstructed application is a useful learning prototype, but
several improvements are recommended before trusting it with important
files.

  -----------------------------------------------------------------------
  Issue                   Why it matters          Improvement
  ----------------------- ----------------------- -----------------------
  Every `.log` file is    Recent logs may be      Add an age threshold
  classified as old       important               

  Hashes are calculated   Can make scanning slow  Group by file size
  for every eligible file                         before hashing
  up to 100 MiB                                   

  `duplicate_paths` is    Unnecessary work        Remove it
  unused                                          

  Manifest is saved after A crash can leave an    Use a safer operation
  moving                  untracked file          journal

  Files may change after  Candidate information   Recheck metadata and
  scanning                can become stale        contents

  Empty review            Leaves unnecessary      Remove empty
  directories remain      folders                 directories carefully

  No scan progress        Large scans may appear  Add progress reporting
  indicator               unresponsive            

  Duplicate detection     Hash collisions are     Compare contents after
  trusts hash equality    theoretically possible  matching hashes

  Filename-based          It may miss or          Add user-configurable
  classification is       misclassify files       rules
  imperfect                                       
  -----------------------------------------------------------------------

A useful optimization for duplicate detection is to group files by size
first. Files with different sizes cannot have identical contents, so
there is no need to hash them against one another.

------------------------------------------------------------------------

# 16. Suggested learning order

To understand and maintain this project, study these concepts in order:

1.  **Functions, parameters, return values, and scope.**
2.  **Lists, tuples, sets, dictionaries, and comprehensions.**
3.  **`pathlib` and filesystem operations.**
4.  **`os.walk()`, generators, and `yield`.**
5.  **Exception handling with `try` and `except`.**
6.  **JSON serialization and persistent data.**
7.  **SHA-256 hashing and duplicate detection.**
8.  **Command-line interfaces with `argparse`.**

The three most important mechanisms to understand deeply are:

-   `scan_files()` --- how the application explores the filesystem.
-   `scan()` --- how the application classifies and selects candidates.
-   `stage_files()` --- how the application moves files and records
    their history.

Once you understand those, the rest of the application becomes much
easier to follow.
