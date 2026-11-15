// How long the reader can expect to wait, said plainly and never promised short.
//
// Two sources, the better one first:
//   the service      chapter experiences and uploaded books' rooms: the status answers carry etaSeconds, worked out on
//                    the server from its own recent jobs and its queue (interpreter/internal/eta)
//   this headset     Peek and Translate (and the fallback for the above when an older service sends no estimate): a
//                    running average per kind of wait, kept with the reader's preferences (Prefs.WaitSeconds) and
//                    seeded from the measured times in docs/LATENCY.md and docs/BACKEND.md
// Wording rounds up and says "about"; past the expected time it says the wait is longer than usual rather than counting
// below zero. A cached answer is instant and nothing is said.
using System;
using System.Collections.Generic;
using UnityEngine;

namespace Fable
{
    public static class WaitEstimate
    {
        /// Seeds, in seconds, before this headset has measured anything (rounded up from the measured times):
        /// peek 18 s through HTTPS to the hosted service; translate 2 s; a chapter's experience 13 to 104 s on the Mac
        /// and slower on the 4-vCPU VM; a room 15 minutes on the VM, plus the wait for the rooms ahead of it.
        static readonly Dictionary<string, float> Seeds = new() { ["peek"] = 20f, ["translate"] = 4f, ["chapter"] = 120f, ["room"] = 1000f };

        public static float Seed(string kind) => Seeds.TryGetValue(kind, out var s) ? s : 30f;

        /// The expected wait for a kind, in seconds: this headset's running average, or the seed.
        public static float Expected(string kind)
        {
            var p = ProgressStore.LoadPrefs();
            return p.WaitSeconds != null && p.WaitSeconds.TryGetValue(kind, out var s) && s > 0 ? s : Seed(kind);
        }

        /// A wait that was measured to the end (not a cache hit, not given up). Outliers are clipped so one stalled
        /// network does not make every later estimate absurd; the average leans 30% towards each new wait.
        public static void Record(string kind, float seconds)
        {
            if (!(seconds > 0)) return;
            var seed = Seed(kind);
            seconds = Mathf.Clamp(seconds, seed / 10f, seed * 6f);
            var p = ProgressStore.LoadPrefs(); p.WaitSeconds ??= new Dictionary<string, float>();
            p.WaitSeconds[kind] = p.WaitSeconds.TryGetValue(kind, out var was) && was > 0 ? was * 0.7f + seconds * 0.3f : (seed + seconds) / 2f;
            ProgressStore.SavePrefs(p);
        }

        /// "a few seconds", "about 20 seconds", "about a minute", "about 4 minutes", "about 15 minutes", "about an hour":
        /// always rounded up.
        public static string About(float seconds)
        {
            if (seconds <= 5) return "a few seconds";
            if (seconds < 55) return $"about {Mathf.CeilToInt(seconds / 5f) * 5} seconds";
            if (seconds <= 75) return "about a minute";
            int min = Mathf.CeilToInt(seconds / 60f);
            if (min < 10) return $"about {min} minutes";
            if (min < 58) return $"about {Mathf.CeilToInt(min / 5f) * 5} minutes";
            int h = Mathf.CeilToInt(seconds / 3600f);
            return h <= 1 ? "about an hour" : $"about {h} hours";
        }

        /// What is left, said plainly: "about 15 seconds left", or "taking longer than usual" once past the expected time.
        public static string Left(float elapsed, float expected)
        {
            float left = expected - elapsed;
            if (left > 0) return About(left) + " left";
            return elapsed > expected * 2f ? "taking much longer than usual" : "taking a little longer than usual";
        }

        /// How far along, 0 to 1, for a progress bar: linear to 90% at the expected time, then creeping towards 98%
        /// (a bar that sits full while nothing arrives is worse than one that slows).
        public static float Fraction(float elapsed, float expected)
        {
            if (expected <= 0) return 0;
            float x = elapsed / expected;
            return x <= 1f ? 0.9f * x : 0.98f - 0.08f * Mathf.Exp(-(x - 1f) * 2f);
        }

        /// A text bar of ten cells (■ done, □ to come) for places that are text only.
        public static string Bar(float fraction)
        {
            int n = Mathf.Clamp(Mathf.RoundToInt(fraction * 10), 0, 10);
            return new string('■', n) + new string('□', 10 - n);
        }

        /// Seconds since an ISO 8601 UTC time saved earlier (0 if it cannot be read).
        public static float Since(string isoUtc) =>
            DateTime.TryParse(isoUtc, null, System.Globalization.DateTimeStyles.RoundtripKind, out var t) ? (float)Math.Max(0, (DateTime.UtcNow - t).TotalSeconds) : 0f;
    }
}
