# 说明：
# 本示例使用 LangChain 的阿里云通义千问（DashScope）聊天模型封装，
# 通过你在「阿里云百炼」创建的 API Key 调用大模型并输出回复。
#
# 依赖：
# - langchain-community  提供 ChatTongyi 集成
# - dashscope            官方 SDK，被 ChatTongyi 用来实际发起调用
#
# 环境变量：
# - 请将你的百炼/通义 API Key 设置为环境变量 DASHSCOPE_API_KEY
#   例如：export DASHSCOPE_API_KEY="你的key"
#
# 运行：
#   1) 安装依赖：uv add langchain-community dashscope
#   2) 设置密钥：export DASHSCOPE_API_KEY="你的key"
#   3) 执行：python /Users/violet/Desktop/pythonproject/agent/main.py

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import  argparse
import logging
import re
import json

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

def ensure_api_key() -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key and api_key.strip():
        return api_key.strip()
    config_path = Path.home() / ".dashscope_key"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            api_key = f.read().strip()
    except FileNotFoundError:
        raise ValueError(f"未检测到环境变量 DASHSCOPE_API_KEY，且未找到密钥文件 {config_path}")
    if not api_key:
        raise ValueError(f"密钥文件 {config_path} 内容为空")
    os.environ["DASHSCOPE_API_KEY"] = api_key
    return api_key


# 允许导入 scripts 目录中的 DB 辅助函数
sys.path.append(str(Path(__file__).parent / "scripts"))
import connect_to_sql  # noqa: E402

logger = logging.getLogger("agent")
logger.setLevel(logging.INFO)
_log_dir = Path(__file__).parent / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
_handler = logging.FileHandler(_log_dir / "agent.log", encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)

def clamp_limit(args, user_limit: int):
    if not isinstance(args, dict):
        return args
    if "limit" in args:
        try:
            n = int(args["limit"])
        except Exception:
            n = user_limit
        if n <= 0:
            n = user_limit
        args["limit"] = min(n, user_limit)
    return args

def sanitize_text(text: str) -> str:
    try:
        t = str(text)
    except Exception:
        t = json.dumps(text, ensure_ascii=False, default=str)
    t = re.sub(r'#[^#]{1,50}#', '[话题]', t)
    t = re.sub(r'@[\w\-\u4e00-\u9fa5]+', '@用户', t)
    t = re.sub(r'(色情|暴力|仇恨|恐怖|毒品|枪支|爆炸|血腥|成人|裸露|性|极端|政治|反动)', '[已隐藏]', t, flags=re.IGNORECASE)
    return t


def sanitize_tool_result(name: str, result: str) -> str:
    if name in ("list_tables", "describe_table"):
        return result
    try:
        data = json.loads(result)
    except Exception:
        return sanitize_text(result)
    keys = ("title", "content", "comment", "text", "topics", "screen_name")
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for k in keys:
                    v = item.get(k)
                    if isinstance(v, str):
                        item[k] = sanitize_text(v)
        return json.dumps(data, ensure_ascii=False, default=str)
    if isinstance(data, dict):
        rows = data.get("rows")
        if isinstance(rows, list):
            for item in rows:
                if isinstance(item, dict):
                    for k in keys:
                        v = item.get(k)
                        if isinstance(v, str):
                            item[k] = sanitize_text(v)
        return json.dumps(data, ensure_ascii=False, default=str)
    return sanitize_text(result)


@tool("fetch_hot_weibo")
def fetch_hot_weibo_tool(limit: int = 50, table: str = "hot_weibo") -> str:
    """获取微博热搜结构化数据（标题、内容、评论），返回JSON。"""
    rows = connect_to_sql.fetch_hot_weibo(limit=limit, table=table)
    return json.dumps(rows, ensure_ascii=False, default=str)

@tool("list_tables")
def list_tables_tool() -> str:
    """列出当前数据库的所有表名，返回JSON：{"count": 数量, "tables": [名称...]}."""
    tables = connect_to_sql.list_tables()
    return json.dumps({"count": len(tables), "tables": tables}, ensure_ascii=False, default=str)

@tool("describe_table")
def describe_table_tool(table: str) -> str:
    """返回指定表的列元数据列表，字段包含 name/type/is_nullable/default/key_type/extra/comment。"""
    cols = connect_to_sql.describe_table(table)
    return json.dumps(cols, ensure_ascii=False, default=str)

@tool("fetch_recent")
def fetch_recent_tool(table: str, limit: int = 50) -> str:
    """返回指定表按 created_at 降序的最近数据（若无该列则直接 LIMIT）。"""
    rows = connect_to_sql.fetch_recent(table=table, limit=limit)
    return json.dumps(rows, ensure_ascii=False, default=str)

@tool("top_by_metric")
def top_by_metric_tool(table: str, metric: str, limit: int = 20, desc: bool = True) -> str:
    """按某数值列排序返回前N条，如 comments_count/attitudes_count/reposts_count。"""
    rows = connect_to_sql.fetch_top_by_metric(table=table, metric=metric, limit=limit, desc=desc)
    return json.dumps(rows, ensure_ascii=False, default=str)

@tool("search_rows_keyword")
def search_rows_keyword_tool(table: str, keyword: str, limit: int = 20) -> str:
    """在常见文本列中进行关键词匹配，返回命中的前N条（title/content/comment/text/topics/screen_name）。"""
    rows = connect_to_sql.search_rows_keyword(table=table, keyword=keyword, limit=limit)
    return json.dumps(rows, ensure_ascii=False, default=str)


def build_chat_model(api_key: str) -> ChatTongyi:
    return ChatTongyi(model="qwen-flash", api_key=api_key, streaming=False)

# 任务模板
TASK_TEMPLATES = {
    "zhihu_daily": (
        "# 今日知乎新闻早报\n"
        "- 日期：{date}\n\n"
        "## 导语\n"
        "简要点出今日整体资讯基调。\n\n"
        "## 热点摘要\n"
        "- 3-5 条关键要点，概括今日最重要的动态。\n\n"
        "## 重点新闻\n"
        "- 至少 3 条，每条包含：标题、简述、以及引用的具体数据/评论原文片段。\n\n"
        "## 关键观点\n"
        "- 3-5 条，有理有据，避免主观。\n\n"
        "## 参考数据\n"
        "- 列出在正文中引用的微博标题或评论原文片段。\n"
    ),
    "hotspot_analysis": (
        "# 热点分析报告\n"
        "- 日期：{date}\n\n"
        "## 概览\n"
        "简述本期热点的整体情况。\n\n"
        "## 趋势\n"
        "从数据中总结趋势与走向。\n\n"
        "## 成因\n"
        "结合事实分析成因。\n\n"
        "## 受众\n"
        "受众画像与关注点。\n\n"
        "## 风险\n"
        "潜在风险与影响。\n\n"
        "## 建议\n"
        "可执行的建议与后续观察点。\n\n"
        "## 参考数据\n"
        "- 引用的标题/评论原文片段与出处。\n"
    ),
    "memes": (
        "# 今日网络热梗\n"
        "- 日期：{date}\n\n"
        "## 梗清单\n"
        "1. 标题：... 解释：... 来源：... 示例评论：...\n"
        "2. 标题：... 解释：... 来源：... 示例评论：...\n"
        "3. 标题：... 解释：... 来源：... 示例评论：...\n"
        "4. 标题：... 解释：... 来源：... 示例评论：...\n"
        "5. 标题：... 解释：... 来源：... 示例评论：...\n\n"
        "## 小结\n"
        "今日网络文化的小结与走向。\n"
    ),
    "public_reaction": (
        "# 大众反应报告\n"
        "- 日期：{date}\n\n"
        "## 情绪分布\n"
        "以百分比或定性说明积极/中立/消极（基于评论印象估算）。\n\n"
        "## 主要观点\n"
        "4-6 条，尽量引用事实依据。\n\n"
        "## 代表性评论\n"
        "5-8 条，引用原文片段并标注话题或标题。\n\n"
        "## 关注点变化\n"
        "指出随时间的关注点变化或分化。\n\n"
        "## 结论\n"
        "给出整体判断与后续观察建议。\n\n"
        "## 参考数据\n"
        "- 在文中引用过的标题/评论原文片段。\n"
    ),
}

# 运行智能体
def run_agent(task: str, limit: int = 50) -> str:
    api_key = ensure_api_key()
    chat = build_chat_model(api_key).bind_tools([
        fetch_hot_weibo_tool,
        list_tables_tool,
        describe_table_tool,
        fetch_recent_tool,
        top_by_metric_tool,
        search_rows_keyword_tool,
    ])
    chat_no_tools = build_chat_model(api_key)

    system = SystemMessage(
        content=(
            "你是一位资深数据新闻撰稿人，需优先基于数据库事实写作。\n"
            "可用工具：\n"
            "- list_tables：获取库内表数量与名称\n"
            "- describe_table(table)：查看指定表的列与类型\n"
            "- fetch_recent(table, limit)：按时间取最近数据（若无 created_at 则直接 LIMIT）\n"
            "- top_by_metric(table, metric, limit, desc)：按数值列排序取前N条\n"
            "- search_rows_keyword(table, keyword, limit)：在常见文本列中检索关键词\n"
            "- fetch_hot_weibo(limit, table)：读取热搜数据（标题/内容/评论）\n"
            "写作原则：\n"
            "- 在生成前，如需数据请先调用工具；引用具体标题/评论原文片段\n"
            "- 严格按用户提供的 Markdown 模板输出；缺失数据写“暂无数据”\n"
            "- 不输出系统/工具说明，不做主观臆测"
        )
    )
    template = TASK_TEMPLATES[task].format(date=datetime.now().strftime("%Y-%m-%d"))
    user = HumanMessage(
        content=(
            f"任务类型：{task}。请调用工具获取最多 {limit} 条数据。" 
            "步骤：\n"
            "1) 先调用 list_tables，了解有哪些表；\n"
            "2) 选择最近日期的表（表名包含形如 weibo_YYYY_MM_DD），每个表调用 fetch_recent(table, limit=10)；\n"
            "3) 如存在 comments_count/attitudes_count/reposts_count，可调用 top_by_metric 做排名；\n"
            "4) 必要时用 describe_table(table) 确认列含义；\n\n"
            "严格按照以下 Markdown 模板生成，不要输出模板外内容：\n\n"
            f"{template}\n\n"
            "规则：\n"
            "- 仅输出 Markdown；\n"
            "- 所有事实尽量引用数据中的标题/评论原文；\n"
            "- 遇到缺失数据写“暂无数据”；\n"
            "- 不要包含系统/工具说明或额外解释。"
        )
    )

    messages = [system, user]
    content = ""
    seen_turns = 0
    max_turns = 15
    while True:
        try:
            reply = chat.invoke(messages)
        except Exception as e:
            if "DataInspectionFailed" in str(e):
                messages.append(HumanMessage(content="请严格遵守安全规范，以概述方式撰写，不引用原文，避免敏感词与不当内容。"))
                seen_turns += 1
                if seen_turns >= max_turns:
                    break
                continue
            raise
        logger.info(str(reply))
        messages.append(reply)
        tool_calls = reply.additional_kwargs.get("tool_calls") or []
        if not tool_calls:
            content = reply.content or ""
            if content.strip():
                break
            seen_turns += 1
            if seen_turns >= max_turns:
                break
            messages.append(HumanMessage(content="请基于以上数据严格按照模板输出完整报告。"))
            continue
        for tc in tool_calls:
            id_ = tc.get("id")
            name = tc.get("name")
            args = tc.get("args")
            if not name and tc.get("function"):
                name = tc["function"].get("name")
                args = tc["function"].get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args.strip() or "{}")
                except Exception:
                    args = {}
            args = clamp_limit(args, limit)
            if name == "fetch_hot_weibo":
                result = fetch_hot_weibo_tool.invoke(args)
            elif name == "list_tables":
                result = list_tables_tool.invoke(args)
            elif name == "describe_table":
                result = describe_table_tool.invoke(args)
            elif name == "fetch_recent":
                result = fetch_recent_tool.invoke(args)
            elif name == "top_by_metric":
                result = top_by_metric_tool.invoke(args)
            elif name == "search_rows_keyword":
                result = search_rows_keyword_tool.invoke(args)
            else:
                result = json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)
            messages.append(ToolMessage(content=sanitize_tool_result(name, result), tool_call_id=id_, name=name))
            seen_turns += 1
            if seen_turns >= max_turns:
                break
        if seen_turns >= max_turns:
            break
    if not content.strip():
        messages.append(HumanMessage(content="请基于以上数据严格按照模板输出完整报告，不要再调用任何工具。"))
        final_reply = chat_no_tools.invoke(messages)
        content = final_reply.content or ""
    return content



def save_report(task: str, content: str) -> Path:
    out_dir = Path(__file__).parent / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{task}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"报告已保存：{path}")
    try:
        rid = connect_to_sql.save_report_to_db(task=task, content=content, file_path=str(path), target_db="ceshishuju")
        logger.info(f"数据库(ceshishuju)已入库：reports.id={rid}")
    except Exception as e:
        logger.error(f"入库失败：{e}")
    return path


def main():
    parser = argparse.ArgumentParser(description="微博热搜数据驱动的报告生成 Agent")
    parser.add_argument("--task", choices=list(TASK_TEMPLATES.keys()), required=True, help="报告类型")
    parser.add_argument("--limit", type=int, default=50, help="抓取的数据条数上限")
    args = parser.parse_args()
    content = run_agent(task=args.task, limit=args.limit)
    logger.info(f"生成的报告长度：{len(content)}")
    logger.info(f"报告预览：{content[:200]}")
    save_report(args.task, content)


if __name__ == "__main__":
    main()
