--!nonstrict
-- MovementService (server): the shared half of the real-life movement system (MovementClient does the moving).
--   * Ragdoll rig on every character: a ball-socket joint with human joint limits beside every body Motor6D (knees and
--     elbows only bend the right way, necks and waists only so far), no-collide between neighbouring body parts, and
--     BreakJointsOnDeath off. To ragdoll, the server switches the motors off (that replicates, so every player
--     sees the body go limp and tumble under real physics); to get up it switches them back on.
--   * Ragdolls: hard falls, being hit by a car, and death (bodies crumple instead of falling apart).
--   * Fall damage from the impact speed the client measured (FALL_DAMAGE).
--   * Relays what each player's body is doing to everyone else: vaults, climbs, rolls, hard landings, wall bumps
--     (character attribute MoveAct = "name|duration|serverTime") and where they're looking and how out of breath
--     they are (character attribute Look = Vector3(yaw, pitch, stamina)).
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")

local FALL_DAMAGE = true
local ACTS = { vault = 1.2, mantle = 1.6, climb = 2.4, roll = 1.0, land = 1.0, bump = 1.0, getup = 1.2, stumble = 1.0,
	soft = 0.6, skid = 1.0, pivot = 0.8 }

local Remotes = RS:FindFirstChild("Remotes")
if not Remotes then
	Remotes = Instance.new("Folder")
	Remotes.Name = "Remotes"
	Remotes.Parent = RS
end
local function remote(name, class)
	local r = Remotes:FindFirstChild(name)
	if not r then
		local ok, inst = pcall(Instance.new, class)
		r = ok and inst or Instance.new("RemoteEvent")
		r.Name = name
		r.Parent = Remotes
	end
	return r
end
local ActRE = remote("MoveAct", "RemoteEvent")
local LookRE = remote("MoveLook", "UnreliableRemoteEvent")

-- { cone, twistLow, twistHigh } in degrees. The cone limits swing of the joint's X axis (sideways / turning);
-- twist is rotation about X, which is the bend: + bends elbows, lifts arms and thighs forward; - bends knees and
-- tips the head and torso forward.
local LIMITS = {
	Neck = { 50, -45, 40 }, Waist = { 20, -45, 20 },
	LeftShoulder = { 80, -60, 170 }, RightShoulder = { 80, -60, 170 },
	LeftElbow = { 6, 0, 140 }, RightElbow = { 6, 0, 140 },
	LeftWrist = { 30, -45, 45 }, RightWrist = { 30, -45, 45 },
	LeftHip = { 45, -30, 115 }, RightHip = { 45, -30, 115 },
	LeftKnee = { 6, -140, 0 }, RightKnee = { 6, -140, 0 },
	LeftAnkle = { 25, -40, 40 }, RightAnkle = { 25, -40, 40 },
	-- classic R6 bodies: plain cones
	["Right Shoulder"] = { 70, -70, 70 }, ["Left Shoulder"] = { 70, -70, 70 },
	["Right Hip"] = { 50, -50, 50 }, ["Left Hip"] = { 50, -50, 50 },
}
local R6_NECK = { 40, -40, 40 }

local function limitsFor(m)
	if m.Name == "Neck" and m.Part0 and m.Part0.Name == "Torso" then
		return R6_NECK
	end
	return LIMITS[m.Name]
end

local function unrig(char)
	local old = char:FindFirstChild("NC_Ragdoll")
	if old then
		old:Destroy()
	end
	for _, d in char:GetDescendants() do
		if d:IsA("Attachment") and (string.sub(d.Name, 1, 5) == "RagA_" or string.sub(d.Name, 1, 5) == "RagB_") then
			d:Destroy()
		end
	end
end

local rig
local function watchRebuilds(char)
	-- an outfit change that swaps body parts or rescales them leaves the ragdoll joints in the wrong places:
	-- rebuild once things settle
	local pending = false
	char.DescendantAdded:Connect(function(d)
		if d:IsA("Motor6D") and not pending then
			pending = true
			task.delay(0.5, function()
				pending = false
				if char.Parent then
					unrig(char)
					rig(char, true)
				end
			end)
		end
	end)
end

function rig(char, rebuilt)
	local hum = char:WaitForChild("Humanoid", 10)
	if not hum or char:FindFirstChild("NC_Ragdoll") then
		return
	end
	if not rebuilt then
		watchRebuilds(char)
	end
	hum.BreakJointsOnDeath = false
	hum.RequiresNeck = false
	char:WaitForChild("HumanoidRootPart", 10)
	task.wait() -- let the body finish loading its joints
	local folder = Instance.new("Folder")
	folder.Name = "NC_Ragdoll"
	for _, m in char:GetDescendants() do
		if m:IsA("Motor6D") and m.Part0 and m.Part1 then
			local lim = limitsFor(m)
			if lim then
				local a0 = Instance.new("Attachment")
				a0.Name = "RagA_" .. m.Name
				a0.CFrame = m.C0
				a0.Parent = m.Part0
				local a1 = Instance.new("Attachment")
				a1.Name = "RagB_" .. m.Name
				a1.CFrame = m.C1
				a1.Parent = m.Part1
				local bs = Instance.new("BallSocketConstraint")
				bs.Name = m.Name
				bs.Attachment0, bs.Attachment1 = a0, a1
				bs.LimitsEnabled = true
				bs.UpperAngle = lim[1]
				bs.TwistLimitsEnabled = true
				bs.TwistLowerAngle, bs.TwistUpperAngle = lim[2], lim[3]
				bs.Restitution = 0
				bs.MaxFrictionTorque = 4 -- a little muscle tone, so limbs don't flop like cloth
				bs.Parent = folder
				local nc = Instance.new("NoCollisionConstraint")
				nc.Part0, nc.Part1 = m.Part0, m.Part1
				nc.Parent = folder
			end
		end
	end
	folder.Parent = char
	if rebuilt then
		return
	end
	hum.Died:Connect(function()
		for _, m in char:GetDescendants() do
			if m:IsA("Motor6D") and limitsFor(m) then
				m.Enabled = false
			end
		end
		char:SetAttribute("Ragdoll", true)
	end)
end

local function setRagdoll(char, on)
	for _, m in char:GetDescendants() do
		if m:IsA("Motor6D") and limitsFor(m) then
			m.Enabled = not on
		end
	end
	char:SetAttribute("Ragdoll", on or nil)
end

local function fallDamage(v)
	if v < 75 then
		return 0
	elseif v < 90 then
		return (v - 75) * 1.4 -- a hard roll: up to ~20
	elseif v < 120 then
		return 21 + (v - 90) * 2.3 -- a bad fall: up to ~90
	end
	return 1000 -- from that high, nobody walks away
end

local budget = {}
local function allow(p, cost)
	local b = budget[p]
	local now = os.clock()
	if not b then
		b = { tokens = 10, t = now }
		budget[p] = b
	end
	b.tokens = math.min(10, b.tokens + (now - b.t) * 6)
	b.t = now
	if b.tokens < cost then
		return false
	end
	b.tokens -= cost
	return true
end

ActRE.OnServerEvent:Connect(function(player, kind, a, b)
	local char = player.Character
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if not hum or typeof(kind) ~= "string" or not allow(player, 1) then
		return
	end
	if kind == "ragdoll" then
		if hum.Health > 0 then
			setRagdoll(char, true)
		end
	elseif kind == "getup" then
		if hum.Health > 0 then
			setRagdoll(char, false)
			char:SetAttribute("MoveAct", ("getup|0.9|%.3f"):format(workspace:GetServerTimeNow()))
		end
	elseif kind == "fall" then
		if FALL_DAMAGE and typeof(a) == "number" and a == a and hum.Health > 0 then
			local dmg = fallDamage(math.clamp(a, 0, 400)) * (player:GetAttribute("BodyFall") or 1) -- heavier bodies land harder
			if dmg > 0 then
				hum:TakeDamage(dmg)
			end
		end
	elseif ACTS[kind] then
		local dur = (typeof(a) == "number" and a == a) and math.clamp(a, 0.1, ACTS[kind] * 2) or ACTS[kind]
		local now = workspace:GetServerTimeNow()
		local t0 = (typeof(b) == "number" and math.abs(b - now) < 2) and b or now
		char:SetAttribute("MoveAct", ("%s|%.3f|%.3f"):format(kind, dur, t0))
	end
end)

-- look direction: keep the newest sample per player and publish at most ~15 times a second (so a burst of
-- packets never leaves an old direction showing)
local pendingLook = {}
LookRE.OnServerEvent:Connect(function(player, v)
	if typeof(v) ~= "Vector3" or v.X ~= v.X or v.Y ~= v.Y or v.Z ~= v.Z then
		return
	end
	pendingLook[player] = v
end)
task.spawn(function()
	while true do
		task.wait(0.066)
		for player, v in pendingLook do
			pendingLook[player] = nil
			local char = player.Parent and player.Character
			if char then
				char:SetAttribute("Look", Vector3.new(math.clamp(math.round(v.X), -80, 80), math.clamp(math.round(v.Y), -50, 50),
					math.clamp(math.round(v.Z * 20) / 20, 0, 1)))
			end
		end
	end
end)

local function onPlayer(p)
	p.CharacterAdded:Connect(rig)
	if p.Character then
		task.spawn(rig, p.Character)
	end
end
Players.PlayerAdded:Connect(onPlayer)
for _, p in Players:GetPlayers() do
	task.spawn(onPlayer, p)
end
Players.PlayerRemoving:Connect(function(p)
	budget[p], pendingLook[p] = nil, nil
end)
