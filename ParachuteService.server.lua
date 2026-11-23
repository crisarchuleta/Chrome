--!nonstrict
-- ParachuteService (server): buy a parachute with earned Cash (once; it's yours for good, saved), and the state
-- relay so every player sees everyone's skydive, canopy and backpack. ParachuteClient does the flying.
-- Shops: any part tagged NC_ParachuteShop (BuildingKit makes them at the office tower's lobby kiosk and in the
-- roof's mechanical room). Ownership is saved in the DataStore NeonCoast_Gear_v1 and shows as the player
-- attribute HasParachute (the client puts the pack on your back and lets you open a canopy).
local CollectionService = game:GetService("CollectionService")
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local SSS = game:GetService("ServerScriptService")

local PRICE = 500
local Wallet = require(SSS:WaitForChild("NCWallet"))

local Remotes = RS:FindFirstChild("Remotes")
if not Remotes then
	Remotes = Instance.new("Folder")
	Remotes.Name = "Remotes"
	Remotes.Parent = RS
end
local StateRE = Remotes:FindFirstChild("ParachuteState") or Instance.new("RemoteEvent")
StateRE.Name = "ParachuteState"
StateRE.Parent = Remotes

local store
pcall(function()
	store = DataStoreService:GetDataStore("NeonCoast_Gear_v1")
end)

local function key(p)
	return "u" .. p.UserId
end

local function load(p)
	if not store then
		return
	end
	local ok, data = pcall(function()
		return store:GetAsync(key(p))
	end)
	if ok and type(data) == "table" and data.parachute then
		p:SetAttribute("HasParachute", true)
	end
end

local function save(p)
	if not store then
		return
	end
	local owned = p:GetAttribute("HasParachute") == true
	for _ = 1, 3 do
		local ok = pcall(function()
			store:UpdateAsync(key(p), function(old)
				old = type(old) == "table" and old or {}
				old.parachute = owned or old.parachute
				return old
			end)
		end)
		if ok then
			return
		end
		task.wait(2)
	end
end

Players.PlayerAdded:Connect(load)
for _, p in Players:GetPlayers() do
	task.spawn(load, p)
end

-- shops
local done = setmetatable({}, { __mode = "k" })
local function setupShop(part)
	if done[part] or not part:IsDescendantOf(workspace) then
		return
	end
	done[part] = true
	local old = part:FindFirstChild("BuyParachute") -- left on a cloned copy, with nothing listening
	if old then
		old:Destroy()
	end
	local pp = Instance.new("ProximityPrompt")
	pp.Name = "BuyParachute"
	pp.ActionText = "Buy parachute"
	pp.ObjectText = ("Skydive gear · $%d"):format(PRICE)
	pp.HoldDuration = 0.4
	pp.MaxActivationDistance = 9
	pp.RequiresLineOfSight = false
	pp.Parent = part
	pp.Triggered:Connect(function(player)
		if player:GetAttribute("HasParachute") then
			Wallet.Notify(player, "You already own a parachute. Jump off something tall: SPACE opens it, C cuts away.")
			return
		end
		if not Wallet.Spend(player, PRICE) then
			Wallet.Notify(player, ("A parachute costs $%d. Earn some more cash first."):format(PRICE), Color3.fromRGB(255, 120, 90))
			return
		end
		player:SetAttribute("HasParachute", true)
		Wallet.Notify(player, "Parachute bought! Jump from a rooftop. Look down to dive, SPACE to open, C to cut away.", Color3.fromRGB(120, 230, 140))
		task.spawn(save, player)
	end)
end
task.spawn(function()
	while true do
		for _, p in CollectionService:GetTagged("NC_ParachuteShop") do
			setupShop(p)
		end
		task.wait(2)
	end
end)

-- what each player's chute is doing, for everyone else's screen
local VALID = { freefall = true, canopy = true }
StateRE.OnServerEvent:Connect(function(player, st)
	local char = player.Character
	if not char then
		return
	end
	if st == "canopy" and not player:GetAttribute("HasParachute") then
		return
	end
	char:SetAttribute("ChuteState", VALID[st] and st or nil)
end)
