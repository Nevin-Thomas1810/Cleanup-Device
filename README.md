# Linux Cleanup

A Python-based command-line utility for finding, reviewing, and managing unnecessary files on Linux.

Linux Cleanup helps you organize your home directory by identifying potential clutter and moving selected files into a dedicated review folder before permanent deletion.

## Features

- **Temporary Files:** Identifies files with temporary file extensions.
- **Old Logs:** Finds log files that may no longer be needed.
- **Duplicate Detection:** Uses file hashing to identify duplicate files.
- **PDF Detection:** Finds PDF files for review.
- **Screenshot Detection:** Identifies screenshots using filenames and directory names.
- **Review System:** Stages selected files in a separate review directory.
- **Restore:** Allows staged files to be restored to their original locations.
- **Permanent Purge:** Permanently deletes staged files after explicit confirmation.
- **Cache Reporting:** Reports cache and Trash locations without automatically modifying them.

## Requirements

- Linux operating system
- Python 3

**Dependencies:** This application uses only Python's standard library. No external packages or `pip install` commands are required.

## Installation

### Option 1: Download a Release

1. Visit the [GitHub Releases](https://github.com/Nevin-Thomas1810/Cleanup-Device/releases) page.
2. Download the latest `.tar.gz` archive.
3. Extract the archive:

```bash
tar -xzf linux-cleanup-v1.0.0.tar.gz
```

4. Enter the extracted directory:

```bash
cd linux-cleanup-v1.0.0
```

### Option 2: Clone the Repository

```bash
git clone https://github.com/Nevin-Thomas1810/Cleanup-Device.git
cd Cleanup-Device
```
### How It Works:

```scan → review → restore | purge ```

```scan — Walks your home directory, identifies candidates (temp files, old logs, duplicates, PDFs, screenshots), and lets you select which to stage.```

```review — Shows everything currently staged in ~/CleanupReview along with its original path.```

```restore — Moves a staged file (or all staged files) back to its original location.```

```purge — Permanently deletes staged files. Requires explicit confirmation.```

A JSON manifest in ~/CleanupReview tracks the original path of every staged file, which is what makes restore possible.

## Usage

Run the application using Python 3:

```bash
python3 main.py
```

Available commands:

| Command | Description |
|---|---|
| `scan` | Scans for potential cleanup candidates |
| `review` | Displays staged files |
| `restore` | Restores staged files |
| `purge` | Permanently deletes staged files after confirmation |

For example:

```bash
python3 main.py scan
python3 main.py review
```

To see the available command-line options:

```bash
python3 main.py --help
```

## Safety

Linux Cleanup is designed with a review-before-deletion approach.

- Scanning does not automatically delete files.
- Selected files are staged in `~/CleanupReview`.
- A JSON manifest keeps track of staged files.
- Files can be restored before permanent deletion.
- Permanent deletion requires explicit confirmation.

**Warning:** The `purge` command permanently deletes selected staged files. Review the files carefully before confirming.

Always keep backups of important data.

## Project Structure

```text
linux-cleanup/
├── main.py
├── README.md
├── LICENSE
└── .gitignore
```

## Technologies Used

- Python 3.9+
- `argparse`
- `hashlib`
- `json`
- `os`
- `shutil`
- `pathlib`

All modules used are part of Python's standard library.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Author

**Nevin Thomas**

GitHub: [@Nevin-Thomas1810](https://github.com/Nevin-Thomas1810)

---

If you find this project useful, consider giving the repository a ⭐!

