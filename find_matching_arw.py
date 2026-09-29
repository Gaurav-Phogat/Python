import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_RAW_ROOT = Path(r"G:\29 June 2026")
DEFAULT_JPEG_FOLDER = Path(r"C:\Users\gaura\Desktop\Final Photos selected")
JPEG_EXTENSIONS = {".jpg", ".jpeg"}


def iter_files(folder: Path):
    def report_walk_error(error: OSError) -> None:
        print(f"Could not scan {error.filename}: {error}")

    for current_folder, _, filenames in os.walk(folder, onerror=report_walk_error):
        for filename in filenames:
            yield Path(current_folder) / filename


def is_same_or_child(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def make_unique_report_path(destination: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = destination / f"missing_arw_{timestamp}.txt"
    suffix = 1
    while report_path.exists():
        report_path = destination / f"missing_arw_{timestamp}_{suffix}.txt"
        suffix += 1
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy ARW files whose names match JPEGs in a selected folder."
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=DEFAULT_RAW_ROOT,
        help="Folder tree to search for .ARW files.",
    )
    parser.add_argument(
        "--jpeg-folder",
        type=Path,
        default=DEFAULT_JPEG_FOLDER,
        help="Folder tree containing the selected .jpg and .jpeg files.",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        help="Folder to receive matching .ARW files (prompted if omitted).",
    )
    args = parser.parse_args()

    raw_root = args.raw_root.expanduser().resolve()
    jpeg_folder = args.jpeg_folder.expanduser().resolve()
    destination_input = args.destination
    if destination_input is None:
        destination_input = Path(input("Folder to copy matching ARW files into: ").strip())
    destination = destination_input.expanduser().resolve()

    if not raw_root.is_dir():
        parser.error(f"ARW search folder does not exist: {raw_root}")
    if not jpeg_folder.is_dir():
        parser.error(f"JPEG folder does not exist: {jpeg_folder}")
    if is_same_or_child(destination, raw_root):
        parser.error("Choose a destination outside the ARW search folder.")

    jpeg_files = [
        path
        for path in iter_files(jpeg_folder)
        if path.suffix.lower() in JPEG_EXTENSIONS
    ]
    if not jpeg_files:
        print(f"No .jpg or .jpeg files found under: {jpeg_folder}")
        return 0

    wanted_stems = {path.stem.casefold() for path in jpeg_files}
    arw_by_stem = {}
    for path in iter_files(raw_root):
        if path.suffix.lower() == ".arw":
            stem = path.stem.casefold()
            if stem in wanted_stems:
                arw_by_stem.setdefault(stem, []).append(path)

    missing_jpegs = [
        path for path in jpeg_files if path.stem.casefold() not in arw_by_stem
    ]
    matching_arws = {
        raw_path
        for jpeg_path in jpeg_files
        for raw_path in arw_by_stem.get(jpeg_path.stem.casefold(), [])
    }

    destination.mkdir(parents=True, exist_ok=True)
    copied_count = 0
    skipped_count = 0
    for raw_path in sorted(matching_arws):
        target_path = destination / raw_path.relative_to(raw_root)
        if target_path.exists():
            print(f"Skipped existing file: {target_path}")
            skipped_count += 1
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(raw_path, target_path)
        copied_count += 1

    report_path = None
    if missing_jpegs:
        report_path = make_unique_report_path(destination)
        with report_path.open("x", encoding="utf-8") as report:
            for jpeg_path in sorted(missing_jpegs):
                report.write(f"{jpeg_path.relative_to(jpeg_folder)}\n")

    print(f"JPEG files checked: {len(jpeg_files)}")
    print(f"Matching ARW files copied: {copied_count}")
    print(f"Existing destination files skipped: {skipped_count}")
    print(f"JPEGs with no matching ARW: {len(missing_jpegs)}")
    if report_path is not None:
        print(f"Missing-name report: {report_path}")
    print("No files were deleted or overwritten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())