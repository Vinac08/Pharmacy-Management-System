# app/ui/sales_page.py
from __future__ import annotations

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox, QLineEdit, QFrame,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QGridLayout, QHeaderView
)

from app.dao.sales_dao import SalesDao


class SalesPage(QWidget):
    """
    Sales CRUD (simplified):
      - Search only by Customer ID or Transaction ID
      - Add Sale = select Customer + select existing Transaction
      - Update Selected = change customer only
      - Delete Selected
      - Customer dropdown auto-refreshes when opened (shows new customers immediately)
      - Dropdowns default to "Select ..." (no preselected value)
    """

    def __init__(self):
        super().__init__()
        self.sales_dao = SalesDao()
        self._loading_row = False

        self._build_ui()

        # ✅ auto-refresh customers when dropdown opened
        self.cb_customer.installEventFilter(self)
        self.cb_update_customer.installEventFilter(self)

        self._load_dropdowns()
        self._refresh()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        # Header
        top = QHBoxLayout()
        title = QLabel("Sales ")
        title.setStyleSheet("font-size:18px; font-weight:600;")
        top.addWidget(title)
        top.addStretch(1)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setFixedWidth(110)
        self.btn_refresh.clicked.connect(self._refresh)
        top.addWidget(self.btn_refresh)
        root.addLayout(top)

        # Card
        card = QFrame()
        card.setStyleSheet("QFrame{background:#fff;border:1px solid #ddd;border-radius:6px;}")
        root.addWidget(card)

        grid = QGridLayout(card)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        # columns stretch for nicer layout
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)
        grid.setColumnStretch(4, 0)
        grid.setColumnStretch(5, 1)

        # -------- Search row --------
        grid.addWidget(QLabel("Customer ID:"), 0, 0)
        self.le_customer_id = QLineEdit()
        self.le_customer_id.setPlaceholderText("e.g. 1")
        grid.addWidget(self.le_customer_id, 0, 1)

        grid.addWidget(QLabel("Transaction ID:"), 0, 2)
        self.le_tx_id = QLineEdit()
        self.le_tx_id.setPlaceholderText("e.g. 10")
        grid.addWidget(self.le_tx_id, 0, 3)

        btns0 = QHBoxLayout()
        btns0.setSpacing(10)
        self.btn_search = QPushButton("Search")
        self.btn_search.setFixedWidth(110)
        self.btn_search.clicked.connect(self._search)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setFixedWidth(110)
        self.btn_clear.clicked.connect(self._clear_search)

        btns0.addWidget(self.btn_search)
        btns0.addWidget(self.btn_clear)
        grid.addLayout(btns0, 0, 4, 1, 2, Qt.AlignRight)

        # -------- Add Sale row --------
        grid.addWidget(QLabel("Customer:"), 1, 0)
        self.cb_customer = QComboBox()
        grid.addWidget(self.cb_customer, 1, 1, 1, 2)

        grid.addWidget(QLabel("Transaction:"), 1, 3)
        self.cb_transaction = QComboBox()
        grid.addWidget(self.cb_transaction, 1, 4, 1, 2)

        # -------- Update customer row --------
        grid.addWidget(QLabel("Update selected sale customer:"), 2, 0)
        self.cb_update_customer = QComboBox()
        grid.addWidget(self.cb_update_customer, 2, 1, 1, 2)

        # -------- Buttons --------
        br = QHBoxLayout()
        br.addStretch(1)

        self.btn_add = QPushButton("Add Sale")
        self.btn_add.setFixedWidth(120)
        self.btn_add.clicked.connect(self._add_sale)
        br.addWidget(self.btn_add)

        self.btn_update = QPushButton("Update Selected")
        self.btn_update.setFixedWidth(150)
        self.btn_update.clicked.connect(self._update_selected)
        br.addWidget(self.btn_update)

        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.setFixedWidth(150)
        self.btn_delete.clicked.connect(self._delete_selected)
        br.addWidget(self.btn_delete)

        grid.addLayout(br, 3, 0, 1, 6)

        # -------- Table --------
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Sale ID", "Customer ID", "Transaction ID", "Sale Date", "Total Amount"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_row_selected)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(True)
        hh.setSectionResizeMode(QHeaderView.Stretch)

        root.addWidget(self.table, 1)

    # ✅ refresh customer dropdowns when user clicks them
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if obj in (self.cb_customer, self.cb_update_customer):
                self._reload_customers_keep_selection()
        return super().eventFilter(obj, event)

    # ---------------- helpers ----------------
    def _parse_optional_int(self, text: str, field_name: str) -> int | None:
        t = (text or "").strip()
        if not t:
            return None
        if not t.isdigit():
            raise ValueError(f"{field_name} must be a positive integer.")
        v = int(t)
        if v <= 0:
            raise ValueError(f"{field_name} must be > 0.")
        return v

    def _selected_row_index(self) -> int | None:
        row = self.table.currentRow()
        return row if row >= 0 else None

    def _cell_text(self, row: int, col: int) -> str:
        it = self.table.item(row, col)
        return it.text() if it else ""

    def _selected_sale_id(self) -> int | None:
        row = self._selected_row_index()
        if row is None:
            return None
        txt = self._cell_text(row, 0).strip()
        return int(txt) if txt else None

    def _set_combo_to_none(self, combo: QComboBox):
        """Select the first item which is our 'Select ...' placeholder."""
        if combo.count() > 0:
            combo.setCurrentIndex(0)

    # ---------------- dropdown loading ----------------
    def _reload_customers_keep_selection(self):
        # keep current selection (if not placeholder)
        current_customer_id = self.cb_customer.currentData()
        current_update_id = self.cb_update_customer.currentData()

        customers = self.sales_dao.list_customers()

        self.cb_customer.blockSignals(True)
        self.cb_update_customer.blockSignals(True)
        try:
            self.cb_customer.clear()
            self.cb_update_customer.clear()

            # ✅ placeholders
            self.cb_customer.addItem("— Select customer —", None)
            self.cb_update_customer.addItem("— Select customer —", None)

            for c in customers:
                self.cb_customer.addItem(c.label, c.customer_id)
                self.cb_update_customer.addItem(c.label, c.customer_id)

            # restore selections if possible (and if not None)
            if current_customer_id is not None:
                for i in range(1, self.cb_customer.count()):
                    if int(self.cb_customer.itemData(i)) == int(current_customer_id):
                        self.cb_customer.setCurrentIndex(i)
                        break
            else:
                self.cb_customer.setCurrentIndex(0)

            if current_update_id is not None:
                for i in range(1, self.cb_update_customer.count()):
                    if int(self.cb_update_customer.itemData(i)) == int(current_update_id):
                        self.cb_update_customer.setCurrentIndex(i)
                        break
            else:
                self.cb_update_customer.setCurrentIndex(0)

        finally:
            self.cb_customer.blockSignals(False)
            self.cb_update_customer.blockSignals(False)

    def _load_transactions(self):
        txs = self.sales_dao.list_transactions()

        self.cb_transaction.blockSignals(True)
        try:
            self.cb_transaction.clear()
            # ✅ placeholder
            self.cb_transaction.addItem("— Select transaction —", None)
            for t in txs:
                self.cb_transaction.addItem(t.label, t.transaction_id)
            self.cb_transaction.setCurrentIndex(0)
        finally:
            self.cb_transaction.blockSignals(False)

    def _load_dropdowns(self):
        self._reload_customers_keep_selection()
        self._load_transactions()

        # set defaults (no selection)
        self._set_combo_to_none(self.cb_customer)
        self._set_combo_to_none(self.cb_update_customer)
        self._set_combo_to_none(self.cb_transaction)

    # ---------------- data refresh ----------------
    def _refresh(self):
        # reload dropdowns too
        self._load_dropdowns()
        rows = self.sales_dao.find_all()
        self._fill(rows)

    def _fill(self, rows):
        self.table.setRowCount(0)
        for r in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(r.sale_id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(r.customer_id)))
            self.table.setItem(row, 2, QTableWidgetItem(str(r.transaction_id)))
            self.table.setItem(row, 3, QTableWidgetItem(str(r.sale_date)))
            self.table.setItem(row, 4, QTableWidgetItem(f"{r.total_amount:.2f}"))

    # ---------------- actions ----------------
    def _clear_search(self):
        self.le_customer_id.setText("")
        self.le_tx_id.setText("")
        self._refresh()

    def _search(self):
        try:
            cust_id = self._parse_optional_int(self.le_customer_id.text(), "Customer ID")
            tx_id = self._parse_optional_int(self.le_tx_id.text(), "Transaction ID")

            rows = self.sales_dao.search(customer_id=cust_id, transaction_id=tx_id)
            self._fill(rows)
        except Exception as e:
            QMessageBox.warning(self, "Search error", str(e))

    def _add_sale(self):
        try:
            customer_id = self.cb_customer.currentData()
            transaction_id = self.cb_transaction.currentData()

            if customer_id is None:
                raise ValueError("Please select a customer.")
            if transaction_id is None:
                raise ValueError("Please select a transaction.")

            sale_id = self.sales_dao.create_sale(customer_id=int(customer_id), transaction_id=int(transaction_id))
            QMessageBox.information(self, "Done", f"Sale created.\nSale ID: {sale_id}")
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _update_selected(self):
        sale_id = self._selected_sale_id()
        if not sale_id:
            QMessageBox.warning(self, "Missing", "Select a sale row first.")
            return

        try:
            new_customer_id = self.cb_update_customer.currentData()
            if new_customer_id is None:
                raise ValueError("Please select a customer in the update dropdown.")

            self.sales_dao.update_sale_customer(sale_id=int(sale_id), customer_id=int(new_customer_id))

            QMessageBox.information(self, "Done", "Sale updated.")
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _delete_selected(self):
        sale_id = self._selected_sale_id()
        if not sale_id:
            QMessageBox.warning(self, "Missing", "Select a sale row first.")
            return

        res = QMessageBox.question(
            self,
            "Confirm",
            f"Delete sale #{sale_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return

        try:
            self.sales_dao.delete_sale(int(sale_id))
            QMessageBox.information(self, "Done", "Sale deleted.")
            self._refresh()
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
            customer_id_txt = self._cell_text(row, 1).strip()
            if not customer_id_txt:
                return
            customer_id = int(customer_id_txt)

            # preselect update dropdown to row's customer
            for i in range(1, self.cb_update_customer.count()):
                if self.cb_update_customer.itemData(i) is not None and int(self.cb_update_customer.itemData(i)) == customer_id:
                    self.cb_update_customer.setCurrentIndex(i)
                    break
        finally:
            self._loading_row = False