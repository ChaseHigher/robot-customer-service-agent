"""Run from the project root: python init_knowledge.py."""
from rag.vector_store import VectorStoreService


def main():
    service = VectorStoreService()
    service.load_document()
    if not service.vector_store.get(limit=1)["ids"]:
        raise RuntimeError("知识库为空，请检查模型密钥、网络、data 目录和 logs 日志。")
    print("知识库已就绪，可以运行：python -m streamlit run app.py")


if __name__ == "__main__":
    main()
