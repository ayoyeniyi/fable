// Where the preparation service is (docs/BACKEND.md): Peek, chapter experiences and uploaded books' rooms all ask it.
//
// In order:
//   1. persistentDataPath/interpreter.txt on the headset (a developer's override, e.g. a Mac on the same network);
//   2. on a device build, Resources/fable-service.txt, written at build time by Editor/ServiceConfig.cs from
//      ~/.config/fable/service-url (the hosted server, https://<host>/k/<access key>);
//   3. http://127.0.0.1:8787: the Mac over `adb reverse` on the headset, the local service in the editor.
// The address carries the access key, so it is never logged whole: Describe gives the host only.
using System;
using System.IO;
using UnityEngine;

namespace Fable
{
    public static class FableService
    {
        public const string Local = "http://127.0.0.1:8787";
        static string url;

        public static string Url => url ??= Find();

        /// True when the app talks to the hosted server rather than a Mac.
        public static bool Hosted => !Url.StartsWith("http://127.0.0.1", StringComparison.Ordinal) && !Url.StartsWith("http://localhost", StringComparison.Ordinal);

        /// The address without its access key, for logs.
        public static string Describe(string u = null)
        {
            u ??= Url;
            if (string.IsNullOrEmpty(u)) return "none";
            try { var x = new Uri(u); return x.Scheme + "://" + x.Authority + (x.AbsolutePath.Length > 1 ? "/…" : ""); }
            catch { return "(unreadable address)"; }
        }

        static string Find()
        {
            try
            {
                var f = Path.Combine(Application.persistentDataPath, "interpreter.txt");
                if (File.Exists(f))
                {
                    var t = File.ReadAllText(f).Trim().TrimEnd('/');
                    if (t.Length > 0) { Debug.Log($"[Fable] service from device file: {Describe(t)}"); return t; }
                }
            }
            catch (Exception e) { Debug.LogWarning($"[Fable] service: device file unreadable ({e.Message})"); }
#if !UNITY_EDITOR
            var ta = Resources.Load<TextAsset>("fable-service");
            if (ta && !string.IsNullOrWhiteSpace(ta.text))
            {
                var t = ta.text.Trim().TrimEnd('/');
                Debug.Log($"[Fable] service: {Describe(t)} (built in)");
                return t;
            }
#endif
            Debug.Log($"[Fable] service: {Local} (this machine, or a Mac over adb reverse)");
            return Local;
        }
    }
}
