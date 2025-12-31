import speech_recognition as sr

class SpeechEngine:
    def listen(self, timeout=6, lang="hi-IN"):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            audio = r.listen(source, timeout=timeout)
        try:
            text = r.recognize_google(audio, language=lang)
            return text
        except sr.UnknownValueError:
            raise Exception("Could not understand audio")
        except sr.RequestError:
            raise Exception("Speech Service Unavailable")