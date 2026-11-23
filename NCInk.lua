--!nonstrict
-- NCInk (ModuleScript in ReplicatedStorage): real tattoo ink for the MakeHuman bodies.
--
-- How it works (same idea as the car vinyls): every body has 13 thin "ink layer" MeshParts that sit 1 mm above the
-- skin with the exact same bone weights, so they bend with the body and look printed on. A tattoo is just a
-- transparent PNG set as the layer's TextureID. Clothes sit above the layer, so anything covered by clothes hides
-- the ink with no extra code. Nothing is ever printed on the torso.
--
-- Pieces:
--   NC_Ink_<Body>.fbx      the 13 layers (Ink_LeftUpperArm ... Ink_Face) skinned to that body's rig. Import each
--                          into ReplicatedStorage.NCInkRigs as a Model named <Body> (e.g. "Male_Average").
--   NCInkSwatches_1.glb + NCInkSwatches_2.glb      every tattoo PNG on its own plane. Import it once into Workspace, run
--                          NCInkSetup.Prepare(model) from the command bar: it saves each texture's asset id into
--                          ReplicatedStorage.NCInkIds (StringValues named after the file) and you can delete the model.
--   NCInkCatalog           the tattoo list (generated from ink_catalog.json).
--
-- A look's ink is a table:
--   { L = { upper = id, lower = id, hand = id, leg = id }, R = { ... }, neck = id, face = id }
-- A full sleeve (zone "full") fills both upper and lower on that arm; a leg sleeve fills the thigh and calf.
local RS = game:GetService("ReplicatedStorage")
local Catalog = require(RS:WaitForChild("NCInkCatalog"))

local Ink = {}

-- which layers each area/zone prints on (layer names without the side)
Ink.ZONES = {
	Arm = { upper = { "UpperArm" }, lower = { "LowerArm" }, full = { "UpperArm", "LowerArm" } },
	Leg = { lower = { "LowerLeg" }, full = { "UpperLeg", "LowerLeg" } },
	Hand = { hand = { "Hand" } },
	Neck = { neck = { "NeckHead", "NeckUpperTorso" } },
	Face = { face = { "Face" } },
}
Ink.LAYERS = {
	"Ink_LeftUpperArm", "Ink_LeftLowerArm", "Ink_LeftHand", "Ink_LeftUpperLeg", "Ink_LeftLowerLeg",
	"Ink_RightUpperArm", "Ink_RightLowerArm", "Ink_RightHand", "Ink_RightUpperLeg", "Ink_RightLowerLeg",
	"Ink_NeckHead", "Ink_NeckUpperTorso", "Ink_Face",
}

local function textureId(file)
	local ids = RS:FindFirstChild("NCInkIds")
	local v = ids and ids:FindFirstChild(file)
	return v and v.Value or ""
end

-- clone the body's ink layers into a character (call once after the body is built or swapped).
-- Skinned MeshParts bind to Bones by name inside the same Model, so the layers follow the character's rig.
function Ink.Attach(character, bodyName)
	local rigs = RS:FindFirstChild("NCInkRigs")
	local src = rigs and rigs:FindFirstChild(bodyName)
	if not src then
		warn("[NCInk] no ink layers for body", bodyName)
		return false
	end
	local folder = character:FindFirstChild("NCInk")
	if folder then
		folder:Destroy()
	end
	folder = Instance.new("Model")
	folder.Name = "NCInk"
	for _, name in ipairs(Ink.LAYERS) do
		local mp = src:FindFirstChild(name, true)
		if mp and mp:IsA("MeshPart") then
			local c = mp:Clone()
			c.Anchored = false
			c.CanCollide = false
			c.CanQuery = false
			c.CanTouch = false
			c.Massless = true
			c.CastShadow = false
			c.TextureID = ""
			c.Transparency = 1
			c.Parent = folder
			-- keep the layer welded to its body part too, so it never drifts if skinning is off
			local partName = name:gsub("^Ink_", ""):gsub("^Neck", "")
			local part = character:FindFirstChild(partName == "Face" and "Head" or partName)
			if part and part:IsA("BasePart") then
				local w = Instance.new("WeldConstraint")
				w.Part0, w.Part1 = part, c
				w.Parent = c
			end
		end
	end
	folder.Parent = character
	return true
end

-- the texture each layer gets for an ink table (layer name -> file name)
function Ink.Resolve(ink)
	local out = {}
	local function put(item, side)
		if not item then
			return
		end
		local zones = Ink.ZONES[item.area] and Ink.ZONES[item.area][item.zone]
		if not zones then
			return
		end
		local file = item.files[side] or item.files.C
		for _, z in ipairs(zones) do
			local layer = (side == "L" and "Ink_Left" or side == "R" and "Ink_Right" or "Ink_") .. z
			out[layer] = file
		end
	end
	ink = ink or {}
	for _, side in ipairs({ "L", "R" }) do
		local s = ink[side] or {}
		local up, lo = Catalog.BY_ID[s.upper or ""], Catalog.BY_ID[s.lower or ""]
		-- a full sleeve wins both halves of the arm
		if up and up.zone == "full" then
			put(up, side)
		elseif lo and lo.zone == "full" then
			put(lo, side)
		else
			put(up, side)
			put(lo, side)
		end
		put(Catalog.BY_ID[s.hand or ""], side)
		put(Catalog.BY_ID[s.leg or ""], side)
	end
	put(Catalog.BY_ID[ink.neck or ""], "C")
	put(Catalog.BY_ID[ink.face or ""], "C")
	return out
end

-- show the ink on a character that already has its layers attached
function Ink.Apply(character, ink)
	local folder = character:FindFirstChild("NCInk")
	if not folder then
		return
	end
	local want = Ink.Resolve(ink)
	for _, name in ipairs(Ink.LAYERS) do
		local mp = folder:FindFirstChild(name)
		if mp then
			local file = want[name]
			local id = file and textureId(file) or ""
			mp.TextureID = id
			mp.Transparency = (id ~= "") and 0 or 1
		end
	end
end

-- server check: is this a valid ink table? (only catalog ids, right area for each spot)
function Ink.Validate(ink)
	if type(ink) ~= "table" then
		return false
	end
	local ok = { upper = "Arm", lower = "Arm", hand = "Hand", leg = "Leg" }
	for _, side in ipairs({ "L", "R" }) do
		local s = ink[side]
		if s ~= nil then
			if type(s) ~= "table" then
				return false
			end
			for k, id in pairs(s) do
				local it = Catalog.BY_ID[id]
				if not ok[k] or not it or it.area ~= ok[k] then
					return false
				end
				if k == "upper" and it.zone == "lower" or k == "lower" and it.zone == "upper" then
					return false
				end
			end
		end
	end
	for k, area in pairs({ neck = "Neck", face = "Face" }) do
		if ink[k] ~= nil then
			local it = Catalog.BY_ID[ink[k]]
			if not it or it.area ~= area then
				return false
			end
		end
	end
	return true
end

-- total price of an ink table (each tattoo counted once, even if it covers two layers)
function Ink.Price(ink)
	local seen, total = {}, 0
	local function add(id)
		local it = id and Catalog.BY_ID[id]
		if it and not seen[id] then
			seen[id] = true
			total += it.price
		end
	end
	for _, side in ipairs({ "L", "R" }) do
		for _, id in pairs((ink or {})[side] or {}) do
			add(id)
		end
	end
	add((ink or {}).neck)
	add((ink or {}).face)
	return total
end

return Ink
