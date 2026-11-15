// What the map Peek needs at run time, in one asset the build keeps (Resources/MapAssets.asset, wired by
// FableBuild.MakeMapAssets): the glTF props (scroll, pin, globe stand; docs/MAP_PROPS.md), the scroll's edge mask and
// the map shader (referenced here so the player build includes it).
using UnityEngine;

namespace Fable
{
    public class MapAssets : ScriptableObject
    {
        public GameObject Props;
        public Texture2D EdgeMask;
        public Shader MapShader;

        static MapAssets loaded;
        public static MapAssets Get() => loaded ? loaded : loaded = Resources.Load<MapAssets>("MapAssets");
    }
}
