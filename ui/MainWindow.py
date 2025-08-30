import os
import json

from PyQt6 import QtCore
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QProgressBar, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QSizePolicy, QFrame, QSpacerItem, QRadioButton,
    QButtonGroup, QSpinBox, QGroupBox, QTextEdit
)
from ui.windowAbs import WindowAbs
from func.loader import DownloadManager

SETTINGS_FILE = "settings.json"
HISTORY_FILE = "history.json"

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QTimer


class ExpandableSide(QWidget):
    def __init__(self, title, min_w=0, max_w=360, side="left"):
        super().__init__()
        self._min = min_w
        self._max = max_w
        self._width = min_w
        self.side = side
        self._expanded = False

        self.setFixedWidth(self._width)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self.container = QFrame()
        self.container.setFrameShape(QFrame.Shape.StyledPanel)
        self.container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        header = QLabel(title)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFixedHeight(28)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(6)

        inner_layout = QVBoxLayout()
        inner_layout.setContentsMargins(6, 6, 6, 6)
        inner_layout.setSpacing(6)
        inner_layout.addWidget(header)
        inner_layout.addLayout(self.content_layout)
        inner_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.container.setLayout(inner_layout)

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.container)
        self.setLayout(layout)

        self.anim = QPropertyAnimation(self, b"fixedWidthProp")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def get_fixedWidthProp(self):
        return self._width

    def set_fixedWidthProp(self, w):
        self._width = w
        self.setFixedWidth(int(w))

    fixedWidthProp = pyqtProperty(float, fget=get_fixedWidthProp, fset=set_fixedWidthProp)

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)

    def expand(self, animate=True):
        if self._expanded: return
        self._expanded = True
        if animate:
            self.anim.stop()
            self.anim.setStartValue(self.width())
            self.anim.setEndValue(self._max)
            self.anim.start()
        else:
            self.setFixedWidth(self._max)

    def collapse(self, animate=True):
        if not self._expanded: return
        self._expanded = False
        if animate:
            self.anim.stop()
            self.anim.setStartValue(self.width())
            self.anim.setEndValue(self._min)
            self.anim.start()
        else:
            self.setFixedWidth(self._min)

    def toggle(self):
        if self._expanded:
            self.collapse()
        else:
            self.expand()

class DownloadCard(QWidget):
    def __init__(self, index, title, url, manager: DownloadManager, remove_callback, main_window):
        super().__init__()
        self.index = index
        self.manager = manager
        self.url = url
        self.remove_callback = remove_callback
        self.main_window = main_window
        self.animation = None
        self.original_style = self.styleSheet()

        self.title_label = QLabel(title)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.url_label = QLabel(url)
        self.url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.status_label = QLabel("В очереди")

        self.btn_start = QPushButton("Скачать")
        self.btn_start.setEnabled(False)

        self.btn_stop = QPushButton("Остановить")
        self.btn_stop.setEnabled(False)

        self.btn_show = QPushButton("Показать в папке")
        self.btn_show.setEnabled(False)

        self.btn_remove = QPushButton("Удалить")
        self.btn_remove.setFixedWidth(80)
        self.btn_remove.setEnabled(True)

        h = QHBoxLayout()
        h.addWidget(self.btn_start)
        h.addWidget(self.btn_stop)
        h.addWidget(self.btn_show)
        h.addWidget(self.btn_remove)

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.url_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addLayout(h)
        self.setLayout(layout)

        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_remove.clicked.connect(self.on_remove)
        self.btn_show.clicked.connect(self.show_in_folder)
        manager.progress_changed.connect(self.on_progress)
        manager.status_changed.connect(self.on_status)
        manager.info_received.connect(self.on_info)

    def on_start(self):
        self.manager.out_dir = self.main_window.out_dir_edit_right.text().strip() or "."
        proxy_str = self.main_window._get_proxy_str(self.url)
        self.manager.proxy = proxy_str
        self.manager.start_download(self.index)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_show.setEnabled(False)
        self.btn_remove.setEnabled(False)
        self.status_label.setText("Запуск...")

    def on_stop(self):
        self.manager.stop_download(self.index)
        self.btn_stop.setEnabled(False)
        self.btn_show.setEnabled(True)
        self.btn_remove.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.status_label.setText("Остановка...")

    def on_remove(self):
        self.remove_callback(self.index)

    def on_progress(self, idx, percent):
        if idx != self.index:
            return
        self.progress_bar.setValue(int(percent))

    def on_status(self, idx, status):
        if idx != self.index:
            return
        self.status_label.setText(status)
        lowered = status.lower() if status else ""
        finished_keywords = ("заверш", "файл готов", "ошибк")
        if any(k in lowered for k in finished_keywords):
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.btn_remove.setEnabled(True)
            self.btn_show.setEnabled(True)

    def on_info(self, idx, info):
        if idx != self.index:
            return
        title = info.get('title', 'Без названия')
        self.title_label.setText(title)

        out_dir = self.main_window.out_dir_edit_right.text().strip() or "."
        ext = info.get('ext', 'mp4')
        filename = f"{title}.{ext}"
        self.manager.queue[self.index]["_filename"] = filename
        filepath = os.path.join(out_dir, filename)
        print(title, ext, filepath)
        if os.path.exists(filepath):
            self.btn_start.setEnabled(False)
            self.btn_show.setEnabled(True)
        else:
            self.btn_start.setEnabled(True)
            self.btn_show.setEnabled(False)

        self.manager.queue[self.index]["_filepath"] = filepath

    def show_in_folder(self):
        filepath = self.manager.queue[self.index].get("_filepath").replace("/", "\\")
        if os.path.exists(filepath):
            path = f"explorer /select, \"{filepath}\""
            print(path)
            os.system(path)
        else:
            QMessageBox.warning(self, "Ошибка", "Файл не найден, возможно вы его уже удалили!")
            out_dir = self.main_window.out_dir_edit_right.text().strip() or "."
            os.system("start "+out_dir)

    def highlight_card(self):
        if self.animation and self.animation.state() == QPropertyAnimation.State.Running:
            self.animation.stop()

        self.animation = QPropertyAnimation(self, b"background_color")
        self.animation.setDuration(1000)
        self.animation.setStartValue(QColor(255, 255, 0, 150))
        self.animation.setEndValue(QColor(255, 255, 255, 0))
        self.animation.start()

        QTimer.singleShot(1100, self.reset_style)

    def get_background_color(self):
        return self.palette().color(self.backgroundRole())

    def set_background_color(self, color):
        palette = self.palette()
        palette.setColor(self.backgroundRole(), color)
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    def reset_style(self):
        self.setAutoFillBackground(False)
        self.setStyleSheet(self.original_style)

    background_color = QtCore.pyqtProperty(QColor, get_background_color, set_background_color)

class MainWindow(WindowAbs):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyTubeLoader")
        self.resize(1060, 700)
        self.manager = DownloadManager()
        self.cards = {}
        self.history = []
        self.settings = {"out_dir": os.path.join(os.getcwd(), "downloads"),
                         "proxy_mode": "none",
                         "proxy_port": 1080,
                         "proxy_custom": "",
                         "history_limit": 50,
                         "proxy_list_mode": "none",
                         "proxy_whitelist": "",
                         "proxy_blacklist": ""}
        self.load_settings()
        self.load_history()
        main_layout = QHBoxLayout()
        container = QWidget()
        container.setLayout(main_layout)
        try:
            self.setCentralWidget(container)
        except Exception:
            self.setLayout(main_layout)
        self.left_panel = ExpandableSide("История", min_w=0, max_w=320, side="left")
        self.history_list = QListWidget()
        self.history_list.setMinimumWidth(220)
        self.left_panel.addWidget(self.history_list)
        main_layout.addWidget(self.left_panel)
        center_widget = QWidget()
        center_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(10, 10, 10, 10)
        center_widget.setLayout(center_layout)
        toggles_layout = QHBoxLayout()
        self.toggle_left_btn = QPushButton("История")
        self.toggle_left_btn.setFixedHeight(34)
        self.toggle_left_btn.clicked.connect(self.left_panel.toggle)
        self.toggle_right_btn = QPushButton("Настройки")
        self.toggle_right_btn.setFixedHeight(34)
        self.toggle_right_btn.clicked.connect(self._toggle_right)
        toggles_layout.addWidget(self.toggle_left_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        toggles_layout.addStretch()
        toggles_layout.addWidget(self.toggle_right_btn, alignment=Qt.AlignmentFlag.AlignRight)
        center_layout.addLayout(toggles_layout)
        add_layout = QHBoxLayout()
        self.url_edit = QLineEdit()
        add_btn = QPushButton("Добавить в очередь")
        add_btn.clicked.connect(self.add_video)
        add_layout.addWidget(self.url_edit)
        add_layout.addWidget(add_btn)
        center_layout.addLayout(add_layout)
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(480)
        center_layout.addWidget(self.list_widget)
        control_layout = QHBoxLayout()
        btn_start_all = QPushButton("Скачать все")
        btn_stop_all = QPushButton("Остановить все")
        btn_start_all.clicked.connect(self.start_all)
        btn_stop_all.clicked.connect(self.stop_all)
        control_layout.addWidget(btn_start_all)
        control_layout.addWidget(btn_stop_all)
        center_layout.addLayout(control_layout)
        main_layout.addWidget(center_widget, stretch=1)
        self.right_panel = ExpandableSide("Настройки", min_w=0, max_w=500, side="right")
        settings_widget = QWidget()
        settings_layout = QVBoxLayout()
        settings_layout.setContentsMargins(6, 6, 6, 6)
        folder_layout2 = QHBoxLayout()
        self.out_dir_edit_right = QLineEdit(self.settings["out_dir"])
        self.out_dir_edit_right.setMinimumHeight(26)
        browse_btn2 = QPushButton("Выбрать")
        browse_btn2.setFixedHeight(26)
        browse_btn2.clicked.connect(self.browse_folder)
        self.out_dir_edit_right.textChanged.connect(self.sync_out_dir_fields)
        folder_layout2.addWidget(self.out_dir_edit_right)
        folder_layout2.addWidget(browse_btn2)
        settings_layout.addLayout(folder_layout2)
        open_download_folder_btn = QPushButton("Открыть папку загрузок")
        open_download_folder_btn.clicked.connect(lambda d, x=self.out_dir_edit_right: os.system("start "+x.text()) if os.path.exists(x.text()) \
                                                                                                else QMessageBox.warning(self, "Ошибка", "Указанный путь не найден!\n"+x.text()))
        settings_layout.addWidget(open_download_folder_btn)
        proxy_box = QGroupBox("Прокси")
        proxy_box_layout = QVBoxLayout()
        self.proxy_none_rb = QRadioButton("Без прокси")
        self.proxy_s4_rb = QRadioButton("Socks4")
        self.proxy_s5_rb = QRadioButton("Socks5")
        self.proxy_custom_rb = QRadioButton("Свои")
        self.proxy_group = QButtonGroup()
        self.proxy_group.addButton(self.proxy_none_rb)
        self.proxy_group.addButton(self.proxy_s4_rb)
        self.proxy_group.addButton(self.proxy_s5_rb)
        self.proxy_group.addButton(self.proxy_custom_rb)
        rb_layout = QHBoxLayout()
        rb_layout.addWidget(self.proxy_none_rb)
        rb_layout.addWidget(self.proxy_s4_rb)
        rb_layout.addWidget(self.proxy_s5_rb)
        rb_layout.addWidget(self.proxy_custom_rb)
        proxy_box_layout.addLayout(rb_layout)
        self.socks_port_widget = QWidget()
        sp_layout = QHBoxLayout()
        sp_layout.setContentsMargins(0, 0, 0, 0)
        sp_layout.addWidget(QLabel("Порт:"))
        self.socks_port_spin = QSpinBox()
        self.socks_port_spin.setRange(1, 65535)
        self.socks_port_spin.setValue(self.settings.get("proxy_port", 1080))
        sp_layout.addWidget(self.socks_port_spin)
        self.socks_port_widget.setLayout(sp_layout)
        self.custom_widget = QWidget()
        cw_layout = QHBoxLayout()
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.addWidget(QLabel("Адрес:"))
        self.custom_edit = QLineEdit(self.settings.get("proxy_custom", ""))
        cw_layout.addWidget(self.custom_edit)
        self.custom_widget.setLayout(cw_layout)
        proxy_box_layout.addWidget(self.socks_port_widget)
        proxy_box_layout.addWidget(self.custom_widget)
        proxy_box.setLayout(proxy_box_layout)
        settings_layout.addWidget(proxy_box)
        self.proxy_none_rb.toggled.connect(self._on_proxy_mode_changed)
        self.proxy_s4_rb.toggled.connect(self._on_proxy_mode_changed)
        self.proxy_s5_rb.toggled.connect(self._on_proxy_mode_changed)
        self.proxy_custom_rb.toggled.connect(self._on_proxy_mode_changed)
        self.socks_port_spin.valueChanged.connect(self.save_settings)
        self.custom_edit.textChanged.connect(self.save_settings)
        list_box = QGroupBox("Списки для прокси")
        list_box_layout = QVBoxLayout()
        self.list_none_rb = QRadioButton("Без списков")
        self.list_white_rb = QRadioButton("Белый список (прокси только для них)")
        self.list_black_rb = QRadioButton("Черный список (прокси для всех, кроме них)")
        self.list_group = QButtonGroup()
        self.list_group.addButton(self.list_none_rb)
        self.list_group.addButton(self.list_white_rb)
        self.list_group.addButton(self.list_black_rb)
        list_rb_layout = QVBoxLayout()
        list_rb_layout.addWidget(self.list_none_rb)
        list_rb_layout.addWidget(self.list_white_rb)
        list_rb_layout.addWidget(self.list_black_rb)
        list_box_layout.addLayout(list_rb_layout)
        self.list_edit = QTextEdit()
        self.list_edit.setMaximumHeight(100)
        self.list_edit.setPlaceholderText("Введите домены/URL, разделенные запятыми или новыми строками")
        list_box_layout.addWidget(self.list_edit)
        list_box.setLayout(list_box_layout)
        settings_layout.addWidget(list_box)
        self.list_none_rb.toggled.connect(self._on_list_mode_changed)
        self.list_white_rb.toggled.connect(self._on_list_mode_changed)
        self.list_black_rb.toggled.connect(self._on_list_mode_changed)
        self.list_edit.textChanged.connect(self._on_list_text_changed)
        settings_layout.addWidget(QLabel("Максимум записей в истории:"))
        self.history_limit_edit = QLineEdit(str(self.settings.get("history_limit", 50)))
        self.history_limit_edit.setMaximumWidth(80)
        self.history_limit_edit.textChanged.connect(self.save_settings)
        settings_layout.addWidget(self.history_limit_edit)
        settings_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        settings_widget.setLayout(settings_layout)
        self.right_panel.addWidget(settings_widget)
        main_layout.addWidget(self.right_panel)
        self.manager.info_received.connect(self.on_info_received)
        self.manager.info_error.connect(self.on_info_error)
        self._restore_proxy_ui()
        self._restore_list_ui()
        if not self.history:
            self.history_list.addItem("Пусто")

    def _toggle_right(self):
        self.right_panel.toggle()

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выбрать папку")
        if folder:
            self.out_dir_edit_right.setText(folder)
            self.out_dir_edit_right.setText(folder)
            self.save_settings()

    def sync_out_dir_fields(self):
        t = self.out_dir_edit_right.text().strip()
        self.out_dir_edit_right.setText(t)
        self.save_settings()

    def _on_proxy_mode_changed(self):
        if self.proxy_none_rb.isChecked():
            self.socks_port_widget.hide()
            self.custom_widget.hide()
            self.settings["proxy_mode"] = "none"
        elif self.proxy_s4_rb.isChecked():
            self.socks_port_widget.show()
            self.custom_widget.hide()
            self.settings["proxy_mode"] = "socks4"
        elif self.proxy_s5_rb.isChecked():
            self.socks_port_widget.show()
            self.custom_widget.hide()
            self.settings["proxy_mode"] = "socks5"
        elif self.proxy_custom_rb.isChecked():
            self.socks_port_widget.hide()
            self.custom_widget.show()
            self.settings["proxy_mode"] = "custom"
        self.save_settings()

    def _restore_proxy_ui(self):
        mode = self.settings.get("proxy_mode", "none")
        if mode == "none":
            self.proxy_none_rb.setChecked(True)
        elif mode == "socks4":
            self.proxy_s4_rb.setChecked(True)
        elif mode == "socks5":
            self.proxy_s5_rb.setChecked(True)
        elif mode == "custom":
            self.proxy_custom_rb.setChecked(True)
        self.socks_port_spin.setValue(self.settings.get("proxy_port", 1080))
        self.custom_edit.setText(self.settings.get("proxy_custom", ""))
        self._on_proxy_mode_changed()

    def _on_list_mode_changed(self, checked):
        if not checked:
            return
        if self.list_none_rb.isChecked():
            self.settings["proxy_list_mode"] = "none"
        elif self.list_white_rb.isChecked():
            self.settings["proxy_list_mode"] = "whitelist"
        elif self.list_black_rb.isChecked():
            self.settings["proxy_list_mode"] = "blacklist"
        self._restore_list_ui()
        self.save_settings()

    def _on_list_text_changed(self):
        mode = self.settings.get("proxy_list_mode", "none")
        if mode == "none":
            return
        text = self.list_edit.toPlainText().strip()
        if mode == "whitelist":
            self.settings["proxy_whitelist"] = text
        elif mode == "blacklist":
            self.settings["proxy_blacklist"] = text
        self.save_settings()

    def _restore_list_ui(self):
        mode = self.settings.get("proxy_list_mode", "none")
        self.list_none_rb.blockSignals(True)
        self.list_white_rb.blockSignals(True)
        self.list_black_rb.blockSignals(True)
        if mode == "whitelist":
            self.list_white_rb.setChecked(True)
        elif mode == "blacklist":
            self.list_black_rb.setChecked(True)
        else:
            self.list_none_rb.setChecked(True)
        self.list_none_rb.blockSignals(False)
        self.list_white_rb.blockSignals(False)
        self.list_black_rb.blockSignals(False)

        text = ""
        if mode == "whitelist":
            text = self.settings.get("proxy_whitelist", "")
        elif mode == "blacklist":
            text = self.settings.get("proxy_blacklist", "")
        self.list_edit.blockSignals(True)
        self.list_edit.setPlainText(text)
        self.list_edit.blockSignals(False)

    def _get_proxy_str(self, url=""):
        mode = self.settings.get("proxy_mode", "none")
        if mode == "none":
            return None
        proxy_str = None
        if mode == "socks4":
            proxy_str = f"socks4://127.0.0.1:{self.socks_port_spin.value()}"
        elif mode == "socks5":
            proxy_str = f"socks5://127.0.0.1:{self.socks_port_spin.value()}"
        elif mode == "custom":
            proxy_str = self.custom_edit.text().strip() or None
        list_mode = self.settings.get("proxy_list_mode", "none")
        if list_mode == "none":
            return proxy_str
        items = []
        if list_mode == "whitelist":
            items = [i.strip().lower() for i in self.settings.get("proxy_whitelist", "").replace("\n", ",").split(",") if i.strip()]
            use_proxy = any(item in url.lower() for item in items)
            return proxy_str if use_proxy else None
        elif list_mode == "blacklist":
            items = [i.strip().lower() for i in self.settings.get("proxy_blacklist", "").replace("\n", ",").split(",") if i.strip()]
            use_proxy = not any(item in url.lower() for item in items)
            return proxy_str if use_proxy else None
        return proxy_str

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    self.settings.update(json.load(f))
            except Exception:
                pass

    def save_settings(self):
        self.settings["out_dir"] = self.out_dir_edit_right.text().strip()
        self.settings["proxy_port"] = int(self.socks_port_spin.value())
        self.settings["proxy_custom"] = self.custom_edit.text().strip()
        try:
            self.settings["history_limit"] = int(self.history_limit_edit.text())
        except Exception:
            self.settings["history_limit"] = 50
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []
        else:
            self.history = []

    def save_history(self):
        try:
            limit = self.settings.get("history_limit", 50)
            self.history = self.history[-limit:]
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
        self.update_history_ui()

    def update_history_ui(self):
        self.history_list.clear()
        if not self.history:
            self.history_list.addItem("Пусто")
        else:
            for entry in reversed(self.history):
                title = entry.get('title', 'Без названия')
                url = entry.get('url', '')
                self.history_list.addItem(f"{title} — {url}")

    def add_video(self):
        url = self.url_edit.text().strip()
        if not url:
            return
        _, index = self.manager.add_video(url)
        if _ == 0:
            if index in self.cards:
                self.cards[index].highlight_card()
                return
            self.manager.queue[index]['status'] = "queued"
        card = DownloadCard(index, "Получаем информацию...", url, self.manager, self.remove_video, self)
        self.cards[index] = card
        item = QListWidgetItem()
        item.setSizeHint(card.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, card)
        proxy = self._get_proxy_str(url)
        print(proxy)
        self.manager.proxy = proxy
        self.manager.get_info(index)
        self.url_edit.clear()

    def start_all(self):
        self.manager.out_dir = self.out_dir_edit_right.text().strip() or "."
        for idx in list(self.cards.keys()):
            if self.cards.get(idx).btn_start.isEnabled():
                self.cards.get(idx).btn_start.click()

    def stop_all(self):
        for idx in list(self.cards.keys()):
            if self.cards.get(idx).btn_stop.isEnabled():
                self.cards.get(idx).btn_stop.click()

    def remove_video(self, index):
        if index not in self.cards:
            return
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget == self.cards[index]:
                self.list_widget.takeItem(i)
                widget.deleteLater()
                break
        del self.cards[index]
        if 0 <= index < len(self.manager.queue):
            self.manager.queue[index]['status'] = 'removed'

    def on_info_received(self, idx, info):
        title = info.get("title", "Без названия")
        url = info.get("webpage_url", self.manager.queue[idx]["url"])
        self.history.append({"title": title, "url": url})
        self.save_history()

    def on_info_error(self, idx, msg):
        QMessageBox.warning(self, "Info error", f"{idx}: {msg}")