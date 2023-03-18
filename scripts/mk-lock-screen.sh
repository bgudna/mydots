#!/bin/sh
# simple tool to create multiple lockscreens for i3 
    convert /mnt/drive/pics/locks/*.jpg -font Liberation-Mono \
    -fill '#0008' -draw 'rectangle 20,110,480,145' \
    -fill white -pointsize 32  -annotate +30+139 'TYPE PASSWORD TO UNLOCK' \
    /mnt/drive/pics/locks/output/lockimage.png

