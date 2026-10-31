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

        public void Build(Transform root)
        {
            EnvironmentRoot = root;
            anchors.Clear(); assets.Clear(); lightGroups.Clear();
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                var n = t.name;
                if (n.StartsWith("anchor.")) anchors[n.Substring(7)] = t;
                else if (n.StartsWith("prop.") || n.StartsWith("fx.") || n == "door.little") assets[n] = t;
            }
            foreach (var l in root.GetComponentsInChildren<Light>(true))
            {
                string id = l.name.StartsWith("Lamp") ? "lamp.row" : l.name.StartsWith("Garden") ? "light.garden" : "light.fill";
                if (!lightGroups.TryGetValue(id, out var list)) lightGroups[id] = list = new List<Light>();
                list.Add(l);
                l.shadows = LightShadows.None; // baked; realtime shadows are too costly on Quest 2
            }
            foreach (var c in Resources.LoadAll<AudioClip>("Audio")) clips[c.name] = c;
            if (clips.Count == 0) foreach (var c in Object.FindObjectsByType<AudioSource>(FindObjectsSortMode.None)) if (c.clip) clips[c.clip.name] = c.clip;
            Debug.Log($"[Fable] registry: {anchors.Count} anchors, {assets.Count} assets, {lightGroups.Count} light groups, {clips.Count} clips");
        }

        public Transform Anchor(string id) => anchors.TryGetValue(id, out var t) ? t : null;
        public Transform Asset(string id) => assets.TryGetValue(id, out var t) ? t : null;
        public List<Light> Lights(string id) => lightGroups.TryGetValue(id, out var l) ? l : null;
        public AudioClip Clip(string id) => clips.TryGetValue(id, out var c) ? c : null;
        public IEnumerable<string> AssetIds => assets.Keys;
    }
}
