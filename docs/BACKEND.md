# The hosted backend

The headset never talks to Claude directly. Peek, chapter experiences and uploaded books' rooms all go through Fable's
preparation service (`interpreter/`). In development the service runs on the owner's Mac, which the headset reaches
over `adb reverse`. For the competition's judges, and for any reader, it runs on one cloud VM. This document covers
that VM.

## Shape

```
headset ──HTTPS──> Caddy (VM, :443) ──/k/<access key>/…──> fable-interpreter (127.0.0.1:8787) ──> Claude API
                                                                     └── Blender 5.2.3 (CPU, sandboxed) for rooms and thumbnails
```

- **One VM.** Ubuntu 24.04, CPU only. 16 vCPU recommended, 8 at least. 80 GB disk.
- **Caddy** terminates HTTPS. It gets the certificate from Let's Encrypt for the VM's name: either a real domain, or
  `<ip-with-dashes>.sslip.io`, a public name that resolves to the IP with no DNS set-up. Only paths under
  `/k/<access key>/` reach the service; everything else is 404. The access key is built into the app.
- **The service** runs as the unprivileged user `fable` under systemd. Hardening:
  - read-only system
  - writes only to `/opt/fable/out` and `/var/lib/fable`
  - the Claude key in `/etc/fable/env`, root-only, given to the service by systemd
- **Blender** builds rooms on the CPU. Chapter thumbnails use Cycles on the CPU, not EEVEE, because EEVEE needs a GPU
  (`FABLE_THUMB_ENGINE=CYCLES`).

## What protects it

| Risk | Guard |
|---|---|
| Anyone calling the service | The access-key path in Caddy. It ships inside the APK, so it stops scanners and casual use, not a determined person. |
| One client running up the Claude bill | Per-client rate limits in public mode (`internal/guard`): 15 costly requests at once, then 60 an hour (Peek, interpret, chapter and room preparation). Everything else: 240 a minute. Over the limit: 429, which the headset already treats as "try again". |
| Total cost | `--daily-claude-calls` (default 1500 on the VM) caps Claude calls per UTC day. Past it, calls fail with "daily limit". Room jobs wait 30 minutes and retry; chapters can be asked for again. |
| One headset filling the room queue | `--rooms-books-per-client 2`: at most two uploaded books in progress per client. Clients are identified by a hash of the address Caddy reports. |
| Claude-written room scripts | roomgen's script check filters them. On the VM, Blender also runs inside **bubblewrap** (`--sandbox`): no network, its own process tree (so it cannot read the service's environment), the system read-only, and only that room's work folder writable. `deploy/provision.sh` checks bubblewrap works and turns it off with a warning if not. |
| "Local only" tools reached through the proxy | Behind Caddy every request comes from 127.0.0.1. `guard.IsLocal` also requires that no `X-Forwarded-For` header is present, so `/rooms/rebuild` stays owner-only. |
| The access key in logs | The app logs only the host (`FableService.Describe`). Caddy's log replaces the request path. |

## Deploying

1. Create the VM (Ubuntu 24.04) with your SSH key for root, and note its IP.
2. From the Mac: `deploy/deploy.sh <ip>`. Optional flags:
   - `--domain fable.example.com`, after pointing the name at the IP
   - `--user ubuntu`, for a non-root login with sudo (not yet supported: use root)

   It provisions the VM (`deploy/provision.sh`), cross-compiles the service, and copies:
   - `blender/*.py`, `content/`, `schema/`, `book/`
   - the built places' glTF models, for thumbnails
   - on the first deploy only, the chapter experiences already prepared on the Mac

   Then it installs the Claude key from `~/.config/fable/env` (never printed), starts Caddy and the service, and
   checks `https://<host>/k/<key>/health` (and that the bare `/health` gives 404).
3. It writes the app's address to `~/.config/fable/service-url`. The next `FableBuild.BuildApk()` builds it in
   (`Editor/ServiceConfig.cs` writes `Resources/fable-service.txt` for the build and deletes it after; it is
   git-ignored). Without that file a build talks to a Mac over `adb reverse`, as before.
4. Redeploy after code or content changes with the same command. The VM's own work in `out/` is kept, and so is the
   access key.

**Headset address order (`FableService.cs`):**
1. `persistentDataPath/interpreter.txt`, a developer's override
2. the built-in address
3. `http://127.0.0.1:8787`

The editor ignores the built-in address and uses the local service.

## Measured

- A reviewed room's Blender build on the Mac's CPU alone (`FABLE_CYCLES_DEVICE=CPU`): 150 s for a 56k-triangle room
  (bake 128 s). Other builds were running at the time.
- A chapter thumbnail with Cycles on the CPU: 9 s.
- Expected on an 8–16 vCPU VM: roughly 2–4× slower per build. That makes a reviewed room (three builds plus Claude)
  about 20–35 minutes, inside the 15–30 minutes per chapter the owner set, at the high end.
- **Not yet measured on a VM.**

## Deployed (2026-11-04)

- **The server:** a DigitalOcean Basic droplet in London: 4 shared vCPU, 8 GB, 154 GB disk, Ubuntu 24.04. The
  CPU-Optimized plans weren't available in US regions, and the owner chose the smaller size for cost. It is at
  `https://178-62-123-9.sslip.io`; the app's full address, with its key, is only in `~/.config/fable/service-url`.
- **Settings:** one review round per room (`ROOM_REVIEW=1` in `fable.service`), not two, for build time.
- **Sandbox:** Ubuntu 24.04 blocks unprivileged user namespaces through AppArmor, so at first bubblewrap failed
  ("loopback: Failed RTM_NEWADDR"). `provision.sh` now installs an AppArmor profile that allows them for
  `/usr/bin/bwrap` alone, and the service runs with `--sandbox`.
- **Measured on the droplet:**
  - one sandboxed roomgen build of a 29k-triangle room: 333 s (check views 179 s, bake 151 s)
  - so a reviewed room (two builds plus Claude) takes about 15 minutes, and a book's three rooms about 45–50
  - a Peek through HTTPS from the Mac: 18 s, including the Claude call
  - requests without the access key get 404

## Not done yet

- A headset build that uses the hosted address, run on the Quest.
- `--user` other than root.
- Storage clean-up for old uploaded books. About 10 MB a book, so an 80 GB disk lasts well past judging.
- A status page or alerting. `journalctl -u fable` on the VM, and `/health` behind the key.
