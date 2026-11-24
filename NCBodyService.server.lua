--!nonstrict
-- NCBodyService (Script, ServerScriptService): puts every player in the right MakeHuman body.
--   * The bodies are the ten rigged MakeHuman models (build_makehuman_rig.py -> NC_Body_<Gender>_<Build>.fbx),
--     finished by AssembleMakeHumanBodies.lua and kept in ServerStorage.NC_Bodies.<Gender>_<Build>.
--   * Which one: the player's chosen frame (Male / Female, picked in Character Studio's Body tab, saved in the
--     DataStore "NeonCoast_Body_v1") + their fitness build (the BodyBuild attribute FitnessService sets:
--     Skinny / Average / Athletic / Muscular / Heavy; Bulky uses Muscular). Train, and your body changes.
--   * How: whenever a character spawns (any way: respawn, LoadCharacter, a hospital script ...) or the build or
--     frame changes, the body is swapped in place: same spot, same facing, same health share, same character
--     scripts. CharacterAdded fires again, so Character Studio dresses the new body (base layer first, always).
--   * Never mid-ride: if you're seated, the swap waits until you stand up.
-- Settings (attributes on this script): Enabled = false turns swapping off (everyone stays the StarterCharacter).
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local SS = game:GetService("ServerStorage")
local DataStoreService = game:GetService("DataStoreService")

if script:GetAttribute("Enabled") == nil then
	script:SetAttribute("Enabled", true)
end

local Data = require(RS:WaitForChild("NCBodyData"))

local Remotes = RS:FindFirstChild("Remotes") or Instance.new("Folder")
Remotes.Name = "Remotes"
Remotes.Parent = RS
local BodyRF = Remotes:FindFirstChild("NCBody") or Instance.new("RemoteFunction")
BodyRF.Name = "NCBody"
BodyRF.Parent = Remotes

local store
pcall(function()
	store = DataStoreService:GetDataStore("NeonCoast_Body_v1")
end)

local function bodies()
	return SS:FindFirstChild("NC_Bodies")
end

local G = {} -- [player] = { gender = "Male", loaded = bool, swapping = bool, lastSwap = clock }

local function wanted(player)
	local g = G[player]
	return Data.id(g and g.gender or "Male", player:GetAttribute("BodyBuild") or "Average")
end

-- copy the character scripts from the old body (Animate, Health and anything from StarterCharacterScripts)
local function moveScripts(old, new)
	for _, ch in old:GetChildren() do
		if (ch:IsA("Script") or ch:IsA("LocalScript") or ch:IsA("ModuleScript")) and not new:FindFirstChild(ch.Name) then
			local ok, c = pcall(function()
				return ch:Clone()
			end)
			if ok and c then
				c.Parent = new
			end
		end
	end
	local scs = game:GetService("StarterPlayer"):FindFirstChild("StarterCharacterScripts")
	if scs then
		for _, ch in scs:GetChildren() do
			if not new:FindFirstChild(ch.Name) then
				ch:Clone().Parent = new
			end
		end
	end
end

local function swap(player)
	local g = G[player]
	if not (g and script:GetAttribute("Enabled")) or g.swapping then
		return
	end
	local old = player.Character
	local folder = bodies()
	if not (old and old.Parent and folder) then
		return
	end
	local id = wanted(player)
	if old:GetAttribute("NC_BodyId") == id then
		return
	end
	local tpl = folder:FindFirstChild(id)
	local hum = old:FindFirstChildOfClass("Humanoid")
	local hrp = old:FindFirstChild("HumanoidRootPart")
	if not (tpl and hum and hrp) or hum.Health <= 0 then
		return
	end
	if hum.SeatPart or old:FindFirstChild("NC_Ragdoll") then
		task.delay(2, swap, player) -- never mid-ride or mid-ragdoll: try again shortly
		return
	end
	g.swapping = true
	local new = tpl:Clone()
	new.Name = player.Name
	new:SetAttribute("NC_BodyId", id)
	moveScripts(old, new)
	local nh = new:FindFirstChildOfClass("Humanoid")
	-- stand on the same ground: old feet = new feet
	local oldFeet = hrp.Position.Y - hum.HipHeight - hrp.Size.Y / 2
	local look = hrp.CFrame - hrp.Position
	local nhrp = new:FindFirstChild("HumanoidRootPart")
	local y = oldFeet + (nh and nh.HipHeight or 2) + (nhrp and nhrp.Size.Y / 2 or 1)
	new:PivotTo(CFrame.new(hrp.Position.X, y, hrp.Position.Z) * look)
	if nh then
		local frac = hum.Health / math.max(1, hum.MaxHealth)
		nh.MaxHealth = hum.MaxHealth
		nh.Health = math.max(1, hum.MaxHealth * frac)
		nh.DisplayName = hum.DisplayName
	end
	for k, v in old:GetAttributes() do -- (attributes other scripts keep on the character carry over)
		if k ~= "NC_BodyId" and k ~= "NC_Body" then
			new:SetAttribute(k, v)
		end
	end
	for _, t in old:GetChildren() do
		if t:IsA("Tool") then
			t.Parent = player:FindFirstChildOfClass("Backpack") or t.Parent
		end
	end
	new.Parent = workspace
	player.Character = new
	old:Destroy()
	g.lastSwap = os.clock()
	g.swapping = false
end

local function queue(player)
	task.defer(function()
		local g = G[player]
		if g and g.lastSwap and os.clock() - g.lastSwap < 1 then
			task.wait(1)
		end
		swap(player)
	end)
end

local function onPlayer(player)
	G[player] = { gender = "Male", loaded = false }
	if store then
		local ok, data = pcall(store.GetAsync, store, "u" .. player.UserId)
		if ok and type(data) == "table" and (data.gender == "Female" or data.gender == "Male") then
			G[player].gender = data.gender
		end
	end
	G[player].loaded = true
	player:SetAttribute("BodyGender", G[player].gender)
	player.CharacterAdded:Connect(function(char)
		char:WaitForChild("HumanoidRootPart", 10)
		queue(player)
	end)
	player:GetAttributeChangedSignal("BodyBuild"):Connect(function()
		queue(player)
	end)
	if player.Character then
		queue(player)
	end
end

BodyRF.OnServerInvoke = function(player, action, value)
	local g = G[player]
	if not (g and g.loaded) then
		return false, "Still loading..."
	end
	if action == "Get" then
		return true, "", { gender = g.gender, body = wanted(player) }
	elseif action == "SetGender" then
		if value ~= "Male" and value ~= "Female" then
			return false, "Pick Male or Female"
		end
		if g.lastSet and os.clock() - g.lastSet < 2 then
			return false, "Slow down"
		end
		g.lastSet = os.clock()
		g.gender = value
		player:SetAttribute("BodyGender", value)
		if store then
			task.spawn(pcall, store.SetAsync, store, "u" .. player.UserId, { v = 1, gender = value })
		end
		swap(player)
		return true, "", { gender = g.gender, body = wanted(player) }
	end
	return false, "Unknown action"
end

Players.PlayerAdded:Connect(onPlayer)
for _, p in Players:GetPlayers() do
	task.spawn(onPlayer, p)
end
Players.PlayerRemoving:Connect(function(p)
	G[p] = nil
end)
if not bodies() then
	warn("NCBodyService: ServerStorage.NC_Bodies is missing. Import the NC_Body_*.fbx files and run AssembleMakeHumanBodies.lua")
end
