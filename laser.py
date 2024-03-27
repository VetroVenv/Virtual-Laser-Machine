from PyQt6.QtCore import QSize, QRectF, QEvent, Qt, QPoint
from PyQt6.QtGui import QImage, QColor, QPainter
from PyQt6.QtWidgets import (
    QApplication, QMainWindow)
from PyQt6 import uic

from enum import Enum
class MarkerState(Enum):
    HIDE = 0,
    ON = 1,
    OFF = 2
from math import floor, log10

from PyQt6.QtCore import QSize, Qt, QPoint, QPointF, QRectF, QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QResizeEvent, QPaintEvent, QPainter, QMatrix4x4, QTransform, QPen, QMouseEvent, \
    QWheelEvent, QStaticText, QColor, QBrush
from PyQt6.QtWidgets import QWidget
import time
from math import sqrt

from PyQt6.QtCore import QTimer, QPoint, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget, QMainWindow

from PyQt6 import QtCore, QtGui, QtWidgets



class PropertyEvent(QObject):
    changed = pyqtSignal()
class LaserMachine():
    def __init__(self):
        self.__timer = QTimer()
        self.__timer.timeout.connect(self.__processOneThing)
        self.__laserState = MarkerState.HIDE
        self.__position = QPoint(0,0)
        self.__destination = QPoint(0,0)
        self.__isMoving = False;
        self.__maxSpeed = 5;
        self.__bounds = QSize(500, 500);
        self.laserStateChanged = PropertyEvent()
        self.positionChanged = PropertyEvent()
        self.destinationChanged = PropertyEvent()
        self.isMovingChanged = PropertyEvent()
        self.__nextMoveTime = 0
        self.__error = int(0);

    def __setIsMoving(self, value):
        self.__isMoving = value
        if(self.__isMoving):
            self.__timer.start()
        else:
            self.__timer.stop()
        self.isMovingChanged.changed.emit()

    def getLaserState(self) -> MarkerState: return self.__laserState

    def getPosition(self) -> QPoint: return self.__position

    def getDestination(self) -> QPoint: return self.__destination

    def getMaxSpeed(self) -> float: return self.__maxSpeed

    def getBounds(self) -> QSize: return self.__bounds

    def setDestination(self, x, y):
        self.__destination = QPoint(x, y)
        self.destinationChanged.changed.emit()
        self.__setIsMoving(True)

    def __setPosition(self, x, y):
        self.__position.setX(x)
        self.__position.setY(y)
        self.positionChanged.changed.emit()

    def __processOneThing(self):
        step_time = 1.0 / self.__maxSpeed;
        #deltaTime = time.time() - self.__lastTimerTick
        self.__lastTimerTick = time.time()
        print(self.__position)
        if self.__isMoving and self.__lastTimerTick > self.__nextMoveTime:
            self.__doMove()
            self.__nextMoveTime = self.__lastTimerTick + step_time

    def __doMove(self):
        x0 = self.__position.x()
        y0 = self.__position.y()
        x1 = self.__destination.x()
        y1 = self.__destination.y()
        steep = abs(y1 - y0) > abs(x1 - x0);
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
        if x0 > x1:
            x0, x1 = x1, x0
            y0, y1 = y1, y0

        dx : int = x1 - x0
        dy : int = abs(y1 - y0)
        self.__error = dx / 2
        ystep = 1 if y0 < y1 else -1
        y = y0
        x = self.__position.x()

        self.__error -= dy
        if self.__error < 0:
            y += ystep
            self.__error += dx
        self.__setPosition(y if steep else x, x if steep else y)
        if self.__position == self.__destination:
            self.__setIsMoving(False)

class StageViewSignals(QObject):
        mouseStageClicked = pyqtSignal(QPoint)
class QZoomStageView(QWidget):
    def __init__(self):
        super(QWidget, self).__init__()
        self.__zoom = 1
        self.__oldMousePosition = QPoint()
        self.setMouseTracking(True)
        self.__isInDragMode = False
        self.canvas = QImage()
        self.init_image(self.size())
        self.__markerPoint = QPoint()
        self.__markerState = MarkerState.OFF
        self.__cameraPosition = QPoint()
        self.__grid_size_ws = 1
        self.stageLimits = QSize(500, 500)
        self.signals = StageViewSignals()
        self.__holdTimer = QTimer()
        self.__holdTimer.setInterval(250)
        self.__holdTimer.timeout.connect(self.__hold_timer_timeout)
        self.points = []
        self.set_zoom(1)

    def showEvent(self, e) -> None:
        self.__cameraPosition = QPointF(0,
                                        0)  # QPointF(self.frameSize().width() * 0.5, self.frameSize().height() * 0.5)
        self.set_zoom(5)

    def setStageLimits(self, limits: QSize):
        self.stageLimits = limits
        self.init_image(limits)
        self.update()

    def setCurrentPosition(self, position: QPoint):
        self.__markerPoint = position
        self.points.append(position)
        self.update()

    def init_image(self, size: QSize):
        self.image = QImage(size.width(), size.height(), QImage.Format.Format_ARGB32)



    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.__oldMousePosition = e.position().toPoint()
            self.__holdTimer.start()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            if not self.__isInDragMode:
                self.moveToClick(e.pos())
            self.__holdTimer.stop()
            self.__isInDragMode = False


    def moveToClick(self, e: QPoint):
        matrix = QTransform()
        matrix.scale(self.__zoom, self.__zoom)  # инвертируем для привычной сетки осей
        matrix.translate(self.__cameraPosition.x(), self.__cameraPosition.y())  # - т.к зумили в -1 по y
        inverted, result = matrix.inverted()
        wx, wy = inverted.map(e.x(), e.y())
        self.signals.mouseStageClicked.emit(QPoint(wx, -wy))


    def __hold_timer_timeout(self):
        self.__isInDragMode = True

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self.__isInDragMode:
            deltaX = e.position().x() - self.__oldMousePosition.x()
            deltaY = e.position().y() - self.__oldMousePosition.y()
            self.__cameraPosition = self.__cameraPosition + QPointF(deltaX, deltaY) / self.__zoom
            self.update()
            self.__oldMousePosition = e.position().toPoint()

    def wheelEvent(self, e: QWheelEvent) -> None:
        steps = e.angleDelta().y()
        vector = steps and steps // abs(steps)
        self.set_zoom(max(0.1, self.__zoom * (1.1 if vector > 0 else 0.9)))
        self.update()

    def resizeEvent(self, e: QResizeEvent):
        self.init_image(e.size())

    def set_zoom(self, zoom):
        if zoom <= 0.1:
            zoom = 0.1
        old_zoom = self.__zoom
        self.__zoom = zoom

        matrix = QTransform()
        matrix.scale(self.__zoom, -self.__zoom)  # инвертируем для привычной сетки осей
        matrix.translate(self.__cameraPosition.x(), -self.__cameraPosition.y())  # - т.к зумили в -1 по y
        inverted, result = matrix.inverted()
        viewport_rect = self.rect()
        world_rect = inverted.mapRect(viewport_rect)
        top = world_rect.top()
        bottom = world_rect.bottom()
        left = world_rect.left()
        right = world_rect.right()

        length = min(max(self.stageLimits.width(), self.stageLimits.height()),
                     max(abs(top - bottom), abs(left - right)))
        major_step = 10
        self.__grid_size_ws, calculated_step = self.calc_step_size(length, major_step)
        # self.__grid_size_ws = 10

    @staticmethod
    def calc_step_size(range, targetSteps) -> float:
        tempStep = range / targetSteps
        mag = floor(log10(tempStep))
        magPow = 10.0 ** mag

        magMsd = int(tempStep / magPow + .5)

        if magMsd > 5.0:
            magMsd = 10.0
        elif magMsd > 2.0:
            magMsd = 5.0
        elif magMsd > 1.0:
            magMsd = 2.0

        return magMsd * magPow, magMsd

    def clamp(self, value, minvalue, maxvalue) -> float:
        return max(minvalue, min(value, maxvalue))

    def paintEvent(self, e: QPaintEvent):
        painter = QPainter(self)
        painter.fillRect(e.rect(), Qt.GlobalColor.darkBlue)
        painter.save()
        matrix = QTransform()
        matrix.scale(self.__zoom, self.__zoom)  # инвертируем для привычной сетки осей
        matrix.translate(self.__cameraPosition.x(), self.__cameraPosition.y())  # - т.к зумили в -1 по y
        painter.setWorldMatrixEnabled(True)
        painter.setWorldTransform(matrix, False)
        painter.setClipping(False)
        painter.setPen(QPen(Qt.GlobalColor.darkGray, 2.0 / self.__zoom))
        inverted, result = matrix.inverted()
        world_rect = inverted.mapRect(self.rect().toRectF())
        verticalBoundsTop = QPointF(0, world_rect.top())
        verticalBoundsBottom = QPointF(0, world_rect.bottom())
        horizontalBoundsLeft = QPointF(world_rect.left(), 0)
        horizontalBoundsRight = QPointF(world_rect.right(), 0)
        painter.drawLine(verticalBoundsTop, verticalBoundsBottom)  # vertical
        painter.drawLine(horizontalBoundsLeft, horizontalBoundsRight)  # horizontal

        painter.setPen(QPen(Qt.GlobalColor.darkGray, 1.0 / self.__zoom))

        max_h_limit = min(self.stageLimits.width(), world_rect.right())
        min_h_limit = max(0, world_rect.left())
        max_v_limit = max(-self.stageLimits.height(), world_rect.top())
        min_v_limit = min(0, world_rect.bottom())
        font = painter.font()

        font.setPointSizeF(12 / self.__zoom if self.__zoom > 1 else 12)
        painter.setFont(font)
        x = 0
        while x <= max_h_limit:  # vertical lines
            start = QPointF(x, min_v_limit)
            end = QPointF(x, max_v_limit)
            painter.drawLine(start, end)

            text = QStaticText(x.__str__())
            if x == 0:
                painter.drawStaticText(QPointF(x + 5.0 / self.__zoom, 0), text)
            else:
                painter.drawStaticText(QPointF(x - text.size().width() * 0.5 / self.__zoom, 0), text)
            x += self.__grid_size_ws

        y = 0
        while y >= max_v_limit:
            start = QPointF(min_h_limit, y)
            end = QPointF(max_h_limit, y)
            painter.drawLine(start, end)
            y -= self.__grid_size_ws

        marker_size = int(max(1, 10 / self.__zoom))

        for p in self.points:
            painter.fillRect(p.x(), p.y(), int(1), int(1), Qt.GlobalColor.yellow)

        painter.translate(-0.5 * marker_size, -0.5 * marker_size)
        print(f"mp: {self.__markerPoint}")
        if self.__markerState != MarkerState.HIDE:
            markerColor: QColor = Qt.GlobalColor.red if self.__markerState == MarkerState.ON else Qt.GlobalColor.yellow
            painter.setBrush(QBrush(markerColor))
            painter.drawEllipse(int(self.__markerPoint.x()), int(self.__markerPoint.y()), marker_size, marker_size)
        painter.translate(0.5 * marker_size, 0.5 * marker_size)
        painter.restore()
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawStaticText(QPointF(5, 10), QStaticText(f"Zoom: {self.__zoom : .2f}"))


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.image = QImage()
        self.userIsResizing = False
        self.resize(320, 240)
        self.init_image(self.size())
        self.stageView = QZoomStageView()
        self.setWindowTitle("My App")
        self.setCentralWidget(self.stageView)
        self.installEventFilter(self)
        self.__connectedMachine: LaserMachine = None
        self.stageView.signals.mouseStageClicked.connect(self.mouse_stage_clicked)

    def mouse_stage_clicked(self, wpos: QPoint):
        self.__connectedMachine.setDestination(wpos.x(), wpos.y())
    def connectMachine(self, machine : LaserMachine):
        if self.__connectedMachine is not None:
            self.__connectedMachine.positionChanged.changed.disconnected(self.machine_position_changed)
        self.__connectedMachine = machine
        self.__connectedMachine.positionChanged.changed.connect(self.machine_position_changed)
        self.stageView.setStageLimits(machine.getBounds())

    def machine_position_changed(self):
        self.stageView.setCurrentPosition(self.__connectedMachine.getPosition())

    def eventFilter(self, object, event) -> bool:
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton and self.userIsResizing:
            self.complete_resize()
        elif event.type() == QEvent.Type.NonClientAreaMouseButtonRelease and self.userIsResizing:
            self.complete_resize()
        return super().eventFilter(object, event)

    def resizeEvent(self, e) -> None:
        self.userIsResizing = True

    def complete_resize(self):
        self.userIsResizing = False
        self.init_image(self.size())
        self.update()

    def init_image(self, size: QSize):
        self.image = QImage(size.width(), size.height(), QImage.Format.Format_ARGB32)
'''
    def paintEvent(self, event):
        width = self.image.width()
        height = self.image.height()
        for x in range(width):
            for y in range(height):
                self.image.setPixel(x, y,
                                    QColor(255 - int(255 * x / width), int(255 * x / width), int(255 * y / height),
                                           255).rgb())
        painter = QPainter(self)
        painter.drawImage(QRectF(0, 0, width, height), self.image)
'''
def dest_changed():
    print(f"destination changed to {machine.getDestination()}")

app = QApplication([])

window = MainWindow()
window.show()
machine = LaserMachine()
window.connectMachine(machine)
machine.destinationChanged.changed.connect(dest_changed)
machine.setDestination(100, 30)
app.exec()
