import shutil
from pathlib import Path
from datetime import datetime

from photo_meta_organizer.constant.constant import ROOT_DIR

# --- 核心配置 ---
# 只有小于等于这个体积的文件才会被移走 (单位: MB)
# 0.5 MB = 512 KB.
SIZE_THRESHOLD_MB = 0.01

# 目标目录 (请务必确认这个路径是正确的)
TARGET_ROOT_DIR = ROOT_DIR


def get_file_size_mb(file_path: Path) -> float:
    return file_path.stat().st_size / (1024 * 1024)


def clean_small_files_recursive(root_dir: str, dry_run: bool = True):
    root_path = Path(root_dir).resolve()
    junk_path = root_path / "junk"

    if not root_path.exists():
        print(f"❌ 错误: 找不到目录 {root_path}")
        return

    print(f"--- 正在扫描: {root_path} ---")
    print(f"--- 阈值设定: <= {SIZE_THRESHOLD_MB} MB ---\n")

    found_count = 0
    scanned_count = 0

    # [关键修改] 使用 rglob('*') 进行递归扫描 (扫描所有子目录)
    for file_path in root_path.rglob('*'):

        # 排除目录本身，只处理文件
        if not file_path.is_file():
            continue

        # [关键安全锁] 绝对不要扫描 junk 目录里面的东西，防止死循环
        if junk_path in file_path.parents:
            continue

        scanned_count += 1
        size_mb = get_file_size_mb(file_path)

        # [调试日志] 如果你想看它扫描了哪些文件但没选中，取消下面这行的注释
        # print(f"[扫描中] {file_path.name} - {size_mb:.4f} MB")

        # 判断大小 (小于等于)
        if size_mb <= SIZE_THRESHOLD_MB:
            found_count += 1

            # 计算目标路径
            target_junk_file = junk_path / file_path.name

            # 防重名逻辑
            if target_junk_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_junk_file = junk_path / f"{file_path.stem}_{timestamp}{file_path.suffix}"

            # 执行/演示
            if dry_run:
                print(f"✅ [发现目标] {file_path.name}")
                print(f"   └─ 路径: {file_path}")
                print(f"   └─ 大小: {size_mb:.4f} MB (将会移动)")
            else:
                try:
                    junk_path.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(target_junk_file))
                    print(f"🚀 [已移动] {file_path.name}")
                except Exception as e:
                    print(f"❌ [失败] 无法移动 {file_path.name}: {e}")

    print(f"\n--- 总结 ---")
    print(f"共扫描文件: {scanned_count} 个")
    print(f"符合条件(<= {SIZE_THRESHOLD_MB} MB): {found_count} 个")

    if scanned_count == 0:
        print("⚠️ 警告: 没有扫描到任何文件。请检查 TARGET_ROOT_DIR 路径是否正确。")


# --- 执行入口 ---
if __name__ == "__main__":
    # 请先确认这里的路径是你的测试路径
    # 例如: "./test_data"
    clean_small_files_recursive(TARGET_ROOT_DIR, dry_run=True)