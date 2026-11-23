# Faces and hair for the MakeHuman bodies

The faces are made for the ten MakeHuman bodies (see MAKEHUMAN_BODIES.md). Hair, brows, lips, lash lines and
stubble are real meshes built on each head's own scalp and face. Eye colour and twelve face shape sliders are in
Character Studio.

**Status: built and checked in Blender. Not yet tested in Studio.** No Luau syntax check has been run on the Lua.
Renders are in the project files under `character-studio/heads/`.

## What's there

- **Hair that grows out of the head, not a helmet.** Each style is a shell that follows the scalp. It thins to
  nothing at a raised, natural hairline, so its edge is a soft line and not a step. A see-through band
  (`Hair_<Style>_Fade`) sits along the hairline, so the hair fades into the skin. Fine strands are combed in the
  direction the hair grows (from the crown, or from the part).
  - Men: Buzz, Crop, TaperFade, HighFade, SidePart, CurlyTop, Locs, Twists
  - Women: Pixie, Locs, LowBun, Ponytail, LongStraight, Bob
  - Long hair drapes over the back and falls behind the shoulders of the rest-pose body, so it never goes through
    them. Locs collide with the head and body.
  - Every style has a `_Cap` version pressed flat under a hat, which is worn automatically when a hat is on.
- **Brows:** Natural, Thick, Arched, Straight, Thin. They're in a new required Brows slot, coloured from the hair palette.
- **Eyes:** a new required Eyes slot with 18 eye colours (browns, hazel, amber, greens, greys, blues).
- **Lips and lash line:** on every face. The lips are tinted from the skin colour.
- **Stubble:** Five O'Clock Shadow and Heavy Stubble use a real stubble layer on the male bodies. It follows the
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
- `NCHead.lua` (ReplicatedStorage) puts the pieces on: each one is placed from the eyes' attachments and scaled
  by the distance between the eyes, so the same pieces fit all five builds. The sliders set `Bone.Position` (it
  replicates), and the brows, lips, lash line, stubble and eyeballs follow their bones.
- `NCLookBuilder` calls NCHead for the `meshhair` and `meshface` families and for the Eyes slot. The slider list is
  `NCLookCatalog.FACE_SLIDERS`, and the server cleans what clients send with `NCLookCatalog.CleanFaceShape`.

## Install in Studio

After the bodies (MAKEHUMAN_BODIES.md):
1. Drag the new `NeonCoastCharacterStudio.rbxmx` into ServerScriptService, replacing the old one. It now includes
   `NCHead` and `NCHeadData`.
2. Import `NC_Head_Male.fbx` and `NC_Head_Female.fbx` with the 3D Importer. Keep the default scale and the names.
3. Select both imported models. Paste `AssembleHeads.lua` into the command bar and press Enter. The pieces go to
   `ReplicatedStorage.NC_HeadAssets.Male` and `.Female`.
4. Re-import the ten `NC_Body_*.fbx` files and run `AssembleMakeHumanBodies.lua` again, because they now have the face bones.
5. Press Play. Open Character Studio, go to Body, then Face shape, and move a slider. Try a few hairstyles with and
   without a hat.

If a piece sits a little off, set `NCHead.FADE_T`, `LIP_TINT` or `STUBBLE_T`, or change a slider's numbers in
`NCLookCatalog.FACE_SLIDERS`.
