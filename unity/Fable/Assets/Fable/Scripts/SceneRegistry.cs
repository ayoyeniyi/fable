// Resolves manifest ids to scene objects. The environment root is the imported GLB whose nodes
// are named after manifest ids: "anchor.table.top", "prop.golden-key", "door.little", lights "Lamp3_Light".
using System.Collections.Generic;
using UnityEngine;

namespace Fable
{
    public class SceneRegistry : MonoBehaviour
    {
        public Transform EnvironmentRoot;
        readonly Dictionary<string, Transform> anchors = new();
        readonly Dictionary<string, Transform> assets = new();
        readonly Dictionary<string, List<Light>> lightGroups = new();
        readonly Dictionary<string, AudioClip> clips = new();

        // the lookup tables are not serialized: rebuild them from the scene when play starts
        void Awake() { if (EnvironmentRoot && anchors.Count == 0) Build(EnvironmentRoot); }

        public void Build(Transform root)
        {
            EnvironmentRoot = root;
            anchors.Clear(); assets.Clear(); lightGroups.Clear();
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                var n = t.name;
                if (n.StartsWith("anchor.")) anchors[n.Substring(7)] = t;
                else if (IsAssetName(n)) assets[n] = t;
            }
            foreach (var l in root.GetComponentsInChildren<Light>(true))
            {
                string id = LightId(l.transform);
                if (!lightGroups.TryGetValue(id, out var list)) lightGroups[id] = list = new List<Light>();
                list.Add(l);
                l.shadows = LightShadows.None; // baked; realtime shadows are too costly on Quest 2
            }
            foreach (var c in Resources.LoadAll<AudioClip>("Audio")) clips[c.name] = c;
            if (clips.Count == 0) foreach (var c in Object.FindObjectsByType<AudioSource>(FindObjectsSortMode.None)) if (c.clip) clips[c.clip.name] = c.clip;
            Debug.Log($"[Fable] registry: {anchors.Count} anchors, {assets.Count} assets, {lightGroups.Count} light groups, {clips.Count} clips");
        }

        public static bool IsAssetName(string n) => n.StartsWith("prop.") || n.StartsWith("fx.") || n.StartsWith("char.") || n == "door.little";

        /// Hall of Doors lights keep their Blender names (Lamp*, Garden*); newer scenes name the light, or a parent
        /// empty, by its manifest id ("light.sun", "light.sun.2" groups as "light.sun").
        static string LightId(Transform t)
        {
            for (var p = t; p; p = p.parent)
            {
                if (p.name.StartsWith("light."))
                {
                    var parts = p.name.Split('.');
                    return parts.Length > 2 && int.TryParse(parts[parts.Length - 1], out _) ? string.Join(".", parts, 0, parts.Length - 1) : p.name;
                }
                if (p.name.StartsWith("env.")) break;
            }
            return t.name.StartsWith("Lamp") ? "lamp.row" : t.name.StartsWith("Garden") ? "light.garden" : "light.fill";
        }

        public Transform Anchor(string id) => anchors.TryGetValue(id, out var t) ? t : null;

        /// Diorama pivot: the hall has hall.centre; newer scenes author scene.centre.
        public Transform Centre => Anchor("scene.centre") ?? Anchor("hall.centre") ?? EnvironmentRoot;

        /// Where the reader stands once the scene is full size.
        public Transform ReaderStand
        {
            get
            {
                foreach (var id in new[] { "reader.table", "reader.entrance", "reader.path", "reader.gate" }) { var a = Anchor(id); if (a) return a; }
                foreach (var kv in anchors) if (kv.Key.StartsWith("reader.")) return kv.Value;
                return EnvironmentRoot;
            }
        }
        public Transform Asset(string id) => assets.TryGetValue(id, out var t) ? t : null;
        public List<Light> Lights(string id) => lightGroups.TryGetValue(id, out var l) ? l : null;
        public AudioClip Clip(string id) => clips.TryGetValue(id, out var c) ? c : null;
        public IEnumerable<string> AssetIds => assets.Keys;
        public IEnumerable<string> LightIds => lightGroups.Keys;
    }
}
