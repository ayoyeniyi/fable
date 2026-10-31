// Second line of defence: Unity re-validates every script before executing it, whether it came
// from the bundled baseline or from the interpreter over the network.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json;

namespace Fable
{
    public static class ScriptValidator
    {
        static readonly Regex SentenceId = new("^[a-z-]+:[0-9]{3}$");
        static readonly string[] Appears = { "instant", "fade", "grow", "settle" };
        static readonly string[] Vanishes = { "instant", "fade", "shrink" };

        public static SceneScript Parse(string json)
        {
            var settings = new JsonSerializerSettings { MissingMemberHandling = MissingMemberHandling.Error };
            return JsonConvert.DeserializeObject<SceneScript>(json, settings);
        }

        static bool InRange(float? v, float lo, float hi) => v == null || (v >= lo && v <= hi);

        public static List<string> Validate(SceneScript s, SceneManifest m, ICollection<string> sentenceIds)
        {
            var errs = new List<string>();
            void Add(string e) => errs.Add(e);
            if (s == null) { Add("script is null"); return errs; }
            if (s.Version != 1) Add("version must be 1");
            if (s.SceneId != m.SceneId) Add($"sceneId '{s.SceneId}' must be '{m.SceneId}'");
            if (s.Title != null && s.Title.Length > 80) Add("title longer than 80 chars");
            if (s.Environment == null) { Add("environment missing"); }
            else
            {
                if (s.Environment.Prefab != m.Environment) Add($"environment.prefab '{s.Environment.Prefab}' must be '{m.Environment}'");
                if (!m.Ambiences.Contains(s.Environment.Ambience)) Add($"environment.ambience '{s.Environment.Ambience}' unknown");
                if (!InRange(s.Environment.Exposure, -2, 2)) Add("environment.exposure out of [-2,2]");
                if (!InRange(s.Environment.Fog, 0, 1)) Add("environment.fog out of [0,1]");
            }
            if (s.Beats == null || s.Beats.Count == 0 || s.Beats.Count > 40) Add("beats must have 1..40 items");
            var seen = new HashSet<string>();
            string prev = null;
            for (int i = 0; i < (s.Beats?.Count ?? 0); i++)
            {
                var b = s.Beats[i]; var p = $"beats[{i}]";
                if (b.SentenceId == null || !SentenceId.IsMatch(b.SentenceId)) Add($"{p}.sentenceId malformed");
                else if (!sentenceIds.Contains(b.SentenceId)) Add($"{p}.sentenceId '{b.SentenceId}' not in passage");
                if (b.SentenceId != null && !seen.Add(b.SentenceId)) Add($"{p}.sentenceId repeated");
                if (prev != null && b.SentenceId != null && string.CompareOrdinal(b.SentenceId, prev) < 0) Add($"{p} out of reading order");
                prev = b.SentenceId;
                if (!string.IsNullOrEmpty(b.Focus) && !m.Anchors.ContainsKey(b.Focus)) Add($"{p}.focus '{b.Focus}' unknown anchor");
                if (b.Actions == null) { Add($"{p}.actions missing"); continue; }
                if (b.Actions.Count > 8) Add($"{p} has more than 8 actions");
                for (int j = 0; j < b.Actions.Count; j++)
                {
                    var a = b.Actions[j]; var q = $"{p}.actions[{j}]";
                    var subject = a.Type == "animate" ? a.Target : a.Asset;
                    if (a.Type != "remove" && subject != null && b.SentenceId != null && m.IntroducedBy != null &&
                        m.IntroducedBy.TryGetValue(subject, out var introducedAt) && string.CompareOrdinal(b.SentenceId, introducedAt) < 0)
                        Add($"{q} uses '{subject}' on {b.SentenceId}, before the text introduces it at {introducedAt}");
                    switch (a.Type)
                    {
                        case "place":
                            if (a.Asset == null || !m.Assets.ContainsKey(a.Asset)) Add($"{q}.asset '{a.Asset}' unknown");
                            if (a.Anchor == null || !m.Anchors.ContainsKey(a.Anchor)) Add($"{q}.anchor '{a.Anchor}' unknown");
                            if (a.Offset != null && (a.Offset.Length != 3 || a.Offset.Any(c => c < -20 || c > 20))) Add($"{q}.offset invalid");
                            if (!InRange(a.YawDegrees, -180, 180)) Add($"{q}.yawDegrees out of range");
                            if (!InRange(a.Scale, 0.05f, 20)) Add($"{q}.scale out of range");
                            if (a.Appear != null && !Appears.Contains(a.Appear)) Add($"{q}.appear invalid");
                            break;
                        case "move":
                            if (a.Asset == null || !m.Assets.ContainsKey(a.Asset)) Add($"{q}.asset '{a.Asset}' unknown");
                            if (a.Anchor == null || !m.Anchors.ContainsKey(a.Anchor)) Add($"{q}.anchor '{a.Anchor}' unknown");
                            if (!InRange(a.DurationSeconds, 0.1f, 20)) Add($"{q}.durationSeconds out of range");
                            if (a.Ease != null && a.Ease != "smooth" && a.Ease != "linear" && a.Ease != "settle") Add($"{q}.ease invalid");
                            break;
                        case "remove":
                            if (a.Asset == null || !m.Assets.ContainsKey(a.Asset)) Add($"{q}.asset '{a.Asset}' unknown");
                            if (a.Vanish != null && !Vanishes.Contains(a.Vanish)) Add($"{q}.vanish invalid");
                            break;
                        case "animate":
                            if (a.Target == null || !m.Clips.TryGetValue(a.Target, out var clips)) Add($"{q}.target '{a.Target}' has no clips");
                            else if (!clips.Contains(a.Clip)) Add($"{q}.clip '{a.Clip}' not supported for '{a.Target}'");
                            if (!InRange(a.DurationSeconds, 0.1f, 20)) Add($"{q}.durationSeconds out of range");
                            break;
                        case "light":
                            if (a.Light == null || !m.Lights.Contains(a.Light)) Add($"{q}.light '{a.Light}' unknown");
                            if (!InRange(a.Intensity, 0, 4)) Add($"{q}.intensity out of [0,4]");
                            if (a.Kelvin != null && (a.Kelvin < 1500 || a.Kelvin > 8000)) Add($"{q}.kelvin out of range");
                            if (!InRange(a.DurationSeconds, 0, 20)) Add($"{q}.durationSeconds out of range");
                            break;
                        case "sound":
                            if (a.Sound == null || !m.Sounds.Contains(a.Sound)) Add($"{q}.sound '{a.Sound}' unknown");
                            if (a.Anchor != null && !m.Anchors.ContainsKey(a.Anchor)) Add($"{q}.anchor '{a.Anchor}' unknown");
                            if (!InRange(a.Volume, 0, 1)) Add($"{q}.volume out of [0,1]");
                            break;
                        case "readerScale":
                            if (a.Anchor == null || !m.Anchors.ContainsKey(a.Anchor)) Add($"{q}.anchor '{a.Anchor}' unknown");
                            if (a.Scale == null || a.Scale < 0.1f || a.Scale > 10) Add($"{q}.scale required in [0.1,10]");
                            if (a.DurationSeconds == null || a.DurationSeconds < 3 || a.DurationSeconds > 12) Add($"{q}.durationSeconds required in [3,12]");
                            if (a.Scale != null && Math.Abs(a.Scale.Value - 1f) > 1e-4f && !string.IsNullOrEmpty(m.ReaderScaleFrom) && b.SentenceId != null &&
                                string.CompareOrdinal(b.SentenceId, m.ReaderScaleFrom) < 0) Add($"{q} changes the reader's size before {m.ReaderScaleFrom}");
                            break;
                        default: Add($"{q}.type '{a.Type}' unknown"); break;
                    }
                }
            }
            return errs;
        }
    }
}
