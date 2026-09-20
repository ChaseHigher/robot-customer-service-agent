"""真实位置和天气查询；不依赖模型、不使用固定天气作为降级结果。"""
import json
import math
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request_json(url, params):
    request = Request(url + "?" + urlencode(params), headers={"User-Agent": "RobotAssistant/1.0"})
    with urlopen(request, timeout=15) as response:
        data = json.load(response)
    if not isinstance(data, dict) or data.get("error"):
        raise ValueError("天气服务返回异常结果")
    return data


def current_location(location):
    if not isinstance(location, dict) or location.get("status") != "success":
        return {"status": "location_required", "message": "请点击侧边栏“获取当前位置”并授权，或直接提供要查询的城市。"}
    try:
        lat, lon = float(location["latitude"]), float(location["longitude"])
        age = time.time() - float(location["timestamp"]) / 1000
        accuracy = float(location["accuracy"])
        if not all(map(math.isfinite, [lat, lon, age, accuracy])) or not (-90 <= lat <= 90 and -180 <= lon <= 180) or accuracy < 0:
            raise ValueError()
        if not -60 <= age <= 1800:
            return {"status": "location_expired", "message": "定位已超过30分钟，请重新获取当前位置，或指定城市。"}
    except (KeyError, ValueError, TypeError, OverflowError):
        return {"status": "location_required", "message": "定位数据无效，请重新定位或指定城市。"}
    city = location.get("city")
    city = city.strip() if isinstance(city, str) else ""
    return {"status": "success", "latitude": lat, "longitude": lon,
            "city": city, "admin1": location.get("region", ""), "country": location.get("country", ""),
            "city_source": "BigDataCloud" if city else None,
            "accuracy_m": accuracy, "source": "浏览器授权定位", "timestamp": location["timestamp"],
            "message": ("回答当前位置时显示city城市名即可，不主动输出经纬度或街道；城市为定位估计结果。"
                        if city else "已获取坐标但未识别城市，请重新点击定位或提供城市名；不要从坐标猜测城市。")}


WEATHER_CODES = {
    0: "晴", 1: "大部晴朗", 2: "局部多云", 3: "阴天", 45: "雾", 48: "雾凇",
    51: "小毛毛雨", 53: "中毛毛雨", 55: "强毛毛雨", 56: "轻冻毛毛雨", 57: "强冻毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "轻冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒", 80: "小阵雨", 81: "中阵雨",
    82: "强阵雨", 85: "小阵雪", 86: "强阵雪", 95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
}


def query_weather(city="", location=None, location_id=None):
    """有城市时查询城市，否则使用当前浏览器坐标；重名地点先返回候选。"""
    try:
        if location_id is not None:
            place = request_json("https://geocoding-api.open-meteo.com/v1/get", {"id": location_id, "language": "zh"})
        elif city.strip():
            city = city.strip()
            places = request_json("https://geocoding-api.open-meteo.com/v1/search", {
                "name": city, "count": 5, "language": "zh", "format": "json",
            }).get("results", [])
            if not places:
                return {"status": "not_found", "message": "未找到该城市，请提供城市名称（可尝试去掉“市”字或使用拼音）。"}
            if len(places) > 1:
                return {"status": "ambiguous", "message": "找到多个地点，请用户确认省份或国家；确认后使用对应location_id查询。不要擅自选取。",
                        "candidates": [{k: p.get(k) for k in ("id", "name", "admin1", "country")} for p in places]}
            place = places[0]
        else:
            place = current_location(location)
            if place["status"] != "success":
                return place
            place = {**place, "name": place.get("city") or "浏览器当前位置（城市未识别）"}

        latitude, longitude = float(place["latitude"]), float(place["longitude"])
        data = request_json("https://api.open-meteo.com/v1/forecast", {
            "latitude": latitude, "longitude": longitude, "timezone": "auto",
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
            "wind_speed_unit": "kmh", "forecast_days": 1,
        })
        current = data["current"]
        if current.get("temperature_2m") is None or not current.get("time"):
            raise ValueError("缺少当前天气数据")
        return {
            "status": "success", "source": "Open-Meteo", "source_url": "https://open-meteo.com/",
            "data_kind": "气象模型当前估算，非现场传感器实测", "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "location": {k: place.get(k) for k in ("name", "admin1", "country", "latitude", "longitude")},
            "timezone": data.get("timezone"), "data_time": current["time"],
            "weather": WEATHER_CODES.get(current.get("weather_code"), "天气状况代码未知"),
            "current": current, "units": data.get("current_units", {}),
            "message": "当前位置优先显示location.name城市名，不主动显示经纬度。仅报告返回指标及单位，注明数据时间和来源。未查询AQI或未来降雨概率，不得编造。",
        }
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {"status": "error", "message": "天气服务暂时无法访问或返回数据不完整，请稍后重试。不能用固定或历史天气代替当前数据。", "error_type": type(error).__name__}
