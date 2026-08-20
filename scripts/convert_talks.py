#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_talks.py

researchmap からエクスポートした学会発表CSV (data/rm_presentations*.csv) を
読み込み、`_talks/` 配下に発表ページ（Markdown）を生成する。

publications と同様、多言語プラグインは使わず、**1発表につき1ファイル**で、
日本語と英語の情報を同じページ内に併記する方式。

再実行可能:
  - CSV を差し替えて何度でも実行できる。
  - 過去にこのスクリプトが生成したファイル（front matter に
    `generated_by: scripts/convert_talks.py` を含むもの）は実行のたびに
    一旦すべて削除してから再生成するため、CSV から消えた／非公開になった発表の
    ファイルが残り続けることはない。
  - 手動で作成した _talks 内の既存ファイル（サンプルの talk-1.md など）は
    対象外なので変更・削除されない。

CSV 仕様:
  - UTF-8 (BOM付き)
  - 1行目: 見出し行 (例: "presentations" のみの行) -> スキップ
  - 2行目: 実際のヘッダ行
  - 主なカラム:
      タイトル(日本語), タイトル(英語), 講演者(日本語), 講演者(英語),
      会議名(日本語), 会議名(英語), 発表年月日, 開催年月日(From),
      開催年月日(To), 招待の有無, 会議種別, 開催地(日本語), 開催地(英語),
      国・地域, URL, URL2, 公開の有無
  - `公開の有無` が "disclosed" の行のみを対象とする
  - researchmapの標準エクスポートには含まれない項目として、
    「講演論文集のページ番号」「発表番号」の2列を追加で読み込む
    (convert_publications.py の 開始/終了ページ に相当するもので、CSV上で
    手入力されていることを想定。無い発表ではその項目自体を出力しない)

使い方:
    python scripts/convert_talks.py
    python scripts/convert_talks.py --csv data/rm_presentations20260820.csv --output-dir _talks
    python scripts/convert_talks.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_PATH = REPO_ROOT / "data" / "rm_presentations20260820.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "_talks"

GENERATED_MARKER = "generated_by: scripts/convert_talks.py"
DISCLOSED_VALUE = "disclosed"

TYPE_LABELS = {
    "oral_presentation": ("口頭発表", "Oral Presentation"),
    "poster_presentation": ("ポスター発表", "Poster Presentation"),
    "public_symposium": ("公開シンポジウム", "Public Symposium"),
    "invited_oral_presentation": ("招待講演", "Invited Talk"),
}


class Talk:
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
    def _clean_people(raw: str) -> str:
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
    def id(self) -> str:
        return self.get("ID")

    @property
    def title_ja(self) -> str:
        return self.get("タイトル(日本語)")

    @property
    def title_en(self) -> str:
        return self.get("タイトル(英語)")

    @property
    def presenters_ja(self) -> str:
        return self._clean_people(self.get("講演者(日本語)"))

    @property
    def presenters_en(self) -> str:
        return self._clean_people(self.get("講演者(英語)"))

    @property
    def venue_ja(self) -> str:
        return self.get("会議名(日本語)")

    @property
    def venue_en(self) -> str:
        return self.get("会議名(英語)")

    @property
    def location_ja(self) -> str:
        parts = [self.get("開催地(日本語)"), self.get("国・地域")]
        return "、".join(p for p in parts if p)

    @property
    def location_en(self) -> str:
        parts = [self.get("開催地(英語)"), self.get("国・地域")]
        return ", ".join(p for p in parts if p)

    @property
    def invited(self) -> bool:
        return self.get("招待の有無").strip().lower() == "true"

    @property
    def conference_type(self) -> str:
        return self.get("会議種別")

    @property
    def type_label(self) -> str:
        ja, en = TYPE_LABELS.get(self.conference_type, (self.conference_type, self.conference_type))
        if self.invited and "招待" not in ja:
            ja = f"招待{ja}" if ja else "招待講演"
            en = f"Invited {en}" if en else "Invited Talk"
        return self._bilingual(ja, en) if ja or en else ""

    @property
    def proceedings_page(self) -> str:
        return self.get("講演論文集のページ番号")

    @property
    def presentation_number(self) -> str:
        return self.get("発表番号")

    @property
    def url(self) -> str:
        return self.get("URL") or self.get("URL2")

    @property
    def disclosed(self) -> bool:
        return self.get("公開の有無").strip().lower() == DISCLOSED_VALUE

    @property
    def date_str(self) -> str:
        """発表年月日 (優先) -> 開催年月日(From) -> 開催年月日(To) の順で
        'YYYY-MM-DD' 形式の値を探す。'YYYY', 'YYYY-MM', 'YYYY-MM-DD' の
        いずれにも対応する（月・日が無ければ 01 で補う）。見つからなければ
        1900-01-01。"""
        for key in ("発表年月日", "開催年月日(From)", "開催年月日(To)"):
            raw = self.get(key)
            if not raw:
                continue
            m = re.search(r"(\d{4})(?:\D+(\d{1,2}))?(?:\D+(\d{1,2}))?", raw)
            if not m:
                continue
            year = int(m.group(1))
            month = int(m.group(2)) if m.group(2) else 1
            day = int(m.group(3)) if m.group(3) else 1
            month = min(max(month, 1), 12)
            day = min(max(day, 1), 28)
            return f"{year:04d}-{month:02d}-{day:02d}"
        return "1900-01-01"

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

    @property
    def display_location(self) -> str:
        return self._bilingual(self.location_ja, self.location_en)

    # --- ファイル名・識別子 ---------------------------------------------------

    def slug(self) -> str:
        """ファイル名に使う ASCII スラッグ。researchmapのID > 英語タイトル > 連番の順で使う。"""
        if self.id:
            candidate = f"talk-{self.id}"
        else:
            candidate = self.title_en or self.title_ja

        candidate = unicodedata.normalize("NFKD", candidate)
        candidate = candidate.encode("ascii", "ignore").decode("ascii")
        candidate = candidate.lower()
        candidate = re.sub(r"[^a-z0-9]+", "-", candidate).strip("-")
        candidate = re.sub(r"-{2,}", "-", candidate)

        if not candidate:
            candidate = f"talk-{self.index:04d}"

        return candidate[:60].strip("-") or f"talk-{self.index:04d}"

    def ref(self) -> str:
        if self._ref_override:
            return self._ref_override
        return f"{self.date_str}-{self.slug()}"

    def filename(self) -> str:
        return f"{self.ref()}.md"

    # --- 出力 -----------------------------------------------------------------

    def to_markdown(self) -> str:
        title = self.display_title.replace('"', '\\"')
        venue = self.display_venue
        location = self.display_location
        permalink = f"/talks/{self.ref()}/"

        lines = [
            "---",
            f'title: "{title}"',
            "collection: talks",
        ]
        if self.type_label:
            lines.append(f"type: '{self.type_label}'")
        lines.append(f"permalink: {permalink}")
        if venue:
            lines.append(f"venue: '{venue}'")
        lines.append(f"date: {self.date_str}")
        if location:
            lines.append(f"location: '{location}'")
        lines.append("excerpt: ''")
        if self.proceedings_page:
            lines.append(f"proceedings_page: '{self.proceedings_page}'")
        if self.presentation_number:
            lines.append(f"presentation_number: '{self.presentation_number}'")
        lines.append(f"# {GENERATED_MARKER}")
        lines.append("---")
        lines.append("")

        if self.title_ja:
            lines.append(f"**{self.title_ja}**  ")
            if self.presenters_ja:
                lines.append(f"{self.presenters_ja}  ")
            if self.venue_ja:
                lines.append(f"*{self.venue_ja}*" + (f"、{self.location_ja}" if self.location_ja else "") + "  ")
            lines.append("")
        if self.title_en and self.title_en != self.title_ja:
            lines.append(f"**{self.title_en}**  ")
            if self.presenters_en:
                lines.append(f"{self.presenters_en}  ")
            if self.venue_en:
                lines.append(f"*{self.venue_en}*" + (f", {self.location_en}" if self.location_en else "") + "  ")
            lines.append("")

        extra = []
        if self.proceedings_page:
            extra.append(f"講演論文集ページ番号 / Proceedings page: {self.proceedings_page}")
        if self.presentation_number:
            extra.append(f"発表番号 / Presentation number: {self.presentation_number}")
        if extra:
            lines.append("  \n".join(extra))
            lines.append("")

        if self.url:
            lines.append(f"[講演会情報 / Conference Information]({self.url})")
            lines.append("")
        return "\n".join(lines)


def read_csv(csv_path: Path) -> list[Talk]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return []

    # 1行目は見出し行 (例: "presentations") なのでスキップし、2行目をヘッダとして使う
    header = rows[1]
    data_rows = rows[2:]

    talks = []
    for i, raw_row in enumerate(data_rows):
        if not any(cell.strip() for cell in raw_row):
            continue
        row = dict(zip(header, raw_row))
        talk = Talk(row, index=i)
        if talk.disclosed:
            talks.append(talk)

    return talks


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


def write_talks(talks: list[Talk], output_dir: Path, dry_run: bool = False) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    seen_refs: dict[str, int] = {}

    for talk in talks:
        base_ref = talk.ref()
        count = seen_refs.get(base_ref, 0)
        seen_refs[base_ref] = count + 1
        if count > 0:
            talk._ref_override = f"{base_ref}-{count}"

        out_path = output_dir / talk.filename()
        content = talk.to_markdown()
        if dry_run:
            print(f"[dry-run] would write {out_path}")
        else:
            out_path.write_text(content, encoding="utf-8")
        written += 1

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH, help="入力CSVのパス")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="出力先ディレクトリ (_talks)")
    parser.add_argument("--dry-run", action="store_true", help="ファイルを書き込まずに何が起きるかだけ表示する")
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"エラー: CSVファイルが見つかりません: {args.csv}", file=sys.stderr)
        return 1

    talks = read_csv(args.csv)
    print(f"読み込んだ公開済み(disclosed)発表: {len(talks)} 件")

    removed = clean_generated_files(args.output_dir, dry_run=args.dry_run)
    print(f"削除した既存の自動生成ファイル: {removed} 件")

    written = write_talks(talks, args.output_dir, dry_run=args.dry_run)
    print(f"書き込んだファイル: {written} 件")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
