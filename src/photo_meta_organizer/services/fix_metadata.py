import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import piexif


def parse_date_from_path(file_path: Path) -> Tuple[Optional[int], Optional[int]]:
    """Parses year and month from the file path structure.

    Strategies:
    1. Parent name contains "YYYY-MM" or "YYYY MM" (e.g. "2023-5", "2023 05")
    2. Parent name is pure year "YYYY" (e.g. "2023") -> Defaults to January
    3. Parent is "MM" and Grandparent is "YYYY" (e.g. "2000/2")

    Args:
        file_path: Path to the file.

    Returns:
        Tuple[Optional[int], Optional[int]]: A tuple of (year, month) if found, else (None, None).
    """
    parent = file_path.parent.name
    grandparent = file_path.parent.parent.name

    # Strategy 1: Strong pattern "2023-5" / "2023 05"
    match = re.search(r"(\d{4})[-.\s]+(\d{1,2})", parent)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Strategy 2: Pure year folder "2023" -> Jan
    if parent.isdigit() and len(parent) == 4:
        return int(parent), 1

    # Strategy 3: Year/Month structure "2000/2"
    if parent.isdigit() and len(parent) <= 2:
        if grandparent.isdigit() and len(grandparent) == 4:
            return int(grandparent), int(parent)

    return None, None


def update_exif_and_file_time(
    file_path: Path, year: int, month: int, dry_run: bool = True
) -> bool:
    """Updates the file's EXIF metadata and system modification time.

    Sets the date to the 26th of the specified month at 12:00:00.

    Args:
        file_path: Path to the image file.
        year: The year to set.
        month: The month to set.
        dry_run: If True, only simulate operations.

    Returns:
        bool: True if successful, False otherwise.
    """
    # 1. Construct date string (EXIF format)
    date_str = f"{year}:{month:02d}:26 12:00:00"

    # 2. Construct timestamp (for filesystem)
    # String -> datetime -> timestamp float
    dt_obj = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    unix_ts = dt_obj.timestamp()

    if dry_run:
        print(f"[Dry Run] {file_path.name}")
        print(f"      -> EXIF Write: {date_str}")
        print(f"      -> System ModTime: {dt_obj}")
        return True

    try:
        # --- A. Modify EXIF Data (Content Layer) ---
        try:
            exif_dict = piexif.load(str(file_path))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        # Critical: Write to three places to ensure compatibility
        # 1. ExifIFD: DateTimeOriginal (Standard)
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str
        # 2. ExifIFD: DateTimeDigitized
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_str
        # 3. 0th IFD: DateTime (Often used by Finder and thumbnails)
        exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str

        # Remove thumbnail to avoid inconsistency errors
        exif_dict.pop("thumbnail", None)

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(file_path))

        # --- B. Modify Filesystem Time (Physical Layer) ---
        # os.utime(path, (access_time, modification_time))
        os.utime(str(file_path), (unix_ts, unix_ts))

        print(f"✅ [Success] {file_path.name} -> {date_str}")
        return True

    except Exception as e:
        print(f"❌ [Failed] {file_path.name}: {e}")
        return False


def run_fix(
    config: Dict[str, Any], dry_run: Optional[bool] = None, verbose: bool = False
) -> Dict[str, Any]:
    """Runs the metadata fix process.

    Args:
        config: Configuration dictionary.
        dry_run: If True, only simulate operations. Defaults to config setting.
        verbose: If True, print detailed logs.

    Returns:
        Dict[str, Any]: Statistics including "success" and "failed".
    """
    target_root = Path(config["directories"]["fix_dir"])
    dry_run = dry_run if dry_run is not None else config["settings"]["dry_run"]
    valid_extensions = {".jpg", ".jpeg"}

    print(
        f"🔧 Fix Mission Start (Exif + System Time) | Mode: {'[DRY RUN]' if dry_run else '[LIVE]'}"
    )
    print(f"📂 Target: {target_root}")

    if not target_root.exists():
        print(f"❌ Directory not found: {target_root}")
        return {"success": 0, "failed": 0}

    count = 0

    for file_path in target_root.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in valid_extensions:
            continue

        year, month = parse_date_from_path(file_path)

        if year and month:
            # Validate year range and month
            if 1900 < year < 2030 and 1 <= month <= 12:
                update_exif_and_file_time(file_path, year, month, dry_run)
                count += 1
            else:
                pass  # Ignore unreasonable dates
        else:
            pass

    print("-" * 40)
    print(f"🏁 Done. Processed: {count} photos")

    return {"success": count, "failed": 0}
