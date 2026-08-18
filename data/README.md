# data/

`rm_published_papers.csv` を配置してください（researchmap からエクスポートした業績CSV、UTF-8 BOM付き、
1行目が見出し行 "published_papers"、2行目がヘッダ行）。

配置後、以下を実行すると `_publications/` 配下に業績ページが生成されます。
1論文につき1ファイルで、日本語と英語の書誌情報を同じページ内に併記します。

```bash
python scripts/convert_publications.py
```

CSVを差し替えて再実行しても問題ありません。前回このスクリプトが生成したファイルは
実行のたびにいったん削除してから再生成されるため、重複や消し忘れは発生しません
（手動で作成した `_publications/` 内の既存ファイルは対象外です）。

詳細は [`scripts/convert_publications.py`](../scripts/convert_publications.py) 冒頭のdocstringを参照してください。
