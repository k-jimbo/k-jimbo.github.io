---
permalink: /
title: "Academic Pages は研究者向け個人サイトのためのフォーク可能な GitHub Pages テンプレートです"
author_profile: true
lang: ja
ref: about
---

このページは、[Academic Pages テンプレート](https://github.com/academicpages/academicpages.github.io)を使い、GitHub Pages でホストされているウェブサイトのトップページです。[GitHub Pages](https://pages.github.com) は、GitHubリポジトリに保存されたコードとデータからウェブサイトを構築・ホストする無料サービスで、リポジトリに新しいコミットがプッシュされるたびに自動的に更新されます。このテンプレートは Michael Rose 氏による [Minimal Mistakes Jekyll テーマ](https://mmistakes.github.io/minimal-mistakes/)をフォークし、研究者が持つようなコンテンツ（業績、講演、教育、ポートフォリオ、ブログ記事、動的に生成されるCV）に対応できるよう拡張したものです。これらの機能は、プロフェッショナルなサイトを見せたい人にも役立ちます。

[このテンプレート](https://github.com/academicpages/academicpages.github.io)は今すぐフォークして、設定ファイルやMarkdownファイルを編集し、自分のPDFなどのコンテンツを追加することで、広告なしの無料の自分のサイトを持つことができます。

データ駆動型の個人サイト
======
他の多くのJekyllベースのGitHub Pagesテンプレートと同様に、Academic Pages はサイトの内容（コンテンツ）と見た目（フォーム）を分離する設計になっています。サイトのコンテンツ・メタデータは構造化されたMarkdownファイルに保存され、それ以外の各種ファイルがテーマを構成し、コンテンツ・メタデータをHTMLページへ変換する方法を指定します。これらのMarkdown (.md)、YAML (.yml)、HTML、CSSファイルは公開GitHubリポジトリで管理します。リポジトリを更新・プッシュするたびに、[GitHub Pages](https://pages.github.com/) サービスがこれらのファイルから静的HTMLページを生成し、GitHubのサーバー上に無料でホストします。

Wordpressのような動的コンテンツ管理システムの多くの機能を、はるかに少ない計算リソースで、ハッキングやDDoS攻撃への耐性も高い形で実現できます。また、サイトのコンテンツに触れずにテーマを自由にカスタマイズすることも可能です。Jekyll/HTML/CSSで何か修復不可能な問題が起きても、講演や業績を記述したMarkdownファイルは無事です。変更をロールバックしたり、リポジトリを削除してやり直したりすることもできます（Markdownファイルだけは必ず保存しておいてください）。また、[このノートブック](https://github.com/academicpages/academicpages.github.io/blob/master/talkmap.ipynb)のように、講演ページのメタデータを解析して[講演を行った場所の地図](https://academicpages.github.io/talkmap.html)を表示するスクリプトを書くこともできます。

より高度な機能が必要な場合、このテンプレートは以下の主要なツールにも対応しています。
- 数式表示のための [MathJax](https://www.mathjax.org/)
- 図表作成のための [Mermaid](https://mermaid.js.org/)
- プロットのための [Plotly](https://plotly.com/javascript/)

はじめかた
======
1. GitHubアカウントを持っていない場合は登録し、メールアドレスの確認を済ませてください（必須）
1. 右上の「Use this template」ボタンから[このテンプレート](https://github.com/academicpages/academicpages.github.io)をフォークします。
1. リポジトリの設定（"Code"タブの右端、"Unwatch"の下あたり）に移動し、リポジトリ名を「[あなたのGitHubユーザー名].github.io」に変更します。これがそのままサイトのURLになります。
1. サイト全体の設定を行い、コンテンツ・メタデータを作成します（下記参照。また、ユーザー名 "getorg-testacct" のサンプルサイトを設定するために変更されたファイルの[差分](https://archive.is/3TPas)も参考にしてください）
1. PDFやzipファイルなどは files/ ディレクトリにアップロードしてください。https://[あなたのGitHubユーザー名].github.io/files/example.pdf のようなURLで公開されます。
1. リポジトリ設定の「GitHub Pages」セクションでビルド状況を確認できます

サイト全体の設定
------
サイトのメイン設定ファイルはリポジトリ直下の [_config.yml](https://github.com/academicpages/academicpages.github.io/blob/master/_config.yml) にあり、サイドバーの内容やサイト全体の機能を定義します。デフォルトの値を自分自身やGitHubリポジトリに関する情報に書き換える必要があります。上部メニューの設定ファイルは [_data/navigation.yml](https://github.com/academicpages/academicpages.github.io/blob/master/_data/navigation.yml) にあります。例えばポートフォリオやブログ記事がない場合は、navigation.yml からその項目を削除すればヘッダーから消えます。

コンテンツ・メタデータの作成
------
サイトのコンテンツは、_publications、_talks、_posts、_teaching、_pages のようなディレクトリに、コンテンツの種類ごとに1つのMarkdownファイルとして保存されます。例えば各講演は [_talksディレクトリ](https://github.com/academicpages/academicpages.github.io/tree/master/_talks) 内のMarkdownファイルです。各Markdownファイルの先頭には講演に関する構造化データ（YAML）があり、テーマがこれを解析していろいろな処理を行います。同じ構造化データは、[講演ページ](https://academicpages.github.io/talks)の一覧、各講演の[個別ページ](https://academicpages.github.io/talks/2012-03-01-talk-1)、[CVページ](https://academicpages.github.io/cv)の講演セクション、そして（[このPythonファイル](https://github.com/academicpages/academicpages.github.io/blob/master/talkmap.py)や[Jupyterノートブック](https://github.com/academicpages/academicpages.github.io/blob/master/talkmap.ipynb)を実行した場合の）[講演場所の地図](https://academicpages.github.io/talkmap.html)の生成にも使われます。

**Markdownジェネレーター**

このリポジトリには、講演や発表に関する構造化データを含むCSVを、Academic Pagesテンプレート用に整形されたMarkdownファイル群に変換する[Jupyterノートブック一式](https://github.com/academicpages/academicpages.github.io/tree/master/markdown_generator)が含まれています。

GitHubリポジトリの編集方法
------
多くの人はgitクライアントを使ってローカルでファイルを作成し、GitHubのサーバーにプッシュします。gitに不慣れな場合は、github.comのインターフェース上で設定ファイルやMarkdownファイルを直接編集することもできます。[このようなファイル](https://github.com/academicpages/academicpages.github.io/blob/master/_talks/2012-03-01-talk-1.md)を開き、プレビューの右上にある鉛筆アイコン（「Raw | Blame | History」ボタンの右）をクリックしてください。鉛筆アイコンの右にあるゴミ箱アイコンでファイルを削除できます。ディレクトリに移動して「Create new file」や「Upload files」ボタンから新規ファイルの作成・アップロードも可能です。

より詳しい情報
------
Academic Pagesの設定に関する詳しい情報は、[ガイド](https://academicpages.github.io/markdown/)や[成長中のwiki](https://github.com/academicpages/academicpages.github.io/wiki)にあります。また[GitHub Discussionsで質問する](https://github.com/academicpages/academicpages.github.io/discussions)こともできます。このテーマのフォーク元である [Minimal Mistakesテーマのガイド](https://mmistakes.github.io/minimal-mistakes/docs/configuration/)も参考になるでしょう。
