import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


def get_file_size_mb(file_path: Path) -> float:
    """Calculates file size in MB.

    Args:
        file_path: Path to the file.

    Returns:
        float: File size in megabytes.
    """
    return file_path.stat().st_size / (1024 * 1024)


def clean_small_files_recursive(
    config: Dict[str, Any], dry_run: Optional[bool] = None, verbose: bool = False
) -> Dict[str, Any]:
    """Recursively finds and moves files smaller than a threshold to a junk folder.

    Args:
        config: Configuration dictionary.
        dry_run: If True, only simulate operations. Defaults to config setting.
        verbose: If True, print detailed logs.

    Returns:
        Dict[str, Any]: Statistics including "found" and "scanned".
    """
    root_dir = config["directories"]["root_dir"]
    size_threshold_mb = config["settings"]["size_threshold_mb"]
    dry_run = dry_run if dry_run is not None else config["settings"]["dry_run"]

    root_path = Path(root_dir).resolve()
    junk_path = root_path / "junk"

    if not root_path.exists():
        print(f"❌ Error: Directory not found {root_path}")
        return {"found": 0, "scanned": 0}

    print(f"--- Scanning: {root_path} ---")
    print(f"--- Threshold: <= {size_threshold_mb} MB ---\n")

    found_count = 0
    scanned_count = 0

    # Recursive scan using rglob('*')
    for file_path in root_path.rglob("*"):
        # Skip directory themselves
        if not file_path.is_file():
            continue

        # [Safety Lock]: Never scan the junk directory itself
        if junk_path in file_path.parents:
            continue

        scanned_count += 1
        size_mb = get_file_size_mb(file_path)

        # Verbose logging
        if verbose:
            print(f"[Scanning] {file_path.name} - {size_mb:.4f} MB")

        # Check size (less than or equal)
        if size_mb <= size_threshold_mb:
            found_count += 1

            # Calculate target path
            target_junk_file = junk_path / file_path.name

            # Handle duplicates
            if target_junk_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_junk_file = (
                    junk_path / f"{file_path.stem}_{timestamp}{file_path.suffix}"
                )

            # Execute/Simulate
            if dry_run:
                print(f"✅ [Found] {file_path.name}")
                print(f"   └─ Path: {file_path}")
                print(f"   └─ Size: {size_mb:.4f} MB (To be moved)")
            else:
                try:
                    junk_path.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(target_junk_file))
                    print(f"🚀 [Moved] {file_path.name}")
                except Exception as e:
                    print(f"❌ [Failed] Could not move {file_path.name}: {e}")

    print("\n--- Summary ---")
    print(f"Scanned: {scanned_count} files")
    print(f"Found (<= {size_threshold_mb} MB): {found_count} files")

    if scanned_count == 0:
        print("⚠️ Warning: No files scanned. Check if root_dir path is correct.")

    return {"found": found_count, "scanned": scanned_count}
