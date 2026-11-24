--!nonstrict
-- NCVehicleWorld (ModuleScript, ServerScriptService): puts the vehicles from the customization system (NCVehicles +
-- NCLowriderKit) into the rest of the game. CarSpawner, PoliceAI and HomeService ask for a car by its template
-- name ("NorrbyDL84", "PoliceCruiser", "DirtBike"...) and get a Kit car with:
--   * the same attributes the old CarTemplates had: IsCar, CarName, TemplateName, PaintColor (+ Police on cop cars)
--   * an F prompt on every seat that swings that door open, seats you, and shuts it; doors also swing on the way out
--   * prompts on the trunk / hood / gas door / doors (the owner's car: only the owner)
--   * the raycast driving model: the driver's client simulates it (LowriderClient), parked cars rest anchored,
--     and Coast Patrol cars are driven here on the server (World.AIDrive)
-- Any name that isn't a Kit vehicle (or whose meshes aren't imported yet) returns nil, so callers fall back to the
-- old ServerStorage.CarTemplates.
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")

local Config = require(RS:WaitForChild("NCLowriderConfig"))
local Vehicles = require(RS:WaitForChild("NCVehicles"))
local Kit = require(RS:WaitForChild("NCLowriderKit"))
local Sim = require(RS:WaitForChild("NCVehicleSim"))

local World = {}

local SETTLE_IDLE = 25 -- an empty, stopped car rests (anchored) after this many seconds
local SETTLE_FAR = 300 -- ...or at once when the player simulating it is this far away / gone

local managed = {} -- [car] = { ai = bool, idleSince = number }

---------------------------------------------------------------------------------------------------- lookups
-- true when `name` is a Kit vehicle that can be built right now (data module installed and meshes imported)
function World.Has(name)
	local v = type(name) == "string" and Vehicles.ById[name]
	if not v or not Vehicles.Data(v.id) then
		return false
	end
	local f = Kit.AssetsFor(v.id)
	local car = f and f:FindFirstChild("Car")
	return car ~= nil and car:IsA("Model")
end

-- Kit vehicles for random parked / personal cars (never the police ones)
function World.CivilianPool()
	local out = {}
	for _, v in Vehicles.List do
		if not v.police and World.Has(v.id) then
			table.insert(out, v.id)
		end
	end
	return out
end

function World.IsKit(car)
	return car ~= nil and car:GetAttribute("NCLowrider") == true and car:GetAttribute("IsCar") == true
end

function World.DisplayName(name)
	local v = Vehicles.ById[name]
	return v and v.name or name
end

---------------------------------------------------------------------------------------------------- physics hand-off
local function chassis(car)
	return car.PrimaryPart
end

function World.SetSim(car, player)
	local ch = chassis(car)
	if not ch or not ch:IsDescendantOf(workspace) then
		return
	end
	if ch.Anchored then
		ch.Anchored = false
	end
	pcall(function()
		ch:SetNetworkOwner(player)
	end)
	if not player then
		ch.Drive.Force = Vector3.zero
		ch.Turn.Torque = Vector3.zero
	end
	car:SetAttribute("Sim", player and player.UserId or 0)
end

-- parks a car where it is: dropped onto the ground at its ride height, level, anchored
function World.Settle(car)
	local ch = chassis(car)
	if not ch or not ch:IsDescendantOf(workspace) then
		return
	end
	local origin = Kit.Origin(car)
	local look = origin.LookVector * Vector3.new(1, 0, 1)
	look = look.Magnitude > 0.05 and look.Unit or Vector3.new(0, 0, -1)
	local params = RaycastParams.new()
	local ignore = Sim.Folders()
	for _, p in Players:GetPlayers() do
		if p.Character then
			table.insert(ignore, p.Character)
		end
	end
	params.FilterDescendantsInstances = ignore
	params.FilterType = Enum.RaycastFilterType.Exclude
	local hit = workspace:Raycast(origin.Position + Vector3.new(0, 6, 0), Vector3.new(0, -40, 0), params)
	local ground = hit and hit.Position or origin.Position
	ch.Drive.Force = Vector3.zero
	ch.Turn.Torque = Vector3.zero
	ch.AssemblyLinearVelocity = Vector3.zero
	ch.AssemblyAngularVelocity = Vector3.zero
	ch.Anchored = true
	-- the chassis carries the Origin attachment at the ground point between the axles
	local target = CFrame.lookAt(ground, ground + look)
	car:PivotTo(target * origin:ToObjectSpace(car:GetPivot()))
	car:SetAttribute("Sim", 0)
	car:SetAttribute("SlipF", Vector2.zero) -- no tyre smoke on a parked car
	car:SetAttribute("SlipR", Vector2.zero)
end

---------------------------------------------------------------------------------------------------- doors (old ids)
-- the old cars' door ids (FL FR RL RR Hood Trunk Tailgate) on a Kit car's panels
local PANEL = { FL = "DoorL", FR = "DoorR", RL = "DoorRL", RR = "DoorRR", Hood = "Hood", Trunk = "Lid", Tailgate = "Lid" }

function World.SetDoor(car, id, open)
	local name = PANEL[id] or id
	return Kit.SetOpen(car, name, open)
end

function World.ToggleAll(car)
	local panels = Kit.Panels(car)
	local anyOpen = false
	for name in panels do
		if Kit.IsOpen(car, name) then
			anyOpen = true
		end
	end
	for name in panels do
		Kit.SetOpen(car, name, not anyOpen)
	end
end

---------------------------------------------------------------------------------------------------- building
local function lookFor(vid, paint, police)
	local look = Config.StarterFor(vid)
	if typeof(paint) == "Color3" then
		look.paint = Config.ToCustom(paint)
	elseif type(paint) == "string" and Config.ById.Paints[paint] then
		look.paint = paint
	elseif not police then
		local list = Config.Paints
		look.paint = list[math.random(#list)].id
	end
	look.susp = "stock"
	return look
end

local function ownerOf(car)
	return car:GetAttribute("Owner") or car:GetAttribute("GarageOwner")
end

-- F at a seat: swing its door open, sit down, shut it (the old cars' EnterPrompt, same key and text)
local function seatPrompts(car)
	for _, s in car:GetChildren() do
		if s:IsA("Seat") or s:IsA("VehicleSeat") then
			local door = Kit.DoorFor(car, s)
			local pp = Instance.new("ProximityPrompt")
			pp.Name = "EnterPrompt"
			pp.ActionText = s.Name == "DriveSeat" and "Drive" or "Ride"
			pp.ObjectText = car:GetAttribute("CarName")
			pp.KeyboardKeyCode = Enum.KeyCode.F
			pp.GamepadKeyCode = Enum.KeyCode.ButtonY
			pp.HoldDuration = 0
			pp.MaxActivationDistance = 8
			pp.RequiresLineOfSight = false
			pp.Parent = s
			pp.Triggered:Connect(function(player)
				local char = player.Character
				local hum = char and char:FindFirstChildOfClass("Humanoid")
				if not hum or hum.Health <= 0 or hum.SeatPart or s.Occupant or s.Disabled then
					return
				end
				local owner = ownerOf(car)
				if s.Name == "DriveSeat" and owner and owner ~= player.UserId then
					return -- someone's own car: anyone can ride along, only the owner drives
				end
				if door and not Kit.IsOpen(car, door) then
					Kit.SetOpen(car, door, true, 0.3)
					task.wait(0.35)
				end
				if s.Occupant == nil and hum.Parent then
					s:Sit(hum)
				end
				task.wait(0.5)
				if door and car.Parent then
					Kit.SetOpen(car, door, false, 0.35)
				end
			end)
			s:GetPropertyChangedSignal("Occupant"):Connect(function()
				pp.Enabled = s.Occupant == nil
			end)
		end
	end
end

-- builds a Kit car of vehicle `name` standing on the ground at cf (facing cf.LookVector). opts:
--   paint   Color3 or a paint id (default: a random paint)
--   police  true for Coast Patrol (seats stay usable until PoliceAI locks them)
--   parked  true: rests anchored until someone gets in
-- Returns nil when `name` can't be built (the caller uses the old template instead).
function World.Build(name, cf, opts)
	opts = opts or {}
	if not World.Has(name) then
		return nil
	end
	local vid = Vehicles.ById[name].id
	local car = Kit.BuildCar(cf, vid)
	local look = lookFor(vid, opts.paint, opts.police)
	car:SetAttribute("Look", HttpService:JSONEncode(look))
	car:SetAttribute("Susp", look.susp)
	Kit.ApplyLook(car, look)
	car.Name = name
	car:SetAttribute("IsCar", true)
	car:SetAttribute("CarName", Vehicles.ById[name].name)
	car:SetAttribute("TemplateName", vid)
	car:SetAttribute("PaintColor", Config.ColorOf("paint", look.paint) or Color3.new(1, 1, 1))
	if Vehicles.ById[name].police then
		car:SetAttribute("Police", true)
	end
	if opts.parked then
		car.PrimaryPart.Anchored = true
	end
	managed[car] = { ai = false, idleSince = os.clock() }
	car.Destroying:Once(function()
		managed[car] = nil
	end)

	seatPrompts(car)
	Kit.AddPanelPrompts(car, function(who)
		local owner = ownerOf(car)
		return owner == nil or owner == who.UserId
	end)
	Kit.AutoDoors(car)

	-- the driver's client simulates it; when they hop out it keeps simulating (parked) until the car settles
	local seat = car.DriveSeat
	seat:GetPropertyChangedSignal("Occupant"):Connect(function()
		local info = managed[car]
		if not info or info.ai then
			return
		end
		local hum = seat.Occupant
		local driver = hum and Players:GetPlayerFromCharacter(hum.Parent)
		local owner = ownerOf(car)
		if driver and owner and owner ~= driver.UserId then
			-- someone's own car (walked into the seat): only the owner drives
			task.defer(function()
				if seat.Occupant == hum then
					hum.Sit = false
					hum.Jump = true
				end
			end)
			return
		end
		if driver then
			car:SetAttribute("LastUsed", os.clock())
			World.SetSim(car, driver)
		end
		info.idleSince = os.clock()
	end)
	return car
end

-- a showroom copy (garage bays): anchored, nobody can sit in it, no prompts
function World.Display(name, paint, cf)
	local car = World.Build(name, cf, { paint = paint, parked = true })
	if not car then
		return nil
	end
	managed[car] = nil
	for _, d in car:GetDescendants() do
		if d:IsA("ProximityPrompt") then
			d:Destroy()
		elseif d:IsA("Seat") or d:IsA("VehicleSeat") then
			d.Disabled = true
		end
	end
	return car
end

---------------------------------------------------------------------------------------------------- AI driving
-- hands a car to the server for AI driving (Coast Patrol)
function World.MakeAI(car)
	local info = managed[car]
	if info then
		info.ai = true
	end
	World.SetSim(car, nil)
	car:SetAttribute("EngineOn", true) -- nobody sits in it, but the engine runs (NCCarLife)
	if car:GetAttribute("Police") then
		car:SetAttribute("Siren", 1) -- Coast Patrol units are always on a call: wail + light bar
		car:SetAttribute("Lights", 1)
	end
end

-- one server step of the driving model: throttle and steer in -1..1 (steer > 0 = right). Returns forward speed.
function World.AIDrive(car, throttle, steer, dt)
	local ch = chassis(car)
	if not ch or ch.Anchored then
		return 0
	end
	local s = Sim.State(car)
	Sim.Step(car, s, math.min(dt, 1 / 20), { throttle = throttle, steer = steer, park = false }, true)
	return s.fwdSpeed or 0
end

---------------------------------------------------------------------------------------------------- housekeeping
-- empty cars come to rest: anchored where they stopped, so nobody's client has to keep simulating them
task.spawn(function()
	while true do
		task.wait(2)
		local now = os.clock()
		for car, info in managed do
			local ch = car.Parent and chassis(car)
			if not ch then
				managed[car] = nil
			elseif not info.ai and not ch.Anchored and not (car:FindFirstChild("DriveSeat") and car.DriveSeat.Occupant) then
				local simId = car:GetAttribute("Sim") or 0
				local simPlayer = simId ~= 0 and Players:GetPlayerByUserId(simId) or nil
				local root = simPlayer and simPlayer.Character and simPlayer.Character:FindFirstChild("HumanoidRootPart")
				local far = not root or (root.Position - ch.Position).Magnitude > SETTLE_FAR
				if ch.AssemblyLinearVelocity.Magnitude > 2 then
					info.idleSince = now
				end
				if far or now - info.idleSince > SETTLE_IDLE then
					World.Settle(car)
				end
			end
		end
	end
end)

return World
