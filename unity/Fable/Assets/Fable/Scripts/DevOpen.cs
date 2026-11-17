// Developer hook for measuring rooms on the headset without anyone navigating: if <persistentDataPath>/dev-open.txt
// exists and holds "<bookSlug> <SceneName>", the app opens that book in that scene at start (once per launch).
// Push it with: adb push dev-open.txt /sdcard/Android/data/com.fable.alice/files/dev-open.txt
// With no file this does nothing.
using System.IO;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Fable
{
    public static class DevOpen
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void AtStart()
        {
            string path;
            try { path = Path.Combine(Application.persistentDataPath, "dev-open.txt"); if (!File.Exists(path)) return; }
            catch { return; }
            string[] parts;
            try { parts = File.ReadAllText(path).Trim().Split((char[])null, System.StringSplitOptions.RemoveEmptyEntries); }
            catch (System.Exception e) { Debug.LogWarning($"[Fable] dev-open: unreadable ({e.Message})"); return; }
            if (parts.Length < 2) { Debug.LogWarning("[Fable] dev-open: expected \"<bookSlug> <SceneName>\""); return; }
            string slug = parts[0], scene = parts[1];
            if (!Application.CanStreamedLevelBeLoaded(scene)) { Debug.LogWarning($"[Fable] dev-open: {scene} is not in the build"); return; }
            Debug.Log($"[Fable] dev-open: {slug} in {scene}");
            FlowController.PendingBook = slug;
            SceneManager.LoadScene(scene);
        }
    }
}
