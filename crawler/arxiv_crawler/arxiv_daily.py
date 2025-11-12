# arxiv_daily.py
# pip install arxiv

import argparse
import datetime as dt
import json
import os
import tempfile
from typing import Dict, List, Iterable, Optional

import arxiv


def under_output(path: str) -> str:
    """Put any given relative path under ./output, preserving subdirs."""
    base = os.path.join("output", path)
    d = os.path.dirname(base)
    if d:
        os.makedirs(d, exist_ok=True)
    return base


def atomic_dump_json(path: str, data: Dict) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def atomic_write_text(path: str, text: str) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def get_authors(authors: Iterable[arxiv.Result.Author], first_author: bool = False) -> str:
    names = [str(a) for a in authors]
    return names[0] if (first_author and names) else ", ".join(names)


def esc_md(s: str) -> str:
    """Escape markdown table metacharacters."""
    return s.replace("|", r"\|").replace("[", r"\[").replace("]", r"\]")


def to_pdf(url: str) -> str:
    # abs -> pdf 直链
    return url.replace("/abs/", "/pdf/") + ".pdf" if "/abs/" in url else url


def fetch_papers(
    topic: str,
    query: str,
    max_results: int = 10,
    since: Optional[dt.date] = None,
    first_author_only: bool = True,
    use_pdf_link: bool = False,
    client: Optional[arxiv.Client] = None,
) -> Dict[str, Dict]:
    """
    Search arXiv and return a dict keyed by base arXiv ID.
    Filters by 'updated' date by default.
    """
    content: Dict[str, Dict] = {}
    # 自动包装查询：若没用字段前缀，提升为 all:"..."
    if ":" not in query and '"' not in query:
        query = f'all:"{query}"'

    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    if client is None:
        client = arxiv.Client(num_retries=3, delay_seconds=2)

    kept = 0
    for result in client.results(search):
        # 以 updated 优先
        base_dt = result.updated or result.published
        if base_dt is None:
            continue  # 极端兜底
        base_date = base_dt.date()
        if since and base_date < since:
            continue

        paper_id_full = result.get_short_id()
        vpos = paper_id_full.find("v")
        paper_key = paper_id_full if vpos == -1 else paper_id_full[:vpos]

        title = esc_md(result.title.strip())
        url = result.entry_id
        if use_pdf_link:
            url = to_pdf(url)

        authors_full = esc_md(get_authors(result.authors, first_author=False))
        first_author = esc_md(get_authors(result.authors, first_author=True))
        primary_category = getattr(result, "primary_category", None) or ""

        print(f"[{topic}] kept: {kept+1}  updated={base_date}  title={title[:80]}")
        authors_md = first_author if first_author_only else authors_full
        md_row = f"|**{base_date}**|**{title}**|{authors_md} et al.|[{paper_id_full}]({url})|\n"

        content[paper_key] = {
            "date": base_date.isoformat(),
            "title": title,
            "url": url,
            "paper_id": paper_id_full,
            "authors": authors_full,
            "first_author": first_author,
            "primary_category": primary_category,
            "abstract": (result.summary or "").replace("\n", " ").strip(),
            "topic": topic,
            "md_row": md_row,
        }
        kept += 1

    return {topic: content}


def _load_json(path: str) -> Dict:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_results(existing: Dict, new_batch: List[Dict[str, Dict]]) -> Dict:
    merged = dict(existing) if existing else {}
    for topic_dict in new_batch:
        for topic, papers in topic_dict.items():
            merged.setdefault(topic, {}).update(papers)
    return merged


def json_to_md(
    json_path: str,
    md_path: str = "output/output.md",
    title_prefix: str = "Updated on",
    sort_desc_by_date: bool = True,
) -> None:
    data = _load_json(json_path)
    today = dt.date.today().strftime("%Y.%m.%d")

    lines: List[str] = [f"## {title_prefix} {today}\n"]
    for topic in sorted(data.keys()):
        items = data[topic]
        if not items:
            continue
        rows = list(items.values())
        rows.sort(key=lambda r: r.get("date", ""), reverse=sort_desc_by_date)
        if not rows:
            continue
        lines.append(f"## {topic}\n")
        lines.append("|Updated Date|Title|Authors|PDF|\n|---|---|---|---|\n")
        for r in rows:
            lines.append(r["md_row"])
        lines.append("\n")

    atomic_write_text(md_path, "".join(lines))
    print(f"Markdown written -> {md_path}")
    print("finished")


def run(
    keywords: Dict[str, str],
    json_out: str = "output/papers.json",
    md_out: str = "output/output.md",
    max_results: int = 10,
    since: Optional[dt.date] = None,
    first_author_only: bool = True,
    use_pdf_link: bool = False,
) -> None:
    client = arxiv.Client(num_retries=3, delay_seconds=2)

    data_collector: List[Dict[str, Dict]] = []
    for topic in sorted(keywords.keys()):
        query = keywords[topic]
        data = fetch_papers(
            topic=topic,
            query=query,
            max_results=max_results,
            since=since,
            first_author_only=first_author_only,
            use_pdf_link=use_pdf_link,
            client=client,
        )
        data_collector.append(data)

    existing = _load_json(json_out)
    merged = merge_results(existing, data_collector)
    atomic_dump_json(json_out, merged)
    json_to_md(json_out, md_out)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch arXiv papers and render JSON/Markdown.")
    p.add_argument("--keyword", action="append", metavar="TOPIC=QUERY",
                   help="Map a topic to an arXiv query. Can be used multiple times.")
    p.add_argument("--json-out", default="papers.json")
    p.add_argument("--md-out", default="output.md")
    p.add_argument("--max-results", type=int, default=10)
    p.add_argument("--since", type=str, default=None,
                   help="Only include papers updated on/after YYYY-MM-DD.")
    p.add_argument("--reset", action="store_true", help="Clear JSON before merging.")
    p.add_argument("--all-authors", action="store_true",
                   help="Show full author list instead of first author.")
    p.add_argument("--pdf-link", action="store_true",
                   help="Link to direct PDF instead of abstract page.")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    keywords = {"SLAM": "SLAM"} if not args.keyword else {
        k.strip(): v.strip() for k, v in (kv.split("=", 1) for kv in args.keyword if "=" in kv)
    }

    since_date = dt.datetime.strptime(args.since, "%Y-%m-%d").date() if args.since else None

    json_out = under_output(args.json_out)
    md_out = under_output(args.md_out)

    if args.reset or (not os.path.exists(json_out)):
        atomic_dump_json(json_out, {})

    run(
        keywords=keywords,
        json_out=json_out,
        md_out=md_out,
        max_results=args.max_results,
        since=since_date,
        first_author_only=not args.all_authors,
        use_pdf_link=args.pdf_link,
    )


if __name__ == "__main__":
    main()
