import os
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Set
from PIL import Image


def extract_location_info(folder_name: str) -> str:
    """Extracts Chinese characters from the folder name to determine location.

    Args:
        folder_name: The name of the folder to scan.

    Returns:
        str: A string containing merged Chinese characters found, or empty string.
    """
    matches = re.findall(r"[\u4e00-\u9fa5]+", folder_name)
    return "".join(matches) if matches else ""


def get_date_taken(path: Path, image_extensions: Set[str]) -> datetime:
    """Gets the creation date of the file.

    Tries to read EXIF data for images. Falls back to file modification time.

    Args:
        path: Path to the file.
        image_extensions: Set of extensions considered as images.

    Returns:
        datetime: The datetime object representing when the file was taken/created.
    """
    is_image = path.suffix.lower() in image_extensions
    if is_image:
        try:
            img = Image.open(path)
            exif_data = img._getexif()
            if exif_data and 36867 in exif_data:
                return datetime.strptime(exif_data[36867], "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
    return datetime.fromtimestamp(os.path.getmtime(path))


def get_unique_path(path: Path) -> Path:
    """Generates a unique path by appending a counter if the file exists.

    Args:
        path: The original destination path.

    Returns:
        Path: A path that does not currently exist.
    """
    if not path.exists():
        return path
    counter = 1
    while True:
        new_path = path.parent / f"{path.stem}_{counter}{path.suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def organize(
    config: Dict[str, Any], dry_run: Optional[bool] = None, verbose: bool = False
) -> Dict[str, Any]:
    """Organizes photos based on metadata into a structured directory tree.

    Structure: Destination / Decade / Year / Year-Month [Location] / Filename

    Args:
        config: Configuration dictionary containing directory paths and settings.
        dry_run: If True, only simulate operations. Defaults to config setting.
        verbose: If True, print detailed logs.

    Returns:
        Dict[str, Any]: Statistics including "success", "skipped", and "errors".
    """
    from photo_meta_organizer.config import get_extensions

    # Parse arguments
    source_dir = Path(config["directories"]["source"])
    target_dir = Path(config["directories"]["destination"])
    dry_run = dry_run if dry_run is not None else config["settings"]["dry_run"]

    extensions = get_extensions(config)
    image_extensions = extensions["image"]
    valid_extensions = extensions["all"]

    print(f"🚀 Mission Start | Mode: {'[DRY RUN]' if dry_run else '[LIVE]'}")
    print(f"📂 Source: {source_dir}")
    print("-" * 40)

    if not source_dir.exists():
        print("❌ Source directory does not exist")
        return {
            "success": 0,
            "skipped": 0,
            "errors": ["Source directory does not exist"],
        }

    count_success = 0
    count_skip = 0
    errors = []
    files_processed_ok = 0  # Counter for successful processes to sample logs

    # Traverse
    for file_path in source_dir.rglob("*"):
        if not file_path.is_file():
            continue

        # 1. Skip system files (Verbose log)
        if file_path.name.startswith(".") or file_path.name == ".DS_Store":
            if verbose:
                print(f"🗑️ [Skip] System file: {file_path.name}")
            count_skip += 1
            continue

        # 2. Skip unsupported formats (Always warn)
        if file_path.suffix.lower() not in valid_extensions:
            print(
                f"⚠️ [Skip] Unsupported format: {file_path.name} ({file_path.parent.name})"
            )
            count_skip += 1
            continue

        # 3. Normal process
        try:
            files_processed_ok += 1

            # Decide whether to print (First one or every 20th)
            should_print = (files_processed_ok == 1) or (files_processed_ok % 20 == 0)

            # --- Core Logic ---
            date_obj = get_date_taken(file_path, image_extensions)
            year_str = str(date_obj.year)
            month_val = date_obj.month

            loc = extract_location_info(file_path.parent.name) or extract_location_info(
                file_path.parent.parent.name
            )
            suffix = f" {loc}" if loc else ""

            decade = (
                "1979-" if date_obj.year <= 1979 else f"{(date_obj.year // 10) * 10}+"
            )
            target_folder = (
                target_dir / decade / year_str / f"{year_str}-{month_val}{suffix}"
            )
            target_path = target_folder / file_path.name

            if dry_run:
                # Dry run mode
                final_path = target_path
                note = ""
                if final_path.exists():
                    final_path = get_unique_path(final_path)
                    note = " [Rename Required]"

                # Sample print
                if should_print or verbose:
                    print(
                        f"[Dry Run] ({files_processed_ok}) .../{final_path.parent.name}/{final_path.name}{note}"
                    )

            else:
                # Live mode
                target_folder.mkdir(parents=True, exist_ok=True)

                if (
                    target_path.exists()
                    and file_path.resolve() == target_path.resolve()
                ):
                    if verbose:
                        print(f"⏩ [Skip] In Place: {file_path.name}")
                    count_skip += 1
                    continue

                if target_path.exists():
                    target_path = get_unique_path(target_path)

                shutil.move(str(file_path), str(target_path))

                # Sample print
                if should_print or verbose:
                    print(f"✅ [Success] ({files_processed_ok}) {file_path.name}")

            count_success += 1

        except Exception as e:
            # Errors must be printed
            error_msg = f"{file_path.name}: {e}"
            print(f"❌ [Error] {error_msg}")
            errors.append(error_msg)
            count_skip += 1

    print("-" * 40)
    print(f"🏁 Done. Success: {count_success}, Skipped/Error: {count_skip}")

    return {"success": count_success, "skipped": count_skip, "errors": errors}
