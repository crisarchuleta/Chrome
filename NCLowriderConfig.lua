--!nonstrict
-- NCLowriderConfig (ModuleScript, ReplicatedStorage): everything you can buy at Low & Slow Kustoms, and the tuning
-- numbers for driving and the hydraulics. All names are original (no real brands). Prices are in the game's Cash.
-- Edit freely: the shop UI, the server checks and the car all read from here.
local C = {}

C.CarName = "Royale Lowrider"
C.CarPrice = 2500
C.StarterLook = {
	paint = "candy_sunset", finish = "candy", art = "none", wheels = "wire_chrome", whitewall = true, susp = "stock",
	continental = false,
	trunkSetup = false, plate = "",
}

-- candy paint colours
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
	{ id = "pearl_white", name = "Pearl White", color = Color3.fromRGB(240, 238, 230), price = 600 },
	{ id = "midnight", name = "Midnight Black", color = Color3.fromRGB(14, 14, 18), price = 600 },
	{ id = "baby_blue", name = "Baby Blue", color = Color3.fromRGB(130, 180, 230), price = 400 },
	{ id = "mint", name = "Mint Cream", color = Color3.fromRGB(160, 230, 200), price = 400 },
}

-- how the paint is laid down (Roblox material + shine)
C.Finishes = {
	{ id = "candy", name = "Candy gloss", material = Enum.Material.SmoothPlastic, reflectance = 0.22, price = 0 },
	{ id = "flake", name = "Metal flake", material = Enum.Material.Foil, reflectance = 0.12, price = 700 },
	{ id = "pearl", name = "Pearl", material = Enum.Material.SmoothPlastic, reflectance = 0.1, price = 500 },
	{ id = "satin", name = "Satin", material = Enum.Material.Plastic, reflectance = 0, price = 300 },
}

-- vinyls: real decal artwork printed flush on the paint (images from make_lowrider_vinyls.py, lowrider_vinyls/).
-- Each livery prints an image on some of the panels (hood, side, trunk, roof); see NCLowriderData.Car.Vinyls.
-- Clear parts of an image show the candy paint underneath, so every livery works with every paint colour.
C.Art = {
	{ id = "none", name = "Clean (no vinyls)", price = 0 },
	{ id = "pinstripe", name = "Gold pinstripe scrolls", price = 500 },
	{ id = "flames", name = "Hot flames with blue pinstripe", price = 1100 },
	{ id = "flames_teal", name = "Ice flames with purple pinstripe", price = 1100 },
	{ id = "patterns", name = "Patterns, lace and fades", price = 1400 },
	{ id = "purple_lace", name = "Purple lace and fades", price = 1400 },
	{ id = "mural", name = "Sunset mural on the trunk + pinstripes", price = 1600 },
	{ id = "showcar", name = "Show car: patterns, lace roof and mural", price = 2400 },
}
-- Decal image ids. Importing LowriderVinyls.glb and running NCLowriderKit.Prepare on it fills these in by itself;
-- you can also upload the PNGs yourself and paste ids here, e.g. flames_side = "rbxassetid://123456".
C.VinylIds = {}

-- wheels: "Classic Wire 100-Spoke" in different finishes
C.Wheels = {
	{ id = "wire_chrome", name = "Classic Wire 100-Spoke, chrome", spokes = "chrome", hub = "chrome", price = 0 },
	{ id = "wire_gold", name = "Classic Wire 100-Spoke, all gold", spokes = "gold", hub = "gold", price = 1500 },
	{ id = "wire_gold_hub", name = "Classic Wire 100-Spoke, gold hub + nipples", spokes = "chrome", hub = "gold", price = 800 },
	{ id = "wire_color", name = "Classic Wire 100-Spoke, colour-matched spokes", spokes = "paint", hub = "chrome", price = 1000 },
	{ id = "wire_black", name = "Classic Wire 100-Spoke, black chrome", spokes = "black", hub = "chrome", price = 900 },
}
C.WhitewallPrice = 150
C.WheelFinish = {
	chrome = { Enum.Material.Metal, Color3.fromRGB(225, 228, 235), 0.45 },
	gold = { Enum.Material.Metal, Color3.fromRGB(232, 182, 64), 0.4 },
	black = { Enum.Material.Metal, Color3.fromRGB(40, 40, 46), 0.35 },
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
C.ContinentalPrice = 900
C.TrunkSetupPrice = 600

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

C.ById = {}
for _, listName in { "Paints", "Finishes", "Art", "Wheels", "Suspension" } do
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

-- inches shown on the hop board (1.15 studs per foot)
function C.Inches(studs)
	return math.floor(studs / 1.15 * 12 + 0.5)
end

return C
