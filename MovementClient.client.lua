--!nonstrict
-- MovementClient: moving like a real person, with real weight. (MovementService is the server half.)
--   Momentum: you push off and build speed (slower the faster you already are), you can't stop on a dime (a
--   sprint skids a couple of steps), you corner in arcs that widen with speed, and asking to go the opposite way
--   at speed makes you plant and brake before turning. Walls kill your momentum; running flat out into one knocks
--   you back. Uphill is slower, downhill a touch faster.
--   Gaits: walk (hold Left Alt, or tilt the stick a little), jog (default), sprint (hold Left Shift; L3 or the
--   Sprint button toggle it). Sprinting burns stamina; tired, you slow down; empty, you have to jog it off.
--   Jumps are human-sized and carry your momentum, with little steering once you're off the ground.
--   Landings: soft dip, hard landing (you crouch and lose speed), a roll if you're moving, a ragdoll from higher;
--   fall damage from the impact speed (MovementService).
--   Vault and climb (press jump facing it): vault fences and rails, mantle onto low walls and counters, jump,
--   hang and pull up over walls and fences up to about 9 studs, dropping down the far side of thin ones.
--   Ragdoll: hard falls and being hit by a car; you get back up facing where your head was.
--   Body: everyone leans into acceleration and corners, heads turn toward where players look, out-of-breath
--   players breathe hard, and feet stand on stairs and slopes instead of floating. Everything is seen by all.
-- Other scripts can slow or freeze you without fighting this: Humanoid attributes SpeedFactor_<anything>
-- multiply your speed (0 freezes you and stops jumps), and a plain WalkSpeed change scales it too (16 = normal).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local CAS = game:GetService("ContextActionService")
local CollectionService = game:GetService("CollectionService")
local RS = game:GetService("ReplicatedStorage")

local player = Players.LocalPlayer
local Remotes = RS:WaitForChild("Remotes")
local ActRE = Remotes:WaitForChild("MoveAct")
local LookRE = Remotes:WaitForChild("MoveLook")

-- the Blender-made animations (NCAnimPlayer + NCAnimations in ReplicatedStorage); without them the default
-- Roblox animations play with this script's procedural poses on top
local Anim = nil
task.spawn(function()
	local m = RS:FindFirstChild("NCAnimPlayer") or RS:WaitForChild("NCAnimPlayer", 10)
	if m then
		local ok, mod = pcall(require, m)
		if ok and type(mod) == "table" and mod.init() then
			Anim = mod
		end
	end
end)
-- which Blender clip plays each act; LEGS = acts that take over your legs (the rest only change how you look)
local ACT_CLIP = { vault = "Vault", mantle = "Mantle", climb = "Climb", roll = "Roll", land = "LandHard", stumble = "Stumble",
	getup = "GetUp", bump = "Bump", skid = "Skid", pivot = "Pivot", soft = "Land" }
local LEGS = { roll = true, land = true, stumble = true, getup = true, bump = true }

-- studs/s in this world's scale (~3.8 studs to a metre): walk ~1.3 m/s, jog ~4.2, sprint ~6.6
local WALK, JOG, SPRINT = 5, 16, 25
local BASE = 16 -- the WalkSpeed every other script thinks of as normal
local ACCEL0, ACCEL1 = 42, 6 -- push-off from a standstill / at full sprint (0->jog 0.5 s, jog->sprint ~0.75 s)
local SLOW_DECEL, STOP_DECEL, SKID_DECEL, PIVOT_DECEL = 30, 50, 40, 72 -- a sprint skids ~7 studs to a stop
local A_LAT = 75 -- how hard you can corner, studs/s^2 (sprint turns ~8 studs wide, jog ~3.4)
local TURN_MAX = math.rad(720)
local PIVOT_ANGLE = math.rad(125)
local AIR_ACCEL = 9
local JUMP_HEIGHT = 4.2
local SPRINT_TIME, REGEN_TIME, REGEN_IDLE = 12, 7, 4.5
local MAX_CLIMB, MAX_VAULT, MIN_OBST, REACH = 9.2, 4.6, 1.6, 3.4
local SPRINT_FOV = 5
local rad = math.rad
local ST = Enum.HumanoidStateType

local function flat(v)
	return Vector3.new(v.X, 0, v.Z)
end
local function bodyOf(char)
	local hrp = char and char:FindFirstChild("HumanoidRootPart")
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if hrp and hum then
		return hrp, hum
	end
	return nil
end
local function lerp(a, b, t)
	return a + (b - a) * t
end
local function clamp01(x)
	return math.clamp(x, 0, 1)
end
local function wrapAngle(a)
	return (a + math.pi) % (2 * math.pi) - math.pi
end

---------------------------------------------------------------------------------------------- the world
local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Exclude
params.RespectCanCollide = true
local overlap = OverlapParams.new()
overlap.FilterType = Enum.RaycastFilterType.Exclude
overlap.RespectCanCollide = true
local function refreshFilter()
	local list = {}
	for _, p in Players:GetPlayers() do
		if p.Character then
			table.insert(list, p.Character)
		end
	end
	local chutes = workspace:FindFirstChild("NC_LocalChutes")
	if chutes then
		table.insert(list, chutes)
	end
	params.FilterDescendantsInstances = list
	overlap.FilterDescendantsInstances = list
end
refreshFilter()

local function inWater(pos)
	for _, w in CollectionService:GetTagged("NC_Water") do
		if w:IsA("BasePart") and w:IsDescendantOf(workspace) then
			local lp = w.CFrame:PointToObjectSpace(pos)
			local h = w.Size / 2
			if math.abs(lp.X) <= h.X and math.abs(lp.Z) <= h.Z and math.abs(lp.Y) <= h.Y + 0.5 then
				return true
			end
		end
	end
	return false
end

-- is this box of space really empty? (true shapes, not bounding boxes, so a big building mesh next to a counter
-- doesn't block the vault)
local probe = Instance.new("Part")
probe.Name = "NC_MoveProbe"
probe.Anchored, probe.CanCollide, probe.CanTouch, probe.CanQuery = true, false, false, false
probe.Transparency = 1
probe.Parent = workspace.CurrentCamera
local function boxClear(cf, size)
	probe.Size = size
	probe.CFrame = cf
	return #workspace:GetPartsInPart(probe, overlap) == 0
end

---------------------------------------------------------------------------------------------- joints
local JN = { "Root", "Waist", "Neck", "RightShoulder", "LeftShoulder", "RightElbow", "LeftElbow", "RightHip", "LeftHip",
	"RightKnee", "LeftKnee", "RightAnkle", "LeftAnkle", "RightWrist", "LeftWrist" }
local JSET = {}
for _, n in JN do
	JSET[n] = true
end
local jointCache = setmetatable({}, { __mode = "k" })
local function jointsOf(char)
	local e = jointCache[char]
	-- (rescan if the body was rebuilt, e.g. a new outfit swapped the body parts and their joints)
	if e and (e.n >= #JN or os.clock() - e.t < 2) and not (e.Waist and e.Waist.Parent == nil) then
		return e
	end
	e = { n = 0, t = os.clock() }
	for _, d in char:GetDescendants() do
		if JSET[d.Name] and (d:IsA("Motor6D") or d:IsA("AnimationConstraint")) and not e[d.Name] then
			e[d.Name] = d
			e.n += 1
		end
	end
	local hip, knee, ankle = e.RightHip, e.RightKnee, e.RightAnkle
	if hip and knee and ankle and hip:IsA("Motor6D") and knee:IsA("Motor6D") and ankle:IsA("Motor6D") then
		e.L1 = (hip.C1.Position - knee.C0.Position).Magnitude
		e.L2 = (knee.C1.Position - ankle.C0.Position).Magnitude
	end
	jointCache[char] = e
	return e
end

local function frames(j)
	if j:IsA("Motor6D") then
		return j.C0.Rotation, j.C1.Rotation
	end
	local a0, a1 = j.Attachment0, j.Attachment1
	local p0 = a0 and a0:FindFirstAncestorWhichIsA("BasePart")
	local p1 = a1 and a1:FindFirstAncestorWhichIsA("BasePart")
	if not (p0 and p1) then
		return nil
	end
	return p0.CFrame:ToObjectSpace(a0.WorldCFrame).Rotation, p1.CFrame:ToObjectSpace(a1.WorldCFrame).Rotation
end

-- absolute pose: the child's rotation (and offset) q relative to its rest pose, blended over the animation by alpha
local function setJoint(j, q, alpha)
	if not j then
		return
	end
	local c0, c1 = frames(j)
	if not c0 then
		return
	end
	local target = c0:Inverse() * q * c1
	j.Transform = alpha < 1 and j.Transform:Lerp(target, alpha) or target
end

-- additive pose: rotate the child by q (parent's axes, about the joint) on top of whatever the animation did this
-- frame. Remembers what it wrote so an un-animated joint doesn't pile the same offset up frame after frame.
local written = setmetatable({}, { __mode = "k" })
local function addTo(j, q)
	if not j then
		return
	end
	local c0 = frames(j)
	if not c0 then
		return
	end
	local cur = j.Transform
	local rec = written[j]
	local base = (rec and cur == rec[1]) and rec[2] or cur
	local value = c0:Inverse() * q * c0 * base
	j.Transform = value
	written[j] = { value, base }
end

local A_ = CFrame.Angles
local function D(x, y, z)
	return A_(rad(x), rad(y or 0), rad(z or 0))
end

-- how far the hips come down when the hip bends h and the knee k (radians, knee bends negative)
local function crouchDrop(J, h, k)
	local L1, L2 = J.L1 or 1.2, J.L2 or 1.2
	return (L1 + L2) - (L1 * math.cos(h) + L2 * math.cos(h + k))
end

---------------------------------------------------------------------------------------------- act poses
-- every act is a function of its progress u (0..1), so the same pose plays on every screen
local function crouchPose(J, a, w, deep)
	local h, k = rad((deep and 95 or 75) * a), rad(-(deep and 125 or 110) * a)
	setJoint(J.RightHip, A_(h, 0, rad(6 * a)), w)
	setJoint(J.LeftHip, A_(h, 0, rad(-6 * a)), w)
	setJoint(J.RightKnee, A_(k, 0, 0), w)
	setJoint(J.LeftKnee, A_(k, 0, 0), w)
	setJoint(J.RightAnkle, A_(-(h + k), 0, 0), w)
	setJoint(J.LeftAnkle, A_(-(h + k), 0, 0), w)
	setJoint(J.Waist, D(-(deep and 35 or 28) * a), w)
	setJoint(J.Neck, D(12 * a), w)
	setJoint(J.RightShoulder, D(40 * a, 0, 12 * a), w)
	setJoint(J.LeftShoulder, D(40 * a, 0, -12 * a), w)
	setJoint(J.RightElbow, D(45 * a), w)
	setJoint(J.LeftElbow, D(45 * a), w)
	setJoint(J.Root, CFrame.new(0, -crouchDrop(J, h, k), 0), w)
end

local POSE = {}
function POSE.vault(J, u)
	local a = clamp01((u - 0.12) / 0.22) * (1 - clamp01((u - 0.68) / 0.27))
	local w = clamp01(math.min(u / 0.1, (1 - u) / 0.12))
	setJoint(J.RightShoulder, D(20 + 40 * a, 0, 25 * a), w) -- hand planted on the top
	setJoint(J.RightElbow, D(10), w)
	setJoint(J.LeftShoulder, D(30 * a, 0, -75 * a), w) -- the free arm out for balance
	setJoint(J.LeftElbow, D(25 * a), w)
	setJoint(J.RightHip, D(80 * a), w) -- legs tucked and swung through
	setJoint(J.LeftHip, D(70 * a), w)
	setJoint(J.RightKnee, D(-100 * a), w)
	setJoint(J.LeftKnee, D(-95 * a), w)
	setJoint(J.Waist, D(-18 * a), w)
	setJoint(J.Neck, D(-8 * a), w)
	setJoint(J.Root, D(0, 0, -25 * a), w) -- body tipped over the planted hand
end
function POSE.mantle(J, u)
	local reach, push = clamp01(u / 0.3), clamp01((u - 0.3) / 0.4)
	local knee = clamp01((u - 0.45) / 0.3) * (1 - clamp01((u - 0.85) / 0.15))
	local w = clamp01(math.min(u / 0.08, (1 - u) / 0.12))
	local sh = lerp(lerp(20, 150, reach), 25, push)
	local el = 15 + 80 * math.sin(math.pi * push)
	setJoint(J.RightShoulder, D(sh, 0, 10), w)
	setJoint(J.LeftShoulder, D(sh, 0, -10), w)
	setJoint(J.RightElbow, D(el), w)
	setJoint(J.LeftElbow, D(el), w)
	setJoint(J.RightHip, D(100 * knee), w)
	setJoint(J.RightKnee, D(-115 * knee), w)
	setJoint(J.LeftHip, D(20 * knee), w)
	setJoint(J.LeftKnee, D(-50 * knee), w)
	setJoint(J.Waist, D(-25 * math.sin(math.pi * u)), w)
end
function POSE.climb(J, u)
	local w = clamp01(math.min(u / 0.08, (1 - u) / 0.1))
	local sh, el, hip, kn, waist, neck = 0, 0, 0, 0, 0, 0
	local rHip, rKnee
	if u < 0.26 then -- jump and reach
		local a = u / 0.26
		sh, el, hip, kn, neck = lerp(30, 170, a), lerp(30, 10, a), 20 * a, -35 * a, 20 * a
	elseif u < 0.38 then -- hanging from the edge
		local s = math.sin((u - 0.26) / 0.12 * math.pi)
		sh, el, hip, kn, neck = 168, 12, 12 + 4 * s, -20 - 6 * s, 20
	elseif u < 0.72 then -- pull up, feet walking the wall
		local b = (u - 0.38) / 0.34
		sh, el = lerp(168, 35, b), 12 + 93 * math.sin(math.pi * b * 0.75) -- elbows bend hard, then start to press
		hip, kn, waist, neck = lerp(12, 40, b), lerp(-20, -60, b), -10 * b, lerp(20, -5, b)
	else -- knee up onto the top
		local c = (u - 0.72) / 0.28
		local s = math.sin(math.pi * c)
		sh, el = lerp(35, 10, c), lerp(78, 10, c)
		rHip, rKnee = lerp(40, 105, s), lerp(-60, -115, s)
		hip, kn, waist, neck = lerp(40, -5, c), lerp(-60, -30, c), lerp(-10, -20, s), -5
	end
	setJoint(J.RightShoulder, D(sh, 0, 8), w)
	setJoint(J.LeftShoulder, D(sh, 0, -8), w)
	setJoint(J.RightElbow, D(el), w)
	setJoint(J.LeftElbow, D(el), w)
	setJoint(J.RightHip, D(rHip or hip), w)
	setJoint(J.RightKnee, D(rKnee or kn), w)
	setJoint(J.LeftHip, D(hip), w)
	setJoint(J.LeftKnee, D(kn), w)
	setJoint(J.Waist, D(waist), w)
	setJoint(J.Neck, D(neck), w)
end
function POSE.roll(J, u)
	local a = math.sin(math.pi * u)
	setJoint(J.RightHip, D(115 * a), 1)
	setJoint(J.LeftHip, D(115 * a), 1)
	setJoint(J.RightKnee, D(-135 * a), 1)
	setJoint(J.LeftKnee, D(-135 * a), 1)
	setJoint(J.RightShoulder, D(70 * a, 0, 15 * a), 1)
	setJoint(J.LeftShoulder, D(70 * a, 0, -15 * a), 1)
	setJoint(J.RightElbow, D(100 * a), 1)
	setJoint(J.LeftElbow, D(100 * a), 1)
	setJoint(J.Neck, D(-40 * a), 1)
	setJoint(J.Waist, D(-30 * a), 1)
	-- head over heels around the tucked body's middle, which travels low along the ground
	local s = u * u * (3 - 2 * u)
	local p = Vector3.new(0, -0.5, 0)
	setJoint(J.Root, CFrame.new(0, -1.4 * a, 0) * CFrame.new(p) * A_(-2 * math.pi * s, 0, 0) * CFrame.new(-p), 1)
end
function POSE.land(J, u)
	crouchPose(J, (1 - u) ^ 1.6, clamp01(u / 0.04), false)
end
function POSE.stumble(J, u)
	crouchPose(J, 0.55 * (1 - u) ^ 1.4, clamp01(u / 0.04), false)
end
function POSE.getup(J, u)
	crouchPose(J, (1 - u) ^ 1.3, 1, true)
end
function POSE.bump(J, u)
	local a = math.sin(math.pi * u)
	setJoint(J.Waist, D(16 * a), a)
	setJoint(J.Neck, D(22 * a), a)
	setJoint(J.RightShoulder, D(60 * a, 0, 20 * a), a)
	setJoint(J.LeftShoulder, D(60 * a, 0, -20 * a), a)
	setJoint(J.RightElbow, D(85 * a), a)
	setJoint(J.LeftElbow, D(85 * a), a)
end

---------------------------------------------------------------------------------------------- local state
local M = {
	V = Vector3.zero, dir = Vector3.new(0, 0, -1), raw = Vector3.zero, controlling = false, lastSet = nil, ext = 1,
	factor = 1, stamina = 1, exhausted = false, lastSprint = -9, sprintHeld = false, sprintToggle = false,
	walkHeld = false, stopT = 0, blockT = 0, air = false, airVy = 0, jumpLockUntil = 0, jumpEnabled = nil,
	fovOff = 0, lookT = 0, lookSent = Vector3.new(999, 0, 0), lastActEnd = -9, sprinting = false, lastFull = 0,
}
local A = { kind = nil } -- the act in progress
local R = { on = false } -- ragdoll

local controls
task.spawn(function()
	local ok, res = pcall(function()
		return require(player:WaitForChild("PlayerScripts"):WaitForChild("PlayerModule", 10)):GetControls()
	end)
	if ok then
		controls = res
	end
end)

-- shift lock moves to Right Shift so Left Shift can sprint
task.spawn(function()
	pcall(function()
		local ml = player:WaitForChild("PlayerScripts"):WaitForChild("PlayerModule", 10):WaitForChild("CameraModule", 5)
			:WaitForChild("MouseLockController", 5)
		local bk = ml:WaitForChild("BoundKeys", 5)
		if bk and bk:IsA("StringValue") then
			bk.Value = "RightShift"
		end
	end)
end)

local function rawInput(hum)
	if controls then
		local mv = controls:GetMoveVector()
		if mv.Magnitude < 0.01 then
			return Vector3.zero
		end
		local cf = workspace.CurrentCamera.CFrame
		local fwd = flat(cf.LookVector)
		if fwd.Magnitude < 0.2 then
			fwd = flat(cf.UpVector)
		end
		fwd = fwd.Unit
		local right = fwd:Cross(Vector3.yAxis)
		local w = right * mv.X - fwd * mv.Z
		return w.Magnitude > 0 and w.Unit * math.min(1, mv.Magnitude) or Vector3.zero
	end
	return hum.MoveDirection
end

local function setJumpEnabled(hum, on)
	if M.jumpEnabled ~= on then
		M.jumpEnabled = on
		hum:SetStateEnabled(ST.Jumping, on)
	end
end

local function recalcFactor(hum)
	local f = 1
	for k, v in hum:GetAttributes() do
		if typeof(v) == "number" and string.sub(k, 1, 12) == "SpeedFactor_" then
			f *= math.max(0, v)
		end
	end
	M.factor = f
end

---------------------------------------------------------------------------------------------- acts
local function startPoseAct(kind, dur, extra)
	A = { kind = kind, dur = dur, t0 = os.clock(), pose = true }
	if extra then
		for k, v in extra do
			A[k] = v
		end
	end
	ActRE:FireServer(kind, dur, workspace:GetServerTimeNow())
end

local function pathAt(keys, u)
	for i = 1, #keys - 1 do
		local k0, k1 = keys[i], keys[i + 1]
		if u <= k1.u or i == #keys - 1 then
			local s = clamp01((u - k0.u) / math.max(k1.u - k0.u, 1e-3))
			local h = k0.p:Lerp(k1.p, s)
			local e = k1.ease == "out" and (1 - (1 - s) ^ 2) or (k1.ease == "in" and s * s) or (s * s * (3 - 2 * s))
			return Vector3.new(h.X, lerp(k0.p.Y, k1.p.Y, e), h.Z)
		end
	end
	return keys[#keys].p
end

-- what's in front of you, and can you get over or onto it?
local function planObstacle(hrp, hum, f)
	local rootH = hrp.Size.Y / 2 + hum.HipHeight
	local feetY = hrp.Position.Y - rootH
	local base = Vector3.new(hrp.Position.X, feetY, hrp.Position.Z)
	local hitD, hitN, hitPart
	for _, h in { 1.7, 3.0, 4.4, 6.0, 7.6 } do
		local r = workspace:Raycast(base + Vector3.new(0, h, 0), f * REACH, params)
		if r and math.abs(r.Normal.Y) < 0.35 and (not hitD or r.Distance < hitD) then
			hitD, hitN, hitPart = r.Distance, r.Normal, r.Instance
		end
	end
	if not hitD then
		return nil
	end
	if not hitPart.Anchored and hitPart.AssemblyLinearVelocity.Magnitude > 4 then
		return nil -- not onto moving traffic
	end
	local fw = -flat(hitN)
	if fw.Magnitude < 0.5 or fw.Unit:Dot(f) < 0.6 then
		return nil
	end
	f = fw.Unit -- square up to the face
	if workspace:Raycast(base + Vector3.new(0, MAX_CLIMB + 0.4, 0), f * (hitD + 1.2), params) then
		return nil -- taller than you can reach
	end
	-- stairs or a ramp (the ground already climbs before the face): that's just a jump
	if hitD > 0.9 then
		local pre = base + f * (hitD - 0.5)
		local gnd = workspace:Raycast(Vector3.new(pre.X, feetY + 3, pre.Z), Vector3.new(0, -4, 0), params)
		if gnd and gnd.Position.Y > feetY + 0.5 then
			return nil
		end
	end
	-- find the top just past the near face (two probes, so a thin rail or fence panel is found too)
	local top, edgeOff
	for _, off in { 0.1, 0.35 } do
		local edge = base + f * (hitD + off)
		local r = workspace:Raycast(Vector3.new(edge.X, feetY + MAX_CLIMB + 0.4, edge.Z), Vector3.new(0, -(MAX_CLIMB - 0.6), 0), params)
		if r and r.Normal.Y >= 0.7 and (not top or r.Position.Y > top.Position.Y + 0.05) then
			top, edgeOff = r, off
		end
	end
	if not top then
		return nil
	end
	local topY = top.Position.Y
	local h = topY - feetY
	if h < MIN_OBST or h > (player:GetAttribute("BodyClimbMax") or MAX_CLIMB) then -- (a heavy body can't reach the top of the tallest walls)
		return nil
	end
	-- thin (a fence, a rail) or deep (a wall top, a counter, a roof)?
	local depth, prev = nil, edgeOff
	for k = 1, 8 do
		local d = 0.35 + k * 0.45
		local q = base + f * (hitD + d)
		if not workspace:Raycast(Vector3.new(q.X, topY + 0.6, q.Z), Vector3.new(0, -1.4, 0), params) then
			depth = prev + 0.2
			break
		end
		prev = d
	end
	local thin = depth ~= nil and depth <= 3.2
	local look = CFrame.lookAt(Vector3.zero, f)
	local function at(s, y)
		local p = base + f * s
		return Vector3.new(p.X, y, p.Z)
	end
	local speedIn = flat(hrp.AssemblyLinearVelocity):Dot(f)
	local start = hrp.Position
	if thin then
		-- room to get the body across and come down beyond?
		local mid = at(hitD + depth / 2, topY + 1.9)
		if not boxClear(look + mid, Vector3.new(1.8, 3.2, depth + 0.8)) then
			return nil
		end
		if not boxClear(look + at(hitD + depth + 1.5, topY + 1.6), Vector3.new(1.8, 3.0, 1.8)) then
			return nil
		end
	else
		local onto = at(hitD + 1.4, topY + rootH + 0.1)
		if not boxClear(look + onto, Vector3.new(1.8, rootH * 2 - 0.4, 1.8)) then
			return nil -- no headroom up there
		end
	end
	if h <= MAX_VAULT then
		if thin then
			local dur = math.clamp(0.62 - 0.012 * math.max(0, speedIn), 0.42, 0.62) * (1 + hitD * 0.06) / (player:GetAttribute("BodyClimbSpeed") or 1)
			return { kind = "vault", f = f, dur = dur, keys = {
				{ u = 0, p = start },
				{ u = 0.38, p = at(hitD - 0.2, topY + 1.55), ease = "out" },
				{ u = 0.8, p = at(hitD + depth + 0.4, topY + 1.45) },
				{ u = 1, p = at(hitD + depth + 1.1, topY + 1.1), ease = "in" },
			}, release = f * math.max(9, speedIn * 0.85) - Vector3.new(0, 6, 0), cost = 0.04 }
		end
		return { kind = "mantle", f = f, dur = (0.6 + 0.05 * h) / (player:GetAttribute("BodyClimbSpeed") or 1), keys = {
			{ u = 0, p = start },
			{ u = 0.45, p = at(hitD - 0.25, math.max(topY + 1.0, feetY + rootH)), ease = "out" },
			{ u = 1, p = at(hitD + 1.3, topY + rootH) },
		}, cost = 0.05 }
	end
	-- (never lower than standing height, or the legs would go into the ground on lower walls)
	local standY = feetY + rootH
	local keys = {
		{ u = 0, p = start },
		{ u = 0.26, p = at(hitD - 0.95, math.max(topY - 2.9, standY)), ease = "out" }, -- hanging, hands on the edge
		{ u = 0.38, p = at(hitD - 0.92, math.max(topY - 3.0, standY)) },
		{ u = 0.72, p = at(hitD - 0.3, topY + 0.9) },
	}
	local release
	if thin then
		table.insert(keys, { u = 1, p = at(hitD + depth + 0.7, topY + 1.5) })
		release = f * 5 - Vector3.new(0, 2, 0)
	else
		table.insert(keys, { u = 1, p = at(hitD + 1.3, topY + rootH) })
	end
	return { kind = "climb", f = f, dur = (1.25 + 0.07 * (h - MAX_VAULT)) / (player:GetAttribute("BodyClimbSpeed") or 1), keys = keys,
		release = release, cost = 0.12 }
end

local function setBodyCollide(char, hrp, saved, mode)
	for _, p in char:GetDescendants() do
		if p:IsA("BasePart") then
			if saved[p] == nil then
				saved[p] = p.CanCollide
			end
			if mode == "none" then
				p.CanCollide = false
			elseif mode == "body" then
				p.CanCollide = p ~= hrp and p.Parent == char
			end
		end
	end
end
local function restoreCollide(saved)
	for p, c in saved do
		if p.Parent then
			p.CanCollide = c
		end
	end
end

local function startPathAct(char, hrp, hum, plan)
	if M.stamina < plan.cost then
		plan.dur *= 1.25 -- tired: slower over
	end
	M.stamina = math.max(0, M.stamina - plan.cost)
	A = { kind = plan.kind, dur = plan.dur, t0 = os.clock(), path = true, keys = plan.keys, f = plan.f,
		release = plan.release, lastP = hrp.Position, saved = {} }
	hum.Jump = false
	setBodyCollide(char, hrp, A.saved, "none")
	hum:ChangeState(ST.Physics)
	ActRE:FireServer(plan.kind, plan.dur, workspace:GetServerTimeNow())
end

local function endAct(hum, hrp)
	if A.path then
		restoreCollide(A.saved)
		if hrp then
			local rel = A.release or (A.f * 4)
			hrp.AssemblyLinearVelocity = rel
			M.V = flat(rel)
			M.dir = A.f
		end
		if hum then
			hum.Jump = false
			hum:ChangeState(A.release and ST.Freefall or ST.Running)
		end
	end
	A = { kind = nil }
	M.lastActEnd = os.clock()
end

---------------------------------------------------------------------------------------------- ragdoll
local RAGJ = {}
for _, n in { "Neck", "Waist", "LeftShoulder", "RightShoulder", "LeftElbow", "RightElbow", "LeftWrist", "RightWrist",
	"LeftHip", "RightHip", "LeftKnee", "RightKnee", "LeftAnkle", "RightAnkle", "Right Shoulder", "Left Shoulder",
	"Right Hip", "Left Hip" } do
	RAGJ[n] = true
end
local function localMotors(char, enabled)
	for _, m in char:GetDescendants() do
		if m:IsA("Motor6D") and RAGJ[m.Name] then
			m.Enabled = enabled
		end
	end
end

local function startRagdoll(char, hrp, hum, vel, minT)
	if R.on or not char:FindFirstChild("NC_Ragdoll") then
		return false
	end
	if A.kind then
		endAct(nil, nil)
	end
	R = { on = true, t0 = os.clock(), minT = minT, saved = {} }
	hum.CameraOffset = Vector3.zero
	setBodyCollide(char, hrp, R.saved, "body")
	localMotors(char, false)
	hum:ChangeState(ST.Physics)
	if vel then
		for p in R.saved do
			if p.Parent == char then
				p.AssemblyLinearVelocity = vel + Vector3.new(math.random() - 0.5, 0, math.random() - 0.5) * 6
			end
		end
	end
	ActRE:FireServer("ragdoll")
	M.V = Vector3.zero
	return true
end

local function getUp(char, hrp, hum)
	local lt = char:FindFirstChild("LowerTorso") or char:FindFirstChild("Torso") or hrp
	local ut = char:FindFirstChild("UpperTorso") or char:FindFirstChild("Torso") or hrp
	local facing = flat(ut.CFrame.UpVector) -- stand up facing where your head was
	if facing.Magnitude < 0.2 then
		facing = flat(ut.CFrame.LookVector)
	end
	facing = facing.Magnitude > 0.05 and facing.Unit or Vector3.new(0, 0, -1)
	local base = lt.Position
	local hit = workspace:Raycast(base + Vector3.new(0, 2, 0), Vector3.new(0, -10, 0), params)
	local gy = hit and hit.Position.Y or (base.Y - 1)
	local rootH = hrp.Size.Y / 2 + hum.HipHeight
	local at = Vector3.new(base.X, gy + rootH, base.Z)
	restoreCollide(R.saved)
	hrp.CFrame = CFrame.lookAt(at, at + facing)
	hrp.AssemblyLinearVelocity = Vector3.zero
	localMotors(char, true)
	R = { on = false }
	M.dir = facing
	hum:ChangeState(ST.GettingUp)
	ActRE:FireServer("getup")
	A = { kind = "getup", dur = 0.9, t0 = os.clock(), pose = true } -- (the server announces it to everyone)
end

---------------------------------------------------------------------------------------------- landings
local function onLand(char, hrp, hum, v)
	local feet = hrp.Position - Vector3.new(0, hrp.Size.Y / 2 + hum.HipHeight, 0)
	if inWater(feet) or inWater(hrp.Position) then
		return
	end
	local hs = M.V.Magnitude
	if v > 68 then
		ActRE:FireServer("fall", v)
	end
	if v > 90 then
		if not startRagdoll(char, hrp, hum, flat(hrp.AssemblyLinearVelocity) * 0.5, v > 120 and 3.5 or 2.2) then
			startPoseAct("land", 0.8)
			M.V = Vector3.zero
		end
	elseif v > 68 then
		if hs > 10 then
			startPoseAct("roll", 0.65, { f = M.dir, v0 = math.min(hs, 18) })
		else
			startPoseAct("land", 0.6)
			M.V = Vector3.zero
		end
	elseif v > 50 then
		startPoseAct("stumble", 0.4)
		M.V *= 0.5
	elseif v > 22 then
		if Anim then
			startPoseAct("soft", 0.32) -- knees give a little (everyone sees it; you keep moving)
		else
			M.dip = os.clock()
			M.dipAmt = clamp01((v - 22) / 28)
		end
	end
	M.jumpLockUntil = os.clock() + (v > 50 and 0.6 or 0.25) -- no bunny hopping
end

---------------------------------------------------------------------------------------------- input
local function onSprint(_, state, input)
	if input.UserInputType == Enum.UserInputType.Keyboard then
		M.sprintHeld = state == Enum.UserInputState.Begin
	elseif state == Enum.UserInputState.Begin then
		M.sprintToggle = not M.sprintToggle
	end
	return Enum.ContextActionResult.Sink
end
local function onWalk(_, state)
	M.walkHeld = state == Enum.UserInputState.Begin
	return Enum.ContextActionResult.Pass
end
CAS:BindActionAtPriority("NC_Sprint", onSprint, true, 2500, Enum.KeyCode.LeftShift, Enum.KeyCode.ButtonL3)
CAS:SetTitle("NC_Sprint", "Sprint")
pcall(function()
	CAS:SetPosition("NC_Sprint", UDim2.new(1, -170, 1, -150))
end)
CAS:BindActionAtPriority("NC_Walk", onWalk, false, 2500, Enum.KeyCode.LeftAlt)

UserInputService.JumpRequest:Connect(function()
	local char = player.Character
	local hrp, hum = bodyOf(char)
	if not hrp or (A.kind and (A.path or LEGS[A.kind])) or R.on or not M.controlling or M.factor < 0.01 then
		return
	end
	local st = hum:GetState()
	if not (st == ST.Running or st == ST.RunningNoPhysics or st == ST.Landed) then
		return
	end
	if os.clock() - M.lastActEnd < 0.3 then
		return
	end
	local f = M.raw.Magnitude > 0.1 and M.raw.Unit or flat(hrp.CFrame.LookVector).Unit
	local plan = planObstacle(hrp, hum, f)
	if plan then
		startPathAct(char, hrp, hum, plan)
	elseif M.sprinting then
		M.stamina = math.max(0, M.stamina - 0.04)
	end
end)

---------------------------------------------------------------------------------------------- HUD
local gui = Instance.new("ScreenGui")
gui.Name = "MovementHUD"
gui.ResetOnSpawn = false
gui.Parent = player:WaitForChild("PlayerGui")
local barBg = Instance.new("Frame")
barBg.AnchorPoint = Vector2.new(0.5, 1)
barBg.Position = UDim2.new(0.5, 0, 1, -88)
barBg.Size = UDim2.fromOffset(170, 6)
barBg.BackgroundColor3 = Color3.fromRGB(10, 12, 16)
barBg.BackgroundTransparency = 0.45
barBg.BorderSizePixel = 0
barBg.Visible = false
barBg.Parent = gui
Instance.new("UICorner", barBg).CornerRadius = UDim.new(1, 0)
local bar = Instance.new("Frame")
bar.Size = UDim2.fromScale(1, 1)
bar.BackgroundColor3 = Color3.fromRGB(26, 216, 216)
bar.BorderSizePixel = 0
bar.Parent = barBg
Instance.new("UICorner", bar).CornerRadius = UDim.new(1, 0)

---------------------------------------------------------------------------------------------- the local body
local function releaseControl(hum)
	if M.controlling then
		M.controlling = false
		local ws = BASE * M.ext
		hum.WalkSpeed = ws
		M.lastSet = ws
	end
end

local function groundBelow(hrp, hum)
	local rootH = hrp.Size.Y / 2 + hum.HipHeight
	return workspace:Raycast(hrp.Position, Vector3.new(0, -(rootH + 1.5), 0), params)
end

local function stepMove(dt)
	local char = player.Character
	local hrp, hum = bodyOf(char)
	if not hrp then
		return
	end
	dt = math.min(dt, 0.1)
	local now = os.clock()
	local cam = workspace.CurrentCamera

	-- ragdolled: let physics have the body; get up once it has come to rest
	if R.on then
		if hum.Health > 0 then
			if hum:GetState() ~= ST.Physics then
				hum:ChangeState(ST.Physics)
			end
			for p, _ in R.saved do
				if p.Parent == char and p ~= hrp then
					p.CanCollide = true
				end
			end
			local lt = char:FindFirstChild("LowerTorso") or char:FindFirstChild("Torso") or hrp
			local t = now - R.t0
			if t > R.minT and (lt.AssemblyLinearVelocity.Magnitude < 3 or t > R.minT + 4) then
				getUp(char, hrp, hum)
			end
		end
		return
	end
	-- vault / mantle / climb: the body follows the planned path
	if A.kind and A.path then
		local u = (now - A.t0) / A.dur
		if u >= 1 or hum.Health <= 0 then
			endAct(hum, hrp)
		else
			local p = pathAt(A.keys, u)
			local v = (p - A.lastP) / math.max(dt, 1 / 240)
			A.lastP = p
			hrp.CFrame = CFrame.lookAt(p, p + A.f)
			hrp.AssemblyLinearVelocity = v
			hrp.AssemblyAngularVelocity = Vector3.zero
			if hum:GetState() ~= ST.Physics then
				hum:ChangeState(ST.Physics)
			end
		end
		return
	end
	if A.kind and A.pose and now - A.t0 >= A.dur then
		A = { kind = nil }
		M.lastActEnd = now
		hum.CameraOffset = Vector3.zero
	end

	local st = hum:GetState()
	local busy = hum.Health <= 0 or hum.SeatPart ~= nil or hum.Sit or hum.PlatformStand or st == ST.Physics or st == ST.Seated
		or st == ST.Dead or st == ST.Climbing or st == ST.Swimming or st == ST.PlatformStanding
	if busy then
		releaseControl(hum)
		setJumpEnabled(hum, true) -- never leave someone unable to jump out of a seat or off a ladder
		M.V = flat(hrp.AssemblyLinearVelocity)
		M.air = false
		-- the sprint view: gone at once when another script takes the body (skydiving, swimming: they save and
		-- restore the FOV themselves, minus the NC_FovOffset we publish), eased out otherwise
		if M.fovOff ~= 0 then
			local newOff = (st == ST.Physics or math.abs(M.fovOff) < 0.05) and 0 or M.fovOff * math.max(0, 1 - dt * 4)
			cam.FieldOfView += newOff - M.fovOff
			M.fovOff = newOff
			cam:SetAttribute("NC_FovOffset", newOff)
		end
		return
	end
	-- someone else changed WalkSpeed (a slow-down, a freeze, a boost): that scales us
	if M.lastSet == nil or math.abs(hum.WalkSpeed - M.lastSet) > 0.01 then
		M.ext = math.clamp(hum.WalkSpeed / BASE, 0, 4)
		if not M.controlling then
			M.V = flat(hrp.AssemblyLinearVelocity)
		end
	end
	M.controlling = true
	local mult = M.ext * M.factor

	local raw = rawInput(hum)
	M.raw = raw
	local mag = raw.Magnitude
	local grounded = st ~= ST.Freefall and st ~= ST.Jumping and st ~= ST.FallingDown
	if not grounded then
		M.air = true
		M.airVy = hrp.AssemblyLinearVelocity.Y
	end

	-- gait
	if mag < 0.05 then
		M.stopT += dt
		if M.stopT > 0.4 then
			M.sprintToggle = false
		end
	else
		M.stopT = 0
	end
	local target, sprinting = 0, false
	if mag >= 0.05 then
		if M.walkHeld then
			target = WALK
		elseif mag < 0.55 then
			target = WALK * math.clamp(mag / 0.55, 0.35, 1)
		elseif (M.sprintHeld or M.sprintToggle) and not M.exhausted and M.stamina > 0 then
			sprinting = true
			target = JOG + (SPRINT - JOG) * (0.55 + 0.45 * clamp01(M.stamina / 0.3))
		else
			target = JOG
		end
	end
	-- the ground: slopes, and what you're standing on (moving floors)
	local g = groundBelow(hrp, hum)
	local floorVel = Vector3.zero
	if g then
		if not g.Instance.Anchored then
			floorVel = flat(g.Instance:GetVelocityAtPosition(g.Position))
		end
		local d = mag > 0.05 and raw.Unit or M.dir
		local n = g.Normal
		if n.Y > 0.3 then
			local grade = -(n.X * d.X + n.Z * d.Z) / n.Y
			target *= grade > 0 and (1 - 0.4 * clamp01(grade)) or (1 + 0.08 * clamp01(-grade))
		end
	end
	target *= mult

	-- a pose act takes the legs for a moment (soft landings, skids and pivots are just how the body looks)
	if A.kind and A.pose and LEGS[A.kind] then
		local u = clamp01((now - A.t0) / A.dur)
		if A.kind == "roll" then
			M.dir = A.f or M.dir
			M.V = M.dir * lerp(A.v0 or 14, 8, u) * mult
		else
			M.V = M.V * math.max(0, 1 - dt * 12)
		end
		local shake = (A.kind == "land" or A.kind == "stumble") and (1 - u) * 0.25 or 0
		hum.CameraOffset = shake > 0.01 and Vector3.new(0, -shake * (A.kind == "land" and 1.6 or 0.8), 0) or Vector3.zero
		sprinting = false
	elseif grounded then
		local speed = M.V.Magnitude
		local dir = speed > 0.05 and M.V.Unit or M.dir
		if target > 0 then
			local want = raw.Unit
			if speed < 2 then
				dir = want -- from (nearly) standing you just turn and go
			end
			local ang = math.atan2(dir:Cross(want).Y, dir:Dot(want))
			if math.abs(ang) > PIVOT_ANGLE and speed > 13 then
				speed = math.max(0, speed - PIVOT_DECEL * dt) -- plant and brake before turning round
				if not A.kind then
					startPoseAct("pivot", 0.38)
				end
			else
				local maxTurn = math.min(TURN_MAX, A_LAT / math.max(speed, 1)) * dt
				dir = CFrame.Angles(0, math.clamp(ang, -maxTurn, maxTurn), 0):VectorToWorldSpace(dir)
				if speed < target then
					local a = lerp(ACCEL0, ACCEL1, clamp01(speed / SPRINT))
					speed = math.min(target, speed + a * dt)
				else
					speed = math.max(target, speed - SLOW_DECEL * dt)
				end
			end
		else
			if speed > 19 and not A.kind then
				startPoseAct("skid", 0.55) -- stopping from a sprint: lean back, dig the front heel in
			end
			speed = math.max(0, speed - (speed > JOG + 1 and SKID_DECEL or STOP_DECEL) * dt)
		end
		-- walls take your momentum: if the body isn't actually getting where the momentum says, bleed it off
		local actual = flat(hrp.AssemblyLinearVelocity) - floorVel
		local along = actual:Dot(dir)
		if speed > 2 and along < speed - 7 then
			M.blockT += dt
			if M.blockT > 0.18 then
				speed = math.max(0, along) + 1
			end
		else
			M.blockT = 0
		end
		-- flat out into a wall: it knocks you back
		if speed > 21 then
			local r = workspace:Raycast(hrp.Position + Vector3.new(0, 0.5, 0), dir * 1.9, params)
			if r and math.abs(r.Normal.Y) < 0.3 and r.Normal:Dot(dir) < -0.8 then
				speed = 0
				hrp.AssemblyLinearVelocity = -dir * 10 + Vector3.new(0, 4, 0)
				startPoseAct("bump", 0.45)
			end
		end
		M.V = dir * speed
		if speed > 0.05 then
			M.dir = dir
		end
	else
		-- in the air you keep what you had; a little steering, no brakes
		if target > 0 then
			local want = raw.Unit * target
			local dv = want - M.V
			if dv.Magnitude > AIR_ACCEL * dt then
				dv = dv.Unit * AIR_ACCEL * dt
			end
			local nv = M.V + dv
			if nv.Magnitude > math.max(M.V.Magnitude, target) then
				nv = nv.Unit * math.max(M.V.Magnitude, target)
			end
			M.V = nv
		end
	end

	-- drive the Humanoid with the momentum
	local speed = M.V.Magnitude
	if controls then
		hum:Move(speed > 0.05 and M.V.Unit or Vector3.zero, false)
	end
	hum.WalkSpeed = speed
	M.lastSet = speed
	setJumpEnabled(hum, M.factor > 0.01 and now >= M.jumpLockUntil and not (A.kind and (A.path or LEGS[A.kind])))

	-- stamina
	M.sprinting = sprinting and speed > JOG + 0.5
	if M.sprinting then
		M.stamina = math.max(0, M.stamina - dt / (player:GetAttribute("BodySprintTime") or SPRINT_TIME))
		M.lastSprint = now
		if M.stamina <= 0 then
			M.exhausted = true
		end
	elseif now - M.lastSprint > 1 then
		M.stamina = math.min(1, M.stamina + dt * (player:GetAttribute("BodyRegen") or 1) / (speed < 1 and REGEN_IDLE or REGEN_TIME))
	end
	if M.exhausted and M.stamina > 0.35 then
		M.exhausted = false
	end
	if M.stamina < 0.999 or M.sprinting then
		M.lastFull = now
	end
	barBg.Visible = now - M.lastFull < 1.5
	bar.Size = UDim2.fromScale(M.stamina, 1)
	bar.BackgroundColor3 = M.exhausted and Color3.fromRGB(255, 90, 80) or Color3.fromRGB(26, 216, 216)

	-- the view opens up a little at a sprint (added on top of whatever FOV the game sets)
	local wantOff = M.sprinting and SPRINT_FOV * clamp01((speed - JOG) / (SPRINT - JOG)) or 0
	local newOff = M.fovOff + (wantOff - M.fovOff) * math.min(1, dt * 4)
	if math.abs(newOff - M.fovOff) > 1e-4 then
		cam.FieldOfView += newOff - M.fovOff
		M.fovOff = newOff
		cam:SetAttribute("NC_FovOffset", newOff)
	end

	-- where you're looking, and how hard you're breathing, for everyone else
	if now - M.lookT > 0.1 then
		local lv = hrp.CFrame:VectorToObjectSpace(cam.CFrame.LookVector)
		local yaw = math.deg(math.atan2(-lv.X, -lv.Z))
		local pitch = math.deg(math.asin(math.clamp(lv.Y, -1, 1)))
		if math.abs(yaw) > 110 then
			yaw, pitch = 0, 0
		end
		local v = Vector3.new(math.clamp(yaw, -75, 75), math.clamp(pitch, -45, 45), M.stamina)
		if (v - M.lookSent).Magnitude > 3 or math.abs(v.Z - M.lookSent.Z) > 0.05 then
			M.lookSent = v
			M.lookT = now
			LookRE:FireServer(v)
		end
	end
end
RunService:BindToRenderStep("NC_Movement", Enum.RenderPriority.Input.Value + 1, stepMove)

---------------------------------------------------------------------------------------------- every body on screen
local CS = setmetatable({}, { __mode = "k" })
local NOSKIP = {}
local RIGHT_ARM = { RightShoulder = true, RightElbow = true, RightWrist = true }
local BOTH_ARMS = { RightShoulder = true, RightElbow = true, RightWrist = true, LeftShoulder = true, LeftElbow = true, LeftWrist = true }
local function stateOf(char)
	local s = CS[char]
	if not s then
		s = { v = Vector3.zero, vPrev = Vector3.zero, acc = Vector3.zero, yaw = 0, yawRate = 0, pitch = 0, roll = 0,
			ly = 0, lp = 0, ik = 0 }
		CS[char] = s
	end
	return s
end

-- sitting in a car: the stock sit animation leaves the shins hanging straight down, and car seats sit low over the
-- floor, so the feet went through it. Thighs rise a little, shins reach forward to the pedals / footwell.
local function carSeatPose(J, driver)
	local h, shin = rad(108), rad(52)
	local k = shin - h
	setJoint(J.RightHip, A_(h, 0, rad(-4)), 1)
	setJoint(J.LeftHip, A_(h, 0, rad(4)), 1)
	setJoint(J.RightKnee, A_(k, 0, 0), 1)
	setJoint(J.LeftKnee, A_(k, 0, 0), 1)
	setJoint(J.RightAnkle, A_(-shin + rad(10), 0, 0), 1)
	setJoint(J.LeftAnkle, A_(-shin + rad(10), 0, 0), 1)
	if driver then -- hands on the wheel
		setJoint(J.RightShoulder, D(62, 0, 8), 1)
		setJoint(J.LeftShoulder, D(62, 0, -8), 1)
		setJoint(J.RightElbow, D(28), 1)
		setJoint(J.LeftElbow, D(28), 1)
	end
end

local BIKE_IDS = {}
do
	local ok, Vehicles = pcall(function()
		return require(game:GetService("ReplicatedStorage"):WaitForChild("NCVehicles", 5))
	end)
	if ok and type(Vehicles) == "table" then
		for _, v in Vehicles.List or Vehicles do
			if type(v) == "table" and v.bike then
				BIKE_IDS[v.id] = true
			end
		end
	end
end
local function isBikeId(id)
	return id ~= nil and BIKE_IDS[id] == true
end

local frame = 0
RunService.Stepped:Connect(function(_, dt)
	dt = math.clamp(dt, 1 / 240, 0.1)
	frame += 1
	if frame % 30 == 1 then
		refreshFilter()
	end
	local cam = workspace.CurrentCamera
	local camPos = cam.CFrame.Position
	local now = os.clock()
	local sNow = workspace:GetServerTimeNow()
	local g = workspace.Gravity
	for _, p in Players:GetPlayers() do
		local char = p.Character
		local hrp, hum = bodyOf(char)
		if not hrp or (hrp.Position - camPos).Magnitude > 160 then
			continue
		end
		local isMe = p == player
		local seatCar = hum.SeatPart and hum.SeatPart.Parent
		if hum.Health > 0 and seatCar and seatCar:GetAttribute("NCLowrider") and not isBikeId(seatCar:GetAttribute("Vehicle")) then
			carSeatPose(jointsOf(char), hum.SeatPart.Name == "DriveSeat")
			continue
		end
		if hum.Health <= 0 or hum.SeatPart or char:GetAttribute("SwimPose") or char:GetAttribute("ChuteState") or char:GetAttribute("Workout") then
			continue
		end
		if (isMe and R.on) or (not isMe and char:GetAttribute("Ragdoll")) then
			continue
		end
		local J = jointsOf(char)
		local cs = stateOf(char)
		local st = hum:GetState()
		if not isMe and (st == ST.Climbing or st == ST.Swimming) then
			continue -- ladders and terrain water keep their own animations
		end

		-- how this body is moving
		local vel = (isMe and M.controlling) and M.V or flat(hrp.AssemblyLinearVelocity)
		cs.vPrev = cs.v
		cs.v = cs.v:Lerp(vel, 1 - math.exp(-dt / (isMe and 0.03 or 0.1)))
		cs.acc = cs.acc:Lerp((cs.v - cs.vPrev) / dt, 1 - math.exp(-dt / 0.12))
		local speed = cs.v.Magnitude
		if speed > 2 then
			local yaw = math.atan2(-cs.v.X, -cs.v.Z)
			cs.yawRate += (wrapAngle(yaw - cs.yaw) / dt - cs.yawRate) * (1 - math.exp(-dt / 0.12))
			cs.yaw = yaw
		else
			cs.yawRate *= math.exp(-dt / 0.1)
		end
		local grounded
		if isMe then
			grounded = st == ST.Running or st == ST.RunningNoPhysics or st == ST.Landed
			if st == ST.Jumping and not cs.wasJump then
				cs.takeoffT = now
			end
			cs.wasJump = st == ST.Jumping
		else
			local vy = hrp.AssemblyLinearVelocity.Y
			grounded = math.abs(vy) < 4
			if vy > 8 and (cs.lastVy or 0) <= 8 then
				cs.takeoffT = now
			end
			cs.lastVy = vy
		end

		-- where they're looking, and how out of breath they are
		local ly, lp, stamina
		if isMe then
			ly, lp, stamina = M.lookSent.X, M.lookSent.Y, M.stamina
			if M.lookSent.X == 999 then
				ly, lp = 0, 0
			end
		else
			local lk = char:GetAttribute("Look")
			if typeof(lk) == "Vector3" then
				ly, lp, stamina = lk.X, lk.Y, lk.Z
			else
				ly, lp, stamina = 0, 0, 1
			end
		end

		-- an act in progress?
		local kind, u
		if isMe then
			if A.kind then
				kind, u = A.kind, (now - A.t0) / A.dur
			end
		else
			local s = char:GetAttribute("MoveAct")
			if typeof(s) == "string" then
				local n, d, t0 = string.match(s, "^(%a+)|([%d%.]+)|([%d%.]+)$")
				if n and (POSE[n] or (Anim and ACT_CLIP[n] and Anim.has(ACT_CLIP[n]))) then
					local uu = (sNow - tonumber(t0)) / math.max(tonumber(d), 0.05)
					if uu >= 0 and uu <= 1 then
						kind, u = n, uu
					end
				end
			end
		end
		local hasAct = kind ~= nil and u >= 0 and u <= 1
		if isMe and not hasAct and (st == ST.Physics or st == ST.Climbing or st == ST.Swimming or st == ST.Seated or st == ST.PlatformStanding) then
			continue -- someone else is driving this body (swimming, diving board, skydiving, ladders)
		end
		if cs.acting and not hasAct then
			-- act over: forget what we wrote so nothing builds on a leftover pose (no snap: the next pose takes over)
			cs.acting = false
			for _, n in JN do
				if J[n] then
					written[J[n]] = nil
				end
			end
		end

		-- the Blender animations: idle / walk / jog / sprint by speed on one step cycle, jump and fall in the air
		local skip = NOSKIP
		if char:GetAttribute("BallPose") then
			skip = BOTH_ARMS -- the basketball script has the arms
		elseif char:FindFirstChildOfClass("Tool") or char:GetAttribute("Eating") and (workspace:GetServerTimeNow() - (tonumber(string.match(char:GetAttribute("Eating"), "|([%d%.]+)$") or "0") or 0)) < 1.9 then
			skip = RIGHT_ARM -- holding something: the tool pose keeps that arm
		end
		local animOn = Anim ~= nil and J.L1 ~= nil
		if animOn then
			local pose = Anim.locomotion(cs, speed, grounded, dt, now, (stamina or 1) < 0.35)
			for jn, cf in pose do
				if not skip[jn] then
					setJoint(J[jn], cf, 1)
				end
			end
		end
		if hasAct then
			local clip = animOn and ACT_CLIP[kind]
			local c = clip and Anim.clip(clip)
			if c then
				local w = math.min(c.blendIn > 0 and u / c.blendIn or 1, c.blendOut > 0 and (1 - u) / c.blendOut or 1)
				local pose = Anim.blendInto({}, clip, u, 1)
				for jn, cf in pose do
					if not skip[jn] then
						setJoint(J[jn], cf, math.clamp(w, 0, 1))
					end
				end
			elseif POSE[kind] then
				POSE[kind](J, u)
			end
			cs.ik = 0
			cs.acting = true
			continue
		end

		-- lean: into acceleration (back when braking) and into corners, like a body keeping its balance
		local facing = flat(hrp.CFrame.LookVector)
		facing = facing.Magnitude > 0.01 and facing.Unit or Vector3.new(0, 0, -1)
		local tp, tr = 0, 0
		if grounded then
			tp = math.clamp(cs.acc:Dot(facing) * 0.0045, -0.15, 0.12)
			if not animOn then
				tp += math.clamp(speed / SPRINT, 0, 1.2) * 0.055 -- (the run cycles already lean with speed)
			end
			tr = math.clamp(math.atan(speed * cs.yawRate / g) * 0.6, -0.32, 0.32)
		end
		cs.pitch += (tp - cs.pitch) * math.min(1, dt * 9)
		cs.roll += (tr - cs.roll) * math.min(1, dt * 9)

		-- feet on the ground: standing on stairs or a slope, the lower foot reaches down, the hips drop to it and
		-- the higher knee bends
		local rootH = hrp.Size.Y / 2 + hum.HipHeight
		local drop = 0
		cs.ik += ((grounded and speed < 0.7 and 1 or 0) - cs.ik) * math.min(1, dt * 8)
		if cs.ik > 0.01 and J.L1 and (hrp.Position - camPos).Magnitude < 80 then
			local y0 = hrp.Position.Y - rootH
			local rise = {}
			local dy = {}
			for _, side in { "Left", "Right" } do
				local foot = char:FindFirstChild(side .. "Foot")
				if foot then
					local fp = foot.Position
					local hit = workspace:Raycast(Vector3.new(fp.X, y0 + 2.0, fp.Z), Vector3.new(0, -5, 0), params)
					-- (nothing under that foot, e.g. over a kerb or roof edge: leave it be rather than reach into the gap)
					dy[side] = hit and math.clamp(hit.Position.Y - y0, -1.3, 1.3) or 0
				end
			end
			if dy.Left and dy.Right then
				drop = math.min(0, dy.Left, dy.Right) * cs.ik
				local L1, L2 = J.L1, J.L2
				for _, side in { "Left", "Right" } do
					local r = dy[side] * cs.ik - drop
					if r > 0.03 then
						local Dd = math.max((L1 + L2) * 0.5, L1 + L2 - 0.02 - r)
						local inner = math.acos(math.clamp((L1 * L1 + L2 * L2 - Dd * Dd) / (2 * L1 * L2), -1, 1))
						local hipA = math.acos(math.clamp((L1 * L1 + Dd * Dd - L2 * L2) / (2 * L1 * Dd), -1, 1))
						local kneeA = -(math.pi - inner)
						rise[side] = { hipA, kneeA }
					end
				end
				for side, a in rise do
					addTo(J[side .. "Hip"], A_(a[1], 0, 0))
					addTo(J[side .. "Knee"], A_(a[2], 0, 0))
					addTo(J[side .. "Ankle"], A_(-(a[1] + a[2]), 0, 0))
				end
			end
		end

		-- the whole body tips about the feet (so they stay put); a soft landing gives at the knees
		local root = J.Root
		if root and root:IsA("Motor6D") and root.Part0 == hrp then
			local jy = root.C0.Position.Y
			local pv = Vector3.new(0, -rootH - jy, 0)
			local dip = 0
			if isMe and M.dip then
				local t = (now - M.dip) / 0.28
				if t < 1 then
					dip = -0.45 * (M.dipAmt or 0.5) * math.sin(math.pi * t)
				else
					M.dip = nil
				end
			end
			addTo(root, CFrame.new(0, drop + dip, 0) * CFrame.new(pv) * A_(-cs.pitch, 0, cs.roll) * CFrame.new(-pv))
		end

		-- head and shoulders turn toward where they're looking; out of breath, the chest heaves
		cs.ly += (ly - cs.ly) * math.min(1, dt * 8)
		cs.lp += (lp - cs.lp) * math.min(1, dt * 8)
		local yawR, pitchR = rad(cs.ly), rad(cs.lp)
		local firstPerson = isMe and char:FindFirstChild("Head") and (camPos - char.Head.Position).Magnitude < 1.5
		if not firstPerson then
			addTo(J.Neck, A_(0, yawR * 0.55, 0) * A_(pitchR * 0.6, 0, 0))
		end
		local tired = (1 - math.clamp(stamina or 1, 0, 1)) ^ 1.5
		local breath = math.sin(now * math.pi * 2 * 1.4) * 0.05 * tired
		local sprintLean = animOn and 0 or -0.1 * clamp01((speed - JOG) / (SPRINT - JOG))
		addTo(J.Waist, A_(0, yawR * 0.35, 0) * A_(pitchR * 0.2 + breath + sprintLean, 0, 0))
	end
end)

---------------------------------------------------------------------------------------------- per character
local function onCharacter(char)
	local hum = char:WaitForChild("Humanoid", 10)
	local hrp = char:WaitForChild("HumanoidRootPart", 10)
	if not (hum and hrp) then
		return
	end
	if A.kind then
		A = { kind = nil }
	end
	R = { on = false }
	M.V, M.controlling, M.lastSet, M.ext, M.air, M.jumpEnabled = Vector3.zero, false, nil, 1, false, nil
	M.stamina, M.exhausted = 1, false
	hum:SetAttribute("NC_Movement", true) -- (local only: tells the pool and TV scripts to slow you through SpeedFactor_)
	if hum.UseJumpPower then
		hum.JumpPower = math.sqrt(2 * workspace.Gravity * JUMP_HEIGHT * (player:GetAttribute("BodyJump") or 1))
	else
		hum.JumpHeight = JUMP_HEIGHT * (player:GetAttribute("BodyJump") or 1)
	end
	recalcFactor(hum)
	hum.AttributeChanged:Connect(function()
		recalcFactor(hum)
	end)
	hum.StateChanged:Connect(function(_, new)
		if new == ST.Landed or ((new == ST.Running or new == ST.RunningNoPhysics) and M.air) then
			if M.air and not R.on and not A.path then
				onLand(char, hrp, hum, -M.airVy)
			end
			M.air = false
		elseif new == ST.Physics or new == ST.Swimming or new == ST.Seated or new == ST.Dead or new == ST.Climbing then
			M.air = false
		end
	end)
	-- bodies crumple when they die (the server unhooks the joints for everyone; this makes them land on the floor)
	hum.Died:Connect(function()
		if A.kind and A.path then
			restoreCollide(A.saved)
		end
		A = { kind = nil }
		if not R.on and char:FindFirstChild("NC_Ragdoll") then
			R = { on = true, t0 = os.clock(), minT = math.huge, saved = {}, dead = true }
			setBodyCollide(char, hrp, R.saved, "body")
			localMotors(char, false)
		end
	end)
	-- hit by something big and fast (a car): knocked down
	for _, part in char:GetChildren() do
		if part:IsA("BasePart") then
			part.Touched:Connect(function(other)
				if R.on or hum.Health <= 0 or hum.SeatPart or other.Anchored or not other.CanCollide or other:IsDescendantOf(char) then
					return
				end
				if hum:GetState() == ST.Physics or char:GetAttribute("SwimPose") or char:GetAttribute("ChuteState") then
					return -- swimming, skydiving or mid-vault: another script owns the body
				end
				local model = other:FindFirstAncestorOfClass("Model")
				if model and model:FindFirstChildOfClass("Humanoid") then
					return
				end
				local ov = other.AssemblyLinearVelocity
				local rel = ov - hrp.AssemblyLinearVelocity
				if ov.Magnitude > 30 and rel.Magnitude > 36 and other.AssemblyMass > 40 then
					local push = ov * 0.8 + Vector3.new(0, 16 + rel.Magnitude * 0.18, 0)
					if not startRagdoll(char, hrp, hum, push, 2.6) then
						startPoseAct("stumble", 0.5)
					end
				end
			end)
		end
	end
end
player.CharacterAdded:Connect(onCharacter)
if player.Character then
	task.spawn(onCharacter, player.Character)
end
