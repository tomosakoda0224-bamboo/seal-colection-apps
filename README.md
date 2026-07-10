# シールコレクション記録アプリ

Streamlitで作った、シール集め用の記録アプリです。登録、検索、絞り込み、編集、削除、CSVバックアップに対応しています。

## ローカルで動かす

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 公開する

一番簡単なのは Streamlit Community Cloud です。

1. このフォルダの中身をGitHubリポジトリにアップロードします。
2. [Streamlit Community Cloud](https://streamlit.io/cloud) にログインします。
3. `New app` からGitHubリポジトリを選びます。
4. Main file path に `app.py` を指定してデプロイします。

## データについて

記録は `data/stickers.csv` に保存されます。公開環境ではファイル保存が永続化されない場合があるため、こまめに「バックアップ」タブからCSVをダウンロードしてください。長期運用する場合は、Google SheetsやSupabaseなど外部データベースに保存先を変える構成がおすすめです。

## CSV項目

- `name`: シール名
- `series`: シリーズ
- `category`: カテゴリ
- `price`: 料金
- `status`: 状態
- `quantity`: 枚数
- `acquired_on`: 入手日
- `source`: 入手元
- `location`: 保管場所
- `notes`: メモ
