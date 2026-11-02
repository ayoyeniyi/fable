# Environment brief (the standing rule for every Fable room)

Every reading environment, whether built by hand, by a `blender/build_*.py` script, by a subagent or by generation,
is made to this brief. Fill in the setting and the passage, give the whole brief to whoever builds the room, and
check the result against the acceptance criteria before calling it done. It came from the project owner on
2026-11-01 and replaces any looser guidance given to the earlier room scripts.

> Create production-quality natural reading environments for Fable: **[SETTING]**, inspired by **[BOOK AND PASSAGE]**.

## Visual target

A convincing real location seen through a VR headset: physically plausible scale, coherent lighting, believable
materials and carefully observed natural detail. Use the existing pipeline (`blender/build_*.py` → glTF →
`FableBuild`) and the budgets in `ARCHITECTURE.md`. The view from the normal reading position matters most, but
nearby surfaces and the space around the reader must still hold up when they turn or lean.

## Composition

- A clear foreground, middle distance and background.
- The reader sits or stands somewhere believable and comfortable for sustained reading.
- A few distinctive natural features are framed. The scene is not filled with uniform detail.
- The area behind the reading panel stays visually calm: restrained contrast and no distracting motion.

## Terrain and natural forms

- No smooth, generic terrain and no evenly scattered props.
- Rocks, soil, roots, vegetation and shorelines vary in ways that follow the place's underlying structure.
- Objects are grounded: partly buried, with accumulated debris, contact shadows and plausible transitions between surfaces.
- Plants vary in age, height, orientation, density and species to suit the habitat. No obvious repeated clusters.

## Materials

- Physically plausible surface properties and a consistent texture scale.
- Variation in roughness, colour, weathering and moisture.
- None of these: plastic-looking foliage, uniformly glossy rocks, oversized surface detail, visible texture repetition, or excessive sharpening.
- Materials are checked at the distances readers will actually see them from.

## Lighting and atmosphere

- One coherent time of day, one weather condition and one lighting direction.
- Believable indirect light, soft shadow transitions and grounded contact shadows.
- Detail is kept in both the bright and the dark areas.
- Haze, fog, bloom and colour grading are used sparingly, each for a clear environmental reason.
- The reading panel and its controls are part of the final composition, and the text stays comfortable to read.

## Motion and sound

- Subtle, local movement that the scene supports: a little foliage movement, restrained water motion, occasional distant activity.
- The viewpoint stays stable.
- Environmental sounds match credible sources, with no conspicuous loops and no constant attention-seeking effects.

## Optimisation

- Geometry and texture detail go where they affect the reader's view most.
- Use baked lighting, suitable levels of detail and efficient materials, plus anything else the pipeline already supports.
- No expensive effect is added just to make a desktop screenshot look impressive.
- The Quest 2 frame rate (72 Hz) must hold. Measured performance is documented.

## Acceptance criteria

The environment holds up at headset scale when the reader looks away from the page, turns around and inspects
nearby surfaces. Check for all of these:

- floating objects
- repetitive assets
- flat vegetation silhouettes
- texture seams
- implausible scale
- lighting leaks
- distracting aliasing

**Deliver:**

- headset-view captures from the reading position and from several angles around it
- performance measurements
- any remaining visual compromises

If headset verification is not available, say so plainly and list what still needs checking. Label every image as
a Blender render, a desktop preview or a headset capture, as the rest of the project does.

The aim is the credibility of a quietly observed real place, with enough restraint that someone would enjoy
reading there for twenty minutes.

## Rooms built before this brief

The step 7 rooms predate this brief. These known faults fall short of it and are the first things to fix when the
rooms are revisited:

- Kansas grass is spiky.
- The outside of Calypso's cave reads as a single boulder.
- Metal and linen in Glumdalclitch's room render black.
- No room has headset captures or frame-time measurements yet.
