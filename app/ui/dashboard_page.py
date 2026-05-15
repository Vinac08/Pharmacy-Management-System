# app/ui/dashboard_page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGridLayout, QFrame,
    QHBoxLayout, QScrollArea, QSizePolicy, QPushButton
)
from PySide6.QtCore import Qt
from app.dao.stats_dao import StatsDao


class StatCard(QFrame):
    def __init__(self, title: str, value: str, color_hex: str, on_click=None):
        super().__init__()
        self.setObjectName("StatCard")
        self.on_click = on_click

        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background: {color_hex};
                border-radius: 14px;
            }}
            QLabel {{ color: white; }}
        """)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet("font-size: 28px; font-weight: 800;")
        self.lbl_value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 600;")
        self.lbl_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_title)

    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click()

    def set_value(self, v: str):
        self.lbl_value.setText(v)


class DashboardPage(QWidget):
    def __init__(self, navigate_to):
        """
        navigate_to(index:int) → handled by app_window.py mapping
        """
        super().__init__()
        self.navigate_to = navigate_to
        self.stats = StatsDao()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(16)
        content_layout.setAlignment(Qt.AlignTop)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: 800;")
        header_row.addWidget(title)
        header_row.addStretch()

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_counts)
        header_row.addWidget(btn_refresh)

        content_layout.addLayout(header_row)

        subtitle = QLabel("Quick overview — click a card to open that section.")
        subtitle.setStyleSheet("color: #666;")
        content_layout.addWidget(subtitle)

        # Grid
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(18)
        self.grid.setVerticalSpacing(18)
        self.grid.setAlignment(Qt.AlignTop)
        content_layout.addLayout(self.grid)

        content_layout.addStretch(1)

        self.cards = []  # (card, table_name)

        def add_card(row, col, label, table, color, target_index):
            card = StatCard(
                title=label,
                value="…",
                color_hex=color,
                on_click=lambda: self.navigate_to(target_index)
            )
            self.grid.addWidget(card, row, col)
            self.cards.append((card, table))

        # ✅ Only tables that exist in your DB (based on screenshot)
        # Index map must match app_window.py
        #
        # 1  Medicines
        # 2  Customers
        # 3  Customer_Address
        # 4  Sellers
        # 5  Person
        # 6  Prescriptions
        # 7  Inventory_Log
        # 8  Transactions
        # 9  Sales

        add_card(0, 0, "Medicines", "Medicines", "#E91E63", 1)
        add_card(0, 1, "Customers", "Customers", "#FF9800", 2)
        add_card(0, 2, "Sellers", "Sellers", "#9C27B0", 4)
        add_card(0, 3, "Person", "Person", "#4CAF50", 5)

        add_card(1, 0, "Customer Address", "Customer_Address", "#673AB7", 3)
        add_card(1, 1, "Prescriptions", "Prescriptions", "#009688", 6)
        add_card(1, 2, "Inventory Log", "Inventory_Log", "#FF5722", 7)
        add_card(1, 3, "Transactions", "Transactions", "#2196F3", 8)

        add_card(2, 0, "Sales", "Sales", "#3F51B5", 9)

        for col in range(4):
            self.grid.setColumnStretch(col, 1)

        self.refresh_counts()

    def refresh_counts(self):
        for card, table in self.cards:
            try:
                count = self.stats.table_count(table)
                card.set_value(str(count))
            except Exception as e:
                card.set_value("—")
                print(f"[Dashboard] Failed counting {table}: {e}")