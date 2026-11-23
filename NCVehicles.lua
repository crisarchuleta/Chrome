--!nonstrict
-- NCVehicles (ModuleScript, ReplicatedStorage): every drivable vehicle in Neon Coast. All of them are sold, saved
-- and customized at Low & Slow Kustoms with the same tuning menu. The menu shows whatever parts a vehicle's GLB has
-- (its data module's Car.Options / Wheel.Options), so adding a vehicle needs no menu or shop code:
--   1. build it in Blender (build_vehicles.py makes <id>.glb, <id>Vinyls.glb and NCVehicleData_<id>.lua)
--   2. add a line below, put the data module in ReplicatedStorage
--   3. import the GLBs in Studio and run NCLowriderKit.Prepare on them
-- All names are original (no real makes or models).
local RS = game:GetService("ReplicatedStorage")

local V = {}
V.Default = "royale"

-- drive = changes to NCLowriderConfig.Drive for this vehicle; suspensions = the kits it can run;
-- defaults = its stock parts (look keys -> option ids) where they differ from the lowrider's
V.List = {
	{
		id = "royale", name = "Royale Lowrider", price = 2500, data = "NCLowriderData", prefix = "Lowrider", class = "lowrider",
		blurb = "Long, low two-door hardtop. The hydraulics king: hops, three-wheel, dance.",
	},
	-- the first new builds (picked 2026-11-23)
	{
		id = "Ironclad", name = "Ironclad SS", price = 4000, class = "muscle",
		blurb = "Big-block two-door muscle coupe. Fast in a straight line, loud everywhere.",
		drive = { TopSpeed = 82, Accel = 32, RearGrip = 8 },
		defaults = { part_FrontBumper = "Classic", part_RearBumper = "Classic", part_Grille = "Bars", part_Headlights = "Dual", part_Taillights = "Bar",
			part_Mirrors = "Rect", part_Hood = "Scoop", part_Exhaust = "Dual", part_Seats = "Buckets", part_Doors = "Smooth", part_Steering = "Wood",
			part_Shifter = "THandle", part_Rim = "Steelie", part_KO = "Cap", part_Tire = "Classic", ww = "" },
	},
	{
		id = "IronhornTRX", name = "Ironhorn TRX", price = 3500, class = "pickup",
		blurb = "Full-size pickup. Lay it on bags or lift it up.",
		drive = { TopSpeed = 68, Accel = 24, SpringSag = 0.32 },
		defaults = { part_FrontBumper = "Classic", part_RearBumper = "Classic", part_Grille = "Billet", part_Headlights = "Square", part_Taillights = "Bar",
			part_Mirrors = "Rect", part_Hood = "", part_Skirts = "Steps", part_Seats = "Buckets", part_Doors = "Smooth", part_Steering = "Sport",
			part_Shifter = "THandle", part_Rim = "Star", part_KO = "Cap", part_Tire = "Offroad", ww = "" },
	},
	{
		id = "KestrelGT", name = "Kestrel GT", price = 9000, class = "sports",
		blurb = "Low sports coupe. The quickest thing on the coast.",
		drive = { TopSpeed = 98, Accel = 40, Grip = 14, RearGrip = 12, SteerMax = 32 },
		suspensions = { "stock", "bags" },
		defaults = { part_FrontBumper = "Sport", part_RearBumper = "Sport", part_Grille = "Mesh", part_Headlights = "Slim", part_Taillights = "Slim",
			part_Mirrors = "Sport", part_Hood = "", part_Spoiler = "Ducktail", part_Exhaust = "Quad", part_Seats = "Racing", part_Doors = "Smooth",
			part_Dash = "Digital", part_Steering = "Sport", part_Shifter = "THandle", part_Rim = "Split", part_KO = "Cap", part_Tire = "Classic", ww = "" },
	},
	{
		id = "Dunewalker", name = "Dunewalker", price = 5500, class = "suv",
		blurb = "Boxy four-door off-roader with room for the whole crew.",
		drive = { TopSpeed = 70, Accel = 25, SpringSag = 0.36, Damping = 0.5 },
		defaults = { part_FrontBumper = "Stock", part_RearBumper = "Stock", part_Grille = "Eggcrate", part_Headlights = "Square", part_Taillights = "Bar",
			part_Mirrors = "Rect", part_Hood = "", part_Top = "Rack", part_Seats = "Buckets", part_Doors = "Smooth", part_Steering = "Sport",
			part_Shifter = "THandle", part_Rim = "Steelie", part_KO = "Cap", part_Tire = "Offroad", ww = "" },
	},
	-- the rest of the city's lineup, rebuilt on this system under their existing names (CarTemplates)
	{
		id = "VantorStrada", name = "Vantor Strada", price = 3000, class = "sedan", blurb = "Everyday four-door sedan.",
		drive = { TopSpeed = 72, Accel = 26 },
		defaults = { part_FrontBumper = "Classic", part_RearBumper = "Classic", part_Grille = "Bars", part_Headlights = "Dual", part_Taillights = "Bar",
			part_Mirrors = "Rect", part_Hood = "", part_Exhaust = "", part_Seats = "Buckets", part_Doors = "Smooth",
			part_Dash = "Classic", part_Steering = "Wood", part_Shifter = "THandle", part_Rim = "Split", part_KO = "Cap",
			part_Tire = "Classic", ww = "" },
	},
	{
		id = "AurexHalcyon", name = "Aurex Halcyon", price = 6000, class = "luxury", blurb = "Smooth luxury sedan.",
		drive = { TopSpeed = 80, Accel = 28, Damping = 0.5 },
		defaults = { part_FrontBumper = "Classic", part_RearBumper = "Classic", part_Grille = "Billet", part_Headlights = "Dual", part_Taillights = "Bar",
			part_Mirrors = "Rect", part_Hood = "", part_Exhaust = "Dual", part_Seats = "Rolls", part_Doors = "Smooth",
			part_Dash = "Wood", part_Steering = "Wood", part_Shifter = "THandle", part_Rim = "Star", part_KO = "Cap",
			part_Tire = "Classic", ww = "" },
	},
	{
		id = "KazumiK2", name = "Kazumi K2", price = 2800, class = "hatch", blurb = "Small, light hatchback.",
		drive = { TopSpeed = 66, Accel = 27, Grip = 12, SteerMax = 34 },
		defaults = { part_FrontBumper = "Sport", part_RearBumper = "Sport", part_Grille = "Eggcrate", part_Headlights = "Square", part_Taillights = "Slim",
			part_Mirrors = "Sport", part_Hood = "", part_Spoiler = "", part_Exhaust = "Dual", part_Seats = "Buckets",
			part_Doors = "Smooth", part_Dash = "Classic", part_Steering = "Sport", part_Shifter = "THandle", part_Rim = "Steelie",
			part_KO = "Cap", part_Tire = "Classic", ww = "" },
	},
	{
		id = "KazeRS8", name = "Kaze RS8", price = 7500, class = "sports", blurb = "Sharp sports coupe.", suspensions = { "stock", "bags" },
		drive = { TopSpeed = 94, Accel = 38, Grip = 13, RearGrip = 11, SteerMax = 32 },
		defaults = { part_FrontBumper = "Sport", part_RearBumper = "Sport", part_Grille = "Mesh", part_Headlights = "Slim", part_Taillights = "Slim",
			part_Mirrors = "Sport", part_Hood = "", part_Spoiler = "Wing", part_Exhaust = "Quad", part_Seats = "Racing",
			part_Doors = "Smooth", part_Dash = "Digital", part_Steering = "Sport", part_Shifter = "THandle", part_Rim = "Mesh",
			part_KO = "Cap", part_Tire = "Classic", ww = "" },
	},
	{
		id = "HayatoTypeZ", name = "Hayato Type Z", price = 7000, class = "jdm", blurb = "Street-tuned sports car.", suspensions = { "stock", "bags" },
		drive = { TopSpeed = 92, Accel = 37, Grip = 13, RearGrip = 10, SteerMax = 33 },
		defaults = { part_FrontBumper = "Sport", part_RearBumper = "Sport", part_Grille = "Mesh", part_Headlights = "Quad", part_Taillights = "Slim",
			part_Mirrors = "Sport", part_Hood = "", part_Spoiler = "Ducktail", part_Exhaust = "Quad", part_Seats = "Racing",
			part_Doors = "Smooth", part_Dash = "Digital", part_Steering = "Sport", part_Shifter = "THandle", part_Rim = "Turbine",
			part_KO = "Cap", part_Tire = "Classic", ww = "" },
	},
	{
		id = "NorrbyDL84", name = "Norrby DL84", price = 2500, class = "boxy", blurb = "Boxy 80s sedan. Built like a brick.",
		drive = { TopSpeed = 68, Accel = 23 },
		defaults = { part_FrontBumper = "Classic", part_RearBumper = "Classic", part_Grille = "Bars", part_Headlights = "Square", part_Taillights = "Bar",
			part_Mirrors = "Rect", part_Hood = "", part_Exhaust = "", part_Seats = "Buckets", part_Doors = "Smooth",
			part_Dash = "Classic", part_Steering = "Sport", part_Shifter = "THandle", part_Rim = "Steelie", part_KO = "Cap",
			part_Tire = "Classic", ww = "" },
	},
	{
		id = "MarloweDeville61", name = "Marlowe 61", price = 4500, class = "cruiser", blurb = "Big 60s cruiser with fins.",
		drive = { TopSpeed = 74, Accel = 24, Damping = 0.45 },
		defaults = { part_FrontBumper = "Classic", part_RearBumper = "Classic", part_Grille = "Bars", part_Headlights = "Dual", part_Taillights = "Bar",
			part_Mirrors = "Rect", part_Hood = "", part_Exhaust = "Dual", part_Seats = "Rolls", part_Doors = "Rolls",
			part_Dash = "Classic", part_Steering = "Chain", part_Shifter = "THandle", part_Rim = "Wire100", part_KO = "Bar2",
			part_Tire = "Classic", ww = "Thin" },
	},
	{
		id = "DusterRidge54", name = "Duster Ridge 54", price = 3200, class = "pickup50s", blurb = "Rounded 50s pickup.",
		drive = { TopSpeed = 66, Accel = 23, SpringSag = 0.3 },
		defaults = { part_FrontBumper = "Classic", part_RearBumper = "Classic", part_Grille = "Bars", part_Headlights = "Dual", part_Taillights = "Bar",
			part_Mirrors = "Rect", part_Hood = "", part_Skirts = "Steps", part_Seats = "Buckets", part_Doors = "Smooth",
			part_Dash = "Classic", part_Steering = "Sport", part_Shifter = "THandle", part_Rim = "Steelie", part_KO = "Cap",
			part_Tire = "Classic", ww = "" },
	},
	{
		id = "ShorelineSix", name = "Shoreline Six", price = 3800, class = "van", blurb = "Six-seat beach van.",
		drive = { TopSpeed = 64, Accel = 21, SpringSag = 0.34 },
		defaults = { part_FrontBumper = "Stock", part_RearBumper = "Stock", part_Grille = "Eggcrate", part_Headlights = "Square", part_Taillights = "Bar",
			part_Mirrors = "Rect", part_Hood = "", part_Top = "Rack", part_Seats = "Buckets", part_Doors = "Smooth",
			part_Dash = "Classic", part_Steering = "Sport", part_Shifter = "THandle", part_Rim = "Steelie", part_KO = "Cap",
			part_Tire = "Offroad", ww = "" },
	},
	{ id = "GeneralsCart", name = "Generals Cart", price = 1200, class = "cart", blurb = "Open-top cart for getting around." },
	{
		id = "PoliceCruiser", name = "Police Cruiser", price = 0, class = "boxy", police = true, blurb = "Coast Patrol cruiser.",
		drive = { TopSpeed = 86, Accel = 32 },
		defaults = { part_FrontBumper = "Classic", part_RearBumper = "Classic", part_Grille = "Bars", part_Headlights = "Dual", part_Taillights = "Bar",
			part_Mirrors = "Rect", part_Hood = "", part_Exhaust = "", part_Seats = "Buckets", part_Doors = "Smooth",
			part_Dash = "Classic", part_Steering = "Sport", part_Shifter = "THandle", part_Rim = "Steelie", part_KO = "Cap",
			part_Tire = "Classic", ww = "" },
	},
	{
		id = "ArmoredTruck", name = "Coast Patrol Armored Truck", price = 0, class = "armored", police = true, blurb = "Coast Patrol armored truck.",
		drive = { TopSpeed = 62, Accel = 18, SpringSag = 0.3, Damping = 0.55 },
		defaults = { part_FrontBumper = "Bull", part_RearBumper = "Stock", part_Grille = "Eggcrate", part_Headlights = "Square", part_Taillights = "Bar",
			part_Mirrors = "Rect", part_Hood = "", part_Top = "", part_Seats = "Buckets", part_Doors = "Smooth",
			part_Dash = "Classic", part_Steering = "Sport", part_Shifter = "THandle", part_Rim = "Steelie", part_KO = "Cap",
			part_Tire = "Offroad", ww = "" },
	},
	-- bikes need their own riding physics; listed so they keep their names when they're rebuilt
	{ id = "DirtBike", name = "Dirt Bike", price = 2000, class = "bike", bike = true, blurb = "Light dirt bike." },
	{ id = "SportBike", name = "Sport Bike", price = 6500, class = "bike", bike = true, blurb = "Fast sport bike." },
}
-- data module + GLB prefix default to the id: NCVehicleData_<id>, <id>.glb with pieces <id>_* / <id>Wheel_*
for _, v in V.List do
	v.data = v.data or ("NCVehicleData_" .. v.id)
	v.prefix = v.prefix or v.id
end

V.ById, V.ByPrefix = {}, {}
for _, v in V.List do
	V.ById[v.id] = v
	V.ByPrefix[v.prefix] = v
end

function V.Get(id)
	return V.ById[id] or V.ById[V.Default]
end

-- the vehicle's generated data module, or nil if it isn't in ReplicatedStorage yet
local cache = {}
function V.Data(id)
	local v = V.Get(id)
	if cache[v.id] == nil then
		local m = RS:FindFirstChild(v.data)
		cache[v.id] = m and require(m) or false
	end
	return cache[v.id] or nil
end

-- vehicles that can actually be sold (their data module is installed; police vehicles aren't for sale)
function V.Available()
	local out = {}
	for _, v in V.List do
		if V.Data(v.id) and not v.police then
			table.insert(out, v)
		end
	end
	return out
end

function V.Of(car)
	return car and car:GetAttribute("Vehicle") or V.Default
end

-- driving numbers for a vehicle: Config.Drive with its changes on top
function V.Drive(id, base)
	local v = V.Get(id)
	local out = table.clone(base)
	for k, x in (v.drive or {}) do
		out[k] = x
	end
	return out
end

return V
