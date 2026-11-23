--!nonstrict
-- NCLookCatalog (ModuleScript in ReplicatedStorage): every item and preset look in the Character Studio.
-- Pure data: NCLookBuilder turns an item's family (fam) + params (p) into geometry; the server checks prices,
-- slots and colours against this file; the studio UI lists it.
--
-- Everything here is original and named generically ("Iced Cuban Link Chain", "Loose Bandana"). Looks are
-- inspired by trends, styles and genres, never copies of a real person, brand logo or a specific game/movie
-- character. See CHARACTER_STUDIO.md for the research behind each collection.
--
-- Adding an item: copy a line in the right section, give it a new unique id, pick a family from NCLookBuilder
-- (B.FAMILIES) and palettes. Set assetId to an Accessory asset you own to wear a real mesh instead of the
-- procedural one (the server loads it with InsertService and falls back to the procedural one if it can't).
local C = {}

---------------------------------------------------------------------------------------------------- slots
-- order = the order pieces layer in (bottoms under tops under jackets ...). required = can't be empty.
C.SLOTS = {
	{ id = "Skin", name = "Skin", icon = "✋", required = true },
	{ id = "Hair", name = "Hair", icon = "💇" },
	{ id = "FacialHair", name = "Beard", icon = "🧔" },
	{ id = "Eyes", name = "Eyes", icon = "👁️", required = true },
	{ id = "Brows", name = "Brows", icon = "〰️", required = true },
	{ id = "Bottom", name = "Bottoms", icon = "👖", required = true },
	{ id = "Top", name = "Tops", icon = "👕", required = true },
	{ id = "Outer", name = "Jackets", icon = "🧥" },
	{ id = "Shoes", name = "Shoes", icon = "👟", required = true },
	{ id = "Head", name = "Hats", icon = "🧢" },
	{ id = "Face", name = "Glasses", icon = "🕶️" },
	{ id = "Mask", name = "Masks", icon = "🎭" },
	{ id = "Neck", name = "Chains", icon = "📿" },
	{ id = "Neck2", name = "Chain 2", icon = "📿" },
	{ id = "Grillz", name = "Grillz", icon = "😁" },
	{ id = "Ears", name = "Earrings", icon = "💎" },
	{ id = "Wrist", name = "Watch", icon = "⌚" },
	{ id = "Wrist2", name = "Bracelets", icon = "💫" },
	{ id = "Rings", name = "Rings", icon = "💍" },
	{ id = "Hands", name = "Gloves", icon = "🧤" },
	{ id = "Waist", name = "Belts", icon = "👝" },
	{ id = "Back", name = "Back", icon = "🎒" },
}

-- the studio's category tabs group the slots
C.TABS = {
	{ name = "Body", slots = { "Skin", "Eyes", "Brows", "Hair", "FacialHair" } },
	{ name = "Clothes", slots = { "Top", "Outer", "Bottom", "Shoes" } },
	{ name = "Headwear", slots = { "Head", "Face", "Mask" } },
	{ name = "Bling", slots = { "Neck", "Neck2", "Grillz", "Ears", "Wrist", "Wrist2", "Rings" } },
	{ name = "Extras", slots = { "Hands", "Waist", "Back" } },
}

-- collections: the "worlds" filter in the studio (Ready Player One style: a bit of everything, all original)
C.COLLECTIONS = {
	{ id = "hood", name = "Realistic Hood", blurb = "Locs over the shades, black hoodies, iced chains, ski masks." },
	{ id = "lowrider", name = "Lowrider", blurb = "Chicano lowrider style: creased khakis, white tees, flannels, zoot suits, fine-line ink." },
	{ id = "rap", name = "Rap Royalty", blurb = "Gold and iced-out chains, grillz, watches, fits that shine." },
	{ id = "street", name = "Streetwear", blurb = "Baggy denim, jerseys, chunky sneakers, 2026 street staples." },
	{ id = "tiktok", name = "For You Page", blurb = "Looks that blew up on short video in the last six months." },
	{ id = "business", name = "Business", blurb = "Suits, quiet luxury, office siren, corner office." },
	{ id = "military", name = "Military", blurb = "Field uniforms, plate carriers, helmets, flight suits." },
	{ id = "heist", name = "Heist Crew", blurb = "Ski masks, duffels, getaway drivers, cat burglars." },
	{ id = "coast", name = "Neon Coast", blurb = "Florida beach, pool and boardwalk living." },
	{ id = "sport", name = "Sports", blurb = "Hoopers, footballers, hockey, the gym." },
	{ id = "work", name = "Jobs", blurb = "Medics, chefs, mechanics, lifeguards, construction." },
	{ id = "retro", name = "Retro", blurb = "80s pastels, 90s grunge, Y2K." },
	{ id = "western", name = "Wild West", blurb = "Cowboy hats, bandanas, boots." },
	{ id = "scifi", name = "Sci-Fi", blurb = "Spacesuits, cyber runners, VR visors, troopers." },
	{ id = "fantasy", name = "Fantasy", blurb = "Knights, wizards, ancient warriors, ronin." },
	{ id = "hero", name = "Heroes & Villains", blurb = "Capes, masks, suits in your colours." },
	{ id = "spooky", name = "Spooky", blurb = "Horror-night masks, vampires, monsters." },
	{ id = "cute", name = "Cute", blurb = "Coquette bows, ears, unicorns, soft colours." },
}

---------------------------------------------------------------------------------------------------- palettes
-- skin: a realistic range from very fair to very deep, warm and cool undertones
C.PALETTES = {
	skin = { "#FBE3D3", "#F6D5C0", "#F0C8AC", "#EBC0A0", "#E3B190", "#D9A27E", "#CF9670", "#C68863", "#BC7B57",
		"#AF6E4C", "#A26244", "#94563A", "#874B33", "#7A412C", "#6C3725", "#5E2F20", "#51281B", "#442116", "#3A1C13", "#2F170F" },
	hair = { "#0B0908", "#1C1512", "#2C2019", "#3B2A1F", "#4E3626", "#6A4630", "#7F5539", "#8E5B3C", "#A0522D", "#B5562C",
		"#C26A3A", "#A8743F", "#C9995C", "#DDBA80", "#E8D0A0", "#F3E6C8", "#D9D4CC", "#B8B2A8", "#8A8580", "#FFFFFF",
		-- dyed: butter yellow, matcha, cherry, pastel pink, electric blue, violet, platinum ice, burgundy, money green
		"#F6E27A", "#9BBF6A", "#B3122E", "#F4A6C8", "#2F6BFF", "#7B3FE4", "#E9F0F5", "#6E1A2E", "#1F7A3A" },
	fabric = { "#111111", "#2B2B2B", "#4A4A4A", "#8C8C8C", "#D6D6D6", "#F5F5F2", "#1B2A41", "#2E4A7A", "#4F7CC2",
		"#9CC3E6", "#0F5257", "#2F7D6D", "#4B5320", "#6B7B3A", "#9BBF6A", "#C8B88A", "#E8DCC0", "#F6E27A", "#E8A33D",
		"#D96C2C", "#B3122E", "#7A1022", "#F4A6C8", "#E0447A", "#7B3FE4", "#4A2B6B", "#5C3A21", "#8B5A2B", "#B98A5E",
		"#C68E5A",
		"#FF2BD6", "#00A2FF", "#FFE600", "#FF3B30", "#39FF14" },
	denim = { "#1E2A3A", "#26354D", "#34507A", "#4C6F9E", "#7A9CC6", "#A9C1DD", "#111418", "#3A3A3A", "#D8D2C4", "#F5F5F2" },
	leather = { "#111111", "#2A1B12", "#4A2C1A", "#6B3E22", "#8B5A2B", "#B98A5E", "#7A1022", "#F5F5F2", "#C8963E",
		"#8C8C8C", "#FF3B30", "#FFE600", "#2E4A7A" },
	metal = { "#E2B240", "#F0C75E", "#DE9680", "#D4D6DC", "#F2F2F2", "#2A2A2A" },
	gem = { "#ECF6FF", "#FFFFFF", "#7FD6FF", "#FF5C8A", "#7CFF9B", "#B88CFF", "#FFD24A", "#111111", "#FF3B30" },
	neon = { "#00FFDC", "#FF2BD6", "#39FF14", "#FFE600", "#00A2FF", "#FF5F1F", "#FFFFFF" },
	bright = { "#F5F5F2", "#111111", "#FFE600", "#00A2FF", "#FF2BD6", "#39FF14", "#FF3B30", "#7B3FE4", "#FF8A00", "#F4A6C8",
		"#B3122E", "#2B2B2B", "#4A2B6B", "#1B2A41" },
	lens = { "#111111", "#2A2F38", "#3B2A1F", "#7A1022", "#2E4A7A", "#E8A33D", "#F4A6C8", "#9CC3E6", "#F5F5F2" },
	sole = { "#F5F5F2", "#111111", "#C8963E", "#8C8C8C", "#B3122E", "#2E4A7A" },
	-- eye colours: browns, hazel, amber, greens, greys, blues
	eye = { "#2B1A10", "#3D2616", "#4E3420", "#5E3E22", "#6E4B2A", "#7A5A30", "#8A6A3A", "#A07A3A", "#6B6A3A", "#56683F",
		"#3F6B4A", "#2F5E46", "#6E7B7E", "#8A949A", "#5C7A9A", "#3E6A9E", "#2F4F7F", "#7FA6C9" },
	ink = { "#1A1A1A", "#26303C", "#2B3A4A", "#3B2A1F", "#1F4F3A", "#7A1022" },
	camo = { "#4B5320", "#6B7B3A", "#C8B88A", "#8C8C8C", "#2B2B2B", "#F4A6C8", "#4F7CC2", "#B3122E" },
}

---------------------------------------------------------------------------------------------------- items
-- I(id, slot, name, price, fam, params, pal1, def1, pal2, def2, collections, tags, mat)
-- tags: "trend" = shows a 🔥 badge and in the Trending filter; "new" = ✨
C.ITEMS = {}
local function I(id, slot, name, price, fam, pp, pal1, def1, pal2, def2, cols, tags)
	table.insert(C.ITEMS, {
		id = id, slot = slot, name = name, price = price, fam = fam, p = pp or {},
		pal1 = pal1, def1 = def1, pal2 = pal2, def2 = def2,
		cols = cols or {}, tags = tags or {},
	})
end
local T, N = { "trend" }, { "new" }
local TN = { "trend", "new" }

------------------------------------------------------------------ skin
I("skin", "Skin", "Natural Skin", 0, "bald", {}, "skin", "#CF9670")

------------------------------------------------------------------ hair
local H = "hair"
I("hair_bald", "Hair", "Clean Shaved Head", 0, "bald", {}, H, "#1C1512")
I("hair_buzz", "Hair", "Buzz Cut", 0, "buzz", {}, H, "#1C1512", nil, nil, { "military", "street" })
I("hair_buzz_fade", "Hair", "Buzz Cut Skin Fade", 0, "buzz", { fade = true }, H, "#0B0908", nil, nil, { "street" })
I("hair_crew", "Hair", "Classic Crew Cut", 0, "crew", {}, H, "#3B2A1F", nil, nil, { "business", "military" })
I("hair_waves", "Hair", "360 Waves", 150, "waves", {}, H, "#0B0908", nil, nil, { "hood", "rap", "street" }, T)
I("hair_waves_fade", "Hair", "360 Waves Low Fade", 180, "waves", { fade = true }, H, "#0B0908", nil, nil, { "hood", "rap" }, T)
I("hair_low_taper", "Hair", "Low Taper Textured Top", 220, "fadetop", { vol = 0.2, fringe = true }, H, "#1C1512", nil, nil, { "street", "tiktok" }, T)
I("hair_mid_fade", "Hair", "Mid Fade Crop", 200, "fadetop", { vol = 0.15 }, H, "#2C2019", nil, nil, { "street" })
I("hair_high_fade_part", "Hair", "High Fade Hard Part", 220, "fadetop", { vol = 0.18, part = true }, H, "#1C1512", nil, nil, { "street", "business" })
I("hair_burst_fade", "Hair", "Burst Fade Fluffy Top", 260, "fadetop", { vol = 0.4, fringe = true }, H, "#1C1512", nil, nil, { "tiktok", "street" }, T)
I("hair_edgar", "Hair", "Blunt Fringe Skin Fade", 220, "edgar", {}, H, "#0B0908", nil, nil, { "street", "tiktok" }, T)
I("hair_fluffy_fringe", "Hair", "Fluffy Perm Fringe", 280, "fringe", { th = 0.12, vol = 0.35, n = 7 }, H, "#2C2019", nil, nil, { "tiktok" }, TN)
I("hair_french_crop", "Hair", "French Crop", 200, "fringe", { th = 0.06, fade = true, n = 5 }, H, "#3B2A1F", nil, nil, { "street", "business" })
I("hair_curtains", "Hair", "Curtain Bangs", 240, "curtains", { th = 0.1 }, H, "#4E3626", nil, nil, { "tiktok", "retro" }, T)
I("hair_long_curtains", "Hair", "Long Curtains Past the Ears", 280, "curtains", { th = 0.12, len = 0.9 }, H, "#6A4630", nil, nil, { "tiktok", "retro" })
I("hair_pomp", "Hair", "Slick Pompadour", 240, "pomp", {}, H, "#1C1512", nil, nil, { "business", "retro" })
I("hair_pomp_fade", "Hair", "Pompadour Skin Fade", 260, "pomp", { fade = true, vol = 0.2 }, H, "#1C1512", nil, nil, { "street" })
I("hair_slick_back", "Hair", "Slicked Back", 200, "slick", {}, H, "#1C1512", nil, nil, { "business" })
I("hair_slick_long", "Hair", "Long Slick Back", 260, "slick", { len = 0.9 }, H, "#2C2019", nil, nil, { "business", "fantasy" })
I("hair_side_part", "Hair", "Gentleman's Side Part", 180, "sidepart", {}, H, "#3B2A1F", nil, nil, { "business" })
I("hair_spiky", "Hair", "Frosted Spikes", 200, "spiky", { h = 0.1 }, H, "#C9995C", nil, nil, { "retro" })
I("hair_mohawk", "Hair", "Mohawk", 220, "mohawk", { h = 0.55 }, H, "#0B0908", nil, nil, { "retro", "scifi" })
I("hair_faux_hawk", "Hair", "Faux Hawk", 200, "mohawk", { h = 0.3 }, H, "#1C1512", nil, nil, { "street" })
I("hair_modern_mullet", "Hair", "Modern Mullet", 260, "mullet", { th = 0.14, fade = true, len = 0.9 }, H, "#4E3626", nil, nil, { "tiktok", "street" }, T)
I("hair_classic_mullet", "Hair", "80s Mullet", 220, "mullet", { th = 0.1, len = 1.3 }, H, "#8E5B3C", nil, nil, { "retro" })
I("hair_sponge_twists", "Hair", "Sponge Twists", 220, "twists", { fade = true, len = 0.2 }, H, "#0B0908", nil, nil, { "hood", "street" }, T)
I("hair_twists_long", "Hair", "Two-Strand Twists", 260, "twists", { len = 0.45 }, H, "#0B0908", nil, nil, { "hood", "rap" })
I("hair_flat_twists", "Hair", "Flat Twists", 260, "twists", { fade = true, len = 0.12 }, H, "#0B0908", nil, nil, { "hood", "street" }, T)
I("hair_messy_twists", "Hair", "Messy Twists Over the Eyes", 320, "locs", { len = 0.85, n = 18, d = 0.15, front = true }, H, "#0B0908", nil, nil, { "hood", "tiktok" }, TN)
I("hair_curly_top", "Hair", "Curly Top Taper", 240, "curlytop", { n = 16, vol = 0.12 }, H, "#1C1512", nil, nil, { "street", "tiktok" }, T)
I("hair_high_top", "Hair", "High Top Fade", 220, "hightop", { h = 0.9 }, H, "#0B0908", nil, nil, { "retro", "street" })
I("hair_afro", "Hair", "Full Afro", 260, "afro", { size = 2.9 }, H, "#0B0908", nil, nil, { "retro", "street" })
I("hair_afro_big", "Hair", "Statement Afro", 300, "afro", { size = 3.4 }, H, "#1C1512", nil, nil, { "retro" })
I("hair_afro_puff", "Hair", "Afro Puff", 220, "puff", {}, H, "#0B0908", nil, nil, { "cute", "street" })
I("hair_afro_puffs", "Hair", "Double Afro Puffs", 240, "puff", { two = true, size = 1.0 }, H, "#0B0908", nil, nil, { "cute" })
I("hair_locs_short", "Hair", "Starter Locs", 260, "locs", { len = 0.9, n = 16 }, H, "#0B0908", nil, nil, { "hood", "rap" }, T)
I("hair_locs_long", "Hair", "Long Locs", 320, "locs", { len = 1.9, n = 18 }, H, "#0B0908", nil, nil, { "hood", "rap" }, T)
I("hair_locs_gold", "Hair", "Gold-Cuffed Locs", 420, "locs", { len = 1.6, n = 16, tips = true }, H, "#0B0908", "metal", "#E2B240", { "hood", "rap" }, T)
I("hair_locs_front", "Hair", "Locs Over the Shades", 380, "locs", { len = 1.3, n = 18, front = true }, H, "#0B0908", nil, nil, { "hood", "rap" }, TN)
I("hair_locs_up", "Hair", "Locs Tied Up", 320, "locs", { len = 0.7, n = 12, up = true }, H, "#1C1512", nil, nil, { "hood", "street" })
I("hair_freeform", "Hair", "Freeform Locs", 300, "locs", { len = 1.2, n = 22, d = 0.2 }, H, "#2C2019", nil, nil, { "hood", "street" })
I("hair_cornrows", "Hair", "Straight-Back Cornrows", 240, "braids", { rows = 7 }, H, "#0B0908", nil, nil, { "hood", "rap", "street" }, T)
I("hair_cornrows_long", "Hair", "Cornrows with Long Braids", 300, "braids", { rows = 8, len = 1.6, n = 12 }, H, "#0B0908", nil, nil, { "hood", "rap" }, T)
I("hair_box_braids", "Hair", "Box Braids", 320, "braids", { rows = 9, len = 2.4, n = 16, d = 0.12 }, H, "#0B0908", nil, nil, { "street", "cute" })
I("hair_braids_beads", "Hair", "Braids with Gold Beads", 380, "braids", { rows = 8, len = 1.8, n = 14, tips = true }, H, "#0B0908", "metal", "#E2B240", { "rap", "cute" }, T)
I("hair_long_straight", "Hair", "Long Straight", 260, "long", { len = 2.2 }, H, "#2C2019", nil, nil, { "cute", "business" })
I("hair_long_sleek", "Hair", "Sleek Glass Hair", 300, "long", { len = 2.4, sleek = true }, H, "#0B0908", nil, nil, { "tiktok", "business" }, T)
I("hair_long_wavy", "Hair", "Beach Waves", 280, "long", { len = 2.2, wavy = true }, H, "#C9995C", nil, nil, { "coast", "tiktok" })
I("hair_butterfly", "Hair", "Butterfly Cut Blowout", 320, "long", { len = 1.9, layers = true }, H, "#6A4630", nil, nil, { "tiktok" }, TN)
I("hair_long_bangs", "Hair", "Long with Wispy Bangs", 280, "long", { len = 2.0, bangs = true }, H, "#3B2A1F", nil, nil, { "tiktok", "cute" }, T)
I("hair_wolf_cut", "Hair", "Wolf Cut", 280, "long", { len = 1.1, layers = true, th = 0.14 }, H, "#1C1512", nil, nil, { "tiktok", "street" }, T)
I("hair_long_male", "Hair", "Shoulder-Length Flow", 240, "long", { len = 1.2 }, H, "#4E3626", nil, nil, { "fantasy", "coast" })
I("hair_bob", "Hair", "Jawline Bob", 240, "bob", { len = 0.3 }, H, "#1C1512", nil, nil, { "tiktok", "business" }, T)
I("hair_italian_bob", "Hair", "Glossy Italian Bob", 260, "bob", { len = 0.6 }, H, "#3B2A1F", nil, nil, { "tiktok", "business" }, TN)
I("hair_bob_bangs", "Hair", "Bob with Bangs", 260, "bob", { len = 0.45, bangs = true }, H, "#0B0908", nil, nil, { "retro", "cute" })
I("hair_pixie", "Hair", "Soft Pixie", 220, "pixie", {}, H, "#DDBA80", nil, nil, { "tiktok" })
I("hair_pony", "Hair", "Sleek Ponytail", 240, "pony", { len = 1.6 }, H, "#1C1512", "fabric", "#111111", { "sport", "business" })
I("hair_high_pony", "Hair", "Snatched High Pony", 260, "pony", { high = true, len = 1.9 }, H, "#0B0908", "fabric", "#111111", { "tiktok", "street" }, T)
I("hair_braided_pony", "Hair", "Braided Ponytail", 280, "pony", { len = 1.9, braid = true }, H, "#4E3626", "fabric", "#111111", { "sport", "fantasy" })
I("hair_bun", "Hair", "Top Bun", 200, "bun", {}, H, "#3B2A1F", nil, nil, { "cute", "sport" })
I("hair_claw_clip", "Hair", "Claw Clip Twist", 240, "bun", { low = true, claw = true }, H, "#6A4630", "fabric", "#C68E5A", { "tiktok", "cute" }, T)
I("hair_space_buns", "Hair", "Space Buns", 240, "bun", { two = true }, H, "#F4A6C8", nil, nil, { "cute", "retro" })
I("hair_man_bun", "Hair", "Man Bun", 220, "bun", { low = true }, H, "#2C2019", nil, nil, { "coast", "fantasy" })

------------------------------------------------------------------ eyes and brows (real meshes on the MakeHuman faces)
I("eyes_natural", "Eyes", "Natural Eyes", 0, "eyes", {}, "eye", "#4E3420")
I("brows_natural", "Brows", "Natural Brows", 0, "meshface", { piece = "Brows_Natural" }, H, "#2C2019")
I("brows_thick", "Brows", "Thick Brows", 0, "meshface", { piece = "Brows_Thick" }, H, "#1C1512", nil, nil, { "street", "tiktok" }, T)
I("brows_arched", "Brows", "Arched Brows", 0, "meshface", { piece = "Brows_Arched" }, H, "#2C2019", nil, nil, { "business", "cute" })
I("brows_straight", "Brows", "Straight Brows", 0, "meshface", { piece = "Brows_Straight" }, H, "#2C2019", nil, nil, { "tiktok" }, T)
I("brows_thin", "Brows", "Thin Brows", 0, "meshface", { piece = "Brows_Thin" }, H, "#3B2A1F", nil, nil, { "retro" })

------------------------------------------------------------------ facial hair
I("beard_stubble", "FacialHair", "Five O'Clock Shadow", 0, "stubble", {}, H, "#1C1512", nil, nil, { "street", "business" })
I("beard_heavy_stubble", "FacialHair", "Heavy Stubble", 80, "stubble", { t = 0.3 }, H, "#1C1512", nil, nil, { "street" })
I("beard_short_boxed", "FacialHair", "Short Boxed Beard", 150, "beard", { boxed = true }, H, "#1C1512", nil, nil, { "business", "street" }, T)
I("beard_full", "FacialHair", "Full Beard", 180, "beard", { len = 0.2 }, H, "#2C2019", nil, nil, { "street", "western" })
I("beard_fade", "FacialHair", "Faded Beard", 180, "beard", { fade = true }, H, "#1C1512", nil, nil, { "hood", "street" }, T)
I("beard_mediterranean", "FacialHair", "Sharp Mediterranean Beard", 200, "beard", { len = 0.1, boxed = true }, H, "#0B0908", nil, nil, { "business" }, T)
I("beard_long", "FacialHair", "Long Beard", 220, "beard", { len = 0.9 }, H, "#3B2A1F", nil, nil, { "western", "fantasy" })
I("beard_viking", "FacialHair", "Braided Warrior Beard", 260, "beard", { len = 1.0, braid = true }, H, "#8E5B3C", "metal", "#D4D6DC", { "fantasy" })
I("beard_goatee", "FacialHair", "Goatee", 120, "goatee", {}, H, "#1C1512", nil, nil, { "rap", "street" })
I("beard_chin_beard", "FacialHair", "Chin Beard", 120, "goatee", { len = 0.25 }, H, "#0B0908", nil, nil, { "hood", "rap" }, T)
I("beard_chinstrap", "FacialHair", "Chin Strap", 120, "chinstrap", {}, H, "#0B0908", nil, nil, { "hood", "street" })
I("beard_mustache", "FacialHair", "Classic Mustache", 100, "mustache", {}, H, "#2C2019", nil, nil, { "retro", "business" })
I("beard_pencil", "FacialHair", "Pencil Mustache", 100, "mustache", { w = 0.7, thick = 0.08 }, H, "#0B0908", nil, nil, { "business", "retro" })
I("beard_horseshoe", "FacialHair", "Horseshoe Mustache", 140, "mustache", { horseshoe = true }, H, "#4E3626", nil, nil, { "western", "retro" })
I("beard_handlebar", "FacialHair", "Handlebar Mustache", 140, "mustache", { handlebar = true }, H, "#6A4630", nil, nil, { "western" })
I("beard_sideburns", "FacialHair", "Mutton Sideburns", 100, "sideburns", { len = 0.7 }, H, "#3B2A1F", nil, nil, { "retro", "western" })
I("beard_soul_patch", "FacialHair", "Soul Patch", 60, "soulpatch", {}, H, "#1C1512", nil, nil, { "retro" })

------------------------------------------------------------------ tattoos (only show on bare skin: sleeves cover arm ink)
local K = "ink"

------------------------------------------------------------------ tops
local F = "fabric"
I("top_tee", "Top", "Plain Tee", 0, "tee", {}, F, "#F5F5F2", F, "#111111", { "street" })
I("top_tee_black", "Top", "Heavyweight Black Tee", 0, "tee", {}, F, "#111111", F, "#F5F5F2", { "street", "hood" })
I("top_tank", "Top", "Ribbed Tank", 0, "tee", { sleeve = "tank" }, F, "#F5F5F2", F, "#111111", { "coast", "sport", "lowrider" })
I("top_long_white", "Top", "Long Oversized White Tee", 60, "tee", {}, F, "#F5F5F2", F, "#F5F5F2", { "lowrider", "street" }, T)
I("top_button_flannel", "Top", "Top-Button Flannel", 160, "shirt", { placket = "dark" }, F, "#111111", F, "#2E4A7A", { "lowrider" }, T)
I("top_short_flannel", "Top", "Short-Sleeve Plaid Shirt", 140, "shirt", { sleeve = "tee", placket = "dark", print = true }, F, "#1B2A41", F, "#F5F5F2", { "lowrider", "coast" })
I("top_longsleeve", "Top", "Long Sleeve Tee", 60, "tee", { sleeve = "long" }, F, "#2B2B2B", F, "#F5F5F2", { "street" })
I("top_pocket_tee", "Top", "Pocket Tee", 60, "tee", { pocket = true }, F, "#C8B88A", F, "#5C3A21", { "street", "work" })
I("top_stripe_tee", "Top", "Chest Stripe Tee", 80, "tee", { stripe = true }, F, "#F5F5F2", F, "#1B2A41", { "retro", "coast" })
I("top_tee_aura", "Top", "\"AURA +1000\" Tee", 120, "tee", { text = "AURA +1000" }, F, "#111111", F, "#F5F5F2", { "tiktok" }, TN)
I("top_tee_67", "Top", "\"6 7\" Tee", 120, "tee", { text = "6 7" }, F, "#F5F5F2", F, "#111111", { "tiktok" }, T)
I("top_tee_locked", "Top", "\"LOCKED IN\" Tee", 120, "tee", { text = "LOCKED IN" }, F, "#2B2B2B", F, "#F6E27A", { "tiktok", "sport" }, T)
I("top_tee_main", "Top", "\"MAIN CHARACTER\" Tee", 120, "tee", { text = "MAIN CHARACTER" }, F, "#F4A6C8", F, "#111111", { "tiktok", "cute" }, T)
I("top_tee_npc", "Top", "\"NPC\" Tee", 100, "tee", { text = "NPC" }, F, "#8C8C8C", F, "#111111", { "tiktok" })
I("top_tee_coast", "Top", "\"NEON COAST\" Tee", 100, "tee", { text = "NEON COAST" }, F, "#00A2FF", "neon", "#FF2BD6", { "coast" })
I("top_tee_palmgrove", "Top", "\"PALMGROVE\" Tee", 100, "tee", { text = "PALMGROVE" }, F, "#F6E27A", F, "#0F5257", { "coast" })
I("top_tee_nodays", "Top", "\"NO DAYS OFF\" Tee", 100, "tee", { text = "NO DAYS OFF" }, F, "#111111", F, "#B3122E", { "sport" })
I("top_hoodie", "Top", "Heavyweight Hoodie", 150, "hoodie", {}, F, "#111111", F, "#F5F5F2", { "hood", "street" }, T)
I("top_hoodie_zip", "Top", "Zip Hoodie", 160, "hoodie", { zip = true }, F, "#2B2B2B", F, "#F5F5F2", { "street" })
I("top_hoodie_puff", "Top", "Puff Print Graphic Hoodie", 260, "hoodie", { puff = true }, F, "#111111", F, "#F5F5F2", { "hood", "rap", "street" }, TN)
I("top_hoodie_camo", "Top", "Camo Print Zip Hoodie", 320, "hoodie", { zip = true, camo = 26 }, "camo", "#F4A6C8", "camo", "#B3122E", { "hood", "rap" }, TN)
I("top_hoodie_camo_green", "Top", "Woodland Camo Hoodie", 280, "hoodie", { camo = 26 }, "camo", "#6B7B3A", "camo", "#4B5320", { "hood", "military" }, T)
I("top_hoodie_crew", "Top", "\"CREW\" Hoodie", 200, "hoodie", { text = "CREW" }, F, "#7A1022", F, "#F5F5F2", { "street" })
I("top_crewneck", "Top", "Crewneck Sweatshirt", 120, "sweater", {}, F, "#8C8C8C", F, "#111111", { "street", "business" })
I("top_chunky_knit", "Top", "Chunky Cable Knit", 220, "sweater", { chunky = true }, F, "#E8DCC0", F, "#111111", { "tiktok", "business" }, T)
I("top_vneck_sweater", "Top", "V-Neck Sweater", 180, "sweater", { vneck = true }, F, "#1B2A41", F, "#F5F5F2", { "business" })
I("top_quarter_zip", "Top", "Quarter-Zip Pullover", 220, "sweater", { qzip = true }, F, "#1B2A41", F, "#F5F5F2", { "business", "tiktok" }, T)
I("top_turtleneck", "Top", "Fine Knit Turtleneck", 200, "sweater", { turtle = true }, F, "#111111", F, "#111111", { "business", "heist" })
I("top_dress_shirt", "Top", "Crisp Dress Shirt", 150, "shirt", {}, F, "#F5F5F2", F, "#F5F5F2", { "business" })
I("top_open_collar", "Top", "Open Collar Shirt", 150, "shirt", { open = true }, F, "#F5F5F2", F, "#F5F5F2", { "business", "coast" })
I("top_resort_shirt", "Top", "Resort Bloom Shirt", 180, "shirt", { sleeve = "tee", open = true, print = true }, F, "#0F5257", F, "#F4A6C8", { "coast", "retro" }, T)
I("top_flannel", "Top", "Buttoned Flannel", 140, "shirt", { placket = "dark" }, F, "#B3122E", F, "#111111", { "street", "western" })
I("top_denim_shirt", "Top", "Denim Western Shirt", 160, "shirt", {}, "denim", "#4C6F9E", "denim", "#34507A", { "western" })
I("top_polo", "Top", "Pique Polo", 120, "polo", {}, F, "#1B2A41", F, "#1B2A41", { "business", "coast" })
I("top_jersey_hoop", "Top", "Hoops Jersey", 180, "jersey", { num = "23" }, F, "#B3122E", F, "#F5F5F2", { "sport", "street" }, T)
I("top_jersey_hoop2", "Top", "Hoops Jersey (Away)", 180, "jersey", { num = "0" }, F, "#F5F5F2", F, "#7B3FE4", { "sport", "street" })
I("top_jersey_soccer", "Top", "Football Kit Jersey", 180, "jersey", { num = "10", sleeve = "tee" }, F, "#F6E27A", F, "#2E4A7A", { "sport", "street" }, T)
I("top_jersey_hockey", "Top", "Hockey Sweater", 220, "jersey", { num = "91", sleeve = "long" }, F, "#7A1022", F, "#F5F5F2", { "sport", "tiktok" }, TN)
I("top_crop", "Top", "Baby Tee Crop", 120, "croptop", { sleeve = true }, F, "#F5F5F2", F, "#F4A6C8", { "retro", "cute" })
I("top_bow_crop", "Top", "Bow Baby Tee", 140, "croptop", { bow = true, sleeve = true }, F, "#F4A6C8", F, "#F5F5F2", { "cute", "tiktok" }, T)
I("top_corset", "Top", "Laced Bodice Top", 220, "corset", {}, F, "#F5F5F2", F, "#F4A6C8", { "cute", "tiktok" }, T)
I("top_office_siren", "Top", "Fitted Button-Down", 160, "shirt", {}, F, "#F5F5F2", F, "#F5F5F2", { "business", "tiktok" }, T)
I("top_coveralls", "Top", "Mechanic Coveralls", 200, "jumpsuit", { zip = "c2", patches = true }, F, "#1B2A41", F, "#E8A33D", { "work" })
I("top_jumpsuit_orange", "Top", "County Orange Jumpsuit", 120, "jumpsuit", { text = "INMATE" }, F, "#E8A33D", F, "#111111", { "work", "heist" })
I("top_flight_suit", "Top", "Flight Suit", 260, "jumpsuit", { patches = true }, F, "#6B7B3A", F, "#E8A33D", { "military" })
I("top_scrubs", "Top", "Hospital Scrubs", 120, "jumpsuit", { shortSleeve = true }, F, "#2F7D6D", F, "#2F7D6D", { "work" })
I("top_racing_suit", "Top", "Racing Suit", 300, "jumpsuit", { m = "leather", patches = true }, "bright", "#FF3B30", "bright", "#F5F5F2", { "sport", "heist" })
I("top_spacesuit", "Top", "Orbital Spacesuit", 600, "jumpsuit", { space = true, m = "smooth" }, F, "#F5F5F2", F, "#8C8C8C", { "scifi" })
I("top_spacesuit_red", "Top", "Red Deep-Space Suit", 650, "jumpsuit", { space = true, m = "smooth" }, F, "#B3122E", F, "#D6D6D6", { "scifi" }, TN)
I("top_hero_suit", "Top", "Hero Bodysuit", 450, "jumpsuit", { m = "smooth", zip = "c1" }, "bright", "#00A2FF", "bright", "#FF3B30", { "hero" })
I("top_ninja_gi", "Top", "Shadow Gi", 300, "robe", { len = 0.8, belt = true }, F, "#111111", F, "#B3122E", { "fantasy" })
I("top_wizard_robe", "Top", "Starry Wizard Robe", 400, "robe", { len = 2.6, belt = true, hood = true }, F, "#4A2B6B", F, "#F6E27A", { "fantasy" })
I("top_vampire", "Top", "Noble's Long Coat", 400, "robe", { len = 2.2 }, F, "#111111", F, "#7A1022", { "spooky", "fantasy" })
I("top_bronze_armor", "Top", "Bronze Warrior Cuirass", 600, "armor", { skirt = true }, "metal", "#E2B240", F, "#7A1022", { "fantasy" }, TN)
I("top_knight_armor", "Top", "Knight's Plate", 650, "armor", {}, "metal", "#D4D6DC", F, "#2E4A7A", { "fantasy" })
I("top_trooper_armor", "Top", "Orbital Trooper Armor", 700, "armor", { scifi = true }, F, "#F5F5F2", F, "#2B2B2B", { "scifi" })
I("top_sequin_dress", "Top", "Red Sequin Party Dress", 450, "dress", { len = 1.2, sequin = true, sleeve = true }, F, "#B3122E", F, "#B3122E", { "retro", "business" })
I("top_slip_dress", "Top", "Satin Midi Dress", 300, "dress", { len = 1.6, sleeve = true }, F, "#E8DCC0", F, "#E8DCC0", { "tiktok", "cute" })
I("top_animal_top", "Top", "Red & Black Animal Stripe Top", 220, "tee", { sleeve = "long", stripe = true }, F, "#B3122E", F, "#111111", { "tiktok", "spooky" }, TN)

------------------------------------------------------------------ outerwear
I("out_puffer", "Outer", "Cropped Puffer", 350, "jacket", { puffer = true, open = false, collar = "stand", zip = true }, F, "#111111", F, "#111111", { "hood", "street" }, T)
I("out_puffer_shine", "Outer", "Glossy Puffer", 420, "jacket", { puffer = true, open = false, collar = "stand", zip = true }, F, "#B3122E", F, "#B3122E", { "hood", "rap" }, T)
I("out_puffer_vest", "Outer", "Puffer Vest", 260, "jacket", { puffer = true, open = false, vest = true, collar = "stand" }, F, "#111111", F, "#111111", { "street", "business" })
I("out_leather_moto", "Outer", "Leather Moto Jacket", 450, "jacket", { m = "leather", zip = "diag", collar = "lapel", open = false }, "leather", "#111111", F, "#111111", { "street", "retro" }, T)
I("out_red_moto", "Outer", "80s Red Leather Jacket", 450, "jacket", { m = "leather", zip = true, collar = "stand", open = false }, "leather", "#7A1022", F, "#111111", { "retro" })
I("out_bomber", "Outer", "Satin Bomber", 280, "jacket", { m = "smooth", zip = true, collar = "rib", cuffs = true }, F, "#4B5320", F, "#E8A33D", { "street", "military" })
I("out_denim", "Outer", "Classic Denim Jacket", 260, "jacket", { collar = "lapel", collarC = "c1", pockets = true }, "denim", "#4C6F9E", "denim", "#34507A", { "street", "western" })
I("out_denim_vest", "Outer", "Denim Vest", 180, "jacket", { collar = "lapel", collarC = "c1", pockets = true, vest = true }, "denim", "#26354D", "denim", "#26354D", { "western", "retro" })
I("out_varsity", "Outer", "Varsity Letterman", 380, "jacket", { collar = "rib", cuffs = true, sleeveC = "c2", sleeveM = "leather", letter = "N" }, F, "#1B2A41", "leather", "#F5F5F2", { "street", "sport", "tiktok" }, T)
I("out_track", "Outer", "Track Jacket", 220, "jacket", { zip = true, open = false, collar = "stand", stripes = true, m = "smooth" }, F, "#111111", F, "#F5F5F2", { "street", "retro", "sport" })
I("out_racing", "Outer", "Motorsport Jacket", 360, "jacket", { zip = true, open = false, collar = "stand", stripes = true, m = "leather" }, "bright", "#FF3B30", "bright", "#F5F5F2", { "street", "sport" }, T)
I("out_windbreaker", "Outer", "Color-Block Windbreaker", 220, "jacket", { zip = true, open = false, collar = "hood", m = "smooth" }, F, "#2E4A7A", F, "#E8A33D", { "street", "retro" })
I("out_gorp_shell", "Outer", "Trail Shell Jacket", 300, "jacket", { zip = true, open = false, collar = "hood", m = "smooth", pockets = true }, F, "#2F7D6D", F, "#111111", { "tiktok", "street" }, T)
I("out_fleece", "Outer", "Sherpa Fleece", 240, "jacket", { zip = true, collar = "stand", pockets = true }, F, "#E8DCC0", F, "#5C3A21", { "tiktok", "coast" })
I("out_funnel", "Outer", "Funnel-Neck Jacket", 320, "jacket", { zip = true, open = false, collar = "funnel" }, F, "#111111", F, "#111111", { "tiktok", "street" }, TN)
I("out_field_waxed", "Outer", "Waxed Field Jacket", 380, "jacket", { collar = "lapel", collarC = "c2", pockets = true, m = "smooth" }, F, "#4B5320", "leather", "#5C3A21", { "tiktok", "business" }, TN)
I("out_suede", "Outer", "Suede Shirt Jacket", 360, "jacket", { collar = "lapel", collarC = "c1", pockets = true, m = "leather" }, "leather", "#8B5A2B", F, "#111111", { "tiktok", "western" }, T)
I("out_work_jacket", "Outer", "Duck Canvas Work Jacket", 300, "jacket", { collar = "lapel", collarC = "c2", pockets = true }, F, "#C68E5A", "leather", "#4A2C1A", { "hood", "work", "street" }, T)
I("out_flannel_open", "Outer", "Open Flannel Overshirt", 160, "jacket", { collar = "lapel", collarC = "c1" }, F, "#B3122E", F, "#111111", { "street", "retro" })
I("out_camo_field", "Outer", "Field Jacket", 280, "jacket", { collar = "lapel", collarC = "c1", pockets = true, camo = 20 }, "camo", "#6B7B3A", "camo", "#4B5320", { "military" })
I("out_officer", "Outer", "Brass-Button Officer Jacket", 420, "jacket", { open = false, collar = "stand", epaulettes = true }, F, "#1B2A41", F, "#E2B240", { "tiktok", "military" }, TN)
I("out_fur", "Outer", "Faux Fur Statement Coat", 600, "jacket", { fur = true, collar = "fur", collarC = "c1", long = 1.3 }, F, "#3B2A1F", F, "#3B2A1F", { "tiktok", "rap", "business" }, T)
I("out_trench", "Outer", "Belted Trench Coat", 420, "jacket", { collar = "lapel", long = 1.4, belted = true, m = "smooth" }, F, "#C8B88A", F, "#8B5A2B", { "business", "heist" })
I("out_overcoat", "Outer", "Long Wool Overcoat", 450, "jacket", { collar = "lapel", long = 1.5 }, F, "#2B2B2B", F, "#111111", { "business" })
I("out_blazer", "Outer", "Two-Button Suit Jacket", 400, "blazer", {}, F, "#1B2A41", F, "#F5F5F2", { "business" })
I("out_blazer_charcoal", "Outer", "Charcoal Suit Jacket", 400, "blazer", {}, F, "#2B2B2B", F, "#F5F5F2", { "business", "heist" })
I("out_tux", "Outer", "Satin Lapel Tuxedo", 550, "blazer", { satin = true }, F, "#111111", F, "#111111", { "business", "heist" })
I("out_double", "Outer", "Double-Breasted Power Blazer", 520, "blazer", { double = true, brass = true }, F, "#F5F5F2", F, "#E2B240", { "business", "tiktok" }, T)
I("out_pastel_suit", "Outer", "Pastel Linen Suit Jacket", 450, "blazer", {}, F, "#F4A6C8", F, "#9CC3E6", { "retro", "coast" }, T)
I("out_waistcoat", "Outer", "Suit Waistcoat", 250, "vest", { suit = true }, F, "#2B2B2B", "metal", "#D4D6DC", { "business", "retro" })
I("out_plate_carrier", "Outer", "Plate Carrier", 380, "vest", {}, F, "#4B5320", F, "#111111", { "military" })
I("out_tactical_black", "Outer", "Black Tactical Vest", 380, "vest", {}, F, "#111111", F, "#F5F5F2", { "military", "heist" })
I("out_agent_vest", "Outer", "\"AGENT\" Raid Vest", 400, "vest", { text = "AGENT" }, F, "#1B2A41", F, "#F6E27A", { "work", "military" }, N)
I("out_agent_jacket", "Outer", "Field Agent Windbreaker", 320, "jacket", { zip = true, open = false, collar = "stand", m = "smooth", back = "AGENT" }, F, "#1B2A41", F, "#F6E27A", { "work", "spooky" }, TN)
I("out_security", "Outer", "Security Bomber", 280, "jacket", { zip = true, open = false, collar = "rib", back = "SECURITY", m = "smooth" }, F, "#111111", F, "#F6E27A", { "work" })
I("out_lab_coat", "Outer", "Lab Coat", 220, "labcoat", {}, F, "#F5F5F2", F, "#F5F5F2", { "work" })
I("out_chef", "Outer", "Chef Jacket", 200, "jacket", { open = false, collar = "stand", collarC = "c1", zip = false }, F, "#F5F5F2", F, "#111111", { "work" })
I("out_lifeguard", "Outer", "Lifeguard Hoodie", 200, "jacket", { open = false, collar = "hood", back = "GUARD" }, F, "#B3122E", F, "#F5F5F2", { "coast", "work" })
I("out_cyber", "Outer", "Neon Runner Jacket", 520, "jacket", { zip = "diag", open = false, collar = "stand", neon = true, m = "leather" }, "leather", "#111111", "neon", "#00FFDC", { "scifi" }, T)
I("out_pirate", "Outer", "Captain's Frock Coat", 450, "jacket", { collar = "lapel", long = 1.4, cuffs = true, cuffC = "gold" }, F, "#7A1022", "metal", "#E2B240", { "fantasy" })
I("out_zoot", "Outer", "Zoot Suit Drape Coat", 520, "jacket", { collar = "lapel", long = 1.7, collarC = "c1" }, F, "#C8963E", F, "#111111", { "lowrider", "retro", "business" }, TN)
I("out_suspenders", "Outer", "Suspenders", 80, "suspenders", {}, F, "#111111", "metal", "#D4D6DC", { "lowrider", "retro", "work" })
I("out_cowboy_vest", "Outer", "Cattleman Vest", 220, "vest", { suit = true }, "leather", "#6B3E22", "metal", "#C8963E", { "western" })

------------------------------------------------------------------ bottoms
local D = "denim"
I("bot_jeans", "Bottom", "Straight Jeans", 0, "pants", {}, D, "#34507A", nil, nil, { "street" })
I("bot_baggy", "Bottom", "Baggy Stacked Jeans", 200, "pants", { stack = true }, D, "#26354D", nil, nil, { "hood", "street", "rap" }, T)
I("bot_baggy_black", "Bottom", "Black Baggy Denim", 200, "pants", { stack = true }, D, "#111418", nil, nil, { "hood", "street" }, T)
I("bot_ripped", "Bottom", "Ripped Knee Jeans", 160, "pants", { rips = true }, D, "#4C6F9E", nil, nil, { "street", "retro" })
I("bot_slim", "Bottom", "Slim Dark Jeans", 120, "pants", {}, D, "#1E2A3A", nil, nil, { "tiktok", "business" }, T)
I("bot_barrel", "Bottom", "Barrel Leg Pants", 240, "pants", { wide = true }, F, "#C8B88A", nil, nil, { "tiktok" }, TN)
I("bot_wide_trouser", "Bottom", "Wide-Leg Trousers", 220, "pants", { wide = true, crease = true }, F, "#2B2B2B", nil, nil, { "business", "tiktok" }, T)
I("bot_cargo", "Bottom", "Cargo Pants", 160, "pants", { cargo = true }, F, "#4B5320", nil, nil, { "street", "military", "tiktok" }, T)
I("bot_cargo_black", "Bottom", "Black Tactical Cargos", 180, "pants", { cargo = true }, F, "#111111", nil, nil, { "military", "heist", "hood" })
I("bot_camo_cargo", "Bottom", "Desert Field Pants", 180, "pants", { cargo = true }, "camo", "#C8B88A", nil, nil, { "military" })
I("bot_joggers", "Bottom", "Fleece Joggers", 100, "pants", { cuff = true }, F, "#8C8C8C", nil, nil, { "street", "sport", "hood" })
I("bot_track", "Bottom", "Track Pants", 140, "pants", { stripe = true }, F, "#111111", F, "#F5F5F2", { "street", "retro", "sport" })
I("bot_trousers", "Bottom", "Pressed Suit Trousers", 200, "pants", { crease = true }, F, "#1B2A41", nil, nil, { "business" })
I("bot_chinos", "Bottom", "Chinos", 120, "pants", {}, F, "#C8B88A", nil, nil, { "business", "coast" })
I("bot_khakis", "Bottom", "Creased Khakis", 120, "pants", { crease = true }, F, "#C8B88A", nil, nil, { "street", "retro", "lowrider" }, T)
I("bot_work_creased", "Bottom", "Pressed Work Pants", 120, "pants", { crease = true, wide = true }, F, "#1B2A41", nil, nil, { "lowrider", "work" }, T)
I("bot_zoot", "Bottom", "High-Waist Zoot Trousers", 260, "pants", { crease = true, wide = true }, F, "#C8963E", nil, nil, { "lowrider", "retro" })
I("bot_shorts_socks", "Bottom", "Long Shorts & Knee Socks", 120, "shorts", { long = true, socks = true }, F, "#C8B88A", F, "#F5F5F2", { "lowrider" }, T)
I("bot_leather", "Bottom", "Leather Pants", 280, "pants", { m = "leather" }, "leather", "#111111", nil, nil, { "retro", "rap" })
I("bot_shorts_hoop", "Bottom", "Long Mesh Hoop Shorts", 100, "shorts", { long = true, stripe = true }, F, "#B3122E", F, "#F5F5F2", { "sport", "street" })
I("bot_jorts", "Bottom", "Baggy Jorts", 140, "shorts", { long = true }, D, "#4C6F9E", nil, nil, { "street", "tiktok" }, T)
I("bot_chino_shorts", "Bottom", "Chino Shorts", 80, "shorts", {}, F, "#C8B88A", nil, nil, { "coast" })
I("bot_swim", "Bottom", "Swim Trunks", 60, "shorts", {}, "bright", "#00A2FF", nil, nil, { "coast" })
I("bot_board", "Bottom", "Board Shorts", 80, "shorts", { long = true, stripe = true }, "bright", "#FF8A00", "bright", "#F5F5F2", { "coast" })
I("bot_gym_shorts", "Bottom", "Gym Shorts", 60, "shorts", { stripe = true }, F, "#111111", F, "#F5F5F2", { "sport" })
I("bot_pleated_skirt", "Bottom", "Pleated Tennis Skirt", 160, "skirt", { len = 0.85, pleats = true }, F, "#F5F5F2", nil, nil, { "cute", "sport", "tiktok" }, T)
I("bot_mini_skirt", "Bottom", "A-Line Skirt", 140, "skirt", { len = 0.9 }, F, "#111111", nil, nil, { "retro", "cute" })
I("bot_pencil_skirt", "Bottom", "Pencil Skirt", 180, "skirt", { len = 1.1, flare = 0, tights = true }, F, "#2B2B2B", F, "#111111", { "business", "tiktok" }, T)
I("bot_maxi_skirt", "Bottom", "Flowing Maxi Skirt", 180, "skirt", { len = 1.9, flare = 6 }, F, "#5C3A21", nil, nil, { "tiktok", "fantasy" })
I("bot_leggings", "Bottom", "Sculpt Leggings", 100, "leggings", {}, F, "#111111", nil, nil, { "sport", "tiktok" })
I("bot_overalls", "Bottom", "Denim Overalls", 180, "overalls", {}, D, "#4C6F9E", nil, nil, { "retro", "work", "cute" })

------------------------------------------------------------------ shoes
local S = "sole"
I("shoe_white_low", "Shoes", "Clean White Low-Tops", 0, "shoes", { panel = true, laces = true }, F, "#F5F5F2", S, "#F5F5F2", { "street" }, T)
I("shoe_black_low", "Shoes", "Triple Black Low-Tops", 0, "shoes", { panel = true }, F, "#111111", S, "#111111", { "street", "hood" })
I("shoe_chunky", "Shoes", "Chunky Retro Runners", 260, "shoes", { sole = 0.32, panel = true, laces = true }, F, "#D6D6D6", S, "#F5F5F2", { "street", "tiktok" }, T)
I("shoe_slim_runner", "Shoes", "Slim Retro Runners", 220, "shoes", { sole = 0.18, panel = true, gum = true }, F, "#2E4A7A", F, "#F5F5F2", { "tiktok", "street" }, TN)
I("shoe_hightop", "Shoes", "Hoops High-Tops", 280, "shoes", { high = true, panel = true, laces = true }, F, "#B3122E", S, "#F5F5F2", { "sport", "street", "hood" }, T)
I("shoe_hightop_bw", "Shoes", "Black & White High-Tops", 280, "shoes", { high = true, panel = true }, F, "#111111", S, "#F5F5F2", { "street", "hood" })
I("shoe_classic", "Shoes", "Classic Leather Runners", 160, "shoes", { sole = 0.16, panel = true, laces = true, soleC = "sole" }, F, "#F5F5F2", "bright", "#FF3B30", { "lowrider", "street", "retro" }, T)
I("shoe_two_tone", "Shoes", "Two-Tone Dress Shoes", 260, "shoes", { m = "leather", sole = 0.1, panel = true }, "leather", "#F5F5F2", "leather", "#111111", { "lowrider", "retro" })
I("shoe_skate", "Shoes", "Suede Skate Shoes", 160, "shoes", { sole = 0.2, panel = true, gum = true }, F, "#111111", F, "#F5F5F2", { "street", "retro" })
I("shoe_runner", "Shoes", "Mesh Running Shoes", 180, "shoes", { sole = 0.24, panel = true }, "bright", "#00A2FF", S, "#F5F5F2", { "sport" })
I("shoe_slides", "Shoes", "Slides & Socks", 80, "shoes", { slides = true }, F, "#111111", F, "#F5F5F2", { "street", "coast", "hood" }, T)
I("shoe_sandals", "Shoes", "Leather Sandals", 80, "shoes", { sandal = true }, "leather", "#6B3E22", nil, nil, { "coast" })
I("shoe_flipflops", "Shoes", "Beach Flip-Flops", 20, "shoes", { sandal = true }, "bright", "#00A2FF", nil, nil, { "coast" })
I("shoe_work_boots", "Shoes", "Wheat Work Boots", 300, "shoes", { boot = 0.6, m = "leather", sole = 0.2, gum = true, collarC = "c1" }, "leather", "#C8963E", S, "#C8963E", { "hood", "work", "street" }, T)
I("shoe_combat", "Shoes", "Combat Boots", 280, "shoes", { boot = 0.8, m = "leather", sole = 0.2 }, "leather", "#111111", S, "#111111", { "military", "heist" })
I("shoe_desert_boots", "Shoes", "Desert Tactical Boots", 280, "shoes", { boot = 0.8, m = "leather", sole = 0.2 }, "leather", "#C8963E", S, "#B98A5E", { "military" })
I("shoe_cowboy", "Shoes", "Stitched Cowboy Boots", 320, "shoes", { boot = 1.0, m = "leather", heel = 0.2 }, "leather", "#6B3E22", "leather", "#4A2C1A", { "western" })
I("shoe_oxford", "Shoes", "Polished Oxfords", 220, "shoes", { m = "leather", sole = 0.1 }, "leather", "#111111", "leather", "#111111", { "business" })
I("shoe_loafer", "Shoes", "Suede Loafers", 220, "shoes", { m = "leather", sole = 0.1 }, "leather", "#8B5A2B", "leather", "#4A2C1A", { "business", "tiktok" }, T)
I("shoe_heels", "Shoes", "Classic Heels", 240, "shoes", { m = "leather", heel = 0.35, sole = 0.06 }, "leather", "#111111", "leather", "#111111", { "business", "retro" })
I("shoe_wedges", "Shoes", "Wedge Heels", 240, "shoes", { wedge = true, sole = 0.06 }, F, "#E8DCC0", F, "#C68E5A", { "tiktok", "retro" }, TN)
I("shoe_clogs", "Shoes", "Cozy Clogs", 120, "shoes", { sole = 0.3, m = "rubber" }, F, "#8C8C8C", F, "#8C8C8C", { "tiktok", "work" })
I("shoe_platform", "Shoes", "Platform Sneakers", 220, "shoes", { sole = 0.45, laces = true }, F, "#F5F5F2", S, "#F5F5F2", { "retro", "cute" })

------------------------------------------------------------------ headwear
I("hat_fitted", "Head", "Flat-Brim Fitted Cap", 120, "cap", { flat = true }, F, "#111111", F, "#111111", { "hood", "street", "rap" }, T)
I("hat_fitted_back", "Head", "Fitted Cap (Backwards)", 120, "cap", { flat = true, back = true }, F, "#111111", F, "#111111", { "hood", "street" })
I("hat_dad", "Head", "Washed Dad Cap", 80, "cap", {}, F, "#C8B88A", F, "#C8B88A", { "street", "coast" })
I("hat_trucker", "Head", "Mesh Trucker Cap", 100, "cap", { trucker = true }, F, "#1B2A41", F, "#1B2A41", { "street", "western", "coast" })
I("hat_crew_cap", "Head", "\"NC\" Snapback", 140, "cap", { flat = true, txt = "NC" }, F, "#00A2FF", "neon", "#FF2BD6", { "coast", "street" })
I("hat_beanie", "Head", "Ribbed Beanie", 80, "beanie", {}, F, "#111111", F, "#111111", { "hood", "street", "heist" }, T)
I("hat_fisherman", "Head", "Fisherman Beanie", 100, "beanie", { short = true }, F, "#B3122E", F, "#B3122E", { "tiktok", "street" }, T)
I("hat_pom", "Head", "Pom Beanie", 100, "beanie", { pom = true }, F, "#2E4A7A", F, "#F5F5F2", { "cute" })
I("hat_work_beanie", "Head", "Watch Cap Beanie", 90, "beanie", { short = true }, F, "#C68E5A", F, "#C68E5A", { "hood", "work" }, T)
I("hat_bucket", "Head", "Bucket Hat", 120, "bucket", {}, F, "#111111", F, "#111111", { "street", "retro", "coast" })
I("hat_durag", "Head", "Silky Durag", 120, "durag", { hideHairTop = true }, F, "#111111", F, "#111111", { "hood", "rap" }, T)
I("hat_durag_velvet", "Head", "Velvet Durag", 150, "durag", { velvet = true }, F, "#7A1022", F, "#7A1022", { "hood", "rap" }, T)
I("hat_head_bandana", "Head", "Bandana Head Wrap", 80, "headwrap", {}, F, "#B3122E", F, "#F5F5F2", { "hood", "western", "street" })
I("hat_folded_bandana", "Head", "Folded Bandana Headband", 80, "foldedband", {}, F, "#111111", nil, nil, { "lowrider", "hood" }, T)
I("hat_hairnet", "Head", "Hairnet", 30, "hairnet", { noFlatten = true }, F, "#111111", nil, nil, { "lowrider", "work" })
I("hat_headband", "Head", "Sweatband", 40, "headband", { noFlatten = true }, F, "#F5F5F2", nil, nil, { "sport", "retro" })
I("hat_fedora", "Head", "Classic Fedora", 220, "fedora", {}, F, "#2B2B2B", F, "#111111", { "business", "retro", "heist" })
I("hat_wide_fedora", "Head", "Wide-Brim Felt Hat", 240, "fedora", { wide = true }, F, "#5C3A21", F, "#111111", { "western", "tiktok" })
I("hat_cowboy", "Head", "Cattleman Cowboy Hat", 260, "cowboy", {}, "leather", "#B98A5E", "leather", "#4A2C1A", { "western", "tiktok" }, T)
I("hat_beret", "Head", "Wool Beret", 120, "beret", {}, F, "#111111", nil, nil, { "military", "retro" })
I("hat_combat_helmet", "Head", "Combat Helmet", 300, "helmet", { strap = true }, F, "#6B7B3A", nil, nil, { "military" })
I("hat_nvg_helmet", "Head", "Night Ops Helmet", 450, "helmet", { strap = true, nvg = true }, F, "#2B2B2B", nil, nil, { "military", "heist" })
I("hat_hardhat", "Head", "Hard Hat", 80, "hardhat", {}, "bright", "#FFE600", nil, nil, { "work" })
I("hat_tophat", "Head", "Top Hat", 260, "tophat", {}, F, "#111111", F, "#7A1022", { "business", "spooky", "retro" })
I("hat_crown", "Head", "Gold Crown", 900, "crown", {}, "metal", "#E2B240", "gem", "#FF3B30", { "rap", "fantasy" })
I("hat_iced_crown", "Head", "Iced Out Crown", 1500, "crown", { iced = true }, "metal", "#D4D6DC", "gem", "#ECF6FF", { "rap" })
I("hat_halo", "Head", "Neon Halo", 400, "halo", { noFlatten = true }, "neon", "#FFE600", nil, nil, { "cute", "hero" })
I("hat_headphones", "Head", "Studio Headphones", 220, "headphones", { noFlatten = true }, F, "#111111", F, "#2B2B2B", { "street", "tiktok" })
I("hat_gamer_headset", "Head", "RGB Gamer Headset", 260, "headphones", { rgb = true, noFlatten = true }, F, "#111111", "neon", "#00FFDC", { "tiktok", "scifi" }, T)
I("hat_tiara", "Head", "Crystal Tiara", 400, "tiara", { iced = true, noFlatten = true }, "metal", "#D4D6DC", "gem", "#ECF6FF", { "cute" })
I("hat_visor", "Head", "Sun Visor", 60, "visor", { noFlatten = true }, F, "#F5F5F2", F, "#F5F5F2", { "coast", "sport" })
I("hat_cat_ears", "Head", "Cat Ear Headband", 120, "ears", { noFlatten = true }, F, "#111111", nil, nil, { "cute" }, T)
I("hat_bunny_ears", "Head", "Bunny Ear Headband", 120, "ears", { bunny = true, noFlatten = true }, F, "#F5F5F2", nil, nil, { "cute" })
I("hat_horns", "Head", "Devil Horns", 160, "horns", { noFlatten = true }, "bright", "#FF3B30", nil, nil, { "spooky" })
I("hat_wizard", "Head", "Wizard's Pointed Hat", 260, "wizard", {}, F, "#4A2B6B", F, "#F6E27A", { "fantasy" })
I("hat_tricorn", "Head", "Captain's Tricorn", 260, "tricorn", {}, F, "#111111", "metal", "#E2B240", { "fantasy" })
I("hat_chef", "Head", "Chef's Toque", 60, "chef", {}, F, "#F5F5F2", nil, nil, { "work" })
I("hat_space_helmet", "Head", "Glass Space Helmet", 500, "spacehelmet", { noFlatten = true }, F, "#F5F5F2", "lens", "#9CC3E6", { "scifi" })
I("hat_knight_helm", "Head", "Knight's Great Helm", 450, "knighthelm", { hideHair = true, hideBeard = true }, "metal", "#D4D6DC", nil, nil, { "fantasy" })
I("hat_hood", "Head", "Up Hood", 100, "hood", {}, F, "#111111", nil, nil, { "hood", "heist", "street" }, T)
I("hat_unicorn_hood", "Head", "Unicorn Onesie Hood", 300, "hood", { horn = true }, F, "#F5F5F2", "bright", "#F4A6C8", { "cute", "spooky" }, TN)
I("hat_bear_hood", "Head", "Bear Ear Hood", 220, "hood", { ears = true }, F, "#8B5A2B", nil, nil, { "cute" })

------------------------------------------------------------------ eyewear
local L = "lens"
I("eye_shades_black", "Face", "Black Wraparound Shades", 120, "glasses", { shape = "shield", tall = 0.38 }, F, "#111111", L, "#111111", { "hood", "rap", "street" }, T)
I("eye_rect_shades", "Face", "Rectangle Shades", 100, "glasses", { shape = "rect" }, F, "#111111", L, "#111111", { "hood", "rap", "street" }, T)
I("eye_aviator", "Face", "Gold Aviators", 160, "glasses", { shape = "aviator" }, "metal", "#E2B240", L, "#3B2A1F", { "rap", "military", "retro" })
I("eye_aviator_mirror", "Face", "Mirrored Aviators", 180, "glasses", { shape = "aviator" }, "metal", "#D4D6DC", L, "#9CC3E6", { "military", "coast" })
I("eye_round", "Face", "Round Wire Frames", 100, "glasses", { shape = "round", clear = true }, "metal", "#E2B240", L, "#F5F5F2", { "business", "retro" })
I("eye_round_shades", "Face", "Round Tinted Shades", 120, "glasses", { shape = "round" }, "metal", "#E2B240", L, "#7A1022", { "retro", "rap" })
I("eye_specs", "Face", "Thin Office Specs", 80, "glasses", { shape = "rect", tall = 0.24, clear = true }, F, "#111111", L, "#F5F5F2", { "business", "tiktok" }, T)
I("eye_cateye", "Face", "Cat-Eye Sunglasses", 140, "glasses", { shape = "cateye" }, F, "#111111", L, "#111111", { "retro", "tiktok", "cute" })
I("eye_tiny_oval", "Face", "Tiny Y2K Ovals", 120, "glasses", { shape = "oval" }, "metal", "#D4D6DC", L, "#F4A6C8", { "retro", "tiktok" }, T)
I("eye_shield_sport", "Face", "Sport Shield Shades", 160, "glasses", { shape = "shield", tall = 0.32 }, F, "#D6D6D6", L, "#E8A33D", { "sport", "tiktok" }, T)
I("eye_ski_goggles", "Face", "Ski Goggles", 160, "goggles", {}, F, "#111111", L, "#E8A33D", { "heist", "sport" })
I("eye_goggles_up", "Face", "Goggles Pushed Up", 160, "goggles", { up = true }, "leather", "#6B3E22", L, "#9CC3E6", { "scifi", "retro" })
I("eye_vr", "Face", "Full-Dive VR Visor", 500, "vrvisor", {}, F, "#111111", "neon", "#00FFDC", { "scifi", "tiktok" }, TN)
I("eye_patch", "Face", "Eye Patch", 60, "eyepatch", {}, "leather", "#111111", nil, nil, { "fantasy" })
I("eye_monocle", "Face", "Monocle", 120, "monocle", {}, "metal", "#E2B240", L, "#F5F5F2", { "business", "retro" })

------------------------------------------------------------------ masks
I("mask_ski", "Mask", "Classic Ski Mask", 120, "balaclava", { hideHair = true }, F, "#111111", F, "#111111", { "heist", "hood" }, T)
I("mask_ski_open", "Mask", "Open-Face Ski Mask", 140, "balaclava", { hideHair = true, open = true, hideBeard = true }, F, "#111111", F, "#111111", { "hood", "heist" }, T)
I("mask_ski_pom", "Mask", "Pom Ski Mask", 140, "balaclava", { hideHair = true, pom = true }, F, "#B3122E", F, "#F5F5F2", { "heist", "cute" })
I("mask_loose_bandana", "Mask", "Loose Bandana", 0, "loosebandana", { assetId = nil }, F, "#B3122E", F, "#F5F5F2", { "hood", "street", "western" }, T)
I("mask_loose_bandana_low", "Mask", "Loose Bandana (Low Drape)", 0, "loosebandana", { low = true }, F, "#2E4A7A", F, "#F5F5F2", { "hood", "street" })
I("mask_bandana_face", "Mask", "Outlaw Bandana (Over Nose)", 80, "bandanaface", { hideBeard = true }, F, "#111111", F, "#F5F5F2", { "heist", "western", "hood" }, T)
I("mask_face", "Mask", "Cloth Face Mask", 40, "facemask", { hideBeard = true }, F, "#111111", nil, nil, { "street", "work" })
I("mask_gas", "Mask", "Gas Mask", 260, "gasmask", { hideBeard = true }, F, "#2B2B2B", L, "#2A2F38", { "military", "scifi" })
I("mask_goalie", "Mask", "Vintage Goalie Mask", 200, "goalie", { hideBeard = true }, F, "#F5F5F2", "bright", "#FF3B30", { "spooky", "sport", "heist" })
I("mask_clown", "Mask", "Heist Clown Mask", 260, "clown", { hideBeard = true }, "bright", "#00A2FF", "bright", "#00A2FF", { "heist", "spooky" })
I("mask_skull", "Mask", "Half Skull Mask", 180, "skullmask", { hideBeard = true }, F, "#111111", nil, nil, { "spooky", "military" })
I("mask_ninja", "Mask", "Ninja Wrap", 160, "ninjamask", { hideHair = true, hideBeard = true }, F, "#111111", F, "#B3122E", { "fantasy", "heist" })
I("mask_masquerade", "Mask", "Masquerade Mask", 200, "masquerade", {}, "metal", "#E2B240", "bright", "#7B3FE4", { "spooky", "business" })
I("mask_fox", "Mask", "Fox Spirit Mask", 240, "foxmask", { hideBeard = true }, F, "#F5F5F2", "bright", "#FF3B30", { "fantasy", "spooky" })
I("mask_cyber", "Mask", "Neon Respirator", 300, "respirator", { hideBeard = true }, F, "#111111", "neon", "#00FFDC", { "scifi" }, T)

------------------------------------------------------------------ chains (two neck slots so they layer)
local M, G = "metal", "gem"
local function chain(id, name, price, pp, def1, def2, cols, tags)
	I(id, "Neck", name, price, "chain", pp, M, def1, G, def2, cols, tags)
	I(id .. "_2", "Neck2", name, price, "chain", pp, M, def1, G, def2, cols, tags)
end
chain("chain_cuban_gold", "Gold Cuban Link Chain", 400, { style = "cuban", drop = 0.55, w = 0.07 }, "#E2B240", "#ECF6FF", { "rap", "hood", "street" }, T)
chain("chain_cuban_iced", "Iced Cuban Link Chain", 1200, { style = "cuban", drop = 0.55, w = 0.08, iced = true }, "#D4D6DC", "#ECF6FF", { "rap", "hood" }, T)
chain("chain_cuban_thick", "Thick Iced Cuban Choker", 1600, { style = "cuban", drop = 0.35, w = 0.11, iced = true }, "#E2B240", "#ECF6FF", { "rap", "hood" }, T)
chain("chain_cuban_pink", "Pink Diamond Cuban", 1800, { style = "cuban", drop = 0.5, w = 0.08, iced = true }, "#DE9680", "#FF5C8A", { "rap", "cute" }, N)
chain("chain_rope_gold", "Gold Rope Chain", 350, { style = "rope", drop = 0.7, w = 0.045 }, "#E2B240", "#ECF6FF", { "rap", "retro" })
chain("chain_dookie", "80s Dookie Rope Chain", 900, { style = "rope", drop = 0.9, w = 0.1 }, "#E2B240", "#ECF6FF", { "rap", "retro" }, T)
chain("chain_tennis", "Diamond Tennis Chain", 1000, { style = "tennis", drop = 0.5, w = 0.05, iced = true }, "#D4D6DC", "#ECF6FF", { "rap", "business" }, T)
chain("chain_box", "Box Link Chain", 250, { style = "box", drop = 0.6, w = 0.04 }, "#D4D6DC", "#ECF6FF", { "street" })
chain("chain_figaro", "Figaro Chain", 300, { style = "figaro", drop = 0.6, w = 0.05 }, "#E2B240", "#ECF6FF", { "street", "retro" })
chain("chain_cross", "Iced Cross Pendant Chain", 1100, { style = "rope", drop = 0.85, w = 0.035, pendant = "cross", iced = true }, "#E2B240", "#ECF6FF", { "rap", "hood" }, T)
chain("chain_cross_gold", "Gold Cross Chain", 400, { style = "box", drop = 0.75, w = 0.03, pendant = "cross" }, "#E2B240", "#ECF6FF", { "street", "rap" })
chain("chain_medallion", "Gold Medallion Chain", 700, { style = "rope", drop = 0.9, w = 0.05, pendant = "medallion" }, "#E2B240", "#FF3B30", { "rap", "retro" })
chain("chain_iced_piece", "Iced Out Square Piece", 2200, { style = "cuban", drop = 0.85, w = 0.07, pendant = "piece", iced = true }, "#E2B240", "#ECF6FF", { "rap", "hood" }, TN)
chain("chain_letter", "Iced Initial Pendant", 2000, { style = "tennis", drop = 0.85, w = 0.05, pendant = "letter", letter = "N", iced = true }, "#E2B240", "#ECF6FF", { "rap", "hood" }, TN)
chain("chain_crown", "Crown Pendant Chain", 900, { style = "cuban", drop = 0.8, w = 0.05, pendant = "crown" }, "#E2B240", "#ECF6FF", { "rap" })
chain("chain_money", "Money Bag Pendant", 800, { style = "rope", drop = 0.85, w = 0.05, pendant = "money" }, "#E2B240", "#ECF6FF", { "rap", "heist" })
chain("chain_lock", "Padlock Chain", 500, { style = "box", drop = 0.5, w = 0.04, pendant = "lock" }, "#D4D6DC", "#ECF6FF", { "tiktok", "street" }, T)
chain("chain_heart", "Iced Heart Pendant", 900, { style = "tennis", drop = 0.6, w = 0.04, pendant = "heart", iced = true }, "#DE9680", "#FF5C8A", { "cute", "rap" })
chain("chain_bolt", "Lightning Bolt Pendant", 600, { style = "cuban", drop = 0.75, w = 0.05, pendant = "bolt" }, "#E2B240", "#FFD24A", { "street", "hero" })
chain("chain_palm", "Palm Tree Pendant", 500, { style = "rope", drop = 0.8, w = 0.035, pendant = "palm" }, "#E2B240", "#7CFF9B", { "coast" })
chain("chain_diamond", "Solitaire Diamond Pendant", 900, { style = "box", drop = 0.5, w = 0.025, pendant = "diamond" }, "#D4D6DC", "#ECF6FF", { "business", "cute" })
chain("chain_layered", "Layered Gold Chains", 800, { style = "rope", drop = 0.85, w = 0.04, layer = "cuban" }, "#E2B240", "#ECF6FF", { "rap", "street" }, T)
chain("chain_rosary", "Rosary Beads", 300, { style = "bead", drop = 0.9, w = 0.05, pendant = "cross" }, "#2A2A2A", "#ECF6FF", { "lowrider" }, T)
chain("chain_rosary_gold", "Gold Rosary", 650, { style = "bead", drop = 0.9, w = 0.05, pendant = "cross" }, "#E2B240", "#ECF6FF", { "lowrider", "rap" })
chain("chain_dogtags", "Dog Tags", 120, { style = "bead", drop = 0.75, w = 0.025, pendant = "dogtags" }, "#D4D6DC", "#ECF6FF", { "military" })
chain("chain_pearls", "Pearl Strand", 600, { style = "pearl", drop = 0.4, w = 0.07 }, "#F0EAE0", "#ECF6FF", { "tiktok", "rap", "business" }, T)
chain("chain_puka", "Puka Shell Necklace", 120, { style = "puka", drop = 0.35, w = 0.06 }, "#F5F5F2", "#B98A5E", { "coast", "retro" })
I("neck_tie", "Neck", "Silk Necktie", 100, "tie", {}, F, "#7A1022", nil, nil, { "business" })
I("neck_tie_black", "Neck", "Skinny Black Tie", 100, "tie", {}, F, "#111111", nil, nil, { "business", "heist" })
I("neck_bowtie", "Neck", "Bow Tie", 100, "tie", { bow = true }, F, "#111111", nil, nil, { "business", "retro" })
I("neck_scarf", "Neck", "Wool Scarf", 120, "scarf", {}, F, "#B3122E", F, "#111111", { "business", "tiktok" })
I("neck_choker", "Neck", "Velvet Choker", 80, "choker", {}, F, "#111111", nil, nil, { "cute", "retro" })
I("neck_stud_choker", "Neck", "Studded Choker", 120, "choker", { studs = true }, M, "#D4D6DC", nil, nil, { "retro", "spooky" })

------------------------------------------------------------------ grillz
I("grill_gold_top", "Grillz", "Gold Top Six", 600, "grillz", { top = 6 }, M, "#E2B240", G, "#ECF6FF", { "rap", "hood" }, T)
I("grill_gold_full", "Grillz", "Full Gold Set (Top & Bottom)", 1000, "grillz", { top = 8, bottom = 8 }, M, "#E2B240", G, "#ECF6FF", { "rap", "hood" }, T)
I("grill_iced_top", "Grillz", "Iced Out Top Six", 1400, "grillz", { top = 6, iced = true }, M, "#D4D6DC", G, "#ECF6FF", { "rap", "hood" }, T)
I("grill_iced_full", "Grillz", "Iced Out Full Set", 2400, "grillz", { top = 8, bottom = 8, iced = true }, M, "#D4D6DC", G, "#ECF6FF", { "rap" }, T)
I("grill_rose", "Grillz", "Rose Gold Bottom Eight", 900, "grillz", { top = 0, bottom = 8 }, M, "#DE9680", G, "#FF5C8A", { "rap", "cute" })
I("grill_platinum", "Grillz", "Platinum Set", 1200, "grillz", { top = 8, bottom = 6 }, M, "#F2F2F2", G, "#ECF6FF", { "rap" })
I("grill_fangs", "Grillz", "Gold Fangs", 700, "grillz", { top = 6, fang = true }, M, "#E2B240", G, "#ECF6FF", { "rap", "spooky" })
I("grill_gap", "Grillz", "Gold Frame Gap Set", 700, "grillz", { top = 6, gap = true }, M, "#E2B240", G, "#ECF6FF", { "rap", "retro" })
I("grill_rainbow", "Grillz", "Rainbow Gem Set", 1600, "grillz", { top = 8, iced = true }, M, "#E2B240", G, "#B88CFF", { "rap", "cute" }, N)

------------------------------------------------------------------ earrings
I("ear_studs", "Ears", "Diamond Studs", 300, "earrings", { kind = "stud" }, M, "#D4D6DC", G, "#ECF6FF", { "rap", "street", "hood" }, T)
I("ear_big_studs", "Ears", "Big Iced Studs", 600, "earrings", { kind = "stud", size = 0.2 }, M, "#D4D6DC", G, "#ECF6FF", { "rap", "hood" }, T)
I("ear_one_stud", "Ears", "Single Stud", 150, "earrings", { kind = "stud", one = true }, M, "#D4D6DC", G, "#ECF6FF", { "street" })
I("ear_hoops", "Ears", "Gold Hoops", 200, "earrings", { kind = "hoop" }, M, "#E2B240", G, "#ECF6FF", { "street", "cute", "retro" })
I("ear_big_hoops", "Ears", "Statement Hoops", 260, "earrings", { kind = "hoop", size = 0.34 }, M, "#E2B240", G, "#ECF6FF", { "retro", "tiktok" }, T)
I("ear_cross", "Ears", "Cross Dangles", 200, "earrings", { kind = "cross" }, M, "#D4D6DC", G, "#ECF6FF", { "street", "spooky" })
I("ear_pearls", "Ears", "Pearl Drops", 220, "earrings", { kind = "pearl" }, M, "#E2B240", G, "#ECF6FF", { "business", "cute" })
I("ear_dangle", "Ears", "Gem Dangles", 260, "earrings", { kind = "dangle" }, M, "#E2B240", G, "#FF5C8A", { "cute", "business" })

------------------------------------------------------------------ wrist
I("watch_gold", "Wrist", "Gold Presidential Watch", 800, "watch", {}, M, "#E2B240", G, "#ECF6FF", { "rap", "business" }, T)
I("watch_iced", "Wrist", "Fully Iced Watch", 2000, "watch", { iced = true }, M, "#D4D6DC", G, "#ECF6FF", { "rap", "hood" }, T)
I("watch_steel", "Wrist", "Steel Diver Watch", 400, "watch", {}, M, "#D4D6DC", G, "#ECF6FF", { "business", "military" })
I("watch_smart", "Wrist", "Smart Watch", 300, "watch", { smart = true }, F, "#111111", "neon", "#00A2FF", { "sport", "tiktok" })
I("watch_rose", "Wrist", "Rose Gold Watch", 700, "watch", {}, M, "#DE9680", G, "#ECF6FF", { "business", "cute" })
I("brace_cuban", "Wrist2", "Cuban Link Bracelet", 400, "bracelet", {}, M, "#E2B240", G, "#ECF6FF", { "rap", "hood" }, T)
I("brace_iced", "Wrist2", "Iced Tennis Bracelet", 900, "bracelet", { iced = true }, M, "#D4D6DC", G, "#ECF6FF", { "rap" }, T)
I("brace_both", "Wrist2", "Iced Bracelets (Both Wrists)", 1600, "bracelet", { iced = true, both = true }, M, "#E2B240", G, "#ECF6FF", { "rap", "hood" })
I("brace_beads", "Wrist2", "Bead Bracelet", 60, "bracelet", { beads = true }, F, "#111111", nil, nil, { "street", "coast" })
I("brace_pearls", "Wrist2", "Pearl Bracelet", 200, "bracelet", { beads = true }, M, "#F0EAE0", nil, nil, { "cute", "tiktok" })
I("rings_gold", "Rings", "Gold Rings", 300, "rings", { n = 2 }, M, "#E2B240", G, "#ECF6FF", { "rap", "business" })
I("rings_iced", "Rings", "Iced Pinky Rings", 900, "rings", { n = 2, iced = true, both = true }, M, "#D4D6DC", G, "#ECF6FF", { "rap", "hood" }, T)
I("rings_stack", "Rings", "Silver Ring Stack", 250, "rings", { n = 3 }, M, "#D4D6DC", G, "#ECF6FF", { "street", "spooky" })

------------------------------------------------------------------ hands, waist, back
I("glove_black", "Hands", "Black Leather Gloves", 120, "gloves", { leather = true }, "leather", "#111111", nil, nil, { "hood", "heist", "business" }, T)
I("glove_tactical", "Hands", "Tactical Gloves", 140, "gloves", {}, F, "#4B5320", nil, nil, { "military" })
I("glove_driving", "Hands", "Driving Gloves", 160, "gloves", { leather = true }, "leather", "#8B5A2B", nil, nil, { "heist", "retro" })
I("glove_white", "Hands", "White Gloves", 80, "gloves", {}, F, "#F5F5F2", nil, nil, { "business", "spooky" })
I("glove_medical", "Hands", "Medical Gloves", 20, "gloves", {}, F, "#4F7CC2", nil, nil, { "work" })
I("belt_leather", "Waist", "Leather Belt", 60, "belt", {}, "leather", "#111111", M, "#D4D6DC", { "business", "street" })
I("belt_gold_plate", "Waist", "Gold Plate Belt", 500, "belt", { big = true }, "leather", "#111111", M, "#E2B240", { "rap" }, T)
I("belt_iced", "Waist", "Iced Buckle Belt", 1200, "belt", { big = true, iced = true }, "leather", "#111111", M, "#D4D6DC", { "rap" })
I("belt_utility", "Waist", "Utility Belt", 200, "utility", {}, F, "#2B2B2B", M, "#8C8C8C", { "military", "work", "heist" })
I("belt_bag", "Waist", "Cross-Body Belt Bag", 160, "beltbag", {}, F, "#111111", M, "#D4D6DC", { "street", "tiktok" }, T)
I("belt_pocket_bandana", "Waist", "Back-Pocket Bandana", 0, "pocketbandana", {}, F, "#B3122E", nil, nil, { "hood", "western", "street" })
I("belt_wallet_chain", "Waist", "Wallet Chain", 160, "walletchain", {}, M, "#D4D6DC", nil, nil, { "retro", "street" })
I("back_duffel", "Back", "Heist Duffel Bag", 300, "duffel", {}, F, "#111111", M, "#8C8C8C", { "heist", "hood" }, T)
I("back_backpack", "Back", "School Backpack", 120, "backpack", {}, F, "#2E4A7A", F, "#111111", { "street", "cute" })
I("back_mini_pack", "Back", "Mini Backpack", 140, "backpack", { mini = true }, F, "#F4A6C8", F, "#F5F5F2", { "cute", "tiktok" })
I("back_sling", "Back", "Sling Bag", 120, "sling", {}, F, "#111111", M, "#D4D6DC", { "street", "hood" }, T)
I("back_cape", "Back", "Hero Cape", 300, "cape", {}, "bright", "#FF3B30", "bright", "#FFE600", { "hero" })
I("back_cape_long", "Back", "Royal Long Cape", 450, "cape", { len = 3.4 }, F, "#7A1022", "metal", "#E2B240", { "fantasy", "rap" })
I("back_wings", "Back", "Feather Wings", 600, "wings", {}, F, "#F5F5F2", F, "#E8DCC0", { "cute", "hero" })
I("back_neon_wings", "Back", "Neon Hologram Wings", 900, "wings", { neon = true }, "neon", "#00FFDC", "neon", "#FF2BD6", { "scifi" }, TN)
I("back_jetpack", "Back", "Retro Jetpack", 1200, "jetpack", {}, M, "#D4D6DC", "neon", "#FF5F1F", { "scifi", "hero" })
I("back_guitar", "Back", "Acoustic Guitar", 300, "guitar", {}, "leather", "#B98A5E", F, "#111111", { "retro", "western" })
I("back_sword", "Back", "Ronin Sword (Cosmetic)", 400, "sword", {}, "leather", "#111111", F, "#B3122E", { "fantasy" })

---------------------------------------------------------------------------------------------------- presets
-- preset looks: a whole outfit in one tap. colours: { slot = { id, c1?, c2? } } (missing colours = item defaults)
local function look(id, name, col, slots, tags)
	return { id = id, name = name, col = col, look = slots, tags = tags or {} }
end
local function e(id, c1, c2)
	return { id = id, c1 = c1, c2 = c2 }
end
C.LOOKS = {
	-- Realistic Hood (inspired by the styles players pick in realistic hood RP games)
	look("hood_locs_shades", "Locs & Shades", "hood", { Hair = e("hair_locs_front"), Top = e("top_hoodie_puff"), Bottom = e("bot_baggy_black"),
		Shoes = e("shoe_hightop_bw"), Face = e("eye_shades_black"), Neck = e("chain_cuban_iced"), Neck2 = e("chain_cross_2"),
		Hands = e("glove_black"), FacialHair = e("beard_chin_beard"), Grillz = e("grill_iced_top") }, T),
	look("hood_pink_camo", "Pink Camo Drip", "hood", { Hair = e("hair_locs_long"), Top = e("top_hoodie_camo"), Bottom = e("bot_baggy"),
		Shoes = e("shoe_white_low"), Face = e("eye_rect_shades"), Neck = e("chain_letter"), Neck2 = e("chain_tennis_2"),
		Hands = e("glove_black"), Ears = e("ear_big_studs") }, TN),
	look("hood_fitted", "Fitted & Iced", "hood", { Hair = e("hair_waves_fade"), Head = e("hat_fitted"), Top = e("top_hoodie"), Bottom = e("bot_baggy_black"),
		Shoes = e("shoe_work_boots"), Face = e("eye_shades_black"), Neck = e("chain_iced_piece"), FacialHair = e("beard_fade"),
		Ears = e("ear_studs"), Wrist = e("watch_iced") }, T),
	look("hood_twists_duffel", "Messy Twists & Duffel", "hood", { Hair = e("hair_messy_twists"), Top = e("top_hoodie"), Bottom = e("bot_cargo_black"),
		Shoes = e("shoe_black_low"), Back = e("back_duffel"), Neck = e("chain_cuban_gold"), Hands = e("glove_black") }, TN),
	look("hood_ski", "Ski Mask Season", "hood", { Mask = e("mask_ski_open"), Top = e("top_hoodie"), Outer = e("out_puffer"), Bottom = e("bot_baggy_black"),
		Shoes = e("shoe_work_boots"), Neck = e("chain_cuban_thick"), Hands = e("glove_black") }, T),
	look("hood_workwear", "Canvas Workwear", "hood", { Hair = e("hair_cornrows"), Head = e("hat_work_beanie"), Top = e("top_hoodie"), Outer = e("out_work_jacket"),
		Bottom = e("bot_baggy"), Shoes = e("shoe_work_boots"), Neck = e("chain_cuban_gold"), FacialHair = e("beard_chinstrap") }, T),
	look("hood_bandana", "Loose Bandana", "hood", { Hair = e("hair_cornrows_long"), Mask = e("mask_loose_bandana"), Top = e("top_tee_black"),
		Bottom = e("bot_baggy"), Shoes = e("shoe_hightop"), Neck = e("chain_rope_gold"), Waist = e("belt_pocket_bandana") }, T),
	look("hood_durag", "Durag & Puffer", "hood", { Head = e("hat_durag"), Top = e("top_hoodie"), Outer = e("out_puffer_shine"), Bottom = e("bot_baggy_black"),
		Shoes = e("shoe_slides"), Neck = e("chain_cuban_iced"), Ears = e("ear_big_studs"), Grillz = e("grill_gold_top") }, T),

	-- Lowrider (Chicano lowrider culture: fashion only, no gang names, colours or numbers)
	look("low_classic", "Lowrider Classic", "lowrider", { Hair = e("hair_bald"), Top = e("top_long_white"), Bottom = e("bot_khakis"), Shoes = e("shoe_classic"),
		Face = e("eye_shades_black"), FacialHair = e("beard_goatee"), Neck = e("chain_rosary"), Waist = e("belt_leather"),
		Ink = { L = { lower = "fa_script_familia" }, R = { lower = "fa_rosa" }, neck = "nk_rosa_lado" } }, TN),
	look("low_flannel", "Top-Button Flannel", "lowrider", { Hair = e("hair_slick_back"), Head = e("hat_hairnet"), Top = e("top_button_flannel"),
		Bottom = e("bot_work_creased"), Shoes = e("shoe_classic"), Face = e("eye_shades_black"), FacialHair = e("beard_pencil"),
		Ink = { face = "fc_cruz" } }, TN),
	look("low_zoot", "Zoot Suit Sharp", "lowrider", { Hair = e("hair_pomp"), Head = e("hat_fedora", "#111111"), Top = e("top_dress_shirt"), Neck = e("neck_tie_black"),
		Outer = e("out_zoot"), Bottom = e("bot_zoot"), Shoes = e("shoe_two_tone"), Waist = e("belt_wallet_chain"), FacialHair = e("beard_pencil") }, TN),
	look("low_cruiser", "Sunday Cruiser", "lowrider", { Hair = e("hair_buzz_fade"), Head = e("hat_folded_bandana"), Top = e("top_tank"), Outer = e("out_suspenders"),
		Bottom = e("bot_shorts_socks"), Shoes = e("shoe_classic"), Neck = e("chain_rosary_gold"),
		Face = e("eye_shades_black"), Ink = { L = { upper = "sl_rosas_nubes" }, R = { upper = "sl_reloj_rosa" } } }, TN),
	look("low_barrio", "Barrio Sleeves", "lowrider", { Hair = e("hair_buzz"), Top = e("top_tank"), Bottom = e("bot_work_creased", "#111111"), Shoes = e("shoe_classic", "#111111"),
		FacialHair = e("beard_goatee"), Neck = e("chain_cross_gold"), Face = e("eye_shades_black"), Wrist = e("watch_gold"),
		Ink = { L = { upper = "sl_smile_cry" }, R = { upper = "sl_corona" }, neck = "nk_cruz" } }, T),

	-- Rap Royalty
	look("rap_iced_out", "Iced Out Rapper", "rap", { Hair = e("hair_locs_gold"), Top = e("top_tee_black"), Outer = e("out_fur"), Bottom = e("bot_leather"),
		Shoes = e("shoe_chunky"), Face = e("eye_rect_shades"), Neck = e("chain_cuban_iced"), Neck2 = e("chain_iced_piece_2"),
		Grillz = e("grill_iced_full"), Ears = e("ear_big_studs"), Wrist = e("watch_iced"), Wrist2 = e("brace_both"), Rings = e("rings_iced") }, T),
	look("rap_gold", "Gold Everything", "rap", { Hair = e("hair_waves"), Top = e("top_tee"), Bottom = e("bot_baggy"), Shoes = e("shoe_white_low"),
		Neck = e("chain_cuban_gold"), Neck2 = e("chain_medallion_2"), Grillz = e("grill_gold_full"), Wrist = e("watch_gold"),
		Wrist2 = e("brace_cuban"), Rings = e("rings_gold"), Face = e("eye_aviator"), Waist = e("belt_gold_plate") }, T),
	look("rap_old_school", "Old-School MC", "rap", { Hair = e("hair_high_top"), Top = e("top_tee"), Outer = e("out_track"), Bottom = e("bot_track"),
		Shoes = e("shoe_white_low"), Neck = e("chain_dookie"), Head = e("hat_bucket"), Ears = e("ear_hoops") }),
	look("rap_pink", "Pink Diamonds", "rap", { Hair = e("hair_braids_beads"), Top = e("top_hoodie", "#F4A6C8"), Bottom = e("bot_baggy", "#A9C1DD"),
		Shoes = e("shoe_white_low"), Neck = e("chain_cuban_pink"), Neck2 = e("chain_heart_2"), Grillz = e("grill_rose"), Ears = e("ear_big_studs") }, N),
	look("rap_king", "Crowned King", "rap", { Hair = e("hair_cornrows"), Head = e("hat_iced_crown"), Top = e("top_tee_black"), Outer = e("out_fur", "#F5F5F2"),
		Bottom = e("bot_leather"), Shoes = e("shoe_chunky", "#111111"), Back = e("back_cape_long"), Neck = e("chain_crown"), Grillz = e("grill_platinum") }),

	-- Streetwear / For You Page
	look("street_fit_check", "Fit Check", "tiktok", { Hair = e("hair_fluffy_fringe"), Top = e("top_tee_black"), Outer = e("out_funnel"), Bottom = e("bot_barrel"),
		Shoes = e("shoe_slim_runner"), Face = e("eye_shield_sport"), Neck = e("chain_lock") }, TN),
	look("tiktok_aura", "Aura Farmer", "tiktok", { Hair = e("hair_burst_fade"), Top = e("top_tee_aura"), Bottom = e("bot_jorts"), Shoes = e("shoe_chunky"),
		Neck = e("chain_pearls"), Ears = e("ear_one_stud") }, TN),
	look("tiktok_quiet_lux", "Quiet Luxury", "business", { Hair = e("hair_slick_back"), Top = e("top_quarter_zip"), Bottom = e("bot_chinos"),
		Shoes = e("shoe_loafer"), Wrist = e("watch_steel") }, T),
	look("tiktok_office_siren", "Office Chic", "tiktok", { Hair = e("hair_claw_clip"), Top = e("top_office_siren"), Bottom = e("bot_pencil_skirt"),
		Shoes = e("shoe_heels"), Face = e("eye_specs"), Ears = e("ear_pearls") }, T),
	look("tiktok_mob_wife", "Fur Coat Era", "tiktok", { Hair = e("hair_long_sleek"), Top = e("top_slip_dress", "#111111"), Outer = e("out_fur"),
		Shoes = e("shoe_heels"), Face = e("eye_cateye"), Neck = e("chain_cuban_gold"), Ears = e("ear_big_hoops") }, T),
	look("tiktok_coquette", "Bows & Pearls", "cute", { Hair = e("hair_long_bangs"), Top = e("top_bow_crop"), Bottom = e("bot_pleated_skirt", "#F4A6C8"),
		Shoes = e("shoe_platform"), Neck = e("chain_pearls"), Ears = e("ear_pearls") }, T),
	look("tiktok_gorp", "Trail Ready", "tiktok", { Hair = e("hair_wolf_cut"), Top = e("top_tee"), Outer = e("out_gorp_shell"), Bottom = e("bot_cargo"),
		Shoes = e("shoe_clogs"), Head = e("hat_fisherman"), Back = e("back_sling") }, T),
	look("tiktok_fisherman", "Fisherman Core", "tiktok", { Hair = e("hair_curtains"), Head = e("hat_fisherman"), Top = e("top_chunky_knit"),
		Bottom = e("bot_wide_trouser", "#1B2A41"), Shoes = e("shoe_clogs"), FacialHair = e("beard_heavy_stubble") }, T),
	look("tiktok_countryside", "Countryside Prep", "tiktok", { Hair = e("hair_side_part"), Top = e("top_vneck_sweater"), Outer = e("out_field_waxed"),
		Bottom = e("bot_slim"), Shoes = e("shoe_work_boots", "#4A2C1A") }, TN),
	look("tiktok_officer", "Brass Buttons", "tiktok", { Hair = e("hair_italian_bob"), Top = e("top_turtleneck"), Outer = e("out_officer"),
		Bottom = e("bot_wide_trouser"), Shoes = e("shoe_wedges") }, TN),
	look("tiktok_butter", "Butter Yellow Summer", "tiktok", { Hair = e("hair_butterfly"), Top = e("top_slip_dress", "#F6E27A"), Shoes = e("shoe_sandals"),
		Face = e("eye_tiny_oval") }, T),
	look("tiktok_hockey", "Rink Romance", "tiktok", { Hair = e("hair_long_curtains"), Top = e("top_jersey_hockey"), Bottom = e("bot_slim"), Shoes = e("shoe_white_low"),
		Head = e("hat_beanie") }, TN),
	look("street_varsity", "Varsity Star", "street", { Hair = e("hair_curly_top"), Top = e("top_tee"), Outer = e("out_varsity"), Bottom = e("bot_baggy"),
		Shoes = e("shoe_hightop") }, T),
	look("street_hooper", "Courtside", "sport", { Hair = e("hair_cornrows"), Top = e("top_jersey_hoop"), Bottom = e("bot_shorts_hoop"), Shoes = e("shoe_hightop"),
		Head = e("hat_headband"), Wrist2 = e("brace_beads") }, T),
	look("street_footy", "Matchday", "sport", { Hair = e("hair_edgar"), Top = e("top_jersey_soccer"), Bottom = e("bot_baggy"), Shoes = e("shoe_slim_runner"),
		Neck = e("chain_box") }, T),
	look("street_moto", "Motorsport Fit", "street", { Hair = e("hair_low_taper"), Top = e("top_tee_black"), Outer = e("out_racing"), Bottom = e("bot_baggy_black"),
		Shoes = e("shoe_chunky", "#111111"), Face = e("eye_shield_sport") }, T),
	look("street_streamer", "Streamer Setup", "tiktok", { Hair = e("hair_wolf_cut"), Top = e("top_hoodie"), Bottom = e("bot_joggers"), Shoes = e("shoe_slides"),
		Head = e("hat_gamer_headset") }, T),

	-- Business
	look("biz_ceo", "Corner Office CEO", "business", { Hair = e("hair_side_part"), Top = e("top_dress_shirt"), Neck = e("neck_tie"), Outer = e("out_blazer"),
		Bottom = e("bot_trousers"), Shoes = e("shoe_oxford"), Wrist = e("watch_gold"), FacialHair = e("beard_short_boxed") }),
	look("biz_power", "Power Suit", "business", { Hair = e("hair_italian_bob"), Top = e("top_office_siren"), Outer = e("out_double"),
		Bottom = e("bot_wide_trouser", "#F5F5F2"), Shoes = e("shoe_heels"), Ears = e("ear_pearls") }, T),
	look("biz_made_man", "Old-School Boss", "business", { Hair = e("hair_slick_back"), Head = e("hat_fedora"), Top = e("top_dress_shirt", "#111111"),
		Neck = e("neck_tie", "#F5F5F2"), Outer = e("out_blazer_charcoal"), Bottom = e("bot_trousers", "#2B2B2B"), Shoes = e("shoe_oxford"),
		Rings = e("rings_gold"), Waist = e("belt_leather") }),
	look("biz_black_tie", "Black Tie", "business", { Hair = e("hair_pomp"), Top = e("top_dress_shirt"), Neck = e("neck_bowtie"), Outer = e("out_tux"),
		Bottom = e("bot_trousers", "#111111"), Shoes = e("shoe_oxford"), Wrist = e("watch_steel") }),
	look("biz_vice", "Pastel Linen Nights", "retro", { Hair = e("hair_long_wavy", "#DDBA80"), Top = e("top_tee", "#9CC3E6"), Outer = e("out_pastel_suit"),
		Bottom = e("bot_trousers", "#F4A6C8"), Shoes = e("shoe_loafer", "#F5F5F2"), Face = e("eye_aviator"), FacialHair = e("beard_stubble") }, T),

	-- Military
	look("mil_woodland", "Woodland Rifleman", "military", { Hair = e("hair_buzz"), Head = e("hat_combat_helmet"), Top = e("top_longsleeve", "#4B5320"),
		Outer = e("out_plate_carrier"), Bottom = e("bot_cargo"), Shoes = e("shoe_combat"), Hands = e("glove_tactical"), Neck = e("chain_dogtags"),
		Waist = e("belt_utility") }),
	look("mil_desert", "Desert Infantry", "military", { Hair = e("hair_crew"), Head = e("hat_combat_helmet", "#C8B88A"), Top = e("top_longsleeve", "#C8B88A"),
		Outer = e("out_plate_carrier", "#C8B88A"), Bottom = e("bot_camo_cargo"), Shoes = e("shoe_desert_boots"), Face = e("eye_shield_sport") }),
	look("mil_night", "Night Ops", "military", { Head = e("hat_nvg_helmet"), Mask = e("mask_skull"), Top = e("top_longsleeve", "#111111"),
		Outer = e("out_tactical_black"), Bottom = e("bot_cargo_black"), Shoes = e("shoe_combat"), Hands = e("glove_black"), Waist = e("belt_utility") }),
	look("mil_pilot", "Fighter Pilot", "military", { Hair = e("hair_crew"), Top = e("top_flight_suit"), Outer = e("out_bomber"), Bottom = e("bot_cargo"),
		Shoes = e("shoe_combat"), Face = e("eye_aviator_mirror") }),
	look("mil_beret", "Honor Guard", "military", { Hair = e("hair_buzz"), Head = e("hat_beret"), Top = e("top_dress_shirt", "#C8B88A"), Neck = e("neck_tie_black"),
		Outer = e("out_officer", "#4B5320"), Bottom = e("bot_trousers", "#4B5320"), Shoes = e("shoe_oxford") }),

	-- Heist Crew
	look("heist_classic", "Classic Bank Robber", "heist", { Mask = e("mask_ski"), Top = e("top_turtleneck"), Outer = e("out_tactical_black"),
		Bottom = e("bot_cargo_black"), Shoes = e("shoe_combat"), Hands = e("glove_black"), Back = e("back_duffel") }, T),
	look("heist_clown", "Clown Crew", "heist", { Mask = e("mask_clown"), Top = e("top_dress_shirt", "#111111"), Outer = e("out_blazer", "#111111"),
		Bottom = e("bot_trousers", "#111111"), Shoes = e("shoe_oxford"), Hands = e("glove_black"), Back = e("back_duffel") }),
	look("heist_driver", "Getaway Driver", "heist", { Hair = e("hair_slick_back", "#C9995C"), Top = e("top_tee"), Outer = e("out_bomber", "#F5F5F2"),
		Bottom = e("bot_slim"), Shoes = e("shoe_loafer"), Hands = e("glove_driving"), Face = e("eye_aviator") }),
	look("heist_cat", "Cat Burglar", "heist", { Hair = e("hair_pony"), Head = e("hat_beanie"), Top = e("top_turtleneck"), Bottom = e("bot_leggings"),
		Shoes = e("shoe_black_low"), Hands = e("glove_black"), Waist = e("belt_utility") }),
	look("heist_outlaw", "Outlaw", "western", { Head = e("hat_cowboy", "#2A1B12"), Mask = e("mask_bandana_face", "#B3122E"), Top = e("top_denim_shirt"),
		Outer = e("out_cowboy_vest"), Bottom = e("bot_jeans"), Shoes = e("shoe_cowboy"), Hands = e("glove_driving") }),
	look("heist_suits", "Suit & Ski Mask", "heist", { Mask = e("mask_ski"), Top = e("top_dress_shirt"), Neck = e("neck_tie_black"), Outer = e("out_blazer_charcoal"),
		Bottom = e("bot_trousers", "#2B2B2B"), Shoes = e("shoe_oxford"), Hands = e("glove_white"), Back = e("back_duffel") }),

	-- Neon Coast & jobs
	look("coast_local", "Beach Local", "coast", { Hair = e("hair_long_wavy"), Top = e("top_resort_shirt"), Bottom = e("bot_board"), Shoes = e("shoe_flipflops"),
		Face = e("eye_aviator_mirror"), Neck = e("chain_puka") }, T),
	look("coast_pool", "Pool Day", "coast", { Hair = e("hair_buzz_fade"), Top = e("top_tank"), Bottom = e("bot_swim"), Shoes = e("shoe_slides"), Face = e("eye_shield_sport"),
		Head = e("hat_bucket", "#F5F5F2") }),
	look("coast_lifeguard", "Lifeguard", "work", { Hair = e("hair_long_male", "#DDBA80"), Top = e("top_tank", "#B3122E"), Outer = e("out_lifeguard"),
		Bottom = e("bot_swim", "#B3122E"), Shoes = e("shoe_flipflops", "#B3122E"), Head = e("hat_visor") }),
	look("job_medic", "Paramedic", "work", { Hair = e("hair_crew"), Top = e("top_scrubs", "#1B2A41"), Bottom = e("bot_cargo", "#1B2A41"), Shoes = e("shoe_black_low"),
		Hands = e("glove_medical"), Wrist = e("watch_smart") }),
	look("job_mechanic", "Mechanic", "work", { Hair = e("hair_mid_fade"), Top = e("top_coveralls"), Bottom = e("bot_jeans"), Shoes = e("shoe_work_boots"),
		Head = e("hat_dad", "#1B2A41") }),
	look("job_chef", "Head Chef", "work", { Hair = e("hair_crew"), Top = e("top_tee"), Outer = e("out_chef"), Bottom = e("bot_chinos", "#111111"), Shoes = e("shoe_clogs"),
		Head = e("hat_chef") }),
	look("job_builder", "Construction", "work", { Hair = e("hair_buzz"), Head = e("hat_hardhat"), Top = e("top_tee", "#E8A33D"), Outer = e("out_work_jacket"),
		Bottom = e("bot_jeans"), Shoes = e("shoe_work_boots"), Waist = e("belt_utility") }),
	look("job_agent", "Federal Agent", "work", { Hair = e("hair_pony"), Top = e("top_dress_shirt"), Outer = e("out_agent_jacket"), Bottom = e("bot_slim"),
		Shoes = e("shoe_combat"), Wrist = e("watch_steel") }, TN),

	-- Retro, western, sci-fi, fantasy, heroes, spooky, cute
	look("retro_80s", "Arcade Kid", "retro", { Hair = e("hair_classic_mullet"), Top = e("top_stripe_tee"), Outer = e("out_windbreaker"), Bottom = e("bot_jeans", "#7A9CC6"),
		Shoes = e("shoe_white_low"), Head = e("hat_headband", "#FF2BD6") }),
	look("retro_grunge", "90s Grunge", "retro", { Hair = e("hair_long_male"), Top = e("top_tee_black"), Outer = e("out_flannel_open"), Bottom = e("bot_ripped"),
		Shoes = e("shoe_combat"), Head = e("hat_beanie") }),
	look("retro_y2k", "Y2K Pop Star", "retro", { Hair = e("hair_space_buns"), Top = e("top_crop"), Bottom = e("bot_jeans", "#A9C1DD"), Shoes = e("shoe_platform"),
		Face = e("eye_tiny_oval"), Ears = e("ear_big_hoops") }),
	look("retro_disco", "Disco Night", "retro", { Hair = e("hair_afro_big"), Top = e("top_open_collar", "#E8A33D"), Outer = e("out_pastel_suit", "#F5F5F2"),
		Bottom = e("bot_wide_trouser", "#F5F5F2"), Shoes = e("shoe_platform"), Neck = e("chain_medallion") }),
	look("west_cowboy", "Gunslinger", "western", { Hair = e("hair_long_male"), Head = e("hat_cowboy"), Top = e("top_denim_shirt"), Outer = e("out_cowboy_vest"),
		Bottom = e("bot_jeans"), Shoes = e("shoe_cowboy"), FacialHair = e("beard_horseshoe"), Mask = e("mask_loose_bandana") }),
	look("west_cowgirl", "Coastal Cowgirl", "western", { Hair = e("hair_long_wavy"), Head = e("hat_cowboy", "#F5F5F2"), Top = e("top_crop", "#F5F5F2"),
		Bottom = e("bot_jorts"), Shoes = e("shoe_cowboy", "#F5F5F2"), Neck = e("chain_puka") }, T),
	look("scifi_runner", "Neon Cyber Runner", "scifi", { Hair = e("hair_mohawk", "#2F6BFF"), Top = e("top_tee_black"), Outer = e("out_cyber"),
		Bottom = e("bot_cargo_black"), Shoes = e("shoe_combat"), Mask = e("mask_cyber"), Face = e("eye_vr") }, T),
	look("scifi_astronaut", "Astronaut", "scifi", { Top = e("top_spacesuit"), Bottom = e("bot_jeans"), Shoes = e("shoe_combat", "#F5F5F2"), Head = e("hat_space_helmet"),
		Hands = e("glove_white") }),
	look("scifi_red_suit", "Red Deep-Space Explorer", "scifi", { Top = e("top_spacesuit_red"), Bottom = e("bot_jeans"), Shoes = e("shoe_combat", "#F5F5F2"),
		Head = e("hat_space_helmet"), Hands = e("glove_white") }, TN),
	look("scifi_trooper", "Orbital Trooper", "scifi", { Top = e("top_trooper_armor"), Bottom = e("bot_cargo_black"), Shoes = e("shoe_combat", "#F5F5F2"),
		Head = e("hat_combat_helmet", "#F5F5F2"), Mask = e("mask_gas", "#F5F5F2"), Hands = e("glove_black") }),
	look("scifi_vr", "Full-Dive Gamer", "scifi", { Hair = e("hair_fluffy_fringe", "#7B3FE4"), Top = e("top_hoodie_zip"), Bottom = e("bot_joggers"),
		Shoes = e("shoe_chunky"), Face = e("eye_vr"), Hands = e("glove_black"), Back = e("back_neon_wings") }, TN),
	look("fan_warrior_king", "Bronze Warrior King", "fantasy", { Hair = e("hair_long_male", "#2C2019"), FacialHair = e("beard_full"), Top = e("top_bronze_armor"),
		Bottom = e("bot_leggings", "#5C3A21"), Shoes = e("shoe_sandals"), Back = e("back_cape_long", "#7A1022"), Head = e("hat_crown") }, TN),
	look("fan_knight", "Knight", "fantasy", { Top = e("top_knight_armor"), Head = e("hat_knight_helm"), Bottom = e("bot_leggings", "#8C8C8C"),
		Shoes = e("shoe_combat", "#8C8C8C"), Back = e("back_cape") }),
	look("fan_wizard", "Wizard", "fantasy", { Hair = e("hair_long_male", "#D9D4CC"), FacialHair = e("beard_long", "#D9D4CC"), Top = e("top_wizard_robe"),
		Head = e("hat_wizard"), Bottom = e("bot_leggings"), Shoes = e("shoe_sandals") }),
	look("fan_ronin", "Ronin", "fantasy", { Hair = e("hair_man_bun"), Top = e("top_ninja_gi", "#1B2A41"), Bottom = e("bot_wide_trouser", "#111111"),
		Shoes = e("shoe_sandals"), Back = e("back_sword"), FacialHair = e("beard_goatee") }),
	look("fan_ninja", "Shadow Ninja", "fantasy", { Mask = e("mask_ninja"), Top = e("top_ninja_gi"), Bottom = e("bot_leggings"), Shoes = e("shoe_black_low"),
		Back = e("back_sword") }),
	look("fan_pirate", "Pirate Captain", "fantasy", { Hair = e("hair_long_male", "#0B0908"), Head = e("hat_tricorn"), Face = e("eye_patch"), Top = e("top_open_collar"),
		Outer = e("out_pirate"), Bottom = e("bot_leather"), Shoes = e("shoe_cowboy", "#111111"), FacialHair = e("beard_full"), Ears = e("ear_hoops") }),
	look("hero_classic", "Caped Hero", "hero", { Hair = e("hair_side_part"), Top = e("top_hero_suit"), Bottom = e("bot_leggings", "#00A2FF"), Shoes = e("shoe_combat", "#FF3B30"),
		Back = e("back_cape"), Waist = e("belt_leather", "#FFE600") }),
	look("hero_night", "Night Vigilante", "hero", { Top = e("top_hero_suit", "#111111", "#2B2B2B"), Bottom = e("bot_leggings"), Shoes = e("shoe_combat"),
		Mask = e("mask_ninja", "#111111"), Back = e("back_cape", "#111111", "#111111"), Hands = e("glove_black"), Waist = e("belt_utility") }),
	look("hero_villain", "Supervillain", "hero", { Hair = e("hair_slick_back", "#E9F0F5"), Top = e("top_hero_suit", "#4A2B6B", "#39FF14"), Bottom = e("bot_leggings", "#4A2B6B"),
		Shoes = e("shoe_combat"), Back = e("back_cape_long", "#111111"), Hands = e("glove_black") }),
	look("spooky_vamp", "Vampire Noble", "spooky", { Hair = e("hair_slick_long"), Top = e("top_vampire"), Bottom = e("bot_trousers", "#111111"), Shoes = e("shoe_oxford"),
		Grillz = e("grill_fangs", "#F2F2F2") }),
	look("spooky_slasher", "Horror Night", "spooky", { Mask = e("mask_goalie"), Top = e("top_coveralls", "#2B2B2B"), Bottom = e("bot_jeans", "#1E2A3A"),
		Shoes = e("shoe_work_boots", "#4A2C1A"), Hands = e("glove_black") }),
	look("spooky_unicorn", "Unicorn Onesie", "cute", { Head = e("hat_unicorn_hood"), Top = e("top_jumpsuit_orange", "#F5F5F2", "#F5F5F2"), Bottom = e("bot_leggings", "#F5F5F2"),
		Shoes = e("shoe_slides", "#F4A6C8") }, TN),
	look("cute_angel", "Angel", "cute", { Hair = e("hair_long_wavy", "#F3E6C8"), Head = e("hat_halo"), Top = e("top_slip_dress", "#F5F5F2"), Shoes = e("shoe_sandals", "#F5F5F2"),
		Back = e("back_wings") }),
	look("cute_kitty", "Kitty", "cute", { Hair = e("hair_bob_bangs"), Head = e("hat_cat_ears"), Top = e("top_crop", "#111111"), Bottom = e("bot_pleated_skirt", "#111111"),
		Shoes = e("shoe_platform", "#111111"), Neck = e("neck_choker") }),
}

-- a fixed mechanic look referenced above: keep presets pointing at real items only (validated at load)
---------------------------------------------------------------------------------------------------- defaults
-- the free starter look everyone spawns in before choosing
C.DEFAULT_LOOK = {
	Skin = { id = "skin", c1 = "#CF9670" },
	Eyes = { id = "eyes_natural", c1 = "#4E3420" },
	Brows = { id = "brows_natural", c1 = "#2C2019" },
	Hair = { id = "hair_low_taper", c1 = "#1C1512" },
	Top = { id = "top_tee", c1 = "#F5F5F2", c2 = "#111111" },
	Bottom = { id = "bot_jeans", c1 = "#34507A" },
	Shoes = { id = "shoe_white_low", c1 = "#F5F5F2", c2 = "#F5F5F2" },
}

---------------------------------------------------------------------------------------------------- face shape
-- Sliders for the MakeHuman faces (Character Studio, Body tab, "Face shape"). Each moves face bones (NC_Face*, made
-- by build_makehuman_rig.py) by `moves` studs per full slider (-1 .. 1), in the head's space: +X = the character's
-- left, +Y up, -Z forward. NCHead applies them; the brows, lips, lashes, stubble and eyes follow their bones.
-- Saved in the look as FaceShape = { v = { [slider id] = number } }. Free, so they never change the price.
C.FACE_SLIDERS = {
	{ id = "eyeSpacing", name = "Eye spacing", moves = { NC_FaceEyeL = Vector3.new(-0.012, 0, 0), NC_FaceEyeR = Vector3.new(0.012, 0, 0) } },
	{ id = "eyeHeight", name = "Eye height", moves = { NC_FaceEyeL = Vector3.new(0, 0.015, 0), NC_FaceEyeR = Vector3.new(0, 0.015, 0) } },
	{ id = "browHeight", name = "Brow height", moves = { NC_FaceBrowL = Vector3.new(0, 0.022, 0), NC_FaceBrowR = Vector3.new(0, 0.022, 0) } },
	{ id = "noseLength", name = "Nose length", moves = { NC_FaceNose = Vector3.new(0, -0.012, -0.032) } },
	{ id = "noseWidth", name = "Nose width", moves = { NC_FaceNostrilL = Vector3.new(-0.018, 0, 0), NC_FaceNostrilR = Vector3.new(0.018, 0, 0) } },
	{ id = "noseBridge", name = "Nose bridge", moves = { NC_FaceNoseBridge = Vector3.new(0, 0, -0.022) } },
	{ id = "cheeks", name = "Cheekbones", moves = { NC_FaceCheekL = Vector3.new(-0.022, 0.004, -0.01), NC_FaceCheekR = Vector3.new(0.022, 0.004, -0.01) } },
	{ id = "mouthWidth", name = "Mouth width", moves = { NC_FaceMouthL = Vector3.new(-0.018, 0, 0), NC_FaceMouthR = Vector3.new(0.018, 0, 0) } },
	{ id = "lips", name = "Lip fullness", moves = { NC_FaceLipUpper = Vector3.new(0, 0.007, -0.012), NC_FaceLipLower = Vector3.new(0, -0.008, -0.012) } },
	{ id = "jawWidth", name = "Jaw width", moves = { NC_FaceJawL = Vector3.new(-0.035, 0, 0), NC_FaceJawR = Vector3.new(0.035, 0, 0) } },
	{ id = "chin", name = "Chin length", moves = { NC_FaceChin = Vector3.new(0, -0.032, -0.012) } },
	{ id = "ears", name = "Ears out", moves = { NC_FaceEarL = Vector3.new(-0.028, 0, 0), NC_FaceEarR = Vector3.new(0.028, 0, 0) } },
}
C.FACE_SLIDER_BY_ID = {}
for _, sl in ipairs(C.FACE_SLIDERS) do
	C.FACE_SLIDER_BY_ID[sl.id] = sl
end
---------------------------------------------------------------------------------------------------- real ink
-- A look's tattoos are its Ink table: { L = { upper, lower, hand, leg }, R = { ... }, neck, face } of NCInkCatalog
-- ids, printed on the MakeHuman bodies' ink layers by NCInk (see CHARACTER_STUDIO.md "Real tattoos"). Each tattoo is
-- bought once (owned as "ink:<id>") and can then go on any spot it fits.
C.INK_SPOTS = {
	{ key = "L.upper", side = "L", spot = "upper", area = "Arm", name = "Left upper arm" },
	{ key = "L.lower", side = "L", spot = "lower", area = "Arm", name = "Left forearm" },
	{ key = "L.hand", side = "L", spot = "hand", area = "Hand", name = "Left hand" },
	{ key = "L.leg", side = "L", spot = "leg", area = "Leg", name = "Left leg" },
	{ key = "R.upper", side = "R", spot = "upper", area = "Arm", name = "Right upper arm" },
	{ key = "R.lower", side = "R", spot = "lower", area = "Arm", name = "Right forearm" },
	{ key = "R.hand", side = "R", spot = "hand", area = "Hand", name = "Right hand" },
	{ key = "R.leg", side = "R", spot = "leg", area = "Leg", name = "Right leg" },
	{ key = "neck", spot = "neck", area = "Neck", name = "Neck" },
	{ key = "face", spot = "face", area = "Face", name = "Face" },
}
local inkMod
function C.InkModule()
	if inkMod == nil then
		inkMod = false
		local RS = game:GetService("ReplicatedStorage")
		local m = RS:FindFirstChild("NCInk")
		if m and RS:FindFirstChild("NCInkCatalog") then
			local ok, res = pcall(require, m)
			inkMod = ok and res or false
		end
	end
	return inkMod or nil
end
function C.InkCatalog()
	local RS = game:GetService("ReplicatedStorage")
	local m = RS:FindFirstChild("NCInkCatalog")
	local ok, res = pcall(function()
		return m and require(m)
	end)
	return ok and res or nil
end
-- does this tattoo fit that spot? (a full arm sleeve goes in upper or lower; upper-only / lower-only pieces only there)
function C.InkFits(item, spot)
	if not item then
		return false
	end
	if spot.area ~= item.area then
		return false
	end
	if spot.spot == "upper" then
		return item.zone == "upper" or item.zone == "full"
	elseif spot.spot == "lower" then
		return item.zone == "lower" or item.zone == "full"
	end
	return true
end
-- a clean Ink table from anything a client sent (known ids on spots they fit), or nil when there's no ink
function C.CleanInk(raw)
	local IC = C.InkCatalog()
	if type(raw) ~= "table" or not IC then
		return nil
	end
	local out, any = {}, false
	for _, sp in ipairs(C.INK_SPOTS) do
		local id
		if sp.side then
			id = type(raw[sp.side]) == "table" and raw[sp.side][sp.spot]
		else
			id = raw[sp.spot]
		end
		local it = type(id) == "string" and IC.BY_ID[id]
		if it and C.InkFits(it, sp) then
			if sp.side then
				out[sp.side] = out[sp.side] or {}
				out[sp.side][sp.spot] = id
			else
				out[sp.spot] = id
			end
			any = true
		end
	end
	return any and out or nil
end
function C.InkIds(ink)
	local ids = {}
	for _, sp in ipairs(C.INK_SPOTS) do
		local id = ink and (sp.side and (ink[sp.side] or {})[sp.spot] or (not sp.side and ink[sp.spot]))
		if type(id) == "string" and not table.find(ids, id) then
			table.insert(ids, id)
		end
	end
	return ids
end

-- a clean FaceShape entry from anything a client sent (known sliders only, -1 .. 1, two decimals), or nil
function C.CleanFaceShape(raw)
	if type(raw) ~= "table" or type(raw.v) ~= "table" then
		return nil
	end
	local v, any = {}, false
	for id, x in pairs(raw.v) do
		if type(id) == "string" and C.FACE_SLIDER_BY_ID[id] and type(x) == "number" and x == x then
			x = math.round(math.clamp(x, -1, 1) * 100) / 100
			if x ~= 0 then
				v[id] = x
				any = true
			end
		end
	end
	return any and { v = v } or nil
end

---------------------------------------------------------------------------------------------------- mesh hair
-- On the MakeHuman bodies these items wear real mesh hair that grows out of a soft hairline (NCHead), one style per
-- body; the procedural version stays as the fallback (stock avatars, a body with no matching style, the previews).
local MESH = {
	hair_buzz = { Male = "Buzz" }, hair_buzz_fade = { Male = "Buzz" }, hair_waves = { Male = "Buzz" },
	hair_waves_fade = { Male = "Buzz" }, hair_crew = { Male = "Crop", Female = "Pixie" },
	hair_low_taper = { Male = "TaperFade", Female = "Pixie" }, hair_mid_fade = { Male = "TaperFade" },
	hair_high_fade_part = { Male = "HighFade" }, hair_burst_fade = { Male = "HighFade" },
	hair_french_crop = { Male = "Crop", Female = "Pixie" }, hair_side_part = { Male = "SidePart", Female = "Pixie" },
	hair_slick_back = { Male = "SidePart" }, hair_curly_top = { Male = "CurlyTop" },
	hair_sponge_twists = { Male = "Twists" }, hair_twists_long = { Male = "Twists" }, hair_flat_twists = { Male = "FlatTwists" },
	hair_messy_twists = { Male = "Twists" },
	hair_locs_short = { Male = "Locs", Female = "Locs" }, hair_locs_long = { Male = "Locs", Female = "Locs" },
	hair_locs_front = { Male = "Locs", Female = "Locs" }, hair_freeform = { Male = "Locs", Female = "Locs" },
	hair_long_straight = { Female = "LongStraight" }, hair_long_sleek = { Female = "LongStraight" },
	hair_long_bangs = { Female = "LongStraight" }, hair_butterfly = { Female = "LongStraight" },
	hair_bob = { Female = "Bob" }, hair_italian_bob = { Female = "Bob" }, hair_pixie = { Female = "Pixie", Male = "Crop" },
	hair_pony = { Female = "Ponytail" }, hair_high_pony = { Female = "Ponytail" },
	hair_claw_clip = { Female = "LowBun" }, hair_man_bun = { Female = "LowBun" },
}
local STUBBLE = { beard_stubble = "Stubble", beard_heavy_stubble = "StubbleHeavy" }
for _, it in ipairs(C.ITEMS) do
	local m = MESH[it.id]
	if m then
		it.p = { Male = m.Male, Female = m.Female, fb = { fam = it.fam, p = it.p } }
		it.fam = "meshhair"
	elseif STUBBLE[it.id] then
		it.p = { Male = STUBBLE[it.id], fb = { fam = it.fam, p = it.p } }
		it.fam = "meshface"
	end
end

---------------------------------------------------------------------------------------------------- index + checks
C.ITEMS_BY_ID = {}
C.SLOT_BY_ID = {}
C.ITEMS_BY_SLOT = {}
for _, s in ipairs(C.SLOTS) do
	C.SLOT_BY_ID[s.id] = s
	C.ITEMS_BY_SLOT[s.id] = {}
end
for _, it in ipairs(C.ITEMS) do
	if C.ITEMS_BY_ID[it.id] then
		warn("NCLookCatalog: duplicate item id " .. it.id)
	end
	C.ITEMS_BY_ID[it.id] = it
	if C.ITEMS_BY_SLOT[it.slot] then
		table.insert(C.ITEMS_BY_SLOT[it.slot], it)
	else
		warn("NCLookCatalog: " .. it.id .. " has unknown slot " .. tostring(it.slot))
	end
	it.trend = table.find(it.tags, "trend") ~= nil
	it.new = table.find(it.tags, "new") ~= nil
	if it.p and it.p.assetId then
		it.assetId = it.p.assetId
	end
end
-- drop preset entries that point at an item that doesn't exist (typo safety) so the studio never shows a broken look
for _, lk in ipairs(C.LOOKS) do
	for slot, en in pairs(lk.look) do
		local it = C.ITEMS_BY_ID[en.id]
		if slot == "Ink" or slot == "FaceShape" then
			continue -- (not a slot item: real ink is checked by C.CleanInk when it's worn)
		elseif not it or it.slot ~= slot then
			warn("NCLookCatalog: look " .. lk.id .. " has a bad " .. slot .. " item " .. tostring(en.id))
			lk.look[slot] = nil
		end
	end
	-- fill required slots from the default look
	for _, s in ipairs(C.SLOTS) do
		if s.required and not lk.look[s.id] then
			lk.look[s.id] = table.clone(C.DEFAULT_LOOK[s.id])
		end
	end
end

-- is this colour allowed on this item (c = 1 or 2)? the server uses this to reject made-up colours
function C.ColourAllowed(item, which, hexStr)
	if type(hexStr) ~= "string" then
		return false
	end
	local pal = which == 1 and item.pal1 or item.pal2
	local def = which == 1 and item.def1 or item.def2
	if hexStr:upper() == (def or ""):upper() then
		return true
	end
	local list = pal and C.PALETTES[pal]
	if not list then
		return false
	end
	for _, h in ipairs(list) do
		if h:upper() == hexStr:upper() then
			return true
		end
	end
	return false
end

-- what a look costs a player who owns `owned` ({ [itemId] = true })
function C.Cost(lookTable, owned)
	local total, missing = 0, {}
	for slot, en in pairs(lookTable) do
		local it = slot ~= "Ink" and slot ~= "FaceShape" and C.ITEMS_BY_ID[en.id]
		if it and it.price > 0 and not (owned and owned[it.id]) and not table.find(missing, it.id) then
			total += it.price
			table.insert(missing, it.id)
		end
	end
	-- real ink: each tattoo is bought once (owned as "ink:<id>")
	local IC = lookTable.Ink and C.InkCatalog()
	if IC then
		for _, id in ipairs(C.InkIds(lookTable.Ink)) do
			local it = IC.BY_ID[id]
			local key = "ink:" .. id
			if it and (it.price or 0) > 0 and not (owned and owned[key]) then
				total += it.price
				table.insert(missing, key)
			end
		end
	end
	return total, missing
end

return C
