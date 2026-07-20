# video-analysis workloads
#
# Host path (Windows): Documents\HomeLLM\videos\
# Mounted in-cluster as hostPath /homellm-media → PVC video-media-pvc → /media in pods
#
# Layout:
#   inbox/ work/ rounds/ state/ done/ failed/
#
# Ingest: services/video-ingest-api
# Segmenter: homellm/valorant-segmenter:dev
# Analyzer:  homellm/valorant-analyzer:dev
