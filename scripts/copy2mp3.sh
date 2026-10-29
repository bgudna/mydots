# a simple  script for converting all opus files in a folder to mp3

#!/bin/bash
for f in *.opus; do
    [ -f "$f" ] || continue

    base="${f%.opus}"
    # Skip if an mp3 already exists (with or without the trailing ID)
    if [ -e "$base.mp3" ] || [ -e "${base% \[*\]}.mp3" ]; then
        echo "MP3 already exists, skipping: $f"
        continue
    fi

    if ffmpeg -nostdin -n -i "$f" -vn -codec:a libmp3lame -q:a 2 "$base.mp3"; then
        rm "$f"
        echo "Converted and deleted: $f"
    else
        echo "Conversion failed, keeping: $f"
    fi
done

# Remove trailing IDs from MP3 filenames
for f in *.mp3; do
    [ -f "$f" ] || continue

    # Only touch files that actually end in " [id].mp3"
    case "$f" in
        *" ["*"].mp3")
            new="${f% \[*\].mp3}.mp3"
            mv -n -- "$f" "$new"
            echo "Renamed: $f -> $new"
            ;;
    esac
done

echo "All done!"
