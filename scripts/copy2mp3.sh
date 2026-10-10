# a simple  script for converting all opus files in a folder to mp3

#!/bin/bash 
for f in *.opus; do
    [ -f "$f" ] || continue
    ffmpeg -i "$f" -vn -codec:a libmp3lame -q:a 2 "${f%.opus}.mp3"
done
