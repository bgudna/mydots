# a simple  script for converting all opus files in a folder to mp3

#!/bin/bash
for f in *.opus; do
    [ -f "$f" ] || continue

    if ffmpeg -i "$f" -vn -codec:a libmp3lame -q:a 2 "${f%.opus}.mp3"; then
        rm "$f"
        echo "Converted and deleted: $f"
    else
        echo "Conversion failed, keeping: $f"
    fi
done

# Remove trailing IDs from MP3 filenames
for f in *.mp3; do
    [ -f "$f" ] || continue

    new="${f% \[*\].mp3}.mp3"

    if [ "$new" != "$f" ]; then
        mv -n -- "$f" "$new"
        echo "Renamed: $f -> $new"
    fi
done

echo "All done!"
