import flet as ft
import cv2
import pyaudio
import wave
import threading
import time
import os
from datetime import datetime
import numpy as np
from PIL import ImageGrab
import subprocess
import sys

# Install required packages if not available
def install_requirements():
    packages = ['opencv-python', 'pyaudio', 'pillow', 'numpy']
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

class ScreenRecorder:
    def __init__(self):
        self.recording = False
        self.camera_active = False
        self.audio_recording = False
        self.output_dir = "recordings"
        self.current_filename = None
        self.video_writer = None
        self.audio_frames = []
        self.audio_stream = None
        self.camera_cap = None
        self.camera_window = None
        
        # Audio settings
        self.audio_format = pyaudio.paInt16
        self.channels = 2
        self.rate = 44100
        self.chunk = 1024
        self.audio = pyaudio.PyAudio()
        
        # Create output directory
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def generate_filename(self, extension):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"recording_{timestamp}.{extension}")
    
    def start_screen_recording(self):
        if self.recording:
            return False
        
        self.recording = True
        self.current_filename = self.generate_filename("avi")
        
        # Get screen dimensions
        screen = ImageGrab.grab()
        screen_width, screen_height = screen.size
        
        # Setup video writer
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(
            self.current_filename, 
            fourcc, 
            20.0, 
            (screen_width, screen_height)
        )
        
        # Start recording thread
        self.recording_thread = threading.Thread(target=self._record_screen)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        return True
    
    def _record_screen(self):
        while self.recording:
            # Capture screen
            screen = ImageGrab.grab()
            frame = np.array(screen)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Write frame
            if self.video_writer:
                self.video_writer.write(frame)
            
            time.sleep(0.05)  # 20 FPS
    
    def stop_screen_recording(self):
        if not self.recording:
            return False
        
        self.recording = False
        
        # Wait for recording thread to finish
        if hasattr(self, 'recording_thread'):
            self.recording_thread.join()
        
        # Release video writer
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        return True
    
    def start_audio_recording(self):
        if self.audio_recording:
            return False
        
        self.audio_recording = True
        self.audio_frames = []
        
        # Start audio stream
        self.audio_stream = self.audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        # Start audio recording thread
        self.audio_thread = threading.Thread(target=self._record_audio)
        self.audio_thread.daemon = True
        self.audio_thread.start()
        
        return True
    
    def _record_audio(self):
        while self.audio_recording:
            try:
                data = self.audio_stream.read(self.chunk)
                self.audio_frames.append(data)
            except Exception as e:
                print(f"Audio recording error: {e}")
                break
    
    def stop_audio_recording(self):
        if not self.audio_recording:
            return False
        
        self.audio_recording = False
        
        # Wait for audio thread to finish
        if hasattr(self, 'audio_thread'):
            self.audio_thread.join()
        
        # Stop and close audio stream
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        
        # Save audio file
        if self.audio_frames:
            audio_filename = self.generate_filename("wav")
            with wave.open(audio_filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.audio_frames))
        
        return True
    
    def start_camera(self):
        if self.camera_active:
            return False
        
        try:
            self.camera_cap = cv2.VideoCapture(0)
            if not self.camera_cap.isOpened():
                return False
            
            self.camera_active = True
            
            # Start camera thread
            self.camera_thread = threading.Thread(target=self._show_camera)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            
            return True
        except Exception as e:
            print(f"Camera error: {e}")
            return False
    
    def _show_camera(self):
        while self.camera_active and self.camera_cap:
            ret, frame = self.camera_cap.read()
            if ret:
                cv2.imshow('Camera Preview', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break
        
        cv2.destroyAllWindows()
    
    def stop_camera(self):
        if not self.camera_active:
            return False
        
        self.camera_active = False
        
        # Wait for camera thread to finish
        if hasattr(self, 'camera_thread'):
            self.camera_thread.join()
        
        # Release camera
        if self.camera_cap:
            self.camera_cap.release()
            self.camera_cap = None
        
        cv2.destroyAllWindows()
        return True
    
    def cleanup(self):
        self.stop_screen_recording()
        self.stop_audio_recording()
        self.stop_camera()
        self.audio.terminate()

def main(page: ft.Page):
    page.title = "Professional Screen Recorder"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 800
    page.window_height = 600
    page.window_resizable = True
    
    # Initialize recorder
    recorder = ScreenRecorder()
    
    # Status indicators
    recording_status = ft.Text("Ready", color=ft.colors.GREEN, size=16, weight=ft.FontWeight.BOLD)
    audio_status = ft.Text("Audio: Off", color=ft.colors.RED, size=14)
    camera_status = ft.Text("Camera: Off", color=ft.colors.RED, size=14)
    
    # Control buttons
    def toggle_recording(e):
        if not recorder.recording:
            # Start recording
            if recorder.start_screen_recording():
                recording_status.value = "Recording..."
                recording_status.color = ft.colors.RED
                record_btn.text = "Stop Recording"
                record_btn.icon = ft.icons.STOP
                record_btn.color = ft.colors.RED
            else:
                recording_status.value = "Failed to start recording"
                recording_status.color = ft.colors.ORANGE
        else:
            # Stop recording
            if recorder.stop_screen_recording():
                recording_status.value = "Recording saved"
                recording_status.color = ft.colors.GREEN
                record_btn.text = "Start Recording"
                record_btn.icon = ft.icons.VIDEOCAM
                record_btn.color = ft.colors.BLUE
        page.update()
    
    def toggle_audio(e):
        if not recorder.audio_recording:
            # Start audio recording
            if recorder.start_audio_recording():
                audio_status.value = "Audio: Recording"
                audio_status.color = ft.colors.GREEN
                audio_btn.text = "Stop Audio"
                audio_btn.icon = ft.icons.MIC_OFF
                audio_btn.color = ft.colors.RED
            else:
                audio_status.value = "Audio: Failed"
                audio_status.color = ft.colors.ORANGE
        else:
            # Stop audio recording
            if recorder.stop_audio_recording():
                audio_status.value = "Audio: Saved"
                audio_status.color = ft.colors.BLUE
                audio_btn.text = "Start Audio"
                audio_btn.icon = ft.icons.MIC
                audio_btn.color = ft.colors.GREEN
        page.update()
    
    def toggle_camera(e):
        if not recorder.camera_active:
            # Start camera
            if recorder.start_camera():
                camera_status.value = "Camera: Active"
                camera_status.color = ft.colors.GREEN
                camera_btn.text = "Stop Camera"
                camera_btn.icon = ft.icons.VIDEOCAM_OFF
                camera_btn.color = ft.colors.RED
            else:
                camera_status.value = "Camera: Failed"
                camera_status.color = ft.colors.ORANGE
        else:
            # Stop camera
            if recorder.stop_camera():
                camera_status.value = "Camera: Off"
                camera_status.color = ft.colors.RED
                camera_btn.text = "Start Camera"
                camera_btn.icon = ft.icons.VIDEOCAM
                camera_btn.color = ft.colors.BLUE
        page.update()
    
    def open_recordings_folder(e):
        import platform
        import subprocess
        
        if platform.system() == "Windows":
            os.startfile(recorder.output_dir)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", recorder.output_dir])
        else:  # Linux
            subprocess.run(["xdg-open", recorder.output_dir])
    
    # Create buttons
    record_btn = ft.ElevatedButton(
        text="Start Recording",
        icon=ft.icons.VIDEOCAM,
        on_click=toggle_recording,
        color=ft.colors.BLUE,
        width=200,
        height=50
    )
    
    audio_btn = ft.ElevatedButton(
        text="Start Audio",
        icon=ft.icons.MIC,
        on_click=toggle_audio,
        color=ft.colors.GREEN,
        width=200,
        height=50
    )
    
    camera_btn = ft.ElevatedButton(
        text="Start Camera",
        icon=ft.icons.VIDEOCAM,
        on_click=toggle_camera,
        color=ft.colors.BLUE,
        width=200,
        height=50
    )
    
    folder_btn = ft.ElevatedButton(
        text="Open Recordings",
        icon=ft.icons.FOLDER_OPEN,
        on_click=open_recordings_folder,
        color=ft.colors.PURPLE,
        width=200,
        height=50
    )
    
    # Create layout
    page.add(
        ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Column([
                        ft.Text("Professional Screen Recorder", 
                               size=24, 
                               weight=ft.FontWeight.BOLD,
                               text_align=ft.TextAlign.CENTER),
                        ft.Text("Record screen, audio, and camera simultaneously", 
                               size=14, 
                               color=ft.colors.GREY_400,
                               text_align=ft.TextAlign.CENTER),
                    ]),
                    padding=20,
                    alignment=ft.alignment.center
                ),
                
                # Status section
                ft.Container(
                    content=ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("Status", size=18, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                recording_status,
                                audio_status,
                                camera_status,
                            ]),
                            padding=20
                        )
                    ),
                    padding=ft.padding.symmetric(horizontal=20)
                ),
                
                # Controls section
                ft.Container(
                    content=ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("Controls", size=18, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                ft.Row([
                                    record_btn,
                                    audio_btn,
                                ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                                ft.Row([
                                    camera_btn,
                                    folder_btn,
                                ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                            ]),
                            padding=20
                        )
                    ),
                    padding=ft.padding.symmetric(horizontal=20)
                ),
                
                # Instructions section
                ft.Container(
                    content=ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("Instructions", size=18, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                ft.Text("• Click 'Start Recording' to begin screen capture", size=12),
                                ft.Text("• Click 'Start Audio' to record system/microphone audio", size=12),
                                ft.Text("• Click 'Start Camera' to open camera preview window", size=12),
                                ft.Text("• All recordings are saved in the 'recordings' folder", size=12),
                                ft.Text("• Press 'q' in camera window to close it", size=12),
                            ]),
                            padding=20
                        )
                    ),
                    padding=ft.padding.symmetric(horizontal=20)
                ),
            ]),
            expand=True
        )
    )
    
    # Cleanup on close
    def on_window_event(e):
        if e.data == "close":
            recorder.cleanup()
            page.window_destroy()
    
    page.window_prevent_close = True
    page.on_window_event = on_window_event

if __name__ == "__main__":
    # Install requirements first
    try:
        install_requirements()
    except Exception as e:
        print(f"Warning: Could not install some requirements: {e}")
    
    ft.app(target=main)