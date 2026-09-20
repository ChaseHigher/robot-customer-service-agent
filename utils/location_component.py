"""在用户点击后请求浏览器定位，不使用服务器 IP。"""
import streamlit as st


location_picker = st.components.v2.component(
    "robot_browser_location",
    html='<button type="button">获取当前位置</button><p role="status"></p>',
    css='button { padding: 8px 12px; border-radius: 8px; cursor: pointer; color: inherit; background: transparent; border: 1px solid #888; } p { font-size: 13px; }',
    js="""
    export default function(component) {
        const {parentElement, setStateValue} = component;
        const button = parentElement.querySelector('button');
        const status = parentElement.querySelector('p');
        let alive = true;
        let controller;
        button.onclick = () => {
            if (!window.isSecureContext || !navigator.geolocation) {
                setStateValue('location', {status: 'error', message: '定位需要HTTPS或localhost，请直接输入城市查询天气。'});
                return;
            }
            button.disabled = true;
            status.textContent = '正在请求位置，请在浏览器中允许定位…';
            navigator.geolocation.getCurrentPosition(
                async position => {
                    if (!alive) return;
                    status.textContent = '正在识别城市…';
                    const location = {
                        status: 'success', latitude: position.coords.latitude,
                        longitude: position.coords.longitude, accuracy: position.coords.accuracy,
                        timestamp: position.timestamp
                    };
                    controller = new AbortController();
                    const timer = setTimeout(() => controller.abort(), 10000);
                    try {
                        const params = new URLSearchParams({
                            latitude: String(location.latitude), longitude: String(location.longitude),
                            localityLanguage: 'zh'
                        });
                        const response = await fetch('https://api.bigdatacloud.net/data/reverse-geocode-client?' + params,
                            {signal: controller.signal, credentials: 'omit'});
                        if (!response.ok) throw new Error('City lookup failed');
                        const address = await response.json();
                        // 只接受城市字段，不把村镇或街区误称为城市。
                        location.city = typeof address.city === 'string' ? address.city.trim() : '';
                        location.region = typeof address.principalSubdivision === 'string' ? address.principalSubdivision : '';
                        location.country = typeof address.countryName === 'string' ? address.countryName : '';
                        location.city_source = 'BigDataCloud';
                        if (!location.city) location.city_error = '已获取坐标，但服务未返回城市名。';
                    } catch (error) {
                        location.city_error = '已获取坐标，但城市识别失败，可重试定位；天气查询仍可使用坐标。';
                    } finally {
                        clearTimeout(timer);
                    }
                    if (!alive) return;
                    button.disabled = false;
                    status.textContent = location.city ? '当前城市：' + location.city : location.city_error;
                    setStateValue('location', location);
                },
                error => {
                    if (!alive) return;
                    button.disabled = false;
                    const messages = {1: '未获定位授权，请允许浏览器定位或直接输入城市。', 2: '无法确定位置，请检查系统定位服务或输入城市。', 3: '定位超时，请重试或直接输入城市。'};
                    status.textContent = messages[error.code] || '定位失败，请直接输入城市。';
                    setStateValue('location', {status: 'error', message: status.textContent});
                }, {enableHighAccuracy: false, timeout: 15000, maximumAge: 60000}
            );
        };
        return () => {alive = false; if (controller) controller.abort(); button.onclick = null;};
    }
    """,
)


def render_location_picker():
    with st.sidebar.expander("位置与天气"):
        st.caption("点击后将授权坐标发送至 BigDataCloud 识别城市，并用于天气查询。也可直接在聊天中输入城市。")
        result = location_picker(default={"location": None}, key="browser_location", on_location_change=lambda: None)
        location = result.location
        if location and location.get("status") == "success":
            if location.get("city"):
                st.text(f"当前城市：{location['city']}")
            else:
                st.info(location.get("city_error", "请重新获取位置以识别城市。"))
            st.caption("移动地点后请重新定位。城市来源：BigDataCloud；天气来源：Open-Meteo。")
        elif location:
            st.info(location.get("message", "定位失败，可直接输入城市。"))
    return location
