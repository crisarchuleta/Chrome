# The MakeHuman bodies: Neon Coast's one character model

Every player in Neon Coast is one of ten realistic MakeHuman bodies: Male or Female, in the five fitness builds
(Skinny, Average, Athletic, Muscular, Heavy). Character Studio (`NCLook*`) dresses them. That is the only outfit
system. The old Studio-only "Character Studio" scripts and the `LookCatalog` / `LookConfig` / `LookPresets` set from an
earlier session should be switched off in the place (see Install). Outfits fit cleanly because every item is sized
from each body's own attachment points.

**Status: built and checked in Blender. Not yet tested in Studio.** All ten bodies are rigged, and they render
cleanly in the rest pose and in a test pose with arms raised, elbows and knees bent, and a closed fist. The
renders are in the project files under `character-studio/rig/`. The Lua was written against the existing code, but
no Luau syntax check has been run on it here.

## The rig

`build_makehuman_rig.py` gives the bodies the **same 55-bone skeleton as `build_human.py`**, with the same names,
parents and axes:
- the 15 standard R15 joints, so Humanoid, tools, seats, ragdoll and every movement script keep working
- 40 extra bones: mid-spine, upper neck, both collarbones, forearm twist, three bones in every finger and thumb, and
  the toes

So `NCAnimationsHuman.lua` (all 18 moves) plays on these bodies unchanged, and so does the movement system. It reads
leg lengths from the joints, so the shorter female bodies keep their feet planted.

How each body is made:
1. The body with the locked `NC_Modesty` shape key baked in, plus its white tank top and dark boxer shorts, scaled to
   studs (3.77 studs to a metre). The men are about 6.8 studs tall and the women about 5.9.
2. Heat-weighted skinning on a temporary rig with bones along the limbs, taken from MakeHuman's own joint helpers.
   The garments copy the weights of the skin right under them, so they move exactly with it.
3. MakeHuman's A-pose is re-posed into the rest pose the animations were made for. The arms drop about 34 degrees
   to hang 7 degrees out from the body, the elbows straighten, the palms face the thighs, the fingers straighten,
   and the legs straighten under the hips.
4. **No nudity:** skin that the tank top and shorts fully cover is deleted, and the base layer is joined into the
   body mesh. It can't be taken off, and nothing can poke through it. `NCLookBuilder` still paints the torso, hips
   and thighs as clothes on top of that.
5. The body is split into the 15 R15 MeshParts by weight. The seams share weights, so they never open. Every cut is
   capped, and the eye openings are left open.

About 33,000 triangles per body. The biggest single part is the head at 8,600, which is under Roblox's 20,000 per
MeshPart limit.

## Files

| File | What it is |
|---|---|
| `build_makehuman_rig.py` | The Blender script (`blender --background --python build_makehuman_rig.py`, about 30 s for all ten) |
| `NC_Body_<Gender>_<Build>.fbx` | The ten bodies: 15 skinned `<Part>_Geo` meshes and the armature each |
| `NeonCoast_MakeHumanRig.blend` | All ten rigged, plus `<Body>_Whole`: the unsplit weighted mesh, for fitting new garments |
| `NCBodyData.lua` | ModuleScript, ReplicatedStorage. Per body: height, HipHeight, eye size, and every attachment point |
| `AssembleMakeHumanBodies.lua` | Paste in Studio's command bar once after importing, to finish the bodies |
| `NCBodyService.server.lua` | ServerScriptService. Swaps each player into the right body |
| `makehuman_rig.json` | Stats: triangles per part, re-pose angles, and any joint the heat solver missed (none) |

## How players get their body

- **Frame:** Male or Female, picked with the two buttons on Character Studio's **Body** tab. It's saved in the
  DataStore `NeonCoast_Body_v1`.
- **Build:** from fitness. FitnessService already sets the `BodyBuild` attribute (Skinny / Average / Athletic /
  Muscular / Heavy / Bulky, and Bulky uses the Muscular body). Train or eat badly, and your body changes.
- `NCBodyService` swaps the body in place whenever a character spawns (by any spawn path) or when the frame or build
  changes. You keep your spot, facing, health share, tools and character scripts. The swap waits while you're seated
  or ragdolled. The new body fires `CharacterAdded`, so Character Studio dresses it: base layer first, then the saved look.
- **Eyes:** the heads have real eye openings. `NCLookBuilder.ApplyEyes` puts a white eyeball, an iris and a pupil at
  `NC_LeftEyeAttachment` / `NC_RightEyeAttachment`, welded to the head. It runs with the base layer, so every body has
  eyes from the moment it spawns. `NCLookBuilder.EYE.iris` sets the default colour.

## Install in Studio

1. **Switch off the old outfit scripts** in the place: the Studio-only Character Studio script and anything named
   `LookCatalog`, `LookConfig` or `LookPresets`. Disable them, or move them to a folder named `_old`. Only the `NCLook*`
   system should dress characters.
2. Drag `NeonCoastCharacterStudio.rbxmx` into **ServerScriptService** (it now includes `NCBodyData` and `NCBodyService`).
3. Import each `NC_Body_*.fbx` with the **3D Importer**. Set Rig type to **R15**, keep the default scale, and don't
   rename the models.
4. Select all ten imported models. Paste `AssembleMakeHumanBodies.lua` into the command bar and press Enter. They
   go to `ServerStorage.NC_Bodies`, and `Male_Average` becomes `StarterPlayer.StarterCharacter`.
5. To play with the human animations, rename `NCAnimationsHuman` to `NCAnimations` in ReplicatedStorage (as for the
   old human body).
6. Press Play. Check the arm swing, the fingers in the jog, the seams at the shoulders and hips, and the eyes. If an
   item sits a little off on these heads, change `NCLookBuilder.FACE` once and every item follows.

Turn body swapping off with the `Enabled` attribute on `NCBodyService`.

## Rebuilding

The bodies come from `build_makehuman.py`, which needs the MPFB add-on and writes `NeonCoast_MakeHuman.blend`. Then
`build_makehuman_rig.py` needs no add-on. It runs in the cloud too: `pip install bpy==5.3.0`, then
`NC_OUT=<folder> python build_makehuman_rig.py`. Set `NC_BODIES=Male_Average` to rebuild just one body.
