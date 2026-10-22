"""清影 2.5：内置 CUNet 原尺寸降噪的圆角玻璃工作台。"""
import json
import os
import sys
import tempfile
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from PySide6.QtCore import Qt, Signal, QObject, QPoint, QPointF, QRectF, QTimer, QVariantAnimation, QEasingCurve, QEventLoop
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QLinearGradient, QFont, QBrush, QImage, QIcon
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QToolButton, QScrollArea, QSlider, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox, QProgressBar, QSizePolicy, QComboBox, QDialog, QFrame)
from engine import MODES, NEURAL_MODE, load_image, denoise, save_image, writable_folder, default_output, cancel_processing, CUGAN_MODE, REHAB_MODE, supported_scales, strength_range, strength_label, validate_settings

IMAGE_FILTER = '图片 (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)'
STYLE = '''
QWidget { font-family: "Microsoft YaHei UI"; font-size: 14px; color: #29364c; background: transparent; }
QLabel#muted { color: #738198; font-size: 12px; }
QLabel#title { font-size: 23px; font-weight: 700; color: #203757; }
QLabel#brand { font-size: 21px; font-weight: 700; color: #254c79; }
QLabel#badge { background: rgba(222,238,255,210); color: #3570a9; border: 1px solid rgba(255,255,255,180); border-radius: 12px; padding: 5px 12px; font-size: 12px; }
QPushButton { background: rgba(255,255,255,165); border: 1px solid rgba(255,255,255,220); border-radius: 11px; padding: 10px 13px; }
QPushButton:hover { background: rgba(231,242,255,220); border-color: #9ac1ea; }
QPushButton:pressed { background: #d9eafa; }
QPushButton:disabled { color: #a1aebe; background: rgba(239,243,249,150); border-color: rgba(255,255,255,100); }
QPushButton#primary { background: #427cb8; color: white; border: 1px solid #6499ce; font-weight: 600; }
QPushButton#primary:hover { background: #528cc8; }
QPushButton#primary:disabled { background: #b4c9de; border-color: #c5d6e7; color: #f8fbff; }
QToolButton { border: none; border-radius: 9px; background: transparent; padding: 8px; }
QToolButton:hover { background: rgba(221,236,253,180); }
QToolButton#sectionHeader { font-size: 14px; font-weight: 600; text-align: left; padding: 12px 10px; }
QRadioButton { spacing: 9px; padding: 4px 0; }
QRadioButton::indicator { width: 16px; height: 16px; border-radius: 9px; border: 1px solid #afc2d6; background: rgba(255,255,255,200); }
QRadioButton::indicator:checked { background: #5089c0; border: 4px solid #e5f0fb; }
QSlider::groove:horizontal { height: 5px; background: rgba(181,202,226,120); border-radius: 2px; }
QSlider::sub-page:horizontal { background: #6d9ccc; border-radius: 2px; }
QSlider::handle:horizontal { width: 16px; height: 16px; margin: -6px 0; background: white; border: 2px solid #6d9ccc; border-radius: 9px; }
QSlider:disabled { opacity: .5; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { width: 6px; background: transparent; margin: 4px 0; }
QScrollBar::handle:vertical { background: rgba(104,132,162,65); border-radius: 3px; min-height: 26px; }
QScrollBar::handle:vertical:hover { background: rgba(104,132,162,130); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QProgressBar { border: none; background: rgba(184,205,228,90); border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: #6095c9; border-radius: 3px; }
QToolTip { color: #29364c; background: #f5f9fe; border: 1px solid #ccdced; padding: 5px; }
'''


def label(text, muted=False):
    widget = QLabel(text)
    widget.setWordWrap(True)
    if muted:
        widget.setObjectName('muted')
    return widget


def pixmap(image):
    rgba = image.convert('RGBA')
    data = rgba.tobytes()
    qimage = QImage(data, rgba.width, rgba.height, rgba.width*4, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimage)


class GlassPanel(QWidget):
    """从窗口缓存的高斯模糊背景取样，再叠加半透明玻璃与高光。"""
    def __init__(self, parent=None, radius=20, tint=0.74):
        super().__init__(parent)
        self.radius, self.tint = radius, tint
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        shape = QPainterPath()
        shape.addRoundedRect(rect, self.radius, self.radius)
        p.setClipPath(shape)
        window = self.window()
        background = getattr(window, 'blurred_background', None)
        if background is not None and not background.isNull():
            origin = self.mapTo(window, QPoint(0, 0))
            p.drawPixmap(-origin.x(), -origin.y(), background)
        tint = QColor('#f8fbff')
        tint.setAlphaF(min(.97, max(.1, self.tint * getattr(window, 'glass_opacity', .8))))
        p.fillPath(shape, tint)
        sheen = QLinearGradient(0, 0, 0, self.height())
        sheen.setColorAt(0, QColor(255, 255, 255, 75))
        sheen.setColorAt(1, QColor(255, 255, 255, 3))
        p.fillPath(shape, sheen)
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 195), 1))
        p.drawPath(shape)
        p.setPen(QPen(QColor(121, 151, 186, 32), 1))
        p.drawRoundedRect(rect.adjusted(.8, .8, -.8, -.8), self.radius-1, self.radius-1)


class FoldCard(GlassPanel):
    def __init__(self, title, expanded=True):
        super().__init__(radius=16, tint=.9)
        self.expanded = expanded
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 3, 8, 6)
        outer.setSpacing(0)
        self.header = QToolButton()
        self.header.setObjectName('sectionHeader')
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setChecked(expanded)
        self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.header.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.setToolTip('点击标题展开或收起')
        outer.addWidget(self.header)
        self.body = QWidget()
        self.content = QVBoxLayout(self.body)
        self.content.setContentsMargins(10, 3, 10, 12)
        self.content.setSpacing(10)
        outer.addWidget(self.body)
        self.body.setVisible(expanded)
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(170)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(lambda value: self.body.setMaximumHeight(int(value)))
        self.animation.finished.connect(self._settle)
        self.header.toggled.connect(self.set_expanded)

    def set_expanded(self, expanded, animate=True):
        self.animation.stop()
        current = self.body.height() if self.body.isVisible() else 0
        self.expanded = bool(expanded)
        self.header.blockSignals(True)
        self.header.setChecked(self.expanded)
        self.header.blockSignals(False)
        self.header.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        if not animate:
            self._settle()
            return
        target = self.content.sizeHint().height() if expanded else 0
        self.body.setMaximumHeight(current)
        self.body.show()
        self.animation.setStartValue(current)
        self.animation.setEndValue(target)
        self.animation.start()

    def _settle(self):
        self.body.setVisible(self.expanded)
        self.body.setMaximumHeight(16777215 if self.expanded else 0)


class Comparison(QWidget):
    open_requested = Signal()
    file_dropped = Signal(str)
    zoom_changed = Signal(str)
    def __init__(self):
        super().__init__()
        self.original = self.result = None
        self.zoom = None
        self.offset = QPointF()
        self.split = .5
        self.view = 'original'
        self.drag = None
        self.last_pos = QPointF()
        self.setMinimumSize(240, 200)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        tile = QPixmap(24,24)
        tile.fill(QColor('#f4f5f7'))
        p=QPainter(tile)
        p.fillRect(0,0,12,12,QColor('#e5e8ed'))
        p.fillRect(12,12,12,12,QColor('#e5e8ed'))
        p.end()
        self.checker=QBrush(tile)

    def set_images(self, original, result=None):
        self.original = pixmap(original) if original is not None else None
        self.result = pixmap(result) if result is not None else None
        self.view = 'compare' if result is not None else 'original'
        self.fit()

    def shown(self):
        return self.result if self.result is not None else self.original

    def current_scale(self):
        shown=self.shown()
        if shown is None:return 1.
        return self.zoom if self.zoom is not None else min((self.width()-40)/shown.width(),(self.height()-40)/shown.height(),1./self.devicePixelRatioF())

    def image_rect(self):
        shown=self.shown()
        if shown is None:return QRectF()
        scale=self.current_scale()
        w,h=shown.width()*scale,shown.height()*scale
        return QRectF((self.width()-w)/2+self.offset.x(),(self.height()-h)/2+self.offset.y(),w,h)

    def report_zoom(self):
        self.zoom_changed.emit(f'{self.current_scale()*self.devicePixelRatioF()*100:.0f}%' if self.original is not None else '—')

    def fit(self):
        self.zoom=None
        self.offset=QPointF()
        self.report_zoom()
        self.update()

    def actual_size(self):
        if self.original is None:return
        self.zoom=1./self.devicePixelRatioF()
        self.offset=QPointF()
        self.report_zoom()
        self.update()

    def set_view(self,view):
        self.view=view
        self.update()

    def clamp_offset(self):
        shown=self.shown()
        if shown is None:return
        scale=self.current_scale()
        dx=max(0,(shown.width()*scale-self.width())/2+40)
        dy=max(0,(shown.height()*scale-self.height())/2+40)
        self.offset=QPointF(max(-dx,min(dx,self.offset.x())),max(-dy,min(dy,self.offset.y())))

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        shape=QPainterPath()
        shape.addRoundedRect(QRectF(self.rect()),12,12)
        p.setClipPath(shape)
        p.fillRect(self.rect(),QColor('#e9eef4'))
        if self.original is None:
            center=QPointF(self.width()/2,self.height()/2-50)
            p.setPen(QPen(QColor('#7999bb'),2))
            p.setBrush(QColor('#f7faff'))
            p.drawRoundedRect(QRectF(center.x()-30,center.y()-30,60,60),16,16)
            p.drawLine(center+QPointF(-12,0),center+QPointF(12,0))
            p.drawLine(center+QPointF(0,-12),center+QPointF(0,12))
            p.setPen(QColor('#314b68'))
            p.setFont(QFont('Microsoft YaHei UI',16))
            p.drawText(QRectF(0,center.y()+52,self.width(),32),Qt.AlignmentFlag.AlignCenter,'点击打开图片，或拖放到这里')
            p.setPen(QColor('#6e8197'))
            p.setFont(QFont('Microsoft YaHei UI',10))
            p.drawText(QRectF(0,center.y()+95,self.width(),25),Qt.AlignmentFlag.AlignCenter,'PNG / JPG / WebP / BMP / TIFF')
            return
        rect=self.image_rect()
        p.save()
        p.setClipRect(rect,Qt.ClipOperation.IntersectClip)
        p.setBrushOrigin(rect.topLeft())
        p.fillRect(rect,self.checker)
        shown=self.original if self.view=='original' or self.result is None else self.result
        p.drawPixmap(rect,shown,QRectF(shown.rect()))
        split=self.width()*self.split
        if self.view=='compare' and self.result is not None:
            p.setClipRect(QRectF(0,0,split,self.height()),Qt.ClipOperation.IntersectClip)
            p.fillRect(rect,self.checker)
            p.drawPixmap(rect,self.original,QRectF(self.original.rect()))
        p.restore()
        if self.view=='compare' and self.result is not None:
            p.setPen(QPen(QColor('#ffffff'),2))
            p.drawLine(QPointF(split,0),QPointF(split,self.height()))
            p.setBrush(QColor('#3e75ad'))
            p.drawRoundedRect(QRectF(split-14,self.height()/2-22,28,44),12,12)
            p.setFont(QFont('Microsoft YaHei UI',11))
            cy=self.height()/2
            p.drawLine(QPointF(split-7,cy),QPointF(split+7,cy))
            p.drawLine(QPointF(split-7,cy),QPointF(split-3,cy-4))
            p.drawLine(QPointF(split-7,cy),QPointF(split-3,cy+4))
            p.drawLine(QPointF(split+7,cy),QPointF(split+3,cy-4))
            p.drawLine(QPointF(split+7,cy),QPointF(split+3,cy+4))
            for text,x in [('原图',14),('处理后',self.width()-82)]:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(31,49,70,210))
                box=QRectF(x,14,68,28)
                p.drawRoundedRect(box,7,7)
                p.setPen(QColor('white'))
                p.setFont(QFont('Microsoft YaHei UI',10))
                p.drawText(box,Qt.AlignmentFlag.AlignCenter,text)

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        if self.original is None:
            self.open_requested.emit()
            return
        self.last_pos=event.position()
        self.drag='split' if self.view=='compare' and self.result is not None and abs(event.position().x()-self.width()*self.split)<20 else 'pan'
        self.setCursor(Qt.CursorShape.SplitHCursor if self.drag=='split' else Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self,event):
        if self.drag=='split':
            self.split=max(.03,min(.97,event.position().x()/self.width()))
        elif self.drag=='pan':
            self.offset+=event.position()-self.last_pos
            self.clamp_offset()
        else:
            split=self.view=='compare' and self.result is not None and abs(event.position().x()-self.width()*self.split)<20
            self.setCursor(Qt.CursorShape.SplitHCursor if split else Qt.CursorShape.OpenHandCursor if self.original else Qt.CursorShape.PointingHandCursor)
        self.last_pos=event.position()
        self.update()

    def mouseReleaseEvent(self,event):
        self.drag=None
        self.unsetCursor()

    def wheelEvent(self,event):
        if self.original is None:return
        old=self.current_scale()
        new=max(.01,min(16.,old*1.2**(event.angleDelta().y()/120)))
        center=QPointF(self.width()/2,self.height()/2)
        self.offset=event.position()-center-(event.position()-center-self.offset)*(new/old)
        self.zoom=new
        self.clamp_offset()
        self.report_zoom()
        self.update()
        event.accept()

    def resizeEvent(self,event):
        self.clamp_offset()
        self.report_zoom()
        super().resizeEvent(event)

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and any(u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in ('.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff') for u in event.mimeData().urls()):event.acceptProposedAction()

    def dropEvent(self,event):
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in ('.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff'):
                self.file_dropped.emit(url.toLocalFile())
                event.acceptProposedAction()
                break


class Bridge(QObject):
    done = Signal(str, object)
    status = Signal(str)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('清影图片降噪 2.5')
        available=self.screen().availableGeometry()
        self.resize(min(1280,max(1000,int(available.width()*.94))),min(820,max(650,int(available.height()*.9))))
        self.setMinimumSize(1000,650)
        self.original=self.result=None
        self.path=None
        self.output=default_output()
        self.busy=False
        self.glass_opacity=.9
        self.blur_radius=30
        self.background=self.blurred_background=None
        self._backdrop_size=None
        self.controls=[]
        self.bridge=Bridge(self)
        self.bridge.done.connect(self.completed)
        self.bridge.status.connect(lambda text:self.status.setText(text))
        resource_root=Path(sys._MEIPASS) if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
        self.setStyleSheet(STYLE+'''
            QLabel#brand { font-size:24px; color:#274969; }
            QLabel#title { font-size:17px; color:#314860; }
            QPushButton { padding:9px 15px; border-radius:8px; }
            QPushButton:checked { background:#deebf9; color:#24598a; border-color:#9dbddd; }
            QComboBox { background:#f9fbfe; border:1px solid #c9d6e5; border-radius:8px; padding:10px; min-height:20px; }
            QComboBox::drop-down { border:none; width:24px; }
            QComboBox::down-arrow { image:url(assets/chevron.svg); width:12px; height:12px; }
            QComboBox QAbstractItemView { background:#f9fbfe; selection-background-color:#deebf9; color:#29364c; }
            QDialog { background:#f0f5fb; }
        '''.replace('assets/chevron.svg',(resource_root/'assets'/'chevron.svg').as_posix()))
        outer=QVBoxLayout(self)
        outer.setContentsMargins(24,20,24,16)
        outer.setSpacing(18)
        top=QHBoxLayout()
        brand=label('清影')
        brand.setObjectName('brand')
        top.addWidget(brand)
        top.addSpacing(10)
        top.addWidget(label('让细节，更清晰',True))
        top.addStretch()
        top.addWidget(self.button('打开图片',self.open_image))
        top.addWidget(self.button('批量处理',self.batch))
        top.addWidget(self.button('设置',self.show_settings))
        self.save_button=self.button('保存结果',self.export,True)
        self.save_button.setEnabled(False)
        top.addWidget(self.save_button)
        outer.addLayout(top)
        workspace=QHBoxLayout()
        workspace.setSpacing(20)
        outer.addLayout(workspace,1)
        self.sidebar=GlassPanel(radius=16,tint=.95)
        self.sidebar.setFixedWidth(290)
        workspace.addWidget(self.sidebar)
        side=QVBoxLayout(self.sidebar)
        side.setContentsMargins(20,20,20,20)
        side.setSpacing(16)
        title=label('处理参数')
        title.setObjectName('title')
        side.addWidget(title)
        self.scroll=QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content=QWidget()
        self.scroll.setWidget(content)
        side.addWidget(self.scroll,1)
        settings=QVBoxLayout(content)
        settings.setContentsMargins(0,0,6,0)
        settings.setSpacing(10)
        algorithm_row=QHBoxLayout()
        algorithm_row.addWidget(label('降噪算法'))
        algorithm_row.addStretch()
        help_button=QToolButton()
        help_button.setText('选择建议')
        help_button.clicked.connect(lambda:QMessageBox.information(self,'选择降噪算法','插画与生成图：优先使用二次元降噪。\n线条重建：可试 Real-CUGAN。\n生成图杂纹：可试 AI Image Rehab。\n普通照片：使用精细降噪。\n轻度噪点：使用快速保边。\n黑白颗粒：使用去除颗粒。'))
        algorithm_row.addWidget(help_button)
        settings.addLayout(algorithm_row)
        self.mode_group=QButtonGroup(self)
        self.radios=[]
        for i,mode in enumerate(MODES):
            radio=QRadioButton(mode,self)
            radio.hide()
            self.mode_group.addButton(radio,i)
            radio.setChecked(i==0)
            self.radios.append(radio)
        self.mode_combo=QComboBox()
        for i in [0,4,5,1,2,3]:self.mode_combo.addItem(MODES[i],i)
        self.controls.append(self.mode_combo)
        settings.addWidget(self.mode_combo)
        self.mode_description=label('',True)
        settings.addWidget(self.mode_description)
        line=QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet('background:#dce5ef;')
        settings.addWidget(line)
        row=QHBoxLayout()
        row.addWidget(label('降噪强度'))
        row.addStretch()
        self.strength_value=label('高')
        self.strength_value.setObjectName('badge')
        row.addWidget(self.strength_value)
        settings.addLayout(row)
        self.strength=QSlider(Qt.Orientation.Horizontal)
        self.strength.setRange(1,3)
        self.strength.setValue(3)
        self.strength.setSingleStep(1)
        self.strength.setPageStep(1)
        self.strength.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.strength.valueChanged.connect(self.strength_changed)
        self.controls.append(self.strength)
        settings.addWidget(self.strength)
        self.strength_hint=label('',True)
        settings.addWidget(self.strength_hint)
        row=QHBoxLayout()
        row.addWidget(label('输出倍率'))
        row.addStretch()
        self.scale_value=label('1×（原尺寸）')
        self.scale_value.setObjectName('badge')
        row.addWidget(self.scale_value)
        settings.addLayout(row)
        self.scale_slider=QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setSingleStep(1)
        self.scale_slider.setPageStep(1)
        self.scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.scale_slider.setTickInterval(1)
        self.controls.append(self.scale_slider)
        settings.addWidget(self.scale_slider)
        self.scale_hint=label('',True)
        settings.addWidget(self.scale_hint)
        settings.addStretch()
        self.info=label('尚未载入图片',True)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        side.addWidget(self.info)
        self.run_button=self.button('开始降噪',self.process,True)
        self.run_button.setMinimumHeight(44)
        side.addWidget(self.run_button)
        self.progress=QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0,1)
        self.progress.setValue(0)
        side.addWidget(self.progress)
        preview=GlassPanel(radius=16,tint=.96)
        workspace.addWidget(preview,1)
        right=QVBoxLayout(preview)
        right.setContentsMargins(16,16,16,12)
        right.setSpacing(12)
        header=QHBoxLayout()
        title=label('图片预览')
        title.setObjectName('title')
        header.addWidget(title)
        header.addStretch()
        self.preview_badge=label('等待载入')
        self.preview_badge.setObjectName('badge')
        header.addWidget(self.preview_badge)
        right.addLayout(header)
        self.result_info=label('打开一张图片，开始清理噪点。',True)
        right.addWidget(self.result_info)
        self.comparison=Comparison()
        self.comparison.open_requested.connect(self.open_image)
        self.comparison.file_dropped.connect(self.load_path)
        right.addWidget(self.comparison,1)
        toolbar=QHBoxLayout()
        toolbar.setSpacing(6)
        self.view_group=QButtonGroup(self)
        self.view_buttons={}
        for i,(text,view) in enumerate([('原图','original'),('结果','result'),('对比','compare')]):
            button=QPushButton(text)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumWidth(54)
            button.clicked.connect(lambda checked=False,v=view:self.comparison.set_view(v))
            self.view_group.addButton(button,i)
            self.view_buttons[view]=button
            toolbar.addWidget(button)
        toolbar.addStretch()
        self.zoom_label=label('—',True)
        toolbar.addWidget(self.zoom_label)
        self.comparison.zoom_changed.connect(self.zoom_label.setText)
        self.fit_button=QPushButton('适应')
        self.fit_button.clicked.connect(self.comparison.fit)
        toolbar.addWidget(self.fit_button)
        self.actual_button=QPushButton('100%')
        self.actual_button.clicked.connect(self.comparison.actual_size)
        toolbar.addWidget(self.actual_button)
        right.addLayout(toolbar)
        right.addWidget(label('滚轮缩放 · 拖动画面 · 对比时拖动中间分割线',True))
        self.status=label('就绪 · 全部处理在本机完成',True)
        outer.addWidget(self.status)
        self._active_mode=0
        self._active_scale=1
        self._result_scale=1
        self._over_limit=False
        self._scales={i:1 for i in range(len(MODES))}
        self._strengths={(i,scale):(3 if i in (0,4) else 2 if i==5 else 10) for i,mode in enumerate(MODES) for scale in supported_scales(mode)}
        self.mode_group.idToggled.connect(lambda index,checked:self.mode_changed(index) if checked else None)
        self.mode_combo.currentIndexChanged.connect(self.select_mode)
        self.scale_slider.valueChanged.connect(self.scale_changed)
        self.settings_dialog=QDialog(self)
        self.settings_dialog.setWindowTitle('清影 · 设置')
        self.settings_dialog.resize(430,430)
        dialog_layout=QVBoxLayout(self.settings_dialog)
        dialog_layout.setContentsMargins(24,24,24,24)
        dialog_layout.setSpacing(16)
        dialog_layout.addWidget(label('默认输出目录'))
        self.output_label=label(str(self.output),True)
        self.output_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dialog_layout.addWidget(self.output_label)
        dialog_layout.addWidget(self.button('更改输出目录',self.choose_output))
        dialog_layout.addWidget(label('玻璃外观'))
        dialog_layout.addWidget(label('背景柔和度',True))
        self.blur_slider=QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setRange(4,40)
        self.blur_slider.setValue(self.blur_radius)
        self.blur_slider.valueChanged.connect(self.set_blur)
        dialog_layout.addWidget(self.blur_slider)
        dialog_layout.addWidget(label('面板底色浓度',True))
        self.opacity_slider=QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(40,95)
        self.opacity_slider.setValue(90)
        self.opacity_slider.valueChanged.connect(self.set_opacity)
        dialog_layout.addWidget(self.opacity_slider)
        dialog_layout.addWidget(label('仅改变界面外观，不影响导出图片。\n清影 2.5 · 本地降噪与放大',True))
        close=QPushButton('完成')
        close.clicked.connect(self.settings_dialog.accept)
        dialog_layout.addWidget(close)
        self.resize_timer=QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(90)
        self.resize_timer.timeout.connect(self.build_background)
        self.blur_timer=QTimer(self)
        self.blur_timer.setSingleShot(True)
        self.blur_timer.setInterval(80)
        self.blur_timer.timeout.connect(self.build_background)
        self.select_mode(0)
        self.refresh_parameters()
        self.sync_view_buttons()
        self.build_background()

    def show_settings(self):
        self.settings_dialog.exec()

    def select_mode(self,index):
        mode_id=self.mode_combo.itemData(index)
        self.radios[mode_id].setChecked(True)
        descriptions={0:'适合插画与生成图，清理颗粒并保留线条。',4:'重建线条与纹理，支持多种放大倍率。',5:'清理生成图杂纹，保持原始尺寸。',1:'适合普通照片的细小噪点，处理较慢。',2:'适合轻度噪点，处理速度较快。',3:'适合黑白颗粒与椒盐噪声。'}
        self.mode_description.setText(descriptions[mode_id])

    def sync_view_buttons(self):
        for view,button in self.view_buttons.items():
            button.setEnabled(self.original is not None if view=='original' else self.result is not None)
            button.setChecked(view==self.comparison.view)
        self.fit_button.setEnabled(self.original is not None)
        self.actual_button.setEnabled(self.original is not None)

    def load_path(self,path):
        if self.busy:return
        self.status.setText('正在读取图片…')
        self.start(lambda:('loaded',(path,load_image(path))))


    def button(self, text, callback, primary=False):
        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            button.setObjectName('primary')
        button.clicked.connect(callback)
        self.controls.append(button)
        return button

    def strength_changed(self,value):
        self.strength_value.setText(strength_label(MODES[self.mode_group.checkedId()],value))
        if hasattr(self, 'run_button') and self.result is not None:
            self.status.setText('参数已调整 · 重新降噪后更新结果')

    def mode_changed(self,index):
        self._strengths[(self._active_mode,self._active_scale)]=self.strength.value()
        self._scales[self._active_mode]=self._active_scale
        self._active_mode=index
        self._active_scale=self._scales[index]
        self.refresh_parameters()

    def scale_changed(self,position):
        self._strengths[(self._active_mode,self._active_scale)]=self.strength.value()
        self._active_scale=supported_scales(MODES[self._active_mode])[position]
        self._scales[self._active_mode]=self._active_scale
        self.refresh_parameters()

    def refresh_parameters(self):
        mode=MODES[self._active_mode]
        scale=self._active_scale
        scales=supported_scales(mode)
        low,high=strength_range(mode,scale)
        self.strength.blockSignals(True)
        self.strength.setRange(low,high)
        self.strength.setTickInterval(1 if high<=3 else 10)
        self.strength.setValue(max(low,min(high,self._strengths[(self._active_mode,scale)])))
        self.strength.blockSignals(False)
        self.strength_changed(self.strength.value())
        self.strength.setEnabled(not self.busy and low!=high)
        self.scale_slider.blockSignals(True)
        self.scale_slider.setRange(0,len(scales)-1)
        self.scale_slider.setValue(scales.index(scale))
        self.scale_slider.blockSignals(False)
        self.scale_slider.setEnabled(not self.busy and len(scales)>1)
        self.scale_value.setText('1×（原尺寸）' if scale==1 else f'{scale}×')
        if mode==CUGAN_MODE:
            text='3× / 4× 模型仅支持高档，已自动选择。' if scale in (3,4) else '低 / 中 / 高三档。1× 以 2× 模型重建后缩回原尺寸。'
        elif mode==REHAB_MODE:
            text='轻柔：半强度柔和上色；柔和上色：保守清理；平涂清理：更强。'
        elif mode==NEURAL_MODE:
            text='低 / 中 / 高三档；支持原尺寸降噪及神经网络放大。'
        else:text='传统模式建议 6–12；强度越高，纹理越柔和。'
        self.strength_hint.setText(text)
        self.update_dimension_hint()

    def update_dimension_hint(self):
        mode=MODES[self._active_mode]
        scale=self._active_scale
        text=('此算法不支持放大，保持原始尺寸。' if len(supported_scales(mode))==1
              else '倍率：'+' / '.join(f'{n}×' for n in supported_scales(mode)))
        self._over_limit=False
        if self.original is not None:
            w,h=self.original.width*scale,self.original.height*scale
            self._over_limit=w*h>60_000_000
            text+=f'\n预计输出 {w} × {h} 像素。'
            if self._over_limit:text+='超过 6000 万像素，请降低倍率。'
        self.scale_hint.setText(text)
        self.scale_hint.setStyleSheet('color:#b45338;' if self._over_limit else '')
        if hasattr(self,'run_button'):self.run_button.setEnabled(not self.busy and self.original is not None and not self._over_limit)

    def set_blur(self, value):
        self.blur_radius = value
        self.blur_timer.start()

    def set_opacity(self, value):
        self.glass_opacity = value/100
        for panel in self.findChildren(GlassPanel):
            panel.update()

    def build_background(self):
        # A small, cached decorative backdrop keeps gaussian blur inexpensive during resize.
        w, h = max(1, self.width()), max(1, self.height())
        yy, xx = np.mgrid[0:450, 0:800]
        ratio = (xx/800*.35+yy/450*.65)[..., None]
        start, end = np.array([222, 235, 249]), np.array([235, 230, 247])
        image = Image.fromarray((start*(1-ratio)+end*ratio).astype('uint8'))
        decor = Image.new('RGBA', image.size)
        d = ImageDraw.Draw(decor)
        d.ellipse((-110, -140, 340, 300), fill=(146, 187, 236, 100))
        d.ellipse((350, -140, 960, 360), fill=(207, 185, 230, 70))
        d.ellipse((15, 295, 470, 740), fill=(171, 214, 223, 95))
        d.arc((-150, -170, 550, 500), 5, 160, fill=(255, 255, 255, 130), width=16)
        d.arc((-95, -110, 520, 530), 5, 160, fill=(255, 255, 255, 80), width=3)
        image = Image.alpha_composite(image.convert('RGBA'), decor)
        self.background = pixmap(image).scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        blurred = image.filter(ImageFilter.GaussianBlur(self.blur_radius))
        self.blurred_background = pixmap(blurred).scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.background = self.blurred_background
        self._backdrop_size = (w, h)
        self.update()
        for panel in self.findChildren(GlassPanel):
            panel.update()

    def paintEvent(self, event):
        p = QPainter(self)
        if self.background is not None:
            p.drawPixmap(self.rect(), self.background)

    def resizeEvent(self, event):
        if hasattr(self, 'resize_timer'):
            self.resize_timer.start()
        super().resizeEvent(event)

    def set_busy(self, busy):
        self.busy = busy
        self.run_button.setText('正在处理…' if busy else '开始降噪')
        for control in self.controls:
            control.setEnabled(not busy)
        self.save_button.setEnabled(not busy and self.result is not None)
        self.scale_slider.setEnabled(not busy and len(supported_scales(MODES[self._active_mode]))>1)
        low,high=strength_range(MODES[self._active_mode],self._active_scale)
        self.strength.setEnabled(not busy and low!=high)
        self.run_button.setEnabled(not busy and self.original is not None and not self._over_limit)
        self.progress.setRange(0, 0 if busy else 1)
        if not busy:
            self.progress.setValue(0)

    def start(self, worker):
        self.set_busy(True)
        def job():
            try:
                kind, data = worker()
                self.bridge.done.emit(kind, data)
            except Exception as exc:
                self.bridge.done.emit('error', str(exc))
        threading.Thread(target=job, daemon=True).start()

    def open_image(self):
        if self.busy:return
        path, _ = QFileDialog.getOpenFileName(self, '载入图片', '', IMAGE_FILTER)
        if path:
            self.status.setText('正在读取图片…')
            self.start(lambda: ('loaded', (path, load_image(path))))

    def process(self):
        if self.original is None:
            QMessageBox.information(self, '提示', '请先载入一张图片。')
            return
        original = self.original
        mode = MODES[self.mode_group.checkedId()]
        strength = self.strength.value()
        scale = self._active_scale
        try:validate_settings(original,mode,strength,scale)
        except ValueError as exc:
            QMessageBox.warning(self,'参数不可用',str(exc))
            return
        self.status.setText(f'正在处理 · {mode} · {scale}× · 大图可能需要一些时间…')
        self.start(lambda: ('result', (denoise(original, mode, strength,scale), mode, strength,scale)))

    def choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, '选择输出目录', str(self.output))
        if folder:
            try:
                self.output = writable_folder(folder)
                self.output_label.setText(str(self.output))
            except OSError as exc:
                QMessageBox.warning(self, '目录不可写', str(exc))

    def export(self):
        if self.result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, '保存降噪结果', str(self.output / (Path(self.path).stem+('_降噪.png' if self._result_scale==1 else f'_降噪_{self._result_scale}x.png'))), 'PNG 图片 (*.png);;JPEG 图片 (*.jpg);;WebP 图片 (*.webp)')
        if not path:
            return
        if not Path(path).suffix:
            path += '.png'
        if os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(self.path)):
            QMessageBox.information(self, '保护原图', '请使用新的文件名保存，保留原图。')
            return
        result = self.result
        def worker():
            save_image(result, path)
            return 'saved', path
        self.start(worker)

    def batch(self):
        paths, _ = QFileDialog.getOpenFileNames(self, '选择多张图片', '', IMAGE_FILTER)
        if not paths:
            return
        folder = QFileDialog.getExistingDirectory(self, '选择导出目录', str(self.output))
        if not folder:
            return
        mode, strength = MODES[self.mode_group.checkedId()], self.strength.value()
        scale=self._active_scale
        def worker():
            output = Path(tempfile.mkdtemp(prefix='清影_降噪_', dir=folder))
            failures = []
            for i, path in enumerate(paths, 1):
                self.bridge.status.emit(f'批量处理中 {i}/{len(paths)} · {Path(path).name}')
                try:
                    save_image(denoise(load_image(path), mode, strength,scale), output/f'{i:03d}_{Path(path).stem}_降噪_{scale}x.png')
                except Exception as exc:
                    failures.append(f'{path}: {exc}')
            if failures:
                (output/'失败记录.txt').write_text('\n'.join(failures), encoding='utf-8')
            return 'batch', f'成功 {len(paths)-len(failures)} 张，失败 {len(failures)} 张。\n{output}'
        self.start(worker)

    def completed(self, kind, data):
        if kind == 'loaded':
            self.path, self.original = data
            self.result = None
            self._result_scale=1
            self.update_dimension_hint()
            self.info.setText(f'{Path(self.path).name}\n{self.original.width} × {self.original.height} 像素')
            self.preview_badge.setText('原图 · 等待降噪')
            self.result_info.setText('图片已载入，点击左侧“开始降噪”。')
            self.status.setText('图片已载入，请选择模式与强度。')
            self.comparison.set_images(self.original)
        elif kind == 'result':
            self.result, mode, strength, *extra = data
            self._result_scale=extra[0] if extra else 1
            strength_text=strength_label(mode,strength)
            self.preview_badge.setText('处理完成')
            self.result_info.setText(f'{Path(self.path).name} · {self.original.width} × {self.original.height} → {self.result.width} × {self.result.height} · {mode} · {strength_text} · {self._result_scale}×')
            self.status.setText('降噪完成 · 可放大检查细节，或拖动分割线对比')
            self.comparison.set_images(self.original, self.result)
        self.set_busy(False)
        self.sync_view_buttons()
        if kind == 'error':
            self.status.setText('操作失败，可调整后重试。')
            QMessageBox.warning(self, '操作失败', data)
        elif kind == 'saved':
            self.status.setText(f'已保存：{data}')
        elif kind == 'batch':
            self.status.setText('批量任务完成')
            QMessageBox.information(self, '批量任务完成', data)

    def closeEvent(self, event):
        if self.busy and QMessageBox.question(self, '退出清影', '当前任务尚未完成，确定退出并终止任务吗？') != QMessageBox.StandardButton.Yes:
            event.ignore()
        else:
            cancel_processing()
            event.accept()


def main():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Qingying.ImageDenoiser')
    application = QApplication(sys.argv)
    application.setApplicationName('清影图片降噪')
    resource_root = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    application.setWindowIcon(QIcon(str(resource_root / 'assets' / 'app_icon.ico')))
    # Construct UI only after QApplication; image processing remains in engine.py.
    window = MainWindow()
    if len(sys.argv)==3 and sys.argv[1]=='--self-test':
        assert not application.windowIcon().isNull(), 'Application icon did not load'
        assert not window.windowIcon().isNull(), 'Window icon did not load'
        folder = writable_folder(sys.argv[2])
        image = Image.fromarray(np.random.default_rng(17).integers(90, 170, (180, 320, 3), dtype=np.uint8))
        for i, mode in enumerate(MODES):
            save_image(denoise(image, mode, 3 if mode in (NEURAL_MODE,CUGAN_MODE,REHAB_MODE) else 12), folder/f'测试_{i}.png')
        window.path = str(folder/'测试_0.png')
        window.completed('loaded', (window.path, image))
        window.completed('result', (load_image(folder/'测试_0.png'), MODES[0], 3))
        window.show()
        application.processEvents()
        rect = window.comparison.image_rect()
        window.comparison.set_view('compare')
        loop = QEventLoop()
        QTimer.singleShot(180, loop.quit)
        loop.exec()
        window.grab().save(str(folder/'界面自检.png'))
        window.close()
        (folder/'自检结果.json').write_text(json.dumps({'status':'PASS','modes':6,'scale_options':{mode:supported_scales(mode) for mode in MODES},'default':'Waifu2x CUNet, noise=3, scale=1','image_export':True,'glass':True,'fixed_comparison':True},ensure_ascii=False),encoding='utf-8')
        return 0
    window.show()
    return application.exec()

