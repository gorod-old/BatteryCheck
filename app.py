import os
import subprocess
from os.path import join

import schedule
from PyQt5 import QtGui

import design
from datetime import datetime
from time import sleep, perf_counter
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QListWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal, Qt

from AsyncProcessPack import AsyncProcess
from MessagePack import print_info_msg
from WinSoundPack import beep


class QTTimer(QThread):

    def __init__(self, app):
        super().__init__()
        self.start_time = 0
        self.last_time = 0
        self.app = app

    def run(self):
        self.start_time = perf_counter()
        self.last_time = perf_counter()
        self.app.startInLabel.setText(f"{datetime.now().strftime('%d/%m/%Y')} {datetime.now().strftime('%H:%M:%S')}")
        self.app.timeLabel.setText('00:00:00')
        while self.app.run:
            # check sleep mode:
            delta = perf_counter() - self.last_time
            if delta > 5:
                # sleep mode detected
                self.app.sleep = True
                self.app.close()
            # timer
            time = perf_counter() - self.start_time
            self.app.timeLabel.setText(self.app.convert_sec_to_time_string(time))
            self.last_time = perf_counter()
            sleep(1)
        print('stop timer')
        self.quit()


class ScheduleThread(QThread):
    about_time = pyqtSignal(int)

    def __init__(self, app):
        super().__init__()
        self.app = app
        print('start scheduler')

    def add_time(self, time: int):
        schedule.every(time).minutes.do(
            lambda: self.about_time.emit(time)
        )

    def run(self):
        while self.app.run:
            schedule.run_pending()
            sleep(1)
        schedule.jobs.clear()
        sleep(1)
        print('stop scheduler')
        self.quit()


class MainWindow(QMainWindow, design.Ui_MainWindow):

    def __init__(self, marker: str = ''):
        # Обязательно нужно вызвать метод супер класса
        QMainWindow.__init__(self)
        self.setupUi(self)

        # ToolTips stylesheet
        self.setStyleSheet("""QToolTip {
                            border: 1px solid black;
                            padding: 3px;
                            border-radius: 3px;
                            opacity: 200;
                        }""")

        self._run = False
        self._interval = 1
        self._interval_timer = None
        self._file_name = None
        self._dir_files = []
        self.sleep = False

        self.setWindowTitle(marker)  # Устанавливаем заголовок окна
        self.setWindowIcon(QtGui.QIcon('Images/Battery-Check.ico'))
        self.startInLabel.setText('00:00:0000 00:00')
        self.timeLabel.setText('00:00:00')
        self.startButton.clicked.connect(self._start_click)
        self.statusBar().showMessage("---created by AlGorodetskiy---v 1.0---")

    @property
    def run(self):
        return self._run

    @classmethod
    def convert_sec_to_time_string(cls, seconds):
        """ Convert time value in seconds to time data string - 00:00:00"""
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return "%02d:%02d:%02d" % (hour, minutes, seconds)

    def _start_click(self):
        if self._run:
            self._stop_click()
            return
        print('start')
        self._run = True
        # no sleep mode
        subprocess.call("powercfg -change -monitor-timeout-ac 0")
        subprocess.call("powercfg -change -disk-timeout-ac 0")
        subprocess.call("powercfg -change -standby-timeout-ac 0")
        # run scheduler
        self._i_timer()
        # run timer
        self.timer = QTTimer(self)
        self.timer.start()
        # set ui data
        AsyncProcess('reset UI', self._reset_ui, 1, (self, '_end_reset_ui'))

    def _stop_click(self):
        print('stop')
        beep()
        self._run = False
        self.startButton.setText('Start')
        self.startInLabel.setText('00:00:0000 00:00')
        self.timeLabel.setText('00:00:00')
        self._delete_file()

    def closeEvent(self, event):
        print('close event')
        if self.sleep:
            event.accept()
            return
        if self._run:
            button = QMessageBox.question(self, "Внимание!", "Текущий тест будет прерван! Продолжить?")
            if button == QMessageBox.Yes:
                self._stop_click()
                sleep(10)
                event.accept()
            else:
                event.ignore()

    def _i_timer(self):
        self._interval_timer = ScheduleThread(self)
        self._interval_timer.about_time.connect(self.check_time)
        self._interval_timer.add_time(self._interval)
        self._interval_timer.start()

    def _reset_ui(self):
        self.startButton.setText('Stop')
        self._check_dir()
        self._create_file()

    def _end_reset_ui(self):
        self._run_app()

    def _run_app(self):
        if not self._run:
            return
        beep()
        self.start = datetime.now().strftime('%H:%M:%S')

    def check_time(self):
        sleep(1)
        path = os.getcwd()
        name = self._get_file_name() + '.txt'
        if self._file_name is None:
            return
        file_old = os.path.join(path, self._file_name)
        file_new = os.path.join(path, name)
        os.rename(file_old, file_new)
        self._file_name = name

    def _get_file_name(self):
        now = datetime.now().strftime('%H:%M:%S')
        time_1 = f"{self.start.split(':')[0]}-{self.start.split(':')[1]}"
        time_2 = f"{now.split(':')[0]}-{now.split(':')[1]}"
        time = f"({self.timeLabel.text().split(':')[0]}-{self.timeLabel.text().split(':')[1]})"
        name = f"{self.num}_{time_1}--{time_2} {time}"
        print(name)
        return name

    def _check_dir(self):
        path = os.getcwd()
        print(os.listdir(path))
        for file in os.listdir(path):
            if file.endswith(".txt"):
                try:
                    print(file)
                    self._dir_files.append(int(file.split('_')[0]))
                except Exception as e:
                    print(str(e))

    def _get_file_num(self):
        print(self._dir_files)
        i = 0
        while True:
            i += 1
            if i not in self._dir_files:
                return i

    def _create_file(self):
        if self._file_name is None:
            self.num = self._get_file_num()
            path = os.getcwd()
            now = datetime.now().strftime('%H:%M:%S')
            self._file_name = f"{self.num}_{now.split(':')[0]}-{now.split(':')[1]}--.txt"
            file = open(join(path, self._file_name), 'w')  # Trying to create a new file or open one
            file.close()

    def _delete_file(self):
        path = os.getcwd()
        os.remove(join(path, self._file_name))


