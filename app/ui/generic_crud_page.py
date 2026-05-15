# app/ui/generic_crud_page.py
from __future__ import annotations

from decimal import Decimal
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QPushButton, QLineEdit, QMessageBox, QScrollArea, QFrame,
    QSizePolicy, QSpacerItem, QComboBox
)
from PySide6.QtCore import Qt

from app.dao.meta_dao import MetaDao
from app.dao.generic_crud_dao import GenericCrudDao


class GenericCrudPage(QWidget):
    """
    Generic CRUD page for any table.

    Special behavior:
    - Medicines: search by name
    - Person: search by first_name, last_name, person_type dropdown
    - ✅ Person table is READ-ONLY: no text inputs, no Add, no Delete
    - ✅ Medicines placeholders: remove "(varchar)/(char)" type hints
    """

    def __init__(self, table_name: str, schema: str = "dbo"):
        super().__init__()
        self.table_name = table_name
        self.schema = schema

        self.meta = MetaDao()
        self.columns = self.meta.get_columns(table_name, schema)  # list[dict]
        self.pk = self.meta.get_primary_key(table_name, schema)

        self.dao = GenericCrudDao(table_name, schema)

        # Cache for search/filter rendering
        self._cached_cols: list[str] = []
        self._cached_rows: list[tuple] = []

        # Medicines search
        self.search_text: str = ""

        # Person search
        self.p_first: str = ""
        self.p_last: str = ""
        self.p_type: str = ""  # "" means All (no filter)

        # ---- Root layout ----
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignTop)

        # ---- Title ----
        title = QLabel(f"{table_name}")
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        root.addWidget(title)

        info = QLabel(f"Primary key: {self.pk if self.pk else 'NOT FOUND'}")
        info.setStyleSheet("color: #666;")
        root.addWidget(info)

        # ---- Buttons row ----
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_table)
        self.btn_refresh.setFixedHeight(32)
        btn_row.addWidget(self.btn_refresh)

        # ✅ Only show Add/Delete if NOT Person table
        self.btn_add = None
        self.btn_delete = None

        if not self._is_person_table():
            self.btn_add = QPushButton("Add row")
            self.btn_add.clicked.connect(self.add_row)

            self.btn_delete = QPushButton("Delete selected")
            self.btn_delete.clicked.connect(self.delete_selected)

            for b in (self.btn_add, self.btn_delete):
                b.setFixedHeight(32)

            btn_row.addWidget(self.btn_add)
            btn_row.addWidget(self.btn_delete)

        btn_row.addStretch(1)
        root.addLayout(btn_row)

        # ---- Search row (Medicines only) ----
        if self.table_name.lower() == "medicines":
            search_row = QHBoxLayout()
            search_row.setSpacing(10)

            lbl = QLabel("Search:")
            lbl.setStyleSheet("color:#555; font-weight:600;")
            search_row.addWidget(lbl)

            self.search_le = QLineEdit()
            self.search_le.setPlaceholderText("Type medicine name…")
            self.search_le.setFixedHeight(32)
            self.search_le.textChanged.connect(self._on_medicine_search_changed)
            search_row.addWidget(self.search_le, stretch=1)

            btn_clear = QPushButton("Clear")
            btn_clear.setFixedHeight(32)
            btn_clear.clicked.connect(lambda: self.search_le.setText(""))
            search_row.addWidget(btn_clear)

            root.addLayout(search_row)

        # ---- Search row (Person only) ----
        if self._is_person_table():
            person_search = QHBoxLayout()
            person_search.setSpacing(10)

            lbl = QLabel("Search Person:")
            lbl.setStyleSheet("color:#555; font-weight:600;")
            person_search.addWidget(lbl)

            self.p_first_le = QLineEdit()
            self.p_first_le.setPlaceholderText("first name")
            self.p_first_le.setFixedHeight(32)
            self.p_first_le.textChanged.connect(lambda _: self._on_person_search_changed())
            person_search.addWidget(self.p_first_le)

            self.p_last_le = QLineEdit()
            self.p_last_le.setPlaceholderText("last name")
            self.p_last_le.setFixedHeight(32)
            self.p_last_le.textChanged.connect(lambda _: self._on_person_search_changed())
            person_search.addWidget(self.p_last_le)

            self.p_type_cb = QComboBox()
            self.p_type_cb.setFixedHeight(32)
            self.p_type_cb.addItems(["All", "Customer", "STAFF"])
            self.p_type_cb.currentTextChanged.connect(lambda _: self._on_person_search_changed())
            person_search.addWidget(self.p_type_cb)

            btn_clear = QPushButton("Clear")
            btn_clear.setFixedHeight(32)

            def _clear_person_search():
                self.p_first_le.setText("")
                self.p_last_le.setText("")
                self.p_type_cb.setCurrentIndex(0)

            btn_clear.clicked.connect(_clear_person_search)
            person_search.addWidget(btn_clear)

            person_search.addStretch(1)
            root.addLayout(person_search)

        # ---- Auto-form (ONLY if NOT Person) ----
        self.inputs: dict[str, QLineEdit] = {}

        if not self._is_person_table():
            form_scroll = QScrollArea()
            form_scroll.setWidgetResizable(True)
            form_scroll.setFrameShape(QFrame.NoFrame)
            form_scroll.setFixedHeight(64)

            form_container = QWidget()
            self.form_layout = QHBoxLayout(form_container)
            self.form_layout.setContentsMargins(0, 0, 0, 0)
            self.form_layout.setSpacing(8)

            insertable_cols = []
            for c in self.columns:
                name = c.get("name")
                if not name:
                    continue

                if self.pk and name == self.pk:
                    continue
                if c.get("is_identity") is True:
                    continue
                if c.get("is_computed") is True:
                    continue
                if c.get("computed") is True:
                    continue
                if name.lower() in ("total_amount",):
                    continue

                insertable_cols.append(c)

            for col in insertable_cols:
                le = QLineEdit()
                col_name = col["name"]
                col_type = col.get("type", "")

                # ✅ Medicines: remove the "(varchar)/(char)" examples from placeholder
                is_medicines = (self.table_name or "").strip().lower() == "medicines"

                if col_name.lower() == "expiry_date":
                    le.setPlaceholderText("expiry_date (YYYY-MM-DD)")
                else:
                    if is_medicines:
                        le.setPlaceholderText(f"{col_name}")
                    else:
                        le.setPlaceholderText(f"{col_name} ({col_type})")

                le.setMinimumWidth(180)
                le.setFixedHeight(32)

                # Press Enter to add (fast data entry)
                le.returnPressed.connect(self.add_row)

                self.inputs[col_name] = le
                self.form_layout.addWidget(le)

            self.form_layout.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
            form_scroll.setWidget(form_container)
            root.addWidget(form_scroll)

        # ---- Table ----
        self.table = QTableWidget(0, 0)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        root.addWidget(self.table, stretch=1)

        self.load_table()

    # ---------------------------
    # Helpers
    # ---------------------------
    def _is_person_table(self) -> bool:
        t = (self.table_name or "").strip().lower()
        return t in ("person", "dbo.person")

    def _is_numeric_type(self, col_type: str) -> bool:
        t = (col_type or "").lower()
        return any(x in t for x in ("int", "bigint", "smallint", "tinyint", "decimal", "numeric", "money", "float", "real"))

    def _is_money_type(self, col_type: str) -> bool:
        t = (col_type or "").lower()
        return any(x in t for x in ("decimal", "numeric", "money", "smallmoney", "float", "real"))

    def _fmt_money(self, v) -> str:
        if v is None:
            return ""
        if isinstance(v, Decimal):
            return f"{float(v):.2f}"
        if isinstance(v, (int, float)):
            return f"{float(v):.2f}"
        try:
            return f"{float(v):.2f}"
        except Exception:
            return str(v)

    def _col_type_map(self) -> dict[str, str]:
        return {c["name"]: c.get("type", "") for c in self.columns if "name" in c}

    # ---------------------------
    # Search rendering
    # ---------------------------
    def _on_medicine_search_changed(self, text: str):
        self.search_text = (text or "").strip().lower()
        self._render_rows()

    def _on_person_search_changed(self):
        self.p_first = (self.p_first_le.text() or "").strip().lower()
        self.p_last = (self.p_last_le.text() or "").strip().lower()
        selected = (self.p_type_cb.currentText() or "").strip()
        self.p_type = "" if selected == "All" else selected
        self._render_rows()

    def _render_rows(self):
        cols = self._cached_cols
        rows = self._cached_rows
        if not cols:
            return

        filtered = rows

        # Medicines filter by name
        if self.table_name.lower() == "medicines" and self.search_text:
            if "name" in cols:
                name_idx = cols.index("name")
                filtered = [
                    r for r in filtered
                    if r[name_idx] is not None and self.search_text in str(r[name_idx]).lower()
                ]

        # Person filter by first_name, last_name, person_type
        if self._is_person_table() and (self.p_first or self.p_last or self.p_type):
            idx_first = cols.index("first_name") if "first_name" in cols else None
            idx_last = cols.index("last_name") if "last_name" in cols else None
            idx_type = cols.index("person_type") if "person_type" in cols else None

            wanted_db_type = None
            if self.p_type:
                if self.p_type.upper() == "STAFF":
                    wanted_db_type = "seller"
                else:
                    wanted_db_type = self.p_type.lower()

            def _match(row: tuple) -> bool:
                if idx_first is not None and self.p_first:
                    v = "" if row[idx_first] is None else str(row[idx_first]).lower()
                    if self.p_first not in v:
                        return False

                if idx_last is not None and self.p_last:
                    v = "" if row[idx_last] is None else str(row[idx_last]).lower()
                    if self.p_last not in v:
                        return False

                if idx_type is not None and wanted_db_type:
                    v = "" if row[idx_type] is None else str(row[idx_type]).lower()
                    if v != wanted_db_type:
                        return False

                return True

            filtered = [r for r in filtered if _match(r)]

        # Render
        self.table.setRowCount(0)
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setStretchLastSection(True)

        col_type_map = self._col_type_map()

        for r in filtered:
            row_i = self.table.rowCount()
            self.table.insertRow(row_i)

            for c_i, val in enumerate(r):
                col_name = cols[c_i] if c_i < len(cols) else ""
                col_type = col_type_map.get(col_name, "")

                if self._is_money_type(col_type):
                    text = self._fmt_money(val)
                else:
                    text = "" if val is None else str(val)

                item = QTableWidgetItem(text)

                if self._is_numeric_type(col_type):
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

                self.table.setItem(row_i, c_i, item)

        self.table.resizeColumnsToContents()

    # ---------------------------
    # DB Load
    # ---------------------------
    def load_table(self):
        try:
            cols, rows = self.dao.find_all(limit=200)
            self._cached_cols = cols
            self._cached_rows = rows
            self._render_rows()
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"{self.schema}.{self.table_name}\n\n{e}")
            print(f"[GenericCrudPage] Load failed for {self.schema}.{self.table_name}: {e}")

    # ---------------------------
    # Insert/delete ONLY for non-Person tables
    # ---------------------------
    def _convert_value(self, col_type: str, text: str):
        if text is None:
            return None
        t = text.strip()
        if t == "":
            return None

        col_type_l = (col_type or "").lower()

        if col_type_l in ("int", "bigint", "smallint", "tinyint"):
            return int(t)

        if col_type_l in ("decimal", "numeric", "money", "smallmoney", "float", "real"):
            return float(t)

        if col_type_l in ("date", "datetime", "datetime2", "smalldatetime"):
            return t  # expect YYYY-MM-DD

        return t

    def _validate_medicines(self, values: dict[str, object]) -> tuple[bool, str]:
        required = ["name", "type", "brand", "price"]
        missing = [r for r in required if not str(values.get(r, "")).strip()]
        if missing:
            return False, f"Missing required field(s): {', '.join(missing)}"

        price = values.get("price")
        if price is None:
            return False, "Price is required."
        try:
            if float(price) < 0:
                return False, "Price cannot be negative."
        except Exception:
            return False, "Price must be a valid number."

        q = values.get("quantity_in_stock")
        if q is not None:
            try:
                if int(q) < 0:
                    return False, "quantity_in_stock cannot be negative."
            except Exception:
                return False, "quantity_in_stock must be an integer."

        r = values.get("reorder_level")
        if r is not None:
            try:
                if int(r) < 0:
                    return False, "reorder_level cannot be negative."
            except Exception:
                return False, "reorder_level must be an integer."

        exp = values.get("expiry_date")
        if exp is not None and str(exp).strip() != "":
            s = str(exp).strip()
            try:
                datetime.strptime(s, "%Y-%m-%d")
            except Exception:
                return False, "expiry_date must be in format YYYY-MM-DD."

        return True, ""

    def add_row(self):
        if self._is_person_table():
            QMessageBox.information(self, "Read-only", "Person table is read-only in this UI.")
            return

        try:
            values: dict[str, object] = {}
            col_type_map = self._col_type_map()

            for col_name, inp in self.inputs.items():
                raw = inp.text()
                try:
                    val = self._convert_value(col_type_map.get(col_name, ""), raw)
                except Exception:
                    QMessageBox.warning(self, "Invalid input", f"Field '{col_name}' has invalid value.")
                    return
                if val is not None:
                    values[col_name] = val

            if self.table_name.lower() == "medicines":
                ok, msg = self._validate_medicines(values)
                if not ok:
                    QMessageBox.warning(self, "Validation error", msg)
                    return

            self.dao.insert(values)

            self.load_table()
            for inp in self.inputs.values():
                inp.clear()

            QMessageBox.information(self, "Success", f"Row added to {self.table_name}.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_selected(self):
        if self._is_person_table():
            QMessageBox.information(self, "Read-only", "Person table is read-only in this UI.")
            return

        if not self.pk:
            QMessageBox.critical(self, "Error", f"No primary key found for {self.table_name}. Cannot delete safely.")
            return

        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Select a row first.")
            return

        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        if self.pk not in headers:
            QMessageBox.critical(self, "Error", f"PK column '{self.pk}' not visible in table.")
            return

        pk_index = headers.index(self.pk)
        pk_item = self.table.item(row, pk_index)
        pk_text = pk_item.text().strip() if pk_item else ""

        if pk_text == "":
            QMessageBox.critical(self, "Error", "Selected row has empty PK value.")
            return

        confirm = QMessageBox.question(self, "Confirm", f"Delete row where {self.pk}={pk_text}?")
        if confirm != QMessageBox.Yes:
            return

        try:
            pk_type = self._col_type_map().get(self.pk, "")
            pk_value = self._convert_value(pk_type, pk_text)
        except Exception:
            pk_value = pk_text

        try:
            self.dao.delete_by_pk(pk_value)
            self.load_table()
            QMessageBox.information(self, "Deleted", "Row deleted.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))