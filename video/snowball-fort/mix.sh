#!/bin/bash
# usage: mix.sh <scratch> <video_noaudio> <out>
S=$1
python3 $S/music.py $S 40 >/dev/null && python3 $S/sfx.py $S
ffmpeg -v error -y -i "$2" -i $S/vo.wav -i $S/music.wav -i $S/sfx.wav -filter_complex \
"[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=5:release=80,loudnorm=I=-15:TP=-1.5:LRA=7,volume=1.0[v];\
[2:a]volume=0.11[m];[3:a]volume=0.9[x];[v][m][x]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.89[a]" \
-map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$3"
