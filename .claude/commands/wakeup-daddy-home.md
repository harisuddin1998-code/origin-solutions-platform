---
description: Wake up Origin Solutions — start the server VM and bring every site back after a power cut
---
The user said "wakeup daddy home". Bring the whole Origin Solutions platform back online:

1. Run the wakeup script:
   `powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\HarisDB\vm-autostart\wakeup.ps1"`
   (it clears stale VMware locks and starts the server VM "Ubuntu 64-bit (2)" headless — idempotent, safe if already running).
2. Wait ~30–60s for the VM to boot, then confirm the `originsolutions` Cloudflare tunnel reconnected:
   `& "C:\Users\HarisDB\toolchain\cloudflared\cloudflared.exe" tunnel list` — it should show connections for `originsolutions`.
3. Verify the platform is live: `https://app.originssolutions.com/` should return 302 → /login (not Cloudflare Error 1033), and spot-check a couple of client sites (e.g. almurad, elite) for 200/302.
4. Report to the user in Roman Urdu which sites are up.

Background/paths are in memory ([[infra-topology]], [[restore-after-power-cut]]).
