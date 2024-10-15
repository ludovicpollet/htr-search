import os
import sys
from typing import Any, Dict, List

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from indexer import search_index, group_lines_by_document
from image_widget import ImageWidget


class MainWindow(QWidget):
    def __init__(self, index_dir: str = "index_dir", image_extension: str = ".jpeg"):
        """
        Initialize the main window.

        Args:
            index_dir (str): The directory where the index is stored.
            image_extension (str): The image file extension to use.
        """
        super().__init__()
        self.setWindowTitle("pageXML Search")
        self.resize(1600, 1200)
        self.current_query: str = ""
        self.index_dir: str = index_dir
        self.image_extension: str = image_extension
        self.matching_lines: List[Dict[str, Any]] = []
        self.image_file_path: str = ""
        self.original_pixmap: QPixmap = QPixmap()
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface components."""
        # Main layout
        main_layout = QVBoxLayout()

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search query...")
        self.search_input.returnPressed.connect(self.perform_search)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)

        # Results list (list of documents)
        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(150)
        self.results_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.results_list.itemClicked.connect(self.display_result)

        # Content layout (horizontal)
        content_layout = QHBoxLayout()

        # Image display widget
        self.image_widget = ImageWidget()
        self.image_widget.setMinimumSize(400, 300)
        self.image_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Text panel (list of matching lines)
        self.text_list = QListWidget()
        self.text_list.setMinimumWidth(200)
        self.text_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Add widgets to content layout with stretch factors
        content_layout.addWidget(self.image_widget, stretch=3)
        content_layout.addWidget(self.text_list, stretch=2)

        # Status label
        self.status_label = QLabel()

        # Add widgets to main layout
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.results_list)
        main_layout.addLayout(content_layout)
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

        # Connect signals
        self.text_list.currentRowChanged.connect(self.on_text_list_selection_changed)
        self.image_widget.selected_line_changed.connect(self.on_image_selection_changed)
    
    def perform_search(self) -> None:
        """Perform a search based on the query in the search input."""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Input Error", "Please enter a search query.")
            return

        self.current_query = query
        self.results_list.clear()
        self.image_widget.clear()
        self.text_list.clear()
        self.status_label.clear()

        try:
            matching_lines = search_index(self.index_dir, query)
        except Exception as e:
            QMessageBox.critical(self, "Search Error", f"Failed to perform search: {e}")
            return
    
        if not matching_lines:
            self.status_label.setText("No results found.")
            return
        
        doc_dict = group_lines_by_document(matching_lines)
        sorted_docs = sorted(doc_dict.items(), key=lambda x: x[1]['num_lines'], reverse=True)
        self.search_results = []
        self.doc_lines = {}

        for doc_path, data in sorted_docs:
            num_lines = data['num_lines']
            lines = data['lines']
            item_text = f"{doc_path} ({num_lines} matching lines)"
            self.results_list.addItem(item_text)
            self.search_results.append(doc_path)
            self.doc_lines[doc_path] = lines
    
        self.status_label.setText(f"Found {len(self.search_results)} with lines matching the query.")

    def display_result(self, item: QListWidgetItem) -> None:
        """Display the selected result.

        Args:
            item (QListWidgetItem): The selected item from the results list.
        """
        selected_index = self.results_list.row(item)
        xml_file_path = self.search_results[selected_index]
        base_name, _ = os.path.splitext(xml_file_path)
        self.image_file_path = f"{base_name}{self.image_extension}"

        # Load the image
        self.original_pixmap = QPixmap(self.image_file_path)
        if self.original_pixmap.isNull():
            self.image_widget.clear()
            self.status_label.setText("Image not found.")
            return

        # Parse the XML to get lines
        self.matching_lines = self.doc_lines.get(xml_file_path, [])


        # Pass the image and matching lines to the image widget
        self.image_widget.set_image_and_lines(self.original_pixmap, self.matching_lines)

        # Populate the text panel with matching transcriptions
        self.text_list.clear()
        for line in self.matching_lines:
            self.text_list.addItem(line['content'])


    def on_text_list_selection_changed(self, current_row: int) -> None:
        """Handle selection changes in the text list.

        Args:
            current_row (int): The index of the currently selected row.
        """
        self.image_widget.selected_index = current_row if current_row != -1 else -1
        self.image_widget.update()

    def on_image_selection_changed(self, index: int) -> None:
        """Handle selection changes in the image widget.

        Args:
            index (int): The index of the selected line in the image widget.
        """
        self.text_list.blockSignals(True)
        if index != -1:
            self.text_list.setCurrentRow(index)
        else:
            self.text_list.clearSelection()
        self.text_list.blockSignals(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
