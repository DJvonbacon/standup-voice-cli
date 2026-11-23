6c
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL_ID = "eleven_flash_v2_5"
DEFAULT_MAX_CHARS = 500
CACHE_DIR = Path("audio_cache")


def build_cache_key(text: str, voice_id: str, model_id: str) -> str:
  payload = f"{model_id}:{voice_id}:{text}".encode("utf-8")
  return hashlib.sha256(payload).hexdigest()[:16]


def clean_for_speech(text: str) -> str:
  # Convert Markdown links [label](url) -> label, and drop raw URLs
  text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
  text = re.sub(r"https?://\S+", "", text)
  # Strip inline code backticks, headings, emphasis markers, and leading bullets
  text = re.sub(r"`+", "", text)
  text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
  text = re.sub(r"(\*\*|__|\*|_)", "", text)
  text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
  # Collapse extra whitespace/newlines into smooth spoken spacing
  text = re.sub(r"\s+", " ", text).strip()
  return text


def load_briefing_text(args: argparse.Namespace) -> str:
  if args.file:
    path = Path(args.file)
    if not path.exists():
      raise FileNotFoundError(f"Briefing file not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
  elif args.text:
    text = args.text.strip()
  elif not sys.stdin.isatty():
    text = sys.stdin.read().strip()
  else:
    raise ValueError("Provide briefing text via --text, --file, or piped stdin.")

  text = clean_for_speech(text)
  if not text:
    raise ValueError("Briefing text is empty.")
  return text

def build_cache_key(text: str, voice_id: str, model_id: str) -> str:
    payload = f"{model_id}:{voice_id}:{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def load_briefing_text(args: argparse.Namespace) -> str:
    if args.file:
        path = Path(args.file)
        if not path.exists():
            raise FileNotFoundError(f"Briefing file not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
    elif args.text:
        text = args.text.strip()
    elif not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    else:
        raise ValueError("Provide briefing text via --text, --file, or piped stdin.")

    if not text:
        raise ValueError("Briefing text is empty.")
    return text


def synthesize_briefing(
    client: ElevenLabs | None,
    text: str,
    voice_id: str,
    model_id: str,
    max_chars: int,
    cache_dir: Path,
    dry_run: bool = False,
) -> Path:
    char_count = len(text)
    if char_count > max_chars:
        raise ValueError(
            f"Briefing is {char_count} characters, exceeding your --max-chars limit of {max_chars}."
        )

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = build_cache_key(text, voice_id, model_id)
    output_path = cache_dir / f"briefing_{cache_key}.mp3"

    if output_path.exists():
        print(f"Cache hit ({char_count} chars, 0 API credits used): {output_path}")
        return output_path

    if dry_run:
        print(
            f"Dry run OK: {char_count} chars within {max_chars}-char guard. "
            f"Would call model={model_id}, voice={voice_id} -> {output_path}"
        )
        return output_path

    if client is None:
        raise EnvironmentError("ElevenLabs client is not initialized.")

    audio_chunks = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128",
    )

    with open(output_path, "wb") as f:
        for chunk in audio_chunks:
            if isinstance(chunk, bytes):
                f.write(chunk)

    print(f"Generated ({char_count} chars): {output_path}")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a daily standup or briefing into spoken audio.")
    parser.add_argument("--text", help="Briefing text passed directly on the command line.")
    parser.add_argument("--file", help="Path to a .txt or .md briefing file.")
    parser.add_argument(
        "--voice-id",
        default=os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID),
        help="ElevenLabs voice ID.",
    )
    parser.add_argument(
        "--model-id",
        default=os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID),
        help="ElevenLabs TTS model ID.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=int(os.getenv("MAX_BRIEFING_CHARS", str(DEFAULT_MAX_CHARS))),
        help="Hard cap on characters per API request to protect free-tier credits.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate length and cache without calling the API.")
    parser.add_argument("--play", action="store_true", help="Play the audio after generation (requires ffmpeg or mpv).")
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    try:
        text = load_briefing_text(args)
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key and not args.dry_run:
            raise EnvironmentError("Missing ELEVENLABS_API_KEY in environment or .env file.")

        client = ElevenLabs(api_key=api_key) if api_key else None
        output_path = synthesize_briefing(
            client=client,
            text=text,
            voice_id=args.voice_id,
            model_id=args.model_id,
            max_chars=args.max_chars,
            cache_dir=CACHE_DIR,
            dry_run=args.dry_run,
        )

        if args.play and output_path.exists():
            play(str(output_path))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
