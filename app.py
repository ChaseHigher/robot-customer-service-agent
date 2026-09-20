import streamlit as st

from agent.react_agent import ReactAgent
from utils.location_component import render_location_picker
from storage.chat_store import (
    init_db,
    create_conversation,
    list_conversations,
    load_messages,
    save_message,
    rename_conversation,
    delete_conversation,
)


# 运行命令：python -m streamlit run app.py

st.title("智扫通机器人智能客服")
st.divider()
current_browser_location = render_location_picker()

# 创建数据库和表；重复执行不会清空已有记录
init_db()

if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()


# ---------- 新建与选择对话 ----------

if st.sidebar.button("新建对话"):
    st.session_state["selected_conversation"] = create_conversation()
    st.rerun()

conversations = list_conversations()

# 第一次使用，没有任何对话时，创建一个
if not conversations:
    st.session_state["selected_conversation"] = create_conversation()
    conversations = list_conversations()

# 列表生成式
# [要放进新列表的内容 for 变量 in 原列表]
conversation_ids = [item["id"] for item in conversations]

# 重新打开页面时默认选择最新创建的对话
if (
    st.session_state.get("selected_conversation") not in conversation_ids
):
    st.session_state["selected_conversation"] = conversation_ids[0]

# 标题按行显示；样式只作用于历史列表中的会话按钮。
st.markdown("""
<style>
[class*="st-key-history_open_"] button {
    justify-content: flex-start; border: none; box-shadow: none;
}
[class*="st-key-history_open_"] button p {
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    text-align: left;
}
[class*="st-key-history_open_"] button[kind="secondary"] {
    background: transparent;
}
[class*="st-key-history_open_"] button:hover {
    background: rgba(128,128,128,0.15);
}
</style>
""", unsafe_allow_html=True)

st.sidebar.caption("最近")
for conversation in conversations:
    conversation_id = conversation["id"]
    with st.sidebar.container():
        title_column, menu_column = st.columns([5, 1], gap="small")
        with title_column:
            if st.button(
                conversation["title"],
                key=f"history_open_{conversation_id}",
                help=conversation["title"],
                use_container_width=True,
                type="primary" if conversation_id == st.session_state["selected_conversation"] else "secondary",
            ):
                st.session_state["selected_conversation"] = conversation_id
                st.rerun()
        with menu_column:
            with st.popover("⋯", help="对话操作"):
                st.caption(conversation["title"])
                with st.form(f"rename_{conversation_id}"):
                    new_title = st.text_input(
                        "重命名", value=conversation["title"], max_chars=100,
                    )
                    if st.form_submit_button("保存名称"):
                        try:
                            rename_conversation(conversation_id, new_title)
                        except ValueError as error:
                            st.error(str(error))
                        else:
                            st.rerun()
                st.divider()
                confirm_delete = st.checkbox(
                    "确认删除此对话及全部消息（不可恢复）",
                    key=f"confirm_delete_{conversation_id}",
                )
                if st.button(
                    "删除对话", key=f"delete_{conversation_id}",
                    disabled=not confirm_delete,
                ):
                    delete_conversation(conversation_id)
                    if st.session_state["selected_conversation"] == conversation_id:
                        st.session_state.pop("selected_conversation", None)
                    st.rerun()

session_id = st.session_state["selected_conversation"]


# ---------- 读取并显示当前会话 ----------

# 数据库成为聊天记录的统一来源
messages = load_messages(session_id)

def render_sources(sources):
    for source in sources:
        page_label = f" · 第 {source['page']} 页" if source.get("page") is not None else ""
        with st.expander(f"[{source['number']}] {source['source']}{page_label}"):
            st.caption(f"片段 ID：{source['id']} · 检索时原文快照")
            st.text(source["text"])


for message in messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        render_sources(message.get("sources", []))


# ---------- 处理新问题 ----------

prompt = st.chat_input("请输入你的问题")

if prompt:
    # 先保存用户问题
    save_message(session_id, "user", prompt)
    st.chat_message("user").write(prompt)

    # 从数据库重新读取，包含刚刚保存的问题
    messages = load_messages(session_id)

    def capture(generator):
        for text in generator:
            for char in text:
                yield char

    try:

        # with的用法，下面这段相当于：
        #     st.spinner("智能客服思考中...")    打开
        #     res_stream = st.session_state["agent"].execute_stream(
        #         messages
        #     )   执行
        #     st.spinner("智能客服思考中...")    关闭
        # 也就是说 自动打开资源，并在用完后关闭资源

        with st.spinner("智能客服思考中..."):
            citations = []
            res_stream = st.session_state["agent"].execute_stream(
                messages, location=current_browser_location, citations=citations
            )

            with st.chat_message("assistant"):
                answer = st.write_stream(capture(res_stream))
                render_sources(citations)

    except Exception:
        st.error(
            "本次回答失败。你的问题已经保存，"
            "可以再次输入“请继续回答上一个问题”。"
        )

    else:
        if isinstance(answer, str) and answer.strip():
            save_message(session_id, "assistant", answer, sources=citations)

            # 重新加载消息和侧边栏标题
            st.rerun()
        else:
            st.warning("本次没有生成有效回答，请重新提问。")
