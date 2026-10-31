// Fable SceneScript data model. Mirrors schema/scene-script.schema.json and interpreter/internal/script.
using System.Collections.Generic;
using Newtonsoft.Json;

namespace Fable
{
    [JsonObject(ItemRequired = Required.Default)]
    public class SceneScript
    {
        [JsonProperty("version")] public int Version;
        [JsonProperty("sceneId")] public string SceneId;
        [JsonProperty("title")] public string Title;
        [JsonProperty("environment")] public SceneEnvironment Environment;
        [JsonProperty("beats")] public List<Beat> Beats = new();
    }

    public class SceneEnvironment
    {
        [JsonProperty("prefab")] public string Prefab;
        [JsonProperty("ambience")] public string Ambience;
        [JsonProperty("exposure")] public float? Exposure;
        [JsonProperty("fog")] public float? Fog;
    }

    public class Beat
    {
        [JsonProperty("sentenceId")] public string SentenceId;
        [JsonProperty("focus")] public string Focus;
        [JsonProperty("actions")] public List<ScriptAction> Actions = new();
    }

    public class ScriptAction
    {
        [JsonProperty("type")] public string Type;
        [JsonProperty("asset")] public string Asset;
        [JsonProperty("anchor")] public string Anchor;
        [JsonProperty("offset")] public float[] Offset;
        [JsonProperty("yawDegrees")] public float? YawDegrees;
        [JsonProperty("scale")] public float? Scale;
        [JsonProperty("appear")] public string Appear;
        [JsonProperty("ease")] public string Ease;
        [JsonProperty("vanish")] public string Vanish;
        [JsonProperty("target")] public string Target;
        [JsonProperty("clip")] public string Clip;
        [JsonProperty("durationSeconds")] public float? DurationSeconds;
        [JsonProperty("loop")] public bool? Loop;
        [JsonProperty("light")] public string Light;
        [JsonProperty("intensity")] public float? Intensity;
        [JsonProperty("kelvin")] public int? Kelvin;
        [JsonProperty("sound")] public string Sound;
        [JsonProperty("volume")] public float? Volume;
    }

    public class SceneManifest
    {
        [JsonProperty("sceneId")] public string SceneId;
        [JsonProperty("environment")] public string Environment;
        [JsonProperty("ambiences")] public List<string> Ambiences = new();
        [JsonProperty("anchors")] public Dictionary<string, string> Anchors = new();
        [JsonProperty("assets")] public Dictionary<string, string> Assets = new();
        [JsonProperty("clips")] public Dictionary<string, List<string>> Clips = new();
        [JsonProperty("lights")] public List<string> Lights = new();
        [JsonProperty("sounds")] public List<string> Sounds = new();
    }

    public class Passage
    {
        public class Sentence { [JsonProperty("id")] public string Id; [JsonProperty("text")] public string Text; }
        public class Scene
        {
            [JsonProperty("id")] public string Id;
            [JsonProperty("title")] public string Title;
            [JsonProperty("chapter")] public string Chapter;
            [JsonProperty("paragraphs")] public List<List<Sentence>> Paragraphs = new();
            [JsonProperty("sentenceCount")] public int SentenceCount;
            public IEnumerable<Sentence> Sentences() { foreach (var p in Paragraphs) foreach (var s in p) yield return s; }
        }
        public class BookInfo { [JsonProperty("title")] public string Title; [JsonProperty("author")] public string Author; [JsonProperty("year")] public int Year; }
        [JsonProperty("book")] public BookInfo Book;
        [JsonProperty("scenes")] public List<Scene> Scenes = new();
    }
}
