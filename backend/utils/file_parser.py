"""文件解析工具 - 提取 PDF/DOCX/TXT 等文件中的文本内容"""
from pathlib import Path
from typing import Optional
from loguru import logger


def parse_file_to_text(file_path: str) -> str:
    """将文件内容提取为纯文本

    支持格式:
    - PDF: PyPDF2
    - DOCX: python-docx
    - MD / TXT / PY / JSON / YAML / JS / TS / HTML / CSS: 直接读取
    - 其他格式: 尝试直接读取，二进制文件返回空

    Args:
        file_path: 文件路径

    Returns:
        str: 提取的文本内容
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"File not found: {file_path}")
        return ""

    suffix = path.suffix.lower()

    try:
        if suffix == ".pdf":
            return _parse_pdf(path)
        elif suffix == ".docx":
            return _parse_docx(path)
        elif suffix in _TEXT_EXTENSIONS:
            return path.read_text(encoding="utf-8", errors="ignore")
        else:
            return _try_read_text(path)
    except Exception as e:
        logger.warning(f"Failed to parse file {file_path}: {e}")
        return ""


def _parse_pdf(path: Path) -> str:
    """解析 PDF 文件"""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(path))
        parts = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                parts.append(text)
        content = "\n\n".join(parts).strip()
        logger.info(f"Parsed PDF: {path.name}, {len(reader.pages)} pages, {len(content)} chars")
        return content
    except ImportError:
        logger.warning("PyPDF2 not installed, cannot parse PDF")
        return ""
    except Exception as e:
        logger.warning(f"PDF parse error for {path.name}: {e}")
        return ""


def _parse_docx(path: Path) -> str:
    """解析 DOCX 文件"""
    try:
        from docx import Document
        doc = Document(str(path))
        parts = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                parts.append(text)
        content = "\n".join(parts).strip()
        logger.info(f"Parsed DOCX: {path.name}, {len(parts)} paragraphs, {len(content)} chars")
        return content
    except ImportError:
        logger.warning("python-docx not installed, cannot parse DOCX")
        return ""
    except Exception as e:
        logger.warning(f"DOCX parse error for {path.name}: {e}")
        return ""


def _try_read_text(path: Path) -> str:
    """尝试以文本形式读取文件"""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        return content.strip()
    except Exception:
        return ""


_TEXT_EXTENSIONS = frozenset((
    ".md", ".txt", ".py", ".json", ".yaml", ".yml",
    ".js", ".ts", ".jsx", ".tsx", ".html", ".htm",
    ".css", ".scss", ".less", ".xml", ".csv", ".log",
    ".cfg", ".ini", ".toml", ".env", ".sh", ".bat",
    ".sql", ".rs", ".go", ".java", ".c", ".cpp", ".h",
))
