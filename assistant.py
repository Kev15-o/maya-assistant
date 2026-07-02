import warnings

warnings.filterwarnings("ignore", category=UserWarning)

import asyncio
import ast
import datetime
import os
import random
import re
import subprocess
import threading
import time
import webbrowser

import edge_tts
import pygame
import pyjokes
import requests
import speech_recognition as sr
import wikipedia

from state import state

# --- Global State Variables ---
is_running = True
is_sleeping = False
active_speech_thread = None

ASSISTANT_NAME = "Maya"
USER_TITLE = "boss"
WEATHER_CITY = "Kochi"
NOTES_FILE = "maya_notes.txt"

NOTE_COMMANDS = [
    "remember that",
    "take a note",
    "take notes",
    "make a note",
    "make notes",
    "note that",
    "save note",
    "save a note",
    "write this down",
    "write down",
]

READ_NOTE_COMMANDS = [
    "read my notes",
    "show my notes",
    "what are my notes",
    "tell me my notes",
    "read notes",
    "show notes",
]

CLEAR_NOTE_COMMANDS = [
    "clear my notes",
    "delete my notes",
    "clear notes",
    "delete notes",
]

CALCULATION_COMMANDS = [
    "calculate",
    "calculation",
    "do calculation",
    "do calculations",
    "solve",
    "what is",
    "what's",
    "whats",
]

NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
    "thirty": "30",
    "forty": "40",
    "fifty": "50",
    "sixty": "60",
    "seventy": "70",
    "eighty": "80",
    "ninety": "90",
    "hundred": "100",
}

VOICE_CHOICES = [
    {"voice": "en-US-EmmaNeural", "rate": "+5%", "pitch": "+0Hz"},
    {"voice": "en-US-JennyNeural", "rate": "+3%", "pitch": "+2Hz"},
    {"voice": "en-GB-SoniaNeural", "rate": "+4%", "pitch": "+0Hz"},
]

RESPONSE_BANK = {
    "ack": [
        "On it, boss.",
        "Right away, boss.",
        "Absolutely, boss.",
        "Got it, boss.",
        "Consider it handled, boss.",
    ],
    "thinking": [
        "Let me check that for you, boss.",
        "Give me a moment, boss.",
        "I am looking into it now, boss.",
        "Working on that, boss.",
    ],
    "not_heard": [
        "I missed that, boss. Say it once more.",
        "I did not catch the command clearly, boss.",
        "The audio was a little muddy, boss. Please repeat that.",
    ],
    "fallback": [
        "I am not fully sure how to do that yet, boss. Try asking for the time, weather, a note, a reminder, a calculation, a joke, or a search.",
        "That one is outside my current command set, boss, but I can still help with weather, notes, reminders, calculations, web searches, and quick facts.",
        "I heard you, boss, but I do not have a clean action for that yet. Ask what I can do and I will list my tools.",
    ],
    "hello": [
        "Welcome back, boss. What are we tackling?",
        "Hello, boss. I am online and ready.",
        "Hey boss. Give me the mission.",
        "Hi boss. Systems are steady and I am listening.",
    ],
    "presence": [
        "Always here, boss.",
        "At your command, boss.",
        "Yes boss, I am listening.",
        "Online, alert, and ready, boss.",
    ],
    "sleep": [
        "Going to standby, boss. Say wake up when you need me.",
        "Understood, boss. I will stay quiet until you wake me.",
        "Standby mode engaged, boss.",
        "Powering down my voice loop for now, boss.",
    ],
    "wake": [
        "I am back online, boss.",
        "Ready and waiting, boss.",
        "System fully operational, boss.",
        "At your service again, boss.",
    ],
    "exit": [
        "Goodbye, boss.",
        "Signing off, boss. Have a strong day.",
        "Session ending, boss. I will be here when you need me.",
        "Standing down, boss.",
    ],
}


def say_variant(key, *extra_parts):
    """Speak a varied canned response, optionally followed by details."""
    parts = [random.choice(RESPONSE_BANK[key]), *[part for part in extra_parts if part]]
    speak(" ".join(parts))


def ensure_boss(text):
    """Keep the assistant's address style consistent without making every line awkward."""
    if USER_TITLE in text.lower():
        return text

    closers = [
        f", {USER_TITLE}.",
        f", {USER_TITLE}.",
        f" for you, {USER_TITLE}.",
    ]
    clean = text.strip()
    if clean.endswith((".", "!", "?")):
        clean = clean[:-1]
    return clean + random.choice(closers)


def clean_query(query):
    return query.lower().strip()


def remove_command_words(query, words):
    cleaned = query
    for word in words:
        cleaned = cleaned.replace(word, "")
    return cleaned.strip(" .?!")


def set_idle_message():
    state.update(mode="wake", sys_text="SYSTEM ONLINE", message="Online and ready.")


def contains_any(query, phrases):
    return any(phrase in query for phrase in phrases)


def normalize_spoken_math(query):
    expression = remove_command_words(query, CALCULATION_COMMANDS)
    replacements = {
        "plus": "+",
        "add": "+",
        "minus": "-",
        "subtract": "-",
        "times": "*",
        "multiplied by": "*",
        "multiply by": "*",
        "into": "*",
        "x": "*",
        "divided by": "/",
        "divide by": "/",
        "over": "/",
        "point": ".",
        "open bracket": "(",
        "close bracket": ")",
        "open parenthesis": "(",
        "close parenthesis": ")",
    }

    for spoken, symbol in replacements.items():
        if spoken == "x":
            expression = re.sub(r"\bx\b", f" {symbol} ", expression)
        else:
            expression = expression.replace(spoken, f" {symbol} ")

    words = []
    for word in re.findall(r"\d+\.\d+|\d+|[a-z]+|[+\-*/().]", expression):
        words.append(NUMBER_WORDS.get(word, word))

    return " ".join(words).strip()


def is_math_query(query):
    explicit_math_commands = [
        "calculate",
        "calculation",
        "do calculation",
        "do calculations",
        "solve",
    ]
    if contains_any(query, explicit_math_commands):
        return True
    return bool(re.search(r"(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten)\s*(plus|minus|times|divided by|\+|\-|\*|/)\s*(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten)", query))


def safe_eval_math(expression):
    allowed_ops = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.Pow: lambda a, b: a**b,
        ast.USub: lambda a: -a,
        ast.UAdd: lambda a: a,
    }

    def eval_node(node):
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](eval_node(node.left), eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](eval_node(node.operand))
        raise ValueError("Unsupported calculation")

    parsed = ast.parse(expression, mode="eval")
    return eval_node(parsed)


def speak(audio):
    """Speaks the audio text in a non-blocking thread and mirrors it to the UI."""
    global active_speech_thread

    audio = ensure_boss(audio)

    if (
        active_speech_thread
        and active_speech_thread.is_alive()
        and threading.current_thread() is not active_speech_thread
    ):
        active_speech_thread.join()

    def run_speech():
        async def amain():
            try:
                filename = "speech.mp3"
                voice = random.choice(VOICE_CHOICES)
                communicate = edge_tts.Communicate(
                    audio,
                    voice["voice"],
                    rate=voice["rate"],
                    pitch=voice["pitch"],
                )

                if os.path.exists(filename):
                    try:
                        pygame.mixer.music.unload()
                        os.remove(filename)
                    except Exception:
                        pass

                await communicate.save(filename)
                pygame.mixer.init()
                pygame.mixer.music.load(filename)
                print(f"maya: {audio}")
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)

                pygame.mixer.music.unload()
                try:
                    os.remove(filename)
                except Exception:
                    pass
            except Exception as e:
                print(f"Voice Error: {e}")

        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        new_loop.run_until_complete(amain())
        new_loop.close()

    state.update(
        mode="speaking",
        sys_text="VOICE OUTPUT ACTIVE",
        message=audio,
        last_reply=audio,
    )

    speech_thread = threading.Thread(target=run_speech, daemon=True)
    speech_thread.start()
    active_speech_thread = speech_thread
    return speech_thread


def get_weather(return_text=False):
    """Fetches structured weather from wttr.in and pushes it to the shared state."""
    try:
        url = f"https://wttr.in/{WEATHER_CITY}?format=j1"
        response = requests.get(url, timeout=6)
        response.raise_for_status()
        data = response.json()
        current = data["current_condition"][0]
        temp_c = current["temp_C"]
        feels_like = current.get("FeelsLikeC", temp_c)
        condition = current["weatherDesc"][0]["value"]
        humidity = current.get("humidity")

        state.update(weather_temp=f"{temp_c} C", weather_cond=condition)

        details = (
            f"The weather in {WEATHER_CITY} is {condition}, {temp_c} degrees celsius, "
            f"feeling like {feels_like}. Humidity is {humidity} percent."
        )
        if return_text:
            return details
        speak(details)
    except Exception:
        state.update(weather_temp="-", weather_cond="Sensor offline")
        if return_text:
            return ""
        speak("I could not reach the weather service right now.")


def wishMe():
    hour = int(datetime.datetime.now().hour)
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    weather_info = get_weather(return_text=True)
    opening = random.choice(
        [
            f"{greeting}, {USER_TITLE}. {ASSISTANT_NAME} is online.",
            f"{greeting}, {USER_TITLE}. I am awake and ready.",
            f"{greeting}, {USER_TITLE}. Systems are live.",
        ]
    )
    speak(f"{opening} {weather_info} What do you need?")


def listen_for_wake_word():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Sleeping...")
        try:
            audio = r.listen(source, timeout=2, phrase_time_limit=2)
            query = r.recognize_google(audio, language="en-in").lower()
            return "wake up" in query or "maya" in query
        except Exception:
            return False


def takeCommand():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        r.pause_threshold = 0.8
        r.dynamic_energy_threshold = True
        try:
            audio = r.listen(source, timeout=9, phrase_time_limit=10)
            query = r.recognize_google(audio, language="en-in")
            print(f"User: {query}")
            return clean_query(query)
        except Exception:
            return "none"


def tell_time():
    time_str = datetime.datetime.now().strftime("%I:%M %p").lstrip("0")
    replies = [
        f"It is {time_str}",
        f"Right now it is {time_str}",
        f"The current time is {time_str}",
        f"My clock says {time_str}",
    ]
    speak(random.choice(replies))


def tell_date():
    today = datetime.datetime.now()
    date_str = today.strftime("%A, %B %d, %Y")
    replies = [
        f"Today is {date_str}",
        f"It is {date_str}",
        f"Calendar check: {date_str}",
    ]
    speak(random.choice(replies))


def tell_day():
    speak(f"Today is {datetime.datetime.now().strftime('%A')}")


def tell_capabilities():
    speak(
        "I can speak with you, tell the time, date, day, and weather, crack jokes, "
        "search Wikipedia, open websites, launch common Windows apps, save notes, "
        "read your notes, clear notes, set spoken reminders, calculate simple math, "
        "and go into standby."
    )


def search_wikipedia(query):
    search_query = remove_command_words(
        query,
        ["what is", "who is", "meaning of", "define", "search wikipedia for", "search for", "tell me about"],
    )
    if not search_query:
        speak("Tell me what you want me to search.")
        return

    say_variant("thinking")
    try:
        wikipedia.set_lang("en")
        results = wikipedia.summary(search_query, sentences=2, auto_suggest=True)
        speak(random.choice(["Here is what I found. ", "Short version. ", "According to my lookup. "]) + results)
    except wikipedia.DisambiguationError as e:
        options = ", ".join(e.options[:4])
        speak(f"That can mean a few things: {options}. Be more specific and I will narrow it down.")
    except Exception:
        speak("I could not find a reliable summary for that.")


def tell_joke():
    intro = random.choice(["Here comes one.", "Tiny comedy packet arriving.", "Brace yourself."])
    speak(f"{intro} {pyjokes.get_joke()}")


def save_note(query):
    note = remove_command_words(query, NOTE_COMMANDS)
    if not note:
        speak("What should I write down?")
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
    with open(NOTES_FILE, "a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {note}\n")
    speak(random.choice(["Saved it.", "I wrote that down.", "Note captured."]))


def read_notes():
    if not os.path.exists(NOTES_FILE) or os.path.getsize(NOTES_FILE) == 0:
        speak("You do not have any saved notes yet.")
        return

    with open(NOTES_FILE, "r", encoding="utf-8") as file:
        notes = [line.strip() for line in file.readlines() if line.strip()]

    recent = notes[-3:]
    speak("Here are your latest notes. " + " ".join(recent))


def clear_notes():
    with open(NOTES_FILE, "w", encoding="utf-8"):
        pass
    speak("All saved notes are cleared.")


def set_reminder(query):
    reminder = remove_command_words(query, ["remind me to", "set reminder to", "set a reminder to", "reminder"])
    if not reminder:
        speak("What should I remind you about?")
        return

    minutes_match = re.search(r"in (\d+) minutes?", reminder)
    seconds_match = re.search(r"in (\d+) seconds?", reminder)
    delay = None
    if minutes_match:
        delay = int(minutes_match.group(1)) * 60
        reminder = re.sub(r"in \d+ minutes?", "", reminder).strip()
    elif seconds_match:
        delay = int(seconds_match.group(1))
        reminder = re.sub(r"in \d+ seconds?", "", reminder).strip()

    if not delay:
        speak("I can set reminders by seconds or minutes for now. For example, remind me to check tea in 5 minutes.")
        return

    def reminder_worker():
        time.sleep(delay)
        speak(f"Reminder: {reminder}")

    threading.Thread(target=reminder_worker, daemon=True).start()
    speak(f"Reminder set for {reminder}.")


def calculate(query):
    expression = normalize_spoken_math(query)
    if not expression or not re.fullmatch(r"[0-9+\-*/().\s]+", expression):
        speak("I can only calculate simple number expressions right now.")
        return

    try:
        result = safe_eval_math(expression)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        speak(f"The answer is {result}")
    except Exception:
        speak("I could not calculate that cleanly.")


def open_website(query):
    sites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "github": "https://github.com",
        "chatgpt": "https://chatgpt.com",
        "whatsapp": "https://web.whatsapp.com",
    }
    for name, url in sites.items():
        if name in query:
            webbrowser.open(url)
            speak(f"Opening {name}")
            return

    match = re.search(r"open (.+)", query)
    if match:
        target = match.group(1).strip().replace(" ", "")
        if "." in target:
            webbrowser.open(f"https://{target}")
            speak(f"Opening {target}")
            return

    speak("Tell me which website to open.")


def is_app_request(query):
    app_names = ["notepad", "calculator", "paint", "command prompt"]
    return any(name in query for name in app_names)


def launch_app(query):
    apps = {
        "notepad": "notepad",
        "calculator": "calc",
        "paint": "mspaint",
        "command prompt": "cmd",
    }
    for name, command in apps.items():
        if name in query:
            subprocess.Popen(command, shell=False)
            speak(f"Launching {name}")
            return
    speak("I can launch Notepad, Calculator, Paint, or Command Prompt right now.")


def handle_query(query):
    global is_running, is_sleeping

    if query == "none":
        set_idle_message()
        return

    state.update(last_query=query)

    if any(phrase in query for phrase in ["sleep", "go to sleep", "standby"]):
        say_variant("sleep")
        is_sleeping = True
    elif "weather" in query:
        get_weather()
    elif "time" in query:
        tell_time()
    elif "date" in query:
        tell_date()
    elif "day" in query:
        tell_day()
    elif "joke" in query or "make me laugh" in query:
        tell_joke()
    elif contains_any(query, NOTE_COMMANDS):
        save_note(query)
    elif contains_any(query, READ_NOTE_COMMANDS):
        read_notes()
    elif contains_any(query, CLEAR_NOTE_COMMANDS):
        clear_notes()
    elif any(phrase in query for phrase in ["remind me", "set reminder", "set a reminder"]):
        set_reminder(query)
    elif is_math_query(query):
        calculate(query)
    elif query.startswith("open ") and is_app_request(query):
        launch_app(query)
    elif query.startswith("open "):
        open_website(query)
    elif query.startswith("launch ") or query.startswith("start "):
        launch_app(query)
    elif any(phrase in query for phrase in ["what can you do", "what all can you do", "about yourself", "your abilities", "help me"]):
        tell_capabilities()
    elif any(phrase in query for phrase in ["hello", "hi ", "hey maya", "good morning", "good afternoon", "good evening"]):
        say_variant("hello")
    elif any(phrase in query for phrase in ["exit", "quit", "bye", "shutdown"]):
        say_variant("exit")
        is_running = False
    elif any(phrase in query for phrase in ["you there", "you their", "are you online", "maya"]):
        say_variant("presence")
    elif any(phrase in query for phrase in ["what is", "who is", "meaning of", "define", "search for", "tell me about"]):
        search_wikipedia(query)
    else:
        set_idle_message()


def run_assistant():
    """Main assistant loop. Call this on a background thread from server.py."""
    global is_running, is_sleeping, active_speech_thread

    wishMe()

    while is_running:
        if active_speech_thread and active_speech_thread.is_alive():
            active_speech_thread.join(timeout=0.1)
            continue

        if is_sleeping:
            state.update(
                mode="standby",
                sys_text="SYSTEM STANDBY",
                message='Standby. Say "wake up" or "Maya" to resume.',
            )
            if listen_for_wake_word():
                is_sleeping = False
                say_variant("wake")
            continue

        state.update(mode="listening", sys_text="AUDIO INPUT ACTIVE", message="Listening...")
        handle_query(takeCommand())

    if active_speech_thread:
        active_speech_thread.join()

    pygame.quit()
    state.update(mode="standby", sys_text="SESSION ENDED", message="Goodbye, boss.")
