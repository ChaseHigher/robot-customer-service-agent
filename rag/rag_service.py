"""
总结服务类：用户提问，搜索参考资料，将提问予参考资料提交给模型，让模型总结回复
"""
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser

from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompt
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model
from utils.citations import make_evidence


def print_prompt(prompt):
    print("\n", "-"*20, "\n", prompt.to_string(), "\n", "-"*20, "\n")
    return prompt

class RagSummarizeService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriever = self.vector_store.get_retriever()
        self.prompt_text = load_rag_prompt()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()

    def _init_chain(self):
        chain = self.prompt_template | print_prompt | self.model | StrOutputParser()
        return chain

    def retriever_docs(self, query: str) -> list[Document]:
        return self.retriever.invoke(query)

    def rag_summarize(self, query: str) -> dict:
        context_docs = self.retriever_docs(query)
        evidence = {}
        for doc in context_docs:
            if doc.page_content.strip():
                item = make_evidence(doc)
                evidence[item["id"]] = item
        sources = list(evidence.values())
        if not sources:
            return {"status": "no_evidence", "summary": "未检索到有效资料，无法根据知识库确认。", "sources": []}
        context = "\n\n".join(
            f"[证据:{item['id']}] 文件：{item['source']}；页码：{item['page'] or '未提供'}\n原文：{item['text']}"
            for item in sources
        )

        summary = self.chain.invoke(
            {
                "input": query,
                "context": context,
             }
        )
        return {"status": "success", "summary": summary, "sources": sources}


if __name__ == "__main__":
    rag = RagSummarizeService()
    print(rag.rag_summarize("小户型适合什么扫地机器人"))
