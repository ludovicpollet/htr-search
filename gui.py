import os
import re
from html import escape
from typing import Any, Dict, List

from PySide6.QtCore import QSize, Qt, QModelIndex
from PySide6.QtGui import (
    QAbstractTextDocumentLayout,
    QPalette,
    QPixmap,
    QPainter,
    QTextDocument,
    QTextOption,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
    QStyleOptionViewItem,
)

from image_widget import ImageWidget
from indexer import group_lines_by_document, search_index


class HTMLDelegate(QStyledItemDelegate):
    """Custom item delegate to render HTML content in QListWidget items."""

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        """
        Paint the item with HTML content and handle selection highlighting.

        Args:
            painter (QPainter): The painter used for drawing.
            option (QStyleOptionViewItem): Provides parameters describing the item.
            index (QModelIndex): The model index of the item to be painted.
        """
        # Get the data to be displayed
        text = index.data(Qt.DisplayRole)

        # Create a QTextDocument for the HTML text
        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setHtml(text)
        doc.setTextWidth(option.rect.width())

        # Disable word wrapping in the QTextDocument
        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.NoWrap)
        doc.setDefaultTextOption(text_option)

        painter.save()

        # Handle selection background using Qt's default
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Translate the painter to the item's top-left corner
        painter.translate(option.rect.left(), option.rect.top())

        # Create a PaintContext
        ctx = QAbstractTextDocumentLayout.PaintContext()
        if option.state & QStyle.State_Selected:
            # Set text color to highlighted text color
            ctx.palette.setColor(
                QPalette.Text, option.palette.highlightedText().color()
            )
        else:
            # Set text color to normal text color
            ctx.palette.setColor(QPalette.Text, option.palette.text().color())

        # Draw the document
        doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """
        Provide the size hint for the item based on its HTML content.

        Args:
            option (QStyleOptionViewItem): Provides parameters describing the item.
            index (QModelIndex): The model index of the item.

        Returns:
            QSize: The size hint for the item.
        """
        # Get the data to be displayed
        text = index.data(Qt.DisplayRole)

        # Create a QTextDocument for the HTML text
        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setHtml(text)
        doc.setTextWidth(option.rect.width())

        # Disable word wrapping in the QTextDocument
        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.NoWrap)
        doc.setDefaultTextOption(text_option)

        doc_size = doc.size().toSize()

        padding = 2
        height = doc_size.height() + padding

        # Return the size of the text document
        return QSize(doc_size.width(), height)


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
        self.search_results: List[str] = []
        self.doc_lines: Dict[str, List[Dict[str, Any]]] = {}
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
        self.text_list.setItemDelegate(HTMLDelegate())
        self.text_list.setUniformItemSizes(True)
        self.text_list.setWrapping(False)
        self.text_list.setWordWrap(False)
        self.text_list.setSpacing(2)
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
        # Get user input
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Input Error", "Please enter a search query.")
            return
        self.current_query = query

        # Make sure we clear the eventual previous search results
        self.results_list.clear()
        self.image_widget.clear()
        self.text_list.clear()
        self.status_label.clear()
        self.search_results = []
        self.doc_lines = {}

        # Search the index for matching lines
        try:
            matching_lines = search_index(self.index_dir, query)
        except Exception as e:
            QMessageBox.critical(self, "Search Error", f"Failed to perform search: {e}")
            return

        # Handle empty results
        if not matching_lines:
            self.status_label.setText("No results found.")
            return

        # Groupe matching lines by document for display
        grouped_lines = group_lines_by_document(matching_lines)
        sorted_documents = sorted(
            grouped_lines.items(), key=lambda x: x[1]["num_lines"], reverse=True
        )

        # Prepare the data in each document for display
        for document_path, data in sorted_documents:
            num_lines = data["num_lines"]
            lines = data["lines"]
            item_text = f"{document_path} ({num_lines} matching lines)"
            self.results_list.addItem(item_text)
            self.search_results.append(document_path)
            self.doc_lines[document_path] = lines

        # Update status text
        self.status_label.setText(
            f"Found {len(matching_lines)} lines matching the query in {len(self.search_results)} documents."
        )

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

        # Get the matching lines for the selected document
        self.matching_lines = self.doc_lines.get(xml_file_path, [])

        # Pass the image and matching lines to the image widget
        self.image_widget.set_image_and_lines(self.original_pixmap, self.matching_lines)

        # Populate the text panel with matching transcriptions
        self.text_list.clear()
        for line in self.matching_lines:
            content = line["content"] or ""
            matched_terms = line.get("matched_terms", [])
            highlighted_text = self.highlight_matched_terms(content, matched_terms)
            item = QListWidgetItem()
            item.setText(highlighted_text)
            self.text_list.addItem(item)

    def highlight_matched_terms(self, text: str, matched_terms: List[str]) -> str:
        """Highlight matched terms in the text using bold styling.

        Args:
            text (str): The original text.
            matched_terms (List[str]): The list of matched terms.

        Returns:
            str: HTML text with matched terms highlighted using HTML bold styling.
        """

        if not matched_terms:
            return text

        # Escape HTML special characters in text
        text = escape(text)

        # Remove duplicates and sort terms by length (longest first)
        unique_terms = sorted(set(matched_terms), key=len, reverse=True)

        # Escape terms for regex
        terms = [re.escape(term) for term in unique_terms]
        # Build regex pattern
        pattern = r"\b(" + "|".join(terms) + r")\b"

        # Function to wrap matched term in <strong> tags for bold styling
        def repl(match):
            return f"<strong>{match.group(0)}</strong>"

        # Replace matched terms with highlighted versions
        highlighted_text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

        return highlighted_text

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
