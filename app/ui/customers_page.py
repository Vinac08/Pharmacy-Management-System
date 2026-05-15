# app/ui/customers_page.py
from __future__ import annotations

import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QScrollArea, QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt

from app.db.connection import get_conn
from app.dao.people_crud_dao import PeopleCrudDao

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CustomersPage(QWidget):
    def __init__(self):
        super().__init__()
        self.dao = PeopleCrudDao()

        self._cached_rows: list[tuple] = []
        self.search_text: str = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignTop)

        title = QLabel("Customers")
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        root.addWidget(title)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.clicked.connect(self.load_table)

        self.btn_add = QPushButton("Add customer")
        self.btn_add.setFixedHeight(32)
        self.btn_add.clicked.connect(self.add_customer)

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
        self.search_le.setPlaceholderText("Search by first or last name…")
        self.search_le.setFixedHeight(32)
        self.search_le.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_le, stretch=1)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedHeight(32)
        btn_clear.clicked.connect(lambda: self.search_le.setText(""))
        search_row.addWidget(btn_clear)

        root.addLayout(search_row)

        # Form
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setFrameShape(QFrame.NoFrame)
        form_scroll.setFixedHeight(64)

        form_container = QWidget()
        form = QHBoxLayout(form_container)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        def mk_input(ph: str) -> QLineEdit:
            le = QLineEdit()
            le.setPlaceholderText(ph)
            le.setMinimumWidth(180)
            le.setFixedHeight(32)
            le.returnPressed.connect(self.add_customer)
            return le

        self.first_name_in = mk_input("first name (required)")
        self.last_name_in = mk_input("last name (required)")
        self.phone_in = mk_input("phone number (optional)")
        self.email_in = mk_input("email (optional)")
        self.address_in = mk_input("address (optional)")

        for w in (self.first_name_in, self.last_name_in, self.phone_in, self.email_in, self.address_in):
            form.addWidget(w)

        form.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        form_scroll.setWidget(form_container)
        root.addWidget(form_scroll)

        # Table (NO customer_name column)
        self.headers = ["customer_id", "person_id", "first_name", "last_name", "phone_number", "email", "address"]
        self.table = QTableWidget(0, len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)

        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._fill_form_from_selected)

        root.addWidget(self.table, stretch=1)

        self.load_table()

    def _on_search_changed(self, text: str):
        self.search_text = (text or "").strip().lower()
        self._render_rows()

    def _render_rows(self):
        rows = self._cached_rows
        if self.search_text:
            q = self.search_text
            rows = [r for r in rows if q in (str(r[2] or "")).lower() or q in (str(r[3] or "")).lower()]

        self.table.setRowCount(0)
        for r in rows:
            row_i = self.table.rowCount()
            self.table.insertRow(row_i)
            for c_i, val in enumerate(r):
                self.table.setItem(row_i, c_i, QTableWidgetItem("" if val is None else str(val)))
        self.table.resizeColumnsToContents()

    def load_table(self):
        sql = """
        SELECT TOP 200
            c.customer_id,
            c.person_id,
            p.first_name,
            p.last_name,
            c.phone_number,
            c.email,
            c.address
        FROM dbo.Customers c
        JOIN dbo.Person p ON p.person_id = c.person_id
        ORDER BY c.customer_id DESC;
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            self._cached_rows = cur.fetchall()
        self._render_rows()

    def _selected_ids(self):
        row = self.table.currentRow()
        if row < 0:
            return None, None
        try:
            return int(self.table.item(row, 0).text()), int(self.table.item(row, 1).text())
        except Exception:
            return None, None

    def _fill_form_from_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        self.first_name_in.setText(self.table.item(row, 2).text() if self.table.item(row, 2) else "")
        self.last_name_in.setText(self.table.item(row, 3).text() if self.table.item(row, 3) else "")
        self.phone_in.setText(self.table.item(row, 4).text() if self.table.item(row, 4) else "")
        self.email_in.setText(self.table.item(row, 5).text() if self.table.item(row, 5) else "")
        self.address_in.setText(self.table.item(row, 6).text() if self.table.item(row, 6) else "")

    def _clear_form(self):
        for inp in (self.first_name_in, self.last_name_in, self.phone_in, self.email_in, self.address_in):
            inp.clear()

    def _validate_inputs(self, first_name: str, last_name: str, email: str | None):
        if not first_name or not last_name:
            return False, "Fill: first_name and last_name."
        if email and not _EMAIL_RE.match(email):
            return False, "Invalid email format (example: name@example.com)."
        return True, ""

    def add_customer(self):
        try:
            first_name = self.first_name_in.text().strip()
            last_name = self.last_name_in.text().strip()
            phone = self.phone_in.text().strip() or None
            email = self.email_in.text().strip() or None
            address = self.address_in.text().strip() or None

            ok, msg = self._validate_inputs(first_name, last_name, email)
            if not ok:
                QMessageBox.information(self, "Invalid input", msg)
                return

            # ✅ IMPORTANT: Customers.name is NOT NULL in DB, so we auto-generate it
            customer_name = f"{first_name} {last_name}".strip()

            customer_id, person_id = self.dao.create_customer(
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                customer_name=customer_name,  # ✅ auto-filled
                address=address,
            )

            QMessageBox.information(
                self, "Success",
                f"Customer created ✅\ncustomer_id={customer_id}\nperson_id={person_id}"
            )
            self.load_table()
            self._clear_form()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def update_selected(self):
        customer_id, _ = self._selected_ids()
        if not customer_id:
            QMessageBox.information(self, "Info", "Select a customer row first.")
            return

        try:
            first_name = self.first_name_in.text().strip() or None
            last_name = self.last_name_in.text().strip() or None
            phone = self.phone_in.text().strip() or None
            email = self.email_in.text().strip() or None
            address = self.address_in.text().strip() or None

            if all(v is None for v in (first_name, last_name, phone, email, address)):
                QMessageBox.information(self, "Info", "Nothing to update.")
                return

            if email and not _EMAIL_RE.match(email):
                QMessageBox.information(self, "Invalid", "Invalid email format.")
                return

            # If both names provided, keep Customers.name consistent
            customer_name = None
            if first_name and last_name:
                customer_name = f"{first_name} {last_name}".strip()

            self.dao.update_customer(
                customer_id,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                customer_name=customer_name,  # ✅ optional update
                address=address,
            )

            QMessageBox.information(self, "Updated", f"Customer updated ✅ (customer_id={customer_id})")
            self.load_table()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_selected(self):
        customer_id, _ = self._selected_ids()
        if not customer_id:
            QMessageBox.information(self, "Info", "Select a customer row first.")
            return

        confirm = QMessageBox.question(
            self, "Confirm delete",
            f"Delete customer_id={customer_id}?\n\nThis also deletes the linked Person row."
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self.dao.delete_customer(customer_id)
            QMessageBox.information(self, "Deleted", "Customer deleted.")
            self.load_table()
            self._clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))