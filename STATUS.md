# Neon Coast: Palmgrove buildings in Blender (status 2026-11-22)

Everything here is built by script in Blender 5.3 (`D:\SteamLibrary\steamapps\common\Blender`), in Roblox studs
(1 Blender unit = 1 stud), and checked with the renders in `previews\`. Every building is enterable: real two-layer
walls (outside finish + plaster inside) around true door and window openings, floors, ceilings, stairs where there
is a second floor. Rooms are empty on purpose (exteriors first).

## Buildings

| File | What | Size (studs) | Biggest mesh (tris) |
|---|---|---|---|
| Ranch.glb | one-story ranch, hip roof, porch, shutters, attached garage | 75 x 45 x 24 | ~1.5k |
| TwoStory.glb | two-story, arched lower windows, columned entry, stairs, garage | 71 x 47 x 38 | ~2.7k |
| Modern.glb | glass front, wood slats, flat roof + clerestory, canopy, garage | 60 x 42 x 21 | ~0.7k |
| SafeHouse.glb | the player's safe house: stone + lap siding, craftsman porch, balcony, dormers, garage wing, keypad | 93 x 57 x 40 | ~5.1k |
| Shop.glb | plaza shop module (used 5x): storefront, awning, sign band, loading door, rooftop units | 131 x 88 x 23 | ~0.6k |
| SchoolMain.glb + SchoolWing.glb | Palmgrove Elementary: brick + stucco main building with entry tower, canopy, stairs, flagpole, covered walkway, classroom wing | 284 x 124 x 43 (+ wing) | ~9.5k |

Added from real Florida references (stucco + tile, shallow wide-eaved hip roofs, screened lanais, raised
coastal cottages; street sizes from municipal standards; palm sizes from UF/IFAS):

| File | What | Biggest mesh (tris) |
|---|---|---|
| FloridaRanch.glb | stucco ranch, low hip tile roof with hip caps, Bahama shutters, columned entry, 2-car garage + coach lights, AC unit, meter, screened pool cage with pool and paver deck | ~2.2k |
| Mediterranean.glb | two-story, arched entry tower with its own roof, stucco quoins, juliet balcony, 2 single garage doors, arched back loggia | ~3.3k |
| KeyWest.glb | raised on piers with lattice, lap siding, standing-seam metal roof, porch with railings and steps | ~2.5k |
| StreetProps.glb | 16 props: mailbox, cobra-head street light, HOA post light, hydrant, sabal / royal / queen palms, shrub, hedge, vinyl fence panel, trash + recycling carts, stop sign, street-name sign, utility box, storm drain (offsets in props.json) | palms ~4.7k |

`build_street.py` lays these out as a test street (curbs, planting strip, sidewalks, driveways, walkways,
mailboxes, one street tree per lot, lights, fences) and renders previews/Street_*.png as the realism check.

Each building is one mesh per material (walls, inside walls, trim, roof, glass, floor, ...), and every door leaf and
garage door is its own set of meshes so it can open.

The safe house keeps the Studio layout: the window the intro camera flies through (Studio local (17, 7.9, -20)),
the garage door centred at local x = 44, the keypad by the garage corner. It needs a 180 degree turn after import.

## Studio side (ready, not yet tested in Studio)

- `BuildingKitData.lua`: per building, the exact collision boxes, door hinges, garage doors and markers, in
  Roblox-local studs (made by `make_kit_data.py` from the `*.json` files).
- `BuildingKit.lua`: `Prepare(importedModel, style)` applies materials/colours, builds the invisible colliders,
  turns doors into hinged models with prompts; `Place(template, cframe, scheme)` puts recoloured copies down.
- `BuildingDoors.server.lua`: swings doors away from whoever opens them (auto-close), rolls garage doors up.
- `NeonCoastBuildingKit.rbxmx`: all three of the above in one file to drop into Studio.

## Blocked

Uploading the GLBs to Roblox: `C:\Users\Crisa\Documents\NeonCoast_Blender` is still refused as an upload folder
(Studio > Assistant Settings > MCP Permissions > approved upload directories). Once it is accepted: upload the 7
GLBs as private Models on YTLechugaGaming1, insert, check orientation/scale, run BuildingKit.Prepare, and swap
them in for the 287 houses, the safe house, the 5 shops and the school.

## Rebuild

    blender --background --factory-startup --python build_pool.py
    blender --background --factory-startup --python build_houses.py
    blender --background --factory-startup --python build_safehouse.py
    blender --background --factory-startup --python build_civic.py
    blender --background --factory-startup --python build_props.py
    blender --background --factory-startup --python build_homeprops.py
    blender --background --factory-startup --python build_street.py
    blender --background --factory-startup --python build_city.py
    blender --background --factory-startup --python build_parachute.py
    blender --background --factory-startup --python build_anims.py      (NC_ANIM_RENDER=0 skips the preview video)
    python nc_walkable.py                                               (every floor reachable on foot)
    blender --background --factory-startup --python make_kit_data.py

## Realism pass 2 (details)

- Ranch, TwoStory and Modern now carry the same details as the Florida styles: hip caps on every hip roof,
  gutters with downspouts and splash blocks, coach lights by the garage (Modern: up/down sconces and scuppers),
  an AC condenser on its pad, the power meter + disconnect + conduit, house numbers, mulch beds with stone edging.
- StreetProps.glb grew to 25 props: + Florida wooden power pole (crossarm, insulators, transformer, wire attach
  points in props.json), basketball hoop, patio set with umbrella, pool lounger, grill, porch rocking chair,
  potted plant, path light, pool pump.
- The test street now has power lines down the back lot lines, a stop bar and ladder crosswalk, pots by the
  front doors, path lights on the walks, hoops on some driveways, loungers in the pool cage, rocking chairs on
  the cottage porch, patio sets and grills in the back yards.
## Houses that work (pass 3; written, not yet tested in Studio)

Everything below is in `NeonCoastBuildingKit.rbxmx` (BuildingKit + data, BuildingDoors, HouseInteractables,
HouseClient) and runs off CollectionService tags, so it works on Blender buildings and on Studio-built furniture.

- Doors swing away from you and close by themselves; garage doors roll up flat (BuildingDoors).
- Windows: every window's lower sash is now its own mesh and slides up behind the top pane (tag NC_Window).
- Lights: a ceiling light over every room (generated from the ceiling slabs), all on one wall switch by the front
  door (NC_Light, Group "House"); porch / coach / lantern lights turn on at dusk and off at dawn (NC_NightLight).
- HomeProps.glb (interactive furniture): ceiling fan (Off / Low / High, spins up and coasts down, light bowl),
  floor lamp, 65" TV on a media console, wardrobe closet (doors swing open), kitchen sink (water + sound, shuts off
  after a minute), garage car panel.
- Closet: "Change outfit" opens the Character Studio, "Gear" opens the Arms shop. Car panel: "Pick a car" opens
  the garage list.
- TV: Snake and Pong, played on the TV's own screen (the camera moves in front of it); everyone in the room sees
  the game live on that TV. (HTML pages can't run inside Roblox, so the games are Roblox ones.)

Needs Neon Coast open in Studio: import the package, test every piece, place the furniture in the safe house
interior layouts (InteriorKit) and tag its existing lamps.

## Half court with a working basketball (pass 4; written, not yet tested in Studio)

- StreetProps.glb now has 26 props: + `HalfCourt`, built to real high-school sizes at 1.15 studs per foot. It is a
  50 x 30 ft slab with the 12 ft key, the free-throw line and circle, and the 19 ft 9 in three-point arc with
  corner lines. It has a pole behind the baseline, a 72 x 42 in board 4 ft in, and an 18 in rim at 10 ft with a net.
  props.json holds the rim, board and ball-spawn points.
- The test street has a pocket park past the last north lot. It has the court, a walk in from the sidewalk, a
  fence behind the hoop, 4 post lights for night games, a picnic table and palms. The renders are
  previews/Street_court.png, Street_court_shooter.png and Street_park.png.
- `BuildingKit.PrepareHalfCourt(importedModel)` finds the court pieces and works however the court was turned.
  It sets materials, collision on the slab and pole, and a regulation bounce on the slab. It places the
  RimCenter, BallSpawn and BoardCenter points and tags the court NC_Hoop.
- `Basketball.server.lua`: real physics, simulated by the server so every player sees the same ball.
  - Gravity is real: 37 studs/s², set with a VectorForce on top of Roblox's 196.
  - The ball is 9.4 in. It bounces about 85% on the court, about 65% off the steel rim and about 80% off the glass.
  - The rim is a ring of 20 real steel tubes with its inner edge exactly at the 18 in rim, so shots roll around,
    rattle in, spin out and bank.
  - Scoring: a ball dropping through the rim from above scores 2, or 3 if the shot was taken beyond the arc. A
    ball pushed up through the net doesn't count. SWISH and BANK are detected.
  - Players get Buckets / Makes / Shots attributes.
  - Bounce, rim and board sounds play.
  - The ball goes back to the free-throw line if it rolls away.
  - Players can catch passes and rebounds by running into the ball.
- `BasketballClient.client.lua`:
  - Shooting: hold click (or Shoot on touch, R2 on a pad) and release at the top of the meter.
    - The arc is real ballistics into the nearest rim you face. The ball comes in at 47°, which leaves about
      ±2.5 in of room along the shot, and leaves with backspin.
    - Releasing early lands short and releasing late lands long. 1% of speed is about 0.5 studs at 17 ft, so the
      green window swishes and "Good" rattles in. Shooting on the move sprays the ball.
  - G passes: a lob to a player you're looking at, or a chest pass.
  - What everyone sees: the dribble, with bounce speed following the runner; the set-point pose; the
    follow-through; the net snap, swish and "+2 / +3" over the rim.
  - The HUD shows points and FG.
- Both scripts are in NeonCoastBuildingKit.rbxmx. Install: Basketball goes in ServerScriptService and
  BasketballClient in StarterPlayerScripts.
- The sounds are built-in placeholders (rbxasset). Swap in store sounds for the bounce, rim clank and swish
  when Studio is open.

## Backyard pools, swimming, springboard, unicorn floaty (pass 5; written, not yet tested in Studio)

- `Pool.glb` (build_pool.py, pool.json):
  - BackyardPool: a 16 x 36 ft residential diving pool. It has a 3'6" shallow end with three entry steps (tile
    nosing) and a handrail, then a slope down to an 8'6" diving well with a spoon back up to the deep wall. Also
    waterline tile, bullnose coping, a paver deck with a soldier border, a stainless ladder, two underwater lights,
    a skimmer, returns, main drains and 7-segment depth markers (3'6", 5', 8'6").
  - The springboard is an 8 ft board on a jump stand, tip 3.5 ft out over the water and about 2 ft above it.
    The board is its own pieces so it can flex.
  - UnicornFloaty: a giant ride-on ring about 6.5 ft across with a 3 ft hole, white vinyl, arched neck and head
    (eyes with lashes, pink cheeks, ears), a gold twisted horn, and a rainbow mane and tail. Smooth shaded.
- `BuildingKit`:
  - `PreparePool(model, parent, cutGround)` sets materials and colliders (the sloped floor as rotated slabs). It
    adds the swimmable water volume (tag NC_Water), the springboard model (tag NC_DivingBoard), and aqua underwater
    spotlights that come on at dusk.
  - `PrepareFloaty(model)` makes one unanchored model on a Body part (tag NC_Floaty).
  - `CutGround(cf, size)` / `CutPools(model)` dig the pit out of terrain, or out of a big ground part with
    SubtractAsync.
  - `Prepare` now also gives the Florida ranch's caged pool its water volume.
- `PoolClient.client.lua` (swimming on your own machine, motions for everyone):
  - Swim physics: get in deeper than your chest, or jump or dive in, and you swim where the camera looks. Space
    rises, C sinks.
    - Momentum carries and quadratic water drag bleeds it off, so a dive carries you a few studs deep and you float
      back up.
    - You float head-out when you stop.
    - Speed is about 9 studs/s at the surface, slower underwater.
  - Space at the wall pulls you out onto the deck. You can climb onto the floaty too.
  - Chest-deep water slows walking. Stop in the shallow end and you stand up.
  - Swim motions seen by everyone:
    - Freestyle: windmill arms with a high-elbow recovery, body roll, a six-beat flutter kick and a breath to the
      side.
    - Treading water: sculling arms and an eggbeater kick.
    - Dive streamline, cannonball tuck (C in the air) and a pull-up at the wall.
  - Springboard: every client sees the board flex under everyone (a damped spring at about 2 Hz).
    - Jump right as you land on the end to ride the recoil, up to 4 bounces higher.
    - Off the end you dive head-first along the arc. The flight uses real gravity (37 studs/s²), so you get a
      real diver's ~1.3 s in the air.
  - Splashes: a column, a crown and ripples sized by speed. A clean dive throws far less water than a cannonball.
    Stroke splashes and sounds too.
  - Underwater: blue tint, blur and an underwater reverb.
- `PoolService.server.lua`:
  - Floaty physics:
    - About 3 mass, floating a third under on small waves and drifting slowly.
    - Pushed by swimmers and kept off the walls.
    - Stand on it and it sinks most of the way. Land on the edge and it tips, then rights itself.
  - Drop through the hole for a "Unicorn hoop!": sparkles, a boing and the UnicornHoops attribute.
  - Relays the swim and dive poses so everyone sees them.
- Both scripts are in NeonCoastBuildingKit.rbxmx. PoolService goes in ServerScriptService, PoolClient in
  StarterPlayerScripts.

## Estate pools, real backyard fences, the first downtown (pass 6)

**The pool is now mansion size.** BackyardPool (build_pool.py) was rebuilt:
- 24 x 60 ft (27.6 x 69 studs), on a 92 x 48 stud paver deck with a soldier border.
- A sun shelf (baja ledge) under 1 ft of water in the shallow corner, with a bench step and steps down. The street
  puts two in-water loungers on it.
- A raised spillover spa (8 x 8 ft, 3 ft deep) set into the house-side wall. It has a bench, jets and a light,
  and a sheet of water spills from it into the pool. It is its own swimmable water volume.
- The 3'6" shallow end slopes to a 9 ft diving well. There is a springboard at the deep end and a ladder on each
  long wall.
- A rock waterfall on the far deck: stacked boulders, a lip stone and a falling sheet. The game adds mist and a
  loop sound.
- Four underwater lights, two skimmers, returns, main drains and depth markers.
- In the game, the spa bubbles, and PoolClient takes the highest water surface where volumes overlap.

**Lots and backyards:**
- Lots are about 125 ft deep (rear lot line at 172).
- Each estate pool sits behind the patio, with five loungers on the far deck, a grill on the deep-end corner and
  palms in the back corners. The unicorn floaty is in two of the pools.

**Fences like real backyards:**
- Each house has a return fence from each side wall to the lot line, in the rear third of the house. It is
  placed clear of AC units, chimneys, side doors, side windows and lattice piers, and goes to the back corner when
  the sides are busy.
- A walk gate on the driveway side right by the house (new FenceGate prop): the leaf is its own piece with strap
  hinges, a brace and a latch, and it closes on the next panel's post.
- Lot-line fences run from where the returns meet them to the rear fence, split so every junction has a post.
- The rear fence has posts on the lot corners.
- Panels are stretched to fit each run exactly.

**New checks in nc_qa:**
- A backyard enclosure check: a flood fill at walking height from every backyard, closing gaps narrower than a
  person, to see if it can reach the street.
- All 12 backyards are closed. A self-test point in a front yard correctly shows as open (`NC_QA_SELFTEST=1`).

**Downtown** (build_city.py -> DecoHotel / MidRiseBrick / MidRiseStucco / OfficeTower .glb, city.json):
- **DecoHotel**: a 4-story Ocean Drive Art Deco hotel in mint stucco.
  - A central pylon with a vertical neon CORAL sign and a stepped crown and spire.
  - Eyebrow sunshades on every window band, with pink neon under the front ones.
  - Coral corner fins, speed lines on the parapet.
  - A terrazzo front terrace up three steps, behind low walls.
  - A deep entrance canopy with HOTEL in neon, and lobby storefronts with a reception desk.
  - A side fire escape: steep stairs on the outer strip, openings in the landings, a drop ladder and doors onto
    each landing.
  - A stair penthouse and rooftop units.
- **MidRise** (brick or stucco): five stories of mixed use.
  - Three storefront bays with display glass, recessed doors, transoms and striped awnings.
  - A dark sign band with neon shop names (CAFE / TACOS / VINYL, PIZZA / BOOKS / SALON).
  - Apartments above with balconies on the middle bay, a stepped cornice, rooftop units and a bulkhead.
  - A party wall on one side for row placement.
- **OfficeTower**: a 300-stud Brickell-style tower.
  - A stone podium with a double-height glass lobby, glass doors and a canopy.
  - A 15-story curtain wall with mullions and dark spandrels; floor plates and the core show through.
  - A louvered crown with a blue LED edge, and a mast with a red aircraft light.
- **Every building:** neon tubes on standoff clips, and window frames wrap the glass. All pass the building
  checks (qa_buildings.py).
- **Test block** (build_cityblock.py, `previews/CityBlock_*.png`, including two night shots in EEVEE where the
  neon glows):
  - A divided avenue with royal palms down the median, crossing a 2-lane street with parking.
  - Sidewalks with queen palms in open tree grates.
  - Street lights, mast-arm signals, ladder crosswalks, stop bars and lane paint.
  - The block passes every check.
- **Fixed by the checks along the way:**
  - Royal palms on the sidewalks had crowns through facades and balconies; they moved to the median, with queen
    palms at the curb.
  - Solid tree grates ran through the trunks; they are now open frames.
  - A palm stood through the tower canopy.
  - Neon letters hovered off their boards.
  - Storefront glass floated inside its frames.
  - Canopy hangers crossed the HOTEL letters.
  - A side eyebrow ran into the fire escape.
  - Fire escape stairs blocked the doors.
- **Studio:** city.json is in BuildingKitData, so Kit.Prepare handles these buildings too. New materials include
  Neon for the Neon* pieces; balcony, shop and fire escape doors swing like the house doors.

## Movement animations made in Blender (pass 9; written, not yet tested in Studio)

`build_anims.py` builds a rig in Blender with the same 15 joints and axes as the Roblox R15 body. Every bone sits
on its Roblox joint and points straight up with zero roll, so a bone's rotation is exactly the Motor6D.Transform
Roblox uses.

**Gaits** are generated from real gait mechanics, then keyed onto the rig in Blender (Bezier curves, seamless
loops):
- The planted foot rolls heel, flat, toe while the body passes over it, and leg IK keeps it on the ground.
- The swing foot loops forward. The pelvis bobs (high mid-stride when walking, low when running), sways, turns and
  drops on the swing side.
- The chest turns against the pelvis, arms swing against the legs, and the head stays level.

| Gait | Speed (studs/s) | Cycle | Stride per cycle |
|---|---|---|---|
| Walk | 5 | 0.64 s | 3.2 studs |
| Jog | 16 | 0.50 s, with a flight phase | 8 |
| Sprint | 25 | 0.42 s, forefoot strike, high knees, arms pumping, 13° lean | 10.5 |

**18 clips:**
- Loops: Idle (breathing, shifting weight, glancing around), TiredIdle (hands on knees, breathing hard), Walk,
  Jog, Sprint, Fall.
- Moves: JumpUp, Land, LandHard, Stumble, Roll, Vault, Mantle, Climb, GetUp, Bump, Skid (stopping from a sprint),
  Pivot (planting to turn round).

**In the game** (`NCAnimPlayer` and `NCAnimations` ModuleScripts in ReplicatedStorage):
- MovementClient plays them on every player's body, with nothing uploaded.
- Idle, walk, jog and sprint blend by speed on one shared step cycle that advances at speed ÷ stride, so feet
  don't skate at any speed.
- In the air it plays the jump, then crossfades into falling. Out of breath, the idle bends over.
- Moves play their Blender clip with blend-in and blend-out. Lean, head turn and foot planting still layer on top.
- Holding a tool leaves the right arm to the tool pose; the basketball keeps both arms.
- Without the modules, the default Roblox animations play as before.

**Other files:**
- `NeonCoast_Animations.blend`: open it to tweak any clip, then re-run `build_anims.py`.
- `NeonCoastAnimations.rbxmx`: the same clips as KeyframeSequences, only needed if you ever want to publish them
  as Roblox animation assets.
- Previews: `previews/Movement_Animations.mp4` and `previews/Anim_*.png` contact sheets.

**Fixes from an independent code review of pass 8:**
- Jumping can no longer stay switched off while you're in a seat or on a ladder.
- Sprinting off a roof with a parachute no longer leaves the view permanently wider. The movement script publishes
  its offset as camera attribute `NC_FovOffset`, and the parachute saves the FOV without it.
- Fences and rails thinner than 0.35 studs can now be vaulted.
- Clearance checks use real shapes, not bounding boxes.
- Climbing no longer sinks the legs into the ground on lower walls.
- Standing at an edge no longer folds a leg into the gap.
- Moves no longer snap to the rest pose for one frame at the end.
- Boats and cars no longer knock over swimmers or skydivers.
- The ragdoll rig rebuilds if an outfit swaps body parts.
- The newest look direction always wins.
- Turning from a standstill is instant.

**Also changed:** walk speed is now 5 (about 1.3 m/s at this world's scale); it was 8.

**Install:** NCAnimPlayer and NCAnimations go in ReplicatedStorage, next to the pass 8 scripts.

**Check in Studio:** the clips were made on Roblox's standard blocky R15 proportions (hips 2 studs up). On very
different body shapes the feet may sit slightly off the ground while moving.

## Real-life movement and physics (pass 8; written, not yet tested in Studio)

Built from how people really move: momentum, weight and balance. No names or assets from any other game.
`MovementClient.client.lua` drives your body; `MovementService.server.lua` handles the ragdoll rig, fall damage
and relaying to other players. It sits on top of the normal Humanoid, so vehicles, ladders, swimming, the
parachute and the elevator keep working.

**Momentum** (checked by simulation):
- 0 to jog in 0.55 s, jog to sprint in 0.8 s.
- Stopping from a jog takes 0.3 s; a sprint skids about 7 studs (2 m).
- Corners get wider with speed: about 3.4 studs at a jog, 8 at a sprint.
- Asking to go the opposite way at speed makes you plant and brake before you turn.
- Walls take your momentum. Sprinting flat into one knocks you back.
- Uphill is up to 40% slower; downhill is a little faster. Moving floors (the elevator) are handled.

**Gaits:**
- Walk (5 studs/s): hold Left Alt, or tilt the stick a little.
- Jog: the default.
- Sprint: hold Left Shift. L3 or the on-screen Sprint button toggles it.
- Shift lock moves to Right Shift.
- Sprinting burns stamina over about 12 s, and you slow as you tire. When it's empty, you jog until it refills.
  A small stamina bar shows only while it isn't full.

**Jumps** are human-sized: 4.2 studs instead of Roblox's 7.2. They carry your momentum, you can only steer a
little in the air, and there's no bunny hopping.

**Landings:**

| Fall height | What happens | Damage |
|---|---|---|
| up to ~6 studs (1.7 m) | soft dip | none |
| ~10 studs (2.9 m) | hard landing: crouch, half your speed | none |
| ~14–20 studs (4–5.7 m) | a roll if you're moving, a crouch if not | up to ~20 |
| 25+ studs (7 m+) | ragdoll | 40+ |
| 37+ studs (10.6 m+) | fatal | — |

Water landings never hurt. Turn damage off with `FALL_DAMAGE` in MovementService.

**Vault and climb** (press jump facing it):
- Fences and rails up to 4.6 studs: a one-hand speed vault, keeping your momentum.
- Low walls, counters and car roofs: mantle up onto them.
- Walls and fences up to 9.2 studs: jump, hang from the edge, pull up. On a thin one you go over and drop
  down the far side (gravity does the drop).
- It checks headroom and space beyond before you go. Stairs and ramps are left alone (that's just a jump).
- You can vault the skyscraper's roof rail, so bring a parachute.

**Ragdoll and getting up:**
- Bad falls, being hit by a car, and death all ragdoll.
- Joints have human limits: knees and elbows only bend the right way.
- Once the body settles, you get up facing where your head was.

**Body language, seen by everyone:**
- Leaning forward to accelerate, back to brake, and into corners by real balance physics (about 12° in a sprint
  turn), with a forward torso lean at a sprint.
- Heads and shoulders turn toward where each player is looking.
- Out-of-breath players' chests heave.
- Feet plant on stairs and slopes: the lower foot reaches down, the hips drop and the upper knee bends.
- Vault, climb, roll, hard-landing, wall-bump and get-up poses play on every screen.

**Changes in other scripts:**
- Pool wading and the TV seat now slow or freeze you through Humanoid attributes `SpeedFactor_Wade` /
  `SpeedFactor_TV`. Any script can use `SpeedFactor_<name>`; 0 freezes you and blocks jumps.
- The TV now restores your speed and jump to what they were, instead of a hardcoded 16/50.
- A plain WalkSpeed change from any script still works: it scales the whole system, with 16 as normal.

**Install** (in NeonCoastBuildingKit.rbxmx): MovementService goes in ServerScriptService, MovementClient in
StarterPlayerScripts.

**Check in Studio:**
- The feel numbers at the top of MovementClient (WALK/JOG/SPRINT, ACCEL, A_LAT, JUMP_HEIGHT).
- Ragdoll joint limits: knees must bend the right way.
- Foot planting on stairs.
- Whether the game already has its own sprint script, fall damage or a server speed check. Sprint is 25 studs/s,
  so any speed limit has to allow at least 26.

## Skyscraper stairs, the paid elevator, parachutes (pass 7; written, not yet tested in Studio)

**Every building is still enterable, now checked by a walk test.** `nc_walkable.py` (plain Python, writes
`walkable.json`):
- It walks a 2 x 2 stud body from the ground around each building. Steps up to 1.3 studs; doors and garage doors
  count as open.
- Every floor of every building must be reachable. For downtown, the main roof must be reachable too.
- All 14 buildings: 0 unreachable floors.
- It found two real problems, both fixed: the TwoStory and SafeHouse stair guard rails boxed you in at the top
  of the stairs. The rails now stop short, with a newel post.
- Railing end posts now reach the floor (they used to start mid-air).

**Real stairs to every roof (free).** `stair_core()` in build_city.py builds a switchback stair:
- Two flights a floor with a landing between them (two switchbacks on tall floors), a divider wall and sloped
  handrails.
- Guard rails around every stair opening, and a door out at each floor.
- DecoHotel and both MidRises have a stair penthouse onto the roof.
- OfficeTower has a concrete core from the lobby to the crown:
  - The stairs go to all 18 floors and the roof deck: the lobby, two podium floors and 15 tower floors.
  - A stair door on every floor, and the elevator shaft beside the stairs.

**The elevator (costs earned money going up).** `Elevator.server.lua`, built from the tower's `elevator` note:
- A real car on a PrismaticConstraint, so you ride it by standing in it; physics carries you.
  - Lobby to roof in about 10 s.
  - A lip on the car floor meets the fixed sill at each stop, so there's no gap to fall through.
- Sliding shaft doors at both stops, a floor display in the car, a chime.
- Call panels are on the core wall by the doors:
  - "Ride to the roof" in the lobby costs $50 (set by `Price`).
  - "Ride down" from the roof is free.
  - Without the money, it tells you the stairs are free.
- Money goes through `NCWallet.lua`, which uses the game's own NC module (`leaderstats.Cash`, `NC.AddCash`,
  `NC.Notify`). It's the same cash jobs pay into, saved by the same DataStore.

**Parachutes (buy once, $500, saved).** Tuned to play like the big battle-royale skydives:
- **Where to buy:** the SKY kiosk in the tower lobby, or the gear locker in the roof's mechanical room. Both are
  `NC_ParachuteShop` prompts.
- **Saving:** ownership is saved in DataStore `NeonCoast_Gear_v1` and shown as the `HasParachute` attribute. You
  wear the pack on your back.
- **Freefall:** step off anything with 40+ studs under you and you're skydiving.
  - The camera steers.
  - W looking level tracks forward fast. W looking down dives head-first at up to about 120 km/h, with the
    wind louder and the view wider.
  - Let go and you fall belly-down. S slows you; A/D slide sideways.
- **Canopy:**
  - SPACE opens it: a hard opening jolt, and the canopy cracks open over you.
  - It turns toward where you look. W is faster and steeper, S brakes and floats, A/D bank harder.
  - C cuts it away and drops you back into freefall, and you can open again.
  - It opens on its own near the ground. You land soft, or splash into a pool and swim.
- **On screen:** altitude and speed. Phones and controllers get Open and Cut buttons.
- **Everyone sees everyone:** the pack, the freefall and dive poses, the canopy with the jumper's hands on the
  toggles, and cutaways. State goes through `ParachuteState`, then a character attribute.
- **The canopy model** (build_parachute.py -> `Parachute.glb`): a 9-cell ram-air wing with real airfoil ribs and
  open intakes, stabilisers, 40 lines, risers, a slider, toggles, and the pack. `Kit.PrepareParachute(import)`
  puts it in `ReplicatedStorage.ParachuteAssets`. Until that's uploaded, the client builds a part-made canopy in
  the same colours.
- **The tower roof** has a BASE-jump platform: a grated deck cantilevered 9 studs out over the avenue, with a
  hazard-striped lip.

**Install** (all in NeonCoastBuildingKit.rbxmx):
- NCWallet, Elevator and ParachuteService go in ServerScriptService.
- ParachuteClient goes in StarterPlayerScripts.
- Kit.Prepare makes the `ElevatorRoot` and the kiosk prompts for the tower by itself.
- A tower template cloned after its car was built gets a fresh, working car.

**Needs a Studio test:**
- The canopy's opening scale (Model:ScaleTo on a canopy welded to the jumper).
- The ride feel in the elevator car.
- The freefall numbers, which are tuning values in `FF` / `CN` at the top of ParachuteClient.

## The street and every house checked for floating / clipping (pass 5)

`nc_qa.py` checks the real meshes, with the ground's pool holes applied:
- Run it with `NC_QA=only` (or `1`) before `build_street.py`.
- `qa_buildings.py` runs the same checks on the safe house, shop, school, pool and home props.

What it checks:
- Every placed prop is sampled at its centre and four corners: floating, sunk or straddling two surfaces.
- Every pair of placed things, using true triangle intersection: clipping.
- Inside every house: details crossing windows, doors or garage doors; windows or doors through a roof; gutters
  and downspouts through anything.
- Any piece of a house that touches nothing that reaches the ground.

Fixed (all checks now pass; the only flag left is the car panel, which hangs on a garage wall by design):
- **Lot layout**
  - Lots are now about 105 ft deep (rear lot line at 150).
  - Rear privacy fence along the back, and side fences now run to the back with one fence per lot line. The
    south lots had doubled fences.
  - Panels share posts; they used to overlap. Power poles moved into the rear easement.
  - The Florida ranch's pool cage used to cross the old pole line.
- **Pools**
  - The ground is dug out under the in-ground pools. The caged pool used to be hidden under the lawn.
- **Back yards**
  - Ranch, Two-Story and Modern back doors opened onto nothing. Each now has a two-riser stoop and a 9.5-stud
    concrete patio that the pool decks meet.
  - The Modern had no back door at all; it now has glass double doors.
  - The Key West back door was 3.6 studs up with no stairs. It now has a landing on piers, even-riser stairs and
    railings.
- **Key West**
  - Front steps have even risers.
  - The lattice reaches the ground and the floor, and a skirt board closes the band under the siding.
- **Lights and downspouts**
  - Every wall lantern and coach light hung 0.1 off its wall.
  - Downspouts floated 0.15 off the walls, never met the gutters, and on the Modern garage ran above the roof. They
    are now real 3 x 4 in downspouts with goosenecks from the gutter, strapped to the wall, with kick-outs and
    splash blocks.
  - The Ranch's front gutter ran through its porch roof; it now stops either side of it.
- **Safe house**
  - Downspouts went through the eaves.
  - Two upstairs windows on the garage side were half-covered by the garage roof. They are removed.
- **Mediterranean**
  - The tower window was stuck on the outside of a solid wall; it is now set into a real opening.
  - The front pots were inside the tower walls; they now flank the arch.
  - The patio umbrella went through the back door, and the grill was sunk in the loggia.
- **Planters, shrubs and palms**
  - Front pots were buried in porches or hanging half off them. They now stand on the porch or stoop.
  - Mulch beds ran into the foundation lip; they now start at its face, and shrubs are planted in the beds.
  - Key West shrubs and pots were under the porch, and its rocking chairs were sunk 0.1 into it.
  - Yard palms tangled with the street palms. Two street palms stood past the end of the ground.
- **Other props**
  - Deck chairs stood on the depth plaques.
  - A recycle bin went through the hydrant.
  - Shirts floated under the closet rod (now on hangers), and the sink handle didn't reach the faucet.

Renders:
- `previews/Walk_<Style>.png`: four corners of every house.
- `previews/Close_*.png`: the fixed details.
- `previews/Street_pools_drone.png`, `Street_pool_twostory.png`, `Street_pool_mediterranean.png`.
- `previews/Pool_*.png`.

## Lowrider with hydraulics + Low & Slow Kustoms (pass 10; written, not yet tested in Studio)

Full notes and install steps in `LOWRIDER.md`.
- `build_lowrider.py` -> `Lowrider.glb` (an original two-door hardtop lowrider, Classic Wire 100-Spoke wheel),
  `LowSlowShop.glb` (two-bay custom shop with a neon sign, paint turntable and hop pit), `NCLowriderData.lua`.
- Drivable with raycast suspension; air bags (smooth lifts, lay frame) or hydraulics (corner lifts, front hop,
  body hop, three-wheel, dance). Hop pit measures hops in inches; top five show on the board.
- Customize at the shop with live preview: candy paints and finishes, vinyl decals printed flush on the paint
  (flames, pinstripes, patterns + lace, sunset mural; images from make_lowrider_vinyls.py, LowriderVinyls.glb),
  wheel finishes, whitewalls, suspension kits, continental kit, trunk pump setup. Saved in `NeonCoast_Garage_v1`.
- Works right away with a part-made car and shop; `NCLowriderKit.Prepare(import)` switches to the Blender meshes.
- Full customization (pass 11): GTA-style tuning menu (categories -> mods -> options, camera on each part, hover
  preview, cart total, custom colour picker). Swappable bumpers, grilles, hoods, ornaments, spoilers, skirts,
  mirrors, visors, exhausts, underglow, trunk setups, 4 seat styles, 5 steering wheels, 4 dashes with a live
  speedometer, 5 shifters, dice and a club plaque; 8 rims, 3 knock-offs, 3 tyre profiles, 4 whitewall styles;
  finishes per chrome group, seat material + colours, tint, light colours, engine tunes; 15 liveries.
  Parts are in `build_lowrider_parts.py`; options and prices are in `NCLowriderConfig.Mods`.
  Roofs: hardtop, landau, full vinyl, convertible top down. 3 saved build slots, random build, back to stock.
