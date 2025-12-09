import os
import re
import piexif
from pathlib import Path
from datetime import datetime

try:
    from photo_meta_organizer.constant.constant import FIX_DIR
except ImportError:
    print(f"⚠️ Warning: Could not import FIX_DIR. using manual path.")
    FIX_DIR = "/Volumes/photo_backup/Scanning"

# ================= 配置区域 =================
DRY_RUN = True  # ⚠️ 记得测完后改成 False
# 修复扫描老照片的脚本, 老照片必须人为放入对应目录中, 目录结构为 2000+/2005/2005-3/)
TARGET_ROOT = Path(FIX_DIR)
VALID_EXTENSIONS = {'.jpg', '.jpeg'}


# ===========================================

def parse_date_from_path(file_path):
    """
    逻辑不变：从路径提取年、月
    """
    parent = file_path.parent.name
    grandparent = file_path.parent.parent.name

    # 策略 1: 强特征 "2023-5" / "2023 05"
    match = re.search(r'(\d{4})[-.\s]+(\d{1,2})', parent)
    if match:
        return int(match.group(1)), int(match.group(2))

    # 策略 2: 纯年份目录 "2023" -> 1月
    if parent.isdigit() and len(parent) == 4:
        return int(parent), 1

    # 策略 3: 年/月 结构 "2000/2"
    if parent.isdigit() and len(parent) <= 2:
        if grandparent.isdigit() and len(grandparent) == 4:
            return int(grandparent), int(parent)

    return None, None


def update_exif_and_file_time(file_path, year, month):
    # 1. 构造时间字符串 (EXIF 格式)
    date_str = f"{year}:{month:02d}:26 12:00:00"

    # 2. 构造时间戳 (用于修改文件系统时间)
    # 将字符串转为 datetime 对象，再转为 timestamp float
    dt_obj = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    unix_ts = dt_obj.timestamp()

    if DRY_RUN:
        print(f"[演习] {file_path.name}")
        print(f"      -> EXIF 写入: {date_str}")
        print(f"      -> 系统 修改时间: {dt_obj}")
        return True

    try:
        # --- A. 修改 EXIF 数据 (内容层) ---
        try:
            exif_dict = piexif.load(str(file_path))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        # 关键修改：同时写入三个地方，确保万无一失
        # 1. ExifIFD: 拍摄时间 (最标准)
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_str
        # 2. ExifIFD: 数字化时间
        exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_str
        # 3. 0th IFD: 图像时间 (Finder 和 缩略图经常看这个!)
        exif_dict['0th'][piexif.ImageIFD.DateTime] = date_str

        # 移除缩略图防止数据不一致报错
        exif_dict.pop("thumbnail", None)

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(file_path))

        # --- B. 修改文件系统时间 (物理层) ---
        # os.utime(path, (访问时间, 修改时间))
        os.utime(str(file_path), (unix_ts, unix_ts))

        print(f"✅ [成功] {file_path.name} -> {date_str}")
        return True

    except Exception as e:
        print(f"❌ [失败] {file_path.name}: {e}")
        return False


def run_fix():
    print(f"🔧 全面修复启动 (Exif + 系统时间) | 模式: {'[DRY RUN]' if DRY_RUN else '[LIVE]'}")
    print(f"📂 目标: {TARGET_ROOT}")

    if not TARGET_ROOT.exists():
        print(f"❌ 目录不存在: {TARGET_ROOT}")
        return

    count = 0

    for file_path in TARGET_ROOT.rglob('*'):
        if not file_path.is_file(): continue
        if file_path.suffix.lower() not in VALID_EXTENSIONS: continue

        year, month = parse_date_from_path(file_path)

        if year and month:
            if 1900 < year < 2030 and 1 <= month <= 12:
                update_exif_and_file_time(file_path, year, month)
                count += 1
            else:
                pass  # 日期不合理忽略

    print("-" * 40)
    print(f"🏁 结束. 处理: {count} 张")


if __name__ == '__main__':
    run_fix()