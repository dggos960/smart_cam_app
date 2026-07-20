import os

# Check if running on Android
IS_ANDROID = 'ANDROID_ARGUMENT' in os.environ or 'ANDROID_BOOTLOGO' in os.environ

if IS_ANDROID:
    from jnius import autoclass, PythonJavaClass, java_method
    from android.permissions import request_permissions, Permission

    # Import Android classes
    Locale = autoclass('java.util.Locale')
    Intent = autoclass('android.content.Intent')
    RecognizerIntent = autoclass('android.speech.RecognizerIntent')
    SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
    TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

    class TTSInitListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
        __javacontext__ = 'app'

        def __init__(self, tts_instance, **kwargs):
            super().__init__(**kwargs)
            self.tts_instance = tts_instance

        @java_method('(I)V')
        def onInit(self, status):
            if status == TextToSpeech.SUCCESS:
                self.tts_instance.setLanguage(Locale.US)

    class VoiceRecognitionListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/RecognitionListener']
        __javacontext__ = 'app'

        def __init__(self, callback, **kwargs):
            super().__init__(**kwargs)
            self.callback = callback

        @java_method('(Landroid/os/Bundle;)V')
        def onReadyForSpeech(self, params):
            pass

        @java_method('()V')
        def onBeginningOfSpeech(self):
            pass

        @java_method('(F)V')
        def onRmsChanged(self, rmsdB):
            pass

        @java_method('([B)V')
        def onBufferReceived(self, buffer):
            pass

        @java_method('()V')
        def onEndOfSpeech(self):
            pass

        @java_method('(I)V')
        def onError(self, error):
            if self.callback:
                self.callback("ERROR", error)

        @java_method('(Landroid/os/Bundle;)V')
        def onResults(self, results):
            matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            if matches and matches.size() > 0:
                recognized_text = matches.get(0).lower()
                if self.callback:
                    self.callback("RESULT", recognized_text)

        @java_method('(Landroid/os/Bundle;)V')
        def onPartialResults(self, partialResults):
            pass

        @java_method('(ILandroid/os/Bundle;)V')
        def onEvent(self, eventType, params):
            pass


    from android.runnable import run_on_ui_thread

    class SpeechHandler:
        def __init__(self, callback):
            self.activity = PythonActivity.mActivity
            self.callback = callback

            # Setup TTS
            self.tts_init_listener = TTSInitListener(None)
            self.tts = TextToSpeech(self.activity, self.tts_init_listener)
            self.tts_init_listener.tts_instance = self.tts

            # Setup STT - Must be initialized on UI thread
            self._setup_stt()

        @run_on_ui_thread
        def _setup_stt(self):
            self.listener = VoiceRecognitionListener(self.handle_speech_result)
            self.recognizer = SpeechRecognizer.createSpeechRecognizer(self.activity)
            self.recognizer.setRecognitionListener(self.listener)

            self.intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            self.intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            self.intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())

        def handle_speech_result(self, status, text):
            self.callback(status, text)

        @run_on_ui_thread
        def start_listening(self):
            self.recognizer.startListening(self.intent)

        @run_on_ui_thread
        def stop_listening(self):
            self.recognizer.stopListening()

        def speak(self, text):
            # QUEUE_FLUSH = 0
            self.tts.speak(text, 0, None, None)

        def request_perms(self):
            request_permissions([
                Permission.RECORD_AUDIO,
                Permission.CAMERA,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE
            ])

else:
    # Mock implementation for non-Android environments
    class SpeechHandler:
        def __init__(self, callback):
            print("SpeechHandler Mock Initialized")
            self.callback = callback

        def start_listening(self):
            print("SpeechHandler Mock: Listening...")

        def stop_listening(self):
            print("SpeechHandler Mock: Stopped Listening")

        def speak(self, text):
            print(f"SpeechHandler Mock Speaking: {text}")

        def request_perms(self):
            print("SpeechHandler Mock: Requesting Permissions")

        def simulate_voice_command(self, text):
            """Helper function to simulate voice commands in desktop environment"""
            print(f"Simulating voice command: {text}")
            if self.callback:
                self.callback("RESULT", text.lower())
