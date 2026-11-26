# 产品表和检索存储都用 PostgreSQL + pgvector

图谱和向量要落在同一套可持久化存储里，不能用 SQLite 顶一阵再迁。PostgreSQL 16 加 pgvector 同时承担产品表、LightRAG 的 KV、向量和图谱（PGTableGraphStorage，不用 Apache AGE）。连接串由环境变量提供；本机可以用 SSH 隧道连已有实例，也可以用 compose 起 `pgvector/pgvector:pg16`。缺库就停，不换库。
