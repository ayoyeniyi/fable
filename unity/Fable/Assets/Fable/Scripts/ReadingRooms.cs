// Every book's reading rooms, for the lobby's book menu and the menu beside the page: three per book (Fable's own
// books: built scenes; the reader's books: the three generated rooms, docs/GENERATED_ROOMS.md), then the library.
using System.Collections.Generic;
using UnityEngine;

namespace Fable
{
    public static class ReadingRooms
    {
        /// Each bundled book's three rooms, its first room first (where it opens by default).
        public static readonly Dictionary<string, string[]> Bundled = new()
        {
            ["alice"] = new[] { "HallOfDoors", "MadTeaParty", "QueensCroquetGround" },
            ["oz"] = new[] { "KansasFarmhouse", "PoppyField", "EmeraldThroneRoom" },
            ["odyssey"] = new[] { "CalypsosCave", "OdysseusShip", "IthacaHall" },
            ["gulliver"] = new[] { "GlumdalclitchsRoom", "LilliputBeach", "Laputa" },
        };

        public static string Name(string scene) => scene switch
        {
            "HallOfDoors" => "The Hall of Doors", "MadTeaParty" => "The Mad Tea-Party", "QueensCroquetGround" => "The Queen’s croquet ground",
            "KansasFarmhouse" => "The Kansas farmhouse", "PoppyField" => "The poppy field", "EmeraldThroneRoom" => "The Throne Room of Oz",
            "CalypsosCave" => "Calypso’s cave", "OdysseusShip" => "Off the Sirens’ island", "IthacaHall" => "The hall at Ithaca",
            "GlumdalclitchsRoom" => "Glumdalclitch’s room", "LilliputBeach" => "The shore of Lilliput", "Laputa" => "The flying island",
            "LibraryRoom" => "The library", _ => scene,
        };

        public class Entry
        {
            public string Label, Note, Scene;
            /// A generated room's number (1-3); 0 for a built scene.
            public int Generated;
            public bool Ready;
        }

        public static List<Entry> For(string slug)
        {
            var list = new List<Entry>();
            if (Bundled.TryGetValue(slug, out var scenes))
            {
                foreach (var sc in scenes)
                    if (Application.CanStreamedLevelBeLoaded(sc)) list.Add(new Entry { Label = Name(sc), Scene = sc, Ready = true });
            }
            else if (Library.IsImported(slug))
            {
                foreach (var r in GeneratedRooms.Instance.Rooms(slug))
                    list.Add(new Entry { Label = r.Title ?? $"Room {r.N}", Generated = r.N, Ready = r.Ready, Note = r.Ready ? null : Describe(r) });
            }
            if (Application.CanStreamedLevelBeLoaded(LobbyController.ImportedScene)) list.Add(new Entry { Label = "The library", Scene = LobbyController.ImportedScene, Ready = true });
            return list;
        }

        public static string Describe(GeneratedRooms.Room r) => r.State switch
        {
            "none" => "not started yet",
            "failed" => "couldn’t be built" + (string.IsNullOrEmpty(r.Error) ? "" : ": " + Short(r.Error)),
            "unavailable" => r.Stage ?? "no room here",
            "done" => "built; coming to the headset",
            _ => r.Stage ?? r.State,
        };

        static string Short(string s) => s.Length > 70 ? s.Substring(0, 69) + "…" : s;
    }
}
