# Faces and hair for the MakeHuman bodies

The faces are made for the ten MakeHuman bodies (see MAKEHUMAN_BODIES.md). Hair, brows, lips, lash lines and
stubble are real meshes built on each head's own scalp and face. Eye colour and twelve face shape sliders are in
Character Studio.

**Status: built and checked close up in Blender (every style, hat version, brow and stubble, front, 3/4, side and back). The hairline rework is not yet tested in Studio.** No Luau syntax check has been run on the Lua.
Renders are in the project files under `character-studio/heads/`.

## What's there

- **Hair that grows out of the head, not a helmet or a wig.** Each style is a shell that follows the scalp and
  sits right on the skin. Its edge is not a line: a greyscale texture turns the last few centimetres into single
  hairs that start at different points and thin out onto the skin, so the hairline is ragged and soft the way a
  real one is. Skin fades thin out the same way down the sides. There is no raised rim and no see-through band.
  In Studio each hair piece has a SurfaceAppearance (AlphaMode Transparency) whose Color is set to the chosen hair
  colour, and the part sits at Transparency 0.02 so the soft alpha shows.
  - The hairline follows the reference turnaround (`references/faces/faces_turnaround.jpg`), not MakeHuman's
    scalp group, which recedes far at the temples. Men: nearly straight across, square temple corners, then
    straight down to a sideburn in front of the ear, ending around mid-ear. Women: a rounder, lower arch that
    curves down over the temple to just in front of the ear top, with the temples covered. The soft edge is kept
    short on the temples and sideburns so those narrow strips stay solid, and wider behind the ears and at the nape
    so dark hair blends into the skin there.
  - Men: Buzz, Crop, TaperFade, HighFade, SidePart, CurlyTop, Locs, Twists, FlatTwists
  - Three styles copy the person's hair references (project files `hair_ref_1..3`): TaperFade is a textured crop
    with a mid skin fade (top brushed up with a small front lift, the length grows gradually from the fade to the
    top); FlatTwists are 12 fat two-strand twists packed side by side (thin parts between them), spaced evenly over the
    scalp, four down each side; they run front to back, draw together slightly at the back, and end on a hard part
    that follows their lower edge, with the skin fade starting right under it. The front is a razor-straight edge-up
    with square corners above the outer brow ends, then a short band of hair before the twists' ends; Twists hang from a centre part (the forehead shows in a V), ending at the brows,
    the ear tops and the fade line, with a squared edge-up and a high skin fade. The women's LowBun is slicked
    straight back with no part, ears showing, into a wrapped bun about 8 cm across just below ear level.
  - Skin fades (TaperFade, HighFade, CurlyTop, Twists, FlatTwists) use their own texture, NC_HairFade (material
    NC_HairFaded): clipper-short hair is fine dark stubble whose density falls off down the head, solid under the
    longer hair and thinning to bare skin about mid-ear, like the reference photos. It stays the hair colour; from a
    step back it reads as a shadow going to skin, never as strands.
  - Women: Pixie, Locs, LowBun, Ponytail, LongStraight, Bob
  - Long hair drapes over the back and falls behind the shoulders of the rest-pose body, so it never goes through
    them. Locs collide with the head and body, grow out of the scalp (no cut ends at the roots) and never start
    on or right above an ear. The ponytail leaves the tie in a short arc, hangs straight down the back and tapers
    to a point.
  - Every style has a `_Cap` version pressed flat under a hat, which is worn automatically when a hat is on.
- **Brows:** Natural, Thick, Arched, Straight, Thin. Each is a flat card on the brow ridge with a texture of short hairs that slant toward the tail and fade out at the top, bottom and inner end. The tail stops just past the outer corner of the eye. They're in a new required Brows slot, coloured from the hair palette.
- **Eyes:** a new required Eyes slot with 18 eye colours (browns, hazel, amber, greens, greys, blues).
- **Lips and lash line:** on every face. The lips are tinted from the skin colour.
- **Stubble:** Five O'Clock Shadow and Heavy Stubble use a real stubble layer on the male bodies. It's a speckled texture that thins out at its edges, and it follows the
  beard line (under the nose, above the mouth corners, up to the sideburns). Female bodies get none.
- **Face shape:** 12 sliders on the Body tab under "🙂 Face shape": eye spacing, eye height, brow height, nose
  length, nose width, nose bridge, cheekbones, mouth width, lip fullness, jaw width, chin length and ears. They're
  free, and they're saved with the look. Presets never change your skin, eyes, brows or face shape.

The catalog hair items that have a mesh version on a body wear it there (for example, Low Taper Textured Top wears
TaperFade on the male body and Pixie on the female body; Long Straight wears LongStraight on the female body). Any
item with no mesh style for that body, and stock avatars, keep the older procedural hair.

## How it works

- `build_heads.py` (Blender, about 25 s) makes every piece from `NeonCoast_MakeHuman.blend` and the rest-pose
  bodies in `NeonCoast_MakeHumanRig.blend`. It writes `NC_Head_Male.fbx`, `NC_Head_Female.fbx`, `NCHeadData.lua`
  (where each piece sits, measured from the point between the eyes), `AssembleHeads.lua`, `heads.json` (the face
  bone positions) and `NeonCoast_Heads.blend`. Every piece is under Roblox's 20,000 triangles.
- `build_makehuman_rig.py` reads `heads.json` and gives every body **19 face bones** (`NC_Face*`, children of
  `Head`). They take a smooth share of the Head's weight only, so no other bone, part or attachment changes, and
  the animations play as before.
- `NCHead.lua` (ReplicatedStorage) puts the pieces on: each one is placed from the face's two eye bones
  (`NC_FaceEyeL/R`, the exact points the pieces were built around; older bodies fall back to the eye attachments)
  and scaled by the distance between the eyes, so the same pieces fit all five builds. The sliders set `Bone.Position` (it
  replicates), and the brows, lips, lash line, stubble and eyeballs follow their bones.
- `NCLookBuilder` calls NCHead for the `meshhair` and `meshface` families and for the Eyes slot. The slider list is
  `NCLookCatalog.FACE_SLIDERS`, and the server cleans what clients send with `NCLookCatalog.CleanFaceShape`.
- `NCHead.lua` holds each piece on the Head with a classic `Weld` (C0 = the piece's offset from the point between the eyes), so a piece can't be left behind if the character is moved or teleported while it is being put on.

## Install in Studio

After the bodies (MAKEHUMAN_BODIES.md):
1. Drag the new `NeonCoastCharacterStudio.rbxmx` into ServerScriptService, replacing the old one. It now includes
   `NCHead` and `NCHeadData`.
2. Import `NC_Head_Male.fbx` and `NC_Head_Female.fbx` with the 3D Importer. Keep the default scale and the names.
   The FBX files carry four greyscale textures (hair edge, brows, two stubble maps). If the hair, brows or
   stubble come in without them, upload the PNGs in `textures_heads/` and set each piece's
   SurfaceAppearance.ColorMap (NC_HairEdge for every Hair_ piece, NC_Brow for Brows_, NC_Stubble /
   NC_StubbleHeavy for the stubble).
3. Select both imported models. Paste `AssembleHeads.lua` into the command bar and press Enter. The pieces go to
   `ReplicatedStorage.NC_HeadAssets.Male` and `.Female`.
4. Re-import the ten `NC_Body_*.fbx` files and run `AssembleMakeHumanBodies.lua` again, because they now have the face bones.
5. Press Play. Open Character Studio, go to Body, then Face shape, and move a slider. Try a few hairstyles with and
   without a hat.

If a piece sits a little off, set `NCHead.LIP_TINT` or `NCHead.SOFT_T`, or change a slider's numbers in
`NCLookCatalog.FACE_SLIDERS`.
