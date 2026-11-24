--!nonstrict
-- LowriderService (server): Low & Slow Kustoms, the lowrider custom shop. Buy the Royale Lowrider, get it out of the
-- shop, and customize it: candy paint and finish, vinyl decals, Classic Wire 100-Spoke wheels, air bags or
-- hydraulics, a continental kit and a chrome pump setup in the trunk. Everything is saved (DataStore
-- NeonCoast_Garage_v1) and paid for with the game's Cash through NCWallet.
--
-- Where the shop goes: every part tagged NC_LowriderShopSpot gets a shop (the spot's front face = the street side;
-- the spot part is hidden). With no spot in the map, one shop is built at Config.ShopFallbackPosition.
-- Driving, hydraulics and the hop pit run on the driver's client (LowriderClient); this script hands each car's
-- physics to its driver (or to its owner while parked) and relays the corner heights so everyone sees the wheels.
local CollectionService = game:GetService("CollectionService")
local DataStoreService = game:GetService("DataStoreService")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local SSS = game:GetService("ServerScriptService")

local Config = require(RS:WaitForChild("NCLowriderConfig"))
local Kit = require(RS:WaitForChild("NCLowriderKit"))
local Vehicles = require(RS:WaitForChild("NCVehicles"))
local Wallet = require(SSS:WaitForChild("NCWallet"))

local Remotes = RS:FindFirstChild("Remotes")
if not Remotes then
	Remotes = Instance.new("Folder")
	Remotes.Name = "Remotes"
	Remotes.Parent = RS
end
local function remote(class, name)
	local r = Remotes:FindFirstChild(name)
	if not r then
		r = Instance.new(class)
		r.Name = name
		r.Parent = Remotes
	end
	return r
end
local ShopRF = remote("RemoteFunction", "LowriderShop") -- client asks: buy the car, spawn it, buy a look
local StateRE = remote("RemoteEvent", "LowriderState") -- driver -> server: corner heights (for other players' wheels)
local UiRE = remote("RemoteEvent", "LowriderUI") -- server -> client: open the shop screen / hop results
local HopRE = remote("RemoteEvent", "LowriderHop") -- client -> server: a measured hop
local WindowRE = remote("RemoteEvent", "VehicleWindow") -- client -> server: roll my window (or, driving, every window)
local ControlRE = remote("RemoteEvent", "VehicleControl") -- client -> server: horn, lights, indicators, siren (driver)

local carsFolder = workspace:FindFirstChild("Lowriders") or Instance.new("Folder")
carsFolder.Name = "Lowriders"
carsFolder.Parent = workspace

---------------------------------------------------------------------------------------------------- saving
local store
pcall(function()
	store = DataStoreService:GetDataStore("NeonCoast_Garage_v1")
end)

-- [player] = { garage = { [vehicleId] = { owned, look, unlocked = { ["key=value"] = true } } }, builds = { [vehicleId] = {...} },
--              active = vehicleId, bestHop = inches }
local profiles = {}

local function copy(t)
	local o = {}
	for k, v in t do
		o[k] = v
	end
	return o
end

local cleanLook = Config.CleanLook

-- one vehicle's entry in a player's garage (created on first use)
local function G(prof, vid)
	vid = Vehicles.Get(vid).id
	local g = prof.garage[vid]
	if not g then
		g = { owned = false, look = Config.StarterFor(vid), unlocked = {} }
		prof.garage[vid] = g
	end
	return g, vid
end

local function publish(p)
	local prof = profiles[p]
	if not prof then
		return
	end
	local any = false
	for _, g in prof.garage do
		any = any or g.owned
	end
	p:SetAttribute("OwnsLowrider", any) -- owns any vehicle
	p:SetAttribute("Garage", HttpService:JSONEncode(prof.garage))
	p:SetAttribute("LowriderBuilds", HttpService:JSONEncode(prof.builds))
	p:SetAttribute("ActiveVehicle", prof.active)
	p:SetAttribute("BestHop", prof.bestHop)
end

local function cleanBuilds(list, vid)
	local out = {}
	for i = 1, Config.BuildSlots do
		local b = type(list) == "table" and list[i]
		out[i] = type(b) == "table" and cleanLook(b, vid) or false
	end
	return out
end

local function load(p)
	local prof = { garage = {}, builds = {}, active = Vehicles.Default, bestHop = 0 }
	if store then
		local ok, data = pcall(function()
			return store:GetAsync("u" .. p.UserId)
		end)
		if ok and type(data) == "table" and type(data.lowrider) == "table" then
			local d = data.lowrider
			prof.bestHop = tonumber(d.bestHop) or 0
			if type(d.garage) == "table" then
				for vid, g in d.garage do
					if Vehicles.ById[vid] and type(g) == "table" then
						prof.garage[vid] = { owned = g.owned == true, look = cleanLook(g.look, vid), unlocked = Config.MigrateUnlocked(g.unlocked) }
					end
				end
				for vid, list in (type(d.builds) == "table" and d.builds or {}) do
					if Vehicles.ById[vid] then
						prof.builds[vid] = cleanBuilds(list, vid)
					end
				end
				prof.active = Vehicles.ById[d.active] and d.active or Vehicles.Default
			else -- the first versions saved just the Royale at the top level
				prof.garage.royale = { owned = d.owned == true, look = cleanLook(d.look, "royale"), unlocked = Config.MigrateUnlocked(d.unlocked) }
				prof.builds.royale = cleanBuilds(d.builds, "royale")
			end
		end
	end
	profiles[p] = prof
	publish(p)
end

local function save(p)
	local prof = profiles[p]
	if not store or not prof then
		return
	end
	for _ = 1, 3 do
		local ok = pcall(function()
			store:UpdateAsync("u" .. p.UserId, function(old)
				old = type(old) == "table" and old or {}
				old.lowrider = { garage = prof.garage, builds = prof.builds, active = prof.active, bestHop = prof.bestHop }
				return old
			end)
		end)
		if ok then
			return
		end
		task.wait(2)
	end
end

---------------------------------------------------------------------------------------------------- shops
local shops = {}

local function buildShopAt(cf)
	local shop = Kit.BuildShop(cf)
	shop.Parent = workspace
	table.insert(shops, shop)
	-- counter: customize; car spawn: buy / get the car
	local pp = Instance.new("ProximityPrompt")
	pp.Name = "Customize"
	pp.ActionText = "Customize your ride"
	pp.ObjectText = "Low & Slow Kustoms"
	pp.HoldDuration = 0.2
	pp.MaxActivationDistance = 12
	pp.RequiresLineOfSight = false
	pp.Parent = shop.Counter
	pp.Triggered:Connect(function(player)
		UiRE:FireClient(player, "open", shop)
	end)
	local zone = shop.CustomZone
	local zp = pp:Clone()
	zp.MaxActivationDistance = 16
	zp.Parent = zone
	zp.Triggered:Connect(function(player)
		UiRE:FireClient(player, "open", shop)
	end)
	local gp = Instance.new("ProximityPrompt")
	gp.Name = "GetCar"
	gp.ActionText = "Get your lowrider"
	gp.ObjectText = Config.CarName
	gp.HoldDuration = 0.4
	gp.MaxActivationDistance = 14
	gp.RequiresLineOfSight = false
	gp.Parent = shop.CarSpawn
	gp.Triggered:Connect(function(player)
		UiRE:FireClient(player, "open", shop)
	end)
	return shop
end

local function nearestShop(pos)
	local best, bd = nil, math.huge
	for _, s in shops do
		if s.Parent then
			local d = (s.PrimaryPart.Position - pos).Magnitude
			if d < bd then
				best, bd = s, d
			end
		end
	end
	return best, bd
end

task.spawn(function()
	local done = {}
	local function fromSpot(spot)
		if done[spot] or not spot:IsDescendantOf(workspace) then
			return
		end
		done[spot] = true
		local cf = spot.CFrame * CFrame.new(0, -spot.Size.Y / 2, 0)
		local _, yaw = cf:ToEulerAnglesYXZ()
		spot.Transparency, spot.CanCollide, spot.CanQuery = 1, false, false
		buildShopAt(CFrame.new(cf.Position) * CFrame.Angles(0, yaw, 0))
	end
	for _, s in CollectionService:GetTagged("NC_LowriderShopSpot") do
		fromSpot(s)
	end
	CollectionService:GetInstanceAddedSignal("NC_LowriderShopSpot"):Connect(fromSpot)
	task.wait(6)
	if #shops == 0 then
		local pos = Config.ShopFallbackPosition
		local params = RaycastParams.new()
		params.FilterDescendantsInstances = { carsFolder }
		params.FilterType = Enum.RaycastFilterType.Exclude
		local hit = workspace:Raycast(pos + Vector3.new(0, 600, 0), Vector3.new(0, -1200, 0), params)
		buildShopAt(CFrame.new(hit and hit.Position or pos))
		warn("LowriderService: no NC_LowriderShopSpot in the map, so the shop was built at Config.ShopFallbackPosition " .. tostring(pos))
	end
end)

---------------------------------------------------------------------------------------------------- cars
local cars = {} -- [player] = car

local function setSim(car, player)
	local ch = car.PrimaryPart
	if not ch or not ch:IsDescendantOf(workspace) then
		return
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

local function despawn(player)
	local car = cars[player]
	if car then
		car:Destroy()
		cars[player] = nil
	end
end

local function spawnCar(player, vid)
	local prof = profiles[player]
	if not prof then
		return false, "Still loading."
	end
	local g
	g, vid = G(prof, vid or prof.active)
	if not g.owned or not Vehicles.Data(vid) then
		return false, "You don't own that one yet."
	end
	prof.active = vid
	player:SetAttribute("ActiveVehicle", vid)
	local char = player.Character
	local root = char and char:FindFirstChild("HumanoidRootPart")
	local shop = root and nearestShop(root.Position)
	if not shop then
		return false, "Head to Low & Slow Kustoms to get your ride."
	end
	despawn(player)
	local spot = shop.CarSpawn.CFrame * CFrame.new(0, -0.1, 0)
	-- step along the lot if someone's car is already there
	local params = OverlapParams.new()
	params.FilterDescendantsInstances = { carsFolder }
	params.FilterType = Enum.RaycastFilterType.Include
	for k = 0, 4 do
		local cf = spot * CFrame.new(k * 10, 0, 0)
		if #workspace:GetPartBoundsInBox(cf * CFrame.new(0, 3, 0), Vector3.new(8, 5, 22), params) == 0 then
			spot = cf
			break
		end
	end
	local car = Kit.BuildCar(spot * CFrame.new(0, 0.6, 0), vid)
	car.Name = player.Name .. "'s " .. Vehicles.Get(vid).name
	car:SetAttribute("Owner", player.UserId)
	car:SetAttribute("Look", HttpService:JSONEncode(g.look))
	car:SetAttribute("Susp", g.look.susp)
	Kit.ApplyLook(car, g.look)
	car.Parent = carsFolder
	cars[player] = car
	setSim(car, player)

	local seat = car.DriveSeat
	seat:GetPropertyChangedSignal("Occupant"):Connect(function()
		local hum = seat.Occupant
		local driver = hum and Players:GetPlayerFromCharacter(hum.Parent)
		if driver and driver ~= player then
			-- only the owner drives (others can ride in the other seats)
			task.defer(function()
				if seat.Occupant == hum then
					hum.Sit = false
					hum.Jump = true
				end
			end)
			Wallet.Notify(driver, "That's " .. player.DisplayName .. "'s ride. Hop in a passenger seat.")
			return
		end
		setSim(car, driver or (player.Parent and player) or nil)
	end)
	-- opening panels: a prompt on the trunk, hood and gas door (and each door, to show the car off). Doors also
	-- swing open by themselves for a moment when someone gets in or out on that side.
	Kit.AddPanelPrompts(car, function(who)
		return who == player
	end)
	Kit.AutoDoors(car)
	return true
end

---------------------------------------------------------------------------------------------------- shop purchases
local function nearShop(player, radius)
	local char = player.Character
	local root = char and char:FindFirstChild("HumanoidRootPart")
	if not root then
		return false
	end
	local _, d = nearestShop(root.Position)
	return d <= radius
end

ShopRF.OnServerInvoke = function(player, action, arg)
	local prof = profiles[player]
	if not prof then
		return false, "Still loading, try again."
	end
	if action == "buyCar" then -- arg = vehicle id
		local veh = Vehicles.ById[arg] or Vehicles.Get(nil)
		local g, vid = G(prof, veh.id)
		if g.owned then
			return spawnCar(player, vid)
		end
		if not Vehicles.Data(vid) then
			return false, "That one isn't in the shop yet."
		end
		if not nearShop(player, 80) then
			return false, "Buy it at Low & Slow Kustoms."
		end
		if not Wallet.Spend(player, veh.price) then
			return false, ("The %s costs $%d. Earn some more cash first."):format(veh.name, veh.price)
		end
		g.owned = true
		publish(player)
		task.spawn(save, player)
		local ok, msg = spawnCar(player, vid)
		return true, ok and "It's yours! Hop in." or msg
	elseif action == "spawn" then -- arg = vehicle id (or nil for the last one)
		return spawnCar(player, Vehicles.ById[arg] and arg or nil)
	elseif action == "saveBuild" then
		-- arg = { slot = 1..BuildSlots, vehicle = id, look = {...} } or no look to clear it
		local slot = type(arg) == "table" and tonumber(arg.slot)
		if not slot or slot ~= math.floor(slot) or slot < 1 or slot > Config.BuildSlots then
			return false, "?"
		end
		local vid = Vehicles.ById[arg.vehicle] and arg.vehicle or Vehicles.Of(cars[player])
		local list = prof.builds[vid] or cleanBuilds(nil, vid)
		list[slot] = type(arg.look) == "table" and cleanLook(arg.look, vid) or false
		prof.builds[vid] = list
		publish(player)
		task.spawn(save, player)
		return true, list[slot] and ("Saved to slot %d."):format(slot) or ("Slot %d cleared."):format(slot)
	elseif action == "quote" then
		local car = cars[player]
		local g, vid = G(prof, Vehicles.Of(car))
		return true, (Config.Quote(g.look, cleanLook(arg, vid), g.unlocked))
	elseif action == "buyLook" then
		local car = cars[player]
		if not car or not nearShop(player, 80) then
			return false, "Bring your ride to the shop."
		end
		local g, vid = G(prof, Vehicles.Of(car))
		if not g.owned then
			return false, "Buy it first."
		end
		local shop, d = nearestShop(car.PrimaryPart.Position)
		if not shop or d > Config.CustomizeRadius + 30 then
			return false, "Park it in the shop first."
		end
		local look = cleanLook(arg, vid)
		local total, items = Config.Quote(g.look, look, g.unlocked)
		if total > 0 and not Wallet.Spend(player, total) then
			return false, ("That build costs $%d. You have $%d."):format(total, Wallet.Balance(player))
		end
		for tag in items do
			g.unlocked[tag] = true
		end
		-- whatever you had on before stays unlocked, so you can switch back for free
		for key, v in g.look do
			g.unlocked[key .. "=" .. tostring(v)] = true
		end
		g.look = look
		publish(player)
		car:SetAttribute("Look", HttpService:JSONEncode(look))
		car:SetAttribute("Susp", look.susp)
		Kit.ApplyLook(car, look)
		task.spawn(save, player)
		return true, total > 0 and ("Done! $%d. Looking clean."):format(total) or "Done!"
	end
	return false, "?"
end

---------------------------------------------------------------------------------------------------- corner heights + hops
local lastState = {}
StateRE.OnServerEvent:Connect(function(player, carModel, fl, fr, rl, rr, mode, slipF, slipR)
	local car = cars[player]
	if carModel ~= car or not car then
		-- passengers' clients never send; a driver of someone else's car is refused at the seat. The city's cars
		-- (NCVehicleWorld) report from whoever is simulating them.
		if typeof(carModel) == "Instance" and carModel:IsA("Model") and carModel:GetAttribute("IsCar")
			and carModel:GetAttribute("NCLowrider") and carModel:GetAttribute("Sim") == player.UserId then
			car = carModel
		else
			return
		end
	end
	local now = os.clock()
	if lastState[player] and now - lastState[player] < 0.05 then
		return
	end
	lastState[player] = now
	local function clamp(v)
		return type(v) == "number" and v == v and math.clamp(v, -1, 3) or 0
	end
	car:SetAttribute("HydF", Vector2.new(clamp(fl), clamp(fr)))
	car:SetAttribute("HydR", Vector2.new(clamp(rl), clamp(rr)))
	car:SetAttribute("HydMode", type(mode) == "string" and mode:sub(1, 12) or "")
	-- how hard each tyre is slipping (0..1): everyone else's clients draw the smoke and skid marks from it
	local function slip(v)
		if typeof(v) ~= "Vector2" or v.X ~= v.X or v.Y ~= v.Y then
			return Vector2.zero
		end
		return Vector2.new(math.floor(math.clamp(v.X, 0, 1) * 20 + 0.5) / 20, math.floor(math.clamp(v.Y, 0, 1) * 20 + 0.5) / 20)
	end
	local sf, sr = slip(slipF), slip(slipR)
	if car:GetAttribute("SlipF") ~= sf then
		car:SetAttribute("SlipF", sf)
	end
	if car:GetAttribute("SlipR") ~= sr then
		car:SetAttribute("SlipR", sr)
	end
end)

local function updateBoards()
	local list = {}
	for p, prof in profiles do
		if prof.bestHop > 0 then
			table.insert(list, { p.DisplayName, prof.bestHop })
		end
	end
	table.sort(list, function(a, b)
		return a[2] > b[2]
	end)
	local lines = { "HOP PIT · TOP HOPPERS" }
	for i = 1, math.min(5, #list) do
		table.insert(lines, ("%d. %s  %d in"):format(i, list[i][1], list[i][2]))
	end
	for _, shop in shops do
		local base = shop:FindFirstChild("HopBoardBase")
		if base then
			local gui = base:FindFirstChild("Board")
			if not gui then
				gui = Instance.new("BillboardGui")
				gui.Name = "Board"
				gui.Size = UDim2.fromScale(10, 6)
				gui.StudsOffset = Vector3.new(0, 15, 0)
				gui.LightInfluence = 0
				gui.MaxDistance = 120
				gui.Parent = base
				local t = Instance.new("TextLabel")
				t.Name = "Text"
				t.Size = UDim2.fromScale(1, 1)
				t.BackgroundColor3 = Color3.fromRGB(16, 16, 20)
				t.BackgroundTransparency = 0.25
				t.TextColor3 = Color3.fromRGB(255, 214, 70)
				t.Font = Enum.Font.GothamBold
				t.TextScaled = true
				t.Parent = gui
			end
			gui.Text.Text = table.concat(lines, "\n")
		end
	end
end

-- R in any Kit vehicle steps your window up -> half -> down; the driver with Shift held steps every window
local windowCooldown = {}
WindowRE.OnServerEvent:Connect(function(player, all)
	local now = os.clock()
	if (windowCooldown[player] or 0) > now then
		return
	end
	windowCooldown[player] = now + 0.25
	local hum = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
	local seat = hum and hum.SeatPart
	local car = seat and seat.Parent
	if not (car and car:IsA("Model") and car:GetAttribute("NCLowrider")) then
		return
	end
	if all == true and seat.Name == "DriveSeat" then
		Kit.StepWindow(car, nil)
	else
		local name = Kit.WindowFor(car, seat)
		if name then
			Kit.StepWindow(car, name)
		end
	end
end)
Players.PlayerRemoving:Connect(function(p)
	windowCooldown[p] = nil
end)

-- the driver's horn / lights / indicators / siren, as car attributes every client turns into sound and light
-- (NCCarLife): Horn bool, Lights 0 off / 1 on / 2 high beams, Signal "L" / "R" / "H" / "", Siren 0 / 1 wail / 2 yelp
local honking = {} -- [player] = car
ControlRE.OnServerEvent:Connect(function(player, action, value)
	local hum = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
	local seat = hum and hum.SeatPart
	local car = seat and seat.Parent
	if not (car and seat.Name == "DriveSeat" and car:IsA("Model") and car:GetAttribute("NCLowrider")) then
		return
	end
	if action == "horn" then
		car:SetAttribute("Horn", value == true)
		honking[player] = value == true and car or nil
	elseif action == "lights" and (value == 0 or value == 1 or value == 2) then
		car:SetAttribute("Lights", value)
	elseif action == "signal" and (value == "L" or value == "R" or value == "H" or value == "") then
		car:SetAttribute("Signal", value)
	elseif action == "siren" and car:GetAttribute("Police") and (value == 0 or value == 1 or value == 2) then
		car:SetAttribute("Siren", value)
	end
end)
local function stopHorn(p)
	local car = honking[p]
	honking[p] = nil
	if car and car.Parent then
		car:SetAttribute("Horn", false)
	end
end
Players.PlayerRemoving:Connect(stopHorn)
-- getting out lets go of the horn
task.spawn(function()
	while true do
		task.wait(0.5)
		for p, car in honking do
			local hum = p.Character and p.Character:FindFirstChildOfClass("Humanoid")
			if not (hum and hum.SeatPart and hum.SeatPart.Parent == car) then
				stopHorn(p)
			end
		end
	end
end)

HopRE.OnServerEvent:Connect(function(player, inches)
	local prof = profiles[player]
	local car = cars[player]
	if not prof or not car or type(inches) ~= "number" or inches ~= inches then
		return
	end
	local susp = Config.Susp(G(prof, Vehicles.Of(car)).look.susp)
	if susp.hop <= 0 then
		return
	end
	-- the most a launch at this kit's hop speed (+ a perfect-timing bonus) could reach
	local maxStuds = (susp.hop * 1.6) ^ 2 / (2 * workspace.Gravity) + 2.5
	inches = math.clamp(math.floor(inches), 0, Config.Inches(maxStuds))
	if inches > prof.bestHop then
		prof.bestHop = inches
		player:SetAttribute("BestHop", inches)
		task.spawn(save, player)
		updateBoards()
	end
end)

---------------------------------------------------------------------------------------------------- players
Players.PlayerAdded:Connect(function(p)
	load(p)
	updateBoards()
end)
for _, p in Players:GetPlayers() do
	task.spawn(load, p)
end
Players.PlayerRemoving:Connect(function(p)
	save(p)
	despawn(p)
	profiles[p] = nil
	lastState[p] = nil
	updateBoards()
end)
game:BindToClose(function()
	for _, p in Players:GetPlayers() do
		task.spawn(save, p)
	end
	task.wait(2)
end)
