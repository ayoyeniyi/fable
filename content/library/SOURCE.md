# Peek library — sources

Everything here was made for Fable; nothing is third-party.

- `peek-library.json`: the index the reader's matcher searches (aliases, the sentence before which an entry is never offered, labels).
- `prefab` entries are props of the Alice rooms, modelled in Blender by `blender/build_hall_of_doors.py` (and the tea-party and croquet scripts) for this project.
- `clay/*.json`: mock models in the clay format (`schema/mock-model.schema.json`), written by Claude in a Claude Code session on 2026-10-31 as offline fixtures. They are marked `"source": "fixture"`, not `"clay"`, because they did not come from `fable-interpreter mock`. Check them with `fable-interpreter mock --check content/library/clay/*.json`.

Labels that quote the books are word-for-word from the editions recorded in `content/books/<slug>/SOURCE.md`, and the check above confirms each quote appears at or before the entry's sentence.
