--!nonstrict
-- NCLowriderKit (ModuleScript, ReplicatedStorage): builds the lowrider and the Low & Slow Kustoms shop, and paints a
-- car with a player's look. Used by LowriderService (server) and LowriderClient (live preview in the shop).
--
-- Meshes: build_lowrider.py makes Lowrider.glb (car + one wheel) and LowSlowShop.glb. After importing them in
-- Studio, run once in the command bar:
--   require(game.ReplicatedStorage.NCLowriderKit).Prepare(workspace.Lowrider)      -- the imported car model
--   require(game.ReplicatedStorage.NCLowriderKit).Prepare(workspace.LowSlowShop)   -- the imported shop model
-- That files the pieces under ReplicatedStorage.LowriderAssets (Car, Wheel, Shop). Until then the kit builds a
-- part-made car and shop in the same colours, so everything works straight away.
--
-- Car model layout (same for mesh and part versions):
--   Model "Lowrider" (PrimaryPart = Chassis)
--     Chassis       invisible collision hull, the only part with mass; origin on the ground between the axles,
--                   front = -Z. Holds the CoM attachment, the VectorForce "Drive" and the Torque "Turn".
--     Cabin         invisible hull for the greenhouse (welded)
--     Visual        every body piece, welded, massless, no collision; each has attribute Role (Body, Chrome, ...)
--     Lid           the trunk lid pieces (+ mural / lid pinstripe), welded by "LidHinge" (server opens it)
--     W_FL/W_FR/W_RL/W_RR   wheel models; their weld (Hub.WheelWeld) is posed every frame by each client
--     DriveSeat (VehicleSeat), Seat_Passenger, Seat_RearL, Seat_RearR
local RS = game:GetService("ReplicatedStorage")
local Data = require(RS:WaitForChild("NCLowriderData"))
local Config = require(RS:WaitForChild("NCLowriderConfig"))

local Kit = {}
Kit.FixYaw = { Car = 0, Shop = 0 } -- degrees, if an import comes in turned

local function v3(t)
	return Vector3.new(t[1], t[2], t[3])
end

local function worldMin(parts)
	local mn = Vector3.one * math.huge
	for _, p in parts do
		local h = p.Size / 2
		for _, s in { Vector3.new(1, 1, 1), Vector3.new(1, 1, -1), Vector3.new(1, -1, 1), Vector3.new(1, -1, -1), Vector3.new(-1, 1, 1), Vector3.new(-1, 1, -1), Vector3.new(-1, -1, 1), Vector3.new(-1, -1, -1) } do
			mn = mn:Min(p.CFrame:PointToWorldSpace(h * s))
		end
	end
	return mn
end

local function roleOf(inst, prefix)
	local cur = inst
	while cur do
		local r = cur.Name:match("^" .. prefix .. "_(%w+)")
		if r then
			return r
		end
		cur = cur.Parent
	end
	return nil
end

local function assetsFolder()
	local f = RS:FindFirstChild("LowriderAssets")
	if not f then
		f = Instance.new("Folder")
		f.Name = "LowriderAssets"
		f.Parent = RS
	end
	return f
end

local function rootPart(name, cf)
	local root = Instance.new("Part")
	root.Name = name
	root.Size = Vector3.one * 0.2
	root.Transparency = 1
	root.CFrame = cf
	root.Anchored, root.CanCollide, root.CanTouch, root.CanQuery, root.Massless = true, false, false, false, true
	return root
end

-- file one prefix's pieces under a new model whose root sits at the Blender origin, turned so front = -Z
local function collect(import, prefix, minT, outName, rootName, rootOffset)
	local list = {}
	for _, p in import:GetDescendants() do
		if p:IsA("MeshPart") then
			local r = roleOf(p, prefix)
			if r and not (prefix == "Lowrider" and p.Name:match("^LowriderWheel")) then
				table.insert(list, { part = p, role = r })
			end
		end
	end
	if #list == 0 then
		return nil
	end
	local parts = {}
	for _, it in list do
		table.insert(parts, it.part)
	end
	local origin = worldMin(parts) - v3(minT)
	local out = Instance.new("Model")
	out.Name = outName
	local root = rootPart(rootName, CFrame.new(origin + (rootOffset or Vector3.zero)) * CFrame.Angles(0, math.pi, 0))
	root.Parent = out
	out.PrimaryPart = root
	for _, it in list do
		local p = it.part
		p.Name = it.role
		p:SetAttribute("Role", it.role)
		p.Anchored = true
		p.Parent = out
	end
	return out
end

function Kit.Prepare(import)
	local folder = assetsFolder()
	local yawCar, yawShop = math.rad(Kit.FixYaw.Car or 0), math.rad(Kit.FixYaw.Shop or 0)
	local made = {}
	if yawCar ~= 0 then
		import:PivotTo(import:GetPivot() * CFrame.Angles(0, yawCar, 0))
	end
	local car = collect(import, "Lowrider", Data.Car.ImportMin, "Car", "Origin")
	if car then
		local old = folder:FindFirstChild("Car")
		if old then
			old:Destroy()
		end
		car.Parent = folder
		table.insert(made, "Car")
	end
	-- the wheel was built at its own offset; its root goes on the wheel centre
	local wheelList = {}
	for _, p in import:GetDescendants() do
		if p:IsA("MeshPart") and roleOf(p, "LowriderWheel") then
			table.insert(wheelList, p)
		end
	end
	if #wheelList > 0 then
		local origin = worldMin(wheelList) - v3(Data.Wheel.ImportMin)
		local wheel = Instance.new("Model")
		wheel.Name = "Wheel"
		local root = rootPart("Hub", CFrame.new(origin + v3(Data.Wheel.Centre)) * CFrame.Angles(0, math.pi, 0))
		root.Parent = wheel
		wheel.PrimaryPart = root
		for _, p in wheelList do
			local r = roleOf(p, "LowriderWheel")
			p.Name = r
			p:SetAttribute("Role", r)
			p.Anchored = true
			p.Parent = wheel
		end
		local old = folder:FindFirstChild("Wheel")
		if old then
			old:Destroy()
		end
		wheel.Parent = folder
		table.insert(made, "Wheel")
	end
	if yawShop ~= 0 then
		import:PivotTo(import:GetPivot() * CFrame.Angles(0, yawShop, 0))
	end
	local shop = collect(import, "LowSlowShop", Data.Shop.ImportMin, "Shop", "Origin")
	if shop then
		local old = folder:FindFirstChild("Shop")
		if old then
			old:Destroy()
		end
		shop.Parent = folder
		table.insert(made, "Shop")
	end
	assert(#made > 0, "NCLowriderKit.Prepare: no Lowrider_*, LowriderWheel_* or LowSlowShop_* pieces in " .. import:GetFullName())
	print("NCLowriderKit: prepared " .. table.concat(made, ", ") .. " in ReplicatedStorage.LowriderAssets")
	return made
end

---------------------------------------------------------------------------------------------------- part-made fallback
local M = Enum.Material
local DEFAULT = {
	Body = { M.SmoothPlastic, Color3.fromRGB(150, 8, 24) }, Lid = { M.SmoothPlastic, Color3.fromRGB(150, 8, 24) },
	ContBody = { M.SmoothPlastic, Color3.fromRGB(150, 8, 24) }, Chrome = { M.Metal, Color3.fromRGB(225, 228, 235) },
	ContChrome = { M.Metal, Color3.fromRGB(225, 228, 235) }, Pump = { M.Metal, Color3.fromRGB(225, 228, 235) },
	SteeringWheel = { M.Metal, Color3.fromRGB(225, 228, 235) }, Glass = { M.Glass, Color3.fromRGB(70, 90, 105), 0.45 },
	Interior = { M.Fabric, Color3.fromRGB(242, 238, 226) }, Tuck = { M.Fabric, Color3.fromRGB(225, 218, 205) },
	Dash = { M.SmoothPlastic, Color3.fromRGB(30, 30, 32) }, Carpet = { M.Carpet, Color3.fromRGB(115, 10, 20) },
	Headlight = { M.Neon, Color3.fromRGB(255, 246, 220) }, Taillight = { M.Neon, Color3.fromRGB(220, 15, 15) },
	Grille = { M.Metal, Color3.fromRGB(20, 20, 22) }, Seam = { M.SmoothPlastic, Color3.fromRGB(12, 12, 12) },
	Under = { M.SmoothPlastic, Color3.fromRGB(16, 16, 18) }, TrunkFloor = { M.Metal, Color3.fromRGB(205, 210, 220) },
	Battery = { M.SmoothPlastic, Color3.fromRGB(26, 26, 28) }, BatteryCap = { M.SmoothPlastic, Color3.fromRGB(215, 25, 25) },
	Tire = { M.Rubber, Color3.fromRGB(20, 20, 22) }, Whitewall = { M.Rubber, Color3.fromRGB(244, 244, 240) },
	Rim = { M.Metal, Color3.fromRGB(225, 228, 235) }, Spokes = { M.Metal, Color3.fromRGB(225, 228, 235) },
	Hub = { M.Metal, Color3.fromRGB(225, 228, 235) },
	-- shop
	WallsOut = { M.Plaster, Color3.fromRGB(226, 205, 176) }, WallsIn = { M.Plaster, Color3.fromRGB(236, 232, 222) },
	Trim = { M.SmoothPlastic, Color3.fromRGB(246, 246, 240) }, Roof = { M.Concrete, Color3.fromRGB(170, 90, 66) },
	Ceiling = { M.Plaster, Color3.fromRGB(240, 240, 236) }, Foundation = { M.Concrete, Color3.fromRGB(150, 150, 146) },
	ShopFloor = { M.Concrete, Color3.fromRGB(108, 108, 112) }, Neon = { M.Neon, Color3.fromRGB(255, 64, 166) },
	Neon2 = { M.Neon, Color3.fromRGB(40, 242, 242) }, SignBack = { M.SmoothPlastic, Color3.fromRGB(16, 16, 20) },
	Turntable = { M.DiamondPlate, Color3.fromRGB(190, 190, 198) }, HopPit = { M.SmoothPlastic, Color3.fromRGB(242, 204, 26) },
	HopBoard = { M.SmoothPlastic, Color3.fromRGB(244, 244, 240) }, HopTick = { M.SmoothPlastic, Color3.fromRGB(20, 20, 22) },
	Bench = { M.Metal, Color3.fromRGB(140, 26, 30) }, Tools = { M.Metal, Color3.fromRGB(178, 180, 188) },
	Mural = { M.SmoothPlastic, Color3.fromRGB(250, 140, 76) }, Glass2 = { M.Glass, Color3.fromRGB(160, 205, 235), 0.45 },
}
Kit.Materials = DEFAULT

local function styleDefault(p, role)
	local d = DEFAULT[role]
	if d then
		p.Material, p.Color = d[1], d[2]
		p.Transparency = d[3] or 0
	end
end

-- a small builder for part-made models in a local frame
local function maker(model, rootCF)
	local B = {}
	function B.part(role, size, localCF, shape)
		local p = Instance.new("Part")
		p.Name = role
		p.Size = size
		if shape then
			p.Shape = shape
		end
		p.CFrame = rootCF * localCF
		p.Anchored = true
		p.CanCollide, p.CanTouch, p.CanQuery = false, false, false
		p.TopSurface, p.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
		p:SetAttribute("Role", role)
		styleDefault(p, role)
		p.Parent = model
		return p
	end
	function B.box(role, x0, y0, z0, x1, y1, z1)
		local a, b = Vector3.new(math.min(x0, x1), math.min(y0, y1), math.min(z0, z1)), Vector3.new(math.max(x0, x1), math.max(y0, y1), math.max(z0, z1))
		return B.part(role, b - a, CFrame.new((a + b) / 2))
	end
	-- plate between two points (a beam with width w and thickness t)
	function B.beam(role, p0, p1, w, t, upHint)
		local d = p1 - p0
		local cf = CFrame.lookAt((p0 + p1) / 2, p1, upHint or Vector3.yAxis)
		return B.part(role, Vector3.new(w, t, d.Magnitude), cf)
	end
	-- cylinder along the local X axis
	function B.cyl(role, centre, length, diameter, rot)
		return B.part(role, Vector3.new(length, diameter, diameter), CFrame.new(centre) * (rot or CFrame.identity), Enum.PartType.Cylinder)
	end
	return B
end

local function fallbackCar()
	local model = Instance.new("Model")
	model.Name = "Car"
	local root = rootPart("Origin", CFrame.new())
	root.Parent = model
	model.PrimaryPart = root
	local B = maker(model, CFrame.new())
	local W, ZF, ZR, AR = 3.82, -6.2, 5.6, 1.42
	-- lower body in sections around the wheel arches (the wheels sit inside the body width)
	B.box("Body", -W, 0.75, -10.4, W, 2.62, ZF - AR)
	B.box("Body", -W, 2.6, ZF - AR, W, 2.78, ZF + AR)
	B.box("Body", -2.4, 0.75, ZF - AR, 2.4, 2.6, ZF + AR)
	B.box("Body", -W, 0.75, ZF + AR, W, 2.8, ZR - AR)
	B.box("Body", -W, 2.6, ZR - AR, W, 2.8, ZR + AR)
	B.box("Body", -2.4, 0.75, ZR - AR, 2.4, 2.6, ZR + AR)
	B.box("Body", -W, 0.75, ZR + AR, W, 2.62, 10.45)
	B.box("Body", -W + 0.15, 2.62, -10.3, W - 0.15, 2.74, ZF - AR) -- hood deck
	B.box("Body", -W + 0.15, 2.62, ZR + AR, W - 0.15, 2.74, 6.03)
	B.box("Body", -W + 0.15, 2.62, 9.82, W - 0.15, 2.74, 10.4)
	-- greenhouse
	B.box("Body", -3.0, 4.55, -0.85, 3.0, 4.75, 3.3)
	B.beam("Glass", Vector3.new(0, 2.84, -2.75), Vector3.new(0, 4.6, -0.85), 6.3, 0.08)
	B.beam("Glass", Vector3.new(0, 4.6, 3.3), Vector3.new(0, 2.84, 5.35), 6.3, 0.08)
	for _, s in { -1, 1 } do
		B.box("Glass", s * 3.2 - 0.04, 2.84, -2.4, s * 3.2 + 0.04, 4.5, 2.2)
		B.box("Body", s * 3.2 - 0.08, 2.84, 2.2, s * 3.2 + 0.08, 4.55, 3.6)
		B.beam("Chrome", Vector3.new(s * 3.2, 2.84, -2.75), Vector3.new(s * 2.95, 4.6, -0.85), 0.16, 0.16)
		B.beam("Chrome", Vector3.new(s * 2.95, 4.6, 3.3), Vector3.new(s * 3.2, 2.84, 5.35), 0.12, 0.12)
		B.beam("Body", Vector3.new(s * 3.1, 4.55, 3.5), Vector3.new(s * 3.3, 2.84, 5.3), 0.3, 1.2)
		-- side spear + rocker trim
		B.box("Chrome", s * W - 0.04, 2.08, ZF + AR + 0.25, s * W + 0.04, 2.16, ZR - AR - 0.25)
		B.box("Chrome", s * W - 0.04, 0.92, ZF + AR + 0.2, s * W + 0.04, 1.04, ZR - AR - 0.2)
		B.box("Seam", s * W - 0.03, 0.95, -2.66, s * W + 0.03, 2.6, -2.63)
		-- lights
		for _, x in { 2.62, 3.18 } do
			B.cyl("Headlight", Vector3.new(s * x, 1.92, -10.42), 0.12, 0.48, CFrame.Angles(0, math.pi / 2, 0))
		end
		for _, x in { 1.55, 2.3, 3.02 } do
			B.cyl("Taillight", Vector3.new(s * x, 1.98, 10.47), 0.12, 0.46, CFrame.Angles(0, math.pi / 2, 0))
		end
	end
	B.box("Chrome", -3.7, 0.92, -10.75, 3.7, 1.52, -10.28)
	B.box("Chrome", -3.7, 0.92, 10.32, 3.7, 1.52, 10.8)
	B.box("Grille", -2.25, 1.62, -10.42, 2.25, 2.18, -10.3)
	for k = 0, 4 do
		B.box("Chrome", -2.2, 1.68 + k * 0.115, -10.47, 2.2, 1.73 + k * 0.115, -10.4)
	end
	-- interior
	B.box("Carpet", -3.2, 0.95, -2.6, 3.2, 1.05, 5.6)
	B.box("Interior", -3.05, 1.05, -0.4, 3.05, 1.75, 1.3) -- front bench (cushion + back)
	B.box("Interior", -3.05, 1.75, 0.95, 3.05, 3.3, 1.3)
	B.box("Interior", -3.05, 1.05, 2.6, 3.05, 1.75, 4.2) -- rear bench
	B.box("Interior", -3.05, 1.75, 3.85, 3.05, 3.3, 4.2)
	B.box("Dash", -3.25, 2.2, -2.9, 3.25, 2.86, -2.25)
	B.cyl("SteeringWheel", Vector3.new(-1.55, 2.92, -1.7), 0.1, 1.05, CFrame.Angles(0, math.pi / 2, 0) * CFrame.Angles(0, 0, math.rad(-33)))
	-- trunk + continental kit
	B.box("TrunkFloor", -3.15, 1.25, 6.05, 3.15, 1.32, 9.8)
	for _, z in { 6.9, 8.2 } do
		B.cyl("Pump", Vector3.new(0.7, 1.75, z), 3.4, 0.6)
		B.cyl("Battery", Vector3.new(-1.5, 1.75, z), 1.0, 0.68)
	end
	for k = 0, 5 do
		local x = 2.75 - k * 1.1
		B.box("Battery", x - 0.9, 1.32, 9.0, x, 2.0, 9.7)
		B.box("BatteryCap", x - 0.75, 2.0, 9.3, x - 0.6, 2.1, 9.42)
	end
	B.box("ContChrome", -1.5, 0.95, 11.7, 1.5, 1.35, 12.0)
	B.cyl("ContBody", Vector3.new(0, 2.05, 11.55), 0.6, 2.24, CFrame.Angles(0, math.pi / 2, 0))
	B.cyl("ContChrome", Vector3.new(0, 2.05, 11.9), 0.1, 0.6, CFrame.Angles(0, math.pi / 2, 0))
	-- lid + art
	B.box("Lid", -3.18, 2.74, 6.03, 3.18, 2.84, 9.82)
	B.cyl("LidMuralSky", Vector3.new(0, 2.86, 7.95), 0.03, 3.2, CFrame.Angles(0, 0, math.pi / 2))
	B.cyl("LidMuralSun", Vector3.new(0, 2.875, 7.7), 0.03, 1.6, CFrame.Angles(0, 0, math.pi / 2))
	for k = 0, 3 do
		B.box("LidMuralSea", -1.2 + k * 0.1, 2.88, 7.4 - k * 0.28, 1.2 - k * 0.1, 2.89, 7.3 - k * 0.28)
	end
	for _, s in { -1, 1 } do
		B.beam("LidMuralPalm", Vector3.new(s * 1.6, 2.895, 7.0), Vector3.new(s * 1.2, 2.895, 9.0), 0.12, 0.02)
		for k = -2, 2 do
			B.beam("LidMuralPalm", Vector3.new(s * 1.2, 2.9, 9.0), Vector3.new(s * 1.2 + k * 0.35, 2.9, 9.5 + math.abs(k) * -0.15), 0.1, 0.02)
		end
		-- side patterns: a framed panel with diamonds
		for k = 0, 6 do
			local z = -4.3 + k * 1.25
			B.part("Patterns2", Vector3.new(0.02, 0.55, 0.55), CFrame.new(s * (W + 0.03), 1.7, z) * CFrame.Angles(math.rad(45), 0, 0))
		end
		B.box("Patterns", s * (W + 0.02) - 0.01, 1.42, -4.3, s * (W + 0.02) + 0.01, 1.47, 3.6)
		B.box("Patterns", s * (W + 0.02) - 0.01, 1.93, -4.3, s * (W + 0.02) + 0.01, 1.98, 3.6)
		-- flames: licks on the hood and the doors
		for k = 0, 3 do
			B.beam("Flames", Vector3.new(s * (0.4 + k * 0.85), 2.76, -10.0), Vector3.new(s * (0.6 + k * 0.7), 2.76, -6.6 + k * 0.7), 0.6 - k * 0.08, 0.02)
			B.beam("Flames", Vector3.new(s * (W + 0.03), 2.3 - k * 0.38, -4.6), Vector3.new(s * (W + 0.03), 2.2 - k * 0.38, 1.5 - k * 0.9), 0.02, 0.28, Vector3.xAxis)
		end
		-- pinstripe: a line over the spear and a hood scroll
		B.box("Pinstripe", s * (W + 0.03) - 0.01, 2.28, -4.4, s * (W + 0.03) + 0.01, 2.32, 3.8)
		B.beam("Pinstripe", Vector3.new(s * 0.2, 2.77, -9.4), Vector3.new(s * 1.5, 2.77, -7.0), 0.06, 0.02)
		B.beam("Pinstripe", Vector3.new(s * 1.5, 2.77, -7.0), Vector3.new(s * 0.3, 2.77, -4.6), 0.06, 0.02)
	end
	return model
end

local function fallbackWheel()
	local model = Instance.new("Model")
	model.Name = "Wheel"
	local root = rootPart("Hub", CFrame.new())
	root.Parent = model
	model.PrimaryPart = root
	local B = maker(model, CFrame.new())
	-- outer face = -X (a left-side wheel); tyre, whitewall ring, rim, 24 spokes, hub, two-bar knock-off
	B.cyl("Tire", Vector3.zero, 0.66, 2.34)
	B.cyl("Whitewall", Vector3.new(-0.335, 0, 0), 0.02, 1.94)
	B.cyl("Tire", Vector3.new(-0.345, 0, 0), 0.02, 1.72)
	B.cyl("Rim", Vector3.new(-0.33, 0, 0), 0.06, 1.48)
	B.cyl("Under", Vector3.new(-0.3, 0, 0), 0.04, 1.3)
	for k = 0, 23 do
		local a = k / 24 * math.pi * 2
		local a2 = a + (k % 2 == 0 and 0.4 or -0.4)
		B.beam("Spokes", Vector3.new(-0.3, 0.15 * math.cos(a), 0.15 * math.sin(a)), Vector3.new(-0.36, 0.62 * math.cos(a2), 0.62 * math.sin(a2)), 0.04, 0.04, Vector3.xAxis)
	end
	B.cyl("Hub", Vector3.new(-0.4, 0, 0), 0.25, 0.36)
	B.box("Hub", -0.52, -0.45, -0.06, -0.46, 0.45, 0.06)
	return model
end

local function fallbackShop()
	local model = Instance.new("Model")
	model.Name = "Shop"
	local root = rootPart("Origin", CFrame.new())
	root.Parent = model
	model.PrimaryPart = root
	local B = maker(model, CFrame.new())
	local X, Z, H = 27, 19, 19
	B.box("ShopFloor", -X, -0.6, -Z, X, 0.1, Z)
	B.box("WallsOut", -X, 0, Z - 1, X, H, Z) -- back wall (+Z)
	B.box("WallsOut", -X, 0, -Z, -X + 1, H, Z)
	B.box("WallsOut", X - 1, 0, -Z, X, H, Z)
	-- front wall (-Z) with two bay openings (x 6..23 each side) and a walk-in door
	B.box("WallsOut", -X, 12.5, -Z, X, H, -Z + 1)
	B.box("WallsOut", -6, 0, -Z, -2.2, 12.5, -Z + 1)
	B.box("WallsOut", 2.2, 0, -Z, 6, 12.5, -Z + 1)
	B.box("WallsOut", -2.2, 8, -Z, 2.2, 12.5, -Z + 1)
	B.box("WallsOut", -X, 0, -Z, -23, 12.5, -Z + 1)
	B.box("WallsOut", 23, 0, -Z, X, 12.5, -Z + 1)
	B.box("Roof", -X - 0.6, H, -Z - 0.6, X + 0.6, H + 0.8, Z + 0.6)
	local sign = B.box("SignBack", -20, 13.6, -Z - 1.4, 20, 18.2, -Z - 0.55)
	local gui = Instance.new("SurfaceGui")
	gui.Face = Enum.NormalId.Front
	gui.LightInfluence = 0
	gui.PixelsPerStud = 25
	gui.Parent = sign
	local t = Instance.new("TextLabel")
	t.Size = UDim2.fromScale(1, 1)
	t.BackgroundTransparency = 1
	t.Font = Enum.Font.FredokaOne
	t.TextScaled = true
	t.RichText = true
	t.Text = '<font color="#ff40a6">LOW &amp; SLOW</font> <font color="#28f2f2">KUSTOMS</font>'
	t.Parent = gui
	B.box("Turntable", 8, 0.1, -12, 21, 0.2, 4) -- the same spots as the mesh shop (NCLowriderData.Shop)
	B.box("HopPit", -21, 0.1, -12, -8, 0.14, 4)
	B.box("HopBoard", -19, 0.5, Z - 1.2, -10, 13, Z - 1)
	for k = 0, 24 do
		local w = k % 2 == 0 and 2.4 or 1.2
		B.box("HopTick", -14.5 - w / 2, 0.45 + k * 0.5, Z - 1.3, -14.5 + w / 2, 0.55 + k * 0.5, Z - 1.2)
	end
	B.box("Bench", -X + 1, 0.1, -6, -X + 4, 3.6, 6)
	for _, x in { -14.5, 14.5 } do
		B.box("Neon2", x - 4, H - 0.5, -0.3, x + 4, H - 0.3, 0.3)
	end
	return model
end

---------------------------------------------------------------------------------------------------- assembling
local function source(name)
	local f = RS:FindFirstChild("LowriderAssets")
	local m = f and f:FindFirstChild(name)
	if m then
		return m:Clone(), true
	end
	if name == "Car" then
		return fallbackCar(), false
	elseif name == "Wheel" then
		return fallbackWheel(), false
	end
	return fallbackShop(), false
end

local LID_ROLES = { Lid = true, LidMuralSky = true, LidMuralSun = true, LidMuralSea = true, LidMuralPalm = true, LidPinstripe = true }

local function weldTo(part, base, name)
	local w = Instance.new("Weld")
	w.Name = name or "Weld"
	w.Part0 = base
	w.Part1 = part
	w.C0 = base.CFrame:ToObjectSpace(part.CFrame)
	w.Parent = part
	return w
end

local function loose(p)
	p.Anchored = false
	p.CanCollide, p.CanTouch, p.CanQuery = false, false, false
	p.Massless = true
	p.CastShadow = true
end

-- builds a car at cf (the ground point between the axles, facing cf.LookVector); unanchored, ready to drive
function Kit.BuildCar(cf)
	local car = Instance.new("Model")
	car.Name = "Lowrider"
	local hull = Data.Car.Hull[1]
	local mn, mx = Vector3.new(hull[1], hull[2], hull[3]), Vector3.new(hull[4], hull[5], hull[6])
	local chassis = Instance.new("Part")
	chassis.Name = "Chassis"
	chassis.Size = mx - mn
	chassis.CFrame = cf * CFrame.new((mn + mx) / 2)
	chassis.Transparency = 1
	chassis.CustomPhysicalProperties = PhysicalProperties.new(Config.Drive.Density, 0.3, 0.2, 1, 1)
	chassis.TopSurface, chassis.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
	chassis.Parent = car
	car.PrimaryPart = chassis
	local origin = Instance.new("Attachment")
	origin.Name = "Origin"
	origin.CFrame = CFrame.new(-(mn + mx) / 2)
	origin.Parent = chassis
	local cab = Data.Car.Hull[2]
	local cmn, cmx = Vector3.new(cab[1], cab[2], cab[3]), Vector3.new(cab[4], cab[5], cab[6])
	local cabin = Instance.new("Part")
	cabin.Name = "Cabin"
	cabin.Size = cmx - cmn
	cabin.CFrame = cf * CFrame.new((cmn + cmx) / 2)
	cabin.Transparency = 1
	cabin.Massless = true
	cabin.Parent = car
	weldTo(cabin, chassis, "CabinWeld")

	-- body pieces
	local body = source("Car")
	local visual = Instance.new("Folder")
	visual.Name = "Visual"
	visual.Parent = car
	local lidFolder = Instance.new("Model")
	lidFolder.Name = "Lid"
	lidFolder.Parent = car
	body:PivotTo(cf)
	local hingeCF = cf * CFrame.new(v3(Data.Car.LidHinge))
	local hinge = Instance.new("Part")
	hinge.Name = "LidRoot"
	hinge.Size = Vector3.new(6, 0.1, 0.1)
	hinge.Transparency = 1
	hinge.CFrame = hingeCF
	loose(hinge)
	hinge.Parent = lidFolder
	lidFolder.PrimaryPart = hinge
	local hw = Instance.new("Weld")
	hw.Name = "LidHinge"
	hw.Part0 = chassis
	hw.Part1 = hinge
	hw.C0 = chassis.CFrame:ToObjectSpace(hingeCF)
	hw.Parent = hinge
	for _, p in body:GetChildren() do
		if p:IsA("BasePart") and p.Name ~= "Origin" then
			loose(p)
			local role = p:GetAttribute("Role") or p.Name
			if LID_ROLES[role] then
				p.Parent = lidFolder
				weldTo(p, hinge)
			else
				p.Parent = visual
				weldTo(p, chassis)
			end
		end
	end
	body:Destroy()

	-- wheels (posed by the clients through their weld)
	for name, pos in Data.Car.Wheels do
		local w = source("Wheel")
		w.Name = "W_" .. name
		local right = pos[1] > 0
		local wcf = cf * CFrame.new(v3(pos)) * (right and CFrame.Angles(0, math.pi, 0) or CFrame.identity)
		w:PivotTo(wcf)
		local hub = w.PrimaryPart
		loose(hub)
		for _, p in w:GetDescendants() do
			if p:IsA("BasePart") and p ~= hub then
				loose(p)
				weldTo(p, hub)
			end
		end
		local ww = Instance.new("Weld")
		ww.Name = "WheelWeld"
		ww.Part0 = chassis
		ww.Part1 = hub
		ww.C0 = chassis.CFrame:ToObjectSpace(wcf)
		ww.Parent = hub
		w:SetAttribute("Right", right)
		w:SetAttribute("Front", pos[3] < 0)
		w:SetAttribute("Rest", Vector3.new(pos[1], pos[2], pos[3]))
		w.Parent = car
	end

	-- seats
	local function seat(name, pos, driver)
		local s = Instance.new(driver and "VehicleSeat" or "Seat")
		s.Name = name
		s.Size = Vector3.new(2, 0.4, 2)
		s.Transparency = 1
		s.CFrame = cf * CFrame.new(v3(pos))
		s.CanCollide = false
		s.Massless = true
		if driver then
			s.MaxSpeed, s.Torque, s.TurnSpeed = 0, 0, 0
			s.HeadsUpDisplay = false
		end
		s.Parent = car
		weldTo(s, chassis, "SeatWeld")
		return s
	end
	seat("DriveSeat", Data.Car.Seats.Driver, true)
	seat("Seat_Passenger", Data.Car.Seats.Passenger)
	seat("Seat_RearL", Data.Car.Seats.RearL)
	seat("Seat_RearR", Data.Car.Seats.RearR)

	-- forces (the driver's client sets them every frame)
	local com = Instance.new("Attachment")
	com.Name = "CoM"
	com.Parent = chassis
	local vf = Instance.new("VectorForce")
	vf.Name = "Drive"
	vf.Attachment0 = com
	vf.RelativeTo = Enum.ActuatorRelativeTo.World
	vf.ApplyAtCenterOfMass = true
	vf.Force = Vector3.zero
	vf.Parent = chassis
	local tq = Instance.new("Torque")
	tq.Name = "Turn"
	tq.Attachment0 = com
	tq.RelativeTo = Enum.ActuatorRelativeTo.World
	tq.Torque = Vector3.zero
	tq.Parent = chassis
	car:SetAttribute("NCLowrider", true)
	return car
end

-- the car's ground origin (between the axles) in world space
function Kit.Origin(car)
	local ch = car.PrimaryPart
	return ch.CFrame * ch.Origin.CFrame
end

---------------------------------------------------------------------------------------------------- painting
local function finishFor(kind)
	return Config.WheelFinish[kind] or Config.WheelFinish.chrome
end

-- paints a car with a look table (see Config.StarterLook); safe to call on the client for a live preview
function Kit.ApplyLook(car, look)
	look = look or Config.StarterLook
	local paint = Config.Paint(look.paint).color
	local finish = Config.ById.Finishes[look.finish] or Config.Finishes[1]
	local art = Config.ById.Art[look.art] or Config.Art[1]
	local artColor = Config.Paint(look.artColor).color
	local stripe = Config.Paint(look.stripeColor).color
	local wheel = Config.ById.Wheels[look.wheels] or Config.Wheels[1]
	local artOn = {}
	for _, r in art.pieces do
		artOn[r] = true
	end
	local ART = { Flames = 1, FlamesEdge = 1, Patterns = 1, Patterns2 = 1, LidMuralSky = 1, LidMuralSun = 1, LidMuralSea = 1, LidMuralPalm = 1, LidPinstripe = 1 }
	for _, p in car:GetDescendants() do
		if not p:IsA("BasePart") then
			continue
		end
		local role = p:GetAttribute("Role")
		if not role then
			continue
		end
		local d = DEFAULT[role]
		if role == "Body" or role == "Lid" or role == "ContBody" then
			p.Color = paint
			p.Material = finish.material
			p.Reflectance = finish.reflectance
		elseif ART[role] then
			p.Transparency = artOn[role] and 0 or 1
			p.Material = Enum.Material.SmoothPlastic
			p.Reflectance = 0.1
			p.Color = Config.MuralColors[role] or (role == "LidPinstripe" and stripe) or artColor
		elseif role == "Pinstripe" then
			p.Transparency = look.pinstripe and 0 or 1
			p.Color = stripe
			p.Material = Enum.Material.SmoothPlastic
		elseif role == "Spokes" then
			local f = wheel.spokes == "paint" and { Enum.Material.SmoothPlastic, paint, 0.2 } or finishFor(wheel.spokes)
			p.Material, p.Color, p.Reflectance = f[1], f[2], f[3]
		elseif role == "Hub" then
			local f = finishFor(wheel.hub)
			p.Material, p.Color, p.Reflectance = f[1], f[2], f[3]
		elseif role == "Rim" or role == "Chrome" or role == "ContChrome" or role == "SteeringWheel" then
			p.Material, p.Color, p.Reflectance = Enum.Material.Metal, Color3.fromRGB(225, 228, 235), 0.45
			if role == "ContChrome" then
				p.Transparency = look.continental and 0 or 1
			end
		elseif role == "Whitewall" then
			p.Color = look.whitewall and DEFAULT.Whitewall[2] or DEFAULT.Tire[2]
			p.Material = Enum.Material.Rubber
		elseif role == "Carpet" then
			p.Color = paint:Lerp(Color3.new(0, 0, 0), 0.25)
			p.Material = Enum.Material.Carpet
		elseif role == "Pump" or role == "Battery" or role == "BatteryCap" then
			p.Transparency = look.trunkSetup and 0 or 1
			if role == "Pump" then
				p.Material, p.Color, p.Reflectance = Enum.Material.Metal, Color3.fromRGB(225, 228, 235), 0.45
			elseif d then
				p.Material, p.Color = d[1], d[2]
			end
		elseif role == "TrunkFloor" then
			p.Material, p.Color, p.Reflectance = Enum.Material.Metal, look.trunkSetup and Color3.fromRGB(225, 228, 235) or Color3.fromRGB(60, 60, 64), look.trunkSetup and 0.5 or 0
		elseif d then
			p.Material, p.Color = d[1], d[2]
			p.Transparency = d[3] or 0
		end
		if role == "ContBody" then
			p.Transparency = look.continental and 0 or 1
		end
	end
end

---------------------------------------------------------------------------------------------------- the shop
-- builds the shop at cf (its front faces cf.LookVector... i.e. the street is at -Z), anchored; returns the model
function Kit.BuildShop(cf)
	local src, isMesh = source("Shop")
	local shop = Instance.new("Model")
	shop.Name = "LowSlowKustoms"
	src:PivotTo(cf)
	for _, p in src:GetDescendants() do
		if p:IsA("BasePart") and p.Name ~= "Origin" then
			p.Anchored = true
			local role = p:GetAttribute("Role")
			if isMesh then
				p.CanCollide = false
				styleDefault(p, role)
				if role == "Glass" then
					styleDefault(p, "Glass2")
				end
			else
				p.CanCollide = role ~= "Neon2" and role ~= "HopTick"
			end
			p.Parent = shop
		end
	end
	src:Destroy()
	if isMesh then -- exact collision boxes from the Blender data
		local cols = Instance.new("Folder")
		cols.Name = "Colliders"
		cols.Parent = shop
		for _, b in Data.Shop.Colliders do
			local mn, mx = Vector3.new(b[1], b[2], b[3]), Vector3.new(b[4], b[5], b[6])
			local p = Instance.new("Part")
			p.Name = "Collider"
			p.Size = (mx - mn):Max(Vector3.one * 0.05)
			p.CFrame = cf * CFrame.new((mn + mx) / 2)
			p.Anchored = true
			p.Transparency = 1
			p.CanTouch = false
			p.Parent = cols
		end
	end
	local function zone(name, box)
		local mn, mx = Vector3.new(box[1], box[2], box[3]), Vector3.new(box[4], box[5], box[6])
		local p = Instance.new("Part")
		p.Name = name
		p.Size = mx - mn
		p.CFrame = cf * CFrame.new((mn + mx) / 2)
		p.Anchored, p.CanCollide, p.CanTouch, p.CanQuery = true, false, false, false
		p.Transparency = 1
		p.Parent = shop
		return p
	end
	zone("CustomZone", Data.Shop.Custom)
	zone("HopPitZone", Data.Shop.HopPit)
	local counter = Instance.new("Part")
	counter.Name = "Counter"
	counter.Size = Vector3.new(2, 2, 2)
	counter.CFrame = cf * CFrame.new(v3(Data.Shop.Counter))
	counter.Anchored, counter.CanCollide, counter.Transparency = true, false, 1
	counter.Parent = shop
	local spawnP = Instance.new("Part")
	spawnP.Name = "CarSpawn"
	spawnP.Size = Vector3.new(8, 0.2, 20)
	spawnP.CFrame = cf * CFrame.new(v3(Data.Shop.Spawn))
	spawnP.Anchored, spawnP.CanCollide, spawnP.Transparency = true, false, 1
	spawnP.Parent = shop
	local board = Instance.new("Part")
	board.Name = "HopBoardBase"
	board.Size = Vector3.new(1, 1, 1)
	board.CFrame = cf * CFrame.new(v3(Data.Shop.HopBoardBase))
	board.Anchored, board.CanCollide, board.Transparency = true, false, 1
	board.Parent = shop
	shop.PrimaryPart = counter
	return shop
end

return Kit
