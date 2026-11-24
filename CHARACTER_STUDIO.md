# Character Studio: deep character customization

Players can look like whoever they want. That covers a rapper in iced-out Cuban links and grillz, a CEO, a soldier, a
bank robber in a ski mask, a beach local or a knight. It takes the *Ready Player One* idea of a bit of every world for
everyone, but **every item is original**. Names are generic ("Iced Cuban Link Chain", "Loose Bandana"). Nothing copies
a brand logo, a real person, or a specific character from a game or movie.

**Status: written and checked offline, not yet tested in Studio.** The Lua passes a syntax check. All 435 items
have been run through the geometry builder with no errors, and the catalog checker passes. Preset looks have been rendered
on the Neon Coast male body from the real catalog and builder code, to catch pieces that sit wrong.

## Install (one drag)

1. Drag `NeonCoastCharacterStudio.rbxmx` into **ServerScriptService**.
2. Press Play. On start, `LookStudioService` moves `NCLookCatalog` and `NCLookBuilder` to ReplicatedStorage and
   `LookStudioClient` to StarterPlayerScripts by itself.
3. If the old Studio-only **Character Studio** script is still in the place, disable it. Both scripts listen to the
   closet's `LocalSignals.OpenCharacterStudio`, so both would open. This new system replaces it completely: it saves
   looks, ownership and outfits, and it dresses every character on spawn.

Want to work from the files instead? `NCLookCatalog.lua` and `NCLookBuilder.lua` are ModuleScripts that go in
ReplicatedStorage. `LookStudioService.server.lua` goes in ServerScriptService and `LookStudioClient.client.lua` in
StarterPlayerScripts. Run `python tools/make_studio_package.py` to rebuild the .rbxmx after editing.

Settings (attributes, set them in Studio):
- `LookStudioService.FreeMode = true`: everything is free (testing or a creative server). If `NCWallet` isn't in
  ServerScriptService, it is free automatically.
- `LookStudioService.Sparkle = false`: turns off the twinkle on iced pieces.
- `LookStudioClient.HotKey = "K"`: adds a key that opens the studio (it's off by default; closets open it).
- `LookStudioClient.OpenOnFirstJoin = false`: stops the studio opening on a brand-new player's first spawn.

## No nudity, ever

Roblox banned this account before, so this is enforced in code, not left to the catalog:
- `NCLookBuilder` always dresses the **torso, hips and thighs in a plain base layer** (an undershirt and shorts) first.
  No item can turn those regions to skin. Any skin texture or SurfaceAppearance on them is stripped.
- `LookStudioService` puts that base layer on **the instant a character spawns**, before the saved look has loaded.
  It does it again if dressing ever fails.
- Top, Bottoms and Shoes are required slots. The server refills them from the default look if a client tries to
  send a look without them.

Only the head, arms, hands, lower legs and feet can ever show skin. Under skirts and dresses the base layer reads as
bike shorts, and every dress and crop top has sleeves. So even a blank or broken body model can't spawn without
clothes once this is installed, and no combination of items looks revealing. The preview mannequin in the
studio goes through the same code.

## What players get

- **435 items in 22 slots:** hair (62 styles), beards (17), tops (56, including jumpsuits, dresses and armour),
  jackets and vests (41), bottoms (28), shoes (21), hats (40), glasses (15), masks (15). Bling: 25 chains, each wearable in two
  layered slots, 9 grillz, 8 earrings, watches, bracelets and rings. Also gloves, belts and back items.
- **Two colours per item**, from realistic palettes: 20 skin tones from very fair to very deep, natural and dyed hair
  colours, fabric, denim, leather, metals (gold, white gold, rose gold, platinum) and gems.
- **84 preset looks** in 18 "worlds": Realistic Hood, Lowrider, Rap Royalty, Streetwear, For You Page, Business, Military,
  Heist Crew, Neon Coast, Sports, Jobs, Retro, Wild West, Sci-Fi, Fantasy, Heroes & Villains, Spooky and Cute.
  One tap tries on the whole outfit, and you can then tweak any piece. Presets never change your skin tone.
- **The studio screen:**
  - A live 3D preview of *your own* body. Drag to spin it, or zoom to Face or Body.
  - Tabs: Looks / Body / Clothes / Headwear / Bling / Extras / Saved.
  - Search, a world filter, 🔥 Trending and Owned filters.
  - 🎲 Random builds a look that hangs together by picking a world first.
  - Undo all, and 8 saved outfit slots.
  - It works on phones too, stacking the preview above the list in portrait.
- **Trying on is free.** "Buy & Wear" charges Cash through `NCWallet` (the same money jobs pay), only for items you
  don't own yet, and puts the look on for everyone.
- Your look, owned items and outfits save in the DataStore `NeonCoast_Look_v1`. If the store is down when you join,
  nothing gets overwritten.
- **New players** get the studio on their first spawn so they make their character.

## Tattoos and Lowrider

- **Tattoos** have two slots: Arm Ink (full and half sleeves, forearm script, roses, calves) and Face & Neck Ink (neck
  script, hand script, a small star or cross under the eye, eyebrow script). They are black-and-grey: a soft grey wash
  with linework on top.
- Ink only appears on **bare skin**. A long-sleeve top hides a sleeve, and nothing is ever drawn on the torso, because
  that's always covered. Roblox requires torso clothing ("modesty layers") on human avatars, so there are no shirtless
  chest or back pieces. A tank top shows the most ink.
- The **Lowrider** collection is Chicano lowrider fashion: creased khakis and work pants, white tees and tanks,
  top-button flannels, zoot suits with suspenders, folded bandanas, hairnets, rosaries, two-tone shoes and script ink.
  It's fashion only, with no gang names, colours, numbers or symbols, so it stays inside Roblox rules.

### Shoes and the white tank (2026-11-24)

- **Sneakers.** The 10 catalog sneakers use `build_shoe`, the shoe maker matched to the person's shoe references
  (`nc_catalog3d.SHOE_MAP`). The styles are court low and high, runner, skate and canvas high. Each shoe is sized from
  that body's own foot:
  - The toe box is never narrower or lower than the toes.
  - The sole never rises above the lowest toe.
  - The collision push only works at the heel and collar, so the toe box stays smooth. Before this, the heavier
    bodies' toes crumpled the front or poked out under it.
  - Dress shoes, boots and sandals still use the older `build_sneakers` maker.
- **Tank coverage.** Every top covers the white base-layer tank on all 10 bodies:
  - A crevice liner covers the armpit and side crease.
  - Small holes in the body shell are filled.
  - Sleeveless armholes hug the strap edge.
  - Open-front jackets show the tank on purpose.
  - `tools/qa/tankcheck.py <Body>` measures how much tank shows through (it flags anything over 0.3%).

## Real tattoos on the MakeHuman bodies (NCInk)

The MakeHuman bodies get real printed ink, done the same way as the car vinyls: a transparent PNG on a thin layer
that hugs the skin, so it looks like part of the skin, not a sticker.

- **Ink layers.** Every body has 13 layers (`Ink_LeftUpperArm`, `Ink_LeftLowerArm`, `Ink_LeftHand`, `Ink_LeftUpperLeg`,
  `Ink_LeftLowerLeg`, the same on the right, `Ink_NeckHead`, `Ink_NeckUpperTorso`, `Ink_Face`). Each one is a copy of the
  skin faces lifted 1.1 mm, one rigid layer per R15 part, welded to that part so it moves with the body. Clothes sit above it, so
  anything covered hides the ink. There is never any ink on the torso. The files are `ink/NC_Ink_<Body>.fbx`, one per
  body, built by `tools/ink/build_ink.py`.
- **Canvases.** All bodies share the same canvases, so one PNG fits every body without stretching:
  - Arm: shoulder to wrist, 768×1024, about 0.5 mm per pixel. Text is never mirrored. Positions are mirrored left to
    right so a piece faces forward on both arms.
  - Leg: hip to ankle, 640×1024.
  - Hand: back of the hand, 512×1024.
  - Neck: wraps around from under the ears, 1024×384.
  - Face: 768×1024.
  - Textures are clamped at the edge and each one keeps a clear border, so nothing repeats. Faces that span the cut
    between body parts are left out of the layers, so no ink smears across a seam.
- **Library.** There are 110 original tattoos, `ink/ink_catalog.json` → `NCInkCatalog.lua`. About 70% are black & grey
  and 30% colour:

  | Group | Count |
  |---|---|
  | Full sleeves | 12 |
  | Half sleeves (upper arm) | 9 |
  | Forearm sleeves | 8 |
  | Forearm pieces | 17, including 9 script words |
  | Upper-arm pieces | 8 |
  | Bands (upper arm and wrist) | 12 |
  | Hands | 13 |
  | Neck | 9 |
  | Face | 7, small, nothing on the eye |
  | Legs | 15, including leg sleeves, calf pieces and ankle bands |

  The art is drawn in Python (`tools/ink/motifs*.py`, `compose.py`) and rendered with Chromium (`rast.js`) using OFL
  Google fonts.
- **PG rules.**
  - Every word comes from the fixed safe list (`NCInkCatalog.WORDS`: Familia, Lealtad, Respeto, Bendecido, Fe, Amor,
    Smile Now / Cry Later ...).
  - There are no gang names, colours, numbers or symbols: no dots, no 13/14/18, no teardrop, no spiderweb.
  - There are no weapons and no bad words.
  - Chicano style comes from roses, clouds, clocks, rosaries, drama masks, dice, cards, lowriders, sugar skulls and
    old-English lettering.
- **Slots.** A look's ink is `{ L = { upper, lower, hand, leg }, R = { ... }, neck, face }`:
  - A full sleeve fills both upper and lower on that arm.
  - A leg sleeve fills the thigh and calf.
  - `NCInk.Validate` and `NCInk.Price` are for the server.
- **Studio setup.**
  1. Import `ink/NCInkSwatches_1.glb + NCInkSwatches_2.glb`, which holds every PNG on a plane, so Studio uploads the images.
  2. Run `require(game.ServerStorage.NCInkSetup).Prepare(workspace.NCInkSwatches_1)` then `_2`. It saves each texture id into
     `ReplicatedStorage.NCInkIds`.
  3. Import the 10 `NC_Ink_<Body>.fbx` files (3D Importer, no rig: they are plain meshes) into
     `ReplicatedStorage.NCInkRigs` as Models named after the body.
- **Runtime.**
  1. `NCInk.Attach(character, "Male_Average")` once after the body is built.
  2. `NCInk.Apply(character, ink)` whenever the look changes.

  Attach places each layer on its own body part from `Ink.FIT` (offset and size as fractions of the part) and holds
  it with a classic Weld. The layers are rigid on purpose: skinned layers came in scattered from the importer.
- **Rebuilding.**
  1. `python tools/ink/compose.py <out>` makes the PNGs and the catalog.
  2. `python tools/ink/build_ink.py rig.blend <out>` makes the layers.
  3. `python tools/ink/make_lua_catalog.py` makes the Lua catalog.
  4. `tools/ink/export_rigid.py` writes the rigid FBXs and `tools/ink/ink_fit.py` the `Ink.FIT` numbers, both from
     the layer blend that build_ink.py saves. `ink_fit.py` must measure against the same rig blend the Studio bodies were
     imported from (the part split changes between rig builds), or the ink sits off; `NCInk.Attach` warns if a part's
     size differs from `Ink.PART_SIZE`, and `NCInk.Debug(character)` prints each layer's placement.
  4. `tools/ink/build_swatches.py` makes the swatch file.
  5. `tools/ink/review.sh <Body>` renders every tattoo on a body to check it.

## How the 3D pieces work

`NCLookBuilder` builds every item from plain parts (balls, blocks, cylinders, wedges) welded to the body part they sit
on. Pieces are massless, with no collision and no touch or query. "Ball" pieces are blocks with a sphere mesh, so they
stretch into ellipsoids (a plain Ball part is always a perfect sphere). Fitted cylinders hug the limb they wrap. Sizes come from the body's own attachments: the head
radius from FaceCenter to FaceFront, and the torso unit from Neck to BodyFront. That way the same item fits the
6.6-stud Neon Coast human and a stock Roblox avatar.
- The body itself is recoloured per region: shirt on the torso and arms, pants on the hips and legs, shoes on the
  feet, skin on the rest. Materials are set too (Fabric, Leather, Metal, Glass for gems, Neon for cyber trim).
- Iced pieces get a small sparkle. Jerseys, tees and agent jackets print their text with SurfaceGuis.
- Hats flatten hair volume so nothing pokes through. Ski masks and full helmets hide hair, and face masks hide beards.
- **Real meshes:** any item can name an `assetId` (in its params). The server loads that Accessory with InsertService
  and wears it instead of the procedural pieces, and falls back to them if the load fails. **Your own Loose Bandana
  UGC** from your other game goes on `mask_loose_bandana`: put its asset id in `{ assetId = ... }`. InsertService can
  only load assets the game's owner owns.

This is the honest limit: these pieces are clean and stylised, not sculpted meshes. For truly realistic hair and
clothes, the next step is to sculpt the top sellers in Blender (locs, twists, durag, puffer, hoodie) with the same
pipeline as `build_human.py`, upload them, and point their items at the asset ids. The game code doesn't change.

**Tuning on the real body:** the face points (eyes, mouth for grillz, ears for earrings) live in one table,
`NCLookBuilder.FACE`. If grillz or glasses sit a little off on the final head, change the numbers there once and every
item follows.

## Real 3D clothes on the MakeHuman bodies (Nov 2026)

The procedural pieces above are the fallback. The real clothes are now sculpted-style meshes fitted to each of the
ten rigged MakeHuman bodies (`NeonCoast_MakeHumanRig.blend` from `build_makehuman_rig.py`), with the SevenM / Tha
Bronx 3 / realistic hood screenshots as the style target: boxy oversized hoodies, a pink camo zip-up, black-on-black
fits, baggy stacked denim, chunky chains, gloves and shades.

- `nc_garments.py` (Blender, pure bpy + numpy + scipy) makes every garment from the body itself:
  1. It fuses the skin, tank and shorts into one clean shell (voxel remesh) so there are no seams to follow.
  2. It cuts that surface along clean hem lines: a ring around the neck, sleeve ends along the arm, the waist and the ankles.
  3. It loosens the cloth with drape envelopes. Tops hang straight down from the chest (the radius never shrinks going
     down), sleeves become round tubes that gather at a rib cuff, pant legs become round tubes from the thigh to a wide
     opening, and the stacks wobble around the lower leg.
  4. It lets cloth hang past the body: hoodie hems drop below the hips, and pant legs drop onto the shoes.
  5. It smooths the result and pushes it outside the body and every layer underneath (tops over pants over shoes),
     so nothing pokes through on any body type.
  It also makes hoods, kangaroo pockets, drawstrings, zips, stand / shirt / lapel / turtleneck collars, open fronts,
  puffer baffles, camo (vertex colours), cargo pockets, jogger cuffs, skirts, lofted sneakers with a flat outsole and
  round toe, gloves, Cuban-link chains with a medallion, fitted caps, beanies and wraparound shades.
- `skin_to_rig` gives each garment the body's bone weights (sleeves can use arm and hand bones; the rest of the cloth
  can't, and each pant leg only follows its own leg). So the clothes move with the R15 rig and `NCAnimationsHuman`.
- `nc_outfits.py` holds the reference looks (`sevenm`, `pinkcamo`, `tee_cargo`, `puffer_sweats`).
- `nc_catalog3d.py` maps every Top / Outer / Bottom / Shoes item in `NCLookCatalog` (about 150) to the garment maker,
  using the item's own colours.
- `nc_headwear.py` fits the head pieces to each MakeHuman head the same way (cut from the head skin, lifted, smoothed,
  kept outside the head by the collider). `nc_catalog3d.py` sends these Head / Mask / Face items to it:
  - `hat_combat_helmet`, `hat_nvg_helmet`: army (ACH-style) shell clear of short hair, edge just above the brows and
    over the ear tops with a slight flare, cloth-cover seams, elastic band with two glow tabs at the back, side bolts,
    Y chin strap pulled tight under the jaw; the night-ops one adds side rails, the front shroud, stowed goggles and a
    back pouch.
  - `hat_durag`, `hat_durag_velvet`: matched to `references/head/durag.jpg`: snug crown with a centre seam, hem level
    round the head from the upper forehead over the ear tops to the base of the skull, a wide stitched tie band, the
    knot at the base of the skull, a wide tail flap that hugs the back of the neck and two flat tie ends over it.
  - `mask_ski` (eye and mouth holes), `mask_ski_open` (one face opening), `mask_ski_pom` (white rib edges and pom):
    knit under tension so it bridges the eye sockets, under the nose and the chin, rib roll on every opening, and a bib
    that runs over the neck base.
  - `hat_knight_helm`: flat-top great helm sized to clear the head by 1.4 cm and resting above the shoulders, eye slits
    with a nose bar, brow band, ridge and bottom band with rivets, cross-shaped breathing holes.
  - `eye_ski_goggles`, `eye_goggles_up`: wide toric lens with a nose notch, foam frame sealing to the face, elastic strap
    (pushed-up pair sits on the forehead, turned 75 degrees to the left).
  Checked from five angles on Male_Average, Male_Skinny, Male_Muscular, Female_Skinny and Female_Heavy with the skin
  rendered bright green: nothing pokes through.
- `build_wardrobe.py` builds them on all ten bodies. It saves `NeonCoast_Wardrobe_<Body>.blend` (one collection per
  look) and game-ready FBX files: subdivision off, decimated to about 7k triangles per piece, skinned to the rig, ready
  for Studio's 3D importer.
  `blender -b -P build_wardrobe.py -- NeonCoast_MakeHumanRig.blend wardrobe`
- The base layer (white tank, shorts, `NC_Modesty`) is part of the body under every garment. Clothes only ever add
  layers on top, so there is still no nudity anywhere.

## The research behind it (Nov 2026)

What players asked for, and what the web shows is popular right now:
- **Realistic hood RP, the main style reference.** The references are "[REALISTIC] SevenM Hood Testing" and
  "Tha Bronx 3". The looks people pick there are locs or messy twists falling over black wraparound shades, black
  heavyweight and puff-print hoodies, pink or woodland camo zip hoodies, iced Cuban chains with big iced pendants,
  black leather gloves, ski masks (including open-face), durags, flat-brim fitted caps, duck-canvas work jackets with
  wheat work boots, and black with red, blue or yellow colourways. All of that is in the **Realistic Hood**
  collection, with no brand logos. We use the realistic human body, not the stretched faces those games have.
  ([South Bronx community style](https://roblox-outfit-styles.fandom.com/wiki/Bronx),
  [SevenM](https://www.roblox.com/games/131558436575033/SevenM-Hood-Testing))
- **Hair:** the modern mullet, textured fluffy fringes (perms), low tapers and burst fades, the blunt-fringe skin fade,
  curtain bangs, the butterfly cut, the glossy Italian bob, glass hair and claw-clip twists.
  ([FASHION Magazine](https://fashionmagazine.com/beauty-grooming/womens-mens-haircut-trends-2026/),
  [John Frieda](https://www.johnfrieda.com/en-uk/blog/hairstyles/tik-tok-hair-trends/),
  [men's TikTok guide](https://www.hairstyletryon.ai/blog/mens-hair-trends-tiktok-guide))
- **Beards:** faded beards, the short boxed comeback, and sharp Mediterranean shaping.
  ([Beardbrand](https://www.beardbrand.com/blogs/urbanbeardsman/beard-styles), [Goldie](https://heygoldie.com/blog/best-beard-styles))
- **TikTok and 2026 fashion:** bows and pearls, gorpcore (shells, cargo), office chic (pencil skirts and
  thin specs), coastal cowgirl, fisherman core, the countryside-prep waxed field jacket, the funnel-neck jacket,
  brass-button officer jackets, wedge heels, barrel pants, quarter-zips, butter yellow, matcha green and the fur
  statement coat.
  ([Who What Wear](https://www.whowhatwear.com/fashion/trends/tiktok-fashion-trends-2026),
  [Trendalytics](https://trendalytics.co/trend-insights/the-10-biggest-tiktok-fashion-trends-of-2026),
  [Core trend dictionary](https://www.acloset.app/magazine/core-trend-dictionary-2026-decoding-tiktok-micro-trends-wit/))
- **Streetwear:** baggy stacked denim and jorts, jerseys (hoops, football kits, hockey), chunky retro runners and
  slimmer retro runners. ([Asphaltgold](https://www.asphaltgold.com/en/blogs/allgemein/streetwear-trends-2026))
- **Hip-hop jewellery:** Cuban links plain and iced, tennis chains, crosses, meaningful pendants, pearls on men, and
  grillz going mainstream. ([VVS Jewelry](https://vvsjewelry.com/blogs/bling-bling/rapper-grillz-jewelry),
  [Metalonyx](https://www.metalonyx.com/custom-hip-hop-jewellery-design-ideas/))
- **Slang tees from short video:** "AURA +1000", "6 7", "LOCKED IN", "MAIN CHARACTER" and "NPC".
- **2026 movies and games, as generic inspired-by pieces.** These come from Google's trending Halloween costumes and
  the year's releases: a bronze warrior cuirass with a red cape (the Greek-epic trend), a red deep-space suit, red and
  black animal-stripe tops, a field agent windbreaker, hockey sweaters and varsity jackets, pastel linen suits and red
  sequin dresses (the 80s Miami look ahead of the big open-world crime game), and a unicorn onesie hood.
  ([Variety](https://variety.com/2026/shopping/news/google-top-trending-halloween-costumes-2026-shop-online-1236910312/),
  [That Shelf](https://thatshelf.com/halloween-costumes-from-2026s-biggest-films-tv-and-pop-culture-moments/),
  [GTA VI fashion](https://www.themoviefashion.com/gta-6-release-complete-fashion-outfit-guide-2026-for-lucia-and-jason/))
- **Roblox avatar demand:** hair and face items are the top sellers, along with tactical "tuff" gear, Y2K and cute
  items, and clean minimal glasses and headphones.
  ([rolearn](https://rolearn.dev/trend-reports/roblox-ugc-marketplace-trends-2026/),
  [kwstudio](https://kwstudio.org/blog/news/most-popular-roblox-ugc-items-in-2025-trending-accessories?gi=8fa7e6d824f2d8cbe8548b2b4336cf775c666c98))

On "looks from popular TikTokers": the catalog captures what those creators made popular (cuts, fits, colourways,
jewellery). It does not copy any real person's face or signature look, because Roblox and copyright rules don't allow
that.

## Adding items

Copy a line in `NCLookCatalog.lua`, give it a new id, and pick a family from `NCLookBuilder` (`F.<name>`) plus
palettes. Run `python tools/check_look_catalog.py`. It catches unknown families or palettes, duplicate ids, presets
that point at missing items, and preset colours that aren't allowed. Then rebuild the package.

## Check in Studio

- Spawn with the Neon Coast human body. Check that hair sits on the scalp, grillz sit at the mouth, glasses at the
  eyes and chains on the chest. Tune `NCLookBuilder.FACE` if needed.
- Open a closet and use "Change outfit". Try on, buy, respawn, and confirm the look comes back.
- Change the build in the gym: FitnessService should scale on top of the look (it uses `NC_LookBase`).
- Ragdoll with a full look on: pieces are welded to the parts, so they should follow.
- Watch performance with 20+ players in full bling. The heaviest item is about 70 parts, and a full look is about
  150 to 250.
