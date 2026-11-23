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

local carsFolder = workspace:FindFirstChild("Lowriders") or Instance.new("Folder")
carsFolder.Name = "Lowriders"
carsFolder.Parent = workspace

---------------------------------------------------------------------------------------------------- saving
local store
pcall(function()
	store = DataStoreService:GetDataStore("NeonCoast_Garage_v1")
end)

local profiles = {} -- [player] = { owned = bool, look = {}, unlocked = { ["Paints:id"] = true }, bestHop = inches }

local function copy(t)
	local o = {}
	for k, v in t do
		o[k] = v
	end
	return o
end

local cleanLook = Config.CleanLook

local function load(p)
	local prof = { owned = false, look = copy(Config.StarterLook), unlocked = {}, bestHop = 0, builds = {} }
	if store then
		local ok, data = pcall(function()
			return store:GetAsync("u" .. p.UserId)
		end)
		if ok and type(data) == "table" and type(data.lowrider) == "table" then
			local d = data.lowrider
			prof.owned = d.owned == true
			prof.look = cleanLook(d.look)
			prof.unlocked = Config.MigrateUnlocked(d.unlocked)
			prof.bestHop = tonumber(d.bestHop) or 0
			for i = 1, Config.BuildSlots do -- saved builds (designs only; they still have to be bought)
				local b = type(d.builds) == "table" and d.builds[i]
				prof.builds[i] = type(b) == "table" and cleanLook(b) or false
			end
		end
	end
	profiles[p] = prof
	p:SetAttribute("OwnsLowrider", prof.owned)
	p:SetAttribute("LowriderLook", HttpService:JSONEncode(prof.look))
	p:SetAttribute("LowriderUnlocked", HttpService:JSONEncode(prof.unlocked))
	p:SetAttribute("BestHop", prof.bestHop)
	p:SetAttribute("LowriderBuilds", HttpService:JSONEncode(prof.builds))
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
				old.lowrider = { owned = prof.owned, look = prof.look, unlocked = prof.unlocked, bestHop = prof.bestHop, builds = prof.builds }
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

local function spawnCar(player)
	local prof = profiles[player]
	if not prof or not prof.owned then
		return false, "You don't own a lowrider yet."
	end
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
	local car = Kit.BuildCar(spot * CFrame.new(0, 0.6, 0))
	car.Name = player.Name .. "'s Lowrider"
	car:SetAttribute("Owner", player.UserId)
	car:SetAttribute("Look", HttpService:JSONEncode(prof.look))
	car:SetAttribute("Susp", prof.look.susp)
	Kit.ApplyLook(car, prof.look)
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
	-- trunk: show off the pump setup
	local lid = car.Lid.LidRoot
	local tp = Instance.new("ProximityPrompt")
	tp.Name = "Trunk"
	tp.ActionText = "Pop the trunk"
	tp.ObjectText = "Pump setup"
	tp.HoldDuration = 0.2
	tp.MaxActivationDistance = 8
	tp.RequiresLineOfSight = false
	tp.Parent = lid
	local open = false
	local base = lid.LidHinge.C0
	tp.Triggered:Connect(function(who)
		if who ~= player then
			return
		end
		open = not open
		tp.ActionText = open and "Close the trunk" or "Pop the trunk"
		local steps = 12
		for k = 1, steps do
			local a = (open and k / steps or 1 - k / steps) * math.rad(62)
			lid.LidHinge.C0 = base * CFrame.Angles(-a, 0, 0)
			task.wait(0.03)
		end
	end)
	return true
end

---------------------------------------------------------------------------------------------------- shop purchases
-- what a new look costs on top of what the player already has unlocked (Config.Quote, shared with the client)
local function quote(prof, look)
	return Config.Quote(prof.look, look, prof.unlocked)
end

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
	if action == "buyCar" then
		if prof.owned then
			return true, "You already own it."
		end
		if not nearShop(player, 80) then
			return false, "Buy it at Low & Slow Kustoms."
		end
		if not Wallet.Spend(player, Config.CarPrice) then
			return false, ("The %s costs $%d. Earn some more cash first."):format(Config.CarName, Config.CarPrice)
		end
		prof.owned = true
		player:SetAttribute("OwnsLowrider", true)
		task.spawn(save, player)
		local ok, msg = spawnCar(player)
		return true, ok and "It's yours! Hop in." or msg
	elseif action == "spawn" then
		return spawnCar(player)
	elseif action == "saveBuild" then
		-- arg = { slot = 1..BuildSlots, look = {...} } or { slot = n } to clear it
		local slot = type(arg) == "table" and tonumber(arg.slot)
		if not slot or slot ~= math.floor(slot) or slot < 1 or slot > Config.BuildSlots then
			return false, "?"
		end
		prof.builds[slot] = type(arg.look) == "table" and cleanLook(arg.look) or false
		for i = 1, Config.BuildSlots do
			prof.builds[i] = prof.builds[i] or false
		end
		player:SetAttribute("LowriderBuilds", HttpService:JSONEncode(prof.builds))
		task.spawn(save, player)
		return true, prof.builds[slot] and ("Saved to slot %d."):format(slot) or ("Slot %d cleared."):format(slot)
	elseif action == "quote" then
		local total = quote(prof, cleanLook(arg))
		return true, total
	elseif action == "buyLook" then
		if not prof.owned then
			return false, "Buy the car first."
		end
		local car = cars[player]
		if not car or not nearShop(player, 80) then
			return false, "Bring your lowrider to the shop."
		end
		local root = car.PrimaryPart
		local shop, d = nearestShop(root.Position)
		if not shop or d > Config.CustomizeRadius + 30 then
			return false, "Park your lowrider in the shop first."
		end
		local look = cleanLook(arg)
		local total, items = quote(prof, look)
		if total > 0 and not Wallet.Spend(player, total) then
			return false, ("That build costs $%d. You have $%d."):format(total, Wallet.Balance(player))
		end
		for tag in items do
			prof.unlocked[tag] = true
		end
		-- whatever you had on before stays unlocked, so you can switch back for free
		for key, v in prof.look do
			prof.unlocked[key .. "=" .. tostring(v)] = true
		end
		prof.look = look
		player:SetAttribute("LowriderLook", HttpService:JSONEncode(look))
		player:SetAttribute("LowriderUnlocked", HttpService:JSONEncode(prof.unlocked))
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
StateRE.OnServerEvent:Connect(function(player, carModel, fl, fr, rl, rr, mode)
	local car = cars[player]
	if carModel ~= car or not car then
		-- passengers' clients never send; a driver of someone else's car is refused at the seat
		return
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

HopRE.OnServerEvent:Connect(function(player, inches)
	local prof = profiles[player]
	local car = cars[player]
	if not prof or not car or type(inches) ~= "number" or inches ~= inches then
		return
	end
	local susp = Config.Susp(prof.look.susp)
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
