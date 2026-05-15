from PySide6.QtWidgets import QApplication, QTabWidget
import sys

from app.ui.transactions_page import TransactionsPage
from app.ui.sales_page import SalesPage

app = QApplication(sys.argv)
tabs = QTabWidget()
tabs.addTab(TransactionsPage(), "Transactions")
tabs.addTab(SalesPage(), "Sales")
tabs.resize(1100, 700)
tabs.show()
sys.exit(app.exec())