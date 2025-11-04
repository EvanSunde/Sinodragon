from typing import Dict

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QTextEdit, QColorDialog
from PyQt5.QtGui import QColor

from core.app_profiles import AppProfilesStore, AppProfile


class AppProfilesDialog(QDialog):
    def __init__(self, parent, store: AppProfilesStore):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("Manage App Profiles")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        for app in self.store.list_apps():
            self.list_widget.addItem(app)
        self.list_widget.currentTextChanged.connect(self._load_selected)
        layout.addWidget(self.list_widget)

        form = QVBoxLayout()
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("App Name:"))
        self.name_edit = QLineEdit()
        row1.addWidget(self.name_edit)
        self.color_btn = QPushButton("Pick Color")
        self.color_btn.clicked.connect(self._pick_color)
        row1.addWidget(self.color_btn)
        form.addLayout(row1)

        form.addWidget(QLabel("Default Keys (space-separated):"))
        self.defaults_edit = QLineEdit()
        form.addWidget(self.defaults_edit)

        form.addWidget(QLabel("Combos (one per line: Modifier+...: Space Separated Keys)"))
        self.combos_edit = QTextEdit()
        form.addWidget(self.combos_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self._new)
        btns.addWidget(new_btn)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete)
        btns.addWidget(del_btn)
        layout.addLayout(btns)

        self._color = (255, 165, 0)

    def _load_selected(self, name: str) -> None:
        if not name:
            return
        p = self.store.load(name)
        if not p:
            return
        self.name_edit.setText(p.name)
        self._color = p.color
        self.defaults_edit.setText(" ".join(p.default_keys))
        # combos display
        lines = []
        for mod, keys in p.combos.items():
            lines.append(f"{mod}: {' '.join(keys)}")
        self.combos_edit.setPlainText("\n".join(lines))

    def _pick_color(self) -> None:
        q = QColor(*self._color)
        c = QColorDialog.getColor(q, self, "Select Profile Color")
        if c.isValid():
            self._color = (c.red(), c.green(), c.blue())

    def _save(self) -> None:
        name = self.name_edit.text().strip() or "Unknown"
        defaults = [k.strip() for k in self.defaults_edit.text().split() if k.strip()]
        combos = {}
        for line in self.combos_edit.toPlainText().splitlines():
            if ":" in line:
                left, right = line.split(":", 1)
                mod = left.strip()
                keys = [k.strip() for k in right.strip().split() if k.strip()]
                if mod:
                    combos[mod] = keys
        p = AppProfile(name, self._color, defaults, combos)
        self.store.save(p)
        if name not in [self.list_widget.item(i).text() for i in range(self.list_widget.count())]:
            self.list_widget.addItem(name)

    def _new(self) -> None:
        self.name_edit.clear()
        self.defaults_edit.clear()
        self.combos_edit.clear()
        self._color = (255, 165, 0)

    def _delete(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            return
        if self.store.delete(name):
            # remove from list
            items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
            self.list_widget.clear()
            for app in self.store.list_apps():
                self.list_widget.addItem(app)
            self._new()


