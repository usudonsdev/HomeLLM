# Built for Raspberry Pi static hosting (ADR-005).
# Browser calls Windows APIs via Tailscale; this app does not proxy video binaries (ADR-008).

npm install
cp .env.example .env.local   # edit API base URLs

# Desktop demo
npm run dev

# Production static build → deploy to Pi
npm run build
powershell -File ..\..\scripts\deploy-web-pi.ps1
