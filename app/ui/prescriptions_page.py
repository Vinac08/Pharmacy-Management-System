# app/ui/prescriptions_page.py
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QComboBox, QScrollArea, QFrame, QSizePolicy, QSpacerItem,
    QTextEdit, QDateEdit, QCheckBox
)
from PySide6.QtCore import Qt, QDate

from app.dao.prescriptions_dao import PrescriptionsDao


class PrescriptionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.dao = PrescriptionsDao()

        self._cached_rows: list[tuple] = []
        self.search_text: str = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignTop)

        title = QLabel("Prescriptions")
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        root.addWidget(title)

        subtitle = QLabel("")
        subtitle.setStyleSheet("color:#666;")
        root.addWidget(subtitle)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.clicked.connect(self.load_table)

        self.btn_add = QPushButton("Add")
        self.btn_add.setFixedHeight(32)
        self.btn_add.clicked.connect(self.add_prescription)

        self.btn_update = QPushButton("Update selected")
        self.btn_update.setFixedHeight(32)
        self.btn_update.clicked.connect(self.update_selected)

        self.btn_delete = QPushButton("Delete selected")
        self.btn_delete.setFixedHeight(32)
        self.btn_delete.clicked.connect(self.delete_selected)

        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_update)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        # Search
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        lbl = QLabel("Search:")
        lbl.setStyleSheet("color:#555; font-weight:600;")
        search_row.addWidget(lbl)

        self.search_le = QLineEdit()
        self.search_le.setPlaceholderText("Search by customer, doctor, details…")
        self.search_le.setFixedHeight(32)
        self.search_le.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_le, stretch=1)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedHeight(32)
        btn_clear.clicked.connect(lambda: self.search_le.setText(""))
        search_row.addWidget(btn_clear)

        root.addLayout(search_row)

        # Form (scrollable)
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setFrameShape(QFrame.NoFrame)
        form_scroll.setFixedHeight(90)  # ✅ reduced from 110

        form_container = QWidget()
        form = QHBoxLayout(form_container)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        # customer dropdown
        self.customer_cb = QComboBox()
        self.customer_cb.setMinimumWidth(220)  # ✅ was 260
        self.customer_cb.setFixedHeight(32)
        form.addWidget(self.customer_cb)

        self.doctor_in = QLineEdit()
        self.doctor_in.setPlaceholderText("doctor name (required)")
        self.doctor_in.setMinimumWidth(200)  # ✅ was 220
        self.doctor_in.setFixedHeight(32)
        form.addWidget(self.doctor_in)

        self.date_issued = QDateEdit()
        self.date_issued.setCalendarPopup(True)
        self.date_issued.setFixedHeight(32)
        self.date_issued.setDisplayFormat("yyyy-MM-dd")
        self.date_issued.setDate(QDate.currentDate())  # default today
        form.addWidget(self.date_issued)

        self.valid_chk = QCheckBox("Has valid till")
        self.valid_chk.setChecked(False)
        self.valid_chk.stateChanged.connect(self._toggle_valid_till)
        form.addWidget(self.valid_chk)

        self.valid_till = QDateEdit()
        self.valid_till.setCalendarPopup(True)
        self.valid_till.setFixedHeight(32)
        self.valid_till.setDisplayFormat("yyyy-MM-dd")
        self.valid_till.setDate(QDate.currentDate())
        self.valid_till.setEnabled(False)
        form.addWidget(self.valid_till)

        # ✅ smaller details box (height + width)
        self.details_in = QTextEdit()
        self.details_in.setPlaceholderText("details (optional)")
        self.details_in.setFixedHeight(48)      # ✅ was 70
        self.details_in.setMinimumWidth(150)    # ✅ was 320
        form.addWidget(self.details_in)

        form.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        form_scroll.setWidget(form_container)
        root.addWidget(form_scroll)

        # Table
        self.headers = [
            "prescription_id", "customer_id", "customer_name",
            "doctor_name", "date_issued", "valid_till", "details"
        ]
        self.table = QTableWidget(0, len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._fill_form_from_selected)
        root.addWidget(self.table, stretch=1)

        self._load_customers_dropdown()
        self.load_table()

    # --------------------
    # Helpers
    # --------------------
    def _toggle_valid_till(self):
        self.valid_till.setEnabled(self.valid_chk.isChecked())

    def _load_customers_dropdown(self):
        self.customer_cb.blockSignals(True)
        self.customer_cb.clear()
        self.customer_cb.addItem("Select customer_id…", None)
        for cid, label in self.dao.list_customers_for_dropdown():
            self.customer_cb.addItem(label, cid)
        self.customer_cb.blockSignals(False)

    def _current_customer_id(self) -> int | None:
        cid = self.customer_cb.currentData()
        return int(cid) if cid is not None else None

    def _current_prescription_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except Exception:
            return None

    def _qdate_to_date(self, qd: QDate) -> date:
        return date(qd.year(), qd.month(), qd.day())

    def _on_search_changed(self, text: str):
        self.search_text = (text or "").strip().lower()
        self._render_rows()

    def _render_rows(self):
        rows = self._cached_rows
        if self.search_text:
            q = self.search_text
            filtered = []
            for r in rows:
                # r = (id, customer_id, customer_name, doctor_name, date_issued, valid_till, details)
                hay = " ".join([
                    str(r[1] or ""),
                    str(r[2] or ""),
                    str(r[3] or ""),
                    str(r[6] or ""),
                ]).lower()
                if q in hay:
                    filtered.append(r)
            rows = filtered

        self.table.setRowCount(0)
        for r in rows:
            row_i = self.table.rowCount()
            self.table.insertRow(row_i)
            for c_i, val in enumerate(r):
                self.table.setItem(row_i, c_i, QTableWidgetItem("" if val is None else str(val)))
        self.table.resizeColumnsToContents()

    # --------------------
    # Load
    # --------------------
    def load_table(self):
        self._cached_rows = self.dao.fetch_all(limit=200)
        self._render_rows()
        self._load_customers_dropdown()

    def _fill_form_from_selected(self):
        pid = self._current_prescription_id()
        if not pid:
            return

        row = self.dao.fetch_one(pid)
        if not row:
            return

        prescription_id, customer_id, doctor_name, date_issued, valid_till, details = row

        # set dropdown
        idx = self.customer_cb.findData(int(customer_id))
        if idx >= 0:
            self.customer_cb.setCurrentIndex(idx)

        self.doctor_in.setText("" if doctor_name is None else str(doctor_name))

        if date_issued:
            self.date_issued.setDate(QDate(date_issued.year, date_issued.month, date_issued.day))
        else:
            self.date_issued.setDate(QDate.currentDate())

        if valid_till:
            self.valid_chk.setChecked(True)
            self.valid_till.setEnabled(True)
            self.valid_till.setDate(QDate(valid_till.year, valid_till.month, valid_till.day))
        else:
            self.valid_chk.setChecked(False)
            self.valid_till.setEnabled(False)
            self.valid_till.setDate(QDate.currentDate())

        self.details_in.setPlainText("" if details is None else str(details))

    def _clear_form(self):
        self.customer_cb.setCurrentIndex(0)
        self.doctor_in.clear()
        self.date_issued.setDate(QDate.currentDate())
        self.valid_chk.setChecked(False)
        self.valid_till.setEnabled(False)
        self.valid_till.setDate(QDate.currentDate())
        self.details_in.clear()

    # --------------------
    # Actions
    # --------------------
    def add_prescription(self):
        cid = self._current_customer_id()
        if not cid:
            QMessageBox.information(self, "Missing", "Select a customer_id first.")
            return

        doctor = (self.doctor_in.text() or "").strip()
        if not doctor:
            QMessageBox.information(self, "Missing", "doctor_name is required.")
            return

        issued = self._qdate_to_date(self.date_issued.date())
        vt = self._qdate_to_date(self.valid_till.date()) if self.valid_chk.isChecked() else None
        details = self.details_in.toPlainText()

        try:
            new_id = self.dao.insert(
                customer_id=cid,
                doctor_name=doctor,
                date_issued=issued,
                valid_till=vt,
                details=details,
            )
            QMessageBox.information(self, "Created", f"Prescription created ✅ (prescription_id={new_id})")
            self.load_table()
            self._clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def update_selected(self):
        pid = self._current_prescription_id()
        if not pid:
            QMessageBox.information(self, "Info", "Select a prescription row first.")
            return

        cid = self._current_customer_id()
        if not cid:
            QMessageBox.information(self, "Missing", "Select a customer_id first.")
            return

        doctor = (self.doctor_in.text() or "").strip()
        if not doctor:
            QMessageBox.information(self, "Missing", "doctor_name is required.")
            return

        issued = self._qdate_to_date(self.date_issued.date())
        vt = self._qdate_to_date(self.valid_till.date()) if self.valid_chk.isChecked() else None
        details = self.details_in.toPlainText()

        try:
            self.dao.update(
                prescription_id=pid,
                customer_id=cid,
                doctor_name=doctor,
                date_issued=issued,
                valid_till=vt,
                details=details,
            )
            QMessageBox.information(self, "Updated", f"Prescription updated ✅ (prescription_id={pid})")
            self.load_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_selected(self):
        pid = self._current_prescription_id()
        if not pid:
            QMessageBox.information(self, "Info", "Select a prescription row first.")
            return

        confirm = QMessageBox.question(self, "Confirm delete", f"Delete prescription_id={pid}?")
        if confirm != QMessageBox.Yes:
            return

        try:
            self.dao.delete(pid)
            QMessageBox.information(self, "Deleted", "Prescription deleted.")
            self.load_table()
            self._clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))