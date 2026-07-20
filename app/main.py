import os
import cv2
from datetime import datetime

# Kivy / KivyMD imports
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import Snackbar

# Import our custom modules
from speech_handlers import SpeechHandler
from document_processing import auto_crop_document, enhance_document
from pdf_maker import create_pdf_from_images

KV = '''
<MainScreen>:
    MDBoxLayout:
        orientation: 'vertical'

        MDTopAppBar:
            title: "Smart Document Scanner"
            elevation: 2

        MDRelativeLayout:

            # The Camera Widget
            Camera:
                id: camera
                resolution: (640, 480)
                play: True
                allow_stretch: True
                keep_ratio: True

            # Overlay to display status and instructions
            MDBoxLayout:
                orientation: 'vertical'
                padding: "16dp"
                spacing: "8dp"

                MDLabel:
                    id: status_label
                    text: "Say 'go' or 'click' to capture.\\nSay 'finish' or 'end' to make PDF."
                    halign: "center"
                    theme_text_color: "Custom"
                    text_color: 1, 1, 1, 1
                    bold: True
                    font_style: "HeadlineSmall"
                    outline_color: 0, 0, 0, 1
                    outline_width: 2
                    size_hint_y: None
                    height: self.texture_size[1]

                Widget: # Spacer

            # Manual Controls (Bottom Right)
            MDBoxLayout:
                orientation: 'horizontal'
                size_hint: None, None
                size: "140dp", "60dp"
                pos_hint: {"right": 0.95, "y": 0.05}
                spacing: "10dp"

                MDFloatingActionButton:
                    icon: "camera"
                    on_release: app.capture_frame()
                    md_bg_color: app.theme_cls.primary_color

                MDFloatingActionButton:
                    icon: "file-pdf-box"
                    on_release: app.finish_and_make_pdf()
                    md_bg_color: app.theme_cls.error_color
'''

class MainScreen(MDScreen):
    pass

class SmartScannerApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.captured_images = []
        self.speech_handler = None
        self.is_listening = False
        self.session_dir = ""

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        Builder.load_string(KV)
        self.screen = MainScreen()
        return self.screen

    def on_start(self):
        # Create a directory for this session's images
        self.session_dir = os.path.join(self.user_data_dir, "scans")
        os.makedirs(self.session_dir, exist_ok=True)

        # Initialize Speech Handler
        self.speech_handler = SpeechHandler(self.on_speech_result)
        self.speech_handler.request_perms()

        # Start listening loop
        self.start_voice_listening()
        self.speech_handler.speak("Camera is ready. Say click or go to capture a photo.")

    def start_voice_listening(self):
        if not self.is_listening:
            self.speech_handler.start_listening()
            self.is_listening = True

    def stop_voice_listening(self):
        if self.is_listening:
            self.speech_handler.stop_listening()
            self.is_listening = False

    def on_speech_result(self, status, text):
        if status == "RESULT":
            print(f"Heard: {text}")
            if "click" in text or "go" in text or "capture" in text:
                Clock.schedule_once(lambda dt: self.capture_frame())
            elif "finish" in text or "end" in text or "done" in text:
                Clock.schedule_once(lambda dt: self.finish_and_make_pdf())

            # Restart listening if not finishing
            if not ("finish" in text or "end" in text or "done" in text):
                Clock.schedule_once(lambda dt: self.start_voice_listening(), 1)

        elif status == "ERROR":
            # Restart listening on error (e.g. no speech detected)
            Clock.schedule_once(lambda dt: self.start_voice_listening(), 1)

    def capture_frame(self):
        self.stop_voice_listening()
        self.speech_handler.speak("Clicking photo")
        self.update_status("Capturing & Processing...")

        # Get frame from Kivy Camera widget
        camera = self.screen.ids.camera
        if not camera.texture:
            self.update_status("Camera not ready!")
            self.start_voice_listening()
            return

        # Convert Kivy texture to OpenCV image (numpy array)
        texture = camera.texture
        size = texture.size
        pixels = texture.pixels

        import numpy as np
        # Kivy returns RGBA, reshape and convert
        img_np = np.frombuffer(pixels, dtype=np.uint8).reshape(size[1], size[0], 4)

        # OpenCV works with BGR, convert from RGBA to BGR
        # Also Kivy textures are flipped vertically
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        img_bgr = cv2.flip(img_bgr, 0)

        # Process the image
        cropped = auto_crop_document(img_bgr)
        enhanced = enhance_document(cropped)

        # Save processed image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.session_dir, f"scan_{timestamp}.jpg")
        cv2.imwrite(filename, enhanced)

        self.captured_images.append(filename)

        self.update_status(f"Captured {len(self.captured_images)} pages. Say 'go' for next.")
        self.speech_handler.speak("Photo processed. Say go for next page, or finish to make pdf.")

        # Resume listening
        Clock.schedule_once(lambda dt: self.start_voice_listening(), 2)

    def finish_and_make_pdf(self):
        self.stop_voice_listening()
        if not self.captured_images:
            self.update_status("No images captured.")
            self.speech_handler.speak("No images captured.")
            Clock.schedule_once(lambda dt: self.start_voice_listening(), 2)
            return

        self.update_status("Creating PDF...")
        self.speech_handler.speak("Creating PDF document")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(self.user_data_dir, f"Document_{timestamp}.pdf")

        success = create_pdf_from_images(self.captured_images, pdf_path)

        if success:
            msg = f"PDF saved: Document_{timestamp}.pdf"
            self.update_status(msg)
            self.speech_handler.speak("PDF created successfully.")
            Snackbar(text=msg).open()

            # Clear session
            self.captured_images.clear()
        else:
            self.update_status("Failed to create PDF.")
            self.speech_handler.speak("Failed to create PDF.")

        # Restart listening for a new session
        Clock.schedule_once(lambda dt: self.start_voice_listening(), 3)

    def update_status(self, text):
        self.screen.ids.status_label.text = text


if __name__ == '__main__':
    # When running on desktop, mock the speech recognition via console input loop in a thread
    import threading
    app = SmartScannerApp()

    def mock_voice_input():
        import time
        time.sleep(2) # wait for app to start
        while True:
            cmd = input("Simulate voice command ('go', 'finish'): ")
            if app.speech_handler:
                app.speech_handler.simulate_voice_command(cmd)

    if not ('ANDROID_ARGUMENT' in os.environ or 'ANDROID_BOOTLOGO' in os.environ):
        threading.Thread(target=mock_voice_input, daemon=True).start()

    app.run()
