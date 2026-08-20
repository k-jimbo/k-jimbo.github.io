#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_publications.py

researchmap からエクスポートした業績CSV (data/rm_published_papers.csv) を読み込み、
`_publications/` 配下に業績ページ（Markdown）を生成する。

多言語プラグインは使わず、**1論文につき1ファイル**で、日本語と英語の情報を
同じページ内に併記する方式。

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

# _config.yml の publication_category に定義されているカテゴリのうち、
# 論文(published_papers)に対応するもの。一覧ページでは "Journal Articles" の
# 見出しの下に表示される。
DEFAULT_CATEGORY = "manuscripts"


class Publication:
    """CSVの1行を保持し、日英併記の front matter を作れるようにするクラス。"""

    def __init__(self, row: dict, index: int):
        self.row = {k: (v or "").strip() for k, v in row.items()}
        self.index = index
        self._ref_override: str | None = None

    def get(self, key: str) -> str:
        value = self.row.get(key, "") or ""
        # researchmapのエクスポートは空欄が空文字列ではなく、文字通りの
        # "null" という文字列で入っていることがあるので、空扱いにする。
        if value.strip().lower() == "null":
            return ""
        return value

    @staticmethod
    def _clean_authors(raw: str) -> str:
        """"[Koki Jimbo,Shinya Morita]" や "[神保康紀\\,舘野寿丈]" のような
        researchmap特有の角カッコ区切り表記を "Koki Jimbo, Shinya Morita" の
        ような読みやすい表記に変換する。"""
        raw = raw.strip()
        if not raw:
            return ""
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw[1:-1]
        parts = re.split(r"\\,|,", raw)
        parts = [p.strip().strip('"').strip() for p in parts]
        return ", ".join(p for p in parts if p)

    # --- 各フィールド ---------------------------------------------------------

    @property
    def title_ja(self) -> str:
        return self.get("タイトル(日本語)")

    @property
    def title_en(self) -> str:
        return self.get("タイトル(英語)")

    @property
    def authors_ja(self) -> str:
        return self._clean_authors(self.get("著者(日本語)"))

    @property
    def authors_en(self) -> str:
        return self._clean_authors(self.get("著者(英語)"))

    @property
    def venue_ja(self) -> str:
        return self.get("誌名(日本語)")

    @property
    def venue_en(self) -> str:
        return self.get("誌名(英語)")

    @property
    def volume(self) -> str:
        return self.get("巻")

    @property
    def issue(self) -> str:
        return self.get("号")

    @property
    def doi(self) -> str:
        return self.get("DOI")

    @property
    def url(self) -> str:
        return self.get("URL") or self.get("URL2")

    @property
    def disclosed(self) -> bool:
        return self.get("公開の有無").strip().lower() == DISCLOSED_VALUE

    _MONTH_ABBR = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    @property
    def date_str(self) -> str:
        """出版年月を 'YYYY-MM-DD' に正規化する。以下の形式に対応:
        '2024/07', '2024-07', '2024年7月', '2024', '2026/4/21'
        'Sep-24' (Excelが 'YYYY-MM' を月名に自動変換してしまったもの)
        """
        raw = self.get("出版年月").strip()
        if not raw:
            return "1900-01-01"

        # "Sep-24" / "Mar-2019" のような "月名-年" 形式 (Excelの日付誤変換対策)
        m = re.match(r"^([A-Za-z]{3,})[-/](\d{2,4})$", raw)
        if m:
            month = self._MONTH_ABBR.get(m.group(1)[:3].lower())
            if month:
                year = int(m.group(2))
                if year < 100:
                    year += 2000
                return f"{year:04d}-{month:02d}-01"

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
        start, end = self.get("開始ページ"), self.get("終了ページ")
        if start and end:
            if start == end:
                # 記事番号(例: "JAMDSM0005")がstart/end両方に入っているケース
                return start
            return f"{start}-{end}"
        return start or end or ""

    # --- 日英併記用の合成フィールド -------------------------------------------

    @staticmethod
    def _bilingual(ja: str, en: str, sep: str = "<br />") -> str:
        """日英両方あれば「日本語<br />English」(改行区切り)、片方だけならそのまま返す。"""
        ja, en = ja.strip(), en.strip()
        if ja and en and ja != en:
            return f"{ja}{sep}{en}"
        return ja or en

    @property
    def display_title(self) -> str:
        return self._bilingual(self.title_ja, self.title_en)

    @property
    def display_venue(self) -> str:
        return self._bilingual(self.venue_ja, self.venue_en)

    def _citation_one_lang(self, authors: str, title: str, venue: str) -> str:
        """1言語分の引用文字列を組み立てる。"""
        year = self.date_str[:4]
        parts = []
        if authors:
            parts.append(f"{authors}.")
        parts.append(f"({year}).")
        if title:
            parts.append(f"&quot;{title}.&quot;")
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

    def citation(self) -> str:
        """日本語・英語の引用を <br /> で併記する（片方しか無ければ1行）。"""
        ja = ""
        en = ""
        if self.title_ja or self.authors_ja or self.venue_ja:
            ja = self._citation_one_lang(
                self.authors_ja or self.authors_en,
                self.title_ja or self.title_en,
                self.venue_ja or self.venue_en,
            )
        if self.title_en or self.authors_en or self.venue_en:
            en = self._citation_one_lang(
                self.authors_en or self.authors_ja,
                self.title_en or self.title_ja,
                self.venue_en or self.venue_ja,
            )
        if ja and en and ja != en:
            return f"{ja}<br />{en}"
        return ja or en

    # --- ファイル名・識別子 ---------------------------------------------------

    def slug(self) -> str:
        """ファイル名に使う ASCII スラッグ。DOI > 英語タイトル > 連番の順で使う。"""
        if self.doi:
            candidate = self.doi
        else:
            candidate = self.title_en or self.title_ja

        candidate = unicodedata.normalize("NFKD", candidate)
        candidate = candidate.encode("ascii", "ignore").decode("ascii")
        candidate = candidate.lower()
        candidate = re.sub(r"[^a-z0-9]+", "-", candidate).strip("-")
        candidate = re.sub(r"-{2,}", "-", candidate)

        if not candidate:
            candidate = f"paper-{self.index:04d}"

        return candidate[:60].strip("-") or f"paper-{self.index:04d}"

    def ref(self) -> str:
        if self._ref_override:
            return self._ref_override
        return f"{self.date_str}-{self.slug()}"

    def filename(self) -> str:
        return f"{self.ref()}.md"

    # --- 出力 -----------------------------------------------------------------

    def to_markdown(self, category: str) -> str:
        title = self.display_title.replace('"', '\\"')
        venue = self.display_venue
        citation = self.citation()
        permalink = f"/publication/{self.ref()}/"

        lines = [
            "---",
            f'title: "{title}"',
            "collection: publications",
            f"category: {category}",
            f"permalink: {permalink}",
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

        # 本文にも日英それぞれの書誌情報とリンクを載せる
        if self.title_ja:
            lines.append(f"**{self.title_ja}**  ")
            if self.authors_ja:
                lines.append(f"{self.authors_ja}  ")
            if self.venue_ja:
                lines.append(f"*{self.venue_ja}*  ")
            lines.append("")
        if self.title_en and self.title_en != self.title_ja:
            lines.append(f"**{self.title_en}**  ")
            if self.authors_en:
                lines.append(f"{self.authors_en}  ")
            if self.venue_en:
                lines.append(f"*{self.venue_en}*  ")
            lines.append("")
        if self.doi:
            lines.append(f"DOI: [{self.doi}](https://doi.org/{self.doi})")
            lines.append("")
        if self.url:
            lines.append(f"[論文へ / Full text]({self.url})")
            lines.append("")
        return "\n".join(lines)


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


def write_publications(
    publications: list[Publication],
    output_dir: Path,
    category: str,
    dry_run: bool = False,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    seen_refs: dict[str, int] = {}

    for pub in publications:
        base_ref = pub.ref()
        # DOI/タイトルが重複して ref が衝突する場合は連番を付けて回避する
        count = seen_refs.get(base_ref, 0)
        seen_refs[base_ref] = count + 1
        if count > 0:
            pub._ref_override = f"{base_ref}-{count}"

        out_path = output_dir / pub.filename()
        content = pub.to_markdown(category)
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
    parser.add_argument("--category", default=DEFAULT_CATEGORY, help="front matter の category (既定: manuscripts)")
    parser.add_argument("--dry-run", action="store_true", help="ファイルを書き込まずに何が起きるかだけ表示する")
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"エラー: CSVファイルが見つかりません: {args.csv}", file=sys.stderr)
        return 1

    publications = read_csv(args.csv)
    print(f"読み込んだ公開済み(disclosed)業績: {len(publications)} 件")

    removed = clean_generated_files(args.output_dir, dry_run=args.dry_run)
    print(f"削除した既存の自動生成ファイル: {removed} 件")

    written = write_publications(publications, args.output_dir, args.category, dry_run=args.dry_run)
    print(f"書き込んだファイル: {written} 件")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
