#!/usr/bin/python3
'''
vid-searcher - The Youtube Video Searcher 
The basis for this tool was made by datagubbe.se - I've modified it to fit my needs.
==============================
Searches Youtube and then downloads an audio version of your selection. 
Version 1.1.7
Requires:  
 * Python > 3.5
 * yt-dlp
 * ffmpeg
 * mpv

Warning to sensitive readers: This software contains crude hacks
and blatant bugs.

 Usage
=======
* Watch a video from a URL:
    $ tube <URL>
  Where <URL> is a Youtube URL containing a video ID.

* Watch a video from a URL without committing to history log,
  regardless of history setting:
    $ tube nohist <URL>
  Where <URL> is a Youtube URL containing a video ID.

* List history:
    $ tube hist
  This will produce a numbered history list.

* Watch a video from the history:
    $ tube <INDEX>
  Where <INDEX> is an integer, corresponding to a number in
  the history list.

* Delete from history:
    $ tube delhist 5 8 13 21
  Will delete entries 5, 8, 13 and 21 from the history.
    $ tube delhist 15-22
  Will delete entries 15 through 22 from the history.
    $ tube delhist last
  Will delete the last entry from the history.

* Create a .ytrc settings file template with sane defaults:
    $ tube makedot

* Search Youtube:
    $ tube search keyword1 keyword2 ... keywordN

 Search Function
=================
The search function will take an arbitrary number of space-separated
query keywords and return the first 20 results (if any) from Youtube's
search function. If there are no search hits, tube will exit. If hits
are found, they will be listed on the format "X) Author: Video Title",
where X is a numbered index for the search hit. The user will then be
presented with a small CLI. The CLI facilitates viewing of a search hit,
(re-)listing the search results, or quitting the search function.
  * Entering the index number corresponding to a search hit will launch
    the configured video player to view this search hit.
  * Entering 'l' will list the search results again.
  * Empty input (I.E. just pressing RETURN) or 'q' will quit
    the search CLI.

NOTE! The search function now requires a CONSENT cookie to be set and
sent to Youtube. This means that by using the search function, you will
effectively have given Youtube legal consent to do whatever it is they
do when such consent is given. YOU HAVE BEEN WARNED.

 Watched Video History
=======================
Watched videos are stored in a simple JSON list.
The list is written to ~/.yt_history

The index starts at 1. The list is always dense,
I.E. after deleting a video from the history, all the
following videos will have a new index.

A video will only be written to the history once
and the order is not updated if a video is re-watched.
Deletion will re-order the list.

 Configuration File
====================
A configuration file called ".ytrc" may be created in the root
of a user's home directory.

Calling tube with the argument "makedot" will create this file for you,
with sane defaults.

The file is expected to be valid JSON.

The following settings are supported:

  * "pref_maxres" is an integer, determining the maximum allowed height of
    matching videos in pixels.
    It defaults to 1700.

  * "verbose" is a boolean, controlling whether informative log messages
    should be written to stdout when running the script.
    It defaults to true.

  * "history" is a boolean, controlling if a history of
    watched videos should be kept (see Watched Video History above).
    It defaults to true.

  * "use_ytdlp" is a boolean, controlling whether tube should launch
    a video player directly, or pipe the output of yt-dlp to the player.
    Not that the "player" setting below must reflect this, I.E. the player
    must be configured to accept data on STDIN.
    It defaults to true.

  * "player" can be a string or a list. It can be extended with any number
    of command line arguments. In each argument, "%url" and "%title" will
    be replaced with the video URL and video title, respectively.

    If "use_ytdlp" is set to true, the "player" setting is what the
    output from yt-dlp will be piped to, so ensure that the configuration
    entered accepts data from STDIN. In this mode, "%title" will be
    replaced as described above, but "%url" will instead be replaced by
    a dash ("-"), since this corresponds to STDIN in most cases. The
    URL itself is not needed when using yt-dlp - it will perform its own
    URL extraction.

    When player is a string, a base set of sane defaults will be applied
    to ensure that the video title is displayed in the window title when
    running under X11. If mplayer is used, the default settings will assume
    usage in a TTY and call it with fbdev2.
    It defaults to "mpv".

For example, to turn history off:
  {
    "history": false
  }

To turn history off and use VLC instead of the default MPV:
  {
    "history": false,
    "player": "vlc"
  }

To turn verbose mode off and use a custom player command line:
  {
    "verbose": false,
    "player": ["vlc", "%url", "--meta-title", "Jeff's VLC playing %title!"]
  }

 Changelog
===========
See CHANGELOG in the distribution archive.

 License
=========
Copyright 2023 Carl Svensson

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import urllib.parse as urlparse
import urllib.request as urlreq
import urllib.error as urlerrs
import json
import sys
import subprocess
import os.path
from shlex import quote as shquote

def token_slice(s, stok, etok):
  # Slice string between given start and end tokens.
  # End token might occur before start token in the raw data,
  # so slice at start token and then look for end token in the result.
  s = s[s.index(stok)+len(stok):]
  s = s[:s.index(etok)]
  return s


# Custom exception class for throwing and handling tube-specific errors.
class YtError(Exception):
  def __init__(self, msg):
    Exception.__init__(self, msg)
    self.msg = msg


# Base class for stdout and stderr messaging.
class YtStdIo:
  @staticmethod
  def out(s):
    try:
      sys.stdout.write("%s\n" % s)
      sys.stdout.flush()
    except (BrokenPipeError, IOError):
      # BrokenPipeError occurs when the recieving process stops reading
      # from stdin before Python stops writing to stdout, E.G. quitting
      # less before having scrolled to the end of the complete tube
      # history listing.
      # On some platforms it might be an IOError - haven't been able
      # to test that properly.
      # Python apparently always prints an error about this on stderr,
      # so we have to close stderr to mute it.
      sys.stderr.close()
      exit(1)

  @staticmethod
  def errout(s):
    sys.stderr.write("%s\n" % s)

  def errdie(self, s, exitcode=1):
    self.errout(s)
    exit(exitcode)


# Class for managing JSON files (I.E. .ytrc and .yt_history).
class YtFileHandler:
  def __init__(self, filename):
    self.path = os.path.expanduser("~/%s" % filename)

  def exists(self):
    return os.path.exists(self.path)

  def try_create(self):
    if not self.exists():
      fptr = open(self.path, "x")
      fptr.close()

  def readj(self):
    # Read JSON file to dict.
    conts = []
    if os.path.exists(self.path):
      with open(self.path, "r") as f:
        fconts = f.read()
        if fconts:
          conts = json.loads(fconts)
    return conts

  def writej(self, conts, indent=None):
    # Write dict to JSON file.
    with open(self.path, "w") as f:
      json.dump(conts, f, indent=indent)


# Class for handling user settings found in .ytrc, with fallback to defaults.
class YtSettings:
  prefs = dict(
    pref_maxres=1700, # Max video height in pixels.
    verbose=True,
    keep_history=True,
  )
  valid_players = ["vlc", "mpv", "mplayer", "omxplayer"]
  def_player = "mpv"
  player = None
  player_defaults = {
    "vlc": ["%url", "--meta-title", "%title"],
    "mpv": ["--loop", "%url", "--title=%title"],
    "mplayer": ["-vo", "fbdev2", "%url"],
    "omxplayer": ["%url"]
  }

  def __init__(self):
    self.read_settings()

  def read_settings(self):
    try:
      rcfile = YtFileHandler(".ytrc")
      if rcfile.exists():
        settings = rcfile.readj()
        self.prefs["keep_history"] = bool(settings.get("history", True))
        self.prefs["verbose"] = bool(settings.get("verbose", True))
        self.prefs["pref_maxres"] = int(settings.get("pref_maxres", 1700))
        self.prefs["use_ytdlp"] = bool(settings.get("use_ytdlp", True))
        self.parse_player_setting(settings.get("player", self.def_player))
      else:
        self.parse_player_setting(self.def_player)
    except YtError as err:
      raise err
    except Exception:
      raise YtError("Unable to parse .ytrc")

  def make_dotfile(self):
    rcfile = YtFileHandler(".ytrc")
    if rcfile.exists():
      raise YtError("%s already exists" % rcfile.path)
    prefs = self.prefs.copy()
    prefs.update({"player": self.def_player})
    rcfile.writej(prefs, 2)
    return rcfile

  def parse_player_setting(self, player):
    if isinstance(player, str) and player in self.valid_players:
      player = [player]
      player.extend(self.player_defaults[player[0]])
      self.player = player
    elif player[0] in self.valid_players:
      self.player = player
    else:
      raise YtError("Unsupported player '%s'" % player)


# Class for managing previously watched videos.
class YtHistory:
  def __init__(self, fhdl=None):
    self.fhdl = fhdl if fhdl else YtFileHandler(".yt_history")

  def read(self):
    if not self.fhdl.exists():
      raise YtError("No history file found.")
    try:
      hist = self.fhdl.readj()
    except Exception:
      raise YtError("Error reading history")
    return hist

  def get_from_pos(self, pos):
    hist = self.read()
    return hist[pos]

  def del_from_positions(self, mpos):
    hist = self.read()
    for pos in mpos:
      hist[pos] = None
    nhist = [i for i in hist if i is not None]
    self.fhdl.writej(nhist)

  def del_last_pos(self):
    hist = self.read()
    hist.pop()
    self.fhdl.writej(hist)

  def write_history(self, vid, title):
    try:
      self.fhdl.try_create()
      hist = self.read()
      ids = [i for i, t in hist]
      if vid not in ids:
        hist.append([vid, title])
      self.fhdl.writej(hist)
    except Exception:
      raise YtError("Error writing history")


# Class for interfacing with youtube's search function.
class YtSearch:
  def __init__(self, query):
    self.query = query
    self.qurl = "https://www.youtube.com/results?"\
      + urlparse.urlencode(dict(search_query=query))

  def search(self):
    # Sometimes parsing fails because of discrepancies in the result,
    # retry before giving up.
    retry = 0
    err = None
    while retry < 2:
      try:
        dat = self.get_result_json()
        err = None
        break
      except ValueError as ex:
        err = ex
        retry += 1

    if err:
      raise YtError(str(err))

    hits = []
    if dat["estimatedResults"] == "0":
      return hits

    res = self.extract_struct_part(dat["contents"])

    for _, val in res:
      if not "videoRenderer" in val:
        # Ignore "shelfRenderer" and similar entries
        # that promote "related" videos.
        continue
      title = val["videoRenderer"]["title"]["runs"][0]["text"]
      author = val["videoRenderer"]["ownerText"]["runs"][0]["text"]
      vid = val["videoRenderer"]["videoId"]
      hits.append((vid, title, author))
    return hits

  def get_result_json(self):
    # Gets the search result JSON.
    # First, fire an initial request to get proper cookies.
    sreq = urlreq.Request(self.qurl)
    resp = urlreq.urlopen(sreq)

    # Build cookies based on initial request.
    cookies = []
    for k, val in resp.getheaders():
      if k.lower() == "set-cookie":
        cookies.append(val.split(";")[0])
    cookies.append("CONSENT=YES+cb.20211001-17-p0.en+FX+789")
    cookie = "; ".join(cookies)

    # Prepare actual search request.
    sreq = urlreq.Request(self.qurl)
    sreq.add_header("Referer", "https://www.youtube.com/")
    sreq.add_header("cookie", cookie)

    # Search!
    raw = urlreq.urlopen(sreq).read().decode("utf-8")

    stok = "var ytInitialData = "
    etok = ";</script>"
    return json.loads(token_slice(raw, stok, etok))

  def extract_struct_part(self, items, parent=None, part_key="videoRenderer"):
    '''
    Recursively find and extract the list or dict
    of dicts containing the key <part_key>,
    E.G. return fooBarKey's items:
      {
        barKey: {
          fooKey: {
            fooBarKey: [
              { part_key: xxx },
              ...
            ]
          }
        }
      }
    '''
    if parent is None:
      parent = []
    result = False
    if isinstance(items, dict):
      if part_key in items:
        # Found!
        return parent
      items = list(items.items())
    elif isinstance(items, list):
      items = list(enumerate(items))
    else:
      # Skip strings, ints, etc.
      items = []
    for _, val in items:
      if isinstance(items, (list, dict)):
        result = self.extract_struct_part(val, items, part_key)
        # We got a result, stop recursion.
        if result != False:
          break
    return result


# Class for extracting video metadata from a given Youtube URL.
class YtExtractor(YtStdIo):
  prefs = dict(
    pref_maxres=1700, # Max video height in pixels.
    verbose=True,
  )

  api_url = "https://www.youtube.com/watch?v=%s"
  user_agent = None

  inurl = ""
  inf = None
  parsed_formats = []
  video_details = []
  streaming_data = None
  vidid = None

  def __init__(self, prefs=None):
    if prefs is not None:
      self._set_prefs(prefs)
    self.user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    self.user_agent += "(KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36"

  def _set_prefs(self, prefs):
    for pref, prefval in prefs.items():
      if pref in self.prefs:
        self.prefs[pref] = prefval

  def log(self, s):
    if self.prefs.get("verbose"):
      self.out("[tube] %s" % s)

  # Main entry point: Tries to extract video metadata from the given url.
  def do_extract(self, inurl):
    self.inurl = inurl
    url = urlparse.urlparse(self.inurl)
    qry = urlparse.parse_qs(url.query)

    try:
      if url.netloc == "youtu.be":
        # Handle "https://youtu.be/f00b4r".
        self.vidid = url.path.replace("/", "")
      else:
        if url.path.startswith("/v/"):
          # Handle "https://www.youtube.com/v/f00b4r".
          self.vidid = url.path.replace("/v/", "")
        else:
          # Handle "https://www.youtube.com/watch?v=f00b4r".
          self.vidid = qry["v"][0]
    except KeyError:
      raise YtError("Malformed URL '%s'" % self.inurl)
    rawurl = self.api_url % self.vidid

    self.log("Sending request to Youtube API")
    try:
      vidreq = self.prepare_req(urlreq.Request(rawurl))
      resp = urlreq.urlopen(vidreq)
      raw = resp.read().decode("utf-8")
    except Exception as conn_ex:
      raise YtError(str(conn_ex))

    # Extract main JSON chunk.
    player_response = self.extract_player_response(raw)

    try:
      inf = json.loads(player_response)
    except json.decoder.JSONDecodeError:
      errstr = "Error decoding JSON:\n\n%s\n\n(Encountered JSONDecodeError)"
      raise YtError(errstr % str(player_response))

    if not inf.get("streamingData"):
      if inf.get("playabilityStatus", {}).get("status"):
        errstr = "%s: %s" % (
          inf.get("playabilityStatus").get("status"),
          inf.get("playabilityStatus").get("reason", "Unknown reason"))
        raise YtError(errstr)
      else:
        raise YtError("Couldn't find streamingData in JSON response.")

    self.streaming_data = inf["streamingData"]

    try:
      self.video_details = inf["videoDetails"]
    except:
      raise YtError("Couldn't find videoDetails in JSON response.")

  @staticmethod
  def extract_player_response(rsp):
    stok = "var ytInitialPlayerResponse = "
    etok = ";var meta ="
    if not etok in rsp:
      etok = ";var head ="
    return token_slice(rsp, stok, etok)

  @staticmethod
  def decode_alternate(fmt):
    raw = None
    unclean_keys = ["cipher", "signatureCipher"]
    for uc_key in unclean_keys:
      if uc_key in fmt:
        raw = fmt.get(uc_key)
        break
    if raw:
      base = "https://www.youtube.com/watch?v="
      unclean = urlparse.parse_qs(urlparse.urlparse(base + raw).query)
      return unclean["url"][0]
    raise YtError("URL Extraction using decode_alternate failed")

  def _parse_formats(self, formats):
    resmax = 0
    vidurl = ""
    found = []
    for fmt in formats:
      # Skip webm, go for MP4.
      if "mp4" in str(fmt.get("mimeType")):
        hres = fmt.get("height", 0)
        # Find the highest desired resolution.
        if resmax < hres < self.prefs["pref_maxres"]:
          resmax = hres
          vidurl = fmt.get("url")
          if not vidurl:
            # Perhaps URL ended up in cipher due to earlier
            # parse errors.
            self.log("Possibly protected video. "\
              + "Using alternate stream extraction method.")
            vidurl = self.decode_alternate(fmt)
          if vidurl:
            found.append((resmax, vidurl))
    found.sort(key=lambda x: x[0])
    found.reverse()
    return found

  def get_video_info(self):
    # Assumes valid streamingData and videoDetails structures
    # have been extracted by do_extract().
    if not self.streaming_data or not self.video_details:
      raise YtError("Parsed data not found, try extraction first")

    formats = self.streaming_data.get("formats")
    if not formats:
      self.log("No standard formats, trying adaptiveFormats...")
      formats = self.streaming_data.get("adaptiveFormats")
    if not formats:
      raise YtError("No formats found")

    found = self._parse_formats(formats)

    http_err = ""
    vidurl = ""
    res = 0
    for res, vidurl in found:
      # Try to access all URLs.
      self.log("Trying HTTP access for resolution %s px..."\
        % str(res))
      try:
        self.assert_http_ok(vidurl)
        http_err = ""
        break
      except YtError as ex:
        http_err = ex.msg
        self.log("...failed to connect")
        vidurl = ""
        continue

    if vidurl:
      title = self.video_details.get("title", "Unknown title")
      self.log("Found stream URL for '%s'. Resolution height %s px." % (
        self.vidid, str(res)))
    elif http_err:
      raise YtError(http_err)
    else:
      errstr = "Unable to find suitable stream URL\n%s\n(No suitable format)"
      raise YtError(errstr % str(formats))

    return {
      "id": self.vidid,
      "url": vidurl,
      "title": title,
      "res": res,
    }

  def prepare_req(self, vidreq):
    vidreq.add_header("Referer", self.inurl)
    vidreq.add_header("User-Agent", self.user_agent)
    return vidreq

  def assert_http_ok(self, url):
    head_req = self.prepare_req(urlreq.Request(url, method="HEAD"))
    try:
      urlreq.urlopen(head_req)
    except urlerrs.HTTPError as http_ex:
      raise YtError("HTTP %d: Cannot access video URL (%s)" % (
        http_ex.getcode(), url))
    except Exception as other_ex:
      raise YtError(str(other_ex))


# A small CLI for handling the search function.
class YtSearchCli(YtStdIo):
  def __init__(self, hits, query, watcher):
    self.watcher = watcher
    self.hits = hits
    self.query = query

  # List search hits.
  def _cli_list(self):
    i = 0
    qdisp = self.query if len(self.query) < 61 else self.query[:60] + "..."
    self.out("Result for '%s':" % qdisp)
    for _, title, author in self.hits:
      vidinf = (author + ": " + title)[:72]
      if len(vidinf) == 72:
        vidinf = vidinf + "..."
      self.out("%s) %s" % (str(i+1).rjust(3), vidinf))
      i += 1

  # Handle user interaction with search results.
  def cli(self):
    while True:
      self._cli_list()
      self.out("Enter number to play video, "\
        +"'l' to list results, empty input or 'q' to quit.")
      inp = input("vid search > ")
      if inp.lower() == "q" or inp == "":
        exit(0)
      if inp.lower() == "l":
        # Loop will re-list results.
        continue
      iinp = int(inp) if inp.isnumeric() else 0
      if iinp <= 0:
        self.out("Unrecognized input '%s'" % inp)
        continue
      idx = iinp - 1
      if 0 <= idx < len(self.hits):
        vid, _, _ = self.hits[idx]
        url = "https://www.youtube.com/watch?v=%s" % vid
        # self.watcher(url)
        # pipe the url to mpv
        self.out("Opening %s in mpv..." % url)
        subprocess.run(["mpv", url])


# Interfaces with the user: CLI args, search, settings management etc.
class YtUserInterface(YtStdIo):
  def __init__(self):
    try:
      self.settings = YtSettings()
    except YtError as ex:
      self.errdie(ex.msg)
    self.hist = YtHistory()
    self.extractor = YtExtractor(self.settings.prefs)

  # Launches the configured player as a subprocess.
  def launch_player(self, info, inurl):
    ply = []
    url = info["url"]
    title = "Youtube (" + info["title"] + ")"
    do_shell = False

    if self.settings.prefs.get("use_ytdlp"):
      quoted_title = shquote(title)
      for s in self.settings.player:
        ply.append(s.replace("%title", quoted_title).replace("%url", "-"))
      ply = ["yt-dlp", "'%s'" % inurl, "-o", "-", "|"] + ply
      do_shell = True
      ply = " ".join(ply)
    else:
      for s in self.settings.player:
        ply.append(s.replace("%url", url).replace("%title", title))

    try:
      if self.settings.prefs.get("verbose"):
        self.out("[tube] Launching player...")
      subprocess.run(ply, shell=do_shell)
    except FileNotFoundError:
      raise YtError("Player binary '%s' not found" % ply[0])

  # Prints a nicely formatted history list.
  def list_history(self):
    try:
      hist = self.hist.read()
      padlen = len(str(len(hist)))
      for i, vidinf in enumerate(hist):
        self.out("%s) %s" % (str(i+1).rjust(padlen), vidinf[1]))
    except YtError as ex:
      self.errdie(ex.msg)

  # Write last watched video to history, if applicable.
  def write_history(self, vid, title):
    if self.settings.prefs["keep_history"]:
      try:
        self.hist.write_history(vid, title)
      except YtError as ex:
        self.errdie(ex.msg)

  # Watch video: Extract metadata, then launch player.
  def watch_video(self, inurl):
    try:
      self.extractor.do_extract(inurl)
      info = self.extractor.get_video_info()
    except YtError as ex:
      self.errdie(ex.msg)
    self.write_history(info["id"], info["title"])
    try:
      self.launch_player(info, inurl)
    except YtError as ex:
      self.errdie(ex.msg)

  # Tries to search youtube. If successful, lists the hits and
  # provides a minimal CLI for handling the results.
  def search_tube(self, query):
    try:
      hits = YtSearch(query).search()
    except YtError as ex:
      self.errdie("Failed parsing search result. (%s)" % str(ex))
    if not hits:
      self.out("No search hits for '%s'" % query)
      exit(0)
    YtSearchCli(hits, query, self.watch_video).cli()

  # Arg handler: List history.
  def _arg_hist(self, args):
    if len(args) > 1:
      # Assume second arg is history position.
      pos = args[1]
      try:
        vid, _ = self.hist.get_from_pos(int(pos)-1)
      except IndexError:
        self.errdie("History: No match for '%s'" % pos)
      except YtError as ex:
        self.errdie(ex.msg)
      url = "https://www.youtube.com/watch?v=%s" % vid
      self.watch_video(url)
    else:
      self.list_history()

  # Arg handler: Watch video without writing it to history.
  def _arg_nohist(self, args):
    self.settings.prefs["keep_history"] = False
    self.watch_video(args[1]) # Assume second arg is video URL.

  # Arg handler: Re-construct a youtube url from a given history entry.
  def _arg_geturl(self, args):
    # Assume second arg is history position.
    pos = args[1]
    try:
      vid, _ = self.hist.get_from_pos(int(pos)-1)
      self.out("https://www.youtube.com/watch?v=%s" % vid)
    except YtError as ex:
      self.errdie(ex.msg)

  # Arg handler: Delete from history.
  def _arg_delhist(self, args):
    if args[1].lower() == "last":
      # Delete last entry in list.
      try:
        self.hist.del_last_pos()
      except YtError as ex:
        self.errdie(ex.msg)
      return # Last entry deleted, all done.

    # Assume remaining args are history positions and parse them.
    if "-" in args[1]:
      # Range of positions, E.G. '7-18'.
      try:
        span = [int(i) for i in args[1].split("-")]
      except ValueError:
        self.errdie("History positions must be integers")
      if len(span) > 2:
        self.errdie("Deletion range may only contain start and end positions")
      span[-1] += 1
      positions = [pos-1 for pos in range(*span)]
    else:
      # List of positions, E.G. '12 37 89'.
      if " " in args[1]:
        # User passed quoted list.
        delargs = args[1].split()
      else:
        # User passed unquoted list.
        delargs = args[1:]
      try:
        positions = [int(pos)-1 for pos in delargs]
      except ValueError:
        self.errdie("History positions must be integers")

    try:
      self.hist.del_from_positions(positions)
    except IndexError:
      self.errdie("Failed to delete history: invalid index")
    except YtError as ex:
      self.errdie(ex.msg)

  # Arg handler: create .ytrc file.
  def _arg_dotfile(self):
    try:
      rcfile = self.settings.make_dotfile()
      self.out("Created %s" % rcfile.path)
    except YtError as ex:
      self.errdie("Unable to create dotfile: %s" % ex.msg)

  # Arg handler: Launch youtube search.
  def _arg_search(self, args):
    query = " ".join(args[1:])
    self.search_tube(query)

  # Arg handler: Output documentation.
  def _arg_docs(self):
    self.out(__doc__.strip())

  # Arg handler: Print short-form help.
  def _arg_help(self):
    helptext = "\n".join([l[4:] for l in '''
    vid - the Youtube Video Extractor (c) 2023 Carl Svensson. This is free software
    with ABSOLUTELY NO WARRANTY. Use '{sn} docs | less' for more information.

    == Parameters ==
    * <URL>|<INDEXNUMBER>
        Watch a video from a Youtube URL or a history index, E.G.:
        {sn} https://youtube.com/watch?v=f00b4r
        {sn} 134
    * nohist <URL>
        Watch a video from a URL without commiting it to the history.
    * hist
        Output an indexed history list of previously watched videos.
    * delhist N1 (N2 N3 N4...Nn), delhist N1-N2, delhist last
        Delete entries at given indices in the history list (delhist 1 2 3 5 8),
        between and including given indices (delhist 15-22) or the last video
        in the history list (delhist last).
    * search <QUERY>
        Search Youtube for videos related to the supplied query.
    * makedot
        Create a '~/.ytrc' config file with sane defaults, for further editing.
    * docs
        Output extensive documentation, examples and licensing information.
    '''.split("\n")])
    ytfile = os.path.basename(__file__)
    self.out(helptext.format(sn=ytfile).strip())

  # Handle CLI args.
  def arg_handler(self):
    args = sys.argv[1:]
    arglen = len(args)
    takes_args, no_args = True, False

    arg_handlers = {
      "--help": (self._arg_help, no_args),
      "help": (self._arg_help, no_args),
      "-h": (self._arg_help, no_args),
      "docs": (self._arg_docs, no_args),
      "makedot": (self._arg_dotfile, no_args),
      "hist": (self._arg_hist, takes_args),
      "search": (self._arg_search, takes_args),
      "geturl": (self._arg_geturl, takes_args),
      "delhist": (self._arg_delhist, takes_args),
      "nohist": (self._arg_nohist, takes_args),
    }

    if arglen:
      arg = args[0]
      if arg in arg_handlers:
        # Argument with matching handler supplied, so handle it.
        handler, do_args = arg_handlers[arg]
        if do_args:
          handler(args)
        else:
          handler()
      else:
        # No matching handler, assume history position or video URL.
        hist_pos = int(arg) if arg.isnumeric() else 0
        if hist_pos:
          # If user supplied an integer, interpret it as a history position.
          self._arg_hist([None, hist_pos])
        else:
          # Assume user supplied a youtube URL.
          self.watch_video(args[0])
    else:
      self._arg_help()

if __name__ == "__main__":
  YtUserInterface().arg_handler()
