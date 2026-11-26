# 检索用 LightRAG Core，产品 API 自写

需要图谱加向量，而不是单纯切块检索。LightRAG 的 mix 查询就是这件事；LlamaIndex 是通用编排，再包一层会重复抽象。不用 LightRAG Server / WebUI，避免把它的账号模型和界面带进产品。我们的 FastAPI 提供登录、知识空间、对话和上传；每个知识空间对应一个不可变的 LightRAG workspace。第一版凡登录即可进全部空间、上传和提问，成员权限后加，但空间分桶从第一版就在，避免以后拆库重建图谱。
