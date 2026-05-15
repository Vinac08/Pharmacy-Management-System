# app/ui/transactions_page.py
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QPushButton, QMessageBox, QLineEdit, QFrame,
    QTableWidget, QTableWidgetItem, QAbstractItemView
)

from app.dao.transactions_dao import TransactionsDao


class TransactionsPage(QWidget):
    """
    CRUD page for dbo.Transactions:
      - Add / Update / Delete / Search
      - Selecting a row loads fields for update
      - ✅ Unit Price auto-fills from dbo.Medicines.price
    """

    def __init__(self):
        super().__init__()
        self.dao = TransactionsDao()
        self._loading_row = False

        self._build_ui()
        self._load_dropdowns()
        self._refresh_table()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("Transactions")
        title.setStyleSheet("font-size:18px; font-weight:600;")
        top.addWidget(title)
        top.addStretch(1)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_table)
        top.addWidget(self.btn_refresh)

        root.addLayout(top)

        card = QFrame()
        card.setStyleSheet("QFrame{background:#fff;border:1px solid #ddd;border-radius:6px;}")
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(14, 14, 14, 14)
        card_l.setSpacing(10)

        # Search row
        sr = QHBoxLayout()
        sr.setSpacing(10)
        sr.addWidget(QLabel("Search Transaction ID:"))
        self.le_search_tid = QLineEdit()
        self.le_search_tid.setPlaceholderText("e.g. 5")
        self.le_search_tid.setFixedWidth(140)
        sr.addWidget(self.le_search_tid)

        sr.addWidget(QLabel("Medicine:"))
        self.cb_search_med = QComboBox()
        self.cb_search_med.setMinimumWidth(260)
        sr.addWidget(self.cb_search_med, 1)

        self.btn_search = QPushButton("Search")
        self.btn_search.clicked.connect(self._search)
        sr.addWidget(self.btn_search)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self._clear_search)
        sr.addWidget(self.btn_clear)

        card_l.addLayout(sr)

        # Form row
        fr = QHBoxLayout()
        fr.setSpacing(10)

        fr.addWidget(QLabel("Medicine:"))
        self.cb_med = QComboBox()
        self.cb_med.setMinimumWidth(380)
        fr.addWidget(self.cb_med, 2)

        # ✅ auto price when medicine changes
        self.cb_med.currentIndexChanged.connect(self._sync_price_from_medicine)

        fr.addWidget(QLabel("Qty:"))
        self.sp_qty = QSpinBox()
        self.sp_qty.setRange(1, 1_000_000)
        self.sp_qty.setValue(1)
        self.sp_qty.setFixedWidth(110)
        fr.addWidget(self.sp_qty)

        fr.addWidget(QLabel("Unit Price:"))
        self.le_price = QLineEdit()
        self.le_price.setFixedWidth(140)
        self.le_price.setAlignment(Qt.AlignRight)
        self.le_price.setPlaceholderText("auto")
        self.le_price.setReadOnly(True)  # ✅ user cannot edit
        fr.addWidget(self.le_price)

        card_l.addLayout(fr)

        # Buttons row
        br = QHBoxLayout()
        br.addStretch(1)

        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self._add)
        br.addWidget(self.btn_add)

        self.btn_update = QPushButton("Update Selected")
        self.btn_update.clicked.connect(self._update_selected)
        br.addWidget(self.btn_update)

        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.clicked.connect(self._delete_selected)
        br.addWidget(self.btn_delete)

        card_l.addLayout(br)
        root.addWidget(card)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Transaction ID", "Medicine ID", "Qty", "Unit Price"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        root.addWidget(self.table, 1)

        hint = QLabel("Tip: If delete fails, it usually means the transaction is referenced by another table (FK).")
        hint.setStyleSheet("color:#666;")
        root.addWidget(hint)

    # ---------------- helpers ----------------
    def _parse_price(self) -> Decimal:
        # price is auto-filled, but still validate (safety)
        txt = (self.le_price.text() or "").strip().replace(",", ".")
        if not txt:
            raise ValueError("Unit price is missing. Select a medicine again.")
        try:
            v = Decimal(txt)
        except InvalidOperation:
            raise ValueError("Unit price is invalid.")
        if v <= 0:
            raise ValueError("Unit price must be > 0.")
        return v

    def _selected_row_index(self) -> int | None:
        row = self.table.currentRow()
        return row if row >= 0 else None

    def _cell_text(self, row: int, col: int) -> str:
        it = self.table.item(row, col)
        return it.text() if it else ""

    def _selected_transaction_id(self) -> int | None:
        row = self._selected_row_index()
        if row is None:
            return None
        tid_txt = self._cell_text(row, 0).strip()
        return int(tid_txt) if tid_txt else None

    def _clear_form(self):
        if self.cb_med.count() > 0:
            self.cb_med.setCurrentIndex(0)
        self.sp_qty.setValue(1)
        self._sync_price_from_medicine()

    def _sync_price_from_medicine(self):
        try:
            med_id = self.cb_med.currentData()
            if med_id is None:
                self.le_price.setText("")
                return
            price = self.dao.get_medicine_price(int(med_id))
            self.le_price.setText(f"{price:.2f}")
        except Exception:
            self.le_price.setText("")

    # ---------------- load ----------------
    def _load_dropdowns(self):
        meds = self.dao.list_medicines()

        # main
        self.cb_med.clear()
        for m in meds:
            self.cb_med.addItem(m.label, m.medicine_id)

        # search
        self.cb_search_med.clear()
        self.cb_search_med.addItem("All", None)
        for m in meds:
            self.cb_search_med.addItem(m.label, m.medicine_id)

        # ✅ set initial price
        self._sync_price_from_medicine()

    def _refresh_table(self):
        rows = self.dao.find_all()
        self._fill_table(rows)

    def _fill_table(self, rows):
        self.table.setRowCount(0)
        for r in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(r.transaction_id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(r.medicine_id)))
            self.table.setItem(row, 2, QTableWidgetItem(str(r.quantity_sold)))
            self.table.setItem(row, 3, QTableWidgetItem(f"{r.price_per_unit:.2f}"))

        self.table.resizeColumnsToContents()

    # ---------------- actions ----------------
    def _clear_search(self):
        self.le_search_tid.setText("")
        self.cb_search_med.setCurrentIndex(0)
        self._refresh_table()

    def _search(self):
        try:
            tid_txt = (self.le_search_tid.text() or "").strip()
            if tid_txt:
                if not tid_txt.isdigit():
                    raise ValueError("Transaction ID must be a positive integer.")
                tid = int(tid_txt)
                if tid <= 0:
                    raise ValueError("Transaction ID must be > 0.")
            else:
                tid = None

            med = self.cb_search_med.currentData()
            med_id = int(med) if med is not None else None

            rows = self.dao.search(transaction_id=tid, medicine_id=med_id)
            self._fill_table(rows)

        except Exception as e:
            QMessageBox.warning(self, "Search error", str(e))

    def _add(self):
        try:
            med_id = int(self.cb_med.currentData())
            qty = int(self.sp_qty.value())

            # ✅ use medicine price from DB (auto filled)
            price = self._parse_price()

            tid = self.dao.insert(medicine_id=med_id, quantity_sold=qty, price_per_unit=price)
            QMessageBox.information(self, "Done", f"Transaction created.\nTransaction ID: {tid}")
            self._refresh_table()
            self._clear_form()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _update_selected(self):
        tid = self._selected_transaction_id()
        if not tid:
            QMessageBox.warning(self, "Missing", "Select a row first.")
            return
        try:
            med_id = int(self.cb_med.currentData())
            qty = int(self.sp_qty.value())
            price = self._parse_price()

            self.dao.update(transaction_id=tid, medicine_id=med_id, quantity_sold=qty, price_per_unit=price)
            QMessageBox.information(self, "Done", "Transaction updated.")
            self._refresh_table()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _delete_selected(self):
        tid = self._selected_transaction_id()
        if not tid:
            QMessageBox.warning(self, "Missing", "Select a row first.")
            return

        res = QMessageBox.question(
            self,
            "Confirm",
            f"Delete transaction #{tid}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return

        try:
            self.dao.delete(tid)
            QMessageBox.information(self, "Done", "Transaction deleted.")
            self._refresh_table()
            self._clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_row_selected(self):
        if self._loading_row:
            return
        row = self._selected_row_index()
        if row is None:
            return

        self._loading_row = True
        try:
            med_id_txt = self._cell_text(row, 1).strip()
            qty_txt = self._cell_text(row, 2).strip()
            price_txt = self._cell_text(row, 3).strip()

            if not (med_id_txt and qty_txt):
                return

            med_id = int(med_id_txt)
            qty = int(qty_txt)

            # set medicine dropdown to correct value
            for i in range(self.cb_med.count()):
                if int(self.cb_med.itemData(i)) == med_id:
                    self.cb_med.setCurrentIndex(i)
                    break

            self.sp_qty.setValue(qty)

            # keep DB price visible; if you want to show transaction saved price, use price_txt
            # but correct POS logic: price comes from Medicines
            self._sync_price_from_medicine()

        finally:
            self._loading_row = False