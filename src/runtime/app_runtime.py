import glob
import logging
import os
import shutil
import sys

from dotenv import load_dotenv


def resolve_project_root(start_path=None):
    """从当前文件向上查找项目根目录。"""
    path = os.path.abspath(start_path or __file__)
    if os.path.isfile(path):
        path = os.path.dirname(path)

    while True:
        if os.path.isdir(os.path.join(path, 'src')):
            return path

        parent = os.path.dirname(path)
        if parent == path:
            return os.getcwd()
        path = parent


def bootstrap_project_path():
    """加载环境变量并确保项目根目录在 Python 路径中。"""
    load_dotenv()
    project_root = resolve_project_root()

    if not os.path.exists(os.path.join(project_root, 'src')):
        print("❌ 无法找到src目录，请检查项目结构")
        print(f"📁 当前工作目录: {os.getcwd()}")
        print(f"📁 计算的project_root: {project_root}")
        sys.exit(1)

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    print(f"✅ 项目根目录: {project_root}")
    return project_root


def setup_logging(project_root=None):
    """配置日志系统。"""
    root = project_root or resolve_project_root()
    log_dir = os.path.join(root, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    log_file = os.path.join(log_dir, 'main.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ],
        force=True
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    logging.getLogger('ccxt').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    for name in list(logging.root.manager.loggerDict):
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.handlers = root_logger.handlers[:]
            logger.propagate = False

    print(f"✅ 日志配置完成，日志文件: {log_file}")


def clear_previous_data(project_root=None):
    """清除之前的数据和日志。"""
    root = project_root or resolve_project_root()
    print("🧹 清理之前的数据...")

    for dirname in ("logs", "reports"):
        directory = os.path.join(root, dirname)
        if os.path.exists(directory):
            try:
                preserved_files = set()
                main_log_file = os.path.join(directory, 'main.log')
                if os.path.exists(main_log_file):
                    backup_log_file = os.path.join(directory, 'main_backup.log')
                    shutil.copy2(main_log_file, backup_log_file)
                    preserved_files.add(os.path.abspath(backup_log_file))
                    print(f"✅ 备份日志文件: {backup_log_file}")

                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)
                    if os.path.abspath(item_path) in preserved_files:
                        continue
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)

                print(f"✅ 清理 {dirname} 目录内容完成")
            except Exception as exc:
                print(f"⚠️ 清理 {dirname} 目录失败: {exc}")

        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ 确保 {dirname} 目录存在")
        except Exception as exc:
            print(f"⚠️ 创建 {dirname} 目录失败: {exc}")

    for pattern in ("*.log", "*.tmp", "*.cache"):
        try:
            for file_path in glob.glob(os.path.join(root, pattern)):
                if os.path.dirname(file_path) == os.path.join(root, 'logs'):
                    continue
                os.remove(file_path)
                print(f"✅ 删除临时文件: {file_path}")
        except Exception:
            pass

    print("🧹 数据清理完成")
