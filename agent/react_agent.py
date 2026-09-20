from langchain.agents import create_agent
from model.factory import chat_model
from utils.prompt_loader import load_system_prompt
from agent.tools.agent_tools import (rag_summarize, get_weather, get_user_location,
                                     fetch_external_data, fill_context_for_report)
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch
from utils.citations import finalize_citations


class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompt(),
            tools=[rag_summarize, get_weather, get_user_location,
                   fetch_external_data, fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
        )

    def execute_stream(self, messages: list[dict], location: dict | None = None, citations: list | None = None):
        input_dict = {
            "messages": [{"role": message["role"], "content": message["content"]} for message in messages]
        }

        if citations is not None:
            citations.clear()
        context = {"report": False, "location": location, "evidence": {}}
        latest_message = None
        # 等本轮执行完成后统一校验引用，避免未校验的编号提前显示或重复输出。
        for chunk in self.agent.stream(input_dict, stream_mode="values", context=context):
            state_messages = chunk.get("messages", [])
            latest_message = state_messages[-1] if len(state_messages) > len(messages) else None
        if (
            latest_message is not None
            and latest_message.type == "ai"
            and not getattr(latest_message, "tool_calls", None)
            and isinstance(latest_message.content, str)
            and latest_message.content.strip()
        ):
            answer, sources = finalize_citations(latest_message.content, context["evidence"])
            if citations is not None:
                citations.extend(sources)
            yield answer


if __name__ == "__main__":
    agent = ReactAgent()
    messages = [
        {"role": "user", "content": "给我生成我的使用报告"}
    ]

    for chunk in agent.execute_stream(messages):
        print(chunk, end="", flush=True)
