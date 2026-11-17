// Frame-cost survey of the built reading rooms, in the editor (no headset needed): draw calls by kind, triangles,
// alpha-tested (cut-out) foliage and its surface area, realtime lights and particle systems. The cut-out foliage is
// what costs most on Quest 2's tiled GPU: every card is overdraw that early depth rejection cannot skip.
//   unity command eval 'return Fable.Editor.FablePerf.Survey("pillaji-forest");'
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Fable.Editor
{
    public static class FablePerf
    {
        public static bool IsCutout(Material m) => m && (m.IsKeywordEnabled("_ALPHATEST_ON") || (m.HasProperty("_AlphaClip") && m.GetFloat("_AlphaClip") > 0.5f)) && m.renderQueue < 3000;

        public static string Survey(string sceneId)
        {
            var def = FableBuild.Scenes.First(d => d.Id == sceneId);
            EditorSceneManager.OpenScene(def.Scene, OpenSceneMode.Single);
            return Describe(sceneId);
        }

        /// The open scene's numbers, one line.
        public static string Describe(string sceneId)
        {
            var env = GameObject.Find("env." + sceneId);
            if (!env) return sceneId + ": no env";
            long tris = 0, cutTris = 0; int draws = 0, cutDraws = 0; float cutArea = 0;
            var top = new System.Collections.Generic.List<(string n, long t, float a)>();
            foreach (var r in env.GetComponentsInChildren<MeshRenderer>(false))
            {
                if (!r.enabled) continue;
                var mf = r.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh) continue;
                var m = mf.sharedMesh; var mats = r.sharedMaterials;
                for (int s = 0; s < m.subMeshCount; s++)
                {
                    long t = m.GetIndexCount(s) / 3; tris += t; draws++;
                    if (s < mats.Length && IsCutout(mats[s]))
                    {
                        cutTris += t; cutDraws++;
                        float a = Area(m, s, r.transform.lossyScale); cutArea += a; top.Add((r.name, t, a));
                    }
                }
            }
            int rt = Object.FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None).Count(l => l.isActiveAndEnabled && l.lightmapBakeType != LightmapBakeType.Baked);
            int ps = env.GetComponentsInChildren<ParticleSystem>(false).Length;
            var sb = new StringBuilder($"{sceneId}: draws={draws} tris={tris / 1000}k cutout draws={cutDraws} tris={cutTris / 1000}k area={cutArea:F0}m2 realtimeLights={rt} particles={ps}");
            foreach (var x in top.OrderByDescending(x => x.a).Take(6)) sb.Append($"\n   {x.n}: {x.t / 1000}k tris {x.a:F0} m2");
            return sb.ToString();
        }

        static float Area(Mesh m, int sub, Vector3 scale)
        {
            var v = m.vertices; var idx = m.GetTriangles(sub); float a = 0;
            for (int i = 0; i < idx.Length; i += 3)
            {
                var p0 = Vector3.Scale(v[idx[i]], scale); var p1 = Vector3.Scale(v[idx[i + 1]], scale); var p2 = Vector3.Scale(v[idx[i + 2]], scale);
                a += Vector3.Cross(p1 - p0, p2 - p0).magnitude * 0.5f;
            }
            return a;
        }

        public static string SurveyAll(string ids)
        {
            var sb = new StringBuilder();
            foreach (var id in ids.Split(',')) sb.AppendLine(Survey(id.Trim()));
            return sb.ToString();
        }
    }
}
