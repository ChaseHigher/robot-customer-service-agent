import hashlib
import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from utils.logger_handler import logger


def get_file_md5_hex(file_path: str):     # 获取文件的md5的十六进制字符串
    if not os.path.exists(file_path):
        logger.error(f"[md5计算]文件{file_path}不存在")
        return

    if not os.path.isfile(file_path):
        logger.error(f"[md5计算]路径{file_path}不是文件")
        return

    md5_obj = hashlib.md5()

    chunk_size = 4096       # 4KB分片，避免文件过大爆内存
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                md5_obj.update(chunk)
            """
            chunk = f.read(chunk_size):
            while chunk:
                md5_obj.update(chunk)
                chunk = f.read(chunk_size)
            """
            md5_hex = md5_obj.hexdigest()
        return md5_hex
    except Exception as e:
        logger.error(f"计算文件{file_path}md5失败，{str(e)}")
        return None


def listdir_with_allowed_type(path: str, allowed_types: tuple[str, ...]) -> tuple[str, ...]:
    """返回目录内符合后缀要求的真实文件；无效目录明确报错。"""
    files = []

    if not os.path.exists(path):
        raise FileNotFoundError(f"知识库目录不存在：{path}")
    if not os.path.isdir(path):
        raise NotADirectoryError(f"知识库路径不是文件夹：{path}")

    for f in os.listdir(path):
        file_path = os.path.join(path, f)
        if os.path.isfile(file_path) and f.endswith(allowed_types):
            files.append(file_path)

    return tuple(files)


def pdf_loader(file_path: str, passwd=None) -> list[Document]:
    return PyPDFLoader(file_path, passwd).load()


def text_loader(file_path: str) -> list[Document]:
    return TextLoader(file_path, encoding="utf-8").load()
