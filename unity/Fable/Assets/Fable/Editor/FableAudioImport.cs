// Import settings for Fable's sounds. Music (Resources/Audio/music.*) streams from disk: a five-minute track decoded
// into memory would cost ~50 MB on the Quest. Ambience loops are Vorbis, compressed in memory;
// one-shot effects stay as they were.
using UnityEditor;
using UnityEngine;

namespace Fable.Editor
{
    public class FableAudioImport : AssetPostprocessor
    {
        void OnPreprocessAudio()
        {
            if (!assetPath.Contains("/Fable/Resources/Audio/")) return;
            var name = System.IO.Path.GetFileName(assetPath);
            var imp = (AudioImporter)assetImporter;
            var s = imp.defaultSampleSettings;
            if (name.StartsWith("music."))
            {
                s.loadType = AudioClipLoadType.Streaming; s.compressionFormat = AudioCompressionFormat.Vorbis; s.quality = 0.6f;
                imp.loadInBackground = true;
            }
            else if (name.StartsWith("amb."))
            {
                // the sound library (audio/SOURCES.md): kept compressed in memory, since SceneRegistry loads every clip
                // in Resources/Audio and a minute of decoded stereo is ~10 MB. Beds stay stereo; point sources are mono.
                s.loadType = AudioClipLoadType.CompressedInMemory; s.compressionFormat = AudioCompressionFormat.Vorbis; s.quality = 0.5f;
                imp.forceToMono = name.StartsWith("amb.fire") || name.StartsWith("amb.candle") || name.StartsWith("amb.clock");
                imp.defaultSampleSettings = s;
                return;
            }
            else return;
            imp.forceToMono = true;
            imp.defaultSampleSettings = s;
        }
    }
}
