#!/bin/bash

echo "Remove all timetable files ..."
rm -f tt*

echo "Removing'adjacency'..."
rm -f adjacency

echo "Removing 'startstations.sh' ..."
rm -f startstations.sh

# Comment it if you wish not to compile the buildrandomtimetables.c yourself
echo "Removing 'buildrandomtimetables' file..."
rm -f buildrandomtimetables

echo "Cleanup completed."

while read pid; do
    kill -SIGTERM $pid
    wait $pid  # Optional: wait for the process to exit
done < server_pids.txt