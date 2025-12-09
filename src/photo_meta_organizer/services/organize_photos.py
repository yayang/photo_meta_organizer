import os
import shutil
import re
from datetime import datetime
from pathlib import Path
from PIL import Image

try:
    from photo_meta_organizer.constant.constant import DST_DIR, SRC_DIR
except ImportError:
    SRC_DIR = "/Volumes/Photo_Source"
    DST_DIR = "/Volumes/Photo_Dest"

# ================= 配置区域 =================
DRY_RUN = False  # True=演习, False=实战
SOURCE_DIR = Path(SRC_DIR)
TARGET_DIR = Path(DST_DIR)

# 扩展名定义 (已包含 .mpg)
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.tiff', '.cr3', '.arw', '.bmp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.3gp', '.mpg', '.mpeg', 'vob'}
VALID_EXTENSIONS = set(IMAGE_EXTENSIONS | VIDEO_EXTENSIONS)


# ===========================================

def extract_location_info(folder_name):
    """提取文件夹名中的中文"""
    matches = re.findall(r'[\u4e00-\u9fa5]+', folder_name)
    return "".join(matches) if matches else ""


def get_date_taken(path):
    """获取时间"""
    is_image = path.suffix.lower() in IMAGE_EXTENSIONS
    if is_image:
        try:
            img = Image.open(path)
            exif_data = img._getexif()
            if exif_data and 36867 in exif_data:
                return datetime.strptime(exif_data[36867], '%Y:%m:%d %H:%M:%S')
        except Exception:
            pass
    return datetime.fromtimestamp(os.path.getmtime(path))


def get_unique_path(path):
    """防重名"""
    if not path.exists(): return path
    counter = 1
    while True:
        new_path = path.parent / f"{path.stem}_{counter}{path.suffix}"
        if not new_path.exists(): return new_path
        counter += 1


def organize():
    print(f"🚀 任务启动 | 模式: {'[演习]' if DRY_RUN else '[实战]'}")
    print(f"📂 源目录: {SOURCE_DIR}")
    print("-" * 40)

    if not SOURCE_DIR.exists():
        print("❌ 源目录不存在")
        return

    count_success = 0
    count_skip = 0
    files_processed_ok = 0  # 专门记录处理成功的文件数，用于采样打印

    # 遍历
    for file_path in SOURCE_DIR.rglob('*'):
        if not file_path.is_file(): continue

        # 1. 警告保留: 系统垃圾 (全量打印，方便确认)
        if file_path.name.startswith('.') or file_path.name == '.DS_Store':
            print(f"🗑️ [跳过] 系统文件: {file_path.name}")
            count_skip += 1
            continue

        # 2. 警告保留: 格式不支持 (全量打印，一定要看!)
        if file_path.suffix.lower() not in VALID_EXTENSIONS:
            print(f"⚠️ [跳过] 格式不支持: {file_path.name} ({file_path.parent.name})")
            count_skip += 1
            continue

        # 3. 正常流程
        try:
            files_processed_ok += 1

            # 判断是否需要打印 (第一条 或 每20条)
            should_print = (files_processed_ok == 1) or (files_processed_ok % 20 == 0)

            # --- 核心逻辑 ---
            date_obj = get_date_taken(file_path)
            year_str = str(date_obj.year)
            month_val = date_obj.month

            loc = extract_location_info(file_path.parent.name) or extract_location_info(file_path.parent.parent.name)
            suffix = f" {loc}" if loc else ""

            decade = '1979-' if date_obj.year <= 1979 else f"{(date_obj.year // 10) * 10}+"
            target_folder = TARGET_DIR / decade / year_str / f"{year_str}-{month_val}{suffix}"
            target_path = target_folder / file_path.name

            if DRY_RUN:
                # 演习模式
                final_path = target_path
                note = ""
                if final_path.exists():
                    final_path = get_unique_path(final_path)
                    note = " [需重命名]"

                # 采样打印
                if should_print:
                    print(f"[演习] ({files_processed_ok}) .../{final_path.parent.name}/{final_path.name}{note}")

            else:
                # 实战模式
                target_folder.mkdir(parents=True, exist_ok=True)

                if target_path.exists() and file_path.resolve() == target_path.resolve():
                    print(f"⏩ [跳过] 原地不动: {file_path.name}")
                    count_skip += 1
                    continue

                if target_path.exists():
                    target_path = get_unique_path(target_path)

                shutil.move(str(file_path), str(target_path))

                # 采样打印
                if should_print:
                    print(f"✅ [成功] ({files_processed_ok}) {file_path.name}")

            count_success += 1

        except Exception as e:
            # 错误信息必须打印
            print(f"❌ [错误] {file_path.name}: {e}")
            count_skip += 1

    print("-" * 40)
    print(f"🏁 结束. 成功处理: {count_success}, 跳过/异常: {count_skip}")


if __name__ == '__main__':
    organize()