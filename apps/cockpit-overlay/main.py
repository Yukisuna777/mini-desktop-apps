#!/usr/bin/env python3
"""
Cockpit Overlay
---------------
猫の手がコックピット操作パネル（左）と操縦桿（右）を握る透過オーバーレイ。
OBS ウィンドウキャプチャ対応。ドラッグバーはギャップを挟んで上部に分離。
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QRectF, QPointF, QPoint
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush,
    QPainterPath, QRadialGradient, QLinearGradient,
)
from pynput import keyboard as kb, mouse as ms


# ── 入力ブリッジ ──────────────────────────────────────────────────────────────

SPECIAL_KEYS: dict = {
    kb.Key.space:   "SPACE",
    kb.Key.shift:   "SHIFT",
    kb.Key.shift_l: "SHIFT",
    kb.Key.shift_r: "SHIFT",
    kb.Key.ctrl_l:  "CTRL",
    kb.Key.ctrl_r:  "CTRL",
}


class InputBridge(QObject):
    key_pressed  = pyqtSignal(str)
    key_released = pyqtSignal(str)
    mouse_moved  = pyqtSignal(float, float)

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


# ── カラーパレット ────────────────────────────────────────────────────────────

CAT_BASE  = QColor(0xD8, 0xC8, 0xB8)
CAT_DARK  = QColor(0xB8, 0xA0, 0x7A)
CAT_PAD   = QColor(0xE8, 0xB0, 0xA8)

PANEL_TOP  = QColor(0x2A, 0x30, 0x50)
PANEL_BOT  = QColor(0x12, 0x18, 0x2A)
PANEL_EDGE = QColor(0x45, 0x5A, 0x85)

STICK_BODY   = QColor(0x30, 0x30, 0x40)
STICK_HLIGHT = QColor(0x58, 0x5A, 0x6C)
STICK_BASE_C = QColor(0x1A, 0x1A, 0x28)
STICK_CAP    = QColor(0x50, 0x52, 0x62)

BTN_RED     = QColor(0xCC, 0x22, 0x22)
BTN_RED_G   = QColor(0xFF, 0x55, 0x55)
BTN_GREEN   = QColor(0x00, 0xCC, 0xAA)
BTN_GREEN_G = QColor(0x00, 0xFF, 0xCC)
BTN_BLUE    = QColor(0x22, 0x44, 0xCC)
BTN_BLUE_G  = QColor(0x55, 0x88, 0xFF)

RED_KEYS   = {"SPACE"}
GREEN_KEYS = {"E", "R", "F", "SHIFT"}
BLUE_KEYS  = {"Q", "W", "A", "S", "D", "Z", "X", "C", "V"}


# ── コックピットキャンバス ────────────────────────────────────────────────────

class CockpitCanvas(QWidget):
    W = 760
    H = 300

    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.W, self.H)
        self._active: set[str] = set()
        self._mx = 0.0
        self._my = 0.0

    def press(self, name: str) -> None:
        self._active.add(name)
        self.update()

    def release(self, name: str) -> None:
        self._active.discard(name)
        self.update()

    def update_mouse(self, nx: float, ny: float) -> None:
        self._mx = nx
        self._my = ny
        self.update()

    # ── paintEvent ───────────────────────────────────────────────────────────

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_left(p)
        self._draw_right(p)

    # ── 左側: コントロールパネル ──────────────────────────────────────────────

    def _draw_left(self, p: QPainter) -> None:
        pcx = self.W * 0.235   # ≈ 179
        pcy = self.H * 0.40    # ≈ 120

        # 指（パネルの後ろに描く）
        self._draw_cat_fingers_left(p, pcx, pcy)

        # パネル本体
        pw, ph = 225, 132
        p.save()
        p.translate(pcx, pcy)
        p.rotate(-17)

        panel = QPainterPath()
        panel.addRoundedRect(QRectF(-pw/2, -ph/2, pw, ph), 14, 14)

        grad = QLinearGradient(0, -ph/2, 0, ph/2)
        grad.setColorAt(0, PANEL_TOP)
        grad.setColorAt(1, PANEL_BOT)
        p.fillPath(panel, QBrush(grad))
        p.setPen(QPen(PANEL_EDGE, 2))
        p.drawPath(panel)

        # 上端ハイライト
        p.setPen(QPen(QColor(0x65, 0x85, 0xB8, 110), 1))
        p.drawLine(int(-pw/2 + 14), int(-ph/2 + 2), int(pw/2 - 14), int(-ph/2 + 2))

        # ボタン配置
        red_on   = bool(self._active & RED_KEYS)
        green_on = bool(self._active & GREEN_KEYS)
        blue_on  = bool(self._active & BLUE_KEYS)

        self._draw_dome_button(p,  55,  12, 20, BTN_RED,   BTN_RED_G,   red_on)
        self._draw_dome_button(p, -15,  12, 20, BTN_GREEN, BTN_GREEN_G, green_on)

        for i, (bx, by) in enumerate([(-80, -22), (-80, 4), (-80, 30), (-80, 56)]):
            self._draw_small_button(p, bx, by, 8,
                                    BTN_BLUE, BTN_BLUE_G, blue_on and i < 2)

        p.restore()

    def _draw_cat_fingers_left(self, p: QPainter, pcx: float, pcy: float) -> None:
        # 人差し指〜薬指（パネル手前を包む）
        for fx, fy, fw, fh, fa in [
            (pcx - 80, pcy + 108, 31, 90, -14),
            (pcx - 38, pcy + 116, 33, 96,  -5),
            (pcx +  8, pcy + 116, 33, 94,   3),
            (pcx + 52, pcy + 108, 30, 86,  12),
        ]:
            self._draw_finger(p, fx, fy, fw, fh, fa)

        # 親指（左下から見える）
        self._draw_finger(p, pcx - 112, pcy + 38, 28, 62, -52)

    # ── 右側: 操縦桿 ─────────────────────────────────────────────────────────

    def _draw_right(self, p: QPainter) -> None:
        scx = self.W * 0.795   # ≈ 605
        scy = self.H * 0.38    # ≈ 114

        # 指（桿の後ろに描く）
        self._draw_cat_fingers_right(p, scx, scy)

        # 操縦桿（マウスX軸で傾く）
        tilt = self._mx * 12
        p.save()
        p.translate(scx, scy)
        p.rotate(tilt + 6)
        self._draw_joystick(p)
        p.restore()

    def _draw_joystick(self, p: QPainter) -> None:
        # ── ベース台形 ───────────────────────────────────────────────────────
        bw_top, bw_bot, bh = 65, 88, 32
        base = QPainterPath()
        base.moveTo(-bw_bot / 2, bh)
        base.lineTo( bw_bot / 2, bh)
        base.lineTo( bw_top / 2, 0)
        base.lineTo(-bw_top / 2, 0)
        base.closeSubpath()
        bg = QLinearGradient(-bw_bot/2, 0, bw_bot/2, 0)
        bg.setColorAt(0,   STICK_BASE_C.darker(130))
        bg.setColorAt(0.5, STICK_BASE_C.lighter(115))
        bg.setColorAt(1,   STICK_BASE_C.darker(130))
        p.setPen(QPen(QColor(0x0E, 0x0E, 0x1A), 1.5))
        p.setBrush(QBrush(bg))
        p.drawPath(base)

        # ── グリップ ─────────────────────────────────────────────────────────
        gw, gh = 58, 112
        grip = QPainterPath()
        grip.addRoundedRect(QRectF(-gw/2, -gh, gw, gh), 17, 17)
        gg = QLinearGradient(-gw/2, 0, gw/2, 0)
        gg.setColorAt(0,   STICK_BODY.darker(135))
        gg.setColorAt(0.3, STICK_HLIGHT)
        gg.setColorAt(0.7, STICK_BODY)
        gg.setColorAt(1,   STICK_BODY.darker(140))
        p.setPen(QPen(QColor(0x16, 0x16, 0x22), 1.5))
        p.setBrush(QBrush(gg))
        p.drawPath(grip)

        # グリップのリブ線
        p.setPen(QPen(QColor(0x1A, 0x1A, 0x2C, 120), 1))
        for y in range(int(-gh * 0.88), -8, 14):
            p.drawLine(int(-gw/2 + 10), y, int(gw/2 - 10), y)

        # トリガーボタン（側面）
        trig_on = bool(self._active & RED_KEYS)
        self._draw_small_button(p, int(gw/2) + 1, int(-gh * 0.58), 9,
                                BTN_RED, BTN_RED_G, trig_on)

        # ── トップキャップ ───────────────────────────────────────────────────
        cap_w, cap_h = 52, 22
        cap = QPainterPath()
        cap.addEllipse(QRectF(-cap_w/2, -gh - cap_h/2, cap_w, cap_h))
        cg = QLinearGradient(0, -gh - cap_h, 0, -gh)
        cg.setColorAt(0, STICK_CAP.lighter(135))
        cg.setColorAt(1, STICK_CAP.darker(110))
        p.setPen(QPen(QColor(0x28, 0x28, 0x38), 1.5))
        p.setBrush(QBrush(cg))
        p.drawPath(cap)

        # キャップハイライト
        hl = QRadialGradient(0, -gh - cap_h * 0.3, cap_w * 0.36)
        hl.setColorAt(0, QColor(255, 255, 255, 105))
        hl.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(hl))
        p.drawEllipse(QPointF(0, -gh - cap_h * 0.3), cap_w * 0.36, cap_h * 0.32)

    def _draw_cat_fingers_right(self, p: QPainter, scx: float, scy: float) -> None:
        # 人差し指〜薬指（グリップを包む）
        for fx, fy, fw, fh, fa in [
            (scx - 45, scy + 104, 30, 88,  -9),
            (scx - 14, scy + 112, 32, 94,  -2),
            (scx + 18, scy + 110, 32, 92,   5),
            (scx + 48, scy + 102, 29, 82,  13),
        ]:
            self._draw_finger(p, fx, fy, fw, fh, fa)

        # 人差し指（トリガー方向に伸びる）
        self._draw_finger(p, scx + 62, scy + 14, 25, 68, 62)

        # 親指（キャップ付近）
        self._draw_finger(p, scx - 22, scy - 76, 26, 54, -22)

    # ── 指プリミティブ ────────────────────────────────────────────────────────

    def _draw_finger(self, p: QPainter, cx: float, cy: float,
                     fw: float, fh: float, angle: float) -> None:
        p.save()
        p.translate(cx, cy)
        p.rotate(angle)

        # 影
        shadow = QPainterPath()
        shadow.addRoundedRect(QRectF(-fw/2 + 3, -fh/2 + 5, fw, fh), fw*0.42, fw*0.42)
        p.fillPath(shadow, QColor(0, 0, 0, 48))

        # 指本体
        body = QPainterPath()
        body.addRoundedRect(QRectF(-fw/2, -fh/2, fw, fh), fw*0.43, fw*0.43)

        bg = QLinearGradient(-fw/2, 0, fw/2, 0)
        bg.setColorAt(0,    CAT_DARK)
        bg.setColorAt(0.32, CAT_BASE)
        bg.setColorAt(0.65, CAT_BASE.lighter(108))
        bg.setColorAt(1,    CAT_DARK)
        p.setPen(QPen(CAT_DARK.darker(118), 1))
        p.setBrush(QBrush(bg))
        p.drawPath(body)

        # 関節ライン
        p.setPen(QPen(CAT_DARK.darker(110), 0.8))
        for yo in (-fh * 0.10, fh * 0.13):
            p.drawLine(int(-fw * 0.30), int(yo), int(fw * 0.30), int(yo))

        # 肉球パッド
        pr = fw * 0.37
        pad = QPainterPath()
        pad.addEllipse(QPointF(0, fh * 0.33), pr, pr * 0.84)
        p.fillPath(pad, QColor(CAT_PAD.red(), CAT_PAD.green(), CAT_PAD.blue(), 185))
        p.setPen(QPen(CAT_DARK, 0.5))
        p.drawPath(pad)

        p.restore()

    # ── ボタン描画 ────────────────────────────────────────────────────────────

    def _draw_dome_button(self, p: QPainter, x: float, y: float, r: float,
                          color: QColor, glow: QColor, active: bool) -> None:
        if active:
            halo = QRadialGradient(x, y, r * 3.0)
            halo.setColorAt(0, QColor(glow.red(), glow.green(), glow.blue(), 155))
            halo.setColorAt(1, QColor(glow.red(), glow.green(), glow.blue(), 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(halo))
            p.drawEllipse(QPointF(x, y), r * 3.0, r * 3.0)

        c = glow if active else color
        body = QRadialGradient(x - r*0.22, y - r*0.22, r * 1.35)
        body.setColorAt(0,   c.lighter(140))
        body.setColorAt(0.5, c)
        body.setColorAt(1,   c.darker(155))
        p.setPen(QPen(c.darker(185), 1.5))
        p.setBrush(QBrush(body))
        p.drawEllipse(QPointF(x, y), r, r)

        # ドームハイライト
        hl = QRadialGradient(x - r*0.28, y - r*0.38, r * 0.52)
        hl.setColorAt(0, QColor(255, 255, 255, 115))
        hl.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(hl))
        p.drawEllipse(QPointF(x - r*0.10, y - r*0.18), r*0.54, r*0.44)

    def _draw_small_button(self, p: QPainter, x: float, y: float, r: float,
                           color: QColor, glow: QColor, active: bool) -> None:
        c = glow if active else color
        body = QRadialGradient(x - r*0.3, y - r*0.3, r * 1.2)
        body.setColorAt(0, c.lighter(130))
        body.setColorAt(1, c.darker(145))
        p.setPen(QPen(c.darker(165), 1))
        p.setBrush(QBrush(body))
        p.drawEllipse(QPointF(x, y), r, r)


# ── ドラッグハンドル ──────────────────────────────────────────────────────────

class CloseButton(QWidget):
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
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.C_HOVER if self._hovered else self.C_NORMAL)
        p.drawEllipse(self.rect())
        m = 5
        s = self.SIZE
        p.setPen(QPen(QColor(255, 255, 255, 220), 1.8))
        p.drawLine(m, m, s - m, s - m)
        p.drawLine(s - m, m, m, s - m)


class DragHandle(QWidget):
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
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.C_GRIP)
        cy = self.HEIGHT // 2
        for dx in (-8, 0, 8):
            p.drawEllipse(QPointF(self.width() // 2 + dx, cy), 2.5, 2.5)


# ── 透明ギャップ ──────────────────────────────────────────────────────────────

class TransparentGap(QWidget):
    def __init__(self, height: int) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedHeight(height)

    def paintEvent(self, _) -> None:
        pass


# ── メインウィンドウ ──────────────────────────────────────────────────────────

class CockpitOverlay(QWidget):
    GAP_H = 28   # ドラッグバーとキャンバスの間隔 (OBSクロップ用)

    def __init__(self, bridge: InputBridge) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("CockpitOverlay")

        self._bridge  = bridge
        self._canvas  = CockpitCanvas()
        self._handle  = DragHandle(self, on_close=self._quit)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._handle)
        root.addWidget(TransparentGap(self.GAP_H))
        root.addWidget(self._canvas)

        bridge.key_pressed.connect(self._canvas.press)
        bridge.key_released.connect(self._canvas.release)
        bridge.mouse_moved.connect(self._canvas.update_mouse)

        self._snap_to_bottom()

    def _snap_to_bottom(self) -> None:
        screen = QApplication.primaryScreen().geometry()
        self.adjustSize()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 40
        self.move(x, y)

    def _quit(self) -> None:
        self._bridge.stop()
        QApplication.quit()

    def paintEvent(self, _) -> None:
        pass


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
