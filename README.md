# 智扫通：扫地机器人智能客服 Agent

这是一个基于 Streamlit、LangChain、通义千问和 Chroma 的扫地机器人智能客服项目。项目参考 B 站课程视频完成，并在此基础上加入知识库引用、聊天记录、工具调用、报告查询和自动测试等功能，主要用于学习和技术展示。

## 项目结构

```text
app.py                 Streamlit 页面入口
agent/                 Agent、工具和中间件
model/                 对话模型和向量模型
rag/                   文档加载、切分和向量检索
data/                  扫地机器人知识库资料和模拟使用记录
prompts/               Agent、RAG 和报告提示词
config/                模型、Chroma 和提示词配置
storage/               聊天历史存储
utils/                 配置、文件、天气、引用等辅助功能
init_knowledge.py      初始化 Chroma 知识库
requirements.txt       Python 依赖
```

## 数据说明

`data/` 中的资料是本项目使用的扫地机器人知识库，内容包括：

- `选购指南.txt`：扫地机器人选购、吸力、导航、避障和适用场景等建议；
- `维护保养.txt`：边刷、主刷、滤网、尘盒和日常清洁维护方法；
- `故障排除.txt`：常见故障现象、可能原因和排查建议；
- `扫拖一体机器人100问.txt`、`扫地机器人100问2.txt`、`扫地机器人100问.pdf`：扫地机器人常见问题及解答；
- `data/external/records.csv`：用于演示使用报告功能的用户记录数据。

其中 CSV 是项目演示数据，不代表真实用户信息。知识库资料来源和代码参考说明见 `THIRD_PARTY_NOTICES.md`。公开项目之前，请确认原始资料和课程代码的授权范围。

## 安装与运行

建议使用 Python 3.12。先进入项目目录并创建虚拟环境：

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，填写自己的 `DASHSCOPE_API_KEY`。不要把 `.env` 提交到 GitHub。也可以直接设置同名系统环境变量。

首次运行前初始化知识库：

```powershell
.\\.venv\\Scripts\\python.exe init_knowledge.py
```

然后启动页面：

```powershell
.\\.venv\\Scripts\\python.exe -m streamlit run app.py
```

打开终端显示的本地网址即可使用。模型调用和向量化可能产生费用。

## 主要功能

- 基于本地知识库回答扫地机器人选购、维护和故障问题；
- 显示回答引用的知识来源；
- 支持多轮对话和聊天历史保存；
- 查询天气和浏览器当前位置；
- 查询指定用户、指定月份的模拟使用记录；
- 根据使用记录生成机器人使用报告和保养建议；
- 使用 Chroma 保存文档向量，并支持 TXT、PDF 知识文件导入；
- 提供引用处理和异常处理。

本项目是学习演示版本，未提供账号认证、多用户权限隔离和生产环境部署配置。
