// Fixed foveated rendering on Quest, set for every scene (the lobby included): the periphery is shaded at lower
// density while the centre of view, where the page floats, stays full. Dynamic: the runtime raises it toward the
// maximum only while the GPU is busy, so a light room keeps full density everywhere.
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Fable
{
    public static class QuestFoveation
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Init()
        {
#if UNITY_ANDROID && !UNITY_EDITOR
            Apply();
            SceneManager.sceneLoaded += (_, _) => Apply();
#endif
        }

        public static void Apply()
        {
#if UNITY_ANDROID && !UNITY_EDITOR
            OVRManager.foveatedRenderingLevel = OVRManager.FoveatedRenderingLevel.High;
            OVRManager.useDynamicFoveatedRendering = true;
#endif
        }
    }
}
