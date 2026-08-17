#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_publications.py

researchmap からエクスポートした業績CSV (data/rm_published_papers.csv) を読み込み、
`_publications/` 配下に日本語版・英語版の Markdown ファイル（jekyll-polyglot 用の
front matter を付与）を生成する。

再実行可能:
  - CSV を差し替えて何度でも実行できる。
  - 過去にこのスクリプトが生成したファイル（front matter に
    `generated_by: scripts/convert_publications.py` を含むもの）は実行のたびに
    一旦すべて削除してから再生成するため、CSV から消えた／非公開になった論文の
    ファイルが残り続けることはない。
  - 手動で作成した _publications 内の既存ファイル（サンプルの
    paper-title-number-*.md など）は対象外なので変更・削除されない。

CSV 仕様:
  - UTF-8 (BOM付き)
  - 1行目: 見出し行 (例: "published_papers" のみの行) -> スキップ
  - 2行目: 実際のヘッダ行
  - 主なカラム:
      タイトル(日本語), タイトル(英語), 著者(日本語), 著者(英語), 出版年月,
      誌名(日本語), 誌名(英語), 巻, 号, 開始ページ, 終了ページ, 記述言語,
      DOI, URL, URL2, 公開の有無
  - `公開の有無` が "disclosed" の行のみを対象とする

使い方:
    python scripts/convert_publications.py
    python scripts/convert_publications.py --csv data/rm_published_papers.csv --output-dir _publications
    python scripts/convert_publications.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_PATH = REPO_ROOT / "data" / "rm_published_papers.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "_publications"

GENERATED_MARKER = "generated_by: scripts/convert_publications.py"
DISCLOSED_VALUE = "disclosed"

LANGS = ("ja", "en")


class Publication:
    """CSVの1行を保持し、日英どちらの front matter も作れるようにするクラス。"""

    def __init__(self, row: dict, index: int):
        self.row = {k: (v or "").strip() for k, v in row.items()}
        self.index = index

    def get(self, key: str) -> str:
        return self.row.get(key, "") or ""

    # --- フォールバック付きフィールド取得 -----------------------------------

    def title(self, lang: str) -> str:
        ja, en = self.get("タイトル(日本語)"), self.get("タイトル(英語)")
        if lang == "ja":
            return ja or en
        return en or ja

    def authors(self, lang: str) -> str:
        ja, en = self.get("著者(日本語)"), self.get("著者(英語)")
        if lang == "ja":
            return ja or en
        return en or ja

    def venue(self, lang: str) -> str:
        ja, en = self.get("誌名(日本語)"), self.get("誌名(英語)")
        if lang == "ja":
            return ja or en
        return en or ja

    @property
    def volume(self) -> str:
        return self.get("巻")

    @property
    def issue(self) -> str:
        return self.get("号")

    @property
    def start_page(self) -> str:
        return self.get("開始ページ")

    @property
    def end_page(self) -> str:
        return self.get("終了ページ")

    @property
    def doi(self) -> str:
        return self.get("DOI")

    @property
    def url(self) -> str:
        return self.get("URL") or self.get("URL2")

    @property
    def disclosed(self) -> bool:
        return self.get("公開の有無").strip().lower() == DISCLOSED_VALUE

    @property
    def date_str(self) -> str:
        """出版年月 (例: '2024/07', '2024-07', '2024年7月', '2024') -> 'YYYY-MM-DD'"""
        raw = self.get("出版年月")
        m = re.search(r"(\d{4})\D*(\d{1,2})?\D*(\d{1,2})?", raw)
        if not m:
            return "1900-01-01"
        year = int(m.group(1))
        month = int(m.group(2)) if m.group(2) else 1
        day = int(m.group(3)) if m.group(3) else 1
        month = min(max(month, 1), 12)
        day = min(max(day, 1), 28)
        return f"{year:04d}-{month:02d}-{day:02d}"

    @property
    def pages(self) -> str:
        if self.start_page and self.end_page:
            return f"{self.start_page}-{self.end_page}"
        return self.start_page or self.end_page or ""

    def slug(self) -> str:
        """ファイル名・ref に使う ASCII スラッグ。DOI > 英語タイトル > 連番の順で使う。"""
        if self.doi:
            candidate = self.doi
        else:
            candidate = self.get("タイトル(英語)") or self.get("タイトル(日本語)")

        candidate = unicodedata.normalize("NFKD", candidate)
        candidate = candidate.encode("ascii", "ignore").decode("ascii")
        candidate = candidate.lower()
        candidate = re.sub(r"[^a-z0-9]+", "-", candidate).strip("-")
        candidate = re.sub(r"-{2,}", "-", candidate)

        if not candidate:
            candidate = f"paper-{self.index:04d}"

        return candidate[:60].strip("-") or f"paper-{self.index:04d}"

    def ref(self) -> str:
        return f"{self.date_str}-{self.slug()}"

    def citation(self, lang: str) -> str:
        authors = self.authors(lang)
        title = self.title(lang)
        venue = self.venue(lang)
        year = self.date_str[:4]

        parts = []
        if authors:
            parts.append(f"{authors}.")
        parts.append(f"({year}).")
        if title:
            parts.append(f'&quot;{title}.&quot;')
        if venue:
            venue_part = f"<i>{venue}</i>."
            if self.volume:
                venue_part += f" {self.volume}"
                if self.issue:
                    venue_part += f"({self.issue})"
                venue_part += "."
            elif self.issue:
                venue_part += f" ({self.issue})."
            parts.append(venue_part)
        if self.pages:
            parts.append(f"pp. {self.pages}.")
        return " ".join(parts)

    def front_matter(self, lang: str, other_lang_exists: bool) -> str:
        title = self.title(lang).replace('"', '\\"')
        venue = self.venue(lang)
        citation = self.citation(lang)
        permalink = f"/publication/{self.ref()}/"

        lines = [
            "---",
            f"title: \"{title}\"",
            "collection: publications",
            f"permalink: {permalink}",
            f"lang: {lang}",
            f"ref: {self.ref()}",
            "excerpt: ''",
            f"date: {self.date_str}",
        ]
        if venue:
            lines.append(f"venue: '{venue}'")
        if self.url:
            lines.append(f"paperurl: '{self.url}'")
        if self.doi:
            lines.append(f"doi: '{self.doi}'")
        lines.append(f"citation: '{citation}'")
        lines.append(f"# {GENERATED_MARKER}")
        lines.append("---")
        lines.append("")
        if self.url:
            lines.append(f"[{'論文へ' if lang == 'ja' else 'Full text'}]({self.url})")
            lines.append("")
        return "\n".join(lines)

    def filename(self, lang: str) -> str:
        return f"{self.ref()}.{lang}.md"


def read_csv(csv_path: Path) -> list[Publication]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return []

    # 1行目は見出し行 (例: "published_papers") なのでスキップし、2行目をヘッダとして使う
    header = rows[1]
    data_rows = rows[2:]

    publications = []
    for i, raw_row in enumerate(data_rows):
        if not any(cell.strip() for cell in raw_row):
            continue
        row = dict(zip(header, raw_row))
        pub = Publication(row, index=i)
        if pub.disclosed:
            publications.append(pub)

    return publications


def clean_generated_files(output_dir: Path, dry_run: bool = False) -> int:
    """前回このスクリプトが生成したファイルを削除する。"""
    removed = 0
    if not output_dir.exists():
        return removed
    for path in output_dir.glob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if GENERATED_MARKER in text:
            removed += 1
            if not dry_run:
                path.unlink()
    return removed


def write_publications(publications: list[Publication], output_dir: Path, dry_run: bool = False) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    seen_refs: dict[str, int] = {}

    for pub in publications:
        base_ref = pub.ref()
        # DOI/タイトルが重複して ref が衝突する場合は連番を付けて回避する
        count = seen_refs.get(base_ref, 0)
        seen_refs[base_ref] = count + 1
        if count > 0:
            pub_ref_override = f"{base_ref}-{count}"
            pub.ref = lambda ref=pub_ref_override: ref  # type: ignore[method-assign]

        for lang in LANGS:
            filename = pub.filename(lang)
            content = pub.front_matter(lang, other_lang_exists=True)
            out_path = output_dir / filename
            if dry_run:
                print(f"[dry-run] would write {out_path}")
            else:
                out_path.write_text(content, encoding="utf-8")
            written += 1

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH, help="入力CSVのパス")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="出力先ディレクトリ (_publications)")
    parser.add_argument("--dry-run", action="store_true", help="ファイルを書き込まずに何が起きるかだけ表示する")
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"エラー: CSVファイルが見つかりません: {args.csv}", file=sys.stderr)
        return 1

    publications = read_csv(args.csv)
    print(f"読み込んだ公開済み(disclosed)業績: {len(publications)} 件")

    removed = clean_generated_files(args.output_dir, dry_run=args.dry_run)
    print(f"削除した既存の自動生成ファイル: {removed} 件")

    written = write_publications(publications, args.output_dir, dry_run=args.dry_run)
    print(f"書き込んだファイル: {written} 件 ({written // 2 if LANGS else 0} 論文 x {len(LANGS)} 言語)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
