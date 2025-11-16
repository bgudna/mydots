#!/usr/bin/env python3
"""
ytwrap - Simple wrapper around yt-dlp's ytsearch to list and play/extract.

Usage examples:
    ytwrap lebron james
    ytwrap -n 15 "doom metal"  # show 15 results
    ytwrap -x jazz fusion       # extract audio of chosen video via yt-dlp -x

Flow:
    1. Perform search using: yt-dlp ytsearch{N}:<query> --dump-json
    2. Show numbered list: <INDEX>) <TITLE> [<ID>]
    3. User selects index; playback/extraction runs.
    4. Results list is shown again for further selections.
    5. Only 'q' quits; empty input just redisplays prompt.
    6. Default: launch mpv with https://youtu.be/<ID>
         With -x: run yt-dlp -x https://youtu.be/<ID> (audio extraction)

Exit codes:
  0  success / user abort / empty results
  2  yt-dlp invocation failure
  3  mpv or yt-dlp (for -x) missing
  4  JSON parse error

Requires external binaries: yt-dlp, mpv (unless -x used) and ffmpeg.
"""

import argparse
import json
import time
import threading
import subprocess
import sys
from typing import List, Tuple

MAX_SHOW = 50
TRUNCATE_LEN = 72

class YtWrapError(Exception):
    pass


def run_search(query: str, limit: int) -> List[str]:
    """Run yt-dlp search returning raw JSON lines with spinner (non-blocking)."""
    search_term = f"ytsearch{limit}:{query}"
    cmd = ["yt-dlp", search_term, "--dump-json", "--flat-playlist", "--skip-download", "--quiet", "--ignore-errors"]
    result: dict = {}

    def worker():
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:
            result["error"] = "yt-dlp binary not found (install yt-dlp)"
            return
        result["returncode"] = proc.returncode
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr

    th = threading.Thread(target=worker)
    th.start()
    spinner_seq = "|/-\\"
    spin_idx = 0
    # Hide the raw search term; just a generic spinner label.
    start_msg = "  Searching "
    print(start_msg, end="", flush=True)
    while th.is_alive():
        print(spinner_seq[spin_idx % len(spinner_seq)], end="\r", flush=True)
        spin_idx += 1
        time.sleep(0.1)
    th.join()
    # Clear spinner line
    print(" " * (len(start_msg) + 2), end="\r")
    if "error" in result:
        raise YtWrapError(result["error"])
    if result.get("returncode", 1) != 0:
        raise YtWrapError(f"yt-dlp search failed: {result.get('stderr','').strip() or 'unknown error'}")
    stdout = result.get("stdout", "")
    lines = [l for l in stdout.splitlines() if l.strip()]
    return lines


def parse_results(lines: List[str]) -> List[Tuple[str, str]]:
    """Parse each JSON line extracting (id, title)."""
    results = []
    for ln in lines:
        try:
            dat = json.loads(ln)
        except json.JSONDecodeError as ex:
            raise YtWrapError(f"JSON parse error: {ex}")
        vid_id = dat.get("id") or dat.get("webpage_url_basename")
        title = dat.get("title") or "(no title)"
        if not vid_id:
            # Skip entries lacking ID
            continue
        if len(title) > TRUNCATE_LEN:
            title = title[:TRUNCATE_LEN] + "..."
        results.append((vid_id, title))
    return results


def display_results(results: List[Tuple[str, str]]):
    """Print numbered list."""
    if not results:
        print("No results.")
        return
    pad = len(str(len(results)))
    for idx, (vid_id, title) in enumerate(results, start=1):
        print(f"{str(idx).rjust(pad)}) {title} [{vid_id}]")


def prompt_selection(results: List[Tuple[str, str]]) -> Tuple[str, str] | None:
    """Prompt user for selection; return (id,title) or None if user quits with q."""
    if not results:
        return None
    while True:
        try:
            inp = input("Select number (q=quit): ").strip()
        except EOFError:
            # Treat EOF as quit
            return None
        if inp.lower() == "q":
            return None
        if inp == "":
            # Empty input: just prompt again
            continue
        if not inp.isdigit():
            print(f"Invalid input '{inp}'. Enter a number or 'q'.")
            continue
        num = int(inp)
        if not (1 <= num <= len(results)):
            print(f"Out of range (1-{len(results)}).")
            continue
        return results[num - 1]


def play_or_extract(video_id: str, title: str, extract_audio: bool) -> int:
    url = f"https://youtu.be/{video_id}"
    if extract_audio:
        cmd = ["yt-dlp", "-x", url]
        desc = "audio extraction"
    else:
        cmd = ["mpv", url]
        desc = "playback"
    print(f"Starting {desc} for {video_id}...")
    try:
        proc = subprocess.run(cmd)
    except FileNotFoundError:
        missing = "yt-dlp" if extract_audio else "mpv"
        print(f"Required binary '{missing}' not found.")
        return 3
    return proc.returncode


def parse_args(argv: List[str]):
    ap = argparse.ArgumentParser(description="Wrapper around yt-dlp ytsearch")
    ap.add_argument("query", nargs=argparse.REMAINDER, help="Search query words")
    ap.add_argument("-n", "--limit", type=int, default=10, help="Number of results (max 50, default 10)")
    ap.add_argument("-x", action="store_true", help="Extract audio instead of playing in mpv")
    args = ap.parse_args(argv)
    if not args.query:
        ap.error("Provide a search query.")
    if args.limit <= 0:
        ap.error("Limit must be > 0")
    if args.limit > MAX_SHOW:
        args.limit = MAX_SHOW
    return args


def main(argv: List[str]) -> int:
    try:
        args = parse_args(argv)
        query = " ".join(args.query)
        lines = run_search(query, args.limit)
        results = parse_results(lines)
    except YtWrapError as ex:
        print(f"Error: {ex}")
        # Distinguish parse error vs other
        if "JSON parse" in str(ex):
            return 4
        if "binary not found" in str(ex):
            return 3
        return 2
    except KeyboardInterrupt:
        print()  # newline
        return 0

    if not results:
        print("No results for query.")
        return 0

    # Persistent selection loop until user quits with 'q'.
    while True:
        display_results(results)
        sel = prompt_selection(results)
        if sel is None:
            print("Quit.")
            return 0
        vid_id, title = sel
        rc = play_or_extract(vid_id, title, args.x)
        if rc != 0:
            # If external tool failed, return its code immediately.
            return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
