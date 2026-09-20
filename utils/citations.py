"""从检索文档生成证据，并将模型引用转换成经过校验的展示编号。"""
import hashlib
import json
import re


def make_evidence(document):
    metadata = document.metadata
    source = str(metadata.get("source") or "来源未标注")
    # 兼容已有向量库的 Windows/Linux 路径，只向页面展示文件名。
    filename = source.replace("\\", "/").rsplit("/", 1)[-1]
    raw_page = metadata.get("page")
    page = raw_page + 1 if filename.lower().endswith(".pdf") and type(raw_page) is int and raw_page >= 0 else None
    identity = json.dumps(
        [source, raw_page, metadata.get("start_index"), document.page_content],
        ensure_ascii=False, default=str,
    )
    chunk_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return {
        "id": chunk_id, "source": filename, "page": page,
        "text": document.page_content,
    }


def finalize_citations(answer, evidence):
    """只接受本轮检索登记的证据；编号有效不等于已经验证语义支持。"""
    cited = []
    numbers = {}
    invalid = False

    def replace(match):
        nonlocal invalid
        evidence_id = match.group(1)
        if evidence_id not in evidence:
            invalid = True
            return "（来源未核实）"
        if evidence_id not in numbers:
            numbers[evidence_id] = len(cited) + 1
            cited.append({**evidence[evidence_id], "number": numbers[evidence_id]})
        return f"[{numbers[evidence_id]}]"

    # 模型只能生成内部证据标记，不能自行生成展示编号。
    answer = re.sub(r"\[(\d+)\](?!\()", "（来源未核实）", answer)
    answer = re.sub(r"\[证据[:：]\s*([^\]]+)\]", replace, answer)
    if invalid:
        answer += "\n\n注：部分引用未能对应本次检索资料，相关内容请核实。"
    if evidence and not cited:
        answer += "\n\n注：本次回答未提供有效的知识库引用，依据尚待核对。"
    return answer, cited
