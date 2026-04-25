import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, 
                             QSlider, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLineEdit, QGroupBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import FfmpegOutput
 
    #----
class DualCameraApp(QWidget): 
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Raspberry Pi Dual Camera Control Center")
        self.resize(900, 700)
        
        # [Key Optimization 1]: Hold instance variables to prevent frame GC and green screen
        self._current_frame_a = None
        self._current_frame_b = None
        
        # Initialize cameras
        self.cam_a = Picamera2(0)
        self.cam_b = Picamera2(1)
        self.init_cameras()
        
        # Recording state flag
        self.is_recording = False
        
        # Initialize GUI
        self.init_ui()
        
        # Timer for live frame refresh
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(33) # ~30 FPS
        
    def init_cameras(self):
        # Pass FrameRate directly as controls dict — compatible with newer picamera2
        config_a = self.cam_a.create_preview_configuration(
            main={"format": "BGR888", "size": (1280, 720)},
            controls={"FrameRate": 30.0}
        )
        self.cam_a.configure(config_a)
        self.cam_a.start()
        
        config_b = self.cam_b.create_preview_configuration(
            main={"format": "BGR888", "size": (1280, 720)},
            controls={"FrameRate": 30.0}
        )
        self.cam_b.configure(config_b)
        self.cam_b.start()
 
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # --- Video display area ---
        video_layout = QHBoxLayout()
        self.label_cam_a = QLabel("Camera A loading...")
        self.label_cam_a.setFixedSize(640, 480)
        self.label_cam_a.setStyleSheet("background-color: black; color: white;")
        
        self.label_cam_b = QLabel("Camera B loading...")
        self.label_cam_b.setFixedSize(640, 480)
        self.label_cam_b.setStyleSheet("background-color: black; color: white;")
        
        video_layout.addWidget(self.label_cam_a)
        video_layout.addWidget(self.label_cam_b)
        main_layout.addLayout(video_layout)
        
        # --- Controls and filename area ---
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("Save filename:"))
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("Enter base filename (e.g. test_run)")
        control_layout.addWidget(self.filename_input)
        
        self.btn_start = QPushButton("Start Recording")
        self.btn_stop = QPushButton("Stop Recording & Exit")
        self.btn_stop.setStyleSheet("background-color: #ff4c4c; color: white; font-weight: bold;")
        
        self.btn_start.clicked.connect(self.start_recording)
        self.btn_stop.clicked.connect(self.stop_and_exit)
        
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        main_layout.addLayout(control_layout)
        
        # --- Parameter controls (Exposure + Focus) ---
        params_layout = QHBoxLayout()
        
        # Camera A control group
        group_a = QGroupBox("Camera A Controls")
        grid_a = QGridLayout()
 
        # Exposure
        grid_a.addWidget(QLabel("Exposure:"), 0, 0)
        self.slider_exp_a = QSlider(Qt.Horizontal)
        self.slider_exp_a.setRange(1000, 30000) # microseconds
        self.slider_exp_a.valueChanged.connect(self.update_exposure_a)
        grid_a.addWidget(self.slider_exp_a, 0, 1)
 
        # Focus (LensPosition: 0.0=infinity, 10.0=close)
        grid_a.addWidget(QLabel("Focus:"), 1, 0)
        self.slider_focus_a = QSlider(Qt.Horizontal)
        self.slider_focus_a.setRange(0, 100)   # mapped to 0.0 ~ 10.0
        self.slider_focus_a.setValue(0)
        self.slider_focus_a.valueChanged.connect(self.update_focus_a)
        grid_a.addWidget(self.slider_focus_a, 1, 1)
 
        group_a.setLayout(grid_a)
        
        # Camera B control group
        group_b = QGroupBox("Camera B Controls")
        grid_b = QGridLayout()
 
        # Exposure
        grid_b.addWidget(QLabel("Exposure:"), 0, 0)
        self.slider_exp_b = QSlider(Qt.Horizontal)
        self.slider_exp_b.setRange(1000, 30000)
        self.slider_exp_b.valueChanged.connect(self.update_exposure_b)
        grid_b.addWidget(self.slider_exp_b, 0, 1)
 
        # Focus
        grid_b.addWidget(QLabel("Focus:"), 1, 0)
        self.slider_focus_b = QSlider(Qt.Horizontal)
        self.slider_focus_b.setRange(0, 100)   # mapped to 0.0 ~ 10.0
        self.slider_focus_b.setValue(0)
        self.slider_focus_b.valueChanged.connect(self.update_focus_b)
        grid_b.addWidget(self.slider_focus_b, 1, 1)
 
        group_b.setLayout(grid_b)
        
        params_layout.addWidget(group_a)
        params_layout.addWidget(group_b)
        main_layout.addLayout(params_layout)
        
        self.setLayout(main_layout)
 
    def update_frames(self):
        try:
            # Capture frames
            frame_a = self.cam_a.capture_array("main")
            frame_b = self.cam_b.capture_array("main")
            
            # [Key Optimization 3]: Assign to instance variables to extend lifetime,
            # preventing GC from freeing memory while C++ still holds a pointer.
            self._current_frame_a = frame_a
            self._current_frame_b = frame_b
            
            # Render instance variables
            self.display_image(self._current_frame_a, self.label_cam_a)
            self.display_image(self._current_frame_b, self.label_cam_b)
        except Exception as e:
            pass 
 
    def display_image(self, frame, label):
        h, w, ch = frame.shape
        bytes_per_line = frame.strides[0] 
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        label.setPixmap(QPixmap.fromImage(q_img).scaled(label.width(), label.height(), Qt.KeepAspectRatio))
 
    def start_recording(self):
        if not self.is_recording:
            base_name = self.filename_input.text().strip()
            if not base_name:
                base_name = "video"
                
            print(f"Recording started: {base_name}_a.mp4 and {base_name}_b.mp4")
            encoder_a = H264Encoder(bitrate=5000000)
            encoder_b = H264Encoder(bitrate=5000000)
            
            output_a = FfmpegOutput(f'{base_name}_a.mp4', audio=False) 
            output_b = FfmpegOutput(f'{base_name}_b.mp4', audio=False)
            
            self.cam_a.start_recording(encoder_a, output_a, quality=Quality.VERY_HIGH)
            self.cam_b.start_recording(encoder_b, output_b, quality=Quality.VERY_HIGH)
            
            self.is_recording = True
            self.btn_start.setEnabled(False)
            self.btn_start.setText("Recording...")
            self.filename_input.setEnabled(False)
 
    def stop_and_exit(self):
        print("Stopping recording and exiting...")
        if self.is_recording:
            self.cam_a.stop_recording()
            self.cam_b.stop_recording()
            self.is_recording = False
        self.close() 
 
    # --- Exposure control ---
    def update_exposure_a(self, value):
        self.cam_a.set_controls({"AeEnable": False, "ExposureTime": value})
 
    def update_exposure_b(self, value):
        self.cam_b.set_controls({"AeEnable": False, "ExposureTime": value})
 
    # --- Focus control ---
    # Pi Camera v3: AfMode=0 is manual, LensPosition 0.0 (infinity) ~ 10.0 (close)
    def update_focus_a(self, value):
        lens_position = value / 10.0  # slider 0~100 → LensPosition 0.0~10.0
        self.cam_a.set_controls({"AfMode": 0, "LensPosition": lens_position})
 
    def update_focus_b(self, value):
        lens_position = value / 10.0
        self.cam_b.set_controls({"AfMode": 0, "LensPosition": lens_position})
 
    def closeEvent(self, event):
        self.timer.stop()
        if self.is_recording:
            self.cam_a.stop_recording()
            self.cam_b.stop_recording()
        self.cam_a.stop()
        self.cam_b.stop()
        event.accept()
 
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DualCameraApp()
    window.show()
    sys.exit(app.exec_())
