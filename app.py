import sys, os, traceback

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
        QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
        QSlider, QCheckBox, QComboBox, QSpinBox, QProgressBar,
        QSizePolicy, QSplitter, QGroupBox, QRadioButton,
        QMessageBox, QStatusBar, QApplication
    )
    from PyQt6.QtCore import (Qt, pyqtSignal, QRunnable, QThreadPool,
                               pyqtSlot, QObject, QPoint, QPointF, QRect)
    from PyQt6.QtGui import (
        QPixmap, QImage, QDragEnterEvent, QDropEvent,
        QKeySequence, QShortcut, QPainter, QPen, QBrush,
        QPolygonF, QFont, QColor, QCursor
    )
    from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
    PYQT = 6
    AC   = Qt.AlignmentFlag.AlignCenter
    ABH  = Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter
    ATL  = Qt.AlignmentFlag.AlignTop    | Qt.AlignmentFlag.AlignLeft
    HOR  = Qt.Orientation.Horizontal
    KAR  = Qt.AspectRatioMode.KeepAspectRatio
    SMO  = Qt.TransformationMode.SmoothTransformation
    EXP  = QSizePolicy.Policy.Expanding
    LMB  = Qt.MouseButton.LeftButton
    RMB  = Qt.MouseButton.RightButton
    NP   = Qt.PenStyle.NoPen
    SL   = Qt.PenStyle.SolidLine
    DL   = Qt.PenStyle.DashLine
    RC   = Qt.PenCapStyle.RoundCap
    RJ   = Qt.PenJoinStyle.RoundJoin
    CC   = Qt.CursorShape.CrossCursor
    CM   = Qt.KeyboardModifier.ControlModifier
    SM   = Qt.KeyboardModifier.ShiftModifier
    SF   = Qt.FocusPolicy.StrongFocus
    KE   = Qt.Key.Key_Escape
    KR   = Qt.Key.Key_Return
    KN   = Qt.Key.Key_Enter
    KZ   = Qt.Key.Key_Z
    _ok  = lambda d: d.exec() == d.DialogCode.Accepted
    _PH  = QPrinter.PrinterMode.HighResolution
except ImportError:
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
        QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
        QSlider, QCheckBox, QComboBox, QSpinBox, QProgressBar,
        QSizePolicy, QSplitter, QGroupBox, QRadioButton,
        QMessageBox, QStatusBar, QApplication
    )
    from PyQt5.QtCore import (Qt, pyqtSignal, QRunnable, QThreadPool,
                               pyqtSlot, QObject, QPoint, QPointF, QRect)
    from PyQt5.QtGui import (
        QPixmap, QImage, QDragEnterEvent, QDropEvent,
        QKeySequence, QShortcut, QPainter, QPen, QBrush,
        QPolygonF, QFont, QColor, QCursor
    )
    from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
    PYQT = 5
    AC   = Qt.AlignCenter
    ABH  = Qt.AlignBottom | Qt.AlignHCenter
    ATL  = Qt.AlignTop    | Qt.AlignLeft
    HOR  = Qt.Horizontal
    KAR  = Qt.KeepAspectRatio
    SMO  = Qt.SmoothTransformation
    EXP  = QSizePolicy.Expanding
    LMB  = Qt.LeftButton
    RMB  = Qt.RightButton
    NP   = Qt.NoPen
    SL   = Qt.SolidLine
    DL   = Qt.DashLine
    RC   = Qt.RoundCap
    RJ   = Qt.RoundJoin
    CC   = Qt.CrossCursor
    CM   = Qt.ControlModifier
    SM   = Qt.ShiftModifier
    SF   = Qt.StrongFocus
    KE   = Qt.Key_Escape
    KR   = Qt.Key_Return
    KN   = Qt.Key_Enter
    KZ   = Qt.Key_Z
    _ok  = lambda d: d.exec() == d.Accepted
    _PH  = QPrinter.HighResolution

from PIL import Image
from processor import (
    auto_crop_document, enhance_image, remove_background,
    manual_polygon_crop, snap_points_to_edges,
    get_cfad_debug_overlay,
    save_image, upscale_image, pil_to_bytes
)

STYLE = """
QMainWindow,QWidget{background:#0d0f1a;color:#dde4f0;
  font-family:'Segoe UI','SF Pro Display',sans-serif;font-size:13px;}
QFrame#card{background:#161929;border:1px solid #252d4a;border-radius:12px;}
QFrame#drop{background:#101320;border:2px dashed #2e3766;border-radius:14px;}
QFrame#drop:hover{border-color:#6c63ff;background:#13162b;}

QPushButton{background:#1e2240;color:#FFFFFF;border:1px solid #2e3660;
  border-radius:8px;padding:7px 16px;font-weight:600;font-size:12px;}
QPushButton:hover{background:#262b50;border-color:#6c63ff;color:#fff;}
QPushButton:pressed{background:#181c38;}
QPushButton:disabled{color:#3a4060;border-color:#1e2240;}
QPushButton:checked{background:#6c63ff;color:#fff;border-color:#6c63ff;}

QPushButton#pri{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 #6c63ff,stop:1 #4f46e5);color:#fff;border:none;padding:9px 22px;font-size:13px;}
QPushButton#pri:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 #7d74ff,stop:1 #5f57f5);}
QPushButton#pri:disabled{background:#1e2240;color:#3a4060;}

QPushButton#dan{background:#28111e;color:#f08090;border:1px solid #4a2030;}
QPushButton#dan:hover{background:#33151f;border-color:#f08090;}

QPushButton#suc{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 #10b981,stop:1 #059669);color:#fff;border:none;}
QPushButton#suc:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 #20c991,stop:1 #16a87a);}
QPushButton#suc:disabled{background:#1e2240;color:#3a4060;}

QPushButton#mb{background:#13162b;border:2px solid #1e2545;border-radius:10px;
  color:#5a6490;font-size:12px;font-weight:700;text-align:left;padding:10px 14px;}
QPushButton#mb:checked{background:#6c63ff18;border-color:#6c63ff;color:#c8d0ff;}
QPushButton#mb:hover:!checked{border-color:#2e3766;color:#8896c0;}

QSlider::groove:horizontal{height:4px;background:#1e2240;border-radius:2px;}
QSlider::handle:horizontal{background:#6c63ff;width:14px;height:14px;
  border-radius:7px;margin:-5px 0;}
QSlider::sub-page:horizontal{background:#6c63ff;border-radius:2px;}

QCheckBox{color:#8896b8;spacing:6px;}
QCheckBox::indicator{width:15px;height:15px;border:1px solid #2e3660;
  border-radius:4px;background:#101320;}
QCheckBox::indicator:checked{background:#6c63ff;border-color:#6c63ff;}

QComboBox{background:#161929;border:1px solid #252d4a;border-radius:6px;
  padding:5px 10px;color:#b8c2ff;}
QComboBox::drop-down{border:none;}
QComboBox QAbstractItemView{background:#161929;border:1px solid #2e3660;
  color:#b8c2ff;selection-background-color:#6c63ff;}

QProgressBar{background:#101320;border:1px solid #1e2240;border-radius:4px;
  height:6px;color:transparent;}
QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 #6c63ff,stop:1 #10b981);border-radius:4px;}

QScrollBar:vertical{background:#0d0f1a;width:5px;border-radius:3px;}
QScrollBar::handle:vertical{background:#252d4a;border-radius:3px;}

QGroupBox{color:#6c63ff;font-weight:700;font-size:10px;letter-spacing:.08em;
  border:1px solid #252d4a;border-radius:10px;margin-top:14px;padding-top:8px;}
QGroupBox::title{subcontrol-origin:margin;left:12px;top:-2px;
  padding:0 6px;background:#0d0f1a;}

QRadioButton{color:#8896b8;spacing:8px;}
QRadioButton::indicator{width:15px;height:15px;border:1px solid #2e3660;
  border-radius:8px;background:#101320;}
QRadioButton::indicator:checked{background:#6c63ff;border-color:#6c63ff;}
QRadioButton:checked{color:#c8d0ff;}

QStatusBar{background:#080a14;color:#ffffff;border-top:1px solid #161929;font-size:11px;}

QLabel#bg{background:#6c63ff1a;color:#6c63ff;border:1px solid #6c63ff44;
  border-radius:9px;padding:2px 9px;font-size:10px;font-weight:800;}
QLabel#bgG{background:#10b9811a;color:#10b981;border:1px solid #10b98144;
  border-radius:9px;padding:2px 9px;font-size:10px;font-weight:800;}
QLabel#bgO{background:#f59e0b1a;color:#f59e0b;border:1px solid #f59e0b44;
  border-radius:9px;padding:2px 9px;font-size:10px;font-weight:800;}
"""

class _S(QObject):
    done  = pyqtSignal(object)
    error = pyqtSignal(str)

class Worker(QRunnable):
    def __init__(self, fn, *a, **kw):
        super().__init__()
        self.fn, self.a, self.kw = fn, a, kw
        self.s = _S()
    @pyqtSlot()
    def run(self):
        try:    self.s.done.emit(self.fn(*self.a, **self.kw))
        except: self.s.error.emit(traceback.format_exc())

#  image preview
class ImgLabel(QLabel):
    def __init__(self, ph="Drop here or Upload", parent=None):
        super().__init__(parent); self._pix=None; self._ph=ph
        self.setAlignment(AC); self.setMinimumSize(160,130)
        self.setSizePolicy(EXP,EXP); self._showph()
    def _showph(self):
        self.setText(self._ph)
        self.setStyleSheet("color:#2e3766;font-size:13px;font-weight:600;")
    def set_pil(self, img):
        self._pix = QPixmap.fromImage(QImage.fromData(pil_to_bytes(img,"PNG")))
        self.setText(""); self.setStyleSheet(""); self._ref()
    def clear(self): self._pix=None; self._showph()
    def _ref(self):
        if self._pix: self.setPixmap(self._pix.scaled(self.size(),KAR,SMO))
    def resizeEvent(self,e): self._ref(); super().resizeEvent(e)

#  drop zone
class DropZone(QFrame):
    dropped = pyqtSignal(str)
    def __init__(self,parent=None):
        super().__init__(parent); self.setObjectName("drop")
        self.setAcceptDrops(True)
        self.img = ImgLabel()
        QVBoxLayout(self).addWidget(self.img)
    def dragEnterEvent(self,e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self,e):
        u=e.mimeData().urls()
        if u:
            p=u[0].toLocalFile()
            if p.lower().endswith((".png",".jpg",".jpeg",".bmp",".tiff",".webp")):
                self.dropped.emit(p)

#  manual crop canvas
class Canvas(QWidget):
    confirmed = pyqtSignal(list)

    _CF = QColor(108,99,255,40)
    _CL = QColor(108,99,255,220)
    _CD = QColor(108,99,255,80)
    _CP = QColor(108,99,255,255)
    _CA = QColor(16,185,129,255)
    _CH = QColor(245,158,11,180)
    _CE = QColor(0,220,200,60)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setMinimumSize(200,160); self.setSizePolicy(EXP,EXP)
        self.setStyleSheet("background:#101320;border-radius:10px;")
        self.setCursor(QCursor(CC)); self.setFocusPolicy(SF)
        self.setMouseTracking(True)
        self._pil=None; self._qpix=None; self._epix=None
        self._sc=1.0; self._off=QPoint(0,0)
        self._pts=[]; self._fh=[]; self._drag=False; self._mpos=None
        self._hint=("Shift+Click = corner  |  Hold LMB = freehand  |  "
                    "Right-click/Ctrl+Z = undo  |  Double-click/Enter = crop  |  Esc = clear")

    # public
    def set_image(self, pil):
        self._pil=pil; self._pts=[]; self._fh=[]
        self._rebuild(); self.update()
    def clear_points(self): self._pts=[]; self._fh=[]; self.update()
    def img_pts(self): return [self._c2i(p) for p in self._pts]
    def npts(self): return len(self._pts)

    # pixmaps
    def _rebuild(self):
        if not self._pil: return
        self._qpix=QPixmap.fromImage(QImage.fromData(pil_to_bytes(self._pil,"PNG")))
        self._epix=self._make_edge_pix()
        self._recalc()
    def _make_edge_pix(self):
        try:
            import numpy as np, cv2
            from processor import pil_to_cv2
            cv_img=pil_to_cv2(self._pil)
            gray=cv2.cvtColor(cv_img,cv2.COLOR_BGR2GRAY)
            e=cv2.Canny(cv2.GaussianBlur(gray,(3,3),0),20,70)
            e=cv2.dilate(e,np.ones((2,2),np.uint8))
            h,w=e.shape
            rgba=np.zeros((h,w,4),np.uint8); rgba[e>0]=[0,220,200,80]
            fmt = QImage.Format.Format_RGBA8888 if PYQT==6 else QImage.Format_RGBA8888
            return QPixmap.fromImage(QImage(rgba.tobytes(),w,h,w*4,fmt))
        except: return None
    def _recalc(self):
        if not self._qpix: return
        ww,wh=self.width(),self.height()
        pw,ph=self._qpix.width(),self._qpix.height()
        self._sc=min(ww/pw,wh/ph)
        dw,dh=int(pw*self._sc),int(ph*self._sc)
        self._off=QPoint((ww-dw)//2,(wh-dh)//2)
    def _c2i(self,p):
        return ((p.x()-self._off.x())/self._sc,(p.y()-self._off.y())/self._sc)
    def _imgrect(self):
        if not self._qpix: return QRect()
        return QRect(self._off.x(),self._off.y(),
                     int(self._qpix.width()*self._sc),int(self._qpix.height()*self._sc))

    # paint
    def paintEvent(self,_):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor("#101320"))
        if not self._qpix:
            p.setPen(QColor("#2e3766")); p.setFont(QFont("Segoe UI",12))
            p.drawText(self.rect(),AC,"Load an image first"); return
        self._recalc()
        p.drawPixmap(self._off,self._qpix.scaled(self.size(),KAR,SMO))
        if self._epix:
            p.drawPixmap(self._off,self._epix.scaled(self.size(),KAR,SMO))
        pts=self._pts
        if len(pts)>=3:
            poly=QPolygonF([QPointF(q.x(),q.y()) for q in pts])
            p.setPen(QPen(NP)); p.setBrush(QBrush(self._CF)); p.drawPolygon(poly)
        if len(pts)>=2:
            p.setPen(QPen(self._CL,2,SL,RC,RJ)); p.setBrush(QBrush(QColor(0,0,0,0)))
            for i in range(len(pts)-1): p.drawLine(pts[i],pts[i+1])
            if len(pts)>=3:
                p.setPen(QPen(self._CD,1.5,DL,RC,RJ)); p.drawLine(pts[-1],pts[0])
        if pts and self._mpos and not self._drag:
            p.setPen(QPen(QColor(108,99,255,70),1,DL)); p.drawLine(pts[-1],self._mpos)
        if len(self._fh)>=2:
            p.setPen(QPen(self._CH,1.8,DL,RC,RJ))
            for i in range(len(self._fh)-1): p.drawLine(self._fh[i],self._fh[i+1])
        for i,pt in enumerate(pts):
            if i==0: p.setBrush(QBrush(self._CA)); p.setPen(QPen(QColor("#fff"),1.5)); p.drawEllipse(pt,8,8)
            else:    p.setBrush(QBrush(self._CP)); p.setPen(QPen(QColor("#fff"),1.5)); p.drawEllipse(pt,5,5)
        if pts:
            p.setPen(QColor("#6c63ff")); p.setFont(QFont("Segoe UI",10))
            p.drawText(self.rect().adjusted(12,10,-12,-10),ATL,f"  {len(pts)} pt{'s' if len(pts)!=1 else ''}")
        p.setPen(QColor("#FFFFFF")); p.setFont(QFont("Segoe UI",9))
        p.drawText(self.rect().adjusted(9,9,-9,-9),ABH,self._hint)

    # events
    def mousePressEvent(self,e):
        if not self._pil: return
        pos=e.pos(); mods=e.modifiers()
        if e.button()==LMB:
            if bool(mods&SM):
                if self._imgrect().contains(pos): self._pts.append(pos); self.update()
            else:
                if self._imgrect().contains(pos): self._drag=True; self._fh=[pos]
        elif e.button()==RMB:
            if self._pts: self._pts.pop(); self.update()
    def mouseMoveEvent(self,e):
        self._mpos=e.pos()
        if self._drag and self._imgrect().contains(e.pos()): self._fh.append(e.pos())
        self.update()
    def mouseReleaseEvent(self,e):
        if e.button()==LMB and self._drag:
            self._drag=False
            if len(self._fh)>=4: self._simplify()
            self._fh=[]; self.update()
    def mouseDoubleClickEvent(self,e):
        if e.button()==LMB and len(self._pts)>=3: self._emit()
    def keyPressEvent(self,e):
        k=e.key()
        if k==KE: self.clear_points()
        elif k in(KR,KN):
            if len(self._pts)>=3: self._emit()
        elif k==KZ and bool(e.modifiers()&CM):
            if self._pts: self._pts.pop(); self.update()
    def resizeEvent(self,e): self._recalc(); super().resizeEvent(e)

    def _simplify(self):
        import numpy as np,cv2
        arr=np.array([[p.x(),p.y()] for p in self._fh],dtype=np.float32).reshape(-1,1,2)
        peri=sum(((self._fh[i+1].x()-self._fh[i].x())**2+
                  (self._fh[i+1].y()-self._fh[i].y())**2)**.5 for i in range(len(self._fh)-1))
        for eps in[.03,.05,.07,.10,.14,.18]:
            a=cv2.approxPolyDP(arr,eps*peri,True)
            if len(a)<=14:
                self._pts=[QPoint(int(x[0][0]),int(x[0][1])) for x in a]; return
        step=max(1,len(self._fh)//12); self._pts=self._fh[::step]

    def _emit(self):
        pts=self.img_pts()
        if len(pts)>=3: self.confirmed.emit(pts)

class EnhPanel(QGroupBox):
    def __init__(self,parent=None):
        super().__init__("Enhancement",parent)
        lay=QGridLayout(self); lay.setContentsMargins(10,16,10,10); lay.setSpacing(6)
        def row(lbl,lo,hi,d,r):
            l=QLabel(lbl); l.setStyleSheet("color:#4a5a80;font-size:11px;")
            sl=QSlider(HOR); sl.setRange(lo,hi); sl.setValue(d)
            vl=QLabel(f"{d/100:.1f}"); vl.setFixedWidth(30)
            vl.setStyleSheet("color:#6c63ff;font-weight:700;font-size:11px;")
            sl.valueChanged.connect(lambda v,_v=vl:_v.setText(f"{v/100:.1f}"))
            lay.addWidget(l,r,0); lay.addWidget(sl,r,1); lay.addWidget(vl,r,2)
            return sl
        self.br=row("Bright",50,200,100,0); self.co=row("Contrast",50,300,100,1)
        self.sh=row("Sharp",50,400,100,2);  self.sa=row("Satur.",50,200,100,3)
        hr=QHBoxLayout()
        self.cd=QCheckBox("Denoise"); self.cd.setChecked(False)
        self.cc=QCheckBox("Auto-Level"); self.cc.setChecked(False)
        hr.addWidget(self.cd); hr.addWidget(self.cc); hr.addStretch()
        lay.addLayout(hr,4,0,1,3)
    def params(self):
        return dict(brightness=self.br.value()/100,contrast=self.co.value()/100,
                    sharpness=self.sh.value()/100,saturation=self.sa.value()/100,
                    denoise=self.cd.isChecked(),clahe=self.cc.isChecked())
    def reset(self):
        self.br.setValue(100);self.co.setValue(100);self.sh.setValue(100);self.sa.setValue(100)
        self.cd.setChecked(False);self.cc.setChecked(False)

class SmartCropApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartCrop Pro"); self.setMinimumSize(1100,700)
        self.resize(1320,820); self.setStyleSheet(STYLE); self.setAcceptDrops(True)
        self._src=None; self._res=None; self._mode=1; self._busy=False
        self._pool=QThreadPool(); self._pool.setMaxThreadCount(2)
        self._build(); self._wire(); self._setmode(1)

    def _build(self):
        c=QWidget(); self.setCentralWidget(c)
        root=QVBoxLayout(c); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(self._hdr())
        body=QSplitter(HOR); body.setContentsMargins(10,8,10,8)
        body.addWidget(self._left()); body.addWidget(self._center()); body.addWidget(self._right())
        body.setSizes([260,700,260]); body.setStretchFactor(1,1)
        root.addWidget(body,1)
        self.sb=QStatusBar(); self.setStatusBar(self.sb)
        self.sb.showMessage("Ready — upload or drop an image to begin")

    def _hdr(self):
        f=QFrame(); f.setFixedHeight(54)
        f.setStyleSheet("background:#080a14;border-bottom:1px solid #161929;")
        lay=QHBoxLayout(f); lay.setContentsMargins(18,0,18,0)
        logo=QLabel("✦ SmartCrop Pro")
        logo.setStyleSheet("font-size:15px;font-weight:800;color:#fff;letter-spacing:-0.02em;")
        lay.addWidget(logo)
        v=QLabel("v4.0"); v.setObjectName("bg"); lay.addWidget(v)
        lay.addStretch()
        self._hb=[]
        for i,t in enumerate(["Smart Crop","Remove BG","Manual Crop"],1):
            b=QPushButton(t); b.setObjectName("pri" if i==0 else "")
            b.setCheckable(True); b.setFixedHeight(30)
            b.clicked.connect(lambda _,n=i:self._setmode(n))
            lay.addWidget(b); self._hb.append(b)
        return f

    def _left(self):
        p=QFrame(); p.setObjectName("card"); p.setFixedWidth(255)
        lay=QVBoxLayout(p); lay.setContentsMargins(14,14,14,14); lay.setSpacing(10)
        lbl=QLabel("MODE"); lbl.setStyleSheet("color:#2e3766;font-size:10px;font-weight:800;letter-spacing:.1em;")
        lay.addWidget(lbl)
        self._mc=[]
        for i,(ic,ti) in enumerate([("","Smart Crop"),("","Remove BG"),("","Manual Crop")],1):
            b=QPushButton(f"  {ic}  {ti}  (Mode {i})")
            b.setObjectName("mb"); b.setCheckable(True); b.setFixedHeight(50)
            b.clicked.connect(lambda _,n=i:self._setmode(n))
            lay.addWidget(b); self._mc.append(b)
        lay.addSpacing(4)
        self.enh=EnhPanel(); lay.addWidget(self.enh)

        self.bgG=QGroupBox("BG Removal Model")
        bl=QVBoxLayout(self.bgG); bl.setContentsMargins(10,16,10,10)
        self.bgC=QComboBox()
        self.bgC.addItems(["u2net (General)","u2net_human_seg (People)","silueta (Fast)","isnet-general-use"])
        bl.addWidget(self.bgC); lay.addWidget(self.bgG)

        self.m3G=QGroupBox("Manual Crop Options")
        ml=QVBoxLayout(self.m3G); ml.setContentsMargins(10,16,10,10); ml.setSpacing(6)
        self.ck_snap=QCheckBox("Snap to edges"); self.ck_snap.setChecked(True)
        self.ck_gc  =QCheckBox("GrabCut refine"); self.ck_gc.setChecked(True)
        self.ck_enh =QCheckBox("Apply enhancement"); self.ck_enh.setChecked(True)
        ml.addWidget(self.ck_snap); ml.addWidget(self.ck_gc); ml.addWidget(self.ck_enh)
        self.btnClrPts=QPushButton("Clear Points"); self.btnClrPts.setObjectName("dan")
        self.btnClrPts.clicked.connect(lambda:self.canvas.clear_points())
        ml.addWidget(self.btnClrPts)
        self.btnConf=QPushButton("Confirm & Crop"); self.btnConf.setObjectName("suc")
        self.btnConf.clicked.connect(self._conf_manual)
        ml.addWidget(self.btnConf)
        lay.addWidget(self.m3G)

        lay.addStretch()
        rb=QPushButton("Reset Settings"); rb.clicked.connect(self._reset)
        lay.addWidget(rb)
        return p

    def _center(self):
        w=QWidget(); lay=QVBoxLayout(w); lay.setContentsMargins(6,0,6,0); lay.setSpacing(8)
        grid=QGridLayout(); grid.setSpacing(8)

        bc=QFrame(); bc.setObjectName("card"); bl=QVBoxLayout(bc); bl.setContentsMargins(10,10,10,10)
        bh=QHBoxLayout()
        t1=QLabel("ORIGINAL"); t1.setStyleSheet("color:#2e3766;font-size:10px;font-weight:800;letter-spacing:.1em;")
        bh.addWidget(t1); bh.addStretch()
        self.szLbl=QLabel(""); self.szLbl.setStyleSheet("color:#2e3766;font-size:10px;")
        bh.addWidget(self.szLbl); bl.addLayout(bh)
        self.dz=DropZone(); bl.addWidget(self.dz,1)
        ur=QHBoxLayout()
        self.btnUp=QPushButton("Upload"); self.btnUp.setObjectName("pri")
        self.btnClr=QPushButton("Clear"); self.btnClr.setObjectName("dan"); self.btnClr.setEnabled(False)
        ur.addWidget(self.btnUp); ur.addWidget(self.btnClr); bl.addLayout(ur)
        self.btnPrev=QPushButton("Preview CFAD Detection")
        self.btnPrev.setEnabled(False)
        self.btnPrev.setToolTip("Showing highlighted area that will be cropped before processing")
        bl.addWidget(self.btnPrev)

        ac=QFrame(); ac.setObjectName("card"); al=QVBoxLayout(ac); al.setContentsMargins(10,10,10,10)
        ah=QHBoxLayout()
        t2=QLabel("RESULT"); t2.setStyleSheet("color:#2e3766;font-size:10px;font-weight:800;letter-spacing:.1em;")
        ah.addWidget(t2); ah.addStretch()
        self.badge=QLabel(""); self.badge.setObjectName("bgG"); self.badge.hide()
        ah.addWidget(self.badge); al.addLayout(ah)
        self.rp=ImgLabel("Process an image to see result"); al.addWidget(self.rp,1)
        rr=QHBoxLayout()
        self.btnProc=QPushButton("Process"); self.btnProc.setObjectName("pri"); self.btnProc.setEnabled(False)
        self.btnSwap=QPushButton("Use as Input"); self.btnSwap.setEnabled(False)
        rr.addWidget(self.btnProc); rr.addWidget(self.btnSwap); al.addLayout(rr)

        grid.addWidget(bc,0,0); grid.addWidget(ac,0,1)

        cf=QFrame(); cf.setObjectName("card"); cl=QVBoxLayout(cf); cl.setContentsMargins(10,10,10,10)
        ch=QHBoxLayout()
        ct=QLabel("DRAW CROP AREA"); ct.setStyleSheet("color:#2e3766;font-size:10px;font-weight:800;letter-spacing:.1em;")
        ch.addWidget(ct); ch.addStretch()
        self.ptsBadge=QLabel(""); self.ptsBadge.setObjectName("bgO"); self.ptsBadge.hide()
        ch.addWidget(self.ptsBadge); cl.addLayout(ch)
        self.canvas=Canvas(); self.canvas.confirmed.connect(self._run_manual)
        cl.addWidget(self.canvas,1)
        orig_paint=self.canvas.paintEvent
        def _pp(e):
            orig_paint(e)
            n=self.canvas.npts()
            self.ptsBadge.setText(f"{n} pt{'s' if n!=1 else ''}"); self.ptsBadge.setVisible(n>0)
        self.canvas.paintEvent=_pp
        self._cf=cf; cf.hide()
        grid.addWidget(cf,1,0,1,2); grid.setRowStretch(0,1); grid.setRowStretch(1,1)

        lay.addLayout(grid,1)
        self.pbar=QProgressBar(); self.pbar.setRange(0,0); self.pbar.hide()
        lay.addWidget(self.pbar)
        return w

    def _right(self):
        p=QFrame(); p.setObjectName("card"); p.setFixedWidth(255)
        lay=QVBoxLayout(p); lay.setContentsMargins(14,14,14,14); lay.setSpacing(10)
        eg=QGroupBox("Export"); el=QGridLayout(eg); el.setContentsMargins(10,16,10,10); el.setSpacing(7)
        el.addWidget(QLabel("Format:"),0,0)
        self.fmt=QComboBox(); self.fmt.addItems(["PNG","JPEG","WEBP","TIFF"]); el.addWidget(self.fmt,0,1)
        el.addWidget(QLabel("DPI:"),1,0)
        self.dpi=QSpinBox(); self.dpi.setRange(72,600); self.dpi.setValue(300); self.dpi.setSuffix(" dpi")
        self.dpi.setStyleSheet("QSpinBox{background:#101320;border:1px solid #1e2240;border-radius:6px;padding:4px 8px;color:#b8c2ff;}")
        el.addWidget(self.dpi,1,1)
        self.ck2x=QCheckBox("2× Upscale (print)"); el.addWidget(self.ck2x,2,0,1,2)
        lay.addWidget(eg)
        self.btnSave=QPushButton("Save Image"); self.btnSave.setObjectName("suc"); self.btnSave.setEnabled(False); self.btnSave.setFixedHeight(36)
        self.btnPrint=QPushButton("Print"); self.btnPrint.setEnabled(False); self.btnPrint.setFixedHeight(36)
        lay.addWidget(self.btnSave); lay.addWidget(self.btnPrint)
        pg=QGroupBox("Print Layout"); pl=QVBoxLayout(pg); pl.setContentsMargins(10,16,10,10)
        self.rb1=QRadioButton("Single"); self.rb1.setChecked(True)
        self.rb2=QRadioButton("2 per page"); self.rb4=QRadioButton("4-up"); self.rb8=QRadioButton("8-up (card)")
        for r in[self.rb1,self.rb2,self.rb4,self.rb8]: pl.addWidget(r)
        lay.addWidget(pg); lay.addStretch()
        self.infoL=QLabel(""); self.infoL.setWordWrap(True)
        self.infoL.setStyleSheet("color:#FFFFFF;font-size:11px;background:#6c63ff0e;border:1px solid #6c63ff2a;border-radius:8px;padding:8px;")
        lay.addWidget(self.infoL)
        return p

    def _wire(self):
        self.dz.dropped.connect(self._load)
        self.btnUp.clicked.connect(self._open)
        self.btnClr.clicked.connect(self._clearall)
        self.btnProc.clicked.connect(self._process)
        self.btnPrev.clicked.connect(self._preview_cfad)
        self.btnSwap.clicked.connect(self._swap)
        self.btnSave.clicked.connect(self._save)
        self.btnPrint.clicked.connect(self._print)
        QShortcut(QKeySequence("Ctrl+O"),self).activated.connect(self._open)
        QShortcut(QKeySequence("Ctrl+S"),self).activated.connect(self._save)
        QShortcut(QKeySequence("Ctrl+Return"),self).activated.connect(self._process)
        QShortcut(QKeySequence("Ctrl+P"),self).activated.connect(self._print)

    def _setmode(self,n):
        self._mode=n
        for i,b in enumerate(self._mc,1): b.setChecked(i==n)
        for i,b in enumerate(self._hb,1): b.setChecked(i==n)
        self.enh.setVisible(n in(1,3)); self.bgG.setVisible(n==2); self.m3G.setVisible(n==3)
        self._cf.setVisible(n==3)
        if n==3:
            self._cf.setMinimumHeight(280)
            if self._src: self.canvas.set_image(self._src); self.canvas.setFocus()
        else:
            self._cf.setMinimumHeight(0); self.canvas.clear_points()
        info={
            1:("Mode 1 — Smart Crop\n\n"
               "Engine: CFAD\n"
               "(Color Frequency Anomaly\n"
               " Detection)\n\n"
               "Scan color frequency\n"
               "Mark dominant color\n"
               "   as a background\n"
               "Color anomaly = object\n"
               "Fit quad → warp\n\n"
               "Click preview to\n"
               "see overlay detection."),
            2:("Mode 2 — Remove BG\n\n"
               "AI background removal.\n\n"),
            3:("Mode 3 — Manual Crop\n\n"
               "Cyan = detected edges.\n\n"
               "Shift+Click → edge\n"
               "Hold LMB   → freehand\n"
               "Right-click → undo\n"
               "Ctrl+Z     → undo\n"
               "Dbl-click/↵ → crop\n"
               "Esc → clear\n\n"
               "4 point → perspective warp\n"
               "Others → GrabCut fit"),
        }
        self.infoL.setText(info[n])
        self.btnPrev.setVisible(n == 1)
        self._uistate()

    def _open(self):
        p,_=QFileDialog.getOpenFileName(self,"Open Image","",
             "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp);;All (*)")
        if p: self._load(p)

    def _load(self,path):
        try:
            img=Image.open(path).convert("RGB")
            self._src=img; self.dz.img.set_pil(img)
            self.szLbl.setText(f"{img.width}×{img.height}")
            self._res=None; self.rp.clear(); self.badge.hide()
            self.sb.showMessage(f"Loaded: {os.path.basename(path)}  ({img.width}×{img.height})")
            if self._mode==3: self.canvas.set_image(img); self.canvas.setFocus()
            self._uistate()
        except Exception as ex:
            QMessageBox.critical(self,"Error",str(ex))

    def _process(self):
        if not self._src or self._busy or self._mode==3: return
        self._startbusy("Processing…")
        if self._mode==1:
            w=Worker(self._m1,self._src)
        else:
            m={0:"u2net",1:"u2net_human_seg",2:"silueta",3:"isnet-general-use"}
            w=Worker(self._m2,self._src,m.get(self.bgC.currentIndex(),"u2net"))
        w.s.done.connect(self._done); w.s.error.connect(self._err); self._pool.start(w)

    def _m1(self,img):
        cropped,method=auto_crop_document(img)
        enhanced=enhance_image(cropped,**self.enh.params())
        return (enhanced,method,"m1")

    def _m2(self,img,model):
        return (remove_background(img,model),True,"m2")

    def _done(self,payload):
        result,info,tag=payload
        self._res=result; self.rp.set_pil(result)
        if tag=="m1":
            labels={"warp":"✓ Perspective Warp","tight":"✓ Tight Crop","fallback":" Fallback"}
            objs={"warp":"bgG","tight":"bgG","fallback":"bg"}
            self.badge.setText(labels.get(info,"✓")); self.badge.setObjectName(objs.get(info,"bgG")); self.badge.show()
            msg=f"Cropped ({info}).  Result: {result.width}×{result.height}"
        else:
            msg=f"Background removed.  Result: {result.width}×{result.height}"
        self.sb.showMessage(msg); self._stopbusy()

    def _err(self,tb):
        self._stopbusy(); QMessageBox.critical(self,"Error",f"Failed:\n\n{tb}")
        self.sb.showMessage("Processing failed.")

    def _preview_cfad(self):
        if not self._src or self._busy: return
        self._startbusy("Scanning color frequencies…")
        w = Worker(get_cfad_debug_overlay, self._src)
        w.s.done.connect(self._done_preview)
        w.s.error.connect(self._err)
        self._pool.start(w)

    def _done_preview(self, overlay_img):
        self.rp.set_pil(overlay_img)
        self.badge.setText("👁 CFAD Preview")
        self.badge.setObjectName("bgO")
        self.badge.show()
        self.sb.showMessage(
            "Preview: green = object's contour  |  red = highlighted area  |  "
            "yellow = quad that'll be wrapped  —  Click process to crop"
        )
        self._stopbusy()
        self._res = None
        self._uistate()

    def _conf_manual(self):
        pts=self.canvas.img_pts()
        if len(pts)<3:
            QMessageBox.warning(self,"Manual Crop","Place at least 3 points.\n\nShift+Click = corner\nHold LMB = freehand"); return
        self._run_manual(pts)

    def _run_manual(self,pts):
        if not self._src or self._busy: return
        self._startbusy(f"Manual crop ({len(pts)} pts)…")
        ep=self.enh.params() if self.ck_enh.isChecked() else None
        w=Worker(manual_polygon_crop,self._src,pts,self.ck_enh.isChecked(),ep,self.ck_gc.isChecked())
        w.s.done.connect(self._done_m3); w.s.error.connect(self._err); self._pool.start(w)

    def _done_m3(self,result):
        self._res=result; self.rp.set_pil(result)
        n=self.canvas.npts()
        self.badge.setText(f"✓ Manual ({n}pt)"); self.badge.setObjectName("bgG"); self.badge.show()
        self.sb.showMessage(f"Manual crop done.  Result: {result.width}×{result.height}")
        self._stopbusy()

    def _save(self):
        if not self._res: return
        fmt=self.fmt.currentText().lower(); ext={"jpeg":"jpg"}.get(fmt,fmt)
        p,_=QFileDialog.getSaveFileName(self,"Save",f"smartcrop.{ext}",f"{fmt.upper()} (*.{ext})")
        if not p: return
        try:
            img=upscale_image(self._res,2) if self.ck2x.isChecked() else self._res
            save_image(img,p,self.dpi.value()); self.sb.showMessage(f"Saved: {os.path.basename(p)}")
        except Exception as ex: QMessageBox.critical(self,"Save Error",str(ex))

    def _print(self):
        if not self._res: return
        try:
            printer=QPrinter(_PH)
            if not _ok(QPrintDialog(printer,self)): return
            copies={self.rb1:1,self.rb2:2,self.rb4:4,self.rb8:8}
            n=next((v for k,v in copies.items() if k.isChecked()),1)
            sheet=self._sheet(self._res,n)
            pix=QPixmap.fromImage(QImage.fromData(pil_to_bytes(sheet,"PNG")))
            pp=QPainter(printer); r=pp.viewport(); s=pix.scaled(r.size(),KAR)
            pp.drawPixmap((r.width()-s.width())//2,(r.height()-s.height())//2,s); pp.end()
            self.sb.showMessage("Sent to printer.")
        except Exception as ex: QMessageBox.critical(self,"Print Error",str(ex))

    def _sheet(self,img,n):
        if n==1: return img.convert("RGB")
        cols=2; rows=n//2; pad=20; W,H=img.width,img.height
        sh=Image.new("RGB",(cols*W+(cols+1)*pad,rows*H+(rows+1)*pad),(255,255,255))
        for i in range(n): sh.paste(img.convert("RGB"),(pad+(i%cols)*(W+pad),pad+(i//cols)*(H+pad)))
        return sh

    def _swap(self):
        if self._res:
            self._src=self._res.convert("RGB"); self.dz.img.set_pil(self._src)
            self.szLbl.setText(f"{self._src.width}×{self._src.height}")
            self._res=None; self.rp.clear(); self.badge.hide()
            if self._mode==3: self.canvas.set_image(self._src)
            self.sb.showMessage("Result moved to input."); self._uistate()

    def _clearall(self):
        self._src=self._res=None; self.dz.img.clear(); self.rp.clear(); self.badge.hide()
        self.szLbl.setText(""); self.canvas.clear_points()
        self.sb.showMessage("Cleared."); self._uistate()

    def _reset(self):
        self.enh.reset(); self.fmt.setCurrentIndex(0); self.dpi.setValue(300)
        self.ck2x.setChecked(False); self.rb1.setChecked(True)

    def _startbusy(self,msg):
        self._busy=True; self.pbar.show(); self.badge.hide()
        self.sb.showMessage(msg); self._uistate()
    def _stopbusy(self):
        self._busy=False; self.pbar.hide(); self._uistate()
    def _uistate(self):
        hs=self._src is not None; hr=self._res is not None; b=self._busy; m3=self._mode==3
        self.btnUp.setEnabled(not b); self.btnClr.setEnabled(hs and not b)
        self.btnProc.setEnabled(hs and not b and not m3)
        self.btnPrev.setEnabled(hs and not b and self._mode==1)
        self.btnConf.setEnabled(hs and not b)
        self.btnSave.setEnabled(hr and not b); self.btnPrint.setEnabled(hr and not b)
        self.btnSwap.setEnabled(hr and not b)

    def dragEnterEvent(self,e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self,e):
        u=e.mimeData().urls()
        if u:
            p=u[0].toLocalFile()
            if p.lower().endswith((".png",".jpg",".jpeg",".bmp",".tiff",".webp")): self._load(p)