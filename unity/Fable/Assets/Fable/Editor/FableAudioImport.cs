// Import settings for Fable's sounds. Music (Resources/Audio/music.*) streams from disk: a five-minute track decoded
// into memory would cost ~50 MB on the Quest. Ambience loops are Vorbis, decompressed on load (short, loop cleanly);
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
                s.loadType = AudioClipLoadType.DecompressOnLoad; s.compressionFormat = AudioCompressionFormat.Vorbis; s.quality = 0.7f;
            }
            else return;
            imp.forceToMono = true;
            imp.defaultSampleSettings = s;
        }
    }
}
