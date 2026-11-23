--!nonstrict
-- LookStudioService (Script in ServerScriptService): the server half of the Character Studio.
--   * Saves each player's look, the items they own and 8 named outfit slots (DataStore "NeonCoast_Look_v1").
--   * Puts the look on every character as it spawns (before FitnessService scales the body, which keeps working:
--     it remembers the look's own build through the NC_LookBase attribute).
--   * Buying goes through NCWallet, so clothes cost the same Cash jobs and robberies pay into.
--   * Everything the client sends is checked here: the item exists, it's in the right slot, the colours are on the
--     item's palette, required slots stay filled, and the player can pay.
-- Remote: ReplicatedStorage.Remotes.LookStudio (RemoteFunction)
--   "Get"                         -> { look, owned, outfits, cash, free }
--   "Wear", look                  -> ok, msg, state       (buys anything not owned, then wears it)
--   "SaveOutfit", index, name     -> ok, msg, state       (saves the current look in slot 1..8)
--   "DeleteOutfit", index         -> ok, msg, state
-- Config (attributes on this script, set them in Studio):
--   FreeMode (bool)     everything is free (testing / a creative server)
--   Sparkle (bool, default true) iced pieces twinkle
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local SSS = game:GetService("ServerScriptService")
local DataStoreService = game:GetService("DataStoreService")
local InsertService = game:GetService("InsertService")

-- one-drag install: if this script arrived inside the NeonCoastCharacterStudio folder (the .rbxmx dropped into
-- ServerScriptService), move the shared modules to ReplicatedStorage and the client to StarterPlayerScripts
do
	local here = script.Parent
	for _, n in ipairs({ "NCLookCatalog", "NCLookBuilder", "NCBodyData" }) do
		local m = here:FindFirstChild(n)
		if m and m:IsA("ModuleScript") then
			local old = RS:FindFirstChild(n)
			if old then
				old:Destroy() -- the package copy is the newer one
			end
			m.Parent = RS
		end
	end
	local cl = here:FindFirstChild("LookStudioClient")
	if cl then
		local sps = game:GetService("StarterPlayer"):WaitForChild("StarterPlayerScripts")
		local old = sps:FindFirstChild(cl.Name)
		if old then
			old:Destroy()
		end
		cl.Parent = sps
	end
end

local Catalog = require(RS:WaitForChild("NCLookCatalog"))
local Builder = require(RS:WaitForChild("NCLookBuilder"))

local Wallet
do
	local m = SSS:FindFirstChild("NCWallet")
	if m then
		local ok, res = pcall(require, m)
		if ok then
			Wallet = res
		end
	end
end

local Remotes = RS:FindFirstChild("Remotes")
if not Remotes then
	Remotes = Instance.new("Folder")
	Remotes.Name = "Remotes"
	Remotes.Parent = RS
end
local LookRF = Remotes:FindFirstChild("LookStudio") or Instance.new("RemoteFunction")
LookRF.Name = "LookStudio"
LookRF.Parent = Remotes
local LookChanged = Remotes:FindFirstChild("LookChanged") or Instance.new("RemoteEvent") -- tells the client its look changed
LookChanged.Name = "LookChanged"
LookChanged.Parent = Remotes

if script:GetAttribute("Sparkle") == nil then
	script:SetAttribute("Sparkle", true)
end

local MAX_OUTFITS = 8
local store
pcall(function()
	store = DataStoreService:GetDataStore("NeonCoast_Look_v1")
end)

local D = {} -- [player] = { look, owned, outfits, dirty, loaded }

---------------------------------------------------------------------------------------------------- helpers
local function freeMode()
	return script:GetAttribute("FreeMode") == true or Wallet == nil
end

local function cash(player)
	return Wallet and Wallet.Balance(player) or 0
end

local function notify(player, text, color)
	if Wallet then
		Wallet.Notify(player, text, color)
	end
end

local function copyLook(look)
	local out = {}
	for slot, e in pairs(look) do
		out[slot] = { id = e.id, c1 = e.c1, c2 = e.c2 }
	end
	return out
end

-- clean a look sent by a client: unknown items, wrong slots and colours off the palette are dropped or reset
local function sanitize(raw)
	if type(raw) ~= "table" then
		return nil, "bad look"
	end
	local look = {}
	for slot, e in pairs(raw) do
		if type(slot) == "string" and Catalog.SLOT_BY_ID[slot] and type(e) == "table" and type(e.id) == "string" then
			local item = Catalog.ITEMS_BY_ID[e.id]
			if item and item.slot == slot then
				local c1 = (Catalog.ColourAllowed(item, 1, e.c1) and e.c1) or item.def1
				local c2 = (Catalog.ColourAllowed(item, 2, e.c2) and e.c2) or item.def2
				look[slot] = { id = item.id, c1 = c1, c2 = c2 }
			end
		end
	end
	for _, s in ipairs(Catalog.SLOTS) do
		if s.required and not look[s.id] then
			look[s.id] = copyLook({ x = Catalog.DEFAULT_LOOK[s.id] }).x
		end
	end
	return look
end

local function state(player)
	local d = D[player]
	if not d then
		return nil
	end
	local owned = {}
	for id in pairs(d.owned) do
		table.insert(owned, id)
	end
	return { look = copyLook(d.look), owned = owned, outfits = d.outfits, cash = cash(player), free = freeMode(), made = d.made == true }
end

---------------------------------------------------------------------------------------------------- real meshes
-- items with an assetId (e.g. the creator's own Loose Bandana) are loaded once and worn as real accessories
local assetCache = {}
local function assetsFor(look)
	local out = {}
	for _, e in pairs(look) do
		local item = Catalog.ITEMS_BY_ID[e.id]
		if item and item.assetId then
			local cached = assetCache[item.assetId]
			if cached == nil then
				local ok, model = pcall(InsertService.LoadAsset, InsertService, item.assetId)
				local acc = ok and model and model:FindFirstChildWhichIsA("Accessory", true)
				if acc then
					acc.Parent = nil
					assetCache[item.assetId] = acc
				else
					warn("LookStudio: couldn't load asset " .. tostring(item.assetId) .. " for " .. item.id .. ", using the built-in version")
					assetCache[item.assetId] = false
				end
				if ok and model then
					model:Destroy()
				end
				cached = assetCache[item.assetId]
			end
			if cached then
				out[item.id] = cached
			end
		end
	end
	return out
end

---------------------------------------------------------------------------------------------------- apply
local function apply(player)
	local d = D[player]
	local char = player.Character
	if not (d and char and char.Parent) then
		return
	end
	local hum = char:FindFirstChildOfClass("Humanoid")
	if not hum or hum.Health <= 0 then
		return
	end
	local ok, err = pcall(Builder.Apply, char, d.look, Catalog, { assets = assetsFor(d.look), sparkle = script:GetAttribute("Sparkle") })
	if not ok then
		warn("LookStudio: couldn't dress " .. player.Name .. ": " .. tostring(err))
		pcall(Builder.ApplyBaseLayer, char)
	end
end

---------------------------------------------------------------------------------------------------- save / load
local function load(player)
	local d = { look = copyLook(Catalog.DEFAULT_LOOK), owned = {}, outfits = {}, dirty = false, loaded = false }
	D[player] = d
	if store then
		local ok, data
		for _ = 1, 3 do
			ok, data = pcall(store.GetAsync, store, "u" .. player.UserId)
			if ok then
				break
			end
			task.wait(1)
		end
		if ok and type(data) == "table" then
			d.look = sanitize(data.look) or d.look
			d.made = data.made == true or data.look ~= nil
			if type(data.owned) == "table" then
				for _, id in ipairs(data.owned) do
					if Catalog.ITEMS_BY_ID[id] then
						d.owned[id] = true
					end
				end
			end
			if type(data.outfits) == "table" then
				for i = 1, MAX_OUTFITS do
					local o = data.outfits[i]
					if type(o) == "table" and type(o.look) == "table" then
						d.outfits[i] = { name = tostring(o.name or ("Outfit " .. i)):sub(1, 24), look = sanitize(o.look) }
					end
				end
			end
		elseif not ok then
			d.noSave = true -- don't overwrite their data with defaults if the store was down at join
			warn("LookStudio: DataStore load failed for " .. player.Name .. "; changes this session won't be saved")
		end
	end
	d.loaded = true
	return d
end

local function save(player)
	local d = D[player]
	if not (store and d and d.loaded and d.dirty and not d.noSave) then
		return
	end
	local owned = {}
	for id in pairs(d.owned) do
		table.insert(owned, id)
	end
	local data = { v = 1, look = d.look, owned = owned, outfits = d.outfits, made = d.made }
	local ok = pcall(store.SetAsync, store, "u" .. player.UserId, data)
	if ok then
		d.dirty = false
	end
end

---------------------------------------------------------------------------------------------------- remote
local last = {}
LookRF.OnServerInvoke = function(player, action, a, b)
	local d = D[player]
	if not (d and d.loaded) then
		return false, "Still loading your closet..."
	end
	local now = os.clock()
	if last[player] and now - last[player] < 0.25 and action ~= "Get" then
		return false, "Slow down"
	end
	last[player] = now

	if action == "Get" then
		return true, "", state(player)

	elseif action == "Wear" then
		local look, err = sanitize(a)
		if not look then
			return false, err, state(player)
		end
		local cost, missing = Catalog.Cost(look, d.owned)
		if cost > 0 and not freeMode() then
			if not Wallet.Spend(player, cost) then
				return false, ("You need $%d more"):format(cost - cash(player)), state(player)
			end
		end
		for _, id in ipairs(missing) do
			d.owned[id] = true
		end
		d.look = look
		d.made = true
		d.dirty = true
		apply(player)
		if cost > 0 then
			notify(player, (freeMode() and "Unlocked %d item%s" or "Bought %d item%s"):format(#missing, #missing == 1 and "" or "s"), Color3.fromRGB(120, 230, 140))
		end
		task.defer(save, player)
		LookChanged:FireClient(player)
		return true, cost > 0 and ("Spent $" .. cost) or "Looking good", state(player)

	elseif action == "SaveOutfit" then
		local i = tonumber(a)
		if not i or i < 1 or i > MAX_OUTFITS or i % 1 ~= 0 then
			return false, "Pick a slot 1-" .. MAX_OUTFITS, state(player)
		end
		local name = (type(b) == "string" and b ~= "") and b:sub(1, 24) or ("Outfit " .. i)
		-- names are shown to the player themself only, but run them through the filter anyway
		local okF, filtered = pcall(function()
			return game:GetService("TextService"):FilterStringAsync(name, player.UserId):GetNonChatStringForBroadcastAsync()
		end)
		d.outfits[i] = { name = okF and filtered or ("Outfit " .. i), look = copyLook(d.look) }
		d.dirty = true
		task.defer(save, player)
		return true, "Saved", state(player)

	elseif action == "DeleteOutfit" then
		local i = tonumber(a)
		if i and d.outfits[i] then
			d.outfits[i] = nil
			d.dirty = true
			task.defer(save, player)
		end
		return true, "Deleted", state(player)
	end
	return false, "Unknown action"
end

---------------------------------------------------------------------------------------------------- players
local function onPlayer(player)
	-- no nudity, ever: every character gets the base layer the moment it spawns, before the saved look has
	-- even loaded (and again if anything goes wrong dressing it)
	local function baseLayer(char)
		char:WaitForChild("UpperTorso", 10)
		pcall(Builder.ApplyBaseLayer, char)
	end
	player.CharacterAdded:Connect(baseLayer)
	if player.Character then
		task.spawn(baseLayer, player.Character)
	end
	load(player)
	local function dress(char)
		-- wait until the body parts are in, then dress before FitnessService (2.5 s) scales the build
		char:WaitForChild("Humanoid", 10)
		char:WaitForChild("Head", 10)
		char:WaitForChild("UpperTorso", 10)
		task.wait(0.2)
		if player.Character == char then
			apply(player)
		end
	end
	player.CharacterAdded:Connect(dress)
	if player.Character then
		task.spawn(dress, player.Character)
	end
end
Players.PlayerAdded:Connect(onPlayer)
for _, p in ipairs(Players:GetPlayers()) do
	task.spawn(onPlayer, p)
end
Players.PlayerRemoving:Connect(function(p)
	save(p)
	D[p], last[p] = nil, nil
end)
task.spawn(function()
	while true do
		task.wait(120)
		for _, p in ipairs(Players:GetPlayers()) do
			save(p)
		end
	end
end)
game:BindToClose(function()
	for _, p in ipairs(Players:GetPlayers()) do
		task.spawn(save, p)
	end
	task.wait(3)
end)
