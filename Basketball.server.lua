--!nonstrict
-- Basketball (server): working half courts with a ball that behaves like a real one.
-- A court is any Model tagged NC_Hoop (BuildingKit.PrepareHalfCourt makes them from the Blender half court) with
-- Attachments RimCenter, BallSpawn and BoardCenter, and attributes RimRadius, ThreeRadius, BoardSize.
--
-- Real numbers (about 1.15 studs per foot): 9.4 in ball (0.9 studs), 18 in rim (inner radius 0.8625) at 10 ft,
-- 72 x 42 in glass board. The ball falls at real gravity (32.2 ft/s^2 = 37 studs/s^2; Roblox's default pulls about
-- 5x harder, so a VectorForce takes the difference off), bounces back about 85% on the court like a regulation
-- ball, softer off the steel rim (~0.65) and livelier off the glass (~0.8). The rim is a ring of real steel tubes,
-- so balls roll around, rattle in, spin out and bank off the board. The server simulates the ball in flight, so
-- every player sees the same bounce and the scoring can't be faked.
--
-- Pick up: E on the ball, or run into a loose ball (catching rebounds and passes). Hold left click (or Shoot on
-- touch) to load the shot, release at the top of the meter, G to pass. Through the rim from above = 2 points,
-- 3 if you shot from beyond the arc. Players carry Buckets / Makes / Shots attributes for the HUD.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Debris = game:GetService("Debris")
local RS = game:GetService("ReplicatedStorage")

local G_REAL = 37.0
local BALL_D = 0.9
local HOLD_C0 = CFrame.new(1.1, -1.4, -1.1) -- right hip, before the client's dribble takes over
-- Built-in sounds so it works anywhere; swap for store sounds (ball bounce, rim clank) when convenient.
local SOUNDS = {
	Bounce = { "rbxasset://sounds/action_jump_land.mp3", 1.75 },
	Rim = { "rbxasset://sounds/action_jump_land.mp3", 2.7 },
	Board = { "rbxasset://sounds/action_jump_land.mp3", 1.25 },
}

local Remotes = RS:FindFirstChild("Remotes")
if not Remotes then
	Remotes = Instance.new("Folder")
	Remotes.Name = "Remotes"
	Remotes.Parent = RS
end
local function remote(name)
	local r = Remotes:FindFirstChild(name)
	if not r then
		r = Instance.new("RemoteEvent")
		r.Name = name
		r.Parent = Remotes
	end
	return r
end
local ShootRE = remote("BallShoot") -- (ball, origin, velocity, spin)
local PassRE = remote("BallPass") -- (ball, origin, velocity)
local PoseRE = remote("BallPose") -- ("charge" | nil): everyone sees the shot coming
local BucketRE = remote("BallBucket") -- server -> all: (court, points, shooterName, swish, bank)

local hoops = {} -- court model -> state

local function playSound(parent, key, volume)
	local def = SOUNDS[key]
	local s = Instance.new("Sound")
	s.SoundId = def[1]
	s.PlaybackSpeed = def[2] * (0.95 + math.random() * 0.1)
	s.Volume = volume
	s.RollOffMinDistance = 6
	s.RollOffMaxDistance = 110
	s.Parent = parent
	s:Play()
	Debris:AddItem(s, 2)
end

local function flatDist(a, b)
	return Vector3.new(a.X - b.X, 0, a.Z - b.Z).Magnitude
end

local function setGravity(ball, on)
	local vf = ball:FindFirstChild("RealGravity")
	if not vf then
		local att = Instance.new("Attachment")
		att.Name = "Centre"
		att.Parent = ball
		vf = Instance.new("VectorForce")
		vf.Name = "RealGravity"
		vf.Attachment0 = att
		vf.RelativeTo = Enum.ActuatorRelativeTo.World
		vf.ApplyAtCenterOfMass = true
		vf.Parent = ball
	end
	vf.Force = Vector3.new(0, ball:GetMass() * (workspace.Gravity - G_REAL), 0)
	vf.Enabled = on
end

local function charOf(userId)
	local p = userId and Players:GetPlayerByUserId(userId)
	return p and p.Character, p
end

local release -- forward

local function grab(b, player)
	if b:GetAttribute("Holder") or not b.Parent then
		return
	end
	local char = player.Character
	local hrp = char and char:FindFirstChild("HumanoidRootPart")
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if not (hrp and hum) or hum.Health <= 0 or char:GetAttribute("HasBall") then
		return
	end
	if (hrp.Position - b.Position).Magnitude > 10 then
		return
	end
	hum:UnequipTools()
	b.CanCollide = false
	b.Massless = true
	setGravity(b, false)
	local w = Instance.new("Weld")
	w.Name = "BallHold"
	w.Part0 = hrp
	w.Part1 = b
	w.C0 = HOLD_C0
	w.Parent = b
	b:SetAttribute("Holder", player.UserId)
	char:SetAttribute("HasBall", true)
	char:SetAttribute("BallPose", nil)
	local pp = b:FindFirstChildOfClass("ProximityPrompt")
	if pp then
		pp.Enabled = false
	end
end

-- origin: where the ball leaves the hands (nil = where it is). shooter: the Player when it's a shot (for scoring).
function release(b, holderChar, origin, vel, spin, shooter)
	local w = b:FindFirstChild("BallHold")
	if w then
		w:Destroy()
	end
	local thrower = b:GetAttribute("Holder")
	if holderChar then
		holderChar:SetAttribute("HasBall", nil)
		holderChar:SetAttribute("BallPose", shooter and "follow" or nil)
		if shooter then
			task.delay(0.6, function()
				if holderChar:GetAttribute("BallPose") == "follow" then
					holderChar:SetAttribute("BallPose", nil)
				end
			end)
		end
	end
	b:SetAttribute("Holder", nil)
	b.Massless = false
	if origin then
		b.CFrame = CFrame.new(origin) * b.CFrame.Rotation
	end
	b.CanCollide = false -- clear of the thrower's own arms for a moment
	setGravity(b, true)
	pcall(function()
		b:SetNetworkOwner(nil) -- the server flies it: same bounce for everyone, honest scoring
	end)
	b.AssemblyLinearVelocity = vel
	b.AssemblyAngularVelocity = spin or Vector3.zero
	local token = (b:GetAttribute("ReleaseId") or 0) + 1
	b:SetAttribute("ReleaseId", token)
	task.delay(0.15, function()
		if b.Parent and b:GetAttribute("ReleaseId") == token and not b:GetAttribute("Holder") then
			b.CanCollide = true
		end
	end)
	b:SetAttribute("LastThrower", thrower)
	b:SetAttribute("ThrowTime", workspace:GetServerTimeNow())
	if shooter then
		local hrp = holderChar and holderChar:FindFirstChild("HumanoidRootPart")
		b:SetAttribute("ShotBy", shooter.UserId)
		b:SetAttribute("ShotFrom", hrp and hrp.Position or origin)
		b:SetAttribute("ShotTime", workspace:GetServerTimeNow())
		b:SetAttribute("TouchedRim", false)
		b:SetAttribute("TouchedBoard", false)
		shooter:SetAttribute("Shots", (shooter:GetAttribute("Shots") or 0) + 1)
	else
		b:SetAttribute("ShotBy", nil)
	end
	local pp = b:FindFirstChildOfClass("ProximityPrompt")
	if pp then
		pp.Enabled = true
	end
end

local function makeBall(court, h)
	local b = Instance.new("Part")
	b.Name = "Basketball"
	b.Shape = Enum.PartType.Ball
	b.Size = Vector3.one * BALL_D
	b.Material = Enum.Material.Leather
	b.Color = Color3.fromRGB(206, 92, 34)
	-- density, friction, elasticity, frictionWeight, elasticityWeight. The court sets its own bounce (0.85, heavy
	-- weight) so a court bounce is regulation; grass, the rim and the board all come out softer than the court.
	b.CustomPhysicalProperties = PhysicalProperties.new(0.12, 0.7, 0.85, 3, 3)
	b.CFrame = h.spawn.WorldCFrame
	for k = 0, 1 do -- the black seams
		local seam = Instance.new("Part")
		seam.Name = "Seam"
		seam.Shape = Enum.PartType.Cylinder
		seam.Size = Vector3.new(0.02, BALL_D + 0.01, BALL_D + 0.01)
		seam.Color = Color3.fromRGB(28, 22, 20)
		seam.Material = Enum.Material.SmoothPlastic
		seam.CanCollide, seam.CanQuery, seam.CanTouch, seam.Massless = false, false, false, true
		seam.CFrame = b.CFrame * CFrame.Angles(0, k * math.pi / 2, 0)
		local wc = Instance.new("WeldConstraint")
		wc.Part0, wc.Part1 = b, seam
		wc.Parent = seam
		seam.Parent = b
	end
	local pp = Instance.new("ProximityPrompt")
	pp.ActionText = "Pick up"
	pp.ObjectText = "Basketball"
	pp.HoldDuration = 0
	pp.MaxActivationDistance = 8
	pp.RequiresLineOfSight = false
	pp.Parent = b
	CollectionService:AddTag(b, "NC_Basketball")
	b.Parent = court
	setGravity(b, true)
	pcall(function()
		b:SetNetworkOwner(nil)
	end)
	pp.Triggered:Connect(function(player)
		grab(b, player)
	end)
	-- run into a loose ball to catch it (rebounds, passes); not with a gun out, not your own throw right away
	b.Touched:Connect(function(hit)
		if b:GetAttribute("Holder") then
			return
		end
		local char = hit:FindFirstAncestorOfClass("Model")
		local player = char and Players:GetPlayerFromCharacter(char)
		if not player or char:FindFirstChildOfClass("Tool") or b.AssemblyLinearVelocity.Magnitude > 45 then
			return
		end
		if b:GetAttribute("LastThrower") == player.UserId and workspace:GetServerTimeNow() - (b:GetAttribute("ThrowTime") or 0) < 0.8 then
			return
		end
		grab(b, player)
	end)
	h.ball = b
	h.prev, h.prevVy, h.away = nil, nil, 0
	return b
end

local function validBall(player, b)
	return typeof(b) == "Instance" and CollectionService:HasTag(b, "NC_Basketball") and b:GetAttribute("Holder") == player.UserId
end

local function validOrigin(player, origin)
	local head = player.Character and player.Character:FindFirstChild("Head")
	return head and typeof(origin) == "Vector3" and origin == origin and (origin - head.Position).Magnitude < 6
end

ShootRE.OnServerEvent:Connect(function(player, b, origin, vel, spin)
	if not validBall(player, b) or not validOrigin(player, origin) then
		return
	end
	if typeof(vel) ~= "Vector3" or vel ~= vel or vel.Magnitude > 90 then
		return
	end
	if typeof(spin) ~= "Vector3" or spin ~= spin or spin.Magnitude > 60 then
		spin = Vector3.zero
	end
	release(b, player.Character, origin, vel, spin, player)
end)

PassRE.OnServerEvent:Connect(function(player, b, origin, vel)
	if not validBall(player, b) or not validOrigin(player, origin) then
		return
	end
	if typeof(vel) ~= "Vector3" or vel ~= vel or vel.Magnitude > 55 then
		return
	end
	release(b, player.Character, origin, vel, Vector3.zero, nil)
end)

PoseRE.OnServerEvent:Connect(function(player, state)
	local char = player.Character
	if char and char:GetAttribute("HasBall") then
		char:SetAttribute("BallPose", state == "charge" and "charge" or nil)
	end
end)

local function score(court, h, b)
	local rimC = h.rimA.WorldPosition
	local shooterId = b:GetAttribute("ShotBy")
	local shooter = shooterId and Players:GetPlayerByUserId(shooterId)
	local fresh = shooter ~= nil and (workspace:GetServerTimeNow() - (b:GetAttribute("ShotTime") or 0)) < 8
	local pts, swish, bank = 0, false, false
	if fresh then
		local from = b:GetAttribute("ShotFrom")
		pts = (typeof(from) == "Vector3" and flatDist(from, rimC) > h.three) and 3 or 2
		swish = not b:GetAttribute("TouchedRim") and not b:GetAttribute("TouchedBoard")
		bank = b:GetAttribute("TouchedBoard") == true
		shooter:SetAttribute("Buckets", (shooter:GetAttribute("Buckets") or 0) + pts)
		shooter:SetAttribute("Makes", (shooter:GetAttribute("Makes") or 0) + 1)
	end
	b:SetAttribute("ShotBy", nil)
	BucketRE:FireAllClients(court, pts, fresh and shooter.DisplayName or nil, swish, bank)
end

local function teardown(court)
	local h = hoops[court]
	if not h then
		return
	end
	if h.ball then
		h.ball:Destroy()
	end
	if h.folder then
		h.folder:Destroy()
	end
	hoops[court] = nil
end

local function setupHoop(court)
	if hoops[court] or not court:IsDescendantOf(workspace) then
		return
	end
	local rimA = court:FindFirstChild("RimCenter", true)
	local spawnA = court:FindFirstChild("BallSpawn", true)
	if not (rimA and spawnA) then
		return
	end
	local r = court:GetAttribute("RimRadius") or 0.8625
	local h = { rimA = rimA, r = r, three = court:GetAttribute("ThreeRadius") or 22.71, spawn = spawnA, ring = {}, away = 0 }
	hoops[court] = h
	local folder = Instance.new("Folder")
	folder.Name = "PhysicsHoop"
	h.folder = folder
	-- the steel rim: 20 tubes round the circle, inner edge exactly at the 18 in rim
	local c = rimA.WorldPosition
	local tube = 0.07
	local n = 20
	local steel = PhysicalProperties.new(7.8, 0.4, 0.45, 1, 3)
	for k = 0, n - 1 do
		local a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
		local p0 = c + Vector3.new(math.cos(a0), 0, math.sin(a0)) * (r + tube)
		local p1 = c + Vector3.new(math.cos(a1), 0, math.sin(a1)) * (r + tube)
		local seg = Instance.new("Part")
		seg.Name = "Rim"
		seg.Shape = Enum.PartType.Cylinder
		seg.Size = Vector3.new((p1 - p0).Magnitude + 0.04, tube * 2, tube * 2)
		seg.CFrame = CFrame.lookAt((p0 + p1) / 2, p1) * CFrame.Angles(0, math.pi / 2, 0) -- cylinder axis (X) along the chord
		seg.Anchored = true
		seg.Transparency = 1
		seg.CastShadow = false
		seg.CustomPhysicalProperties = steel
		seg.Parent = folder
		h.ring[seg] = true
		seg.Touched:Connect(function(hit)
			if hit == h.ball then
				hit:SetAttribute("TouchedRim", true)
				if os.clock() - (h.rimSound or 0) > 0.12 then
					h.rimSound = os.clock()
					playSound(hit, "Rim", math.clamp(hit.AssemblyLinearVelocity.Magnitude / 22, 0.2, 1))
				end
			end
		end)
	end
	local boardA = court:FindFirstChild("BoardCenter", true)
	if boardA then
		local board = Instance.new("Part")
		board.Name = "Board"
		board.Size = court:GetAttribute("BoardSize") or Vector3.new(6.9, 4.025, 0.15)
		board.CFrame = boardA.WorldCFrame
		board.Anchored = true
		board.Transparency = 1
		board.CastShadow = false
		board.CustomPhysicalProperties = PhysicalProperties.new(2.6, 0.3, 0.75, 1, 3)
		board.Parent = folder
		board.Touched:Connect(function(hit)
			if hit == h.ball then
				hit:SetAttribute("TouchedBoard", true)
				if os.clock() - (h.boardSound or 0) > 0.15 then
					h.boardSound = os.clock()
					playSound(hit, "Board", math.clamp(hit.AssemblyLinearVelocity.Magnitude / 22, 0.25, 1))
				end
			end
		end)
	end
	folder.Parent = court
	makeBall(court, h)
end

-- courts come and go (Kit.Place clones, streaming, a template moved in from ServerStorage)
task.spawn(function()
	while true do
		for _, court in CollectionService:GetTagged("NC_Hoop") do
			if not hoops[court] and court:IsDescendantOf(workspace) then
				task.spawn(setupHoop, court)
			end
		end
		for court in hoops do
			if not court:IsDescendantOf(workspace) then
				teardown(court)
			end
		end
		task.wait(1)
	end
end)

local floorParams = RaycastParams.new()
floorParams.FilterType = Enum.RaycastFilterType.Exclude

RunService.Heartbeat:Connect(function(dt)
	for court, h in hoops do
		local b = h.ball
		if not (b and b.Parent) then
			makeBall(court, h)
			continue
		end
		local holderId = b:GetAttribute("Holder")
		if holderId then
			-- the holder died, left, pulled a gun or the hold broke: the ball drops where it is
			local char = charOf(holderId)
			local hum = char and char:FindFirstChildOfClass("Humanoid")
			local w = b:FindFirstChild("BallHold")
			if not (hum and hum.Health > 0 and w and w.Part0 and w.Part0:IsDescendantOf(char)) or char:FindFirstChildOfClass("Tool") then
				release(b, char, nil, Vector3.new(0, 4, 0))
			end
			h.prev, h.prevVy = nil, nil
			continue
		end
		local pos, vel = b.Position, b.AssemblyLinearVelocity
		local prev = h.prev
		if prev then
			local rimC = h.rimA.WorldPosition
			local function crossedInside()
				local t = (prev.Y - rimC.Y) / (prev.Y - pos.Y)
				local cross = prev:Lerp(pos, t)
				return flatDist(cross, rimC) < h.r - 0.15
			end
			if prev.Y > rimC.Y and pos.Y <= rimC.Y and crossedInside() then
				if os.clock() - (h.upThrough or -99) > 2.5 then -- not a ball pushed up through the net and back
					score(court, h, b)
				end
			elseif prev.Y < rimC.Y and pos.Y >= rimC.Y and crossedInside() then
				h.upThrough = os.clock()
			end
		end
		-- bounce sound off the ground: the fall turned into a rise with the floor right under the ball
		if h.prevVy and h.prevVy < -5 and vel.Y > 1 then
			floorParams.FilterDescendantsInstances = { b, h.folder }
			if workspace:Raycast(pos, Vector3.new(0, -BALL_D, 0), floorParams) then
				playSound(b, "Bounce", math.clamp(-h.prevVy / 28, 0.15, 0.9))
			end
		end
		-- rolled away or fell out of the world: back to the free-throw line after a while
		local spawnP = h.spawn.WorldPosition
		if pos.Y < spawnP.Y - 50 then
			h.away = 99
		elseif (pos - spawnP).Magnitude > 75 then
			h.away += dt
		else
			h.away = 0
		end
		if h.away > 8 then
			b.AssemblyLinearVelocity, b.AssemblyAngularVelocity = Vector3.zero, Vector3.zero
			b.CFrame = h.spawn.WorldCFrame
			b:SetAttribute("ShotBy", nil)
			h.away = 0
			pos = b.Position
		end
		h.prev, h.prevVy = pos, vel.Y
	end
end)

Players.PlayerRemoving:Connect(function(player)
	for _, h in hoops do
		if h.ball and h.ball:GetAttribute("Holder") == player.UserId then
			release(h.ball, player.Character, nil, Vector3.zero)
		end
	end
end)
