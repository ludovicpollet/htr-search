from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QPolygonF,
    QResizeEvent,
)
from PySide6.QtWidgets import QWidget


class ImageWidget(QWidget):
    """
    A widget to display an image and overlay polygons representing lines of text.

    Attributes:
        selected_line_changed (Signal): Signal emitted when the selected line index changes.
    """

    selected_line_changed = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ImageWidget.

        Args:
            parent (Optional[QWidget]): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.original_pixmap: Optional[QPixmap] = None
        self.matching_lines: List[Dict[str, Any]] = []
        self.polygons: List[Optional[QPolygonF]] = []
        self.selected_index: int = -1  # Index of the currently selected line

    def set_image_and_lines(self, pixmap: QPixmap, lines: List[Dict[str, Any]]) -> None:
        """
        Set the image and matching lines to display.

        Args:
            pixmap (QPixmap): The image pixmap to display.
            lines (List[Dict[str, Any]]): The list of matching lines with their coordinates.
        """
        self.original_pixmap = pixmap
        self.matching_lines = lines
        self.create_polygons()
        self.selected_index = -1
        self.update()

    def create_polygons(self) -> None:
        """
        Create scaled polygons based on the current widget size and matching lines.
        """
        self.polygons = []
        if not self.original_pixmap or not self.matching_lines:
            return

        pixmap_width = self.original_pixmap.width()
        pixmap_height = self.original_pixmap.height()
        widget_width = self.width()
        widget_height = self.height()
        if widget_width == 0 or widget_height == 0:
            return

        # Determine scaling factors
        aspect_ratio_pixmap = pixmap_width / pixmap_height
        aspect_ratio_widget = widget_width / widget_height

        if aspect_ratio_pixmap > aspect_ratio_widget:
            # Pixmap is wider than widget
            scale = widget_width / pixmap_width
        else:
            # Pixmap is taller than widget
            scale = widget_height / pixmap_height

        offset_x = (widget_width - pixmap_width * scale) / 2
        offset_y = (widget_height - pixmap_height * scale) / 2

        for line in self.matching_lines:
            coords = line.get("coords")
            if coords:
                points = [
                    QPointF(x * scale + offset_x, y * scale + offset_y)
                    for x, y in coords
                ]
                polygon = QPolygonF(points)
                self.polygons.append(polygon)
            else:
                self.polygons.append(None)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the widget, including the image and any polygons.

        Args:
            event (QPaintEvent): The paint event.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.original_pixmap:
            # Scale the pixmap to fit the widget size
            scaled_pixmap = self.original_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Draw the pixmap at the center
            pixmap_x = int((self.width() - scaled_pixmap.width()) / 2)
            pixmap_y = int((self.height() - scaled_pixmap.height()) / 2)
            painter.drawPixmap(pixmap_x, pixmap_y, scaled_pixmap)

            # Draw the polygons
            for idx, polygon in enumerate(self.polygons):
                if polygon:
                    if idx == self.selected_index:
                        # Highlighted polygon
                        pen = QPen(
                            QColor(0, 255, 0, 200), 2
                        )  # Green for selected polygon
                        brush = QBrush(QColor(0, 255, 0, 50))
                    else:
                        pen = QPen(QColor(255, 0, 0, 200), 2)  # Red for other polygons
                        brush = QBrush(QColor(255, 0, 0, 50))
                    painter.setPen(pen)
                    painter.setBrush(brush)
                    painter.drawPolygon(polygon)
        painter.end()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Handle the widget resize event.

        Args:
            event (QResizeEvent): The resize event.
        """
        super().resizeEvent(event)
        self.create_polygons()
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events to select polygons.

        Args:
            event (QMouseEvent): The mouse event.
        """
        if not self.polygons:
            return

        x = event.x()
        y = event.y()
        clicked_point = QPointF(x, y)

        for idx, polygon in enumerate(self.polygons):
            if polygon and polygon.containsPoint(
                clicked_point, Qt.FillRule.OddEvenFill
            ):
                self.selected_index = idx
                self.selected_line_changed.emit(idx)
                self.update()
                break
        else:
            # Clicked outside any polygon
            self.selected_index = -1
            self.selected_line_changed.emit(-1)
            self.update()

    def clear(self) -> None:
        """
        Clear the widget content.
        """
        self.original_pixmap = None
        self.matching_lines = []
        self.polygons = []
        self.selected_index = -1
        self.update()
