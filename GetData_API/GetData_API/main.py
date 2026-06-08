import json
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from api_tool import ApiError, build_params, call_api
from db import (
    delete_api,
    get_api,
    init_db,
    load_api_parameters,
    load_apis,
    save_api,
    save_api_parameters,
)
from excel_loader import load_excel_file


class BatchWorker(QThread):
    progress = Signal(int, int, int)
    result = Signal(int, object)
    finishedSignal = Signal()
    error = Signal(int, str)

    def __init__(self, api_url, method, parameter_rows, data_frame, verify=True):
        super().__init__()
        self.api_url = api_url
        self.method = method
        self.parameter_rows = parameter_rows
        self.data_frame = data_frame
        self.verify = verify

    def run(self):
        total = len(self.data_frame)
        success = 0
        failure = 0

        for index, row in self.data_frame.iterrows():
            params = build_params(self.parameter_rows, row)
            if not params:
                failure += 1
                self.error.emit(index + 1, f"第 {index + 1} 筆資料無可用參數。")
                self.progress.emit(total, success, failure)
                continue

            try:
                response = call_api(self.api_url, self.method, params, verify=self.verify)
                self.result.emit(index + 1, response)
                success += 1
            except ApiError as exc:
                failure += 1
                self.error.emit(index + 1, f"第 {index + 1} 筆 API 失敗：{exc}")
            self.progress.emit(total, success, failure)

        self.finishedSignal.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("API批次查詢工具")
        self.resize(1200, 760)

        init_db()
        self.data_frame = None
        self.excel_columns = []
        self.current_api_id = None
        self.batch_results = []

        self._create_actions()
        self._create_widgets()
        self._create_layout()
        self._connect_signals()
        self._load_api_profiles()

    def _create_actions(self):
        self.open_action = QAction("開啟 Excel", self)
        self.exit_action = QAction("離開", self)

    def _create_widgets(self):
        self.api_profile_combo = QComboBox()
        self.new_api_button = QPushButton("新 API")
        self.save_api_button = QPushButton("儲存 API")
        self.delete_api_button = QPushButton("刪除 API")

        self.api_name_input = QLineEdit()
        self.api_url_input = QLineEdit()
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST"])

        self.add_param_button = QPushButton("新增參數")
        self.delete_param_button = QPushButton("刪除參數")
        self.auto_map_button = QPushButton("自動對應")
        self.param_table = QTableWidget(0, 3)
        self.param_table.setHorizontalHeaderLabels(["參數名稱", "來源欄位", "固定值"])
        self.param_table.horizontalHeader().setStretchLastSection(True)

        self.load_excel_button = QPushButton("選擇 Excel")
        self.excel_preview = QTableWidget(0, 0)
        self.excel_preview.setEditTriggers(QTableWidget.NoEditTriggers)

        self.test_api_button = QPushButton("測試 API")
        self.batch_query_button = QPushButton("執行批次")
        self.export_results_button = QPushButton("匯出結果")
        self.export_results_button.setEnabled(False)
        self.skip_ssl_checkbox = QCheckBox("跳過 SSL 驗證（已預設勾選，僅測試用）")
        self.skip_ssl_checkbox.setChecked(True)

        self.status_label = QLabel("尚未載入 Excel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        self.results_table = QTableWidget(0, 2)
        self.results_table.setHorizontalHeaderLabels(["序號", "結果"])
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.horizontalHeader().setStretchLastSection(True)

    def _create_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("API設定："))
        profile_layout.addWidget(self.api_profile_combo)
        profile_layout.addWidget(self.new_api_button)
        profile_layout.addWidget(self.save_api_button)
        profile_layout.addWidget(self.delete_api_button)

        form_layout = QFormLayout()
        form_layout.addRow("API名稱：", self.api_name_input)
        form_layout.addRow("API URL：", self.api_url_input)
        form_layout.addRow("Method：", self.method_combo)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_param_button)
        button_layout.addWidget(self.delete_param_button)
        button_layout.addWidget(self.auto_map_button)
        button_layout.addStretch()

        left_layout = QVBoxLayout()
        left_layout.addLayout(profile_layout)
        left_layout.addLayout(form_layout)
        left_layout.addLayout(button_layout)
        left_layout.addWidget(self.param_table)
        left_layout.addWidget(self.load_excel_button)
        left_layout.addWidget(QLabel("Excel 資料預覽："))
        left_layout.addWidget(self.excel_preview)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.test_api_button)
        right_layout.addWidget(self.skip_ssl_checkbox)
        right_layout.addWidget(self.batch_query_button)
        right_layout.addWidget(self.export_results_button)
        right_layout.addWidget(self.status_label)
        right_layout.addWidget(self.progress_bar)
        right_layout.addWidget(QLabel("執行記錄："))
        right_layout.addWidget(self.log_output)
        right_layout.addWidget(QLabel("查詢結果："))
        right_layout.addWidget(self.results_table)
        right_layout.addWidget(QLabel("結果詳情："))
        self.result_detail = QTextEdit()
        self.result_detail.setReadOnly(True)
        right_layout.addWidget(self.result_detail)

        main_layout = QGridLayout(central_widget)
        main_layout.addLayout(left_layout, 0, 0)
        main_layout.addLayout(right_layout, 0, 1)
        main_layout.setColumnStretch(0, 2)
        main_layout.setColumnStretch(1, 1)

    def _connect_signals(self):
        self.api_profile_combo.currentIndexChanged.connect(self._on_api_profile_selected)
        self.new_api_button.clicked.connect(self._new_api_profile)
        self.save_api_button.clicked.connect(self._save_api_profile)
        self.delete_api_button.clicked.connect(self._delete_api_profile)
        self.add_param_button.clicked.connect(self._add_parameter_row)
        self.delete_param_button.clicked.connect(self._delete_parameter_rows)
        self.auto_map_button.clicked.connect(self._auto_map_parameters)
        self.load_excel_button.clicked.connect(self._load_excel)
        self.test_api_button.clicked.connect(self._test_api)
        self.batch_query_button.clicked.connect(self._run_batch)
        self.export_results_button.clicked.connect(self._export_results)
        self.results_table.cellClicked.connect(self._on_result_selected)

    def _create_source_column_widget(self, value=""):
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItem("")
        combo.addItems(self.excel_columns)
        if value:
            combo.setCurrentText(value)
        return combo

    def _add_parameter_row(self, parameter=None):
        row = self.param_table.rowCount()
        self.param_table.insertRow(row)
        self.param_table.setItem(row, 0, QTableWidgetItem(parameter.get("parameter_name", "") if parameter else ""))
        self.param_table.setCellWidget(row, 1, self._create_source_column_widget(parameter.get("source_column", "") if parameter else ""))
        self.param_table.setItem(row, 2, QTableWidgetItem(parameter.get("default_value", "") if parameter else ""))

    def _delete_parameter_rows(self):
        selected = sorted({idx.row() for idx in self.param_table.selectedIndexes()}, reverse=True)
        for row in selected:
            self.param_table.removeRow(row)

    def _normalize_text(self, text):
        return "".join(ch for ch in str(text).lower() if ch.isalnum())

    def _build_response_summary(self, response):
        if isinstance(response, dict):
            keys = list(response.keys())[:4]
            preview = ", ".join(f"{k}:{str(response[k])[:15]}" for k in keys)
            return f"dict({len(response)} keys) {preview}"
        if isinstance(response, list):
            if not response:
                return "list(0)"
            first = response[0]
            if isinstance(first, dict):
                return f"list({len(response)}) dict first keys: {list(first.keys())[:4]}"
            return f"list({len(response)}) {type(first).__name__}"
        return str(response)[:120]

    def _flatten_batch_result(self, item):
        if item["error"]:
            return pd.DataFrame(
                [{
                    "序號": item["index"],
                    "狀態": "失敗",
                    "錯誤": item["error"],
                }]
            )

        response = item["response"]
        if isinstance(response, list):
            if response and all(isinstance(record, dict) for record in response):
                df = pd.json_normalize(response)
                df.insert(0, "序號", item["index"])
                df.insert(1, "結果索引", range(1, len(df) + 1))
                df["錯誤"] = ""
                return df
            return pd.DataFrame(
                [
                    {
                        "序號": item["index"],
                        "結果值": json.dumps(response, ensure_ascii=False),
                        "錯誤": "",
                    }
                ]
            )

        if isinstance(response, dict):
            df = pd.json_normalize(response)
            df.insert(0, "序號", item["index"])
            df["錯誤"] = ""
            return df

        return pd.DataFrame(
            [
                {
                    "序號": item["index"],
                    "結果值": str(response),
                    "錯誤": "",
                }
            ]
        )

    def _auto_map_parameters(self):
        if not self.excel_columns:
            QMessageBox.warning(self, "無 Excel 欄位", "請先載入 Excel 資料，才能執行自動對應。")
            return

        normalized_columns = {self._normalize_text(col): col for col in self.excel_columns}
        updated = 0
        for row_index in range(self.param_table.rowCount()):
            name_item = self.param_table.item(row_index, 0)
            if not name_item:
                continue
            parameter_name = name_item.text().strip()
            if not parameter_name:
                continue

            source_widget = self.param_table.cellWidget(row_index, 1)
            current_source = source_widget.currentText().strip() if isinstance(source_widget, QComboBox) else ""
            if current_source:
                continue

            normalized_name = self._normalize_text(parameter_name)
            if normalized_name in normalized_columns:
                source_widget.setCurrentText(normalized_columns[normalized_name])
                updated += 1
                continue

            # try partial matches
            for normalized_col, original_col in normalized_columns.items():
                if normalized_name == normalized_col or normalized_name in normalized_col or normalized_col in normalized_name:
                    source_widget.setCurrentText(original_col)
                    updated += 1
                    break

        self.log_output.append(f"自動對應完成，已更新 {updated} 個參數來源欄位。")

    def _on_result_selected(self, row, column):
        if row < 0 or row >= len(self.batch_results):
            return
        item = self.batch_results[row]
        if item["error"]:
            self.result_detail.setPlainText(item["error"])
            return
        result = item["response"]
        self.result_detail.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))

    def _clear_parameter_table(self):
        self.param_table.setRowCount(0)

    def _load_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "選擇 Excel 檔案", str(Path.home()), "Excel Files (*.xlsx *.xls)")
        if not file_path:
            return

        try:
            self.data_frame = load_excel_file(file_path)
            self.excel_columns = list(self.data_frame.columns)
            self._update_preview()
            self._refresh_source_column_options()
            self.status_label.setText(f"已載入 Excel：{Path(file_path).name}，共 {len(self.data_frame)} 筆資料")
            self.log_output.append(f"已載入 Excel：{file_path}")
        except Exception as exc:
            QMessageBox.warning(self, "讀取失敗", f"無法讀取 Excel：{exc}")

    def _update_preview(self):
        if self.data_frame is None or self.data_frame.empty:
            self.excel_preview.setRowCount(0)
            self.excel_preview.setColumnCount(0)
            return

        self.excel_preview.setColumnCount(len(self.data_frame.columns))
        self.excel_preview.setRowCount(min(10, len(self.data_frame)))
        self.excel_preview.setHorizontalHeaderLabels(list(self.data_frame.columns))

        for row_index in range(min(10, len(self.data_frame))):
            for col_index, column_name in enumerate(self.data_frame.columns):
                value = str(self.data_frame.iat[row_index, col_index])
                self.excel_preview.setItem(row_index, col_index, QTableWidgetItem(value))

    def _refresh_source_column_options(self):
        for row_index in range(self.param_table.rowCount()):
            widget = self.param_table.cellWidget(row_index, 1)
            if isinstance(widget, QComboBox):
                current_text = widget.currentText()
                widget.clear()
                widget.addItem("")
                widget.addItems(self.excel_columns)
                widget.setCurrentText(current_text)

    def _collect_parameter_rows(self):
        rows = []
        for row_index in range(self.param_table.rowCount()):
            name_item = self.param_table.item(row_index, 0)
            source_widget = self.param_table.cellWidget(row_index, 1)
            default_item = self.param_table.item(row_index, 2)
            source = ""
            if isinstance(source_widget, QComboBox):
                source = source_widget.currentText().strip()
            else:
                source = source_item.text().strip() if source_item else ""
            rows.append(
                {
                    "parameter_name": name_item.text().strip() if name_item else "",
                    "source_column": source,
                    "default_value": default_item.text().strip() if default_item else "",
                }
            )
        return rows

    def _test_api(self):
        if self.data_frame is None or self.data_frame.empty:
            QMessageBox.warning(self, "未載入資料", "請先載入 Excel 資料。")
            return

        api_url = self.api_url_input.text().strip()
        method = self.method_combo.currentText()
        if not api_url:
            QMessageBox.warning(self, "未設定 API", "請輸入 API URL。")
            return

        parameter_rows = self._collect_parameter_rows()
        first_row = self.data_frame.iloc[0].to_dict()
        params = build_params(parameter_rows, first_row)
        if not params:
            QMessageBox.warning(self, "參數不足", "請設定 API 參數對應欄位或固定值。")
            return

        verify = not self.skip_ssl_checkbox.isChecked()
        self.log_output.append(f"測試 API URL：{api_url}")
        self.log_output.append(f"測試 API 參數：{params}")
        self.log_output.append(f"SSL 驗證：{'啟用' if verify else '已跳過'}")
        try:
            response = call_api(api_url, method, params, verify=verify)
            self.log_output.append("=== 測試 API 成功 ===")
            self.log_output.append(json.dumps(response, ensure_ascii=False, indent=2))
            self.status_label.setText("API 測試成功")
        except ApiError as exc:
            message = str(exc)
            QMessageBox.warning(self, "API 呼叫失敗", message)
            self.log_output.append(f"API 測試失敗：{message}")
            if message.startswith("伺服器內部錯誤"):
                self.status_label.setText("伺服器內部錯誤，請稍後再試")
            else:
                self.status_label.setText("API 測試失敗")

    def _load_api_profiles(self, selected_api_id=None):
        self.api_profile_combo.blockSignals(True)
        self.api_profile_combo.clear()
        self.api_profile_combo.addItem("(新增 API)", None)
        for api in load_apis():
            self.api_profile_combo.addItem(api["api_name"], api["id"])
        self.api_profile_combo.blockSignals(False)

        if selected_api_id is None:
            self.api_profile_combo.setCurrentIndex(0)
        else:
            self._select_api_profile(selected_api_id)

    def _on_api_profile_selected(self, index):
        api_id = self.api_profile_combo.itemData(index)
        if api_id is None:
            self._new_api_profile()
            return

        api = get_api(api_id)
        if not api:
            return

        self.current_api_id = api_id
        self.api_name_input.setText(api["api_name"])
        self.api_url_input.setText(api["api_url"])
        self.method_combo.setCurrentText(api["method"])
        self._clear_parameter_table()

        parameters = load_api_parameters(api_id)
        for parameter in parameters:
            self._add_parameter_row(
                {
                    "parameter_name": parameter["parameter_name"],
                    "source_column": parameter["source_column"],
                    "default_value": parameter["default_value"],
                }
            )
        self._refresh_source_column_options()

    def _save_api_profile(self):
        api_name = self.api_name_input.text().strip()
        api_url = self.api_url_input.text().strip()
        method = self.method_combo.currentText()

        if not api_name:
            QMessageBox.warning(self, "未設定 API 名稱", "請輸入 API 名稱。")
            return
        if not api_url:
            QMessageBox.warning(self, "未設定 API URL", "請輸入 API URL。")
            return

        parameter_rows = [row for row in self._collect_parameter_rows() if row["parameter_name"]]
        if not parameter_rows:
            QMessageBox.warning(self, "未設定參數", "請至少新增一筆 API 參數。")
            return

        self.current_api_id = save_api(api_name, api_url, method, self.current_api_id)
        save_api_parameters(self.current_api_id, parameter_rows)
        self.log_output.append(f"已儲存 API：{api_name}")
        self.status_label.setText("API 設定已儲存")
        self._load_api_profiles(self.current_api_id)

    def _select_api_profile(self, api_id):
        for index in range(self.api_profile_combo.count()):
            if self.api_profile_combo.itemData(index) == api_id:
                self.api_profile_combo.setCurrentIndex(index)
                return

    def _new_api_profile(self):
        self.current_api_id = None
        self.api_profile_combo.blockSignals(True)
        self.api_profile_combo.setCurrentIndex(0)
        self.api_profile_combo.blockSignals(False)
        self.api_name_input.clear()
        self.api_url_input.clear()
        self.method_combo.setCurrentIndex(0)
        self._clear_parameter_table()
        self._reset_results()
        self.status_label.setText("已建立新 API 設定")

    def _delete_api_profile(self):
        if self.current_api_id is None:
            QMessageBox.warning(self, "未選取 API", "請先選擇要刪除的 API。")
            return

        confirm = QMessageBox.question(
            self,
            "刪除 API",
            f"確定要刪除 API：{self.api_name_input.text()}？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        delete_api(self.current_api_id)
        self.log_output.append(f"已刪除 API：{self.api_name_input.text()}")
        self._load_api_profiles()
        self._new_api_profile()
        self.status_label.setText("API 已刪除")

    def _reset_results(self):
        self.batch_results = []
        self.results_table.setRowCount(0)
        self.export_results_button.setEnabled(False)

    def _run_batch(self):
        if self.data_frame is None or self.data_frame.empty:
            QMessageBox.warning(self, "未載入資料", "請先載入 Excel 資料。")
            return

        api_url = self.api_url_input.text().strip()
        method = self.method_combo.currentText()
        if not api_url:
            QMessageBox.warning(self, "未設定 API", "請輸入 API URL。")
            return

        parameter_rows = [row for row in self._collect_parameter_rows() if row["parameter_name"]]
        if not parameter_rows:
            QMessageBox.warning(self, "未設定參數", "請先新增至少一個 API 參數。")
            return

        self._reset_results()
        self.batch_query_button.setEnabled(False)
        verify = not self.skip_ssl_checkbox.isChecked()
        self.log_output.append(f"批次 API URL：{api_url}")
        self.log_output.append(f"批次 API 參數：{parameter_rows}")
        self.log_output.append(f"SSL 驗證：{'啟用' if verify else '已跳過'}")
        self.worker = BatchWorker(api_url, method, parameter_rows, self.data_frame, verify=verify)
        self.worker.progress.connect(self._on_batch_progress)
        self.worker.result.connect(self._on_batch_result)
        self.worker.error.connect(self._on_batch_error)
        self.worker.finishedSignal.connect(self._on_batch_finished)
        self.worker.start()

    @Slot(int, int, int)
    def _on_batch_progress(self, total, success, failure):
        if total:
            progress = int((success + failure) / total * 100)
            self.progress_bar.setValue(progress)
            self.status_label.setText(f"總筆數：{total}，成功：{success}，失敗：{failure}")

    @Slot(int, object)
    def _on_batch_result(self, index, response):
        self.batch_results.append({"index": index, "response": response, "error": None})
        self.log_output.append(f"第 {index} 筆成功：")
        if isinstance(response, (dict, list)):
            self.log_output.append(json.dumps(response, ensure_ascii=False, indent=2))
        else:
            self.log_output.append(str(response))

        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(str(index)))
        self.results_table.setItem(row, 1, QTableWidgetItem(self._build_response_summary(response)))

    @Slot(int, str)
    def _on_batch_error(self, index, message):
        self.batch_results.append({"index": index, "response": None, "error": message})
        self.log_output.append(f"第 {index} 筆失敗：{message}")
        if "伺服器內部錯誤" in message:
            self.status_label.setText("批次執行發生伺服器錯誤")

        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(str(index)))
        self.results_table.setItem(row, 1, QTableWidgetItem(f"失敗：{message}"))

    @Slot()
    def _on_batch_finished(self):
        self.batch_query_button.setEnabled(True)
        self.export_results_button.setEnabled(bool(self.batch_results))
        self.status_label.setText("批次執行完成")

    def _export_results(self):
        if not self.batch_results:
            QMessageBox.warning(self, "無結果可匯出", "請先執行批次查詢，才可匯出結果。")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出查詢結果",
            str(Path.home() / "api_batch_results.xlsx"),
            "Excel Files (*.xlsx)",
        )
        if not file_path:
            return

        try:
            frames = [self._flatten_batch_result(item) for item in self.batch_results]
            df = pd.concat(frames, ignore_index=True, sort=False).fillna("")
            df.to_excel(file_path, index=False)
            self.log_output.append(f"已匯出結果：{file_path}")
            self.status_label.setText("結果已匯出")
        except Exception as exc:
            QMessageBox.warning(self, "匯出失敗", f"無法匯出結果：{exc}")
            self.log_output.append(f"匯出失敗：{exc}")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
