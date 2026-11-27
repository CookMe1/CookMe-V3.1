#!/bin/bash
# Double-click to add photos to the Grubly recipes. It asks for your Pexels key (pasted, not saved anywhere).
# Runs by itself, hour after hour, until every recipe has a photo or has no match. Safe to stop and start again.
cd "$(dirname "$0")"
clear
echo "Grubly photo loader"
echo "-------------------"
echo "Paste your Pexels API key and press Enter (nothing will show as you paste):"
read -s PEXELS_API_KEY
export PEXELS_API_KEY
if [ -z "$PEXELS_API_KEY" ]; then echo "No key entered. Close this window and try again."; exit 1; fi
pip3 install -q requests 2>&1 | tail -1
echo
echo "Starting. At most 199 Pexels searches an hour; it waits by itself at the limit, retries after any error, and carries on overnight."
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
