# Step In and Peek latencies

Measured 2026-11-03 on the owner's Mac (Apple M3, 16 GB, macOS 26.7.1) over Wi-Fi (en0, private LAN 10.45.1.x) against `api.anthropic.com`. Interpreter built from `interpreter/` that day (`go build -o out/fable-interpreter ./cmd/fable-interpreter`), run as `fable-interpreter serve --addr 127.0.0.1:8787 --wait 120s` (Opus) and `--addr 127.0.0.1:8788 --model claude-haiku-5-5 --wait 120s` (Haiku), both at once, one request at a time per server. Times are the HTTP round trip of `POST /interpret` / `POST /peek` from a Python `urllib` client on the same Mac (`out/latency/timeit.py`); the server's own `interpret <scene>: N beats in T, K attempt(s)` log lines agree to within 1 ms for every live run. Live runs sent `noCache: true, waitSeconds: 120`; the cache was copied aside first and restored byte for byte afterwards (`out/cache/hall-of-doors.json`, `out/cache/mad-tea-party.json` unchanged, SHA-256 checked). Raw logs, the generated scripts and the timing script are under `out/latency/` (not in the repo).

Model choice is `--model <id>` or `FABLE_MODEL` on `generate`, `serve` and `mock`; the default is `claude-opus-5-5`. Nothing had to be added.

## Results

"First attempt" is how many of the runs validated on the model's first reply; the others took the one repair round (`internal/llm`: validator findings sent back once). Every script below passed `fable-interpreter validate` again offline.

| scene | mode | model | runs | min s | median s | max s | first attempt | notes |
|---|---|---|---|---|---|---|---|---|
| hall-of-doors | cache hit (`X-Fable-Cache: hit`) | n/a | 5 + 3 curl | 0.0008 | 0.016 | 0.034 | n/a | curl `%{time_total}` 0.76 to 0.94 ms; Python client 15 to 34 ms (client overhead); server handler 0 to 1 ms including re-validation of the cached script |
| mad-tea-party | cache hit | n/a | 5 | 0.016 | 0.016 | 0.017 | n/a | same shape as above |
| hall-of-doors | live, reader at the passage end (`readingPosition: hall-of-doors:013`) | claude-opus-5-5 | 3 | 24.7 | 30.0 | 30.7 | 3 / 3 | 11, 9, 8 beats of 13 sentences |
| hall-of-doors | live, reader at the passage end | claude-haiku-5-5 | 3 | 20.8 | 21.3 | 24.5 | 2 / 3 | 8, 7, 8 beats; run 1 needed the repair round and then passed |
| mad-tea-party | live, reader at the passage end (`mad-tea-party:017`) | claude-opus-5-5 | 3 | 19.7 | 20.3 | 20.5 | 3 / 3 | 12, 13, 12 beats of 17 sentences |
| mad-tea-party | live, reader at the passage end | claude-haiku-5-5 | 3 | 10.2 | 12.1 | 15.2 | 3 / 3 | 7, 10, 8 beats |
| hall-of-doors | live, reader at the first sentence (`hall-of-doors:001`) | claude-opus-5-5 | 3 | 6.5 | 6.5 | 8.2 | 3 / 3 | 2 beats each: Opus honours the reading position and stages only what has been read |
| hall-of-doors | live, reader at the first sentence | claude-haiku-5-5 | 3 | 14.7 | 17.3 | 22.5 | 1 / 3 | 7 and 6 beats (Haiku stages past the reading position); run 2 was still invalid after repair (`readerScale` on sentence 007 before the text shrinks Alice at 012) and answered `502` after 17.3 s; run 3 passed after repair |
| mad-tea-party | live, reader at the first sentence (`mad-tea-party:001`) | claude-opus-5-5 | 3 | 10.0 | 10.1 | 14.8 | 3 / 3 | 2 beats each |
| mad-tea-party | live, reader at the first sentence | claude-haiku-5-5 | 3 | 5.5 | 6.1 | 7.0 | 3 / 3 | 1 to 2 beats |
| Peek "golden key" (alice, `alice:c01.p013.s01`) | live `POST /peek` | claude-opus-5-5 | 3 | 13.8 | 15.3 | 16.2 | 3 / 3 | 9, 6, 7 parts, 3 labels, 664 to 1508 triangles |
| Peek "golden key" | live `POST /peek` | claude-haiku-5-5 | 3 | 9.1 | 9.1 | 9.6 | 3 / 3 | 7, 4, 4 parts, 3 labels, 420 to 716 triangles |

Validity over all 30 live calls: 27 valid on the first attempt, 2 valid after the repair round (both Haiku, hall), 1 still invalid after repair (Haiku, hall, position 001). Opus: 18 / 18 first attempt. Haiku: 9 / 12 scripts and 3 / 3 Peek models on the first attempt. Nothing invalid ever reached the cache or the client; the failed run answered `502`.

## What the numbers mean for the headset

- A pinch on a passage whose script is cached is answered in about a millisecond; the Unity request itself (local Wi-Fi to the Mac) is the only cost.
- A first live Step In at the end of a passage is 20 to 31 s on Opus and 10 to 25 s on Haiku. Haiku is roughly 1.5x faster on the hall and 1.7x on the tea party, writes fewer beats, and is the only model that needed repairs. Opus is the default.
- The headset never waits that long. `SceneDirector.cs` sends no `waitSeconds` (server default `--wait 3s`) and times out at 8 s, so a first live request gets `202 generating` and the page shows the cached or bundled script; the live script lands in `out/cache/` and is served as a hit the next time the passage opens. The same holds for Peek (9 to 16 s): the library and clay models cover the wait.
- A reading position early in the passage makes Opus fast (6 to 8 s for two beats) because it stages only what the reader has reached, which is what the spoiler rule asks for. The validator does not enforce the position (it checks ids against the whole passage), so Haiku's ahead-of-position beats pass; Unity plays beats only as the reader reaches their sentence, so they are not shown early either way.

## Not done

Streaming the script beat by beat and the 20 s rule in the client (give up on live and announce the fallback after 20 s) are still not built; today the client's 8 s request timeout plus the server's background generation and cache stand in for both. Nothing here was measured on a Quest; the Wi-Fi hop from the headset to the Mac is in addition to these numbers.

## Repeating it

```bash
cd interpreter && go build -o ../out/fable-interpreter ./cmd/fable-interpreter && cd ..
set -a; . ~/.config/fable/env; set +a                      # ANTHROPIC_API_KEY, never printed
cp -Rp out/cache out/latency/cache.backup                  # the headset's cache; restore it afterwards
./out/fable-interpreter serve --addr 127.0.0.1:8787 --wait 120s > out/latency/serve.log 2>&1 &
./out/fable-interpreter serve --addr 127.0.0.1:8788 --wait 120s --model claude-haiku-5-5 > out/latency/serve.haiku.log 2>&1 &
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' -H 'Content-Type: application/json' \
  -d '{"sceneId":"hall-of-doors"}' 127.0.0.1:8787/interpret                                    # cache hit
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' -H 'Content-Type: application/json' \
  -d '{"sceneId":"hall-of-doors","readingPosition":"hall-of-doors:013","noCache":true,"waitSeconds":120}' 127.0.0.1:8787/interpret
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' -H 'Content-Type: application/json' \
  -d '{"book":"alice","sentenceId":"alice:c01.p013.s01","phrase":"golden key","noCache":true,"waitSeconds":120}' 127.0.0.1:8788/peek
```

The server log says how long each generation took and how many attempts it needed; `fable-interpreter mock` prints the same for Peek from the command line.
