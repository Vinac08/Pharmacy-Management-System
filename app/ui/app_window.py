# app/ui/app_window.py
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QStackedWidget,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt

from app.ui.dashboard_page import DashboardPage
from app.ui.generic_crud_page import GenericCrudPage

from app.ui.customers_page import CustomersPage
from app.ui.sellers_page import SellersPage

from app.ui.transactions_page import TransactionsPage
from app.ui.sales_page import SalesPage

# ✅ Real pages (not generic)
from app.ui.customer_address_page import CustomerAddressPage
from app.ui.prescriptions_page import PrescriptionsPage

# ✅ Inventory Log (read-only)
from app.ui.inventory_log_page import InventoryLogPage


def _make_section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #555; margin-top: 10px;")
    return lbl


def _style_sidebar_button(btn: QPushButton) -> None:
    btn.setFixedHeight(36)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet("""
        QPushButton {
            text-align: left;
            padding: 8px 12px;
            border-radius: 10px;
            background: #F3F4F6;
            border: 1px solid #E5E7EB;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #E9EEF7;
            border: 1px solid #D6E0F5;
        }
        QPushButton:pressed {
            background: #DDE7FB;
        }
    """)


class MainWindow(QMainWindow):
    def __init__(self, user: dict | None = None):
        super().__init__()

        # ✅ allow running even without login/user dict
        self.user = user or {"username": "local", "role": "admin"}

        self.setWindowTitle(f"PharmacyApp - {self.user.get('username')} ({self.user.get('role')})")

        # (Optional) fallback size, but app will open maximized
        self.resize(1180, 720)
        self.setMinimumSize(1050, 650)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        # --------------------
        # Sidebar (scrollable)
        # --------------------
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet("""
            QFrame#Sidebar {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 14px;
            }
        """)

        sidebar_outer = QVBoxLayout(sidebar)
        sidebar_outer.setContentsMargins(14, 14, 14, 14)
        sidebar_outer.setSpacing(10)

        header = QLabel("Menu")
        header.setStyleSheet("font-size: 18px; font-weight: 800;")
        sidebar_outer.addWidget(header)

        role = QLabel(f"Signed in as: {self.user.get('username')} ({self.user.get('role')})")
        role.setStyleSheet("color: #666; font-size: 11px;")
        sidebar_outer.addWidget(role)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; }
            QWidget { background: transparent; }
        """)
        sidebar_outer.addWidget(scroll, stretch=1)

        menu_container = QWidget()
        menu_layout = QVBoxLayout(menu_container)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(8)
        scroll.setWidget(menu_container)

        # --------------------
        # Pages container
        # --------------------
        self.pages = QStackedWidget()

        def goto(widget: QWidget):
            self.pages.setCurrentWidget(widget)

        # --------------------
        # Pages
        # --------------------
        page_dashboard = DashboardPage(navigate_to=lambda idx: None)

        page_medicines = GenericCrudPage("Medicines")
        page_customers = CustomersPage()
        page_sellers = SellersPage()

        page_person = GenericCrudPage("Person")

        # ✅ real pages
        page_customer_address = CustomerAddressPage()
        page_prescriptions = PrescriptionsPage()

        # ✅ Inventory Log page (READ-ONLY, from triggers)
        page_inventory_log = InventoryLogPage()

        # ✅ Transactions input page
        page_transactions = TransactionsPage()

        # ✅ Sales summary page
        page_sales = SalesPage()

        # Add all pages to stack
        for p in (
            page_dashboard,
            page_medicines,
            page_customers,
            page_customer_address,
            page_sellers,
            page_person,
            page_prescriptions,
            page_inventory_log,
            page_transactions,
            page_sales,
        ):
            self.pages.addWidget(p)

        # ✅ Dashboard card mapping
        # Must match dashboard_page.py index map
        index_to_widget = {
            1: page_medicines,
            2: page_customers,
            3: page_customer_address,
            4: page_sellers,
            5: page_person,
            6: page_prescriptions,
            7: page_inventory_log,
            8: page_transactions,
            9: page_sales,
        }
        page_dashboard.navigate_to = lambda idx: goto(index_to_widget.get(idx, page_dashboard))

        # --------------------
        # Sidebar buttons
        # --------------------
        menu_layout.addWidget(_make_section("Overview"))

        btn_dashboard = QPushButton("Dashboard")
        _style_sidebar_button(btn_dashboard)
        btn_dashboard.clicked.connect(lambda: goto(page_dashboard))
        menu_layout.addWidget(btn_dashboard)

        menu_layout.addWidget(_make_section("Core"))

        btn_medicines = QPushButton("Medicines")
        _style_sidebar_button(btn_medicines)
        btn_medicines.clicked.connect(lambda: goto(page_medicines))
        menu_layout.addWidget(btn_medicines)

        btn_customers = QPushButton("Customers")
        _style_sidebar_button(btn_customers)
        btn_customers.clicked.connect(lambda: goto(page_customers))
        menu_layout.addWidget(btn_customers)

        btn_customer_address = QPushButton("Customer Address")
        _style_sidebar_button(btn_customer_address)
        btn_customer_address.clicked.connect(lambda: goto(page_customer_address))
        menu_layout.addWidget(btn_customer_address)

        btn_sellers = QPushButton("Sellers")
        _style_sidebar_button(btn_sellers)
        btn_sellers.clicked.connect(lambda: goto(page_sellers))
        menu_layout.addWidget(btn_sellers)

        menu_layout.addWidget(_make_section("Operations"))

        btn_prescriptions = QPushButton("Prescriptions")
        _style_sidebar_button(btn_prescriptions)
        btn_prescriptions.clicked.connect(lambda: goto(page_prescriptions))
        menu_layout.addWidget(btn_prescriptions)

        btn_inventory_log = QPushButton("Inventory Log")
        _style_sidebar_button(btn_inventory_log)
        btn_inventory_log.clicked.connect(lambda: goto(page_inventory_log))
        menu_layout.addWidget(btn_inventory_log)

        btn_transactions = QPushButton("Transactions")
        _style_sidebar_button(btn_transactions)
        btn_transactions.clicked.connect(lambda: goto(page_transactions))
        menu_layout.addWidget(btn_transactions)

        btn_sales = QPushButton("Sales")
        _style_sidebar_button(btn_sales)
        btn_sales.clicked.connect(lambda: goto(page_sales))
        menu_layout.addWidget(btn_sales)

        menu_layout.addWidget(_make_section("Admin tables"))

        btn_person = QPushButton("Person")
        _style_sidebar_button(btn_person)
        btn_person.clicked.connect(lambda: goto(page_person))
        menu_layout.addWidget(btn_person)

        menu_layout.addStretch(1)

        # --------------------
        # Layout
        # --------------------
        root_layout.addWidget(sidebar, 0)
        root_layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)

        self.pages.setCurrentWidget(page_dashboard)

        # ✅ OPEN MAXIMIZED EVERY TIME
        self.setWindowState(self.windowState() | Qt.WindowMaximized)

        print("[MainWindow] Loaded. Pages:", self.pages.count())