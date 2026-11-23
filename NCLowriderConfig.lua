--!nonstrict
-- NCLowriderConfig (ModuleScript, ReplicatedStorage): everything you can buy at Low & Slow Kustoms, and the tuning
-- numbers for driving and the hydraulics. All names are original (no real brands). Prices are in the game's Cash.
-- Edit freely: the shop UI, the server checks and the car all read from here.
local C = {}

C.CarName = "Royale Lowrider"
C.CarPrice = 2500

-- candy paint colours (also used for the two-tone roof)
C.Paints = {
	{ id = "candy_sunset", name = "Candy Sunset Red", color = Color3.fromRGB(150, 8, 24), price = 0 },
	{ id = "candy_brandy", name = "Candy Brandywine", color = Color3.fromRGB(96, 6, 22), price = 400 },
	{ id = "candy_tangerine", name = "Candy Tangerine", color = Color3.fromRGB(230, 90, 10), price = 400 },
	{ id = "gold_leaf", name = "Candy Gold Leaf", color = Color3.fromRGB(226, 170, 40), price = 400 },
	{ id = "candy_lime", name = "Candy Lime Glow", color = Color3.fromRGB(90, 200, 30), price = 400 },
	{ id = "candy_teal", name = "Candy Teal Wave", color = Color3.fromRGB(10, 150, 150), price = 400 },
	{ id = "candy_cobalt", name = "Candy Cobalt", color = Color3.fromRGB(16, 52, 190), price = 400 },
	{ id = "candy_grape", name = "Candy Grape", color = Color3.fromRGB(92, 20, 140), price = 400 },
	{ id = "candy_magenta", name = "Candy Magenta Night", color = Color3.fromRGB(200, 20, 120), price = 400 },
	{ id = "root_beer", name = "Candy Root Beer", color = Color3.fromRGB(80, 34, 14), price = 400 },
	{ id = "candy_emerald", name = "Candy Emerald", color = Color3.fromRGB(8, 110, 50), price = 400 },
	{ id = "candy_rose", name = "Candy Rose Gold", color = Color3.fromRGB(214, 130, 120), price = 500 },
	{ id = "candy_copper", name = "Candy Copper", color = Color3.fromRGB(170, 70, 30), price = 400 },
	{ id = "candy_ice", name = "Candy Ice Blue", color = Color3.fromRGB(110, 190, 240), price = 400 },
	{ id = "pearl_white", name = "Pearl White", color = Color3.fromRGB(240, 238, 230), price = 600 },
	{ id = "silver", name = "Liquid Silver", color = Color3.fromRGB(175, 178, 186), price = 500 },
	{ id = "gunmetal", name = "Gunmetal", color = Color3.fromRGB(62, 66, 74), price = 400 },
	{ id = "midnight", name = "Midnight Black", color = Color3.fromRGB(14, 14, 18), price = 600 },
	{ id = "baby_blue", name = "Baby Blue", color = Color3.fromRGB(130, 180, 230), price = 400 },
	{ id = "mint", name = "Mint Cream", color = Color3.fromRGB(160, 230, 200), price = 400 },
	{ id = "butter", name = "Butter Cream", color = Color3.fromRGB(240, 220, 150), price = 400 },
	{ id = "bubblegum", name = "Bubblegum Pink", color = Color3.fromRGB(240, 140, 190), price = 400 },
}
C.CustomColorPrice = 750 -- any colour from the colour picker (paid once per exact colour)
C.BuildSlots = 3 -- saved build designs in the tuning menu

-- how the paint is laid down (Roblox material + shine)
C.Finishes = {
	{ id = "candy", name = "Candy gloss", material = Enum.Material.SmoothPlastic, reflectance = 0.22, price = 0 },
	{ id = "flake", name = "Metal flake", material = Enum.Material.Foil, reflectance = 0.12, price = 700 },
	{ id = "pearl", name = "Pearl", material = Enum.Material.SmoothPlastic, reflectance = 0.1, price = 500 },
	{ id = "chrome_wrap", name = "Chrome wrap", material = Enum.Material.Metal, reflectance = 0.5, price = 2500 },
	{ id = "brushed", name = "Brushed metal", material = Enum.Material.Metal, reflectance = 0.15, price = 900 },
	{ id = "satin", name = "Satin", material = Enum.Material.Plastic, reflectance = 0, price = 300 },
	{ id = "matte", name = "Flat matte", material = Enum.Material.Slate, reflectance = 0, price = 400 },
}

-- vinyls: real decal artwork printed flush on the paint (images from make_lowrider_vinyls.py, lowrider_vinyls/).
-- Each livery prints an image on some of the panels (hood, side, trunk, roof); see NCLowriderData.Car.Vinyls.
-- Clear parts of an image show the candy paint underneath, so every livery works with every paint colour.
C.Art = {
	{ id = "none", name = "Clean (no vinyls)", price = 0 },
	{ id = "pinstripe", name = "Gold pinstripe scrolls", price = 500 },
	{ id = "stripes", name = "Twin racing stripes", price = 600 },
	{ id = "checker", name = "Checker bands", price = 700 },
	{ id = "scallops", name = "Pearl scallops", price = 900 },
	{ id = "sunset_fade", name = "Sunset fade", price = 900 },
	{ id = "retro_waves", name = "Retro waves", price = 1000 },
	{ id = "lightning", name = "Electric lightning", price = 1000 },
	{ id = "flames", name = "Hot flames with blue pinstripe", price = 1100 },
	{ id = "flames_teal", name = "Ice flames with purple pinstripe", price = 1100 },
	{ id = "roses", name = "Rose vines", price = 1200 },
	{ id = "tropical", name = "Tropical palms", price = 1300 },
	{ id = "patterns", name = "Patterns, lace and fades", price = 1400 },
	{ id = "purple_lace", name = "Purple lace and fades", price = 1400 },
	{ id = "mural", name = "Sunset mural on the trunk + pinstripes", price = 1600 },
	{ id = "showcar", name = "Show car: patterns, lace roof and mural", price = 2400 },
}
-- Decal image ids. Importing LowriderVinyls.glb and running NCLowriderKit.Prepare on it fills these in by itself;
-- you can also upload the PNGs yourself and paste ids here, e.g. flames_side = "rbxassetid://123456".
C.VinylIds = {}

-- finishes for chrome parts (bumpers, grille, trim, rims, knock-offs...). "paint" follows the body colour.
C.TrimFinishes = {
	{ id = "chrome", name = "Chrome", price = 0, material = Enum.Material.Metal, color = Color3.fromRGB(225, 228, 235), reflectance = 0.45 },
	{ id = "gold", name = "24k gold", price = 800, material = Enum.Material.Metal, color = Color3.fromRGB(232, 182, 64), reflectance = 0.4 },
	{ id = "black", name = "Black chrome", price = 600, material = Enum.Material.Metal, color = Color3.fromRGB(40, 40, 46), reflectance = 0.35 },
	{ id = "rose", name = "Rose gold", price = 700, material = Enum.Material.Metal, color = Color3.fromRGB(222, 150, 132), reflectance = 0.38 },
	{ id = "copper", name = "Copper", price = 500, material = Enum.Material.Metal, color = Color3.fromRGB(190, 100, 60), reflectance = 0.35 },
	{ id = "satin", name = "Satin black", price = 400, material = Enum.Material.SmoothPlastic, color = Color3.fromRGB(22, 22, 24), reflectance = 0 },
	{ id = "paint", name = "Colour-matched", price = 500 },
}

-- suspension. hop = front hop launch speed (studs/s), lift = how far each corner can raise (studs),
-- drop = how far it can lay (studs below ride height), speed = how fast a corner moves (studs/s)
C.Suspension = {
	{ id = "stock", name = "Stock springs", price = 0, lift = 0, drop = 0, speed = 0, hop = 0, kit = "none" },
	{ id = "bags", name = "Air bags (smooth, lays frame, no hopping)", price = 1800, lift = 1.2, drop = 0.35, speed = 0.9, hop = 0, kit = "bags" },
	{ id = "hyd1", name = "Hydraulics: 2-pump street", price = 2500, lift = 1.4, drop = 0.35, speed = 4.0, hop = 15, kit = "hyd" },
	{ id = "hyd2", name = "Hydraulics: 3-pump, 3-wheel ready", price = 4500, lift = 1.7, drop = 0.35, speed = 5.5, hop = 23, kit = "hyd", threeWheel = true },
	{ id = "hyd3", name = "Hydraulics: 4-pump competition hopper", price = 8000, lift = 1.9, drop = 0.35, speed = 7.0, hop = 33, kit = "hyd", threeWheel = true, dance = true },
}

-- engine tunes: multiply top speed and acceleration
C.Engines = {
	{ id = "stock", name = "Stock 6.5L", price = 0, speed = 1, accel = 1 },
	{ id = "street", name = "Street tune", price = 1500, speed = 1.08, accel = 1.15 },
	{ id = "bigblock", name = "Big block + dual carbs", price = 4000, speed = 1.16, accel = 1.32 },
	{ id = "show", name = "Show motor (chrome everything)", price = 6500, speed = 1.22, accel = 1.45 },
}

-- driving (studs, seconds). The world is 1.15 studs per foot, so 60 studs/s is about 36 mph.
C.Drive = {
	TopSpeed = 70, ReverseSpeed = 18, Accel = 26, Brake = 60, Coast = 6,
	SteerMax = 34, SteerFast = 14, -- degrees at a standstill / at top speed
	Grip = 11, RearGrip = 9, -- sideways grip (1/s); lower rear = a little tail on hard turns
	SpringSag = 0.28, -- how far the springs settle under the car's weight
	Damping = 0.42, -- fraction of critical damping
	BumpStop = 0.45, -- the wheel can tuck this far above its laid position before the bump stop
	Droop = 0.6, -- how far a wheel hangs below its target when the corner is in the air
	Density = 0.55,
}

-- the shop: where it goes if the map has no part tagged NC_LowriderShopSpot (its front faces the spot's -Z)
C.ShopFallbackPosition = Vector3.new(260, 0, -260)
C.CustomizeRadius = 40 -- your car must be this close to the shop to customize it

-- optional sounds: put your own uploaded sound ids here ("rbxassetid://123"); empty = silent
C.Sounds = { Pump = "", Dump = "", Hop = "", Engine = "" }

---------------------------------------------------------------------------------------------------- the tuning menu
-- Everything you can change is one "mod": a look key with a list of options. The shop UI, the server's checks and
-- prices, and the car all read this table, so adding an option here (and its part in Blender, for "part_" keys)
-- is all it takes. Option ids are strings; "" means "none". A mod with custom = price also takes any colour from
-- the colour picker (stored as "c:RRGGBB").
--   part_<Slot>  shows that variant of a swappable part (NCLowriderData.Car.Options / Wheel.Options)
--   fin_<Group>  finish of the chrome pieces of those parts (C.TrimFinishes)
local function opts(list, extra)
	local out = {}
	for _, o in list do
		table.insert(out, { id = o[1], name = o[2], price = o[3] or 0, color = o[4] })
	end
	return out
end
local function fromList(list, priceOverride)
	local out = {}
	for _, it in list do
		table.insert(out, { id = it.id, name = it.name, price = priceOverride or it.price, color = it.color })
	end
	return out
end
local function rgb(r, g, b)
	return Color3.fromRGB(r, g, b)
end
local FIN = fromList(C.TrimFinishes)
local FIN_NO_PAINT = {}
for _, f in FIN do
	if f.id ~= "paint" then
		table.insert(FIN_NO_PAINT, f)
	end
end
local ROOF = { { id = "same", name = "Same as the body", price = 0 } }
for _, p in C.Paints do
	table.insert(ROOF, { id = p.id, name = p.name, price = 300, color = p.color })
end
local UPHOLSTERY = opts({
	{ "pearl", "Pearl white", 0, rgb(242, 238, 226) }, { "cream", "Cream", 200, rgb(236, 222, 190) }, { "black", "Black", 200, rgb(22, 22, 24) },
	{ "red", "Red", 300, rgb(170, 18, 30) }, { "wine", "Wine", 300, rgb(100, 14, 34) }, { "tan", "Saddle tan", 300, rgb(170, 110, 60) },
	{ "babyblue", "Baby blue", 300, rgb(140, 185, 230) }, { "purple", "Royal purple", 300, rgb(90, 30, 140) }, { "mint", "Mint", 300, rgb(160, 225, 195) },
	{ "teal", "Teal", 300, rgb(20, 140, 140) }, { "pink", "Pink", 300, rgb(240, 140, 190) }, { "gold", "Gold", 400, rgb(220, 170, 60) },
})
local PIPING = opts({
	{ "match", "Match the seats", 0 }, { "white", "White", 150, rgb(250, 250, 250) }, { "black", "Black", 150, rgb(20, 20, 22) },
	{ "gold", "Gold", 200, rgb(226, 176, 60) }, { "red", "Red", 150, rgb(190, 20, 30) }, { "teal", "Teal", 150, rgb(30, 190, 190) },
	{ "pink", "Pink", 150, rgb(240, 90, 170) }, { "purple", "Purple", 150, rgb(120, 50, 200) },
})
local NEON = opts({
	{ "magenta", "Magenta", 0, rgb(255, 50, 170) }, { "cyan", "Cyan", 0, rgb(40, 240, 240) }, { "purple", "Purple", 200, rgb(150, 60, 255) },
	{ "green", "Toxic green", 200, rgb(80, 255, 80) }, { "red", "Red", 200, rgb(255, 40, 40) }, { "gold", "Gold", 200, rgb(255, 196, 40) },
	{ "white", "Ice white", 200, rgb(235, 245, 255) }, { "blue", "Electric blue", 200, rgb(40, 100, 255) },
})

C.Mods = {
	{ id = "paint", name = "Paint", cam = "front34", mods = {
		{ key = "paint", name = "Body colour", options = fromList(C.Paints), custom = C.CustomColorPrice, default = "candy_sunset" },
		{ key = "finish", name = "Paint finish", options = fromList(C.Finishes), default = "candy" },
		{ key = "paint2", name = "Two-tone roof", options = ROOF, custom = C.CustomColorPrice, default = "same" },
	} },
	{ id = "vinyls", name = "Vinyls", cam = "side", mods = {
		{ key = "art", name = "Livery", options = fromList(C.Art), default = "none" },
	} },
	{ id = "body", name = "Body kit", cam = "front34", mods = {
		{ key = "part_Top", name = "Roof", default = "", options = opts({ { "", "Hardtop" }, { "Landau", "Landau vinyl top + S-bars", 900 }, { "Vinyl", "Full vinyl top", 1100 }, { "Down", "Convertible, top down", 2500 } }) },
		{ key = "col_Top", name = "Vinyl / soft top colour", default = "black", custom = C.CustomColorPrice, options = opts({ { "black", "Black", 0, rgb(14, 14, 16) }, { "white", "White", 150, rgb(236, 234, 226) }, { "burgundy", "Burgundy", 200, rgb(90, 14, 26) }, { "tan", "Tan", 200, rgb(170, 128, 84) }, { "navy", "Navy", 200, rgb(20, 28, 70) } }) },
		{ key = "part_FrontBumper", name = "Front bumper", default = "Classic", options = opts({ { "Classic", "Classic chrome" }, { "Bullet", "Bullet guards", 900 }, { "Split", "Split with plate frame", 1000 }, { "Tube", "Tube push bar", 700 }, { "Shaved", "Shaved roll pan", 1200 } }) },
		{ key = "part_RearBumper", name = "Rear bumper", default = "Classic", options = opts({ { "Classic", "Classic chrome" }, { "Bullet", "Bullet guards", 900 }, { "Tube", "Tube bar", 700 }, { "Shaved", "Shaved roll pan", 1200 } }) },
		{ key = "fin_Bumpers", name = "Bumper finish", options = FIN, default = "chrome" },
		{ key = "part_Grille", name = "Grille", default = "Bars", options = opts({ { "Bars", "Classic bars" }, { "Eggcrate", "Eggcrate", 600 }, { "Waterfall", "Waterfall", 900 }, { "Mesh", "Diamond mesh", 700 }, { "Billet", "Billet bars", 800 } }) },
		{ key = "fin_Grille", name = "Grille finish", options = FIN, default = "chrome" },
		{ key = "part_Hood", name = "Hood", default = "Spear", options = opts({ { "Spear", "Chrome spear" }, { "", "Smooth (shaved)", 0 }, { "Louvers", "Louvers", 900 }, { "Cowl", "Cowl bulge", 1100 }, { "Scoop", "Scoop", 1300 } }) },
		{ key = "part_Ornament", name = "Hood ornament", default = "", options = opts({ { "", "None" }, { "Sun", "Sunburst", 400 }, { "Wings", "Wings", 500 }, { "Comet", "Comet", 450 } }) },
		{ key = "part_Spoiler", name = "Spoiler", default = "", options = opts({ { "", "None" }, { "Ducktail", "Ducktail", 700 }, { "Wing", "Wing", 1200 }, { "Fins", "Tail fins + fin lights", 1500 } }) },
		{ key = "part_Skirts", name = "Side skirts", default = "", options = opts({ { "", "None" }, { "Rocker", "Rocker panels", 700 }, { "Chrome", "Chrome rocker plates", 900 }, { "Fender", "Rear fender skirts", 1100 } }) },
		{ key = "part_Mirrors", name = "Side mirrors", default = "Bullet", options = opts({ { "Bullet", "Driver bullet" }, { "Dual", "Dual bullets", 300 }, { "Rect", "Square", 400 }, { "Stem", "Tall stems", 500 } }) },
		{ key = "fin_Mirrors", name = "Mirror finish", options = FIN, default = "chrome" },
		{ key = "part_Visor", name = "Sun visor", default = "", options = opts({ { "", "None" }, { "Chrome", "Chrome visor", 900 }, { "Body", "Painted visor", 800 } }) },
		{ key = "part_Exhaust", name = "Exhaust", default = "", options = opts({ { "", "Hidden" }, { "Dual", "Dual tips", 500 }, { "Turndown", "Turndowns", 400 }, { "Side", "Side pipes", 1200 } }) },
		{ key = "fin_Exhaust", name = "Exhaust finish", options = FIN_NO_PAINT, default = "chrome" },
		{ key = "part_Continental", name = "Continental kit", default = "", options = opts({ { "", "None" }, { "Kit", "Continental kit", 900 } }) },
		{ key = "fin_Trim", name = "Body trim finish", options = FIN, default = "chrome" },
	} },
	{ id = "wheels", name = "Wheels", cam = "wheel", mods = {
		{ key = "part_Rim", name = "Rims", default = "Wire100", options = opts({ { "Wire100", "Classic Wire 100-Spoke" }, { "Wire72", "Classic Wire 72-Spoke", 1200 }, { "Star", "Five Star", 900 }, { "Split", "Split Ten", 1000 }, { "Mesh", "Cross Mesh", 1000 }, { "Turbine", "Turbine", 1100 }, { "Disc", "Moon Disc", 800 }, { "Steelie", "Steelie + dog dish", 500 } }) },
		{ key = "fin_Spokes", name = "Spokes / face", options = FIN, default = "chrome" },
		{ key = "fin_Rim", name = "Rim lip + dish", options = FIN, default = "chrome" },
		{ key = "part_KO", name = "Knock-off", default = "Bar2", options = opts({ { "Bar2", "Two-bar spinner" }, { "Bar3", "Three-bar spinner", 300 }, { "Cap", "Smooth cap", 200 }, { "", "None" } }) },
		{ key = "fin_KO", name = "Knock-off finish", options = FIN, default = "chrome" },
		{ key = "part_Tire", name = "Tyres", default = "Classic", options = opts({ { "Classic", "Classic low profile" }, { "Balloon", "Fat balloon", 600 }, { "Skinny", "Skinny vintage", 500 } }) },
		{ key = "ww", name = "Whitewalls", default = "Thin", options = opts({ { "Thin", "Thin whitewall" }, { "Wide", "Wide whitewall", 300 }, { "Double", "Double stripe", 350 }, { "", "Blackwall" } }) },
		{ key = "col_Band", name = "Whitewall colour", default = "white", custom = C.CustomColorPrice, options = opts({ { "white", "White", 0, rgb(244, 244, 240) }, { "cream", "Cream", 150, rgb(238, 226, 196) }, { "red", "Red line", 250, rgb(200, 20, 30) }, { "blue", "Blue line", 250, rgb(30, 80, 220) }, { "gold", "Gold line", 300, rgb(226, 176, 60) } }) },
	} },
	{ id = "interior", name = "Interior", cam = "interior", mods = {
		{ key = "part_Seats", name = "Seats", default = "Rolls", options = opts({ { "Rolls", "Tuck-and-roll benches" }, { "Diamond", "Diamond tufted benches", 1100 }, { "SplitBench", "Split bench + armrest", 900 }, { "Buckets", "Bucket seats + console", 1300 } }) },
		{ key = "mat_Seat", name = "Seat material", default = "vinyl", options = opts({ { "vinyl", "Pleated vinyl" }, { "leather", "Leather", 600 }, { "velour", "Crushed velour", 500 }, { "suede", "Suede", 700 }, { "fabric", "Woven fabric", 300 } }) },
		{ key = "col_Seat", name = "Seat colour", default = "pearl", custom = C.CustomColorPrice, options = UPHOLSTERY },
		{ key = "col_Stitch", name = "Piping + stitching", default = "match", custom = C.CustomColorPrice, options = PIPING },
		{ key = "col_Carpet", name = "Carpet", default = "match", options = opts({ { "match", "Match the paint" }, { "black", "Black", 150, rgb(24, 24, 26) }, { "red", "Red", 150, rgb(120, 12, 22) }, { "grey", "Grey", 150, rgb(90, 90, 96) }, { "tan", "Tan", 150, rgb(150, 110, 70) }, { "white", "White shag", 300, rgb(236, 232, 222) }, { "purple", "Purple", 150, rgb(70, 20, 110) } }) },
		{ key = "part_Dash", name = "Dashboard", default = "Classic", options = opts({ { "Classic", "Classic chrome strip" }, { "Wood", "Wood panel", 900 }, { "Billet", "Billet slats", 1100 }, { "Digital", "Digital + neon", 1300 } }) },
		{ key = "col_Dash", name = "Dash colour", default = "black", custom = C.CustomColorPrice, options = opts({ { "black", "Black", 0, rgb(30, 30, 32) }, { "match", "Match the paint", 300 }, { "white", "White", 200, rgb(236, 232, 222) }, { "tan", "Tan", 200, rgb(160, 110, 66) }, { "red", "Red", 200, rgb(130, 14, 24) } }) },
		{ key = "gauge", name = "Speedometer", default = "classic", options = opts({ { "classic", "Classic white face" }, { "vintage", "Vintage cream", 300 }, { "chrome", "Chrome bezel", 400 }, { "neon", "Neon glow", 600 }, { "digital", "Digital readout", 700 } }) },
		{ key = "part_Steering", name = "Steering wheel", default = "Chain", options = opts({ { "Chain", "Chain link" }, { "Wood", "Wood rim", 700 }, { "Sport", "Sport three-spoke", 500 }, { "Banjo", "Banjo spokes", 600 }, { "Mini", "Mini chain", 900 } }) },
		{ key = "part_Shifter", name = "Shifter", default = "Column", options = opts({ { "Column", "Column shift" }, { "Chain", "Chain-link floor shifter", 400 }, { "Crystal", "Crystal knob", 600 }, { "WoodKnob", "Wood knob", 350 }, { "THandle", "T-handle", 450 } }) },
		{ key = "col_Wood", name = "Wood trim", default = "walnut", options = opts({ { "walnut", "Walnut", 0, rgb(96, 52, 26) }, { "cherry", "Cherry", 200, rgb(140, 50, 30) }, { "maple", "Maple", 200, rgb(200, 150, 90) }, { "ebony", "Ebony", 300, rgb(36, 26, 22) } }) },
		{ key = "fin_Cabin", name = "Interior chrome", options = FIN, default = "chrome" },
	} },
	{ id = "lights", name = "Lights + glass", cam = "front", mods = {
		{ key = "headlights", name = "Headlights", default = "warm", options = opts({ { "warm", "Warm halogen", 0, rgb(255, 238, 200) }, { "xenon", "Xenon white", 300, rgb(230, 240, 255) }, { "yellow", "Yellow", 300, rgb(255, 214, 80) }, { "ice", "Ice blue", 400, rgb(150, 200, 255) } }) },
		{ key = "taillights", name = "Taillights", default = "red", options = opts({ { "red", "Red", 0, rgb(220, 15, 15) }, { "smoke", "Smoked red", 300, rgb(110, 10, 14) }, { "candy", "Candy red", 300, rgb(255, 40, 70) }, { "amber", "Amber", 300, rgb(255, 130, 20) } }) },
		{ key = "tint", name = "Window tint", default = "none", options = opts({ { "none", "Clear", 0, rgb(70, 90, 105) }, { "light", "Light smoke", 200, rgb(50, 56, 62) }, { "dark", "Dark smoke", 300, rgb(26, 28, 32) }, { "limo", "Limo", 400, rgb(8, 8, 10) }, { "blue", "Blue mirror", 400, rgb(40, 80, 140) }, { "purple", "Purple haze", 400, rgb(70, 30, 100) } }) },
		{ key = "part_Glow", name = "Underglow", default = "", options = opts({ { "", "Off" }, { "On", "Neon underglow", 1200 } }) },
		{ key = "col_Neon", name = "Neon colour (underglow, dash, show trunk)", default = "magenta", custom = C.CustomColorPrice, options = NEON },
	} },
	{ id = "hydraulics", name = "Hydraulics", cam = "rear34", mods = {
		{ key = "susp", name = "Suspension", options = fromList(C.Suspension), default = "stock" },
		{ key = "part_Trunk", name = "Trunk setup", default = "", options = opts({ { "", "Empty trunk" }, { "Street", "Street: 2 pumps, 6 batteries", 600 }, { "Show", "Show: 4 upright pumps, mirror floor", 1500 } }) },
		{ key = "fin_Trunk", name = "Pump finish", options = FIN_NO_PAINT, default = "chrome" },
	} },
	{ id = "extras", name = "Extras", cam = "rear34", mods = {
		{ key = "engine", name = "Engine", options = fromList(C.Engines), default = "stock" },
		{ key = "part_Dice", name = "Fuzzy dice", default = "", options = opts({ { "", "None" }, { "On", "Fuzzy dice", 150 } }) },
		{ key = "col_Fur", name = "Dice colour", default = "white", options = opts({ { "white", "White", 0, rgb(245, 245, 245) }, { "pink", "Pink", 0, rgb(250, 150, 200) }, { "red", "Red", 0, rgb(210, 20, 30) }, { "black", "Black", 0, rgb(26, 26, 28) }, { "teal", "Teal", 0, rgb(30, 200, 200) } }) },
		{ key = "part_Plaque", name = "Car club plaque (rear window)", default = "", options = opts({ { "", "None" }, { "Chain", "Chain plaque", 400 } }) },
		{ key = "plaque", name = "Plaque name", default = "neoncoast", options = opts({ { "neoncoast", "NEON COAST" }, { "lowslow", "LOW & SLOW" }, { "boulevard", "BOULEVARD KINGS" }, { "sunset", "SUNSET CRUISERS" }, { "candy", "CANDY CREW" }, { "midnight", "MIDNIGHT RIDERS" }, { "oldies", "OLDIES CLUB" } }) },
	} },
}
-- speedometer faces: face colour, tick/text colour, needle colour, glows?
C.Gauges = {
	classic = { face = rgb(240, 238, 230), ink = rgb(20, 20, 24), needle = rgb(220, 30, 30) },
	vintage = { face = rgb(236, 220, 180), ink = rgb(70, 40, 20), needle = rgb(160, 20, 20) },
	chrome = { face = rgb(30, 30, 34), ink = rgb(225, 228, 235), needle = rgb(255, 200, 60), bezel = true },
	neon = { face = rgb(8, 8, 16), ink = rgb(40, 240, 240), needle = rgb(255, 50, 170), glow = true },
	digital = { face = rgb(4, 10, 6), ink = rgb(80, 255, 120), needle = rgb(80, 255, 120), glow = true, digital = true },
}
C.SeatMaterials = {
	vinyl = { Enum.Material.SmoothPlastic, 0.08 }, leather = { Enum.Material.Leather, 0 }, velour = { Enum.Material.Fabric, 0 },
	suede = { Enum.Material.Sand, 0 }, fabric = { Enum.Material.Fabric, 0 },
}

-- lookups
C.ModByKey, C.OptionOf = {}, {}
for _, cat in C.Mods do
	for _, m in cat.mods do
		C.ModByKey[m.key] = m
		C.OptionOf[m.key] = {}
		for _, o in m.options do
			C.OptionOf[m.key][o.id] = o
		end
	end
end
C.StarterLook = {}
for key, m in C.ModByKey do
	C.StarterLook[key] = m.default
end

C.ById = {}
for _, listName in { "Paints", "Finishes", "Art", "Suspension", "TrimFinishes", "Engines" } do
	C.ById[listName] = {}
	for _, it in C[listName] do
		C.ById[listName][it.id] = it
	end
end

function C.Paint(id)
	return C.ById.Paints[id] or C.Paints[1]
end

function C.Susp(id)
	return C.ById.Suspension[id] or C.Suspension[1]
end

function C.Engine(id)
	return C.ById.Engines[id] or C.Engines[1]
end

-- "c:RRGGBB" -> Color3 (nil if it isn't one)
function C.CustomColor(v)
	if type(v) ~= "string" then
		return nil
	end
	local hex = v:match("^c:(%x%x%x%x%x%x)$")
	return hex and Color3.fromHex(hex) or nil
end

function C.ToCustom(c)
	return "c:" .. c:ToHex():upper()
end

-- the colour a colour mod's value stands for (option colour or custom), or nil
function C.ColorOf(key, value)
	local o = C.OptionOf[key] and C.OptionOf[key][value]
	return (o and o.color) or C.CustomColor(value)
end

-- older saves: { paint, finish, art, wheels, whitewall, susp, continental, trunkSetup }
local OLD_WHEELS = { wire_gold = { "gold", "gold" }, wire_gold_hub = { "chrome", "gold" }, wire_color = { "paint", "chrome" }, wire_black = { "black", "chrome" } }

-- a safe, complete look from anything a client (or an old save) sends
function C.CleanLook(look)
	local out = table.clone(C.StarterLook)
	if type(look) ~= "table" then
		return out
	end
	if look.wheels ~= nil or look.whitewall ~= nil then -- migrate the first version's keys
		local w = OLD_WHEELS[look.wheels]
		if w then
			out.fin_Spokes, out.fin_KO = w[1], w[2]
		end
		out.ww = look.whitewall == false and "" or "Thin"
		out.part_Continental = look.continental == true and "Kit" or ""
		out.part_Trunk = look.trunkSetup == true and "Street" or ""
	end
	for key, m in C.ModByKey do
		local v = look[key]
		if type(v) == "string" and (C.OptionOf[key][v] or (m.custom and C.CustomColor(v))) then
			out[key] = v
		end
	end
	return out
end

-- old unlock tags ("Paints:id", "Extra:whitewall") -> the new "key=value" tags
function C.MigrateUnlocked(unlocked)
	local out = {}
	local LIST = { Paints = "paint", Finishes = "finish", Art = "art", Suspension = "susp" }
	for tag, v in (type(unlocked) == "table" and unlocked or {}) do
		local list, id = tostring(tag):match("^(%a+):(.+)$")
		if list and LIST[list] then
			out[LIST[list] .. "=" .. id] = true
		elseif list == "Wheels" and OLD_WHEELS[id] then
			out["fin_Spokes=" .. OLD_WHEELS[id][1]] = true
			out["fin_KO=" .. OLD_WHEELS[id][2]] = true
		elseif tag == "Extra:whitewall" then
			out["ww=Thin"] = true
		elseif tag == "Extra:continental" then
			out["part_Continental=Kit"] = true
		elseif tag == "Extra:trunkSetup" then
			out["part_Trunk=Street"] = true
		elseif not list then
			out[tag] = v
		end
	end
	return out
end

function C.PriceOf(key, value)
	local m = C.ModByKey[key]
	if not m then
		return 0
	end
	local o = C.OptionOf[key][value]
	if o then
		return o.price or 0
	end
	return (m.custom and C.CustomColor(value)) and m.custom or 0
end

-- what changing `saved` into `look` costs, given what's already unlocked; returns total, { tag = price }
function C.Quote(saved, look, unlocked)
	local total, items = 0, {}
	for key in C.ModByKey do
		local v = look[key]
		if v ~= saved[key] then
			local tag = key .. "=" .. v
			local price = C.PriceOf(key, v)
			if price > 0 and not unlocked[tag] then
				total += price
				items[tag] = price
			end
		end
	end
	return total, items
end

-- inches shown on the hop board (1.15 studs per foot)
function C.Inches(studs)
	return math.floor(studs / 1.15 * 12 + 0.5)
end

return C
