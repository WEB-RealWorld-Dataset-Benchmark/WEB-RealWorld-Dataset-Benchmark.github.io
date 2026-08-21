#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "HF_TOKEN is required" >&2
  exit 2
fi

repo="WorldEngineAI/WEB-Dataset"
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
tmp_root="$(mktemp -d)"
trap 'rm -rf "$tmp_root"' EXIT

count=0
shard_index="${SHARD_INDEX:-0}"
shard_total="${SHARD_TOTAL:-1}"
while IFS= read -r sample; do
  task="$(basename "$(dirname "$sample")")"
  filename="$(basename "$sample")"
  episode="${filename%.mp4}"
  episode="${episode%.h264}"
  remote_file="${episode}.mp4"
  left="$tmp_root/${task}-${episode}-left.mp4"
  right="$tmp_root/${task}-${episode}-right.mp4"
  output="$tmp_root/${task}-${episode}-three-view.mp4"
  base="https://huggingface.co/datasets/${repo}/resolve/main/${task}/videos"

  if [[ "$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$sample")" == "960" ]]; then
    echo "[skip] ${task}/${filename} is already three-view"
    continue
  fi

  echo "[$((count + 1))] ${task}/${filename}"
  curl --fail --location --silent --show-error --retry 3 --connect-timeout 20 --max-time 300 \
    -H "Authorization: Bearer ${HF_TOKEN}" \
    -o "$left" \
    "$base/observation.images.cam_left_wrist/chunk-000/$remote_file"
  curl --fail --location --silent --show-error --retry 3 --connect-timeout 20 --max-time 300 \
    -H "Authorization: Bearer ${HF_TOKEN}" \
    -o "$right" \
    "$base/observation.images.cam_right_wrist/chunk-000/$remote_file"

  ffmpeg -nostdin -hide_banner -loglevel error -y \
    -i "$left" -i "$sample" -i "$right" \
    -filter_complex \
      "[0:v]scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2,fps=30[left];[1:v]scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2,fps=30[head];[2:v]scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2,fps=30[right];[left][head][right]hstack=inputs=3[out]" \
    -map "[out]" -an -c:v libx264 -preset medium -crf 27 \
    -pix_fmt yuv420p -movflags +faststart -shortest "$output"

  mv "$output" "$sample"
  rm -f "$left" "$right"
  count=$((count + 1))
done < <(find assets -mindepth 2 -maxdepth 2 -type f -name '*.mp4' | sort | awk -v i="$shard_index" -v n="$shard_total" 'NR % n == i')

echo "Built $count three-view sample videos."
