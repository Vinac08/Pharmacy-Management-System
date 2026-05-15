# app/ui/sellers_page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QScrollArea, QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt

from app.db.connection import get_conn
from app.dao.people_crud_dao import PeopleCrudDao


class SellersPage(QWidget):
    """
    Sellers CRUD (trigger-safe).
    DB keeps Person.person_type = 'Seller' (required by constraint/trigger),
    but UI displays role as "STAFF" (UI-only label).

    ✅ Search/filter sellers by:
      - first_name
      - last_name
      - position
    Uses cached rows (no extra DB calls while typing).
    """

    def __init__(self):
        super().__init__()
        self.dao = PeopleCrudDao()

        # ---- cache for filtering ----
        self._cached_rows: list[tuple] = []
        self.search_first: str = ""
        self.search_last: str = ""
        self.search_position: str = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignTop)

        title = QLabel("Sellers")
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        root.addWidget(title)

        subtitle = QLabel("")
        subtitle.setStyleSheet("color: #666;")
        root.addWidget(subtitle)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.clicked.connect(self.load_table)

        self.btn_add = QPushButton("Add seller")
        self.btn_add.setFixedHeight(32)
        self.btn_add.clicked.connect(self.add_seller)

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

        # ✅ Search row (First / Last / Position only)
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        lbl = QLabel("Search Seller:")
        lbl.setStyleSheet("color:#555; font-weight:600;")
        search_row.addWidget(lbl)

        self.s_first_le = QLineEdit()
        self.s_first_le.setPlaceholderText("first name ")
        self.s_first_le.setFixedHeight(32)
        self.s_first_le.textChanged.connect(lambda _: self._on_search_changed())
        search_row.addWidget(self.s_first_le)

        self.s_last_le = QLineEdit()
        self.s_last_le.setPlaceholderText("last name ")
        self.s_last_le.setFixedHeight(32)
        self.s_last_le.textChanged.connect(lambda _: self._on_search_changed())
        search_row.addWidget(self.s_last_le)

        self.s_pos_le = QLineEdit()
        self.s_pos_le.setPlaceholderText("position ")
        self.s_pos_le.setFixedHeight(32)
        self.s_pos_le.textChanged.connect(lambda _: self._on_search_changed())
        search_row.addWidget(self.s_pos_le)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedHeight(32)

        def _clear():
            self.s_first_le.setText("")
            self.s_last_le.setText("")
            self.s_pos_le.setText("")

        btn_clear.clicked.connect(_clear)
        search_row.addWidget(btn_clear)

        search_row.addStretch(1)
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

        def mk_input(ph: str) -> QLineEdit:
            le = QLineEdit()
            le.setPlaceholderText(ph)
            le.setMinimumWidth(180)
            le.setFixedHeight(32)
            return le

        self.first_name_in = mk_input("first name (required)")
        self.last_name_in = mk_input("last name (required)")
        self.phone_in = mk_input("phone number (optional)")
        self.email_in = mk_input("email (optional)")
        self.hire_date_in = mk_input("hire date (YYYY-MM-DD optional)")
        self.position_in = mk_input("position (optional)")
        self.salary_in = mk_input("salary (optional, e.g. 650.00)")

        for w in (
            self.first_name_in, self.last_name_in, self.phone_in, self.email_in,
            self.hire_date_in, self.position_in, self.salary_in
        ):
            form.addWidget(w)

        form.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        form_scroll.setWidget(form_container)
        root.addWidget(form_scroll)

        # Table (UI shows "role" = STAFF; DB remains Seller)
        headers = [
            "seller_id", "person_id", "role",
            "first_name", "last_name",
            "phone_number", "email", "hire_date", "position", "salary"
        ]
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._fill_form_from_selected)

        root.addWidget(self.table, stretch=1)

        self.load_table()

    # ---------------------------
    # Search helpers
    # ---------------------------
    def _on_search_changed(self):
        self.search_first = (self.s_first_le.text() or "").strip().lower()
        self.search_last = (self.s_last_le.text() or "").strip().lower()
        self.search_position = (self.s_pos_le.text() or "").strip().lower()
        self._render_filtered()

    def _render_filtered(self):
        self.table.setRowCount(0)

        rows = self._cached_rows
        if not rows:
            return

        # Each cached row = (seller_id, person_id, first_name, last_name, phone, email, hire_date, position, salary)
        def _match(r: tuple) -> bool:
            seller_id, person_id, first_name, last_name, phone, email, hire_date, position, salary = r

            if self.search_first:
                v = "" if first_name is None else str(first_name).lower()
                if self.search_first not in v:
                    return False

            if self.search_last:
                v = "" if last_name is None else str(last_name).lower()
                if self.search_last not in v:
                    return False

            if self.search_position:
                v = "" if position is None else str(position).lower()
                if self.search_position not in v:
                    return False

            return True

        filtered = [r for r in rows if _match(r)]

        for r in filtered:
            row_i = self.table.rowCount()
            self.table.insertRow(row_i)

            seller_id, person_id, first_name, last_name, phone, email, hire_date, position, salary = r

            values = [
                seller_id,
                person_id,
                "STAFF",          # UI-only label
                first_name,
                last_name,
                phone,
                email,
                hire_date,
                position,
                salary
            ]

            for c_i, val in enumerate(values):
                self.table.setItem(row_i, c_i, QTableWidgetItem("" if val is None else str(val)))

        self.table.resizeColumnsToContents()

    # ---------------------------
    # DB load
    # ---------------------------
    def load_table(self):
        sql = """
        SELECT TOP 200
            s.seller_id,
            s.person_id,
            p.first_name,
            p.last_name,
            p.phone_number,
            p.email,
            s.hire_date,
            s.position,
            s.salary
        FROM dbo.Sellers s
        JOIN dbo.Person p ON p.person_id = s.person_id
        ORDER BY s.seller_id DESC;
        """

        try:
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute(sql)
                rows = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load sellers:\n{e}")
            return

        # cache + render (keeps current search filters)
        self._cached_rows = rows
        self._render_filtered()

    # ---------------------------
    # Selection helpers
    # ---------------------------
    def _selected_ids(self):
        row = self.table.currentRow()
        if row < 0:
            return None, None
        seller_id_item = self.table.item(row, 0)
        person_id_item = self.table.item(row, 1)
        if not seller_id_item or not person_id_item:
            return None, None
        return int(seller_id_item.text()), int(person_id_item.text())

    def _fill_form_from_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return

        # columns shifted because of role column at index 2
        self.first_name_in.setText(self.table.item(row, 3).text() if self.table.item(row, 3) else "")
        self.last_name_in.setText(self.table.item(row, 4).text() if self.table.item(row, 4) else "")
        self.phone_in.setText(self.table.item(row, 5).text() if self.table.item(row, 5) else "")
        self.email_in.setText(self.table.item(row, 6).text() if self.table.item(row, 6) else "")
        self.hire_date_in.setText(self.table.item(row, 7).text() if self.table.item(row, 7) else "")
        self.position_in.setText(self.table.item(row, 8).text() if self.table.item(row, 8) else "")
        self.salary_in.setText(self.table.item(row, 9).text() if self.table.item(row, 9) else "")

    def _clear_form(self):
        for inp in (
            self.first_name_in, self.last_name_in, self.phone_in, self.email_in,
            self.hire_date_in, self.position_in, self.salary_in
        ):
            inp.clear()

    # ---------------------------
    # CRUD actions
    # ---------------------------
    def add_seller(self):
        try:
            first_name = self.first_name_in.text().strip()
            last_name = self.last_name_in.text().strip()
            phone = self.phone_in.text().strip() or None
            email = self.email_in.text().strip() or None

            hire_date = self.hire_date_in.text().strip() or None
            position = self.position_in.text().strip() or None

            salary_txt = self.salary_in.text().strip()
            salary = float(salary_txt) if salary_txt else None

            if not first_name or not last_name:
                QMessageBox.information(self, "Missing", "Fill: first_name and last_name.")
                return

            seller_id, person_id = self.dao.create_seller(
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                hire_date=hire_date,
                position=position,
                salary=salary,
            )

            QMessageBox.information(
                self, "Success",
                f"Staff created ✅\nseller_id={seller_id}\nperson_id={person_id}"
            )
            self.load_table()
            self._clear_form()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def update_selected(self):
        seller_id, _ = self._selected_ids()
        if not seller_id:
            QMessageBox.information(self, "Info", "Select a row first.")
            return

        try:
            first_name = self.first_name_in.text().strip() or None
            last_name = self.last_name_in.text().strip() or None
            phone = self.phone_in.text().strip() or None
            email = self.email_in.text().strip() or None

            hire_date = self.hire_date_in.text().strip() or None
            position = self.position_in.text().strip() or None

            salary_txt = self.salary_in.text().strip()
            salary = float(salary_txt) if salary_txt else None

            self.dao.update_seller(
                seller_id,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                hire_date=hire_date,
                position=position,
                salary=salary,
            )

            QMessageBox.information(self, "Updated", f"Staff updated ✅ (seller_id={seller_id})")
            self.load_table()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_selected(self):
        seller_id, _ = self._selected_ids()
        if not seller_id:
            QMessageBox.information(self, "Info", "Select a row first.")
            return

        confirm = QMessageBox.question(
            self, "Confirm delete",
            f"Delete staff (seller_id={seller_id})?\n\nThis also deletes the linked Person row."
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self.dao.delete_seller(seller_id)
            QMessageBox.information(self, "Deleted", "Staff deleted.")
            self.load_table()
            self._clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))