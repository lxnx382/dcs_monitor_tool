import sys
import json
import os
from dataclasses import dataclass
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QVBoxLayout, QPushButton, QFileDialog, QMenu,
    QDialog, QTextEdit, QHBoxLayout, QComboBox, QLabel, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPen, QColor


# =========================
# Custom Widgets (no scroll change)
# =========================

class NoScrollComboBox(QComboBox):
    """ComboBox that ignores mouse wheel events unless focused"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor_item = None  # Will be set by MonitorItem
    
    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()
    
    def showPopup(self):
        """Bring parent monitor to front when dropdown is opened"""
        if self.monitor_item and hasattr(self.monitor_item, 'bring_to_front'):
            self.monitor_item.bring_to_front()
        super().showPopup()

class NoScrollLineEdit(QLineEdit):
    """LineEdit that ignores mouse wheel events unless focused"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor_item = None  # Will be set by MonitorItem
    
    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()
    
    def focusInEvent(self, event):
        """Bring parent monitor to front when focused"""
        super().focusInEvent(event)
        # Bring monitor to front if reference exists
        if self.monitor_item and hasattr(self.monitor_item, 'bring_to_front'):
            self.monitor_item.bring_to_front()


# =========================
# Datenmodelle
# =========================

@dataclass
class DcsItem:
    name: str
    x: int
    y: int
    width: int
    height: int
    viewDx: int = 0
    viewDy: int = 0
    is_viewport: bool = False


# =========================
# Graphics Item
# =========================

class MonitorItem(QGraphicsRectItem):
    def __init__(self, w, h, name="UNASSIGNED"):
        super().__init__(0, 0, w, h)
        self.name = name
        self.is_viewport = False
        self.viewDx = 0
        self.viewDy = 0
        self.monitor_width = w
        self.monitor_height = h
        self._x = 0
        self._y = 0

        self.setFlags(QGraphicsRectItem.ItemIsSelectable)
        self.setPen(QPen(Qt.white, 2))
        self.setBrush(QColor(70, 120, 180, 120))

        # Overlay: Label + Dropdown
        from PySide6.QtWidgets import QGraphicsProxyWidget, QComboBox, QLabel
        from PySide6.QtGui import QFont

        self.label = QLabel()
        label_font = QFont()
        label_font.setPointSize(int(self.monitor_height * 0.05))  # Scaling based on monitor height
        self.label.setFont(label_font)
        self.label.setStyleSheet(
            "color: white; "
            "background: rgba(0,0,0,150); "
            "padding: 4px;"
        )

        self.combo = NoScrollComboBox()
        self.combo.monitor_item = self  # Reference to parent MonitorItem
        self.combo.addItems([
            "UNASSIGNED",
            "Viewport: Left",
            "Viewport: Center",
            "Viewport: Right",
            "Panel: FA_18C_IFEI",
            "Panel: FA_18C_RWR",
            "Panel: FA_18C_SARI",
            "Panel: LEFT_MFCD",
            "Panel: CENTER_MFCD",
            "Panel: RIGHT_MFCD",
        ])
        self.combo.currentTextChanged.connect(self.apply_selection)
        
        # No longer need activated signal since showPopup handles bring_to_front
        # self.combo.activated.connect(self.bring_to_front)

        self.proxy_label = QGraphicsProxyWidget(self)
        self.proxy_label.setWidget(self.label)
        self.proxy_label.setPos(2, 2)
        self.proxy_label.setFlag(QGraphicsProxyWidget.ItemIgnoresTransformations, False)
        self.proxy_label.setZValue(10)  # Above the rectangle

        self.proxy_combo = QGraphicsProxyWidget(self)
        self.proxy_combo.setWidget(self.combo)
        self.proxy_combo.setZValue(10)  # Above the rectangle

        # Combobox sizing - normal compact size
        self.combo_width = self.monitor_width * 0.7
        self.combo_height = self.monitor_height * 0.2
        combo_font = QFont()
        combo_font.setPointSize(int(self.combo_height * 0.4))  # Skalierung der Schriftgröße
        self.combo.setFont(combo_font)
        self.combo.setFixedSize(int(self.combo_width), int(self.combo_height))
        
        # Make dropdown popup wider to show full text
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(combo_font)
        max_width = 0
        for i in range(self.combo.count()):
            text_width = fm.horizontalAdvance(self.combo.itemText(i))
            max_width = max(max_width, text_width)
        # Add padding for scrollbar and margins
        popup_width = max_width + 60
        self.combo.view().setMinimumWidth(popup_width)
        self.combo.setStyleSheet(
            "QComboBox { "
            "background-color: rgba(50, 50, 50, 220); "
            "color: white; "
            "border: 2px solid rgba(100, 100, 100, 255); "
            "border-radius: 5px; "
            "padding: 4px; "
            "min-height: 30px; "
            "} "
            "QComboBox::drop-down { "
            "border: none; "
            "} "
            "QComboBox::down-arrow { "
            "image: none; "
            "border-left: 5px solid transparent; "
            "border-right: 5px solid transparent; "
            "border-top: 8px solid white; "
            "width: 0px; "
            "height: 0px; "
            "} "
            "QComboBox QAbstractItemView { "
            "background-color: rgba(50, 50, 50, 240); "
            "color: white; "
            "selection-background-color: rgba(100, 150, 200, 255); "
            "border: 2px solid rgba(100, 100, 100, 255); "
            "}"
        )
        
        # Make sure the popup appears on top of everything
        popup_view = self.combo.view()
        popup_view.window().setWindowFlags(
            popup_view.window().windowFlags() | Qt.WindowStaysOnTopHint
        )

        self.proxy_combo.setFlag(QGraphicsProxyWidget.ItemIgnoresTransformations, False)
        self.update_combo_position()

        # Offset/Override fields (initially hidden)
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit
        
        self.config_widget = QWidget()
        # Match the label styling (black background with transparency)
        self.config_widget.setStyleSheet(
            "QWidget { background: rgba(0, 0, 0, 150); border: none; padding: 4px; }"
            "QLabel { color: white; background: transparent; border: none; padding: 0px; margin: 0px; }"
            "QLineEdit { background: rgba(50, 50, 50, 200); color: white; border: 1px solid rgba(100, 100, 100, 180); padding: 1px; margin: 1px; }"
        )
        
        config_layout = QVBoxLayout()
        config_layout.setSpacing(2)
        config_layout.setContentsMargins(4, 4, 4, 4)
        
        # Calculate font size based on monitor height (match label font)
        config_font_size = int(self.monitor_height * 0.03)
        # Increase input width for better number visibility
        input_width = int(self.monitor_width * 0.12)
        
        # X Offset
        x_layout = QHBoxLayout()
        x_layout.setSpacing(2)
        x_label = QLabel("X:")
        x_label_font = QFont()
        x_label_font.setPointSize(config_font_size)
        x_label.setFont(x_label_font)
        self.x_offset_input = NoScrollLineEdit("0")
        self.x_offset_input.setFixedWidth(input_width)
        self.x_offset_input.setPlaceholderText("0")
        self.x_offset_input.setFont(x_label_font)
        self.x_offset_input.monitor_item = self  # Reference to parent MonitorItem
        x_layout.addWidget(x_label)
        x_layout.addWidget(self.x_offset_input)
        config_layout.addLayout(x_layout)
        
        # Y Offset
        y_layout = QHBoxLayout()
        y_layout.setSpacing(2)
        y_label = QLabel("Y:")
        y_label.setFont(x_label_font)
        self.y_offset_input = NoScrollLineEdit("0")
        self.y_offset_input.setFixedWidth(input_width)
        self.y_offset_input.setPlaceholderText("0")
        self.y_offset_input.setFont(x_label_font)
        self.y_offset_input.monitor_item = self  # Reference to parent MonitorItem
        y_layout.addWidget(y_label)
        y_layout.addWidget(self.y_offset_input)
        config_layout.addLayout(y_layout)
        
        # Width Override
        w_layout = QHBoxLayout()
        w_layout.setSpacing(2)
        w_label = QLabel("W:")
        w_label.setFont(x_label_font)
        self.width_input = NoScrollLineEdit("-1")
        self.width_input.setFixedWidth(input_width)
        self.width_input.setPlaceholderText("-1")
        self.width_input.setFont(x_label_font)
        self.width_input.monitor_item = self  # Reference to parent MonitorItem
        w_layout.addWidget(w_label)
        w_layout.addWidget(self.width_input)
        config_layout.addLayout(w_layout)
        
        # Height Override
        h_layout = QHBoxLayout()
        h_layout.setSpacing(2)
        h_label = QLabel("H:")
        h_label.setFont(x_label_font)
        self.height_input = NoScrollLineEdit("-1")
        self.height_input.setFixedWidth(input_width)
        self.height_input.setPlaceholderText("-1")
        self.height_input.setFont(x_label_font)
        self.height_input.monitor_item = self  # Reference to parent MonitorItem
        h_layout.addWidget(h_label)
        h_layout.addWidget(self.height_input)
        config_layout.addLayout(h_layout)
        
        self.config_widget.setLayout(config_layout)
        
        self.proxy_config = QGraphicsProxyWidget(self)
        self.proxy_config.setWidget(self.config_widget)
        self.proxy_config.setZValue(10)
        self.proxy_config.hide()  # Initially hidden

        self.update_label()
    
    def bring_to_front(self):
        """Bring this monitor to front when dropdown is activated"""
        if self.scene():
            # Reset all monitors to default z-value
            for item in self.scene().items():
                if isinstance(item, MonitorItem) and item != self:
                    item.setZValue(0)
                    item.proxy_label.setZValue(10)
                    item.proxy_combo.setZValue(10)
            # Bring this one to front with much higher z-values
            self.setZValue(100)
            self.proxy_label.setZValue(110)
            self.proxy_combo.setZValue(110)
    
    def mousePressEvent(self, event):
        """Bring to front when clicked"""
        self.bring_to_front()
        super().mousePressEvent(event)

    def setPos(self, *args):
        """Override setPos() to store position and update label"""
        super().setPos(*args)
        if len(args) == 1:  # QPointF
            self._x = int(args[0].x())
            self._y = int(args[0].y())
        else:  # x, y
            self._x = int(args[0])
            self._y = int(args[1])
        self.update_label()

    def update_combo_position(self):
        """Updates the dropdown position to keep it centered"""
        # Since ItemIgnoresTransformations is active, the widget is drawn in viewport coordinates
        # We need to use the center of the monitor rectangle
        center_x = self.monitor_width / 2
        center_y = self.monitor_height / 2
        print(f"{self.name} Monitor size: ({self.monitor_width}, {self.monitor_height})")
        print(f"{self.name} Center: ({center_x}, {center_y})")
        
        # Die tatsächliche Größe des Widgets verwenden
        actual_width = self.proxy_combo.size().width()
        actual_height = self.proxy_combo.size().height()
        print(f"{self.name} Actual size: ({actual_width}, {actual_height})")
        
        # Dropdown mittig platzieren (Zentrum minus halbe Dropdown-Größe)
        combo_x = center_x - (actual_width / 2)
        combo_y = center_y - (actual_height / 2)
        print(f"{self.name} Combo position: ({combo_x}, {combo_y})")
        print(f"{self.name} ---")
        
        self.proxy_combo.setPos(combo_x, combo_y)

    def apply_selection(self, text):
        if text.startswith("Viewport"):
            name = text.split(": ")[1]
            dx = {"Left": -1, "Center": 0, "Right": 1}[name]
            self.name = name
            self.is_viewport = True
            self.viewDx = dx
            self.viewDy = 0
            self.setBrush(QColor(0, 180, 0, 120))
            self.show_config_fields()
        elif text.startswith("Panel"):
            self.name = text.split(": ")[1]
            self.is_viewport = False
            self.setBrush(QColor(180, 120, 0, 120))
            self.show_config_fields()
        else:
            self.name = "UNASSIGNED"
            self.is_viewport = False
            self.setBrush(QColor(70, 120, 180, 120))
            self.hide_config_fields()

        # Label will be updated by MainWindow with DCS coordinates
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            if hasattr(view, 'window') and hasattr(view.window(), 'update_all_labels_with_dcs_coords'):
                view.window().update_all_labels_with_dcs_coords()
    
    def show_config_fields(self):
        """Show offset/override configuration fields"""
        self.proxy_config.show()
        # Position in bottom-left corner of monitor
        config_x = 2  # Small margin from left
        # Calculate bottom position (monitor height minus widget height minus margin)
        widget_height = self.proxy_config.size().height()
        config_y = self.monitor_height - widget_height - 2
        self.proxy_config.setPos(config_x, config_y)
    
    def hide_config_fields(self):
        """Hide offset/override configuration fields"""
        self.proxy_config.hide()

    def update_label(self, dcs_x=None, dcs_y=None):
        """Updates the label with DCS coordinates (relative to LEFT Viewport)"""
        if dcs_x is not None and dcs_y is not None:
            self.label.setText(f"{self.name}\nDCS X:{dcs_x} Y:{dcs_y}")
        else:
            # Fallback: Windows coordinates
            self.label.setText(f"{self.name}\nWin X:{self._x} Y:{self._y}")


# =========================
# Canvas
# =========================

class MonitorScene(QGraphicsScene):
    GRID = 50

    def drawBackground(self, painter, rect):
        painter.setPen(QPen(QColor(40, 40, 40)))
        left = int(rect.left()) - int(rect.left()) % self.GRID
        top = int(rect.top()) - int(rect.top()) % self.GRID

        x = left
        while x < rect.right():
            painter.drawLine(x, rect.top(), x, rect.bottom())
            x += self.GRID

        y = top
        while y < rect.bottom():
            painter.drawLine(rect.left(), y, rect.right(), y)
            y += self.GRID


# =========================
# Zoomable Graphics View
# =========================

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Allows scrolling/panning outside scene boundaries
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self._zoom = 1.0
        self._zoom_step = 1.15
        self._min_zoom_fallback = 0.05
        self._max_zoom = 20.0
        
        # For panning with middle mouse button
        self._is_panning = False
        self._pan_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            # Middle mouse button: activate panning
            self._is_panning = True
            self._pan_start_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning and self._pan_start_pos is not None:
            # Move the view
            delta = event.position() - self._pan_start_pos
            self._pan_start_pos = event.position()
            
            # Move scrollbars
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            # Middle mouse button release: deactivate panning
            self._is_panning = False
            self._pan_start_pos = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if not (event.modifiers() & Qt.ControlModifier):
            super().wheelEvent(event)
            return

        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()

        event.accept()

    def zoom_in(self):
        if self._zoom < self._max_zoom:
            self._zoom *= self._zoom_step
            self.scale(self._zoom_step, self._zoom_step)

    def zoom_out(self):
        min_zoom = self.compute_min_zoom()

        if self._zoom / self._zoom_step < min_zoom:
            return

        self._zoom /= self._zoom_step
        self.scale(1 / self._zoom_step, 1 / self._zoom_step)

    def compute_min_zoom(self) -> float:
        scene = self.scene()
        if not scene or not scene.items():
            return self._min_zoom_fallback

        scene_rect = scene.itemsBoundingRect()
        if scene_rect.isNull():
            return self._min_zoom_fallback

        view_rect = self.viewport().rect()
        if view_rect.width() == 0 or view_rect.height() == 0:
            return self._min_zoom_fallback

        sx = view_rect.width() / scene_rect.width()
        sy = view_rect.height() / scene_rect.height()

        return min(sx, sy) * 0.9


# =========================
# Lua Export
# =========================


def export_lua(items, filename):
    viewports = []
    panels = []

    for it in items:
        r = it.sceneBoundingRect()
        if it.is_viewport:
            viewports.append(DcsItem(
                it.name, int(r.x()), int(r.y()),
                int(r.width()), int(r.height()),
                it.viewDx, it.viewDy, True
            ))
        else:
            panels.append(DcsItem(
                it.name, int(r.x()), int(r.y()),
                int(r.width()), int(r.height())
            ))

    with open(filename, "w", encoding="utf-8") as f:
        f.write("_ = function(p) return p; end;\n")
        f.write("name = _('MyCockpit');\n")
        f.write("Description = 'Generated by DCS Monitor Tool'\n\n")

        f.write("Viewports =\n{\n")
        for v in viewports:
            aspect = v.width / v.height
            f.write(f"    {v.name} =\n")
            f.write(f"    {{\n")
            f.write(f"        x = {v.x};\n")
            f.write(f"        y = {v.y};\n")
            f.write(f"        width = {v.width};\n")
            f.write(f"        height = {v.height};\n")
            f.write(f"        viewDx = {v.viewDx};\n")
            f.write(f"        viewDy = {v.viewDy};\n")
            f.write(f"        aspect = {aspect};\n")
            f.write(f"    }},\n")
        f.write("}\n\n")

        for p in panels:
            f.write(f"{p.name} =\n")
            f.write(f"{{\n")
            f.write(f"    x = {p.x};\n")
            f.write(f"    y = {p.y};\n")
            f.write(f"    width = {p.width};\n")
            f.write(f"    height = {p.height};\n")
            f.write(f"}}\n\n")

        xs = [i.x for i in viewports + panels]
        ys = [i.y for i in viewports + panels]
        xe = [i.x + i.width for i in viewports + panels]
        ye = [i.y + i.height for i in viewports + panels]

        x0, y0 = min(xs), min(ys)
        w, h = max(xe) - x0, max(ye) - y0
        aspect = w / h

        f.write(f"Main =\n")
        f.write(f"{{\n")
        f.write(f"    x = {x0};\n")
        f.write(f"    y = {y0};\n")
        f.write(f"    width = {w};\n")
        f.write(f"    height = {h};\n")
        f.write(f"    aspect = {aspect};\n")
        f.write(f"}}\n")
        f.write(f"UIMainView = Main\n")
        f.write(f"GU_MAIN_VIEWPORT = Main\n")


# =========================
# Code Preview Dialog
# =========================

class CodePreviewDialog(QDialog):
    def __init__(self, code, filename = "", dcs_path="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lua Code Preview")
        self.resize(800, 600)
        self.code = code
        self.filename = filename
        self.dcs_path = dcs_path
        self.saved = False
        
        # Text editor for code display
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(code)
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet(
            "QTextEdit { font-family: 'Consolas', 'Courier New', monospace; font-size: 12pt; }"
        )
        
        # Buttons
        btn_save = QPushButton("Save as...")
        btn_save.clicked.connect(self.save_code)
        
        # Quick-Save button only shown if DCS path is configured
        self.btn_quick_save = None
        if dcs_path and os.path.isdir(dcs_path):
            self.btn_quick_save = QPushButton("💾 Quick Save to DCS")
            self.btn_quick_save.clicked.connect(self.quick_save_to_dcs)
            self.btn_quick_save.setToolTip(f"Saves directly to:\n{dcs_path}")
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        # Button-Layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        if self.btn_quick_save:
            button_layout.addWidget(self.btn_quick_save)
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_cancel)
        
        # Haupt-Layout
        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def quick_save_to_dcs(self):
        """Saves directly to the DCS MonitorSetup folder"""
        if not self.dcs_path or not os.path.isdir(self.dcs_path):
            print("DCS path not configured or invalid")
            return
        
        fn = f"{self.filename}.lua"
        filepath = os.path.join(self.dcs_path, fn)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.code)
            self.saved = True
            print(f"Successfully saved: {filepath}")
            
            # Also save .dml file if parent has the method
            if self.parent() and hasattr(self.parent(), 'save_dml_file'):
                dml_path = os.path.join(self.dcs_path, f"{self.filename}.dml")
                self.parent().save_dml_file(dml_path)
                print(f"Successfully saved: {dml_path}")
            
            self.accept()
        except Exception as e:
            print(f"Error during Quick Save: {e}")
    
    def save_code(self):
        fn, _ = QFileDialog.getSaveFileName(
            self, "Save as", "", "Lua (*.lua)"
        )
        if fn:
            try:
                with open(fn, "w", encoding="utf-8") as f:
                    f.write(self.code)
                self.saved = True
                
                # Also save .dml file if parent has the method
                if self.parent() and hasattr(self.parent(), 'save_dml_file'):
                    # Replace .lua extension with .dml
                    dml_path = fn.rsplit('.', 1)[0] + '.dml'
                    self.parent().save_dml_file(dml_path)
                    print(f"Successfully saved: {dml_path}")
                
                self.accept()
            except Exception as e:
                print(f"Error saving: {e}")


# =========================
# Main Window
# =========================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DCS Monitor Layout Tool")

        self.scene = MonitorScene()
        self.saved_assignments = {}  # Stores monitor assignments
        self.config_file = os.path.join(os.path.dirname(__file__), "config.json")

        # Scene is dynamically derived from Windows monitor layout
        self.view = ZoomableGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)

        # Name and Description fields
        from PySide6.QtWidgets import QLineEdit, QLabel
        
        name_layout = QHBoxLayout()
        name_label = QLabel("Layout Name:")
        self.name_input = QLineEdit()
        self.name_input.setText("MyCockpit")
        self.name_input.setPlaceholderText("Enter layout name")
        self.name_input.setMaximumWidth(200)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        name_layout.addStretch()
        
        desc_layout = QHBoxLayout()
        desc_label = QLabel("Description:")
        self.desc_input = QLineEdit()
        self.desc_input.setText("Generated by DCS Monitor Tool")
        self.desc_input.setPlaceholderText("Enter description")
        self.desc_input.setMaximumWidth(300)
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.desc_input)
        desc_layout.addStretch()
        
        # Controls legend
        legend_layout = QHBoxLayout()
        legend_label = QLabel(
            "🎮 Controls: "
            "<b>Ctrl + Scroll</b> = Zoom | "
            "<b>Middle Mouse</b> = Pan | "
            "<b>Click Monitor</b> = Bring to Front"
        )
        legend_label.setStyleSheet(
            "color: #888; "
            "font-size: 10pt; "
            "padding: 4px; "
            "background: rgba(50, 50, 50, 100); "
            "border-radius: 3px;"
        )
        legend_layout.addWidget(legend_label)
        legend_layout.addStretch()

        # Buttons
        btn_load = QPushButton("📂 Load Layout")
        btn_load.clicked.connect(self.load_layout)
        btn_load.setToolTip("Load monitor assignments from .dml file")
        
        btn_display_settings = QPushButton("🖥️ Windows Display Settings")
        btn_display_settings.clicked.connect(self.open_display_settings)
        btn_display_settings.setToolTip("Open Windows Display Settings to arrange monitors")
        
        btn_refresh = QPushButton("🔄 Refresh Monitor Layout")
        btn_refresh.clicked.connect(self.refresh_monitors)
        
        btn_offsets = QPushButton("⚙️ Config")
        btn_offsets.clicked.connect(self.open_config)
        btn_offsets.setToolTip("Edit Config File for Monitor Offsets, DCS Path, etc.")
        
        btn_export = QPushButton("Export DCS Lua")
        btn_export.clicked.connect(self.export)

        # Button-Layout (oben)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(btn_load)
        button_layout.addWidget(btn_offsets)
        button_layout.addWidget(btn_display_settings)
        button_layout.addWidget(btn_refresh)

        # Haupt-Layout
        layout = QVBoxLayout()
        layout.addLayout(name_layout)
        layout.addLayout(desc_layout)
        layout.addLayout(legend_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.view)
        layout.addWidget(btn_export)

        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)

        # Windows-Monitore beim Start einlesen
        QTimer.singleShot(0, self.load_windows_monitors)

    def save_current_assignments(self):
        """Save current monitor assignments based on monitor names."""
        self.saved_assignments.clear()
        
        for item in self.scene.items():
            if isinstance(item, MonitorItem):
                # Use the monitor name as key (e.g. "MONITOR_1")
                monitor_id = item.monitor_id
                current_text = item.combo.currentText()
                
                # Only save if an assignment exists
                if current_text and current_text != "UNASSIGNED":
                    self.saved_assignments[monitor_id] = current_text
                    print(f"Saved: {monitor_id} -> {current_text}")
    
    def restore_assignment(self, item, monitor_id):
        """Restore saved assignment for a monitor."""
        if monitor_id in self.saved_assignments:
            saved_text = self.saved_assignments[monitor_id]
            index = item.combo.findText(saved_text)
            if index >= 0:
                item.combo.setCurrentIndex(index)
                print(f"Restored: {monitor_id} -> {saved_text}")
            else:
                print(f"Could not find saved text '{saved_text}' in combo for {monitor_id}")
    
    def load_offsets_config(self):
        """Loads the global config (only DCS path)"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Create default config with only global settings
        default_config = {
            "_dcs_monitor_setup_path": "C:\\DCS\\DCS World\\Config\\MonitorSetup",
            "_comment": "This is the global config. Only the DCS path is stored here. All other settings (name, description, offsets) are stored per-layout in .dml files."
        }
        return default_config
    
    def save_offsets_config(self, config):
        """Saves the global config"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def open_config(self):
        """Opens the offset config for editing"""
        # Load or create config
        config = self.load_offsets_config()
        
        # Save config if it doesn't exist yet
        if not os.path.exists(self.config_file):
            self.save_offsets_config(config)
        
        # Open in default text editor
        try:
            if sys.platform == 'win32':
                os.startfile(self.config_file)
            elif sys.platform == 'darwin':
                os.system(f'open "{self.config_file}"')
            else:
                os.system(f'xdg-open "{self.config_file}"')
        except Exception as e:
            print(f"Error opening config: {e}")
    
    def open_display_settings(self):
        """Opens Windows Display Settings"""
        try:
            if sys.platform == 'win32':
                # Open Windows Display Settings using ms-settings URI
                os.system('start ms-settings:display')
            elif sys.platform == 'darwin':
                # macOS System Preferences Displays
                os.system('open "x-apple.systempreferences:com.apple.preference.displays"')
            else:
                # Linux - try common display settings commands
                os.system('xrandr --query || gnome-control-center display || systemsettings5 display')
        except Exception as e:
            print(f"Error opening display settings: {e}")
    
    def save_dml_file(self, filepath):
        """Save monitor assignments to .dml file"""
        try:
            dml_data = {
                "version": "1.0",
                "name": self.name_input.text() or "MyCockpit",
                "description": self.desc_input.text() or "Generated by DCS Monitor Tool",
                "monitor_assignments": {},
                "monitor_info": {},
                "monitor_offsets": {}
            }
            
            for item in self.scene.items():
                if isinstance(item, MonitorItem):
                    monitor_id = item.monitor_id
                    assignment = item.combo.currentText()
                    
                    # Only save non-UNASSIGNED monitors
                    if assignment != "UNASSIGNED":
                        dml_data["monitor_assignments"][monitor_id] = assignment
                        
                        # Save offsets/overrides for assigned monitors
                        try:
                            x_offset = int(item.x_offset_input.text() or "0")
                            y_offset = int(item.y_offset_input.text() or "0")
                            width_override = int(item.width_input.text() or "-1")
                            height_override = int(item.height_input.text() or "-1")
                            
                            dml_data["monitor_offsets"][monitor_id] = {
                                "x": x_offset,
                                "y": y_offset,
                                "width": width_override,
                                "height": height_override
                            }
                        except ValueError:
                            # If parsing fails, use defaults
                            dml_data["monitor_offsets"][monitor_id] = {
                                "x": 0,
                                "y": 0,
                                "width": -1,
                                "height": -1
                            }
                    
                    # Save monitor info for validation
                    dml_data["monitor_info"][monitor_id] = {
                        "width": item.monitor_width,
                        "height": item.monitor_height,
                        "x": int(item.pos().x()),
                        "y": int(item.pos().y())
                    }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(dml_data, f, indent=4)
            
            return True
        except Exception as e:
            print(f"Error saving .dml file: {e}")
            return False
    
    def load_layout(self):
        """Load monitor assignments from .dml file"""
        # Get DCS path from config and use it as starting directory
        config = self.load_offsets_config()
        dcs_path = config.get("_dcs_monitor_setup_path", "")
        
        # Use DCS path as starting directory if it exists, otherwise use current directory
        start_dir = dcs_path if dcs_path and os.path.isdir(dcs_path) else ""
        
        fn, _ = QFileDialog.getOpenFileName(
            self, "Load Layout", start_dir, "DCS Monitor Layout (*.dml)"
        )
        if not fn:
            return
        
        try:
            with open(fn, 'r', encoding='utf-8') as f:
                dml_data = json.load(f)
            
            if "version" not in dml_data or "monitor_assignments" not in dml_data:
                print("Invalid .dml file format")
                return
            
            # Check if monitor configuration matches
            warnings = []
            if "monitor_info" in dml_data:
                for monitor_id, saved_info in dml_data["monitor_info"].items():
                    # Find corresponding monitor in current scene
                    found = False
                    for item in self.scene.items():
                        if isinstance(item, MonitorItem) and item.monitor_id == monitor_id:
                            found = True
                            # Check if resolution or position changed
                            if (item.monitor_width != saved_info["width"] or 
                                item.monitor_height != saved_info["height"]):
                                warnings.append(
                                    f"{monitor_id}: Resolution changed from "
                                    f"{saved_info['width']}x{saved_info['height']} to "
                                    f"{item.monitor_width}x{item.monitor_height}"
                                )
                            if (int(item.pos().x()) != saved_info["x"] or 
                                int(item.pos().y()) != saved_info["y"]):
                                warnings.append(
                                    f"{monitor_id}: Position changed from "
                                    f"({saved_info['x']}, {saved_info['y']}) to "
                                    f"({int(item.pos().x())}, {int(item.pos().y())})"
                                )
                            break
                    
                    if not found:
                        warnings.append(f"{monitor_id}: Monitor not found in current configuration")
            
            # Show warnings if any
            if warnings:
                from PySide6.QtWidgets import QMessageBox
                warning_msg = "Monitor configuration has changed:\n\n" + "\n".join(warnings)
                warning_msg += "\n\nDo you want to load the layout anyway?"
                
                reply = QMessageBox.warning(
                    self, "Monitor Configuration Changed", warning_msg,
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    return
            
            # Load name and description
            if "name" in dml_data:
                self.name_input.setText(dml_data["name"])
            if "description" in dml_data:
                self.desc_input.setText(dml_data["description"])
            
            # Apply assignments and offsets
            loaded_count = 0
            for item in self.scene.items():
                if isinstance(item, MonitorItem):
                    monitor_id = item.monitor_id
                    if monitor_id in dml_data["monitor_assignments"]:
                        assignment = dml_data["monitor_assignments"][monitor_id]
                        index = item.combo.findText(assignment)
                        if index >= 0:
                            item.combo.setCurrentIndex(index)
                            loaded_count += 1
                            
                            # Load offsets if available
                            if "monitor_offsets" in dml_data and monitor_id in dml_data["monitor_offsets"]:
                                offsets = dml_data["monitor_offsets"][monitor_id]
                                item.x_offset_input.setText(str(offsets.get("x", 0)))
                                item.y_offset_input.setText(str(offsets.get("y", 0)))
                                item.width_input.setText(str(offsets.get("width", -1)))
                                item.height_input.setText(str(offsets.get("height", -1)))
                        else:
                            print(f"Warning: Assignment '{assignment}' not found for {monitor_id}")
            
            print(f"Successfully loaded {loaded_count} monitor assignments from {fn}")
            
        except json.JSONDecodeError as e:
            print(f"Error parsing .dml file: {e}")
        except Exception as e:
            print(f"Error loading layout: {e}")
    
    def update_all_labels_with_dcs_coords(self):
        """Updates all monitor labels with DCS coordinates relative to LEFT Viewport"""
        all_items = []
        viewports = []
        
        for item in self.scene.items():
            if isinstance(item, MonitorItem):
                all_items.append(item)
                if item.is_viewport:
                    viewports.append(item)
        
        if not all_items:
            return
        
        # Null point: If viewports exist, use their top-left corner
        # Otherwise use the top-left corner of all monitors
        if viewports:
            min_x = min(int(item.pos().x()) for item in viewports)
            min_y = min(int(item.pos().y()) for item in viewports)
        else:
            min_x = min(int(item.pos().x()) for item in all_items)
            min_y = min(int(item.pos().y()) for item in all_items)
        
        # Update all labels
        for item in all_items:
            win_x = int(item.pos().x())
            win_y = int(item.pos().y())
            dcs_x = win_x - min_x
            dcs_y = win_y - min_y
            item.update_label(dcs_x, dcs_y)
        
        # Update bounding box
        self.update_dcs_bounding_box()
    
    def refresh_monitors(self):
        """Refreshes the monitor display and keeps assignments"""
        # Save current assignments
        self.save_current_assignments()
        
        # Clear all items from the scene
        self.scene.clear()
        
        # Reload monitors
        self.load_windows_monitors()

    def load_windows_monitors(self):
        """
        Reads the currently registered Windows monitors
        and creates them as MonitorItems in the scene 1:1.
        """
        try:
            from screeninfo import get_monitors
        except ImportError:
            raise RuntimeError("Please install 'screeninfo': pip install screeninfo")

        monitors = get_monitors()
        
        # Find the primary monitor
        primary_monitor = None
        for m in monitors:
            if getattr(m, 'is_primary', False):
                primary_monitor = m
                break
        
        # Use the actual Windows DISPLAY numbers
        # These come from the hardware (which port on the graphics card)
        # and have NOTHING to do with the position in the layout
        display_to_ui_number = {}
        
        for m in monitors:
            # Extract the number from the display name (e.g. "\\.\DISPLAY1" -> 1)
            if 'DISPLAY' in m.name:
                display_num = int(m.name.split('DISPLAY')[-1])
                display_to_ui_number[m.name] = display_num
            else:
                # Fallback if the name is formatted differently
                display_to_ui_number[m.name] = monitors.index(m) + 1
        
        # Debug: Show all monitor information
        print("\n=== Monitor Information ===")
        for idx, m in enumerate(monitors):
            ui_num = display_to_ui_number.get(m.name, '?')
            print(f"Index {idx}: Name='{m.name}', UI-Number={ui_num}, X={m.x}, Y={m.y}, "
                  f"Width={m.width}, Height={m.height}, "
                  f"Primary={getattr(m, 'is_primary', 'N/A')}")
        print("===========================\n")

        # Adjust scene bounds roughly to desktop with extra margin for free zooming/panning
        min_x = min(m.x for m in monitors)
        min_y = min(m.y for m in monitors)
        max_x = max(m.x + m.width for m in monitors)
        max_y = max(m.y + m.height for m in monitors)
        
        # Add 50% margin on all sides
        margin_x = (max_x - min_x) * 0.5
        margin_y = (max_y - min_y) * 0.5

        self.scene.setSceneRect(
            min_x - margin_x, 
            min_y - margin_y, 
            (max_x - min_x) + (2 * margin_x), 
            (max_y - min_y) + (2 * margin_y)
        )
        
        for m in monitors:
            # Use the calculated UI number
            ui_number = display_to_ui_number.get(m.name, monitors.index(m) + 1)
            label = f"MONITOR_{ui_number}"
            monitor_id = f"MONITOR_{ui_number}"  # Unique ID based on Windows Display number
            
            item = MonitorItem(m.width, m.height, name=label)
            item.monitor_id = monitor_id  # Store the ID in the item
            item.setPos(m.x, m.y)
            self.scene.addItem(item)
            
            # Restore saved assignment if available
            self.restore_assignment(item, monitor_id)

        self.zoom_to_fit()
        
        # Update all labels with DCS coordinates
        self.update_all_labels_with_dcs_coords()
    
    def update_dcs_bounding_box(self):
        """Draw orange bounding box around all assigned monitors (DCS render area)"""
        # Remove old bounding box if exists
        if hasattr(self, 'dcs_bbox_rect'):
            self.scene.removeItem(self.dcs_bbox_rect)
        if hasattr(self, 'dcs_bbox_label'):
            self.scene.removeItem(self.dcs_bbox_label)
        
        # Get all assigned monitors (not UNASSIGNED or MONITOR_X)
        assigned_items = []
        for item in self.scene.items():
            if isinstance(item, MonitorItem):
                if not (item.name == "UNASSIGNED" or item.name.startswith("MONITOR_")):
                    assigned_items.append(item)
        
        if not assigned_items:
            return
        
        # Calculate bounding box
        min_x = min(int(item.pos().x()) for item in assigned_items)
        min_y = min(int(item.pos().y()) for item in assigned_items)
        max_x = max(int(item.pos().x()) + int(item.monitor_width) for item in assigned_items)
        max_y = max(int(item.pos().y()) + int(item.monitor_height) for item in assigned_items)
        
        bbox_width = max_x - min_x
        bbox_height = max_y - min_y
        
        # Draw orange bounding box
        from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
        from PySide6.QtGui import QPen, QColor, QFont
        
        self.dcs_bbox_rect = QGraphicsRectItem(min_x, min_y, bbox_width, bbox_height)
        orange_pen = QPen(QColor(255, 140, 0), 6)  # Orange, 6px thick
        orange_pen.setStyle(Qt.DashLine)
        self.dcs_bbox_rect.setPen(orange_pen)
        self.dcs_bbox_rect.setZValue(-1)  # Behind monitors
        self.scene.addItem(self.dcs_bbox_rect)
        
        # Add text label with resolution
        self.dcs_bbox_label = QGraphicsTextItem()
        label_text = f"DCS Resolution: {bbox_width} × {bbox_height}"
        self.dcs_bbox_label.setPlainText(label_text)
        
        # Style the text - font size scales with bounding box width
        font_size = int(0.016 * bbox_width)
        font = QFont("Arial", font_size, QFont.Bold)
        self.dcs_bbox_label.setFont(font)
        self.dcs_bbox_label.setDefaultTextColor(QColor(255, 140, 0))  # Orange
        
        # Position text at top-left corner of bounding box
        # Adjust Y position based on font size to keep text above the box
        text_offset_y = font_size * 2  # Scale offset with font size
        self.dcs_bbox_label.setPos(min_x + 10, min_y - text_offset_y)
        self.dcs_bbox_label.setZValue(200)  # Above everything
        self.scene.addItem(self.dcs_bbox_label)

    def zoom_to_fit(self):
        if not self.scene.items():
            return

        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        self.view._zoom = self.view.transform().m11()

    def export(self):
        # Collect all MonitorItems
        items = [i for i in self.scene.items() if isinstance(i, MonitorItem)]
        
        # Generate the Lua code as a string
        lua_code = self.generate_lua_code(items)
        
        # Show preview dialog with DCS path
        config = self.load_offsets_config()
        dcs_path = config.get("_dcs_monitor_setup_path", "")
        filename = self.name_input.text() or "MyCockpit"
        dialog = CodePreviewDialog(lua_code, filename, dcs_path, self)
        dialog.exec()
    
    def generate_lua_code(self, items):
        """Generates the Lua code and returns it as a string"""
        viewports = []
        panels = []
        viewport_monitors = []  # Only viewport monitors for null point calculation

        # First collect all items and find viewports for null point
        # IMPORTANT: Exclude monitors with MONITOR_ prefix or UNASSIGNED name
        temp_items = []
        for it in items:
            # Skip unassigned monitors completely
            if it.name == "UNASSIGNED" or it.name.startswith("MONITOR_"):
                continue
                
            x = int(it.pos().x())
            y = int(it.pos().y())
            width = int(it.monitor_width)
            height = int(it.monitor_height)
            
            temp_items.append((it, x, y, width, height))
            
            # Only use viewports for null point calculation
            if it.is_viewport:
                viewport_monitors.append(DcsItem(
                    it.name, x, y, width, height, 0, 0, False
                ))
        
        # Find the DCS null point: top-left corner of VIEWPORTS (not all monitors!)
        if not viewport_monitors:
            return ""
        
        min_x = min(m.x for m in viewport_monitors)
        min_y = min(m.y for m in viewport_monitors)
        
        # ========================================
        # MODE: PHYSICAL 1:1
        # ========================================
        # Use physical desktop coordinates
        # No FOV extension, pure 1:1 mapping
        # ========================================
        
        for it, x, y, width, height in temp_items:
            # Normalize to DCS coordinates (0,0 = top-left corner of viewports)
            dcs_x = x - min_x
            dcs_y = y - min_y
            
            # Apply offsets and size overrides from MonitorItem input fields
            output_width = width  # Default: original monitor width
            output_height = height  # Default: original monitor height
            
            try:
                offset_x = int(it.x_offset_input.text() or "0")
                offset_y = int(it.y_offset_input.text() or "0")
                dcs_x += offset_x
                dcs_y += offset_y
                
                # Check for width/height overrides (-1 means use original)
                config_width = int(it.width_input.text() or "-1")
                config_height = int(it.height_input.text() or "-1")
                
                if config_width != -1:
                    output_width = config_width
                if config_height != -1:
                    output_height = config_height
            except (ValueError, AttributeError):
                # If parsing fails or fields don't exist, use defaults
                pass
            
            if it.is_viewport:
                # Physical width, physical X position
                # Note: Position calculation always uses original monitor dimensions
                viewports.append(DcsItem(
                    it.name, dcs_x, dcs_y, output_width, output_height,
                    it.viewDx, it.viewDy, True
                ))
            else:
                # Panels with configurable dimensions
                panels.append(DcsItem(
                    it.name, dcs_x, dcs_y, output_width, output_height
                ))

        # Generate code
        lines = []
        lines.append("_ = function(p) return p; end;")
        
        # Use name and description from GUI inputs
        layout_name = self.name_input.text() or "MyCockpit"
        layout_description = self.desc_input.text() or "Generated by DCS Monitor Tool"
        
        lines.append(f"name = _('{layout_name}');")
        lines.append(f"Description = '{layout_description}'")
        lines.append("")
        lines.append("Viewports =")
        lines.append("{")
        
        for v in viewports:
            aspect = v.width / v.height
            lines.append(f"    {v.name} =")
            lines.append(f"    {{")
            lines.append(f"        x = {v.x};")
            lines.append(f"        y = {v.y};")
            lines.append(f"        width = {v.width};")
            lines.append(f"        height = {v.height};")
            lines.append(f"        viewDx = {v.viewDx};")
            lines.append(f"        viewDy = {v.viewDy};")
            lines.append(f"        aspect = {aspect};")
            lines.append(f"    }},")
        
        lines.append("}")
        lines.append("")
        
        for p in panels:
            lines.append(f"{p.name} =")
            lines.append(f"{{")
            lines.append(f"    x = {p.x};")
            lines.append(f"    y = {p.y};")
            lines.append(f"    width = {p.width};")
            lines.append(f"    height = {p.height};")
            lines.append(f"}}")
            lines.append("")
        
        # ============================================
        # MAIN CALCULATION (PHYSICAL 1:1)
        # ============================================
        # Main = bounding box of physical viewports
        if viewports:
            xs = [v.x for v in viewports]
            ys = [v.y for v in viewports]
            xe = [v.x + v.width for v in viewports]
            ye = [v.y + v.height for v in viewports]

            x0, y0 = min(xs), min(ys)
            w, h = max(xe) - x0, max(ye) - y0
            aspect = w / h

            lines.append(f"Main =")
            lines.append(f"{{")
            lines.append(f"    x = {x0};")
            lines.append(f"    y = {y0};")
            lines.append(f"    width = {w};")
            lines.append(f"    height = {h};")
            lines.append(f"    aspect = {aspect};")
            lines.append(f"}}")
            lines.append(f"UIMainView = Main")
            lines.append(f"GU_MAIN_VIEWPORT = Main")
        
        return "\n".join(lines)


# =========================
# Entry
# =========================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1400, 900)
    win.show()
    sys.exit(app.exec())
