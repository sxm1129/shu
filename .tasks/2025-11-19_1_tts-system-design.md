# Task Context
**File**: 2025-11-19_1
**Created**: 2025-11-19_00:00:00
**User**: $(whoami)
**Branch**: task/tts-system-design_2025-11-19_1
**Yolo Mode**: Off

# Task Description
构建一个高并发的文本转语音处理系统，支持从《四大名著》等 txt 资源解析章节，入库 MySQL，并通过 index-tts HTTP 服务生成对应章节的 mp3 音频，包含任务调度、重试、心跳和僵尸任务回收等全链路能力。

# Project Overview
当前仓库以 `/books` 目录收录大量中文古籍 txt 文件及少量处理脚本，并无现成的后端代码或数据库结构。目标系统需新增完整的 Python 服务端组件（数据库访问、解析导入、任务调度、TTS 调用、监控守护等），并依赖外部的 MySQL 8.0、对象存储（MinIO/S3/OSS）以及 index-tts API。当前环境尚未部署 MySQL，需要在设计中明确初始化流程与配置模板。

# Analysis
1. 书籍数据：`/books` 下存在单层与多层目录（如 `books/先秦/`），说明摄取逻辑需支持递归遍历与多级分类映射，文本大多为 UTF-8，需要处理潜在的编码异常与噪声行（参考 `tools/filter_out_bad_lines.py` 等）。
2. TTS 服务：本地 REST 端点为 `POST http://127.0.0.1:8009/api/tts/synthesize`（multipart/form-data），需上传 `speaker_audio`、`text` 等字段；生成的 `task_id` 可通过 `/api/tts/audio/{task_id}?format=mp3` 轮询获取 mp3。接口未限制特定参数，默认可采用示例配置。
3. 系统要求：需要 MySQL 表 `dim_books` 与 `fct_chapter_tasks`，利用 `SELECT ... FOR UPDATE SKIP LOCKED` 争抢任务，配合心跳字段和 watchdog 进行僵尸回收；音频文件上传至对象存储，URL 回写数据库；任务需支持重试与指数退避。
4. 约束：暂无现成 MySQL 实例与对象存储，需要在设计中提供初始化脚本与 `.env.example` 以便部署；心跳周期、重试上限、GPU 并发策略可按常规经验配置（例如 10 秒心跳、5 次重试、4 并发令牌）。

# Proposed Solution
1. 使用 SQLAlchemy 定义 `dim_books` 与 `fct_chapter_tasks`，并提供 `init_db.py` 初始化脚本。
2. 在 `src/infra/` 下封装数据库连接池与 S3 客户端，统一管理配置与资源。
3. `src/ingest/` 提供 `BookParser` 正则切章及 `Importer` 幂等写入逻辑，批量将章节入库。
4. `src/worker/` 实现 `TaskFetcher`（SKIP LOCKED）与 `TaskProcessor`（心跳、TTS 调用、S3 上传、重试），`main_worker.py` 组装执行循环。
5. `watchdog_service.py` 定期重置僵尸任务，`.env.example` 提供环境参数模板。

# Current Step
"Execute"

# Task Progress
2025-11-19_12:00:00

- Modified: `init_db.py`, `src/models.py`, `src/infra/database.py`, `src/infra/s3_client.py`, `src/ingest/parser.py`, `src/ingest/importer.py`, `src/worker/fetcher.py`, `src/worker/processor.py`, `main_worker.py`, `watchdog_service.py`, `.env.example`, `.tasks/2025-11-19_1_tts-system-design.md`
- Changes: 新增系统核心代码（模型、基础设施、解析导入、worker、watchdog、配置模板），完成计划中的全部功能。
- Reason: 支持基于 MySQL 的高并发 TTS 流水线，实现章节入库、任务调度、语音生成与监控。
- Blockers: 无
- Status: SUCCESSFUL

2025-11-20_10:00:00

- Modified: `src/ingest/parser.py`, `.tasks/2025-11-19_1_tts-system-design.md`
- Changes: 扩展章节解析策略（多模式正则、启发式简单标题、段落分隔与递归分块），显著提高无显式章节书籍的拆分成功率。
- Reason: 解决大批 TXT 未标注“第X章/回”时的导入失败问题，保障入库流程稳定。
- Blockers: 无
- Status: SUCCESSFUL

# Final Review
数据库已成功初始化并通过 Importer 导入《红楼梦》章节数据（book_id=1）。尚未在本地运行 worker/TTS 流程，待 index-tts 与对象存储就绪后可依照文档继续执行。
