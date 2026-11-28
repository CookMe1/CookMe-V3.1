#!/bin/bash
# Double-click to add photos to the Grubly recipes. Keys are pasted, never saved anywhere.
# Pixabay is tried first (fast), then Pexels for the ones Pixabay misses. Runs by itself until every recipe has a photo or no match.
cd "$(dirname "$0")"
clear
echo "Grubly photo loader"
echo "-------------------"
echo "Paste your PIXABAY key and press Enter (nothing will show as you paste):"
read -s PIXABAY_API_KEY
echo "Paste your PEXELS key and press Enter (or just press Enter to skip Pexels):"
read -s PEXELS_API_KEY
export PIXABAY_API_KEY PEXELS_API_KEY
if [ -z "$PIXABAY_API_KEY" ] && [ -z "$PEXELS_API_KEY" ]; then echo "No key entered. Close this window and try again."; exit 1; fi
pip3 install -q requests 2>&1 | tail -1
echo
echo "Starting. Pixabay: about 80 searches a minute. Pexels: at most 199 an hour. It waits by itself at the limits and retries after errors."
echo "Leave this window open, the Mac plugged in and the lid open (a closed lid sends the Mac to sleep)."
echo
for pass in $(seq 1 40); do
  caffeinate -i python3 scripts/fill_images.py --file data/staging/open_new.json,data/staging/open_new2.json,data/staging/wikibooks_approved.json --priority drink,sauce,snack 2>&1 | tee /tmp/grubly_photos_last.log
  if grep -q " 0 recipes still have no image" /tmp/grubly_photos_last.log; then echo "All done."; break; fi
  echo "Pass $pass ended with recipes still to do. Trying again in 10 minutes..."; sleep 600
done
echo
echo "Finished. Tell Claude you are done."
read -n 1 -s -r -p "Press any key to close."
