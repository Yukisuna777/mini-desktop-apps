#!/usr/bin/env python3
"""
Cockpit Overlay
---------------
画面下部に透過表示されるコックピット風オーバーレイ。
  左パネル : キー入力（Q/W/E/R, A/S/D/F, Z/X/C/V, Space）に反応するボタン群
  右パネル : マウス移動に連動する操縦レバー（ジョイスティック表示）

OBS のウィンドウキャプチャで配信オーバーレイとして使用可能。
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QRectF, QPointF, QPoint
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QPainterPath, QRadialGradient,
)
from pynput import keyboard as kb, mouse as ms


# ── キーレイアウト ────────────────────────────────────────────────────────────

KEY_ROWS = [
    ["Q", "W", "E", "R"],
    ["A", "S", "D", "F"],
    ["Z", "X", "C", "V"],
    ["", "SPACE", "", ""],
]

# pynput の特殊キー → 表示名
SPECIAL_KEYS: dict = {
    kb.Key.space:   "SPACE",
    kb.Key.shift:   "SHIFT",
    kb.Key.shift_l: "SHIFT",
    kb.Key.shift_r: "SHIFT",
    kb.Key.ctrl_l:  "CTRL",
    kb.Key.ctrl_r:  "CTRL",
}


# ── pynput → Qt シグナルブリッジ ──────────────────────────────────────────────

class InputBridge(QObject):
    key_pressed  = pyqtSignal(str)
    key_released = pyqtSignal(str)
    mouse_moved  = pyqtSignal(float, float)   # 正規化済み –1.0 … +1.0

    def __init__(self, screen_w: int, screen_h: int) -> None:
        super().__init__()
        self._cx = screen_w / 2
        self._cy = screen_h / 2
        self._hw = screen_w / 2
        self._hh = screen_h / 2

    def _key_name(self, key) -> str | None:
        if key in SPECIAL_KEYS:
            return SPECIAL_KEYS[key]
        try:
            ch = key.char
            return ch.upper() if ch else None
        except AttributeError:
            return None

    def start(self) -> None:
        def on_press(key):
            name = self._key_name(key)
            if name:
                self.key_pressed.emit(name)

        def on_release(key):
            name = self._key_name(key)
            if name:
                self.key_released.emit(name)

        def on_move(x, y):
            nx = max(-1.0, min(1.0, (x - self._cx) / self._hw))
            ny = max(-1.0, min(1.0, (y - self._cy) / self._hh))
            self.mouse_moved.emit(nx, ny)

        self._kb = kb.Listener(on_press=on_press, on_release=on_release)
        self._ms = ms.Listener(on_move=on_move)
        self._kb.daemon = True
        self._ms.daemon = True
        self._kb.start()
        self._ms.start()

    def stop(self) -> None:
        self._kb.stop()
        self._ms.stop()


# ── 左パネル：キーボード ──────────────────────────────────────────────────────

class KeyPanel(QWidget):
    KEY_W = 52
    KEY_H = 44
    GAP   = 6
    PAD   = 14

    C_BG      = QColor(18, 20, 30, 210)
    C_KEY_OFF = QColor(42, 48, 64, 230)
    C_KEY_ON  = QColor(70, 190, 255, 245)
    C_BORDER  = QColor(90, 110, 150, 180)
    C_TEXT    = QColor(200, 220, 255, 255)
    C_TEXT_ON = QColor(10,  20,  40, 255)

    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._active: set[str] = set()
        cols = max(len(r) for r in KEY_ROWS)
        w = self.PAD * 2 + cols * (self.KEY_W + self.GAP) - self.GAP
        h = self.PAD * 2 + len(KEY_ROWS) * (self.KEY_H + self.GAP) - self.GAP
        self.setFixedSize(w, h)

    def press(self, name: str) -> None:
        self._active.add(name)
        self.update()

    def release(self, name: str) -> None:
        self._active.discard(name)
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # パネル背景
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(self.rect()), 12, 12)
        p.fillPath(bg_path, self.C_BG)
        p.setPen(QPen(self.C_BORDER, 1.5))
        p.drawPath(bg_path)

        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))

        for row_i, row in enumerate(KEY_ROWS):
            for col_i, key in enumerate(row):
                if not key:
                    continue
                is_space = key == "SPACE"
                kw = self.KEY_W * 2 + self.GAP if is_space else self.KEY_W
                x  = self.PAD + col_i * (self.KEY_W + self.GAP)
                y  = self.PAD + row_i * (self.KEY_H + self.GAP)
                on = key in self._active

                kpath = QPainterPath()
                kpath.addRoundedRect(QRectF(x, y, kw, self.KEY_H), 6, 6)

                if on:
                    grad = QRadialGradient(x + kw / 2, y + self.KEY_H / 2, kw * 0.7)
                    grad.setColorAt(0, QColor(130, 225, 255, 255))
                    grad.setColorAt(1, QColor(60,  180, 255, 200))
                    p.fillPath(kpath, QBrush(grad))
                    p.setPen(QPen(QColor(180, 240, 255), 1.5))
                else:
                    p.fillPath(kpath, self.C_KEY_OFF)
                    p.setPen(QPen(self.C_BORDER, 1))

                p.drawPath(kpath)
                p.setPen(self.C_TEXT_ON if on else self.C_TEXT)
                p.drawText(QRectF(x, y, kw, self.KEY_H),
                           Qt.AlignmentFlag.AlignCenter, key)


# ── 右パネル：マウスジョイスティック ─────────────────────────────────────────

class JoystickPanel(QWidget):
    SIZE = 190

    C_BG     = QColor(18, 20, 30, 210)
    C_BORDER = QColor(90, 110, 150, 180)
    C_RING   = QColor(55, 65, 85, 220)
    C_AXIS   = QColor(55, 75,  95, 150)
    C_STICK  = QColor(70, 190, 255, 200)
    C_BASE   = QColor(50, 65,  90, 210)
    C_DOT    = QColor(255, 255, 255, 250)

    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._nx = 0.0
        self._ny = 0.0
        self.setFixedSize(self.SIZE, self.SIZE)

    def update_pos(self, nx: float, ny: float) -> None:
        self._nx = nx
        self._ny = ny
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy   = self.SIZE / 2, self.SIZE / 2
        r_outer  = (self.SIZE - 24) / 2
        r_base   = r_outer * 0.28

        # パネル背景
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(self.rect()), 12, 12)
        p.fillPath(bg_path, self.C_BG)
        p.setPen(QPen(self.C_BORDER, 1.5))
        p.drawPath(bg_path)

        # 外枠リング
        p.setPen(QPen(self.C_RING, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r_outer, r_outer)

        # 軸線
        p.setPen(QPen(self.C_AXIS, 1))
        p.drawLine(int(cx - r_outer), int(cy), int(cx + r_outer), int(cy))
        p.drawLine(int(cx), int(cy - r_outer), int(cx), int(cy + r_outer))

        # スティック先端位置（円内にクランプ）
        dx = self._nx * r_outer
        dy = self._ny * r_outer
        dist = (dx ** 2 + dy ** 2) ** 0.5
        if dist > r_outer:
            dx = dx / dist * r_outer
            dy = dy / dist * r_outer

        # スティック棒
        p.setPen(QPen(self.C_STICK, 3))
        p.drawLine(int(cx), int(cy), int(cx + dx), int(cy + dy))

        # 中心ベース
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.C_BASE)
        p.drawEllipse(QPointF(cx, cy), r_base, r_base)

        # 先端グロー
        glow = QRadialGradient(cx + dx, cy + dy, 18)
        glow.setColorAt(0, QColor(150, 225, 255, 230))
        glow.setColorAt(1, QColor(70, 190, 255, 0))
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(cx + dx, cy + dy), 16, 16)

        # 先端ドット
        p.setBrush(self.C_DOT)
        p.drawEllipse(QPointF(cx + dx, cy + dy), 6, 6)

        # 座標テキスト
        p.setFont(QFont("Consolas", 8))
        p.setPen(QColor(110, 150, 195, 200))
        p.drawText(QRectF(0, self.SIZE - 22, self.SIZE, 18),
                   Qt.AlignmentFlag.AlignCenter,
                   f"X:{self._nx:+.2f}  Y:{self._ny:+.2f}")


# ── ドラッグハンドル ──────────────────────────────────────────────────────────

class CloseButton(QWidget):
    """×ボタン。クリックでアプリを終了する。"""

    SIZE = 18
    C_NORMAL = QColor(180, 60, 60, 200)
    C_HOVER  = QColor(230, 80, 80, 240)

    def __init__(self, on_click) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._on_click = on_click
        self._hovered = False

    def enterEvent(self, _) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, _) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._on_click()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.C_HOVER if self._hovered else self.C_NORMAL
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(self.rect())
        p.setPen(QPen(QColor(255, 255, 255, 220), 1.8))
        m = 5
        s = self.SIZE
        p.drawLine(m, m, s - m, s - m)
        p.drawLine(s - m, m, m, s - m)


class DragHandle(QWidget):
    """ウィンドウ上部のドラッグ可能なバー。つかんで移動、×で終了。"""

    HEIGHT = 22
    C_BG     = QColor(28, 32, 45, 200)
    C_BORDER = QColor(90, 110, 150, 160)
    C_GRIP   = QColor(100, 130, 170, 180)

    def __init__(self, target: QWidget, on_close) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._target = target
        self._drag_pos: QPoint | None = None
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        self._close_btn = CloseButton(on_close)
        self._close_btn.setParent(self)

    def resizeEvent(self, _) -> None:
        m = (self.HEIGHT - CloseButton.SIZE) // 2
        self._close_btn.move(self.width() - CloseButton.SIZE - m, m)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self._target.frameGeometry().topLeft()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self._target.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e) -> None:
        self._drag_pos = None

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景バー（上角だけ丸める）
        path = QPainterPath()
        r = QRectF(self.rect())
        path.moveTo(r.left() + 8, r.top())
        path.arcTo(QRectF(r.left(), r.top(), 16, 16), 90, 90)
        path.lineTo(r.left(), r.bottom())
        path.lineTo(r.right(), r.bottom())
        path.arcTo(QRectF(r.right() - 16, r.top(), 16, 16), 0, 90)
        path.closeSubpath()
        p.fillPath(path, self.C_BG)
        p.setPen(QPen(self.C_BORDER, 1))
        p.drawPath(path)

        # グリップドット（中央に3つ）
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.C_GRIP)
        cy = self.HEIGHT // 2
        for dx in (-8, 0, 8):
            cx = self.width() // 2 + dx
            p.drawEllipse(QPointF(cx, cy), 2.5, 2.5)


# ── メインウィンドウ ──────────────────────────────────────────────────────────

class CockpitOverlay(QWidget):
    def __init__(self, bridge: InputBridge) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("CockpitOverlay")

        self._bridge = bridge
        self._key_panel = KeyPanel()
        self._joy_panel = JoystickPanel()
        self._drag_handle = DragHandle(self, on_close=self._quit)

        panels = QHBoxLayout()
        panels.setContentsMargins(24, 0, 24, 12)
        panels.setSpacing(36)
        panels.addWidget(self._key_panel)
        panels.addWidget(self._joy_panel)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._drag_handle)
        root.addLayout(panels)

        bridge.key_pressed.connect(self._key_panel.press)
        bridge.key_released.connect(self._key_panel.release)
        bridge.mouse_moved.connect(self._joy_panel.update_pos)

        self._snap_to_bottom()

    def _quit(self) -> None:
        self._bridge.stop()
        QApplication.quit()

    def _snap_to_bottom(self) -> None:
        screen = QApplication.primaryScreen().geometry()
        self.adjustSize()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 48
        self.move(x, y)

    def paintEvent(self, _) -> None:
        pass   # 子ウィジェットが個別に描画するため何もしない


# ── エントリポイント ──────────────────────────────────────────────────────────

def main() -> None:
    app = QApplication(sys.argv)
    screen = app.primaryScreen().geometry()

    bridge = InputBridge(screen.width(), screen.height())
    bridge.start()

    overlay = CockpitOverlay(bridge)
    overlay.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
