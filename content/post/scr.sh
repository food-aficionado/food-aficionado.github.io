#!/bin/bash

for file in *.md; do
  awk -F'"' '/date:/ {
                gsub(/T/, " ", $2);
                gsub(/Z/, "", $2);
                gsub(/-/, " ", $2);
                cmd="date -j -f \"%Y %m %d %H:%M:%S\" \""$2"\" +\"%e %B %Y\"";
                cmd | getline d;
                close(cmd);
                print "date: \"" d "\"";
                next
             }
             {print}' "$file" > temp.md
  mv temp.md "$file"
done
