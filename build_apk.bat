@echo off
wsl -e /bin/bash -c "export PATH=/home/seniorcoder/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; export HOME=/home/seniorcoder; cd /home/seniorcoder/vcm_build; yes | buildozer android debug"
