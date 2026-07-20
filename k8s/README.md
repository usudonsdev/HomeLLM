# k8s layout (management plane + Valorant ingest)

Production target: **k3s on the gaming notebook**.  
Desktop demo: **k3d** (k3s-in-Docker) on this machine.

```
k8s/
  base/                 # namespaces, ResourceQuota, LimitRange
  job-hunting/          # API + Postgres + Ollama ExternalName
  video-analysis/       # media hostPath, ingest API, Valorant Jobs
```

## Host video folder

User-facing path on Windows:

```text
Documents\HomeLLM\videos\inbox\
```

`scripts/ensure-video-media-host.ps1` creates it.  
`scripts/cluster-create-demo.ps1` mounts that folder into k3d as `/homellm-media` (see `media-pv.yaml`).

## Desktop demo — management

```powershell
powershell -File .\scripts\demo-up.ps1
kubectl -n job-hunting port-forward svc/job-hunting-api 8000:8000
powershell -File .\scripts\smoke_test.ps1
```

## Desktop demo — Valorant ingest

**Primary UX:** open the Web from any Tailscale client → drag-and-drop upload on `/videos`  
(`POST /v1/jobs/upload` → Windows `video-ingest-api`, default max **32 GiB** ≈ 1h 1080p). Pi never proxies the binary.

```powershell
powershell -File .\scripts\demo-valorant-ingest.ps1
# or full analyze:
powershell -File .\scripts\demo-valorant-analyze.ps1
```

Optional host drop folder (huge files only): `Documents\HomeLLM\videos\inbox\` on the analysis Windows node.

Tear down cluster:

```powershell
powershell -File .\scripts\cluster-destroy-demo.ps1
```

**Note:** If the cluster was created before the Documents mount, recreate it so hostPath works:

```powershell
powershell -File .\scripts\cluster-destroy-demo.ps1
powershell -File .\scripts\cluster-create-demo.ps1
powershell -File .\scripts\cluster-apply-video-analysis.ps1
```

## Production notes

- Copy large VODs to `Documents\HomeLLM\videos\inbox\` on the notebook
- Register with ingest API (`filename` basename only), or use Web DnD for small demos
- Do not proxy multi-GB uploads through the Raspberry Pi
