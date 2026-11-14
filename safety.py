"""
Matrix Root AI Assistant - Safety layer (version 2)

How it works:
  1. check_input()  looks at the user's message BEFORE it reaches the AI.
  2. check_output() looks at the AI's answer BEFORE the user sees it.
  3. Every blocked message is counted in blocked_log.csv (time + category only,
     the message text itself is NOT stored, to protect privacy).
"""

import csv
import os
import re
from datetime import datetime

from better_profanity import profanity

profanity.load_censor_words()

# Add abusive words from your local languages here (Telugu, Hindi, Tamil, etc.,
# written in English letters). Example: ["word1", "word2"]
EXTRA_BLOCKED_WORDS = []
if EXTRA_BLOCKED_WORDS:
    profanity.add_censor_words(EXTRA_BLOCKED_WORDS)

LOG_FILE = "blocked_log.csv"

# Harmless phrases that contain scary words. They are removed before checking.
SAFE_PHRASES = [
    "bath bomb", "photo bomb", "photobomb", "life hack", "growth hack",
    "hackathon", "kill a process", "kill the process", "kill -9",
    "kill the lights", "killer feature", "shoot a video", "shoot a photo",
]

# Each category: a list of patterns + a reply message.
# Patterns are matched against the lowercase message.
CATEGORIES = {
    "weapons": [
        r"\b(make|build|create|assemble|3d[- ]?print|manufacture)\b.{0,30}\b(bomb|explosive|grenade|ied|gun|firearm|silencer|poison|nerve agent|bioweapon)\b",
        r"\bhow (to|do i|can i)\b.{0,20}\b(poison|kill|murder)\b.{0,20}\b(someone|somebody|a person|my (boss|wife|husband|colleague|neighbour|neighbor))\b",
    ],
    "cyber_attack": [
        r"\b(write|create|build|make|code)\b.{0,30}\b(ransomware|keylogger|malware|virus|trojan|botnet|spyware)\b",
        r"\b(hack|hacking|steal|break into)\b.{0,30}\b(account|password|wifi|wi-fi|phone|whatsapp|instagram|facebook|gmail|bank|someone|somebody)\b",
    ],
    "fraud": [
        r"\b(write|create|make|generate|build)\b.{0,30}\b(phishing|scam)\b",
        r"\b(fake|forged|forge)\b.{0,25}\b(certificate|payslip|pay slip|experience letter|offer letter|degree|marksheet|id card|aadhaar|aadhar|pan card|invoice|document)\b",
    ],
    "drugs": [
        r"\b(make|cook|synthesi[sz]e|produce|manufacture)\b.{0,25}\b(meth|methamphetamine|cocaine|heroin|lsd|mdma|ecstasy|crack cocaine)\b",
    ],
    "sexual": [
        r"\b(child|children|minor|underage|kid|teen|teenager)\b.{0,40}\b(sexual|nude|naked|explicit|porn)\b",
        r"\b(write|generate|describe|create)\b.{0,30}\b(explicit|erotic|porn|pornographic|sex scene)\b",
    ],
    "harassment": [
        r"\b(write|draft|send|generate|create)\b.{0,30}\b(abusive|threatening|insulting|harassing|hateful)\b.{0,20}\b(message|email|mail|text|post|letter|comment)\b",
        r"\b(insult|abuse|mock|humiliate|threaten)\b.{0,30}\b(my (boss|colleague|manager|employee|teacher|friend|ex)|someone|somebody)\b",
        r"\b(racist|sexist|casteist|homophobic|islamophobic|hateful)\b.{0,20}\b(joke|jokes|insult|insults|rant|essay|post|speech)\b",
        r"\b(insult|abuse|mock|humiliate)\b.{0,30}\b(religion|caste|race|community|gender)\b",
    ],
    "privacy": [
        r"\b(track|spy on|stalk|monitor)\b.{0,30}\b(my )?(someone|girlfriend|boyfriend|wife|husband|ex|partner)\b.{0,30}\b(phone|location|whatsapp|messages|secretly|without)\b",
        r"\b(find|get|give me)\b.{0,20}\b(home address|phone number|personal details)\b.{0,20}\b(of|for)\b",
    ],
    "jailbreak": [
        r"\bignore\b.{0,20}\b(previous|prior|above|all|your)\b.{0,20}\b(instructions|rules|prompt|guidelines)\b",
        r"\b(reveal|show|print|tell me|repeat)\b.{0,25}\b(system prompt|your instructions|your rules|hidden prompt)\b",
        r"\b(jailbreak|do anything now|developer mode)\b",
        r"\bpretend\b.{0,30}\b(no rules|no restrictions|no filter|without rules|without restrictions)\b",
        r"\byou are (now )?(dan|free from|no longer bound)\b",
    ],
}

# Self-harm is handled with care, not just a refusal.
SELF_HARM_PATTERNS = [
    r"\b(kill|hurt|harm|cut)\s+(myself|my ?self)\b",
    r"\b(end|take)\s+my\s+(own\s+)?life\b",
    r"\bwant\s+to\s+die\b",
    r"\bdon'?t\s+want\s+to\s+(live|be alive)\b",
    r"\bhow\s+to\b.{0,15}\b(commit\s+suicide|die\s+by\s+suicide|end\s+it\s+all)\b",
    r"\b(suicide)\b.{0,25}\b(method|methods|painless|easiest way)\b",
]

SELF_HARM_MESSAGE = (
    "I'm really sorry you're feeling this way. You don't have to go through it alone.\n\n"
    "Please talk to someone you trust right now, such as a family member, a close friend "
    "or a doctor. In India, **Tele-MANAS** offers free, confidential support 24x7: "
    "call **14416** (or 1-800-891-4416). If you are in immediate danger, call **112**.\n\n"
    "I'm here to chat too, if you'd like to tell me what's on your mind."
)

MESSAGES = {
    "default": (
        "I'm sorry, but I can't help with that request. "
        "I'm happy to help with something else, so please feel free to ask!"
    ),
    "abuse": (
        "Let's keep our conversation respectful, please. "
        "Could you rephrase your question politely? I'm glad to help."
    ),
    "jailbreak": (
        "I can't change or reveal my rules, but I'm happy to help you with "
        "any normal question or project."
    ),
    "fraud": (
        "I can't help create fake or misleading documents or scams. "
        "I can help you write genuine, professional documents instead."
    ),
}

OUTPUT_FALLBACK = (
    "I'm sorry, my answer contained inappropriate language, so I've withheld it. "
    "Please try rephrasing your question."
)

_COMPILED = {
    name: [re.compile(p) for p in patterns] for name, patterns in CATEGORIES.items()
}
_SELF_HARM = [re.compile(p) for p in SELF_HARM_PATTERNS]


def _log(category):
    """Record that something was blocked (time + category only, no message text)."""
    try:
        new_file = not os.path.exists(LOG_FILE)
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["time", "category"])
            writer.writerow([datetime.now().isoformat(timespec="seconds"), category])
    except Exception:
        pass  # logging must never break the chatbot


def _normalise(text):
    """Make tricks like 'f u c k', 'fuuuck' or 'sh1t' easier to catch."""
    t = text.lower()
    t = t.translate(str.maketrans("01345@$!", "oieasasi"))
    t = re.sub(r"(.)\1{2,}", r"\1", t)  # fuuuck -> fuck
    t = re.sub(
        r"\b(?:\w[\s\.\-_*]){3,}\w\b",
        lambda m: re.sub(r"[\s\.\-_*]", "", m.group(0)),
        t,
    )  # f u c k -> fuck
    return t


def _remove_safe_phrases(text):
    for phrase in SAFE_PHRASES:
        text = text.replace(phrase, " ")
    return text


def check_input(text):
    """Returns (is_allowed, message_if_blocked)."""
    lowered = _remove_safe_phrases(text.lower())

    # 1. Self-harm: reply with care
    for pattern in _SELF_HARM:
        if pattern.search(lowered):
            _log("self_harm")
            return False, SELF_HARM_MESSAGE

    # 2. Dangerous or inappropriate requests
    for category, patterns in _COMPILED.items():
        for pattern in patterns:
            if pattern.search(lowered):
                _log(category)
                return False, MESSAGES.get(category, MESSAGES["default"])

    # 3. Abusive language (checks both the original and the cleaned-up text)
    if profanity.contains_profanity(text) or profanity.contains_profanity(_normalise(text)):
        _log("abuse")
        return False, MESSAGES["abuse"]

    return True, ""


def check_output(text):
    """Checks the AI's answer before the user sees it."""
    if profanity.contains_profanity(text):
        _log("output_abuse")
        return OUTPUT_FALLBACK
    return text
