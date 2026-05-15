# app/ui/customer_address_page.py
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QComboBox, QScrollArea, QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt

from app.dao.customer_address_dao import CustomerAddressDao


class CustomerAddressPage(QWidget):
    def __init__(self):
        super().__init__()
        self.dao = CustomerAddressDao()

        self._cached_rows: list[tuple] = []
        self.search_text: str = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignTop)

        title = QLabel("Customer Address")
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        root.addWidget(title)

        subtitle = QLabel("")
        subtitle.setStyleSheet("color:#9ACEEB;")
        root.addWidget(subtitle)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.clicked.connect(self.load_table)

        self.btn_save = QPushButton("Save (Insert/Update)")
        self.btn_save.setFixedHeight(32)
        self.btn_save.clicked.connect(self.save_address)

        self.btn_delete = QPushButton("Delete selected")
        self.btn_delete.setFixedHeight(32)
        self.btn_delete.clicked.connect(self.delete_selected)

        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_save)
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
        self.search_le.setPlaceholderText("Search by customer_id, city, country, street…")
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
        form_scroll.setFixedHeight(64)

        form_container = QWidget()
        form = QHBoxLayout(form_container)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        # customer_id dropdown
        self.customer_cb = QComboBox()
        self.customer_cb.setMinimumWidth(240)
        self.customer_cb.setFixedHeight(32)
        self.customer_cb.currentIndexChanged.connect(self._on_customer_changed)
        form.addWidget(self.customer_cb)

        def mk_input(ph: str) -> QLineEdit:
            le = QLineEdit()
            le.setPlaceholderText(ph)
            le.setMinimumWidth(180)
            le.setFixedHeight(32)
            le.returnPressed.connect(self.save_address)
            return le

        self.street_in = mk_input("street (optional)")
        self.city_in = mk_input("city (optional)")
        self.postal_in = mk_input("postal_code (optional)")
        self.country_in = mk_input("country (optional)")

        for w in (self.street_in, self.city_in, self.postal_in, self.country_in):
            form.addWidget(w)

        form.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        form_scroll.setWidget(form_container)
        root.addWidget(form_scroll)

        # Table
        self.headers = ["customer_id", "street", "city", "postal_code", "country"]
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
    # Dropdown
    # --------------------
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

    def _on_customer_changed(self):
        cid = self._current_customer_id()
        if not cid:
            self._clear_form(keep_customer=True)
            return

        row = self.dao.fetch_one(cid)
        if not row:
            self._clear_form(keep_customer=True)
            return

        _, street, city, postal_code, country = row
        self.street_in.setText("" if street is None else str(street))
        self.city_in.setText("" if city is None else str(city))
        self.postal_in.setText("" if postal_code is None else str(postal_code))
        self.country_in.setText("" if country is None else str(country))

    # --------------------
    # Search/render
    # --------------------
    def _on_search_changed(self, text: str):
        self.search_text = (text or "").strip().lower()
        self._render_rows()

    def _render_rows(self):
        rows = self._cached_rows
        if self.search_text:
            q = self.search_text
            filtered = []
            for r in rows:
                # r = (customer_id, street, city, postal_code, country)
                if q in str(r[0]).lower() \
                   or q in str(r[1] or "").lower() \
                   or q in str(r[2] or "").lower() \
                   or q in str(r[3] or "").lower() \
                   or q in str(r[4] or "").lower():
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
        # keep dropdown fresh too (in case new customers were added)
        self._load_customers_dropdown()

    # --------------------
    # Selection helpers
    # --------------------
    def _selected_customer_id(self) -> int | None:
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

    def _fill_form_from_selected(self):
        cid = self._selected_customer_id()
        if not cid:
            return

        # set dropdown to this customer
        idx = self.customer_cb.findData(cid)
        if idx >= 0:
            self.customer_cb.setCurrentIndex(idx)

        row = self.dao.fetch_one(cid)
        if not row:
            self._clear_form(keep_customer=True)
            return

        _, street, city, postal_code, country = row
        self.street_in.setText("" if street is None else str(street))
        self.city_in.setText("" if city is None else str(city))
        self.postal_in.setText("" if postal_code is None else str(postal_code))
        self.country_in.setText("" if country is None else str(country))

    def _clear_form(self, keep_customer: bool = False):
        self.street_in.clear()
        self.city_in.clear()
        self.postal_in.clear()
        self.country_in.clear()
        if not keep_customer:
            self.customer_cb.setCurrentIndex(0)

    # --------------------
    # Actions
    # --------------------
    def save_address(self):
        cid = self._current_customer_id()
        if not cid:
            QMessageBox.information(self, "Missing", "Select a customer_id first.")
            return

        street = self.street_in.text()
        city = self.city_in.text()
        postal = self.postal_in.text()
        country = self.country_in.text()

        try:
            action = self.dao.upsert(
                customer_id=cid,
                street=street,
                city=city,
                postal_code=postal,
                country=country,
            )
            QMessageBox.information(self, "Saved", f"Address {action} ✅ (customer_id={cid})")
            self.load_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_selected(self):
        cid = self._selected_customer_id()
        if not cid:
            QMessageBox.information(self, "Info", "Select a row first.")
            return

        confirm = QMessageBox.question(
            self, "Confirm delete",
            f"Delete address for customer_id={cid}?"
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self.dao.delete(cid)
            QMessageBox.information(self, "Deleted", "Address deleted.")
            self.load_table()
            self._clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))