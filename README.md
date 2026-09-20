# 智扫通 · 扫地机器人智能客服 Agent

基于 Streamlit、LangChain、通义千问和 Chroma 的学习演示项目，支持知识库问答、工具调用、使用报告、聊天历史与引用展示。

## 功能与结构

- Agent 按对话调用知识检索、使用记录、天气等工具。
- 本地 TXT/PDF 经分片、向量化后存入 Chroma。
- 对话通过 SQLite 保存；答案来源由引用处理模块校验和整理。
- 浏览器定位由用户点击授权，也可以直接提供城市查询天气。

```text
app.py                 Streamlit 页面
agent/                 Agent、工具和中间件
model/                 通义模型与向量模型
rag/                   检索与知识导入
prompts/ config/       提示词与参数
storage/               聊天记录存储代码
utils/                 配置、引用、天气等辅助功能
data/                  新编写的演示知识与模拟使用记录
tests/                 无需模型密钥的离线测试
init_knowledge.py      知识库初始化入口
```

## 本地运行（Windows PowerShell）

建议 Python 3.12。依赖版本来自原项目 openai-env 环境；尚未完成全新环境的在线安装与端到端验证。

```powershell
cd 路径\robot-customer-service-agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 .env，将占位符替换为自己的 DASHSCOPE_API_KEY。也支持同名系统环境变量，已有环境变量优先。不要提交真实密钥。

默认聊天模型 qwen3-max、向量模型 text-embedding-v4，可在 config/rag.yml 修改；须确保自己的服务账号具有访问权限。模型调用和知识导入可能计费。

```powershell
.\.venv\Scripts\python.exe init_knowledge.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

打开终端提示的本地网址。聊天数据库和日志自动生成；首次启动前必须先导入知识库。

## 演示问题

- 扫地机器人清扫前需要整理哪些物品？
- 帮我生成用户1002在2025年1月的使用报告。
- 杭州现在天气怎么样？（需要网络）

本上传版使用小型演示资料，回答覆盖范围不等同于原版知识库；使用记录完全虚构。

## 测试

```powershell
python -m unittest discover -s tests -v
```

该测试集无需 API 密钥，覆盖引用与存储等逻辑，不代表在线模型效果、真实天气请求和所有页面交互均已验证。GitHub Actions 自动运行离线测试和语法检查。

## 已知限制

- 面向本地单用户学习演示，没有账号认证和多用户权限隔离；不应直接用真实用户记录部署公共服务。
- 报告格式仍受模型输出影响，固定标题等要求不保证每次严格满足。
- 当前位置查询需要点击按钮并授权；浏览器定位需要 localhost 或 HTTPS。
- 天气和逆地理编码依赖外部服务及网络，定位会将坐标发送给对应服务。
- 知识更新尚无完整版本管理；替换资料时需同步重建数据库与 MD5 清单，见 data/README.md。
- 尚未提供量化效果评测，不宣称生产可用或特定准确率。

## 上传 GitHub

1. 检查 THIRD_PARTY_NOTICES.md，补齐原代码来源与授权。
2. 创建空 GitHub 仓库，不预先生成 README 或许可证。
3. 在本目录执行以下命令，将地址替换为自己的仓库地址。

```powershell
git init
git branch -M main
git add .
git diff --cached --stat
# 检查暂存文件不含密钥、聊天数据库、日志后继续
git commit -m "Initial project release"
git remote add origin https://github.com/YOUR_NAME/YOUR_REPOSITORY.git
git push -u origin main
```

.gitignore 已排除密钥、向量库、导入记录、聊天数据库、日志和缓存。不要仅上传 ZIP；让本 README 位于仓库根目录。

## 来源与许可

见 THIRD_PARTY_NOTICES.md。上游授权尚未确认，因此本整理版暂未添加开源许可证。
