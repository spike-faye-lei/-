"""简历文件解析：按扩展名提取文本，支持 PDF / DOCX / TXT / MD"""
import os


def extract_text(file_path: str) -> str:
    """按文件扩展名提取文本，返回纯文本内容"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return _extract_pdf(file_path)
    if ext == ".docx":
        return _extract_docx(file_path)
    if ext in (".txt", ".md"):
        return _extract_txt(file_path)
    raise ValueError(f"不支持的文件格式：{ext}，请上传 PDF/DOCX/TXT 文件")


def _extract_pdf(file_path: str) -> str:
    """用 pypdf 提取全部页文本；扫描件无文本层时给出明确提示"""
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if not text:
        return "PDF 为扫描件，无法提取文本"
    return text


def _extract_docx(file_path: str) -> str:
    """用 python-docx 提取段落文本"""
    import docx

    doc = docx.Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs).strip()


def _extract_txt(file_path: str) -> str:
    """读取纯文本，utf-8 优先，失败回退 gbk"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="gbk") as f:
            return f.read().strip()
