--!nonstrict
-- Elevator (server): the office tower's express elevator, lobby <-> roof. The stairs next to it are free; the
-- elevator costs earned Cash going up (PRICE, through NCWallet -> the game's NC module), coming down is free.
-- BuildingKit puts an ElevatorRoot part (tag NC_Elevator) in the tower with the shaft, car, stops, door and call
-- points as attributes in the tower's own frame; this script builds a real car in the shaft that rides a
-- PrismaticConstraint (so players standing in it are carried by physics, smoothly, with the car), sliding shaft
-- doors at both stops, call panels, a floor display and a chime.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local TweenService = game:GetService("TweenService")
local SSS = game:GetService("ServerScriptService")

local PRICE = 50
local SPEED = 26 -- studs/s: lobby to roof (~260 studs) in about 10 s, like a real express car
local Wallet = require(SSS:WaitForChild("NCWallet"))

local function part(name, size, cf, color, material)
	local p = Instance.new("Part")
	p.Name = name
	p.Size = size
	p.CFrame = cf
	p.Color = color or Color3.fromRGB(200, 200, 205)
	p.Material = material or Enum.Material.Metal
	p.TopSurface, p.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
	return p
end

local function chime(where)
	local s = Instance.new("Sound")
	s.SoundId = "rbxasset://sounds/volume_slider.ogg"
	s.PlaybackSpeed = 1.6
	s.Volume = 0.8
	s.RollOffMaxDistance = 60
	s.Parent = where
	s:Play()
	game:GetService("Debris"):AddItem(s, 2)
end

local done = setmetatable({}, { __mode = "k" })
local function setup(root)
	if done[root] then
		return
	end
	done[root] = true
	-- a copy of a tower cloned after its car was built carries a dead car: clear it and build a live one
	local stale = root.Parent and root.Parent:FindFirstChild("ElevatorCar")
	if stale then
		stale:Destroy()
	end
	local cf = root.CFrame
	local A = function(k)
		return root:GetAttribute(k)
	end
	local s0, s1 = A("Stop0"), A("Stop1")
	local price = A("Price") or PRICE
	local cmin, cmax = A("CarMin"), A("CarMax")
	local cw, cd = cmax.X - cmin.X, cmax.Z - cmin.Z
	local ccx, ccz = (cmin.X + cmax.X) / 2, (cmin.Z + cmax.Z) / 2
	local CH = 10.0
	local model = Instance.new("Model")
	model.Name = "ElevatorCar"
	model.Parent = root.Parent
	-- the car: floor, back and side walls, roof, handrail, light, display; open toward the shaft doors (+X)
	local heavy = PhysicalProperties.new(20, 0.8, 0, 1, 1)
	local floor = part("CarFloor", Vector3.new(cw, 0.35, cd), cf * CFrame.new(ccx, s0 + 0.18, ccz), Color3.fromRGB(60, 62, 66), Enum.Material.DiamondPlate)  -- sits just above the stop
	floor.CustomPhysicalProperties = heavy
	local car = { floor }
	local function carPart(name, size, offset, color, material)
		local p = part(name, size, floor.CFrame * CFrame.new(offset), color, material)
		p.CustomPhysicalProperties = heavy
		table.insert(car, p)
		return p
	end
	local wallC = Color3.fromRGB(176, 180, 186)
	local back = carPart("CarBack", Vector3.new(0.3, CH, cd), Vector3.new(-cw / 2 + 0.15, CH / 2 + 0.25, 0), wallC, Enum.Material.Metal)
	carPart("CarSideL", Vector3.new(cw, CH, 0.3), Vector3.new(0, CH / 2 + 0.25, -cd / 2 + 0.15), wallC, Enum.Material.Metal)
	carPart("CarSideR", Vector3.new(cw, CH, 0.3), Vector3.new(0, CH / 2 + 0.25, cd / 2 - 0.15), wallC, Enum.Material.Metal)
	local roof = carPart("CarRoof", Vector3.new(cw, 0.4, cd), Vector3.new(0, CH + 0.45, 0), Color3.fromRGB(230, 230, 228), Enum.Material.SmoothPlastic)
	carPart("Handrail", Vector3.new(0.2, 0.2, cd - 1.0), Vector3.new(-cw / 2 + 0.45, 3.6, 0), Color3.fromRGB(210, 190, 140), Enum.Material.Metal)
	local light = Instance.new("PointLight")
	light.Range = 14
	light.Brightness = 1.6
	light.Color = Color3.fromRGB(255, 246, 226)
	light.Parent = roof
	local gui = Instance.new("SurfaceGui")
	gui.Face = Enum.NormalId.Right -- the back wall's inside face looks toward +X
	gui.CanvasSize = Vector2.new(400, 300)
	gui.LightInfluence = 0
	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundColor3 = Color3.fromRGB(12, 14, 20)
	label.TextColor3 = Color3.fromRGB(255, 120, 60)
	label.Font = Enum.Font.Code
	label.TextScaled = true
	label.Text = "LOBBY"
	label.Parent = gui
	local display = carPart("Display", Vector3.new(0.1, 1.4, 2.4), Vector3.new(-cw / 2 + 0.36, 8.2, 0), Color3.new(0, 0, 0), Enum.Material.SmoothPlastic)
	gui.Parent = display
	-- the car's door lip reaches out to the shaft wall, where the building's fixed sill (in the tower model, with its
	-- own collider) takes over, so there's no gap to drop through stepping in or out. It stays inside the shaft.
	local dx0, dzA, dzB = A("DoorX"), A("DoorZ0"), A("DoorZ1")
	local shaftX = (A("ShaftMax") and A("ShaftMax").X) or (dx0 - 1.0)
	local lipEnd = shaftX - 0.1
	if lipEnd > cmax.X + 0.05 then
		local lw = lipEnd - cmax.X
		carPart("Lip", Vector3.new(lw, 0.35, dzB - dzA), Vector3.new(cw / 2 + lw / 2, 0, (dzA + dzB) / 2 - ccz), Color3.fromRGB(150, 152, 156), Enum.Material.DiamondPlate)
	end
	for _, p in car do
		p.Anchored = false
		p.Parent = model
		if p ~= floor then
			local w = Instance.new("WeldConstraint")
			w.Part0, w.Part1 = floor, p
			w.Parent = p
		end
	end
	-- the guide: a prismatic joint straight up the shaft, servo-driven between the two stops
	local rail = part("Guide", Vector3.new(0.4, 0.4, 0.4), cf * CFrame.new(ccx, s0 + 0.18, ccz))
	rail.Anchored, rail.Transparency, rail.CanCollide, rail.CanQuery = true, 1, false, false
	rail.Parent = model
	local up = CFrame.fromMatrix(Vector3.zero, Vector3.yAxis, -Vector3.xAxis) -- attachment primary axis = up
	local a0 = Instance.new("Attachment")
	a0.CFrame = up
	a0.Parent = rail
	local a1 = Instance.new("Attachment")
	a1.CFrame = up
	a1.Parent = floor
	local pc = Instance.new("PrismaticConstraint")
	pc.Attachment0, pc.Attachment1 = a0, a1
	pc.ActuatorType = Enum.ActuatorType.Servo
	pc.ServoMaxForce = 1e10
	pc.Speed = SPEED
	pc.LimitsEnabled = true
	pc.LowerLimit, pc.UpperLimit = -0.05, (s1 - s0) + 0.05
	pc.TargetPosition = 0
	pc.Parent = floor
	pcall(function()
		floor:SetNetworkOwner(nil)
	end)
	-- sliding shaft doors at both stops (two leaves meeting in the middle)
	local dx, dz0, dz1, dh = A("DoorX"), A("DoorZ0"), A("DoorZ1"), A("DoorH")
	local doors = {}
	for i, z in ipairs({ s0, s1 }) do
		local half = (dz1 - dz0) / 2
		local leaves = {}
		for k, zc in ipairs({ dz0 + half / 2, dz1 - half / 2 }) do
			local leaf = part("ShaftDoor", Vector3.new(0.25, dh, half), cf * CFrame.new(dx - 0.6, z + dh / 2, zc), Color3.fromRGB(190, 192, 196), Enum.Material.Metal)
			leaf.Anchored = true
			leaf.Parent = model
			leaves[k] = { part = leaf, closed = leaf.CFrame, open = leaf.CFrame * CFrame.new(0, 0, (k == 1 and -1 or 1) * (half - 0.2)) }
		end
		doors[i] = leaves
	end
	local function setDoors(i, open)
		for _, l in doors[i] do
			TweenService:Create(l.part, TweenInfo.new(1.0, Enum.EasingStyle.Quad), { CFrame = open and l.open or l.closed }):Play()
		end
		if open then
			chime(doors[i][1].part)
		end
		task.wait(1.0)
	end
	local at, busy = 1, false
	local function travel(i)
		label.Text = i == 2 and "▲ ROOF" or "▼ LOBBY"
		pc.TargetPosition = i == 1 and 0 or (s1 - s0)
		local t0 = os.clock()
		repeat
			task.wait(0.1)
		until math.abs(pc.CurrentPosition - pc.TargetPosition) < 0.2 or os.clock() - t0 > 40
		at = i
		label.Text = i == 2 and "ROOF" or "LOBBY"
	end
	local function trip(from, to)
		busy = true
		if at ~= from then
			travel(from)
		end
		setDoors(from, true)
		task.wait(6)
		setDoors(from, false)
		travel(to)
		setDoors(to, true)
		task.wait(7)
		setDoors(to, false)
		busy = false
	end
	-- call panels
	local function panel(pos, action, object)
		-- (the panel itself is modelled on the core wall; this is just the prompt's anchor in front of it)
		local p = part("CallPanel", Vector3.new(0.3, 1.6, 1.0), cf * CFrame.new(pos), Color3.fromRGB(40, 40, 46), Enum.Material.Metal)
		p.Anchored, p.Transparency, p.CanCollide, p.CanQuery, p.CanTouch = true, 1, false, false, false
		p.Parent = model
		local pp = Instance.new("ProximityPrompt")
		pp.ActionText = action
		pp.ObjectText = object
		pp.HoldDuration = 0.3
		pp.MaxActivationDistance = 9
		pp.RequiresLineOfSight = false
		pp.Parent = p
		return pp
	end
	local up_ = panel(A("Call0"), "Ride to the roof", ("Elevator · $%d (stairs are free)"):format(price))
	local down = panel(A("Call1"), "Ride down", "Elevator · free")
	up_.Triggered:Connect(function(player)
		if busy then
			Wallet.Notify(player, "The elevator is busy, one moment.")
			return
		end
		if not Wallet.Spend(player, price) then
			Wallet.Notify(player, ("The elevator costs $%d. The stairs are free!"):format(price), Color3.fromRGB(255, 120, 90))
			return
		end
		Wallet.Notify(player, ("Paid $%d. Step in, going up!"):format(price), Color3.fromRGB(120, 230, 140))
		task.spawn(trip, 1, 2)
	end)
	down.Triggered:Connect(function(player)
		if busy then
			Wallet.Notify(player, "The elevator is busy, one moment.")
			return
		end
		task.spawn(trip, 2, 1)
	end)
end

-- (only roots that are really in the world: a tower template sitting in ServerStorage gets no car)
task.spawn(function()
	while true do
		for _, r in CollectionService:GetTagged("NC_Elevator") do
			if r:IsDescendantOf(workspace) and not done[r] then
				task.spawn(setup, r)
			end
		end
		task.wait(2)
	end
end)
