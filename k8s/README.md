# k8s layout (management plane + Valorant ingest)

Production target: **k3s on the gaming notebook**.  
Desktop demo: **k3d** (k3s-in-Docker) on this machine.

```
k8s/
  base/                 # namespaces, ResourceQuota, LimitRange
  job-hunting/          # API + Postgres + Ollama ExternalName
  video-analysis/       # media PVC, ingest API, Valorant segmenter Jobs
```

## Desktop demo — management

```powershell
powershell -File .\scripts\demo-up.ps1
kubectl -n job-hunting port-forward svc/job-hunting-api 8000:8000
powershell -File .\scripts\smoke_test.ps1
```

## Desktop demo — Valorant ingest (inbox)

Videos are **not** uploaded through the API. Place files in `media/inbox` (via `kubectl cp` in the demo script).

```powershell
powershell -File .\scripts\demo-valorant-ingest.ps1
```

This will:

1. Build/import `video-ingest-api` and `valorant-segmenter`
2. Apply PVC / RBAC / ingest Deployment
3. Seed a short stub mp4 into inbox
4. `POST /v1/jobs` and wait until segmenter Job finishes

Tear down cluster:

```powershell
powershell -File .\scripts\cluster-destroy-demo.ps1
```

## Production notes

- Copy large VODs onto the notebook disk (or Tailscale sync) under the media volume's `inbox/`
- Register with ingest API (`filename` basename only)
- Do not proxy multi-GB uploads through the Raspberry Pi
