import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Set
from PIL import Image
from pillow_heif import register_heif_opener

# Register HEIC support
register_heif_opener()


def get_date_strategy(
    file_path: Path, image_extensions: Set[str]
) -> Tuple[Optional[datetime], str]:
    """Determines the best date strategy for the file.

    Strategies:
    1. EXIF DateTimeOriginal (for images).
    2. EXIF DateTime (fallback for images).
    3. File modification time (for videos or images without EXIF).

    Args:
        file_path: Path to the file.
        image_extensions: Set of extensions considered as images.

    Returns:
        Tuple[Optional[datetime], str]: A tuple containing the datetime object
        (or None if not found) and a source tag string ("" for EXIF, "sys_" for system time).
    """
    suffix = file_path.suffix.lower()

    # --- Strategy A: Try reading EXIF for images ---
    if suffix in image_extensions:
        try:
            with Image.open(file_path) as img:
                exif_data = img.getexif()
                if exif_data:
                    # 36867=DateTimeOriginal, 306=DateTime
                    date_str = exif_data.get(36867) or exif_data.get(306)
                    if date_str:
                        # Format is typically YYYY:MM:DD HH:MM:SS
                        return (
                            datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S"),
                            "",
                        )  # Empty string indicates official EXIF
        except Exception:
            pass  # Fallback to next strategy

    # --- Strategy B: System modification time (Video or failed EXIF) ---
    # Note: Returns "sys_" tag to indicate it's a guess
    try:
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime), "sys_"
    except Exception:
        return None, ""


def get_unique_path(path: Path) -> Path:
    """Generates a unique path by appending a counter if the file exists.

    Format: filename_1.ext, filename_2.ext, etc.

    Args:
        path: The original destination path.

    Returns:
        Path: A path that does not currently exist.
    """
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1

    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def rename_process(
    config: Dict[str, Any], dry_run: Optional[bool] = None, verbose: bool = False
) -> Dict[str, Any]:
    """Runs the batch rename process.

    Renames files to YYYYMMDD_HHMMSS_[sys_]OriginalName.ext.

    Args:
        config: Configuration dictionary.
        dry_run: If True, only simulate operations. Defaults to config setting.
        verbose: If True, print detailed logs.

    Returns:
        Dict[str, Any]: Statistics including "success" and "skipped".
    """
    from photo_meta_organizer.config import get_extensions

    target_dir = Path(config["directories"]["target_dir"])
    dry_run = dry_run if dry_run is not None else config["settings"]["dry_run"]

    extensions = get_extensions(config)
    image_extensions = extensions["image"]
    valid_extensions = extensions["all"]

    print(f"🚀 Rename Mission Start | Mode: {'[DRY RUN]' if dry_run else '[LIVE]'}")
    print(f"📂 Target: {target_dir}")
    print("-" * 40)

    if not target_dir.exists():
        print("❌ Target directory not found")
        return {"success": 0, "skipped": 0}

    count_success = 0
    count_skip = 0

    # Recursive scan
    for file_path in target_dir.rglob("*"):
        if not file_path.is_file():
            continue

        # 1. Skip system files
        if file_path.name.startswith(".") or file_path.name == ".DS_Store":
            continue

        # 2. Check extensions
        if file_path.suffix.lower() not in valid_extensions:
            continue

        # 3. Check if already renamed (8 digits + underscore) e.g. 20220101_
        if (
            len(file_path.name) > 9
            and file_path.name[:8].isdigit()
            and file_path.name[8] == "_"
        ):
            # print(f"⏩ [Already Renamed] Skip: {file_path.name}")
            continue

        # --- Core Logic ---
        try:
            date_obj, source_tag = get_date_strategy(file_path, image_extensions)

            if not date_obj:
                print(f"⚠️ [No Date] Cannot process: {file_path.name}")
                count_skip += 1
                continue

            # Construct new filename: YYYYMMDD_HHMMSS_[sys_]Original.ext
            time_prefix = date_obj.strftime("%Y%m%d_%H%M%S")
            original_name = file_path.name

            # Combine
            new_filename = f"{time_prefix}_{source_tag}{original_name}"
            target_path = file_path.parent / new_filename

            # Skip if name hasn't changed
            if target_path.name == file_path.name:
                continue

            # Handle duplicates
            if target_path.exists():
                target_path = get_unique_path(target_path)

            # Execute
            if dry_run:
                print(f"📝 [Dry Run] {file_path.name}  --->  {target_path.name}")
            else:
                file_path.rename(target_path)
                print(f"✅ {file_path.name} -> {target_path.name}")

            count_success += 1

        except Exception as e:
            print(f"❌ [Error] {file_path.name}: {e}")
            count_skip += 1

    print("-" * 40)
    print(f"🏁 Done. Planned rename: {count_success}, Skipped/Error: {count_skip}")
    if dry_run:
        print("💡 Tip: Set DRY_RUN = False in code or config to execute.")

    return {"success": count_success, "skipped": count_skip}
