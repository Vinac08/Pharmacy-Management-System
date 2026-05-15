from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout
from app.dao.table_dao import TableDao


class GenericTablePage(QWidget):
    def __init__(self, table_name: str):
        super().__init__()
        self.table_name = table_name
        self.dao = TableDao()

        layout = QVBoxLayout()

        title = QLabel(f"{table_name}")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_data)
        btn_row.addWidget(self.btn_refresh)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget(0, 0)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        cols, rows = self.dao.fetch_all(self.table_name, limit=200, schema="dbo")

        self.table.setRowCount(0)
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)

        for r in rows:
            row_i = self.table.rowCount()
            self.table.insertRow(row_i)
            for c_i, val in enumerate(r):
                self.table.setItem(row_i, c_i, QTableWidgetItem("" if val is None else str(val)))
