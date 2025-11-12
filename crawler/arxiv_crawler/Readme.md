
---

# 🧠 arxiv-daily — 自动抓取 ArXiv 最新论文

一个轻量级 Python 工具，用于**自动从 ArXiv 获取最新论文**（例如 “SLAM”、“VIO”、“RNA Secondary Structure”等主题），并将结果生成结构化的 **JSON** 与 **Markdown** 表格列表。

---

## ✨ 功能特点

* 🚀 自动搜索 ArXiv 上指定主题的最新论文
* 📄 输出 JSON 数据与 Markdown 表格
* 🔍 支持多个主题 / 查询关键字
* 🔁 自动合并历史记录，避免重复
* 🗓 默认按 **最近更新日期（Updated Date）** 过滤论文
* ⚙️ 自动保存至 `output/` 文件夹
* 🧩 可选功能：

  * `--reset` 清空历史记录
  * `--pdf-link` 直接输出 PDF 链接
  * `--all-authors` 显示完整作者列表

---

## 📦 安装依赖

```bash
pip install arxiv
```

或使用：

```bash
pip install -r requirements.txt
```

---

## 🚀 命令行使用

```bash
python arxiv_daily.py \
  --keyword SLAM="SLAM" \
  --keyword VIO="visual-inertial odometry" \
  --keyword RNA_SS_predict="RNA secondary structure prediction" \
  --max-results 50 \
  --since 2025-05-01
```

### 参数说明

| 参数              | 说明                                 | 示例                       |
| --------------- | ---------------------------------- | ------------------------ |
| `--keyword`     | 主题=查询，可多次使用                        | `--keyword SLAM=SLAM`    |
| `--max-results` | 每个主题获取的最大论文数                       | `--max-results 50`       |
| `--since`       | 仅保留指定日期（YYYY-MM-DD）之后更新的论文         | `--since 2025-05-01`     |
| `--json-out`    | 自定义 JSON 输出文件名（默认 `papers.json`）   | `--json-out custom.json` |
| `--md-out`      | 自定义 Markdown 输出文件名（默认 `output.md`） | `--md-out mylist.md`     |
| `--reset`       | 清空历史 JSON 数据后重新抓取                  | `--reset`                |
| `--pdf-link`    | 生成直达 PDF 链接                        | `--pdf-link`             |
| `--all-authors` | 在表格中显示完整作者列表                       | `--all-authors`          |

> 所有文件都会自动保存在 **`output/`** 文件夹中。

---

### 🕒 时间过滤示例

1. 获取 2025 年 5 月 1 日之后更新的论文：

   ```bash
   python arxiv_daily.py \
     --keyword SLAM="SLAM" \
     --since 2025-05-01
   ```

2. 同时检索多个主题：

   ```bash
   python arxiv_daily.py \
     --keyword SLAM="SLAM" \
     --keyword VIO="visual-inertial odometry" \
     --since 2025-05-01
   ```

3. 清空历史数据并重新生成：

   ```bash
   python arxiv_daily.py \
     --keyword RNA_SS_predict="RNA secondary structure prediction" \
     --since 2025-05-01 \
     --reset
   ```

4. 生成 PDF 链接 + 全部作者：

   ```bash
   python arxiv_daily.py \
     --keyword LLM="large language model" \
     --since 2025-05-01 \
     --pdf-link --all-authors
   ```

---

## 🧩 Python 模块调用

可直接在 Python 中使用：

```python
import arxiv_daily as ad
import datetime as dt

keywords = {
    "SLAM": "SLAM",
    "RNA_SS": "RNA secondary structure prediction",
    "BioML": "biomedical foundation model"
}

since_date = dt.date(2025, 5, 1)

ad.run(
    keywords=keywords,
    json_out="output/papers.json",
    md_out="output/output.md",
    max_results=50,
    since=since_date,
    use_pdf_link=True
)
```

---

## 📁 输出文件示例

### JSON (`output/papers.json`)

```json
{
  "SLAM": {
    "2501.01234": {
      "date": "2025-11-12",
      "title": "A Robust SLAM Framework Based on Graph Optimization",
      "first_author": "John Doe",
      "url": "https://arxiv.org/abs/2501.01234",
      "md_row": "|**2025-11-12**|**A Robust SLAM Framework Based on Graph Optimization**|John Doe et al.|[2501.01234](https://arxiv.org/pdf/2501.01234.pdf)|\n"
    }
  }
}
```

### Markdown (`output/output.md`)

```markdown
## Updated on 2025.11.12

## SLAM

|Updated Date|Title|Authors|PDF|
|---|---|---|---|
|**2025-11-12**|**A Robust SLAM Framework Based on Graph Optimization**|John Doe et al.|[2501.01234](https://arxiv.org/pdf/2501.01234.pdf)|
```

---

## ⚙️ 文件结构建议

```
arxiv-daily/
│
├── arxiv_daily.py          # 主程序
├── requirements.txt        # 依赖列表
├── output/                 # 输出文件夹
│   ├── papers.json
│   └── output.md
└── README.md               # 使用说明（本文件）
```

---

## 🧑‍💻 作者与许可

* 作者：[Haobin Chen](https://github.com/CHB-learner)
* License: **Unlicense**（公共领域，无任何使用限制）

> 你可以自由地使用、修改、分发本项目的全部或部分内容，无需署名或许可。

---
