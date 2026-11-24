-- Neon Coast HomeService: private safe-house interiors, spawning, garage storage/buying, home style.
local Players = game:GetService("Players")
local DataStoreService = game:GetService("DataStoreService")
local RS = game:GetService("ReplicatedStorage")
local SS = game:GetService("ServerStorage")
local Remotes = RS:WaitForChild("Remotes")
local HomeConfig = require(RS:WaitForChild("HomeConfig"))
local InteriorKit = require(SS:WaitForChild("InteriorKit"))
local NC = require(script.Parent:WaitForChild("NC"))
local World = require(script.Parent:WaitForChild("NCVehicleWorld"))

local root = workspace:WaitForChild("NeonCoast")
local homesFolder = root:WaitForChild("Homes")
local safeHouse = root:WaitForChild("Districts"):WaitForChild("Palmgrove"):WaitForChild("SafeHouse")
local frontPoint = safeHouse:WaitForChild("FrontDoorPoint")
local garagePoint = safeHouse:WaitForChild("GarageDoorPoint")
local keypadPoint = safeHouse:WaitForChild("KeypadPoint")
local drivewaySpawn = safeHouse:WaitForChild("DrivewaySpawn")
while not _G.NeonCoastSpawner do task.wait() end
local Spawner = _G.NeonCoastSpawner

local store
pcall(function() store = DataStoreService:GetDataStore("NeonCoast_Home_v1") end)

local homes = {}      -- player -> {data=, model=, slot=, introDone=}
local usedSlots = {}

local function slotCFrame(slot)
	return CFrame.new(40000 + (slot % 10) * 600, 1500, 40000 + math.floor(slot / 10) * 600)
end
local function freeSlot()
	local s = 0
	while usedSlots[s] do s += 1 end
	usedSlots[s] = true
	return s
end

local function toColor(t) return t and Color3.fromRGB(t[1], t[2], t[3]) or HomeConfig.Paints[1] end
local function fromColor(c) return {math.floor(c.R * 255 + 0.5), math.floor(c.G * 255 + 0.5), math.floor(c.B * 255 + 0.5)} end

local function teleport(player, cf)
	local char = player.Character
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if not char or not hum then return end
	if hum.SeatPart then hum.Sit = false; task.wait(0.15) end
	pcall(function() player:RequestStreamAroundAsync(cf.Position, 5) end)
	char:PivotTo(cf)
end

local function garageSummary(home)
	local list = {}
	for i, e in ipairs(home.data.garage) do
		table.insert(list, {index = i, template = e.t, color = toColor(e.c), out = e.out == true})
	end
	return list
end
local function pushGarage(player)
	local home = homes[player]
	if home then Remotes.GarageUpdate:FireClient(player, garageSummary(home)) end
end

------------------------------------------------------------------ garage display (first two stored cars sit in the bays)
local function refreshDisplay(player)
	local home = homes[player]
	if not home or not home.model then return end
	local g = home.model:FindFirstChild("Garage")
	if not g then return end
	for _, c in ipairs(g:GetChildren()) do if c.Name == "DisplayCar" then c:Destroy() end end
	local bay = 1
	for i, e in ipairs(home.data.garage) do
		if bay > 2 then break end
		if not e.out then
			local bayPart = g:FindFirstChild("Bay" .. bay)
			-- the new vehicles sit on the bay floor; old templates are cloned and lifted by their ride height
			local car = bayPart and World.Display(e.t, toColor(e.c), bayPart.CFrame)
			local tpl = not car and SS.CarTemplates:FindFirstChild(e.t)
			if tpl then
				car = tpl:Clone()
				for _, p in ipairs(car:GetDescendants()) do
					if p:IsA("BasePart") then p.Anchored = true; if p:GetAttribute("Paint") then p.Color = toColor(e.c) end end
					if p:IsA("ProximityPrompt") or p:IsA("Constraint") then p:Destroy() end
					if p:IsA("Seat") or p:IsA("VehicleSeat") then p.Disabled = true end
				end
				car:PivotTo(bayPart.CFrame + Vector3.new(0, (car:GetAttribute("RideHeight") or 3.5), 0))
			end
			if car then
				car.Name = "DisplayCar"
				car.Parent = g
				local pp = Instance.new("ProximityPrompt"); pp.ActionText = "Drive Out"; pp.ObjectText = World.DisplayName(e.t); pp.MaxActivationDistance = 14; pp.RequiresLineOfSight = false
				pp.Parent = car.PrimaryPart
				local index = i
				pp.Triggered:Connect(function(who) if who == player then task.spawn(function() _G.NeonCoastDriveOut(player, index) end) end end)
				bay += 1
			end
		end
	end
end

------------------------------------------------------------------ interiors
local function buildInterior(player)
	local home = homes[player]
	if home.model then home.model:Destroy() end
	local m = InteriorKit.Build(home.data.layout, home.data.palette)
	m.Name = "Home_" .. player.UserId
	m:PivotTo(slotCFrame(home.slot))
	m.Parent = homesFolder
	home.model = m
	m:FindFirstChild("ExitPrompt", true).Triggered:Connect(function(who)
		if who ~= player then return end
		teleport(player, frontPoint.CFrame * CFrame.new(0, 0, -2))
	end)
	m:FindFirstChild("GaragePrompt", true).Triggered:Connect(function(who)
		if who ~= player then return end
		teleport(player, m.Garage.GarageSpawn.CFrame)
	end)
	m:FindFirstChild("GarageMenuPrompt", true).Triggered:Connect(function(who)
		if who ~= player then return end
		Remotes.OpenGarage:FireClient(player, garageSummary(home))
	end)
	m:FindFirstChild("StylePrompt", true).Triggered:Connect(function(who)
		if who ~= player then return end
		Remotes.OpenHomeStyle:FireClient(player, home.data.layout, home.data.palette)
	end)
	refreshDisplay(player)
	return m
end

local function goHome(player, toGarage)
	local home = homes[player]
	if not home or not home.model then return end
	local target = toGarage and home.model.Garage.GarageSpawn.CFrame or home.model.Spawn.CFrame
	teleport(player, target)
end

------------------------------------------------------------------ save / load
local function defaultData() return {layout = 1, palette = 1, garage = {}} end
local function save(player)
	local home = homes[player]
	if not store or not home then return end
	local clean = {layout = home.data.layout, palette = home.data.palette, garage = {}}
	for _, e in ipairs(home.data.garage) do table.insert(clean.garage, {t = e.t, c = e.c}) end
	pcall(function() store:SetAsync("home_" .. player.UserId, clean) end)
end

Players.PlayerAdded:Connect(function(player)
	local data
	if store then
		local ok, d = pcall(function() return store:GetAsync("home_" .. player.UserId) end)
		if ok and type(d) == "table" then data = d end
	end
	data = data or defaultData()
	data.garage = data.garage or {}
	data.layout = math.clamp(tonumber(data.layout) or 1, 1, #HomeConfig.Layouts)
	data.palette = math.clamp(tonumber(data.palette) or 1, 1, #HomeConfig.Palettes)
	homes[player] = {data = data, slot = freeSlot(), introDone = false}
	player:SetAttribute("IntroDone", false)
	buildInterior(player)

	player.CharacterAdded:Connect(function(char)
		local home = homes[player]
		if not home then return end
		-- a body swap from the Character Studio keeps its position: nothing to do
		if char:GetAttribute("Swapped") then return end
		local hrp = char:WaitForChild("HumanoidRootPart", 10)
		if not hrp then return end
		task.wait(0.2)
		if player:GetAttribute("Jailed") then return end
		if not home.introDone then
			-- stand in the front yard while the intro camera flies in
			char:PivotTo(frontPoint.CFrame * CFrame.new(0, 0, -14))
			hrp.Anchored = true
			-- the camera ends by flying through the big front window (house local (17, 7.9, -20)); the house faces +Z, its street side
			local houseCF = safeHouse:GetPivot()
			-- window spans local x 12.5..21.5; the porch column sits at x 17, so fly through at x 19.5 (railing ends at x 17)
			local windowPos = houseCF:PointToWorldSpace(Vector3.new(19.5, 7.9, -20))
			local outward = -houseCF.LookVector -- house front is local -Z
			if outward:Dot(windowPos - houseCF.Position) < 0 then outward = -outward end
			-- make sure the places the camera flies over are loaded for this player
			task.spawn(function()
				for _, pos in ipairs({Vector3.new(2600, 0, 0), windowPos, Vector3.new(2400, 0, -2600)}) do
					pcall(function() player:RequestStreamAroundAsync(pos, 4) end)
				end
			end)
			Remotes.PlayIntro:FireClient(player, {
				door = frontPoint.Position,
				window = windowPos,
				outward = outward,
				city = Vector3.new(2600, 0, 0),
				mapCenter = Vector3.new(-3500, 0, -1000),
			})
			-- safety: never leave someone frozen if the client never answers
			task.delay(30, function()
				if not home.introDone and player.Parent then
					home.introDone = true; player:SetAttribute("IntroDone", true)
					if hrp.Parent then hrp.Anchored = false end
					goHome(player)
				end
			end)
		else
			goHome(player) -- respawn at your safe house
		end
	end)
end)

Remotes.IntroDone.OnServerEvent:Connect(function(player)
	local home = homes[player]
	if not home or home.introDone then return end
	home.introDone = true
	player:SetAttribute("IntroDone", true)
	local hrp = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
	if hrp then hrp.Anchored = false end
	goHome(player)
end)

Players.PlayerRemoving:Connect(function(player)
	save(player)
	local home = homes[player]
	if home then
		if home.model then home.model:Destroy() end
		if home.outCar and home.outCar.Parent then home.outCar:Destroy() end
		usedSlots[home.slot] = nil
	end
	homes[player] = nil
end)
game:BindToClose(function() for _, p in ipairs(Players:GetPlayers()) do save(p) end end)

------------------------------------------------------------------ exterior prompts at the safe house
local function prompt(parent, action, object, key, dist)
	local pp = Instance.new("ProximityPrompt"); pp.ActionText = action; pp.ObjectText = object
	pp.KeyboardKeyCode = key or Enum.KeyCode.E; pp.MaxActivationDistance = dist or 10; pp.RequiresLineOfSight = false; pp.Parent = parent
	return pp
end
prompt(frontPoint, "Enter Home", "Safe House").Triggered:Connect(function(player)
	if (player:GetAttribute("Stars") or 0) > 0 then NC.Notify(player, "Lose the Coast Patrol before going home!", Color3.fromRGB(255,200,80)) return end
	goHome(player)
end)
-- phone "Home" app: head home from anywhere (not while wanted)
Remotes.GoHome.OnServerEvent:Connect(function(player)
	if (player:GetAttribute("Stars") or 0) > 0 then NC.Notify(player, "Lose the Coast Patrol before going home!", Color3.fromRGB(255,200,80)) return end
	if player:GetAttribute("Jailed") then return end
	goHome(player)
end)
prompt(keypadPoint, "Garage Menu", "Buy & Manage Cars").Triggered:Connect(function(player)
	local home = homes[player]
	if home then Remotes.OpenGarage:FireClient(player, garageSummary(home)) end
end)
local storePrompt = prompt(garagePoint, "Store Car", "Garage", Enum.KeyCode.E, 28)
storePrompt.HoldDuration = 0.5
-- the car's own passenger prompts also use E and sit closer; make sure this one is never hidden by them
storePrompt.Exclusivity = Enum.ProximityPromptExclusivity.AlwaysShow
storePrompt.Triggered:Connect(function(player)
	local home = homes[player]
	local _, hum = NC.GetRoot(player)
	local seat = hum and hum.SeatPart
	local car = seat and seat.Name == "DriveSeat" and seat.Parent
	if not home then return end
	if not car or not car:GetAttribute("IsCar") then NC.Notify(player, "Drive a car up to the garage to store it.", Color3.fromRGB(255,200,80)) return end
	if car:IsDescendantOf(root.Police) then return end
	if (player:GetAttribute("Stars") or 0) > 0 then NC.Notify(player, "Lose the Coast Patrol first!", Color3.fromRGB(255,200,80)) return end
	local owner, idx = car:GetAttribute("GarageOwner"), car:GetAttribute("GarageIndex")
	if owner == player.UserId and idx and home.data.garage[idx] then
		home.data.garage[idx].out = false
	else
		if #home.data.garage >= HomeConfig.GarageSlots then NC.Notify(player, "Your garage is full!", Color3.fromRGB(255,120,120)) return end
		local tname = car:GetAttribute("TemplateName")
		if not tname or not (World.Has(tname) or SS.CarTemplates:FindFirstChild(tname)) then return end
		table.insert(home.data.garage, {t = tname, c = fromColor(car:GetAttribute("PaintColor") or HomeConfig.Paints[1])})
		NC.Notify(player, "Car stored in your garage!", Color3.fromRGB(80,255,170))
	end
	if home.outCar == car then home.outCar = nil end
	hum.Sit = false
	task.wait(0.1)
	car:Destroy()
	refreshDisplay(player)
	pushGarage(player)
	goHome(player, true)
	save(player)
end)

------------------------------------------------------------------ drive a stored car out to the driveway
local function driveOut(player, index)
	local home = homes[player]
	local e = home and home.data.garage[index]
	if not e then return false, "No car there" end
	if e.out then return false, "That car is already out" end
	if home.outCar and home.outCar.Parent then
		-- one car out at a time: send the old one back
		local oi = home.outCar:GetAttribute("GarageIndex")
		if oi and home.data.garage[oi] then home.data.garage[oi].out = false end
		home.outCar:Destroy()
	end
	local look = drivewaySpawn.CFrame.LookVector * Vector3.new(1, 0, 1)
	local pos = drivewaySpawn.Position
	local car = Spawner.MakeCar(CFrame.lookAt(pos, pos + look), toColor(e.c), nil, e.t)
	car.Name = player.Name .. "'s " .. World.DisplayName(e.t)
	car:SetAttribute("GarageOwner", player.UserId)
	car:SetAttribute("GarageIndex", index)
	e.out = true
	home.outCar = car
	car.Destroying:Connect(function()
		if homes[player] and e.out and home.outCar == car then e.out = false; home.outCar = nil; refreshDisplay(player); pushGarage(player) end
	end)
	refreshDisplay(player)
	pushGarage(player)
	-- hop in
	teleport(player, car.DriveSeat.CFrame + Vector3.new(0, 3, 0))
	task.wait(0.25)
	local _, hum = NC.GetRoot(player)
	if hum and car.Parent then car.DriveSeat:Sit(hum) end
	return true
end
_G.NeonCoastDriveOut = driveOut

Remotes.GarageAction.OnServerInvoke = function(player, action, a, b)
	local home = homes[player]
	if not home then return false, "No home" end
	if action == "buy" then
		local entry
		for _, c in ipairs(HomeConfig.Cars) do if c.template == a then entry = c end end
		local paint = HomeConfig.Paints[tonumber(b) or 1]
		if not entry or not paint then return false, "Unknown car" end
		if #home.data.garage >= HomeConfig.GarageSlots then return false, "Garage is full" end
		local cash = NC.GetCash(player)
		if not cash or cash.Value < entry.price then return false, "Not enough cash" end
		cash.Value -= entry.price
		table.insert(home.data.garage, {t = entry.template, c = fromColor(paint)})
		refreshDisplay(player)
		save(player)
		return true, garageSummary(home)
	elseif action == "driveout" then
		local ok, msg = driveOut(player, tonumber(a))
		return ok, ok and garageSummary(home) or msg
	elseif action == "sell" then
		local i = tonumber(a)
		local e = home.data.garage[i]
		if not e or e.out then return false, "Can't sell that car right now" end
		local value = 300
		for _, c in ipairs(HomeConfig.Cars) do if c.template == e.t then value = math.floor(c.price * 0.4) end end
		table.remove(home.data.garage, i)
		NC.AddCash(player, value)
		refreshDisplay(player)
		save(player)
		return true, garageSummary(home)
	elseif action == "list" then
		return true, garageSummary(home)
	end
	return false, "Unknown action"
end

Remotes.SetHomeStyle.OnServerEvent:Connect(function(player, layout, palette)
	local home = homes[player]
	if not home then return end
	layout, palette = tonumber(layout), tonumber(palette)
	if not layout or not palette or not HomeConfig.Layouts[layout] or not HomeConfig.Palettes[palette] then return end
	home.data.layout, home.data.palette = layout, palette
	local hrp = NC.GetRoot(player)
	local inside = hrp and home.model and (hrp.Position - home.model:GetPivot().Position).Magnitude < 150
	buildInterior(player)
	if inside then goHome(player) end
	NC.Notify(player, ("Home restyled: %s / %s"):format(HomeConfig.Layouts[layout].name, HomeConfig.Palettes[palette].name), Color3.fromRGB(80,255,170))
	save(player)
end)
