import csv
import os
import re

from langchain_core.tools import tool
from langchain.tools import ToolRuntime
from utils.weather_service import current_location, query_weather
from rag.rag_service import RagSummarizeService
from utils.config_handler import agent_conf
from utils.logger_handler import logger
from utils.path_tool import get_abs_path

rag = RagSummarizeService()

external_data = {}


@tool(description="检索知识库，返回status、summary和sources原文证据。依据资料回答时在结论后保留[证据:id]标记，id必须来自本次sources；无证据时说明无法确认。")
def rag_summarize(query: str, runtime: ToolRuntime) -> dict:
    result = rag.rag_summarize(query)
    # 每次请求独立登记真实证据，不使用模型编造的来源或跨会话缓存。
    registry = runtime.context["evidence"]
    for item in result["sources"]:
        registry[item["id"]] = item
    return result


@tool(description="查询当前天气。用户指定城市时传city；查询用户当前位置时city留空，程序使用浏览器授权坐标。若重名则请用户确认候选地点，再传返回的location_id。只报告success结果，注明数据时间、单位和Open-Meteo来源，不得编造AQI或降雨概率。")
def get_weather(runtime: ToolRuntime, city: str = "", location_id: int | None = None) -> dict:
    return query_weather(city, (runtime.context or {}).get("location"), location_id)


@tool(description="读取浏览器授权位置及BigDataCloud解析的city城市名，无需模型传参数。优先回答城市名，不主动输出坐标。city为空时请重新定位或手动提供城市，不得猜测。未授权或过期时请点击侧边栏获取当前位置。成功后用空city调用get_weather以原坐标查询当地天气。")
def get_user_location(runtime: ToolRuntime) -> dict:
    return current_location((runtime.context or {}).get("location"))


def generate_external_data():
    """
    {
        "user_id":
        {
            "month": {"特征": XXX, "效率": XXX, ...},
            "month": {"特征": XXX, "效率": XXX, ...},
            "month": {"特征": XXX, "效率": XXX, ...},
            ...
        },
        "user_id":
        {
            "month": {"特征": XXX, "效率": XXX, ...},
            "month": {"特征": XXX, "效率": XXX, ...},
            "month": {"特征": XXX, "效率": XXX, ...},
            ...
        },
        ...
    }
    :return:
    """
    if not external_data:
        loaded_data = {}
        external_data_path = get_abs_path(agent_conf["external_data_path"])
        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件{external_data_path}不存在")
        # newline="" 让 csv 正确处理带引号字段中的换行；utf-8-sig 兼容 BOM。
        with open(external_data_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, strict=True)
            required_fields = ("用户ID", "特征", "清洁效率", "耗材", "对比", "时间")
            missing_fields = set(required_fields) - set(reader.fieldnames or [])
            if missing_fields:
                raise ValueError(f"使用记录 CSV 缺少必要列：{', '.join(sorted(missing_fields))}")

            for row in reader:
                # 多余的数据列或缺失字段通常意味着文件格式有误，不继续生成报告。
                if None in row:
                    raise ValueError(f"使用记录 CSV 第 {reader.line_num} 行存在多余字段")
                empty_fields = [name for name in required_fields if not (row.get(name) or "").strip()]
                if empty_fields:
                    raise ValueError(
                        f"使用记录 CSV 第 {reader.line_num} 行缺少有效值：{', '.join(empty_fields)}"
                    )

                user_id = row["用户ID"].strip()
                feature = row["特征"]
                efficiency = row["清洁效率"]
                consumables = row["耗材"]
                comparison = row["对比"]
                time = row["时间"].strip()

                if user_id not in loaded_data:
                    loaded_data[user_id] = {}

                loaded_data[user_id][time] = {
                    "特征": feature,
                    "效率": efficiency,
                    "耗材": consumables,
                    "对比": comparison,
                }
        # 全部读取成功后才更新缓存，避免读取失败留下不完整数据。
        external_data.update(loaded_data)


@tool(description=(
    "查询用户指定月份的使用记录。"
    "必须同时提供 user_id 和 month；"
    "user_id 为用户ID，month 格式为 YYYY-MM，例如 2025-09。"
    "两个参数必须来自当前对话中用户明确提供的信息，不得猜测或使用示例值。"
    "缺少参数时先向用户追问，不调用本工具；中文年月先转换为YYYY-MM。"
    "返回status、user_id、month、data和message；仅status为success时可生成报告。"
))
def fetch_external_data(user_id: str, month: str) -> dict:
    user_id = user_id.strip()
    month = month.strip()
    result = {
        "status": "invalid_parameters",
        "user_id": user_id,
        "month": month,
        "data": None,
        "message": "",
    }
    errors = []
    if not re.fullmatch(r"[0-9]+", user_id):
        errors.append("请提供由数字组成的用户 ID。")
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month) or month.startswith("0000-"):
        errors.append("请提供完整且有效的报告年月，格式为 YYYY-MM。")
    if errors:
        result["message"] = " ".join(errors)
        return result

    try:
        generate_external_data()
    except Exception:
        logger.exception("[fetch_external_data]使用记录读取失败")
        result.update(status="error", message="使用记录读取失败，请稍后重试；不要生成报告。")
        return result

    record = external_data.get(user_id, {}).get(month)
    if record is None:
        logger.warning(f"[fetch_external_data]未能检索到用户：{user_id}在{month}中的使用记录数据")
        result.update(status="not_found", message=f"用户 {user_id} 在 {month} 暂无使用记录，请核对用户 ID 和月份。")
        return result

    result.update(status="success", data=record.copy(), message="查询成功。")
    return result


@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    return "fill_context_for_report已调用"
