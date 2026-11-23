--!nonstrict
-- PoolService (server): unicorn floaties that ride the water like real inflatables, the jump-through fun, and the
-- swim / dive pose relay so every player sees how each swimmer is moving (PoolClient does the swimming itself).
--
-- Floaty physics: a very light vinyl ring (about 3 mass) floating high (a third of the tube under), bobbing on
-- small waves, drifting slowly, pushed around by swimmers and kept off the pool walls. Stand on it and it sinks
-- most of the way (it can carry about one person fully pushed under); land on the edge and it tips, then rights
-- itself. The ring's hole (3.4 studs) is open: drop through it from the board or the deck for a "unicorn hoop".
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local RS = game:GetService("ReplicatedStorage")

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
local PoseRE = remote("SwimPose") -- client -> server: "swim" | "dive" | "cannon" | "climb" | nil
local HoopRE = remote("FloatyHoop") -- server -> all: (floaty, player, count)

local POSES = { swim = true, dive = true, cannon = true, climb = true }
PoseRE.OnServerEvent:Connect(function(player, pose)
	local char = player.Character
	if char then
		char:SetAttribute("SwimPose", POSES[pose] and pose or nil)
	end
end)

local CARRY = 16 -- extra mass the floaty holds up when pushed all the way under (about one person)
local floaties = {}

local function waterFor(pos)
	for _, w in CollectionService:GetTagged("NC_Water") do
		if w:IsA("BasePart") and w:IsDescendantOf(workspace) then
			local lp = w.CFrame:PointToObjectSpace(pos)
			local h = w.Size / 2
			if math.abs(lp.X) <= h.X + 1 and math.abs(lp.Z) <= h.Z + 1 and lp.Y <= h.Y + 10 and lp.Y >= -h.Y - 2 then
				return w
			end
		end
	end
	return nil
end

local function weld(a, b)
	local w = Instance.new("WeldConstraint")
	w.Part0, w.Part1 = a, b
	w.Parent = b
end

local function setup(model)
	if floaties[model] or not model:IsDescendantOf(workspace) then
		return
	end
	local body = model.PrimaryPart or model:FindFirstChild("Body")
	if not (body and body:IsA("BasePart")) then
		return
	end
	local R = model:GetAttribute("RingRadius") or 2.7
	local r = model:GetAttribute("TubeRadius") or 1.0
	local folder = Instance.new("Folder")
	folder.Name = "Physics"
	-- the ring: 16 overlapping vinyl balls round the tube (the hole stays open), springy like a pumped-up float
	local vinyl = PhysicalProperties.new(0.04, 0.35, 0.9, 1, 8)
	for k = 0, 15 do
		local a = 2 * math.pi * k / 16
		local ball = Instance.new("Part")
		ball.Name = "Tube"
		ball.Shape = Enum.PartType.Ball
		ball.Size = Vector3.one * (2 * r)
		ball.CFrame = body.CFrame * CFrame.new(math.cos(a) * R, 0, math.sin(a) * R)
		ball.Transparency = 1
		ball.CastShadow = false
		ball.CustomPhysicalProperties = vinyl
		ball.Parent = folder
		weld(body, ball)
	end
	local nmin, nmax = model:GetAttribute("NeckMin"), model:GetAttribute("NeckMax")
	if typeof(nmin) == "Vector3" and typeof(nmax) == "Vector3" then
		local neck = Instance.new("Part")
		neck.Name = "Neck"
		neck.Size = (nmax - nmin) * Vector3.new(0.8, 1, 0.8)
		neck.CFrame = body.CFrame * CFrame.new((nmin + nmax) / 2)
		neck.Transparency = 1
		neck.CastShadow = false
		neck.CustomPhysicalProperties = vinyl
		neck.Parent = folder
		weld(body, neck)
	end
	folder.Parent = model
	local att = Instance.new("Attachment")
	att.Name = "Float"
	att.Parent = body
	local vf = Instance.new("VectorForce")
	vf.Name = "Buoyancy"
	vf.Attachment0 = att
	vf.RelativeTo = Enum.ActuatorRelativeTo.World
	vf.ApplyAtCenterOfMass = true
	vf.Force = Vector3.zero
	vf.Parent = body
	local tq = Instance.new("Torque")
	tq.Name = "Righting"
	tq.Attachment0 = att
	tq.RelativeTo = Enum.ActuatorRelativeTo.World
	tq.Torque = Vector3.zero
	tq.Parent = body
	for _, p in model:GetDescendants() do
		if p:IsA("BasePart") then
			p.Anchored = false
		end
	end
	pcall(function()
		body:SetNetworkOwner(nil)
	end)
	local w = waterFor(body.Position)
	floaties[model] = {
		body = body, vf = vf, tq = tq, R = R, r = r, hole = model:GetAttribute("HoleRadius") or (R - r),
		home = body.CFrame, water = w, seed = math.random() * 100, last = {}, cool = {}, lost = 0, flipped = 0,
	}
end

task.spawn(function()
	while true do
		for _, m in CollectionService:GetTagged("NC_Floaty") do
			if not floaties[m] and m:IsDescendantOf(workspace) then
				task.spawn(setup, m)
			end
		end
		for m in floaties do
			if not m:IsDescendantOf(workspace) then
				floaties[m] = nil
			end
		end
		task.wait(1)
	end
end)

RunService.Heartbeat:Connect(function(dt)
	local now = os.clock()
	for model, f in floaties do
		local body = f.body
		if not body.Parent then
			floaties[model] = nil
			continue
		end
		local g = workspace.Gravity
		local M = body.AssemblyMass
		local pos, vel = body.Position, body.AssemblyLinearVelocity
		local up = body.CFrame.UpVector
		local w = f.water
		if not (w and w.Parent) or not waterFor(pos) then
			w = waterFor(pos)
			f.water = w
		end
		local force = Vector3.zero
		if w then
			local surf = w.Position.Y + w.Size.Y / 2 + 0.05 * math.sin(now * 1.4 + f.seed) -- small waves
			local bottom = pos.Y - f.r * math.max(0.35, math.abs(up.Y))
			local sub = math.clamp((surf - bottom) / (2 * f.r), 0, 1)
			local k = (M + CARRY) * g
			local damp = 2 * 0.35 * math.sqrt(k / (2 * f.r) * M) -- lightly damped bob
			local fy = k * sub - (sub > 0 and damp * vel.Y or 0)
			-- water drag on drifting + a slow wander, kept off the walls
			local hv = Vector3.new(vel.X, 0, vel.Z)
			local wander = Vector3.new(math.noise(now * 0.05, f.seed), 0, math.noise(f.seed, now * 0.05)) * M * 1.5
			local lp = w.CFrame:PointToObjectSpace(pos)
			local h = w.Size / 2
			local margin = f.R + f.r + 0.2
			local push = Vector3.new(
				math.max(0, lp.X - (h.X - margin)) * -1 + math.max(0, -lp.X - (h.X - margin)),
				0,
				math.max(0, lp.Z - (h.Z - margin)) * -1 + math.max(0, -lp.Z - (h.Z - margin))
			)
			force = Vector3.new(0, fy, 0) - hv * (M + 4) * 1.4 * sub + wander * sub + w.CFrame:VectorToWorldSpace(push) * M * 40
			f.lost = 0
		else
			f.lost += dt
		end
		f.vf.Force = force
		-- keep it upright (it tips when someone lands on the edge, then comes back); damp spinning
		local av = body.AssemblyAngularVelocity
		local kr = up.Y < 0.2 and 2600 or 900
		if up.Y < 0.2 then
			f.flipped += dt
		else
			f.flipped = 0
		end
		if f.flipped > 4 then
			kr = 6000 -- an upside-down float gets turned back over after a while
		end
		f.tq.Torque = up:Cross(Vector3.yAxis) * kr - Vector3.new(av.X, 0, av.Z) * 70 - Vector3.new(0, av.Y, 0) * 25
		-- lost (thrown out of the pool, fell through the world): back home after a while
		if f.lost > 15 or pos.Y < f.home.Y - 60 then
			body.AssemblyLinearVelocity, body.AssemblyAngularVelocity = Vector3.zero, Vector3.zero
			model:PivotTo(f.home)
			f.lost = 0
		end
		-- the jump-through: a player's middle passing down through the ring plane inside the hole
		for _, p in Players:GetPlayers() do
			local hrp = p.Character and p.Character:FindFirstChild("HumanoidRootPart")
			if not hrp then
				f.last[p] = nil
				continue
			end
			local lp = body.CFrame:PointToObjectSpace(hrp.Position)
			local near = Vector2.new(lp.X, lp.Z).Magnitude < f.R + f.r + 3 and math.abs(lp.Y) < 9
			local prev = f.last[p]
			if near and prev and prev.Y > 0.3 and lp.Y <= 0.3 then
				local t = (prev.Y - 0.3) / math.max(1e-3, prev.Y - lp.Y)
				local c = prev:Lerp(lp, t)
				if Vector2.new(c.X, c.Z).Magnitude < f.hole + 0.25 and now - (f.cool[p] or 0) > 1.2 then
					f.cool[p] = now
					local n = (p:GetAttribute("UnicornHoops") or 0) + 1
					p:SetAttribute("UnicornHoops", n)
					HoopRE:FireAllClients(model, p, n)
				end
			end
			f.last[p] = near and lp or nil
		end
	end
end)

Players.PlayerRemoving:Connect(function(p)
	for _, f in floaties do
		f.last[p], f.cool[p] = nil, nil
	end
end)
