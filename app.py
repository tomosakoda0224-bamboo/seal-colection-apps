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
    "price",
    "status",
    "quantity",
    "acquired_on",
    "source",
    "location",
    "notes",
]

STATUS_OPTIONS = ["所持", "未所持", "交換予定", "探し中"]


def ensure_data_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_PATH.exists():
        pd.DataFrame(columns=COLUMNS).to_csv(DATA_PATH, index=False)


@st.cache_data
def load_data() -> pd.DataFrame:
    ensure_data_file()
    df = pd.read_csv(DATA_PATH, dtype={"id": "string"}).fillna("")
    if "price" not in df.columns:
        df["price"] = ""
    for column in COLUMNS:
        if column not in df.columns:
            df[column] = ""
    df = df[COLUMNS]
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0).astype(int)
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
    imported["price"] = (
        pd.to_numeric(imported["price"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    )
    return imported


def history_options(df: pd.DataFrame, column: str, current_value: str = "") -> list[str]:
    options = sorted({str(value).strip() for value in df[column].dropna() if str(value).strip()})
    if current_value and current_value not in options:
        options.insert(0, current_value)
    return options


def history_input(
    label: str,
    options: list[str],
    value: str,
    key: str,
) -> str:
    choices = [""]
    choices.extend(option for option in options if option)
    index = choices.index(value) if value in choices else 0
    return st.selectbox(
        label,
        choices,
        index=index,
        key=key,
        accept_new_options=True,
        placeholder="入力または候補から選択",
    )


def record_form(
    prefix: str,
    df: pd.DataFrame,
    initial: dict[str, object] | None = None,
) -> dict[str, object]:
    initial = initial or {}

    name = st.text_input("シール名", value=str(initial.get("name", "")), key=f"{prefix}_name")
    series_value = str(initial.get("series", "")).strip()
    series = history_input(
        "シリーズ",
        history_options(df, "series", series_value),
        series_value,
        key=f"{prefix}_series",
    )

    col1, col2 = st.columns(2)
    with col1:
        category = st.text_input("カテゴリ", value=str(initial.get("category", "")), key=f"{prefix}_category")
        price = st.number_input(
            "料金",
            min_value=0,
            max_value=999999,
            value=int(initial.get("price") or 0),
            step=1,
            key=f"{prefix}_price",
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
        source_value = str(initial.get("source", "")).strip()
        source = history_input(
            "入手元",
            history_options(df, "source", source_value),
            source_value,
            key=f"{prefix}_source",
        )

    location = st.text_input("保管場所", value=str(initial.get("location", "")), key=f"{prefix}_location")
    notes = st.text_area("メモ", value=str(initial.get("notes", "")), key=f"{prefix}_notes")

    return {
        "name": name.strip(),
        "series": series.strip(),
        "category": category.strip(),
        "price": price,
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
    source = st.sidebar.multiselect("入手元", sorted([x for x in df["source"].unique() if x]))
    status = st.sidebar.multiselect("状態", STATUS_OPTIONS)

    filtered = df.copy()
    if keyword:
        keyword_mask = filtered.astype(str).apply(
            lambda column: column.str.contains(keyword, case=False, na=False)
        )
        filtered = filtered[keyword_mask.any(axis=1)]
    if series:
        filtered = filtered[filtered["series"].isin(series)]
    if source:
        filtered = filtered[filtered["source"].isin(source)]
    if status:
        filtered = filtered[filtered["status"].isin(status)]
    return filtered


def show_metrics(df: pd.DataFrame) -> None:
    owned = df[df["status"] == "所持"]
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("登録数", f"{len(df):,}")
    col2.metric("所持種類", f"{len(owned):,}")
    col3.metric("合計枚数", f"{int(df['quantity'].sum()):,}")
    col4.metric("合計金額", f"{int(df['price'].sum()):,}円")
    col5.metric("シリーズ数", f"{df['series'].replace('', pd.NA).dropna().nunique():,}")


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
        "price",
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
            "price": st.column_config.NumberColumn("料金", format="%d円"),
            "status": "状態",
            "quantity": "枚数",
            "acquired_on": "入手日",
            "source": "入手元",
            "location": "保管場所",
            "notes": "メモ",
        },
    )


def show_add_tab(df: pd.DataFrame) -> None:
    with st.form("add_form", clear_on_submit=True):
        record = record_form("add", df)
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
    selected_id = st.selectbox("編集する記録", list(labels.keys()), format_func=lambda value: labels[value])
    selected = df[df["id"] == selected_id].iloc[0].to_dict()

    with st.form(f"edit_form_{selected_id}"):
        record = record_form(f"edit_{selected_id}", df, selected)
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
        show_add_tab(df)
    with tab_edit:
        show_edit_tab(df)
    with tab_backup:
        show_backup_tab(df)


if __name__ == "__main__":
    main()
