#!/bin/bash
for v in r28 r27b r27 r26d r26c r26b r26 r25c r25b; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "https://dl.google.com/android/repository/android-ndk-${v}-linux.zip")
  echo "NDK ${v}: HTTP ${code}"
done
