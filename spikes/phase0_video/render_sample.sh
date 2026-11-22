#!/usr/bin/env bash
# Render 3 images into a 15 s 1080x1920 H.264/AAC (silent, stereo 48 kHz) 30 fps MP4.
# Usage: render_sample.sh img1.jpg img2.jpg img3.jpg [out.mp4]
# Each image shows 6 s with 1 s crossfades: 3*6 - 2*1 = 16 s, trimmed to 15 s.
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: $0 img1 img2 img3 [out.mp4]" >&2
  exit 2
fi
command -v ffmpeg >/dev/null || { echo "ffmpeg not found" >&2; exit 3; }
command -v ffprobe >/dev/null || { echo "ffprobe not found" >&2; exit 3; }

OUT="${4:-out_15s.mp4}"
W=1080; H=1920; FPS=30; SEG=6; XF=1

kb() { # input index -> ken-burns zoom-in clip, SEG seconds
  echo "[$1:v]scale=${W}*2:${H}*2:force_original_aspect_ratio=increase,crop=${W}*2:${H}*2,\
zoompan=z='min(zoom+0.0007,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=$((SEG*FPS)):s=${W}x${H}:fps=${FPS},\
setsar=1,format=yuv420p[v$1]"
}

ffmpeg -y \
  -loop 1 -t "$SEG" -i "$1" -loop 1 -t "$SEG" -i "$2" -loop 1 -t "$SEG" -i "$3" \
  -f lavfi -t 15 -i anullsrc=channel_layout=stereo:sample_rate=48000 \
  -filter_complex "$(kb 0);$(kb 1);$(kb 2);\
[v0][v1]xfade=transition=fade:duration=${XF}:offset=$((SEG-XF))[x1];\
[x1][v2]xfade=transition=fade:duration=${XF}:offset=$((2*SEG-2*XF))[x2];\
[x2]trim=duration=15,setpts=PTS-STARTPTS[vout]" \
  -map "[vout]" -map 3:a \
  -c:v libx264 -profile:v high -pix_fmt yuv420p -r "$FPS" -g $((FPS*2)) -keyint_min $((FPS*2)) -sc_threshold 0 \
  -c:a aac -b:a 128k -ar 48000 -ac 2 \
  -t 15 -movflags +faststart "$OUT"

ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt:format=duration \
  -of default=nw=1 "$OUT"
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,channels,sample_rate -of default=nw=1 "$OUT"

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
W_OUT=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$OUT")
H_OUT=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$OUT")
awk -v d="$DUR" 'BEGIN{exit !(d>=14.8 && d<=15.2)}' || { echo "FAIL: duration $DUR" >&2; exit 1; }
[ "$W_OUT" = "$W" ] && [ "$H_OUT" = "$H" ] || { echo "FAIL: size ${W_OUT}x${H_OUT}" >&2; exit 1; }
echo "OK: ${W_OUT}x${H_OUT}, ${DUR}s"
