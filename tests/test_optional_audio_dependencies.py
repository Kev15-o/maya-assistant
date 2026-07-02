import builtins
import importlib
import sys
import unittest
from unittest import mock


class OptionalAudioDependenciesTest(unittest.TestCase):
    def test_speak_falls_back_when_optional_audio_deps_are_unavailable(self):
        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in {"edge_tts", "pygame", "pyjokes", "speech_recognition", "wikipedia"}:
                raise ImportError("simulated missing optional dependency")
            return real_import(name, globals, locals, fromlist, level)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            sys.modules.pop("assistant", None)
            assistant = importlib.import_module("assistant")

            self.assertFalse(assistant._has_voice_runtime())
            self.assertIsNone(assistant.speak("hello"))


if __name__ == "__main__":
    unittest.main()
