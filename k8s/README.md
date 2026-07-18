# k8s layout (management plane)

Production target: **k3s on the gaming notebook**.  
Desktop demo: **k3d** (k3s-in-Docker) on this machine.

```
k8s/
  base/                 # namespaces, ResourceQuota, LimitRange
  job-hunting/          # API + Postgres + Ollama ExternalName
  video-analysis/       # reserved (Jobs come later)
```

## Desktop demo (management first)

Prereq: Docker Desktop running, `k3d`, `kubectl`.

```powershell
powershell -File .\scripts\demo-up.ps1
kubectl -n job-hunting port-forward svc/job-hunting-api 8000:8000
powershell -File .\scripts\smoke_test.ps1
```

Tear down:

```powershell
powershell -File .\scripts\cluster-destroy-demo.ps1
```

## Production notebook

1. Install k3s on the notebook (not k3d).
2. Copy secret examples to a private path, set real passwords (never commit).
3. Point `ollama` ExternalName at the Windows host gateway used by that k3s install.
4. `kubectl apply` base → secrets → job-hunting (same manifests).

`docker-compose.test.yml` remains a non-k8s smoke fallback only.
