"""pytest 公共配置：把项目根目录加入 sys.path，保证 tests/ 外也能 import 项目模块"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
