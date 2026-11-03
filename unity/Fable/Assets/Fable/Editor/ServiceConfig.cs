// Writes the hosted service's address into a device build (docs/BACKEND.md).
//
// Before a build: Assets/Resources/fable-service.txt gets the address from the FABLE_SERVICE_URL environment
// variable or ~/.config/fable/service-url (written by deploy/deploy.sh; it carries the access key, so it is never
// committed: the Resources file is git-ignored and removed again after the build). With neither, the build talks to
// a Mac over `adb reverse` as before. The editor never reads the file (FableService skips it there).
using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace Fable.Editor
{
    public class ServiceConfig : IPreprocessBuildWithReport, IPostprocessBuildWithReport
    {
        const string Asset = "Assets/Resources/fable-service.txt";
        public int callbackOrder => 0;

        public static string Configured()
        {
            var env = Environment.GetEnvironmentVariable("FABLE_SERVICE_URL");
            if (!string.IsNullOrWhiteSpace(env)) return env.Trim();
            var f = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".config", "fable", "service-url");
            return File.Exists(f) ? File.ReadAllText(f).Trim() : null;
        }

        public void OnPreprocessBuild(BuildReport report)
        {
            var url = Configured();
            if (string.IsNullOrEmpty(url))
            {
                Remove();
                Debug.Log("[FableBuild] service: none configured; the build uses a Mac over adb reverse (http://127.0.0.1:8787)");
                return;
            }
            if (!url.StartsWith("https://", StringComparison.Ordinal))
                throw new BuildFailedException($"the service address must be https (Android blocks plain http to other hosts): {Fable.FableService.Describe(url)}");
            File.WriteAllText(Asset, url);
            AssetDatabase.ImportAsset(Asset, ImportAssetOptions.ForceSynchronousImport);
            Debug.Log($"[FableBuild] service: {Fable.FableService.Describe(url)} built in");
        }

        public void OnPostprocessBuild(BuildReport report) => Remove();

        static void Remove()
        {
            if (File.Exists(Asset)) AssetDatabase.DeleteAsset(Asset);
        }
    }
}
