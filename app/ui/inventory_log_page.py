# app/ui/inventory_log_page.py
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QComboBox, QSizePolicy, QFrame
)
from PySide6.QtCore import Qt

from app.db.connection import get_conn


class InventoryLogPage(QWidget):
    """
    Inventory Log

    - Table is read-only
    - Normally filled automatically by DB triggers
    - OPTIONAL: manual insert form (for testing / admin use)
    - Filters (client-side):
        • Medicine name
        • Change type
    """

    def __init__(self):
        super().__init__()

        # cached rows for filtering
        self._cached_cols: list[str] = []
        self._cached_rows: list[tuple] = []

        # filters
        self.f_med: str = ""
        self.f_type: str = ""

        # medicine cache for insert form
        self._med_map: dict[str, int] = {}  # "Name (ID: X)" -> medicine_id

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignTop)

        title = QLabel("Inventory Log")
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        root.addWidget(title)

        subtitle = QLabel("")
        subtitle.setStyleSheet("color: #666;")
        root.addWidget(subtitle)

        # --------------------
        # Buttons row
        # --------------------
        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.clicked.connect(self.load_table)
        btn_row.addWidget(self.btn_refresh)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        # --------------------
        # Manual Insert (NEW)
        # --------------------
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                border: 1px solid #e6e6e6;
                border-radius: 10px;
                background: #fafafa;
            }
        """)
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(12, 12, 12, 12)
        card_l.setSpacing(8)

        card_title = QLabel("Manual Insert (Admin Only)")
        card_title.setStyleSheet("font-weight: 800; color:#333;")
        card_l.addWidget(card_title)

        form_row = QHBoxLayout()
        form_row.setSpacing(10)

        # Medicine dropdown
        self.ins_med_cb = QComboBox()
        self.ins_med_cb.setFixedHeight(32)
        self.ins_med_cb.setMinimumWidth(240)
        form_row.addWidget(self.ins_med_cb)

        # Change type dropdown (editable)
        self.ins_type_cb = QComboBox()
        self.ins_type_cb.setFixedHeight(32)
        self.ins_type_cb.setEditable(True)
        self.ins_type_cb.addItems(["SALE", "UPDATE_STOCK", "MANUAL", "ADJUSTMENT"])
        self.ins_type_cb.setMinimumWidth(160)
        form_row.addWidget(self.ins_type_cb)

        # Quantity changed
        self.ins_qty_le = QLineEdit()
        self.ins_qty_le.setFixedHeight(32)
        self.ins_qty_le.setPlaceholderText("quantity (e.g., -2 or 10)")
        self.ins_qty_le.setMinimumWidth(170)
        form_row.addWidget(self.ins_qty_le)

        # Reason
        self.ins_reason_le = QLineEdit()
        self.ins_reason_le.setFixedHeight(32)
        self.ins_reason_le.setPlaceholderText("reason (optional)")
        self.ins_reason_le.setMinimumWidth(260)
        form_row.addWidget(self.ins_reason_le)

        # Insert button
        self.btn_insert = QPushButton("Insert Log")
        self.btn_insert.setFixedHeight(32)
        self.btn_insert.clicked.connect(self.insert_log)
        form_row.addWidget(self.btn_insert)

        form_row.addStretch(1)
        card_l.addLayout(form_row)

        note = QLabel("")
        note.setStyleSheet("color:#666; font-size:12px;")
        card_l.addWidget(note)

        root.addWidget(card)

        # --------------------
        # Filters
        # --------------------
        filters = QHBoxLayout()
        filters.setSpacing(10)

        lbl = QLabel("Filter:")
        lbl.setStyleSheet("color:#555; font-weight:600;")
        filters.addWidget(lbl)

        self.med_le = QLineEdit()
        self.med_le.setPlaceholderText("medicine name contains…")
        self.med_le.setFixedHeight(32)
        self.med_le.textChanged.connect(self._on_filter_changed)
        filters.addWidget(self.med_le)

        self.type_cb = QComboBox()
        self.type_cb.setFixedHeight(32)
        self.type_cb.addItems(["All", "SALE", "UPDATE_STOCK"])
        self.type_cb.currentTextChanged.connect(self._on_filter_changed)
        filters.addWidget(self.type_cb)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedHeight(32)

        def _clear():
            self.med_le.setText("")
            self.type_cb.setCurrentIndex(0)

        btn_clear.clicked.connect(_clear)
        filters.addWidget(btn_clear)

        filters.addStretch(1)
        root.addLayout(filters)

        # --------------------
        # Table
        # --------------------
        self.table = QTableWidget(0, 0)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        root.addWidget(self.table, stretch=1)

        # initial loads
        self._load_medicines_for_insert()
        self.load_table()

    # --------------------
    # Manual Insert Helpers
    # --------------------
    def _load_medicines_for_insert(self):
        sql = """
        SELECT TOP 500 medicine_id, name
        FROM dbo.Medicines
        ORDER BY name ASC;
        """
        try:
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute(sql)
                rows = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(self, "Load Medicines Error", str(e))
            return

        self._med_map.clear()
        self.ins_med_cb.clear()

        for med_id, name in rows:
            label = f"{name} (ID: {med_id})"
            self._med_map[label] = int(med_id)
            self.ins_med_cb.addItem(label)

        if self.ins_med_cb.count() == 0:
            self.ins_med_cb.addItem("No medicines found")

    def insert_log(self):
        if self.ins_med_cb.count() == 0 or self.ins_med_cb.currentText() not in self._med_map:
            QMessageBox.warning(self, "Insert", "No valid medicine selected.")
            return

        med_label = self.ins_med_cb.currentText()
        medicine_id = self._med_map[med_label]

        change_type = self.ins_type_cb.currentText().strip()
        if not change_type:
            QMessageBox.warning(self, "Insert", "Change type is required.")
            return

        qty_txt = self.ins_qty_le.text().strip()
        if not qty_txt:
            QMessageBox.warning(self, "Insert", "Quantity is required.")
            return

        try:
            qty = int(qty_txt)
        except ValueError:
            QMessageBox.warning(self, "Insert", "Quantity must be an integer (e.g., -2 or 10).")
            return

        reason = self.ins_reason_le.text().strip() or None

        sql = """
        INSERT INTO dbo.Inventory_Log (medicine_id, change_type, quantity_changed, log_date, reason)
        VALUES (?, ?, ?, GETDATE(), ?);
        """

        try:
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute(sql, (medicine_id, change_type, qty, reason))
                conn.commit()
        except Exception as e:
            QMessageBox.critical(self, "Insert Error", str(e))
            return

        # clear qty/reason for convenience
        self.ins_qty_le.setText("")
        self.ins_reason_le.setText("")
        self.load_table()

    # --------------------
    # Load data
    # --------------------
    def load_table(self):
        sql = """
        SELECT TOP 500
            il.log_id,
            il.medicine_id,
            m.name AS medicine_name,
            il.change_type,
            il.quantity_changed,
            il.log_date,
            il.reason
        FROM dbo.Inventory_Log il
        JOIN dbo.Medicines m ON m.medicine_id = il.medicine_id
        ORDER BY il.log_id DESC;
        """

        try:
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute(sql)
                self._cached_rows = cur.fetchall()
                self._cached_cols = [c[0] for c in cur.description]
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))
            return

        self._refresh_type_dropdown()
        self._render_filtered()

    def _refresh_type_dropdown(self):
        idx = self._cached_cols.index("change_type")
        types = sorted({str(r[idx]) for r in self._cached_rows if r[idx]})
        self.type_cb.blockSignals(True)
        current = self.type_cb.currentText()
        self.type_cb.clear()
        self.type_cb.addItems(["All"] + types)
        # try keep selection
        if current in (["All"] + types):
            self.type_cb.setCurrentText(current)
        self.type_cb.blockSignals(False)

    # --------------------
    # Filtering
    # --------------------
    def _on_filter_changed(self, *_):
        self.f_med = self.med_le.text().strip().lower()
        sel = self.type_cb.currentText()
        self.f_type = "" if sel == "All" else sel.lower()
        self._render_filtered()

    def _render_filtered(self):
        cols = self._cached_cols
        rows = self._cached_rows
        if not cols:
            return

        idx_med = cols.index("medicine_name")
        idx_type = cols.index("change_type")

        def match(r):
            if self.f_med and self.f_med not in str(r[idx_med]).lower():
                return False
            if self.f_type and str(r[idx_type]).lower() != self.f_type:
                return False
            return True

        filtered = [r for r in rows if match(r)]

        self.table.setRowCount(0)
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setStretchLastSection(True)

        for r in filtered:
            row_i = self.table.rowCount()
            self.table.insertRow(row_i)
            for c_i, val in enumerate(r):
                item = QTableWidgetItem("" if val is None else str(val))
                if cols[c_i] in ("log_id", "medicine_id", "quantity_changed"):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_i, c_i, item)

        self.table.resizeColumnsToContents()