[中文文档](#中文文档) | [English](#english)

# 中文文档

## 项目简介
- 基于 LangChain 与阿里云通义千问（DashScope），从 MySQL 数据库读取微博数据（标题/内容/评论等），按模板自动生成 Markdown 报告。
- 报告保存到 `agent/outputs/`，运行日志写入 `agent/logs/agent.log`；支持将报告入库到数据库（如 `ceshishuju.reports`）便于协作处理。

## 功能
- 工具化检索：`list_tables`、`describe_table`、`fetch_recent`、`top_by_metric`、`search_rows_keyword`
- 多轮调用：模型根据需要多次调用工具后生成正文；不足数据用“暂无数据”占位。
- 稳健性：限制工具 `limit` 不超过用户参数；自动解析表名；基础敏感文本净化。

## 环境与依赖
- Python 3.10+
- 依赖：`langchain-community`、`dashscope`、`pymysql`

### 使用 uv 快速复刻环境
- 创建虚拟环境并激活：
  ```bash
  uv venv
  source .venv/bin/activate
  ```
- 安装依赖并锁定：
  ```bash
  uv add langchain-community dashscope pymysql
  uv pip freeze > requirements.txt
  ```
- 基于 `pyproject.toml` 与 `uv.lock` 同步环境（推荐）：
  ```bash
  uv venv
  source .venv/bin/activate
  uv sync --frozen
  ```
  说明：`uv sync` 会读取 `pyproject.toml` 与 `uv.lock` 精确安装依赖；`--frozen` 保证严格按锁文件，不重新解析版本。
- 复刻既有环境（他人机器上）：
  ```bash
  uv venv
  source .venv/bin/activate
  uv pip install -r requirements.txt
  ```
- 运行示例：
  ```bash
  python /Users/violet/Desktop/pythonproject/agent/main.py --task zhihu_daily --limit 30
  ```

## 配置
- API Key：`export DASHSCOPE_API_KEY="你的key"` 或写入 `~/.dashscope_key`
- 数据库连接：在 `agent/scripts/connect_to_sql.py` 设置 `host/port/user/password`；自动选择最新库名 `weibo_YYYY_MM_DD`。

## 运行
- 生成报告：
  - `python /Users/violet/Desktop/pythonproject/agent/main.py --task zhihu_daily --limit 30`
  - `python /Users/violet/Desktop/pythonproject/agent/main.py --task memes --limit 5`
- 输出路径：`agent/outputs/<task>-YYYYMMDD-HHMMSS.md`
- 入库：默认写入 `ceshishuju.reports`（字段：`id/task/content/file_path/created_at`）

## 目录结构
```
agent/
├─ main.py           # Agent入口、工具绑定、对话循环、保存/入库、日志
├─ scripts/
│  └─ connect_to_sql.py  # MySQL操作：连接、列出表、表结构、取数、排序、检索
├─ outputs/          # 报告文件
└─ logs/
   └─ agent.log      # 运行日志
```

## 可用工具
- `list_tables`：列出所有表名
- `describe_table(table)`：查看列与类型
- `fetch_recent(table, limit)`：按时间取最近数据（无 `created_at` 则直接 `LIMIT`）
- `top_by_metric(table, metric, limit, desc)`：按数值列排序取前N条
- `search_rows_keyword(table, keyword, limit)`：在常见文本列中做关键词匹配

---

# English

## Overview
- Uses LangChain with Alibaba Cloud DashScope to read Weibo data from MySQL and auto-generate templated Markdown reports.
- Reports are saved to `agent/outputs/`, logs to `agent/logs/agent.log`; reports can be persisted into a DB (e.g., `ceshishuju.reports`) for collaboration.

## Features
- Tool-based retrieval: `list_tables`, `describe_table`, `fetch_recent`, `top_by_metric`, `search_rows_keyword`.
- Multi-turn: the model gathers data via tools, then writes the final report; missing data is marked as "暂无数据".
- Robustness: cap tool `limit` to user-specified value; resolve table names; basic text sanitization.

## Requirements
- Python 3.10+
- Dependencies: `langchain-community`, `dashscope`, `pymysql`

### Replicate environment with uv
- Create and activate a virtualenv:
  ```bash
  uv venv
  source .venv/bin/activate
  ```
- Install deps and lock:
  ```bash
  uv add langchain-community dashscope pymysql
  uv pip freeze > requirements.txt
  ```
- Sync directly from `pyproject.toml` and `uv.lock` (recommended):
  ```bash
  uv venv
  source .venv/bin/activate
  uv sync --frozen
  ```
  Note: `uv sync` reads both files and installs exact locked versions; `--frozen` enforces the lock without resolution changes.
- Reproduce on another machine:
  ```bash
  uv venv
  source .venv/bin/activate
  uv pip install -r requirements.txt
  ```
- Run example:
  ```bash
  python /Users/violet/Desktop/pythonproject/agent/main.py --task zhihu_daily --limit 30
  ```

## Setup
- API Key: `export DASHSCOPE_API_KEY="your_key"` or put it in `~/.dashscope_key`.
- Database: configure `host/port/user/password` in `agent/scripts/connect_to_sql.py`; latest DB `weibo_YYYY_MM_DD` is auto-selected.

## Run
- Generate reports:
  - `python /Users/violet/Desktop/pythonproject/agent/main.py --task zhihu_daily --limit 30`
  - `python /Users/violet/Desktop/pythonproject/agent/main.py --task memes --limit 5`
- Outputs: `agent/outputs/<task>-YYYYMMDD-HHMMSS.md`
- DB persistence: inserts into `ceshishuju.reports` (`id/task/content/file_path/created_at`).

## Structure
```
agent/
├─ main.py           # entrypoint, tools binding, loop, save/DB, logging
├─ scripts/
│  └─ connect_to_sql.py  # MySQL ops: connect, list tables, describe, fetch, sort, search
├─ outputs/          # generated reports
└─ logs/
   └─ agent.log      # runtime logs
```

## Tools
- `list_tables`: list tables
- `describe_table(table)`: describe columns
- `fetch_recent(table, limit)`: recent rows by `created_at` (fallback to `LIMIT`)
- `top_by_metric(table, metric, limit, desc)`: top-N by numeric metric
- `search_rows_keyword(table, keyword, limit)`: keyword search on common text columns


本项目通过 LangChain 调用阿里云通义千问（DashScope），将 MySQL 中的微博数据（标题、内容、评论等）按模板自动生成 Markdown 报告，并支持将报告入库以便协作处理。  
This project uses LangChain with Alibaba Cloud DashScope (Tongyi) to query Weibo data stored in MySQL, auto-generate Markdown reports based on templates, and optionally persist reports into a database for collaboration.

## 功能概览 / Features
- 数据驱动写作：优先使用数据库事实生成报告  
  Data-first authoring: reports are grounded in database facts.
- 工具化检索：表枚举、表结构查看、最近数据拉取、按指标排序、关键词检索  
  Tool-based retrieval: list tables, describe schema, fetch recent rows, sort by metric, keyword search.
- 多轮调用：模型可多次调用工具收集数据后再生成正文  
  Multi-turn workflow: model gathers data via tools, then composes the final report.
- Markdown 输出与日志：报告保存到 `agent/outputs/`，日志写到 `agent/logs/agent.log`  
  Markdown outputs and logs: reports in `agent/outputs/`, logs in `agent/logs/agent.log`.
- 报告入库（可选）：将生成的报告写入数据库（如 `ceshishuju.reports`）以供协作  
  Optional DB persistence: save reports into a database (e.g., `ceshishuju.reports`) for collaboration.
- 合规与稳健性：支持敏感文本净化、limit 上限控制、表名解析  
  Compliance & robustness: text sanitization, user limit clamping, and table name resolution.

## 环境要求 / Requirements
- Python 3.10+
- macOS（项目命令示例基于 macOS 路径与 shell）
- 依赖 / Dependencies:
  - `langchain-community`
  - `dashscope`
  - `pymysql`

## 安装与配置 / Setup
- 安装依赖 / Install dependencies
  ```bash
  # 使用 uv
  uv add langchain-community dashscope pymysql

  # 或使用 pip
  pip install langchain-community dashscope pymysql