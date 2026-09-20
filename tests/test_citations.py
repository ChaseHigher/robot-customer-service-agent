"""离线验证引用和存储，不调用模型、不修改项目数据库。

运行：python -m unittest discover -s tests -v
"""
import ast
from contextlib import closing
import importlib.util
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utils.citations import make_evidence, finalize_citations


def load_class(relative, name, namespace):
    # 只加载被测类，避开原模块导入时创建模型和向量库的副作用。
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8-sig"))
    node = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), relative, "exec"), namespace)
    return namespace[name]


def document(text="定期清理边刷", source="维护.txt", page=None):
    return SimpleNamespace(page_content=text, metadata={"source": source, "page": page})


class CitationTests(unittest.TestCase):
    def test_source_metadata_and_identity(self):
        pdf = make_evidence(document(source=r"E:\data\手册.pdf", page=0))
        self.assertEqual((pdf["source"], pdf["page"]), ("手册.pdf", 1))
        self.assertIsNone(make_evidence(document(page=0))["page"])
        self.assertIsNone(make_evidence(document(source="手册.pdf"))["page"])
        self.assertEqual(make_evidence(document())["id"], make_evidence(document())["id"])
        self.assertNotEqual(make_evidence(document())["id"], make_evidence(document("另一段"))["id"])

    def test_citation_numbering_and_unknown_sources(self):
        first, second = make_evidence(document()), make_evidence(document("检查滤网"))
        registry = {item["id"]: item for item in (first, second)}
        answer, sources = finalize_citations(
            f"甲[证据:{second['id']}]乙[证据:{first['id']}]丙[证据:{second['id']}]", registry
        )
        self.assertEqual(answer, "甲[1]乙[2]丙[1]")
        self.assertEqual([s["id"] for s in sources], [second["id"], first["id"]])
        answer, sources = finalize_citations("建议[证据:fake]另一条[9]", registry)
        self.assertEqual(sources, [])
        self.assertIn("来源未核实", answer)
        self.assertNotIn("[9]", answer)
        self.assertIn("未提供有效", finalize_citations("未引用", registry)[0])
        self.assertEqual(finalize_citations("你好", {}), ("你好", []))

    def test_rag_preserves_original_evidence_and_empty_retrieval(self):
        cls = load_class("rag/rag_service.py", "RagSummarizeService", {
            "Document": SimpleNamespace, "make_evidence": make_evidence,
        })
        service = cls.__new__(cls)
        doc = document()
        service.retriever = SimpleNamespace(invoke=lambda query: [doc, doc])
        seen = []
        service.chain = SimpleNamespace(invoke=lambda inputs: seen.append(inputs) or "概括")
        result = service.rag_summarize("边刷如何保养")
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["text"], doc.page_content)
        self.assertIn(result["sources"][0]["id"], seen[0]["context"])
        service.retriever = SimpleNamespace(invoke=lambda query: [])
        self.assertEqual(service.rag_summarize("未知")["status"], "no_evidence")
        self.assertEqual(len(seen), 1)

    def test_agent_request_isolation_and_final_output(self):
        cls = load_class("agent/react_agent.py", "ReactAgent", {"finalize_citations": finalize_citations})
        agent = cls.__new__(cls)
        evidence = make_evidence(document())
        inputs = []
        def stream(data, stream_mode, context):
            inputs.append(data)
            self.assertEqual(context["evidence"], {})
            context["evidence"][evidence["id"]] = evidence
            yield {"messages": data["messages"]}
            message = SimpleNamespace(type="ai", tool_calls=[], content=f"建议[证据:{evidence['id']}]")
            yield {"messages": data["messages"] + [message]}
            yield {"messages": data["messages"] + [message]}
        agent.agent = SimpleNamespace(stream=stream)
        history = [{"role": "user", "content": "问题", "sources": []}]
        for _ in range(2):
            citations = []
            self.assertEqual(list(agent.execute_stream(history, citations=citations)), ["建议[1]"])
            self.assertEqual(citations[0]["text"], evidence["text"])
        self.assertNotIn("sources", inputs[0]["messages"][0])
        agent.agent = SimpleNamespace(stream=lambda *args, **kwargs: iter([{"messages": history}]))
        self.assertEqual(list(agent.execute_stream(history)), [])

    def test_old_database_migration_and_source_roundtrip(self):
        spec = importlib.util.spec_from_file_location("citation_test_store", ROOT / "storage/chat_store.py")
        store = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(store)
        with tempfile.TemporaryDirectory() as directory:
            store.DB_PATH = Path(directory) / "history.sqlite3"
            with closing(sqlite3.connect(store.DB_PATH)) as db, db:
                db.executescript("""
                    CREATE TABLE conversations (id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                    CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT);
                    INSERT INTO conversations(id,title) VALUES ('old','旧对话');
                    INSERT INTO messages(session_id,role,content) VALUES ('old','assistant','旧回答');
                """)
            store.init_db()
            store.init_db()
            self.assertEqual(store.load_messages("old")[0]["sources"], [])
            session = store.create_conversation()
            sources = [{**make_evidence(document()), "number": 1}]
            store.save_message(session, "assistant", "建议[1]", sources=sources)
            self.assertEqual(store.load_messages(session)[0], {"role": "assistant", "content": "建议[1]", "sources": sources})
            self.assertTrue(store.list_conversations())

    def test_real_langchain_tool_runtime(self):
        try:
            from langchain.agents import create_agent
            from langchain.tools import ToolRuntime
            from langchain_core.tools import tool
            from langchain_core.messages import AIMessage
            from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
        except ImportError:
            self.skipTest("需要安装项目的 LangChain 依赖")

        class OfflineModel(FakeMessagesListChatModel):
            def bind_tools(self, tools, **kwargs):
                return self

        item = make_evidence(document())
        service = SimpleNamespace(rag_summarize=lambda query: {
            "status": "success", "summary": f"建议[证据:{item['id']}]", "sources": [item],
        })
        tree = ast.parse((ROOT / "agent/tools/agent_tools.py").read_text(encoding="utf-8-sig"))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "rag_summarize")
        namespace = {"tool": tool, "ToolRuntime": ToolRuntime, "rag": service}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "agent_tools.py", "exec"), namespace)
        rag_tool = namespace["rag_summarize"]
        self.assertNotIn("runtime", rag_tool.tool_call_schema.model_fields)
        model = OfflineModel(responses=[
            AIMessage(content="", tool_calls=[{"name": "rag_summarize", "args": {"query": "边刷"}, "id": "lookup1", "type": "tool_call"}]),
            AIMessage(content=f"定期清理边刷[证据:{item['id']}]"),
        ])
        cls = load_class("agent/react_agent.py", "ReactAgent", {"finalize_citations": finalize_citations})
        agent = cls.__new__(cls)
        agent.agent = create_agent(model=model, tools=[rag_tool])
        sources = []
        answer = list(agent.execute_stream([{"role": "user", "content": "边刷如何保养"}], citations=sources))
        self.assertEqual(answer, ["定期清理边刷[1]"])
        self.assertEqual(sources[0]["text"], item["text"])


if __name__ == "__main__":
    unittest.main()
