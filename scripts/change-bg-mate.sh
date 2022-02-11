#!/bin/bash

# images directory
rep="/home/bgudna/Pictures/"

# Create image list from directory
liste=("${rep}/"*)

# Compute the number of images
nbre=${#liste[@]}

# Random select
selection=$((${RANDOM} % ${nbre}))

# Image loading
dconf write /org/mate/desktop/background/picture-filename "'${liste[${selection}]}'"
