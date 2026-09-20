# 数据说明

本目录的 demo_maintenance.txt 和 external/records.csv 为整理上传版时新编写的演示资料及虚构记录，不代表真实设备参数、用户信息或评测结果。

原项目的 TXT、PDF、记录表及向量数据库没有复制。需要原有知识时，确认资料允许再分发后再导入；本地使用可自行复制到 data/。加载器目前读取 data/ 顶层 TXT/PDF。

更换知识后应重建索引：先备份并移走 chroma_db/ 和 md5.txt，再执行 python init_knowledge.py。两者必须同步处理，避免旧 MD5 记录使新数据库跳过导入。导入会调用 embedding 服务，可能计费。
