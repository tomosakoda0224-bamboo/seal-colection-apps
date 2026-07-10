from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st


APP_TITLE = "シールコレクション記録"
DATA_DIR = Path("data")
DATA_PATH = DATA_DIR / "stickers.csv"

COLUMNS = [
    "id",
    "name",
    "series",
    "category",
    "rarity",
    "status",
    "quantity",
    "acquired_on",
    "source",
    "location",
    "notes",
]

STATUS_OPTIONS = ["所持", "未所持", "交換予定", "探し中"]
RARITY_OPTIONS = ["不明", "ノーマル", "レア", "スーパーレア", "限定", "シークレット"]


def ensure_data_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_PATH.exists():
        pd.DataFrame(columns=COLUMNS).to_csv(DATA_PATH, index=False)


@st.cache_data
def load_data() -> pd.DataFrame:
    ensure_data_file()
    df = pd.read_csv(DATA_PATH, dtype={"id": "string"}).fillna("")
    for column in COLUMNS:
        if column not in df.columns:
            df[column] = ""
    df = df[COLUMNS]
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)
    return df


def save_data(df: pd.DataFrame) -> None:
    ensure_data_file()
    df = df[COLUMNS].copy()
    df.to_csv(DATA_PATH, index=False)
    load_data.clear()


def add_record(record: dict[str, object]) -> None:
    df = load_data()
    new_row = {"id": str(uuid4()), **record}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_data(df)


def update_record(record_id: str, record: dict[str, object]) -> None:
    df = load_data()
    for key, value in record.items():
        df.loc[df["id"] == record_id, key] = value
    save_data(df)


def delete_record(record_id: str) -> None:
    df = load_data()
    save_data(df[df["id"] != record_id])


def normalize_import(df: pd.DataFrame) -> pd.DataFrame:
    imported = df.copy().fillna("")
    for column in COLUMNS:
        if column not in imported.columns:
            imported[column] = ""
    imported = imported[COLUMNS]
    imported.loc[imported["id"].astype(str).str.strip() == "", "id"] = [
        str(uuid4()) for _ in range((imported["id"].astype(str).str.strip() == "").sum())
    ]
    imported["quantity"] = (
        pd.to_numeric(imported["quantity"], errors="coerce").fillna(1).clip(lower=0).astype(int)
    )
    return imported


def record_form(prefix: str, initial: dict[str, object] | None = None) -> dict[str, object]:
    initial = initial or {}

    name = st.text_input("シール名", value=str(initial.get("name", "")), key=f"{prefix}_name")
    series = st.text_input("シリーズ", value=str(initial.get("series", "")), key=f"{prefix}_series")

    col1, col2 = st.columns(2)
    with col1:
        category = st.text_input("カテゴリ", value=str(initial.get("category", "")), key=f"{prefix}_category")
        rarity = st.selectbox(
            "レア度",
            RARITY_OPTIONS,
            index=RARITY_OPTIONS.index(str(initial.get("rarity", "不明")))
            if str(initial.get("rarity", "不明")) in RARITY_OPTIONS
            else 0,
            key=f"{prefix}_rarity",
        )
        acquired_on = st.date_input(
            "入手日",
            value=pd.to_datetime(initial.get("acquired_on") or date.today()).date(),
            key=f"{prefix}_acquired_on",
        )
    with col2:
        status = st.selectbox(
            "状態",
            STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(str(initial.get("status", "所持")))
            if str(initial.get("status", "所持")) in STATUS_OPTIONS
            else 0,
            key=f"{prefix}_status",
        )
        quantity = st.number_input(
            "枚数",
            min_value=0,
            max_value=999,
            value=int(initial.get("quantity") or 1),
            step=1,
            key=f"{prefix}_quantity",
        )
        source = st.text_input("入手元", value=str(initial.get("source", "")), key=f"{prefix}_source")

    location = st.text_input("保管場所", value=str(initial.get("location", "")), key=f"{prefix}_location")
    notes = st.text_area("メモ", value=str(initial.get("notes", "")), key=f"{prefix}_notes")

    return {
        "name": name.strip(),
        "series": series.strip(),
        "category": category.strip(),
        "rarity": rarity,
        "status": status,
        "quantity": quantity,
        "acquired_on": acquired_on.isoformat(),
        "source": source.strip(),
        "location": location.strip(),
        "notes": notes.strip(),
    }


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("絞り込み")
    keyword = st.sidebar.text_input("キーワード")
    series = st.sidebar.multiselect("シリーズ", sorted([x for x in df["series"].unique() if x]))
    status = st.sidebar.multiselect("状態", STATUS_OPTIONS)
    rarity = st.sidebar.multiselect("レア度", RARITY_OPTIONS)

    filtered = df.copy()
    if keyword:
        keyword_mask = filtered.astype(str).apply(
            lambda column: column.str.contains(keyword, case=False, na=False)
        )
        filtered = filtered[keyword_mask.any(axis=1)]
    if series:
        filtered = filtered[filtered["series"].isin(series)]
    if status:
        filtered = filtered[filtered["status"].isin(status)]
    if rarity:
        filtered = filtered[filtered["rarity"].isin(rarity)]
    return filtered


def show_metrics(df: pd.DataFrame) -> None:
    owned = df[df["status"] == "所持"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("登録数", f"{len(df):,}")
    col2.metric("所持種類", f"{len(owned):,}")
    col3.metric("合計枚数", f"{int(df['quantity'].sum()):,}")
    col4.metric("シリーズ数", f"{df['series'].replace('', pd.NA).dropna().nunique():,}")


def show_collection(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("まだ記録がありません。左の「追加」タブから最初のシールを登録しましょう。")
        return

    filtered = apply_filters(df)
    show_metrics(filtered)

    visible_columns = [
        "name",
        "series",
        "category",
        "rarity",
        "status",
        "quantity",
        "acquired_on",
        "source",
        "location",
        "notes",
    ]
    st.dataframe(
        filtered[visible_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "name": "シール名",
            "series": "シリーズ",
            "category": "カテゴリ",
            "rarity": "レア度",
            "status": "状態",
            "quantity": "枚数",
            "acquired_on": "入手日",
            "source": "入手元",
            "location": "保管場所",
            "notes": "メモ",
        },
    )


def show_add_tab() -> None:
    with st.form("add_form", clear_on_submit=True):
        record = record_form("add")
        submitted = st.form_submit_button("登録する", type="primary")
        if submitted:
            if not record["name"]:
                st.error("シール名を入力してください。")
            else:
                add_record(record)
                st.success("登録しました。")
                st.rerun()


def show_edit_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("編集できる記録がまだありません。")
        return

    labels = {
        row["id"]: f"{row['name']} / {row['series'] or 'シリーズ未設定'} / {row['status']}"
        for _, row in df.iterrows()
    }
    selected_id = st.selectbox("編集する記録", labels.keys(), format_func=lambda value: labels[value])
    selected = df[df["id"] == selected_id].iloc[0].to_dict()

    with st.form("edit_form"):
        record = record_form("edit", selected)
        col1, col2 = st.columns([1, 1])
        save_clicked = col1.form_submit_button("更新する", type="primary")
        delete_clicked = col2.form_submit_button("削除する")

        if save_clicked:
            if not record["name"]:
                st.error("シール名を入力してください。")
            else:
                update_record(selected_id, record)
                st.success("更新しました。")
                st.rerun()

        if delete_clicked:
            delete_record(selected_id)
            st.warning("削除しました。")
            st.rerun()


def show_backup_tab(df: pd.DataFrame) -> None:
    st.download_button(
        "CSVをダウンロード",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="sticker_collection.csv",
        mime="text/csv",
    )

    uploaded = st.file_uploader("CSVをインポート", type=["csv"])
    if uploaded is not None:
        try:
            imported = normalize_import(pd.read_csv(uploaded))
        except Exception as exc:
            st.error(f"CSVを読み込めませんでした: {exc}")
            return

        st.dataframe(imported.drop(columns=["id"]), use_container_width=True, hide_index=True)
        mode = st.radio("インポート方法", ["現在の記録に追加", "現在の記録を置き換え"], horizontal=True)
        if st.button("インポートを実行", type="primary"):
            if mode == "現在の記録に追加":
                combined = pd.concat([df, imported], ignore_index=True)
                save_data(combined)
            else:
                save_data(imported)
            st.success("インポートしました。")
            st.rerun()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="*", layout="wide")
    st.title(APP_TITLE)
    st.caption("集めたシール、探しているシール、交換予定のシールをまとめて管理できます。")

    df = load_data()
    tab_collection, tab_add, tab_edit, tab_backup = st.tabs(["一覧", "追加", "編集", "バックアップ"])

    with tab_collection:
        show_collection(df)
    with tab_add:
        show_add_tab()
    with tab_edit:
        show_edit_tab(df)
    with tab_backup:
        show_backup_tab(df)


if __name__ == "__main__":
    main()
