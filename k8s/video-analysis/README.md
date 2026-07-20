# video-analysis workloads
#
# Host path (Windows): Documents\HomeLLM\videos\
# Mounted in-cluster as hostPath /homellm-media → PVC video-media-pvc → /media in pods
#
# Layout:
#   inbox/ work/ rounds/ state/ done/ failed/ templates/valorant/
#
# Segmenter: OpenCV logo templates → transition spikes → time fallback
# Analyzer:  keyframes + host Ollama (qwen3.5:9b) → video_matches/rounds
#
# Ingest: services/video-ingest-api
# Segmenter: homellm/valorant-segmenter:dev
# Analyzer:  homellm/valorant-analyzer:dev
