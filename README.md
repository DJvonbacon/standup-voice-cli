# standup-voice-cli

Convert daily standup or morning briefing text into cached MP3 audio using the ElevenLabs API.

## Setup

1. Create and activate a virtual environment:
   python3 -m venv .venv && source .venv/bin/activate
2. Install dependencies:
   pip install -r requirements.txt
3. Copy .env.example to .env and add your ELEVENLABS_API_KEY.

## Usage

Dry run (0 API credits):
python briefing.py --text "Daily standup summary." --dry-run

Generate and play audio from a file:
python briefing.py --file standup.txt --play
