# PDF/Word 用本机 MinerU 转成 Markdown，不用 pypdf / python-docx

制度、方案里的事实经常在表格和标题里。`pypdf` / `python-docx` 抽成乱行后，LightRAG 切块和抽实体都会差；mineru.net 云解析又要把原文件送出内网，和「原文件存本地」冲突。因此 PDF、Word 在进入 LightRAG 之前，由**本机 MinerU 4.x** 解析成带标题和表格的 Markdown；产品 FastAPI 只 HTTP 调用本机 `mineru-kit api-server`（**8001**，避开知识库自己的 8000），不把 MinerU 装进本仓库环境，也不在请求里同步跑模型。部署目录是 `C:\code\RAG\MinerU`，操作见该目录 README。

## Considered Options

- **pypdf / python-docx 抽纯文本再 `ainsert`**：依赖已经在 `pyproject.toml` 里，接得最快。表格丢失，建库质量不可接受。明确拒绝，实现时从依赖删除。
- **mineru.net 云 + OSS**（RAG-cy 现用路径）：解析质量可用，但原文件出网，密钥和服务绑在云上。拒绝。
- **MinerU 装进 FastAPI 进程**：一次部署简单，模型和 CUDA/ONNX 与 LightRAG 抢环境和内存，解析会堵住问答。拒绝。
- **本机 MinerU 服务 + HTTP**（采用）：原文件留本地；解析与问答进程分开；Markdown 与用户直接上传的 md 走同一条 LightRAG 插入路径。数字 PDF 用 `flash` + `ocr-mode txt`，扫描件再升 `standard`。
