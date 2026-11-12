import json

import pandas as pd
import streamlit as st

from storage.experiment_store import (
    DEFAULT_DATA_DIR,
    delete_experiment,
    experiment_json,
    list_experiments,
    save_metadata,
)


st.set_page_config(page_title="Data Eksperimen ESP32", page_icon="🗂️", layout="wide")
st.title("Data Eksperimen ESP32")
st.caption("Kelola, tinjau, visualisasikan, dan ekspor rekaman yang sudah tersimpan.")

if st.sidebar.button("Muat ulang data"):
    st.rerun()

experiments = list_experiments()
if not experiments:
    st.info(f"Belum ada folder eksperimen di `{DEFAULT_DATA_DIR}`.")
    st.stop()

summary_rows = []
for experiment in experiments:
    metadata = experiment["metadata"]
    summary_rows.append({
        "Folder": experiment["folder"],
        "ID": metadata.get("experiment_id", experiment["folder"]),
        "Material": metadata.get("material", "(tanpa material)"),
        "Ketebalan (mm)": metadata.get("thickness_mm"),
        "Trial": metadata.get("trial"),
        "Sampel": len(experiment["samples"]),
        "Disimpan": metadata.get("saved_at", ""),
        "Validasi": "OK" if not experiment["errors"] else "Perlu diperiksa",
    })
summary = pd.DataFrame(summary_rows)

st.sidebar.header("Filter")
materials = sorted({str(value) for value in summary["Material"].dropna()})
selected_materials = st.sidebar.multiselect("Material", materials, default=materials)
search_text = st.sidebar.text_input("Cari ID atau nama folder").strip().lower()

visible_folders = set()
for row in summary_rows:
    if row["Material"] not in selected_materials:
        continue
    if search_text and search_text not in str(row["ID"]).lower() and search_text not in row["Folder"].lower():
        continue
    visible_folders.add(row["Folder"])
visible_experiments = [e for e in experiments if e["folder"] in visible_folders]
visible_summary = summary[summary["Folder"].isin(visible_folders)]

if not visible_experiments:
    st.warning("Tidak ada eksperimen yang cocok dengan filter.")
    st.stop()

total_samples = sum(len(experiment["samples"]) for experiment in visible_experiments)
metric_a, metric_b, metric_c = st.columns(3)
metric_a.metric("Eksperimen", len(visible_experiments))
metric_b.metric("Total sampel", f"{total_samples:,}")
metric_c.metric("Material", visible_summary["Material"].nunique())

tab_visual, tab_manage, tab_json = st.tabs(["Visualisasi", "Manajemen", "JSON & API"])
folder_options = [experiment["folder"] for experiment in visible_experiments]
experiment_by_folder = {experiment["folder"]: experiment for experiment in experiments}

with tab_visual:
    st.subheader("Ringkasan data tersimpan")
    st.dataframe(visible_summary, use_container_width=True, hide_index=True)

    experiment_for_chart = st.selectbox(
        "Pilih rekaman untuk grafik detail",
        folder_options,
        format_func=lambda folder: (
            f"{experiment_by_folder[folder]['metadata'].get('experiment_id', folder)} · "
            f"{experiment_by_folder[folder]['metadata'].get('material', 'tanpa material')} · {folder}"
        ),
        key="chart_experiment",
    )
    selected_experiment = experiment_by_folder[experiment_for_chart]
    selected_samples = selected_experiment["samples"]
    if selected_experiment["errors"]:
        st.warning("; ".join(selected_experiment["errors"]))
    if selected_samples:
        frame = pd.DataFrame(selected_samples)
        numeric_columns = [column for column in ("raw_value", "baseline") if column in frame]
        if "elapsed_seconds" in frame and numeric_columns:
            st.line_chart(frame.set_index("elapsed_seconds")[numeric_columns], height=320)
        average_columns = st.columns(4)
        for column, label, container in zip(
            ("raw_value", "baseline", "delta", "delta_percent"),
            ("Rata-rata raw value", "Rata-rata baseline", "Rata-rata delta", "Rata-rata delta percent"),
            average_columns,
        ):
            values = (
                pd.to_numeric(frame[column], errors="coerce")
                if column in frame else pd.Series(dtype="float64")
            )
            container.metric(label, f"{values.mean():.4f}" if values.notna().any() else "—")

        detail_a, detail_b = st.columns(2)
        detail_a.metric("Sampel rekaman", f"{len(frame):,}")
        detail_b.metric("Raw minimum–maksimum", (
            f"{pd.to_numeric(frame['raw_value'], errors='coerce').min():.2f} – "
            f"{pd.to_numeric(frame['raw_value'], errors='coerce').max():.2f}"
        ) if "raw_value" in frame else "—")
        with st.expander("Lihat sampel", expanded=False):
            st.dataframe(frame, use_container_width=True, hide_index=True)
    else:
        st.info("Rekaman CSV belum tersedia atau belum berisi sampel.")

    st.subheader("Perbandingan delta percent antar eksperimen")
    comparison_rows = []
    for experiment in visible_experiments:
        samples = pd.DataFrame(experiment["samples"])
        if samples.empty or "delta_percent" not in samples:
            continue
        values = pd.to_numeric(samples["delta_percent"], errors="coerce").dropna()
        if not values.empty:
            comparison_rows.append({
                "Eksperimen": experiment["metadata"].get("experiment_id", experiment["folder"]),
                "Material": experiment["metadata"].get("material", "(tanpa material)"),
                "Rata-rata delta percent (%)": values.mean(),
            })
    if comparison_rows:
        comparison = pd.DataFrame(comparison_rows)
        st.bar_chart(comparison, x="Eksperimen", y="Rata-rata delta percent (%)", color="Material")
        st.caption("Setiap batang menunjukkan rata-rata delta percent dari satu eksperimen.")
    else:
        st.info("Belum ada kolom delta_percent yang dapat dibandingkan.")

with tab_manage:
    st.subheader("Edit metadata")
    folder_to_edit = st.selectbox(
        "Eksperimen",
        folder_options,
        format_func=lambda folder: f"{experiment_by_folder[folder]['metadata'].get('experiment_id', folder)} · {folder}",
        key="edit_experiment",
    )
    edit_experiment = experiment_by_folder[folder_to_edit]
    metadata = edit_experiment["metadata"]
    with st.form("metadata_form"):
        st.text_input("Experiment ID", value=str(metadata.get("experiment_id", "")), disabled=True)
        operator = st.text_input("Operator", value=str(metadata.get("operator", "") or ""))
        material = st.text_input("Material", value=str(metadata.get("material", "") or ""))
        electrode = st.text_input("Elektroda", value=str(metadata.get("electrode", "") or ""))
        thickness = st.number_input(
            "Ketebalan (mm)", min_value=0.0,
            value=max(0.0, float(metadata.get("thickness_mm") or 0)), step=0.1,
        )
        trial = st.number_input(
            "Trial", min_value=1, value=max(1, int(metadata.get("trial") or 1)), step=1,
        )
        save_clicked = st.form_submit_button("Simpan perubahan metadata")
    if save_clicked:
        updated = dict(metadata)
        updated.update({
            "operator": operator.strip(),
            "material": material.strip(),
            "electrode": electrode.strip(),
            "thickness_mm": float(thickness),
            "trial": int(trial),
        })
        try:
            save_metadata(edit_experiment, updated)
            st.success("Metadata berhasil diperbarui.")
            st.rerun()
        except (OSError, TypeError, ValueError) as exc:
            st.error(f"Gagal menyimpan metadata: {exc}")

    st.divider()
    st.subheader("Hapus eksperimen")
    st.caption("Tindakan ini menghapus folder eksperimen beserta metadata dan CSV-nya.")
    confirm_delete = st.checkbox(f"Saya yakin ingin menghapus {folder_to_edit}", key="confirm_delete")
    if st.button("Hapus folder eksperimen", type="secondary", disabled=not confirm_delete):
        try:
            delete_experiment(edit_experiment)
            st.session_state.confirm_delete = False
            st.success(f"Eksperimen {folder_to_edit} berhasil dihapus.")
            st.rerun()
        except (OSError, ValueError) as exc:
            st.error(f"Gagal menghapus eksperimen: {exc}")

with tab_json:
    st.subheader("Ekspor data sebagai JSON")
    folder_for_json = st.selectbox(
        "Eksperimen JSON",
        folder_options,
        format_func=lambda folder: f"{experiment_by_folder[folder]['metadata'].get('experiment_id', folder)} · {folder}",
        key="json_experiment",
    )
    json_payload = experiment_json(experiment_by_folder[folder_for_json])
    json_bytes = json.dumps(json_payload, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    st.download_button(
        "Download eksperimen JSON",
        data=json_bytes,
        file_name=f"{folder_for_json}.json",
        mime="application/json",
        key="download_one_json",
    )
    with st.expander("Pratinjau JSON eksperimen", expanded=False):
        st.json(json_payload)

    all_payload = [experiment_json(experiment) for experiment in visible_experiments]
    all_json_bytes = json.dumps(all_payload, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    st.download_button(
        "Download semua eksperimen terfilter (JSON)",
        data=all_json_bytes,
        file_name="experiments.json",
        mime="application/json",
        key="download_all_json",
    )

    st.subheader("HTTP JSON API")
    st.markdown(
        "Jalankan server API di terminal terpisah dengan `python serve_json.py`. "
        "Default-nya hanya bisa diakses dari komputer ini."
    )
    st.code(
        "GET http://127.0.0.1:8765/api/experiments\n"
        "GET http://127.0.0.1:8765/api/experiments/<nama-folder>\n"
        "GET http://127.0.0.1:8765/api/experiments/<nama-folder>/metadata\n"
        "GET http://127.0.0.1:8765/api/health",
        language="text",
    )
    st.caption("Respons detail berisi metadata dan array `samples` dari recording.csv.")
