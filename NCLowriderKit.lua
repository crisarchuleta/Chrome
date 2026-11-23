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
--     Lid           the trunk lid (a paint panel too), welded by "LidHinge" (server opens it)
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
	-- vinyls: LowriderVinyls.glb holds every decal image on a copy of its panel. Studio uploads the images on
	-- import; keep their ids (as attributes of LowriderAssets.Vinyls) and drop the copies.
	local vinyls = folder:FindFirstChild("Vinyls") or Instance.new("Configuration")
	vinyls.Name = "Vinyls"
	vinyls.Parent = folder
	local nV = 0
	for _, p in import:GetDescendants() do
		local liv, pan = nil, nil
		local cur = p
		while cur and not liv do
			liv, pan = cur.Name:match("^Livery_(.+)_(%a+)$")
			cur = cur.Parent
		end
		if liv and p:IsA("MeshPart") then
			local id = p.TextureID
			local sa = p:FindFirstChildOfClass("SurfaceAppearance")
			if (id == nil or id == "") and sa then
				pcall(function()
					id = sa.ColorMap
				end)
			end
			if id and id ~= "" then
				vinyls:SetAttribute(liv .. "_" .. pan, id)
				nV += 1
			else
				warn("NCLowriderKit.Prepare: " .. p:GetFullName() .. " came in without its image; upload lowrider_vinyls/" .. liv .. "_" .. pan .. ".png and put its id in NCLowriderConfig.VinylIds")
			end
		end
	end
	if nV > 0 then
		table.insert(made, nV .. " vinyls")
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
	assert(#made > 0, "NCLowriderKit.Prepare: no Lowrider_*, LowriderWheel_*, Livery_* or LowSlowShop_* pieces in " .. import:GetFullName())
	print("NCLowriderKit: prepared " .. table.concat(made, ", ") .. " in ReplicatedStorage.LowriderAssets")
	return made
end

---------------------------------------------------------------------------------------------------- part-made fallback
local M = Enum.Material
local DEFAULT = {
	Body = { M.SmoothPlastic, Color3.fromRGB(150, 8, 24) }, Lid = { M.SmoothPlastic, Color3.fromRGB(150, 8, 24) },
	PanelHood = { M.SmoothPlastic, Color3.fromRGB(150, 8, 24) }, PanelRoof = { M.SmoothPlastic, Color3.fromRGB(150, 8, 24) },
	PanelSideL = { M.SmoothPlastic, Color3.fromRGB(150, 8, 24) }, PanelSideR = { M.SmoothPlastic, Color3.fromRGB(150, 8, 24) },
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
	B.box("PanelHood", -W + 0.15, 2.62, -10.3, W - 0.15, 2.74, -2.7) -- hood deck (takes the hood vinyl as a Decal)
	B.box("Body", -W + 0.15, 2.62, ZR + AR, W - 0.15, 2.74, 6.03)
	B.box("Body", -W + 0.15, 2.62, 9.82, W - 0.15, 2.74, 10.4)
	-- greenhouse
	B.box("PanelRoof", -3.0, 4.55, -0.85, 3.0, 4.75, 3.3)
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

local LID_ROLES = { Lid = true }

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

---------------------------------------------------------------------------------------------------- dash gauge + plaque
-- The dash's gauge face gets a live 60s-style ribbon speedometer (a SurfaceGui), the club plaque gets its name.
local GAUGE = Data.Car.Gauge or { Centre = { -1.55, 2.62, -2.3 }, Size = { 1.6, 0.418 }, Tilt = 16.7 }
local PLAQUE = Data.Car.Plaque or { Centre = { 0, 3.35, 4.68 }, Size = { 2.0, 0.6 } }
local MAX_MPH = 120

local function facePart(name, size, localCF, chassis, origin)
	local p = Instance.new("Part")
	p.Name = name
	p.Size = size
	p.Transparency = 1
	loose(p)
	p.CastShadow = false
	p.CFrame = chassis.CFrame * origin.CFrame * localCF
	weldTo(p, chassis)
	return p
end

local function buildSpeedo(car, chassis, origin)
	local t = math.rad(GAUGE.Tilt)
	local n = Vector3.new(0, math.sin(t), math.cos(t))
	local cf = CFrame.new(v3(GAUGE.Centre) + n * 0.02) * CFrame.Angles(-t, 0, 0)
	local p = facePart("GaugeFace", Vector3.new(GAUGE.Size[1] - 0.1, GAUGE.Size[2] - 0.04, 0.02), cf, chassis, origin)
	p.Parent = car
	local g = Instance.new("SurfaceGui")
	g.Name = "Speedo"
	g.Face = Enum.NormalId.Back
	g.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
	g.CanvasSize = Vector2.new(400, 96)
	g.LightInfluence = 0.4
	g.Parent = p
	local face = Instance.new("Frame")
	face.Name = "Dial"
	face.Size = UDim2.fromScale(1, 1)
	face.BorderSizePixel = 0
	face.Parent = g
	Instance.new("UICorner", face).CornerRadius = UDim.new(0, 12)
	local stroke = Instance.new("UIStroke", face)
	stroke.Name = "Bezel"
	stroke.Thickness = 5
	for k = 0, 12 do
		local x = 0.06 + 0.88 * k / 12
		local tick = Instance.new("Frame")
		tick.Name = "Tick"
		tick.AnchorPoint = Vector2.new(0.5, 0)
		tick.Position = UDim2.new(x, 0, 0.12, 0)
		tick.Size = UDim2.new(0, k % 2 == 0 and 4 or 2, k % 2 == 0 and 0.32 or 0.2, 0)
		tick.BorderSizePixel = 0
		tick.Parent = face
		if k % 2 == 0 then
			local l = Instance.new("TextLabel")
			l.Name = "Num"
			l.AnchorPoint = Vector2.new(0.5, 0)
			l.Position = UDim2.new(x, 0, 0.48, 0)
			l.Size = UDim2.new(0, 50, 0.32, 0)
			l.BackgroundTransparency = 1
			l.Font = Enum.Font.GothamBold
			l.TextScaled = true
			l.Text = tostring(k * MAX_MPH / 12)
			l.Parent = face
		end
	end
	local needle = Instance.new("Frame")
	needle.Name = "Needle"
	needle.AnchorPoint = Vector2.new(0.5, 0)
	needle.Position = UDim2.new(0.06, 0, 0.06, 0)
	needle.Size = UDim2.new(0, 6, 0.86, 0)
	needle.BorderSizePixel = 0
	needle.ZIndex = 3
	needle.Parent = face
	local digits = Instance.new("TextLabel")
	digits.Name = "Digits"
	digits.Size = UDim2.fromScale(1, 1)
	digits.BackgroundTransparency = 1
	digits.Font = Enum.Font.Code
	digits.TextScaled = true
	digits.Text = "0 MPH"
	digits.ZIndex = 4
	digits.Parent = face
end

local function buildPlaque(car, chassis, origin)
	local p = facePart("PlaqueFace", Vector3.new(PLAQUE.Size[1], PLAQUE.Size[2], 0.02), CFrame.new(v3(PLAQUE.Centre)), chassis, origin)
	p.Parent = car
	local g = Instance.new("SurfaceGui")
	g.Name = "Plaque"
	g.Face = Enum.NormalId.Back
	g.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
	g.CanvasSize = Vector2.new(400, 120)
	g.LightInfluence = 0.5
	g.Enabled = false
	g.Parent = p
	local l = Instance.new("TextLabel")
	l.Name = "Label"
	l.Size = UDim2.fromScale(1, 1)
	l.BackgroundTransparency = 1
	l.Font = Enum.Font.Fondamento
	l.TextScaled = true
	l.TextColor3 = Color3.fromRGB(235, 236, 240)
	l.TextStrokeTransparency = 0.4
	l.Parent = g
end

local function styleSpeedo(car, look)
	local p = car:FindFirstChild("GaugeFace")
	local g = p and p:FindFirstChild("Speedo")
	if not g then
		return
	end
	local st = Config.Gauges[look.gauge] or Config.Gauges.classic
	local face = g.Dial
	face.BackgroundColor3 = st.face
	face.Bezel.Color = st.bezel and Color3.fromRGB(225, 228, 235) or st.face:Lerp(Color3.new(0, 0, 0), 0.4)
	g.LightInfluence = st.glow and 0 or 0.4
	g.Brightness = st.glow and 2 or 1
	for _, c in face:GetChildren() do
		if c.Name == "Tick" then
			c.BackgroundColor3 = st.ink
			c.Visible = not st.digital
		elseif c.Name == "Num" then
			c.TextColor3 = st.ink
			c.Visible = not st.digital
		end
	end
	face.Needle.BackgroundColor3 = st.needle
	face.Needle.Visible = not st.digital
	face.Digits.TextColor3 = st.ink
	face.Digits.Visible = st.digital == true
end

-- moves a car's speedometer (call on clients; mph = road speed)
function Kit.SetSpeed(car, mph)
	local p = car:FindFirstChild("GaugeFace")
	local g = p and p:FindFirstChild("Speedo")
	if not g then
		return
	end
	local f = math.clamp(mph / MAX_MPH, 0, 1)
	g.Dial.Needle.Position = UDim2.new(0.06 + 0.88 * f, 0, 0.06, 0)
	g.Dial.Digits.Text = ("%d MPH"):format(math.floor(mph + 0.5))
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
	local optFolder = Instance.new("Folder")
	optFolder.Name = "Opt"
	optFolder.Parent = car
	for _, p in body:GetChildren() do
		if p:IsA("BasePart") and p.Name ~= "Origin" then
			loose(p)
			local role = p:GetAttribute("Role") or p.Name
			if Data.Car.OptInfo and Data.Car.OptInfo[role] then
				p:Destroy() -- swappable parts come from ApplyLook
			elseif LID_ROLES[role] then
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
				if Data.Wheel.OptInfo and Data.Wheel.OptInfo[p:GetAttribute("Role") or p.Name] then
					p:Destroy()
				else
					loose(p)
					weldTo(p, hub)
				end
			end
		end
		local wopt = Instance.new("Folder")
		wopt.Name = "Opt"
		wopt.Parent = w
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

	buildSpeedo(car, chassis, origin)
	buildPlaque(car, chassis, origin)

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

---------------------------------------------------------------------------------------------------- swappable parts
-- The imported car / wheel hold every variant of every part (NCLowriderData OptInfo: piece -> slot, variant, mat).
-- A built car only carries the variants its look picks: ApplyLook clones them from LowriderAssets into the car's
-- (or wheel's) "Opt" folder and welds them on. Running it again only swaps the slots that changed, so it's cheap
-- enough for the live preview in the shop (the client does it locally; the server's copy is what everyone sees).
local OPT = Data.Car.OptInfo or {}
local WOPT = Data.Wheel.OptInfo or {}
local LID_SLOTS = { Spoiler = true } -- these ride on the trunk lid
local templates = {}

local function template(name, info)
	local f = RS:FindFirstChild("LowriderAssets")
	local m = f and f:FindFirstChild(name)
	if not m or not m.PrimaryPart then
		return nil
	end
	local t = templates[name]
	if t and t.model == m then
		return t
	end
	t = { model = m, bySlot = {} }
	local root = m.PrimaryPart.CFrame
	for _, p in m:GetChildren() do
		if p:IsA("BasePart") then
			local inf = info[p:GetAttribute("Role") or p.Name]
			if inf then
				local bySlot = t.bySlot[inf.slot] or {}
				t.bySlot[inf.slot] = bySlot
				bySlot[inf.variant] = bySlot[inf.variant] or {}
				table.insert(bySlot[inf.variant], { part = p, rel = root:ToObjectSpace(p.CFrame) })
			end
		end
	end
	templates[name] = t
	return t
end

local function syncParts(folder, t, wantOf, attach)
	local keep = {}
	for _, p in folder:GetChildren() do
		local slot = p:GetAttribute("Slot")
		if not slot or p:GetAttribute("Variant") ~= wantOf(slot) or keep[p.Name] then
			p:Destroy()
		else
			keep[p.Name] = true
		end
	end
	for slot, variants in t.bySlot do
		local want = wantOf(slot)
		for _, it in (want ~= "" and variants[want] or {}) do
			if not keep[it.part.Name] then
				local c = it.part:Clone()
				loose(c)
				c:SetAttribute("Slot", slot)
				c:SetAttribute("Variant", want)
				attach(c, slot, it.rel)
				c.Parent = folder
			end
		end
	end
end

local function weldAt(c, part0, c0)
	c.CFrame = part0.CFrame * c0
	local w = Instance.new("Weld")
	w.Part0, w.Part1, w.C0 = part0, c, c0
	w.Parent = c
end

local function syncCarParts(car, look)
	local t = template("Car", OPT)
	local folder = car:FindFirstChild("Opt")
	local ch = car.PrimaryPart
	local origin = ch and ch:FindFirstChild("Origin")
	if not (t and folder and origin) then
		return
	end
	local lid = car:FindFirstChild("Lid")
	local hinge = lid and lid:FindFirstChild("LidRoot")
	local hingeInv = CFrame.new(v3(Data.Car.LidHinge)):Inverse()
	syncParts(folder, t, function(slot)
		if (slot == "Visor" or slot == "Headliner") and look.part_Top == "Down" then
			return "" -- nothing to hang a visor on with the top down
		end
		return look["part_" .. slot] or ""
	end, function(c, slot, rel)
		if LID_SLOTS[slot] and hinge then
			weldAt(c, hinge, hingeInv * rel)
		else
			weldAt(c, ch, origin.CFrame * rel)
		end
	end)
end

local function wheelWant(look)
	return function(slot)
		if slot == "Band" then
			return (look.ww or "") ~= "" and (look.part_Tire or "Classic") .. look.ww or ""
		end
		return look["part_" .. slot] or ""
	end
end

local function syncWheelParts(car, look)
	local t = template("Wheel", WOPT)
	if not t then
		return
	end
	for _, w in car:GetChildren() do
		local folder = w:IsA("Model") and w.Name:match("^W_") and w:FindFirstChild("Opt")
		if folder and w.PrimaryPart then
			local hub = w.PrimaryPart
			syncParts(folder, t, wheelWant(look), function(c, _, rel)
				weldAt(c, hub, rel)
			end)
		end
	end
end

---------------------------------------------------------------------------------------------------- painting
local PANEL_OF = Data.Car.PanelOf or { PanelSideL = "side", PanelSideR = "side", PanelHood = "hood", Lid = "trunk", PanelRoof = "roof" }
-- the fallback (part-made) car shows a vinyl as a Decal on this face of each panel part
local DECAL_FACE = { PanelHood = Enum.NormalId.Top, PanelRoof = Enum.NormalId.Top, Lid = Enum.NormalId.Top, PanelSideL = Enum.NormalId.Left, PanelSideR = Enum.NormalId.Right }
-- which finish key the chrome pieces of each slot follow (everything else: fin_Trim)
local FIN_GROUP = {
	FrontBumper = "Bumpers", RearBumper = "Bumpers", Grille = "Grille", Mirrors = "Mirrors", Exhaust = "Exhaust", Trunk = "Trunk",
	Steering = "Cabin", Dash = "Cabin", Shifter = "Cabin", Plaque = "Cabin", Doors = "Cabin", Audio = "Cabin", Pedals = "Cabin",
	Headlights = "Lights", Taillights = "Lights", Rim = "Rim", KO = "KO",
}

-- the uploaded image id for a livery's panel ("" if there's none)
function Kit.VinylId(livery, panel)
	local key = livery .. "_" .. panel
	local id = Config.VinylIds[key]
	if id and id ~= "" then
		return id
	end
	local f = RS:FindFirstChild("LowriderAssets")
	local v = f and f:FindFirstChild("Vinyls")
	return v and v:GetAttribute(key) or ""
end

local function printVinyl(p, role, id)
	if p:IsA("MeshPart") then
		p.TextureID = id -- clear pixels show the part's Color (the candy paint) through
	else
		local d = p:FindFirstChild("Vinyl")
		if id == "" then
			if d then
				d:Destroy()
			end
			return
		end
		if not d then
			d = Instance.new("Decal")
			d.Name = "Vinyl"
			d.Face = DECAL_FACE[role] or Enum.NormalId.Top
			d.Parent = p
		end
		d.Texture = id
	end
end

local ROOF_ROLES = { PanelRoof = true, RoofGlass = true, RoofBody = true, RoofChrome = true }

local function colorOf(look, key, fallback)
	return Config.ColorOf(key, look[key]) or fallback
end

-- material, colour, reflectance, transparency for one piece
local styleFor
function styleFor(role, look, ctx)
	local inf = OPT[role] or WOPT[role]
	local mat = inf and inf.mat or role
	local function trim(key)
		local f = Config.ById.TrimFinishes[look[key]] or Config.TrimFinishes[1]
		if f.id == "paint" then
			return ctx.finish.material, ctx.paint, ctx.finish.reflectance, 0
		end
		return f.material, f.color, f.reflectance, 0
	end
	if mat == "Chrome" or mat == "ContChrome" or mat == "SteeringWheel" then
		return trim("fin_" .. (inf and FIN_GROUP[inf.slot] or "Trim"))
	elseif mat == "Rim" or mat == "Dish" then
		return trim("fin_Rim")
	elseif mat == "Spokes" then
		return trim("fin_Spokes")
	elseif mat == "Hub" then
		return trim("fin_KO")
	elseif mat == "Pump" then
		return trim("fin_Trunk")
	elseif mat == "Body" or mat == "ContBody" or mat == "Lid" or PANEL_OF[mat] then
		local c = (mat == "PanelRoof") and ctx.roof or ctx.paint
		return ctx.finish.material, c, ctx.finish.reflectance, 0
	elseif mat == "Seat" or mat == "Interior" then
		return ctx.seatMat[1], ctx.seat, ctx.seatMat[2], 0
	elseif mat == "SeatTrim" or mat == "Tuck" then
		return ctx.seatMat[1], ctx.stitch, ctx.seatMat[2], 0
	elseif mat == "Carpet" then
		return Enum.Material.Carpet, ctx.carpet, 0, 0
	elseif mat == "Dash" then
		return Enum.Material.SmoothPlastic, ctx.dash, 0.05, 0
	elseif mat == "Wood" then
		return Enum.Material.Wood, colorOf(look, "col_Wood", Color3.fromRGB(96, 52, 26)), 0.1, 0
	elseif mat == "Gauge" then
		local st = Config.Gauges[look.gauge] or Config.Gauges.classic
		return st.glow and Enum.Material.Neon or Enum.Material.SmoothPlastic, st.face, 0, 0
	elseif mat == "Neon" then
		return Enum.Material.Neon, ctx.neon, 0, 0
	elseif mat == "Top" then
		return Enum.Material.Fabric, colorOf(look, "col_Top", Color3.fromRGB(14, 14, 16)), 0, 0
	elseif mat == "RoofGlass" then
		return styleFor("Glass", look, ctx)
	elseif mat == "RoofChrome" then
		return trim("fin_Trim")
	elseif mat == "RoofBody" then
		return ctx.finish.material, ctx.paint, ctx.finish.reflectance, 0
	elseif mat == "Fur" then
		return Enum.Material.Fabric, colorOf(look, "col_Fur", Color3.new(1, 1, 1)), 0, 0
	elseif mat == "Dark" then
		return Enum.Material.SmoothPlastic, Color3.fromRGB(20, 20, 22), 0.05, 0
	elseif mat == "Rubber" or mat == "Tire" then
		return Enum.Material.Rubber, Color3.fromRGB(20, 20, 22), 0, 0
	elseif mat == "Band" then
		return Enum.Material.Rubber, ctx.band, 0, 0
	elseif mat == "Whitewall" then -- the part-made wheel
		return Enum.Material.Rubber, (look.ww or "") ~= "" and ctx.band or Color3.fromRGB(20, 20, 22), 0, 0
	elseif mat == "Glass" then
		if inf then -- mirror glass, crystal knob, show-trunk mirror floor
			return Enum.Material.Glass, Color3.fromRGB(200, 220, 235), 0.4, 0.15
		end
		local tint = Config.OptionOf.tint[look.tint] or Config.OptionOf.tint.none
		local tr = ({ none = 0.45, light = 0.35, dark = 0.22, limo = 0.08, blue = 0.25, purple = 0.25 })[tint.id] or 0.45
		return Enum.Material.Glass, tint.color, 0.15, tr
	elseif mat == "Headlight" then
		return Enum.Material.Neon, colorOf(look, "headlights", Color3.fromRGB(255, 238, 200)), 0, 0
	elseif mat == "Head" then
		return Enum.Material.Neon, colorOf(look, "headlights", Color3.fromRGB(255, 238, 200)), 0, 0
	elseif mat == "Taillight" or mat == "Light" or mat == "Tail" then
		return Enum.Material.Neon, colorOf(look, "taillights", Color3.fromRGB(220, 15, 15)), 0, 0
	elseif mat == "TrunkFloor" then
		local on = (look.part_Trunk or "") ~= ""
		return Enum.Material.Metal, on and Color3.fromRGB(205, 210, 220) or Color3.fromRGB(60, 60, 64), on and 0.4 or 0, 0
	end
	local d = DEFAULT[mat]
	if d then
		return d[1], d[2], 0, d[3] or 0
	end
	return nil
end

-- paints and builds a car to a look (Config.CleanLook makes one); safe to call on the client for a live preview
function Kit.ApplyLook(car, look)
	look = Config.CleanLook(look)
	syncCarParts(car, look)
	syncWheelParts(car, look)
	local paint = Config.ColorOf("paint", look.paint) or Config.Paints[1].color
	local seat = colorOf(look, "col_Seat", Color3.fromRGB(242, 238, 226))
	local ctx = {
		paint = paint,
		roof = look.paint2 == "same" and paint or (Config.ColorOf("paint2", look.paint2) or paint),
		finish = Config.ById.Finishes[look.finish] or Config.Finishes[1],
		seat = seat,
		stitch = look.col_Stitch == "match" and seat:Lerp(Color3.new(0, 0, 0), 0.12) or colorOf(look, "col_Stitch", seat),
		seatMat = Config.SeatMaterials[look.mat_Seat] or Config.SeatMaterials.vinyl,
		carpet = look.col_Carpet == "match" and paint:Lerp(Color3.new(0, 0, 0), 0.3) or colorOf(look, "col_Carpet", paint),
		dash = look.col_Dash == "match" and paint or colorOf(look, "col_Dash", Color3.fromRGB(30, 30, 32)),
		neon = colorOf(look, "col_Neon", Color3.fromRGB(255, 50, 170)),
		band = colorOf(look, "col_Band", Color3.fromRGB(244, 244, 240)),
	}
	local art = Config.ById.Art[look.art] or Config.Art[1]
	local trunkOn, contOn = (look.part_Trunk or "") ~= "", (look.part_Continental or "") ~= ""
	local topDown = look.part_Top == "Down"
	for _, p in car:GetDescendants() do
		if not p:IsA("BasePart") then
			continue
		end
		local role = p:GetAttribute("Role")
		if not role then
			continue
		end
		local m, c, r, tr = styleFor(role, look, ctx)
		if m then
			p.Material, p.Color, p.Reflectance, p.Transparency = m, c, r, tr
		end
		if PANEL_OF[role] then
			printVinyl(p, role, art.id == "none" and "" or Kit.VinylId(art.id, PANEL_OF[role]))
		end
		-- convertible: the hardtop roof, rear glass and side glass go away
		if ROOF_ROLES[role] then
			p.Transparency = topDown and 1 or p.Transparency
			local d = p:FindFirstChild("Vinyl")
			if d then
				d.Transparency = topDown and 1 or 0
			end
			if topDown and p:IsA("MeshPart") then
				p.TextureID = ""
			end
		end
		-- pieces that only the part-made fallback car has
		if role == "Pump" or role == "Battery" or role == "BatteryCap" then
			p.Transparency = trunkOn and 0 or 1
		elseif role == "ContBody" or role == "ContChrome" then
			p.Transparency = contOn and 0 or 1
		end
		-- underglow throws light on the road
		local inf = OPT[role]
		if inf and inf.slot == "Glow" then
			local l = p:FindFirstChild("Glow") or Instance.new("PointLight")
			l.Name = "Glow"
			l.Color = ctx.neon
			l.Range = 10
			l.Brightness = 3
			l.Parent = p
		end
	end
	styleSpeedo(car, look)
	local pf = car:FindFirstChild("PlaqueFace")
	local pg = pf and pf:FindFirstChild("Plaque")
	if pg then
		pg.Enabled = (look.part_Plaque or "") ~= ""
		local o = Config.OptionOf.plaque[look.plaque]
		pg.Label.Text = o and o.name or ""
	end
	car:SetAttribute("Engine", look.engine)
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
