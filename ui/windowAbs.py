from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QPushButton, QApplication, QLabel,
    QSizeGrip, QVBoxLayout, QFrame, QToolButton, QMenu, QDialog, QStyle
)
from PyQt6.QtCore import Qt, QPoint, QRect, QEvent, QVariantAnimation, QEasingCurve, QTimer, QSize, QPointF, QRectF
from PyQt6.QtGui import QMouseEvent, QResizeEvent, QAction, QCursor, QPainterPath, QPainter, QColor, QBrush, QPen

from ui.WindowsAbstractWindow import WindowsFramelessWindow


class CustomTitleBar(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('CustomTitleBar')
        self.parent = parent
        self.setMinimumHeight(32)
        self.hLayout = QHBoxLayout(self)
        self.hLayout.setContentsMargins(10, 0, 10, 0)
        self.hLayout.setSpacing(8)
        self.title = QLabel("Custom Window")
        self.btn_min = QPushButton("—")
        self.btn_max = QPushButton("□")
        self.btn_close = QPushButton("×")
        self.btn_close.setObjectName("closeButton")
        for btn in [self.btn_min, self.btn_max, self.btn_close]:
            btn.setFixedSize(30, 30)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet("QPushButton {background-color: transparent; border: none; border-radius: 4px} QPushButton:hover {background-color: grey;}")
        self.hLayout.addWidget(self.title)
        self.hLayout.addStretch()
        self.hLayout.addWidget(self.btn_min)
        self.hLayout.addWidget(self.btn_max)
        self.hLayout.addWidget(self.btn_close)
        self.btn_min.clicked.connect(parent.showMinimized)
        self.btn_max.clicked.connect(self.toggle_maximize)
        self.btn_close.clicked.connect(parent.close)
        self.old_pos = None
        self.normal_size = None
        self.offset = None
        self.isDrag = False

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            if self.normal_size:
                self.parent.setGeometry(self.x(), self.y(), self.normal_size.width(), self.normal_size.height())
        else:
            self.normal_size = self.parent.geometry()
            self.parent.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.parent.getDirectionMousePos() is None:
            self.isDrag = True
            event.accept()
        self.parent.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.parent.mouseMoveEvent(event)
        if self.parent.isMaximized():
            self.parent.showNormal()
            if self.normal_size:
                self.parent.setGeometry(self.x(), self.y(), self.normal_size.width(), self.normal_size.height())
        elif self.isDrag:
            self.isDrag = False
            self.parent.windowHandle().startSystemMove()

    def mouseReleaseEvent(self, event):
        self.parent.mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()

class OutlineWidget(QWidget):
    def __init__(self, parent, window_manager):
        super().__init__(parent)
        self.window_manager = window_manager
        self.parent_window = parent

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.update_position()
        self.hide()

    def update_position(self):
        if self.parent_window:
            global_pos = self.parent_window.mapToGlobal(QPoint(0, 0))

            self.setGeometry(
                global_pos.x(),
                global_pos.y(),
                self.parent_window.width(),
                self.parent_window.height()
            )
            self.update()

    def paintEvent(self, event):
        if not self.parent_window or not self.parent_window.isActiveWindow():
            return

        painter = QPainter(self)
        pen = QPen(QColor(255, 255, 255), 2)
        painter.setPen(pen)

        parent_rect_global = self.parent_window.frameGeometry()
        parent_global_top_left = parent_rect_global.topLeft()

        other_windows = [
            w for w in self.window_manager.windows
            if w is not self.parent_window and w.isVisible() and not w.isMinimized()
        ]

        for win in other_windows:
            win_rect = win.frameGeometry()
            intersection = parent_rect_global.intersected(win_rect)

            if not intersection.isNull():
                local_intersection = intersection.translated(-parent_global_top_left)

                if intersection.top() == parent_rect_global.top():
                    painter.drawLine(
                        local_intersection.left(),
                        0,
                        local_intersection.right(),
                        0
                    )

                if intersection.bottom() == parent_rect_global.bottom():
                    painter.drawLine(
                        local_intersection.left(),
                        self.height() - 1,
                        local_intersection.right(),
                        self.height() - 1
                    )

                if intersection.left() == parent_rect_global.left():
                    painter.drawLine(
                        0,
                        local_intersection.top(),
                        0,
                        local_intersection.bottom()
                    )

                if intersection.right() == parent_rect_global.right():
                    painter.drawLine(
                        self.width() - 1,
                        local_intersection.top(),
                        self.width() - 1,
                        local_intersection.bottom()
                    )

class WindowManager:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = WindowManager()
        return cls._instance

    def __init__(self):
        self.windows = []
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self.check_window_positions)
        self.position_timer.start(100)

    def add_window(self, window):
        self.windows.append(window)
        self.update_active_window_outline()

    def remove_window(self, window):
        if window in self.windows:
            self.windows.remove(window)
        self.update_active_window_outline()

    def update_active_window_outline(self):
        active_window = QApplication.activeWindow()
        for window in self.windows:
            if hasattr(window, 'outline_widget'):
                if window is active_window:
                    window.outline_widget.update_position()
                    window.outline_widget.show()
                    window.outline_widget.raise_()
                else:
                    window.outline_widget.hide()

    def check_window_positions(self):
        for window in self.windows:
            if hasattr(window, 'outline_widget') and window.isActiveWindow():
                window.outline_widget.update_position()


class WindowAbs(WindowsFramelessWindow):
    def __init__(self):
        super().__init__()
        # self.setMinimumWidth(750)
        # self.action_bar = CustomActionBar(self)
        # self._titleBar.hBoxLayout.insertWidget(2, self.action_bar, 0, Qt.AlignmentFlag.AlignLeft)


class DialogAbs(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.corner_radius = 10
        self.background_color = QColor(12, 12, 12)
        self.border_color = QColor(80, 80, 80)
        self.border_width = 2
        self.pointMode = None

        self.outline_widget = OutlineWidget(None, WindowManager.instance())
        self.outline_widget.parent_window = self
        self.outline_widget.update_position()
        self.outline_widget.hide()
        WindowManager.instance().add_window(self)

        self.rootLayout = QVBoxLayout(self)
        self.rootLayout.setContentsMargins(0, 0, 0, 0)
        self.rootLayout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        self.title_bar.btn_max.hide()
        self.title_bar.setFixedHeight(32)
        self.rootLayout.addWidget(self.title_bar)

        self.centralContainer = QWidget(self)
        self.rootLayout.addWidget(self.centralContainer)
        self.centralLayout = QHBoxLayout(self.centralContainer)
        self.centralLayout.setContentsMargins(0, 0, 0, 0)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.checkMousePos)
        self.timer.start(10)

    def setCentralWidget(self, widget):
        for i in reversed(range(self.centralLayout.count())):
            old = self.centralLayout.takeAt(i)
            if old.widget():
                old.widget().deleteLater()
        self.centralLayout.addWidget(widget)

    def setWindowTitle(self, title):
        self.title_bar.title.setText(title)
        return super().setWindowTitle(title)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        radius = self.corner_radius

        path = QPainterPath()
        path.moveTo(rect.left(), rect.top() + radius)
        path.quadTo(rect.left(), rect.top(), rect.left() + radius, rect.top())
        path.lineTo(rect.right() - radius, rect.top())
        path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + radius)
        path.lineTo(rect.right(), rect.bottom() - radius)
        path.quadTo(rect.right(), rect.bottom(), rect.right() - radius, rect.bottom())
        path.lineTo(rect.left() + radius, rect.bottom())
        path.quadTo(rect.left(), rect.bottom(), rect.left(), rect.bottom() - radius)
        path.lineTo(rect.left(), rect.top() + radius)

        painter.setBrush(QBrush(self.background_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

    def checkMousePos(self):
        if self.maximumSize() == self.minimumSize():
            return
        direct = self.getDirectionMousePos()
        if direct in ["top_right", "bottom_left"]:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif direct in ["top_left", "bottom_right"]:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif direct in ["right", "left"]:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif direct in ["top", "bottom"]:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def getDirectionMousePos(self):
        pos = self.mapFromGlobal(QCursor.pos())
        if self.isMaximized() or self.maximumSize() == self.minimumSize():
            return None
        if pos.x() > self.width() - 10 and pos.y() < 10:
            return "top_right"
        elif pos.x() < 10 and pos.y() < 10:
            return "top_left"
        elif pos.y() < 10:
            return "top"
        elif pos.x() > self.width() - 10 and pos.y() > self.height() - 10:
            return "bottom_right"
        elif pos.x() < 10 and pos.y() > self.height() - 10:
            return "bottom_left"
        elif pos.y() > self.height() - 10:
            return "bottom"
        elif pos.x() > self.width() - 10:
            return "right"
        elif pos.x() < 10:
            return "left"
        return None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pointMode = self.getDirectionMousePos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.pointMode = None
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.maximumSize() != self.minimumSize():
            geometry = self.geometry()
            if self.pointMode:
                pos = QCursor.pos()
                if self.pointMode == "top_right":
                    geometry.setTopRight(pos)
                elif self.pointMode == "top_left":
                    oldpos = QPoint(geometry.x(), geometry.y())
                    geometry.setTopLeft(pos)
                    geometry.setX(oldpos.x())
                    geometry.setY(oldpos.y())
                elif self.pointMode == "bottom_right":
                    geometry.setBottomRight(pos)
                elif self.pointMode == "bottom_left":
                    geometry.setBottomLeft(pos)
                elif self.pointMode == "top":
                    geometry.setTop(pos.y())
                elif self.pointMode == "bottom":
                    geometry.setBottom(pos.y())
                elif self.pointMode == "right":
                    geometry.setRight(pos.x())
                elif self.pointMode == "left":
                    geometry.setLeft(pos.x())
                self.setGeometry(geometry)
        super().mouseMoveEvent(event)

    def closeEvent(self, event):
        self.outline_widget.close()
        super().closeEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        self.outline_widget.update_position()
        WindowManager.instance().update_active_window_outline()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.outline_widget.update_position()
        WindowManager.instance().update_active_window_outline()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange:
            WindowManager.instance().update_active_window_outline()
            self.outline_widget.update_position()

def information(parent, title: str, text: str, btn_text="Ok", width=600, height=400):
    dialog = DialogAbs(parent)
    wid = QWidget()
    dialog.setCentralWidget(wid)
    dialog.setFixedSize(width, height)
    dialog.setWindowTitle(title)

    layout = QVBoxLayout(wid)

    label = QLabel(text)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label, stretch=1)

    button_layout = QHBoxLayout()
    button_layout.addStretch()

    button = QPushButton(btn_text)
    button.setFixedWidth(100)
    button.clicked.connect(dialog.close)
    button_layout.addWidget(button)

    button_layout.addStretch()
    layout.addLayout(button_layout)

    dialog.exec()

def critical(parent, title: str, text: str, btn_text="Ok", width=600, height=300):
    QApplication.beep()

    dialog = DialogAbs(parent)
    wid = QWidget()
    dialog.setCentralWidget(wid)
    dialog.setFixedSize(width, height)
    dialog.setWindowTitle(title)

    layout = QVBoxLayout(wid)

    content_layout = QHBoxLayout()

    icon_label = QLabel()
    icon = dialog.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
    icon_label.setPixmap(icon.pixmap(64, 64))
    content_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop)

    label = QLabel(text)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
    content_layout.addWidget(label, stretch=1)

    layout.addLayout(content_layout)

    button_layout = QHBoxLayout()
    button_layout.addStretch()

    button = QPushButton(btn_text)
    button.setFixedWidth(100)
    button.clicked.connect(dialog.close)
    button_layout.addWidget(button)

    button_layout.addStretch()
    layout.addLayout(button_layout)

    dialog.exec()

def question(parent, title: str, text: str, yes_text="Yes", no_text="No", width=500, height=200) -> bool:
    # QApplication.beep()

    dialog = DialogAbs(parent)
    dialog.setFixedSize(width, height)
    dialog.setWindowTitle(title)

    wid = QWidget()
    dialog.setCentralWidget(wid)

    layout = QVBoxLayout(wid)

    content_layout = QHBoxLayout()

    icon_label = QLabel()
    icon = dialog.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)
    icon_label.setPixmap(icon.pixmap(64, 64))
    content_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop)

    label = QLabel(text)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
    content_layout.addWidget(label, stretch=1)

    layout.addLayout(content_layout)

    result = {"value": None}

    button_layout = QHBoxLayout()
    button_layout.addStretch()

    yes_button = QPushButton(yes_text)
    yes_button.setFixedWidth(100)
    no_button = QPushButton(no_text)
    no_button.setFixedWidth(100)

    yes_button.clicked.connect(lambda: (result.update({"value": True}), dialog.accept()))
    no_button.clicked.connect(lambda: (result.update({"value": False}), dialog.reject()))

    button_layout.addWidget(yes_button)
    button_layout.addWidget(no_button)
    button_layout.addStretch()

    layout.addLayout(button_layout)

    dialog.exec()
    return result["value"] is True