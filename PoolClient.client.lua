--!nonstrict
-- PoolClient: swimming, the springboard, dives and splashes. Works in any part tagged NC_Water (an invisible box
-- whose top face is the water surface: every Blender pool gets one from BuildingKit).
--
-- Swimming (your own character, physics run on your machine like normal walking):
--   * Get in deeper than your chest (or jump/dive in) and you swim. WASD swims where the camera looks: look down
--     and you dive under, look up and you come back up; Space rises, C (or Ctrl, B on a pad) sinks.
--   * Real water: you keep your momentum and the water bleeds it off (quadratic drag), so a dive carries you a few
--     studs deep and then you float back up; you float with your head out when you stop. ~9 studs/s freestyle at
--     the surface (a fit swimmer's 2 m/s at this scale), slower underwater.
--   * Space at the wall pulls you out onto the deck. Walk out up the steps. Chest-deep water slows walking.
-- Swim motions (everyone sees them, on every client): freestyle with alternating arm windmill, high-elbow recovery,
-- body roll, a six-beat flutter kick and a breath to the side; treading water with sculling arms and an eggbeater
-- kick when you stop; arms-overhead streamline on a dive, a tuck for a cannonball, a pull-up at the wall.
-- Springboard: walk out to the end and jump. Land back on the end and jump again right as you touch down to ride
-- the board's recoil higher (up to 4 bounces). Off the end you dive head-first (the body follows the arc), or press
-- C in the air for a cannonball. Flight uses real gravity (37 studs/s^2), so the air time is a real diver's ~1.3 s.
-- Splashes, ripples, stroke splashes and sounds for everyone; underwater the view turns blue and muffled.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local Lighting = game:GetService("Lighting")
local SoundService = game:GetService("SoundService")
local Debris = game:GetService("Debris")
local TweenService = game:GetService("TweenService")
local RS = game:GetService("ReplicatedStorage")

local player = Players.LocalPlayer
local Remotes = RS:WaitForChild("Remotes")
local PoseRE = Remotes:WaitForChild("SwimPose")
local HoopRE = Remotes:WaitForChild("FloatyHoop")

local G_REAL = 37.0
local SWIM_SPEED, UNDER_SPEED = 9.0, 7.5
local SND_SPLASH = "rbxasset://sounds/impact_water.mp3"
local SND_STROKE = "rbxasset://sounds/action_swim.mp3"
local SND_BOARD = "rbxasset://sounds/action_jump_land.mp3"
local TEX_DROP = "rbxasset://textures/particles/smoke_main.dds"
local TEX_SPARK = "rbxasset://textures/particles/sparkles_main.dds"
local BOUNCE_VY = { 13, 17, 21, 24 } -- springboard launch speeds: about 2, 4, 6 and 8 studs over the board
local rad = math.rad
local TAU = 2 * math.pi

local function flat(v)
	return Vector3.new(v.X, 0, v.Z)
end

-- the water a point is in (or up to 12 studs above): part, surface height
local function waterAt(pos, slack)
	-- where volumes overlap (a raised spa set into a pool) the highest surface wins
	slack = slack or 0
	local best, bestTop = nil, -math.huge
	for _, w in CollectionService:GetTagged("NC_Water") do
		if w:IsA("BasePart") and w:IsDescendantOf(workspace) then
			local lp = w.CFrame:PointToObjectSpace(pos)
			local h = w.Size * 0.5
			if math.abs(lp.X) <= h.X + slack and math.abs(lp.Z) <= h.Z + slack and lp.Y <= h.Y + 12 and lp.Y >= -h.Y - 1 then
				local top = w.Position.Y + h.Y
				if top > bestTop then
					best, bestTop = w, top
				end
			end
		end
	end
	if best then
		return best, bestTop
	end
	return nil
end

local function bodyOf(char)
	local hrp = char and char:FindFirstChild("HumanoidRootPart")
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	local head = char and char:FindFirstChild("Head")
	if hrp and hum and head then
		return hrp, hum, head
	end
	return nil
end

local function sound(parent, id, volume, speed, maxDist)
	local s = Instance.new("Sound")
	s.SoundId = id
	s.Volume = volume
	s.PlaybackSpeed = speed * (0.94 + math.random() * 0.12)
	s.RollOffMinDistance = 6
	s.RollOffMaxDistance = maxDist or 90
	s.Parent = parent
	s:Play()
	Debris:AddItem(s, 3)
end

local function fxAnchor(pos)
	local p = Instance.new("Part")
	p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch = true, false, false, false
	p.Transparency = 1
	p.Size = Vector3.one * 0.2
	p.CFrame = CFrame.new(pos)
	p.Parent = workspace
	Debris:AddItem(p, 3)
	return p
end

---------------------------------------------------------------------------------------------- splashes
local function emitter(parent, props)
	local e = Instance.new("ParticleEmitter")
	e.Texture = props.Texture or TEX_DROP
	e.Rate = 0
	e.EmissionDirection = Enum.NormalId.Top
	for k, v in props do
		if k ~= "Texture" and k ~= "Count" then
			e[k] = v
		end
	end
	e.Parent = parent
	e:Emit(props.Count)
	return e
end

local function ripple(pos, size, time)
	local r = Instance.new("Part")
	r.Shape = Enum.PartType.Cylinder
	r.Anchored, r.CanCollide, r.CanQuery, r.CanTouch = true, false, false, false
	r.Material = Enum.Material.SmoothPlastic
	r.Color = Color3.fromRGB(235, 248, 255)
	r.Transparency = 0.45
	r.Size = Vector3.new(0.04, 1.2, 1.2)
	r.CFrame = CFrame.new(pos + Vector3.new(0, 0.03, 0)) * CFrame.Angles(0, 0, math.pi / 2)
	r.Parent = workspace
	TweenService:Create(r, TweenInfo.new(time, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { Size = Vector3.new(0.04, size, size), Transparency = 1 }):Play()
	Debris:AddItem(r, time + 0.1)
end

local function splash(pos, speed, big)
	local s = math.clamp(speed / 30, 0.25, 1.4) * (big and 1.8 or 1)
	local a = fxAnchor(pos)
	local white = ColorSequence.new(Color3.fromRGB(255, 255, 255), Color3.fromRGB(200, 235, 255))
	emitter(a, { -- the column and droplets
		Count = math.floor(45 * s), Color = white, Speed = NumberRange.new(9 * s, 24 * s), SpreadAngle = Vector2.new(22, 22),
		Acceleration = Vector3.new(0, -55, 0), Lifetime = NumberRange.new(0.5, 1.1), Drag = 0.6,
		Size = NumberSequence.new(0.42, 0.12), Transparency = NumberSequence.new(0.05, 1),
	})
	emitter(a, { -- the crown and mist
		Count = math.floor(20 * s), Color = white, Speed = NumberRange.new(3 * s, 8 * s), SpreadAngle = Vector2.new(85, 85),
		Acceleration = Vector3.new(0, -10, 0), Lifetime = NumberRange.new(0.6, 1.3), Drag = 1.5,
		Size = NumberSequence.new(1.0 * s, 2.6 * s), Transparency = NumberSequence.new(0.35, 1),
	})
	ripple(pos, 7 + 9 * s, 1.4)
	ripple(pos, 4 + 5 * s, 0.9)
	sound(a, SND_SPLASH, math.clamp(0.35 + 0.45 * s, 0.3, 1.2), big and 0.8 or 1.0, 120)
end

local function strokeSplash(pos)
	local a = fxAnchor(pos)
	emitter(a, {
		Count = 6, Color = ColorSequence.new(Color3.fromRGB(255, 255, 255)), Speed = NumberRange.new(4, 9), SpreadAngle = Vector2.new(35, 35),
		Acceleration = Vector3.new(0, -50, 0), Lifetime = NumberRange.new(0.3, 0.6), Size = NumberSequence.new(0.25, 0.08),
		Transparency = NumberSequence.new(0.1, 1),
	})
	sound(a, SND_STROKE, 0.18, 1.0, 60)
end

---------------------------------------------------------------------------------------------- joints (all rigs)
local JOINTS = { "RightShoulder", "RightElbow", "LeftShoulder", "LeftElbow", "RightHip", "RightKnee", "LeftHip", "LeftKnee",
	"RightAnkle", "LeftAnkle", "Neck", "Waist" }
local JSET = {}
for _, n in JOINTS do
	JSET[n] = true
end
local jointCache = setmetatable({}, { __mode = "k" })
local function jointsOf(char)
	local e = jointCache[char]
	if e and (e.n >= 10 or os.clock() - e.t < 2) then
		return e
	end
	e = { n = 0, t = os.clock() }
	for _, d in char:GetDescendants() do
		if JSET[d.Name] and (d:IsA("Motor6D") or d:IsA("AnimationConstraint")) and not e[d.Name] then
			e[d.Name] = d
			e.n += 1
		end
	end
	jointCache[char] = e
	return e
end

-- rotation-only override: q = where Part1 points relative to Part0 (identity = the rig's rest pose)
local function setJoint(j, q, alpha)
	if not j then
		return
	end
	local c0, c1
	if j:IsA("Motor6D") then
		c0, c1 = j.C0.Rotation, j.C1.Rotation
	else
		local a0, a1 = j.Attachment0, j.Attachment1
		local p0 = a0 and a0:FindFirstAncestorWhichIsA("BasePart")
		local p1 = a1 and a1:FindFirstAncestorWhichIsA("BasePart")
		if not (p0 and p1) then
			return
		end
		c0, c1 = p0.CFrame:ToObjectSpace(a0.WorldCFrame).Rotation, p1.CFrame:ToObjectSpace(a1.WorldCFrame).Rotation
	end
	local target = c0:Inverse() * q * c1
	j.Transform = alpha < 1 and j.Transform:Lerp(target, alpha) or target
end

local A = CFrame.Angles
local function poseFreestyle(J, ph, w)
	local th = math.pi - TAU * ph -- overhead -> pull under the body -> hips -> recover over the back
	setJoint(J.RightShoulder, A(th, 0, rad(8)), w)
	setJoint(J.LeftShoulder, A(th + math.pi, 0, rad(-8)), w)
	setJoint(J.RightElbow, A(rad(15 + 80 * math.max(0, -math.sin(th))), 0, 0), w)
	setJoint(J.LeftElbow, A(rad(15 + 80 * math.max(0, -math.sin(th + math.pi))), 0, 0), w)
	local kick = math.sin(ph * TAU * 3) -- six-beat kick
	setJoint(J.RightHip, A(rad(14 * kick), 0, 0), w)
	setJoint(J.LeftHip, A(rad(-14 * kick), 0, 0), w)
	setJoint(J.RightKnee, A(rad(-8 - 16 * math.max(0, kick)), 0, 0), w)
	setJoint(J.LeftKnee, A(rad(-8 - 16 * math.max(0, -kick)), 0, 0), w)
	setJoint(J.RightAnkle, A(rad(-40), 0, 0), w)
	setJoint(J.LeftAnkle, A(rad(-40), 0, 0), w)
	setJoint(J.Neck, A(0, rad(70 * math.max(0, math.sin(ph * math.pi)) ^ 6), 0), w) -- breathe every other stroke
end

local function poseTread(J, ph, w)
	local sc = math.sin(ph * TAU)
	setJoint(J.RightShoulder, A(rad(20), rad(25 * sc), rad(70)), w)
	setJoint(J.LeftShoulder, A(rad(20), rad(-25 * sc), rad(-70)), w)
	setJoint(J.RightElbow, A(rad(35), 0, 0), w)
	setJoint(J.LeftElbow, A(rad(35), 0, 0), w)
	setJoint(J.RightHip, A(rad(40 + 25 * sc), 0, rad(10)), w)
	setJoint(J.LeftHip, A(rad(40 - 25 * sc), 0, rad(-10)), w)
	setJoint(J.RightKnee, A(rad(-60 - 25 * sc), 0, 0), w)
	setJoint(J.LeftKnee, A(rad(-60 + 25 * sc), 0, 0), w)
end

local function poseDive(J, w)
	setJoint(J.RightShoulder, A(rad(178), 0, rad(-6)), w)
	setJoint(J.LeftShoulder, A(rad(178), 0, rad(6)), w)
	for _, n in { "RightElbow", "LeftElbow", "RightHip", "LeftHip", "RightKnee", "LeftKnee", "Waist" } do
		setJoint(J[n], CFrame.identity, w)
	end
	setJoint(J.RightAnkle, A(rad(-45), 0, 0), w)
	setJoint(J.LeftAnkle, A(rad(-45), 0, 0), w)
end

local function poseCannon(J, w)
	setJoint(J.RightHip, A(rad(115), 0, 0), w)
	setJoint(J.LeftHip, A(rad(115), 0, 0), w)
	setJoint(J.RightKnee, A(rad(-135), 0, 0), w)
	setJoint(J.LeftKnee, A(rad(-135), 0, 0), w)
	setJoint(J.RightShoulder, A(rad(75), 0, rad(-20)), w)
	setJoint(J.LeftShoulder, A(rad(75), 0, rad(20)), w)
	setJoint(J.RightElbow, A(rad(95), 0, 0), w)
	setJoint(J.LeftElbow, A(rad(95), 0, 0), w)
	setJoint(J.Waist, A(rad(-25), 0, 0), w)
	setJoint(J.Neck, A(rad(-20), 0, 0), w)
end

local function poseClimb(J, k, w)
	setJoint(J.RightShoulder, A(rad(150 - 135 * k), 0, rad(10)), w) -- reach onto the deck, then press down
	setJoint(J.LeftShoulder, A(rad(150 - 135 * k), 0, rad(-10)), w)
	setJoint(J.RightElbow, A(rad(40 * (1 - k)), 0, 0), w)
	setJoint(J.LeftElbow, A(rad(40 * (1 - k)), 0, 0), w)
	setJoint(J.RightHip, A(rad(85 * k * k), 0, 0), w) -- knee up onto the coping at the end
	setJoint(J.RightKnee, A(rad(-90 * k * k), 0, 0), w)
end

---------------------------------------------------------------------------------------------- local swimmer state
local S = { on = false, v = Vector3.zero, phase = 0, moving = false, climb = nil, pose = nil, height = 5.2 }
local B = { air = false, diving = false, cannon = false, level = 0, lastLand = -9, pending = nil, right = nil, board = nil }
local movers = {}

local function setPose(p)
	if S.pose ~= p then
		S.pose = p
		PoseRE:FireServer(p)
	end
end

local function clearMovers()
	for _, m in movers do
		if typeof(m) == "Instance" then
			m:Destroy()
		end
	end
	movers = {}
end

local function makeMovers(hrp, withVelocity)
	clearMovers()
	local att = Instance.new("Attachment")
	att.Name = "NC_SwimAtt"
	att.Parent = hrp
	local ao = Instance.new("AlignOrientation")
	ao.Name = "NC_SwimAlign"
	ao.Mode = Enum.OrientationAlignmentMode.OneAttachment
	ao.Attachment0 = att
	ao.Responsiveness = 12
	ao.MaxTorque = math.huge
	ao.CFrame = hrp.CFrame.Rotation
	ao.Parent = hrp
	movers.att, movers.ao = att, ao
	if withVelocity then
		local lv = Instance.new("LinearVelocity")
		lv.Name = "NC_SwimVel"
		lv.Attachment0 = att
		lv.VelocityConstraintMode = Enum.VelocityConstraintMode.Vector
		lv.RelativeTo = Enum.ActuatorRelativeTo.World
		lv.MaxForce = hrp.AssemblyMass * 4000
		lv.VectorVelocity = hrp.AssemblyLinearVelocity
		lv.Parent = hrp
		movers.lv = lv
	end
end

local function gravityForce(on)
	local hrp = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
	if not hrp then
		return
	end
	local vf = hrp:FindFirstChild("NC_RealG")
	if on then
		if not vf then
			local a = Instance.new("Attachment")
			a.Name = "NC_RealGAtt"
			a.Parent = hrp
			vf = Instance.new("VectorForce")
			vf.Name = "NC_RealG"
			vf.Attachment0 = a
			vf.RelativeTo = Enum.ActuatorRelativeTo.World
			vf.ApplyAtCenterOfMass = true
			vf.Parent = hrp
		end
		vf.Force = Vector3.new(0, hrp.AssemblyMass * (workspace.Gravity - G_REAL), 0) -- what's left falls at 37
		vf.Enabled = true
	elseif vf then
		vf.Enabled = false
	end
end

local function endAir()
	B.air, B.diving, B.cannon = false, false, false
	gravityForce(false)
end

local function startSwim(hrp, hum)
	if S.on then
		return
	end
	S.on, S.climb = true, nil
	S.v = hrp.AssemblyLinearVelocity
	endAir()
	hum:ChangeState(Enum.HumanoidStateType.Physics)
	local animator = hum:FindFirstChildOfClass("Animator")
	if animator then
		for _, t in animator:GetPlayingAnimationTracks() do
			t:Stop(0.25)
		end
	end
	makeMovers(hrp, true)
	setPose("swim")
end

local function stopSwim(hum, nextState)
	S.on, S.climb = false, nil
	clearMovers()
	setPose(nil)
	if hum then
		hum:ChangeState(nextState or Enum.HumanoidStateType.Freefall)
	end
end

local rayParams = RaycastParams.new()
rayParams.FilterType = Enum.RaycastFilterType.Exclude
local function refreshFilter()
	local list = {}
	for _, p in Players:GetPlayers() do
		if p.Character then
			table.insert(list, p.Character)
		end
	end
	for _, f in CollectionService:GetTagged("NC_Floaty") do
		table.insert(list, f)
	end
	rayParams.FilterDescendantsInstances = list
end

local function floorBelow(pos)
	local hit = workspace:Raycast(pos, Vector3.new(0, -40, 0), rayParams)
	return hit and hit.Position.Y or (pos.Y - 40)
end

-- Space at the surface facing the wall: is there a deck to climb onto? (the floaty counts: you can climb on it)
local climbParams = RaycastParams.new()
climbParams.FilterType = Enum.RaycastFilterType.Exclude
local function tryClimb(hrp, surf, fl)
	climbParams.FilterDescendantsInstances = { player.Character }
	local o = Vector3.new(hrp.Position.X, surf + 0.3, hrp.Position.Z)
	local hit = workspace:Raycast(o, fl * 2.8, climbParams)
	if not hit then
		return false
	end
	local top = workspace:Raycast(hit.Position + fl * 1.0 + Vector3.new(0, 4, 0), Vector3.new(0, -6, 0), climbParams)
	if not top or top.Position.Y < surf or top.Position.Y - surf > 2.0 then
		return false
	end
	S.climb = { t = 0, from = hrp.Position, wall = hit.Position, top = top.Position, fl = fl }
	return true
end

local function climbStep(dt, hrp, hum)
	local c = S.climb
	c.t += dt
	local standY = c.top.Y + hrp.Size.Y / 2 + hum.HipHeight
	local T1, T2 = 0.5, 0.35
	local wallXZ = Vector3.new(c.wall.X, 0, c.wall.Z)
	local target
	if c.t < T1 then -- pull up at the wall
		local a = c.t / T1
		local at = wallXZ - c.fl * 0.9
		target = Vector3.new(at.X, c.from.Y + (standY + 0.4 - c.from.Y) * a, at.Z)
	elseif c.t < T1 + T2 then -- swing onto the deck
		local a = (c.t - T1) / T2
		local at = wallXZ + c.fl * (-0.9 + 2.6 * a)
		target = Vector3.new(at.X, standY + 0.4, at.Z)
	else
		stopSwim(hum, Enum.HumanoidStateType.GettingUp)
		return
	end
	local v = (target - hrp.Position) * 14
	if v.Magnitude > 30 then
		v = v.Unit * 30
	end
	movers.lv.VectorVelocity = v
	movers.ao.CFrame = CFrame.lookAt(Vector3.zero, c.fl)
	S.climbK = math.clamp(c.t / (T1 + T2), 0, 1)
	setPose("climb")
end

local function swimStep(dt, hrp, hum)
	local w, surf = waterAt(hrp.Position)
	if not w or hrp.Position.Y > surf + 1.2 then
		stopSwim(hum)
		return
	end
	local cam = workspace.CurrentCamera
	local look = cam.CFrame.LookVector
	local fl = flat(look)
	fl = fl.Magnitude > 0.01 and fl.Unit or flat(hrp.CFrame.LookVector).Unit
	local md = hum.MoveDirection
	local fwdAmt = md:Dot(fl)
	local dir = look * fwdAmt + (md - fl * fwdAmt)
	local upKey = hum.Jump or UserInputService:IsKeyDown(Enum.KeyCode.Space)
	local downKey = UserInputService:IsKeyDown(Enum.KeyCode.C) or UserInputService:IsKeyDown(Enum.KeyCode.LeftControl)
		or UserInputService:IsGamepadButtonDown(Enum.UserInputType.Gamepad1, Enum.KeyCode.ButtonB)
	local moving = dir.Magnitude > 0.1
	local floatY = surf - (moving and 0.45 or 0.95) -- prone: back at the surface; upright: head out
	local atSurface = hrp.Position.Y > floatY - 0.7
	if atSurface and dir.Y > 0 then
		dir = flat(dir)
	end
	if upKey and atSurface and tryClimb(hrp, surf, fl) then
		return
	end
	-- stand up in shallow water when you stop (or on the steps)
	local depth = surf - floorBelow(hrp.Position)
	if (depth < 0.6 * S.height) or (not moving and not downKey and depth < 0.82 * S.height and S.v.Y > -1) then
		stopSwim(hum)
		return
	end
	local speed = atSurface and SWIM_SPEED or UNDER_SPEED
	local desired = moving and dir.Unit * math.min(dir.Magnitude, 1) * speed or Vector3.zero
	if downKey then
		desired += Vector3.new(0, -6, 0)
	elseif upKey and not atSurface then
		desired += Vector3.new(0, 6, 0)
	end
	if not downKey and not (moving and dir.Y < -0.25) then -- buoyancy: back to floating level
		desired += Vector3.new(0, math.clamp((floatY - hrp.Position.Y) * 1.8, -3, 3.5), 0)
	end
	local diff = desired - S.v
	local k = 2.4 + 0.11 * diff.Magnitude -- quadratic water drag: bleeds a dive fast, gentle at swimming speed
	S.v += diff * (1 - math.exp(-k * dt))
	movers.lv.VectorVelocity = S.v
	local spd = S.v.Magnitude
	S.moving = moving and spd > 1.5
	S.atSurface = atSurface
	if S.moving then
		local d = atSurface and flat(S.v) or S.v
		d = d.Magnitude > 0.5 and d.Unit or fl
		local back = Vector3.yAxis - d * d.Y
		if back.Magnitude < 0.2 then
			back = -fl
		end
		back = back.Unit
		local roll = atSurface and math.sin(S.phase * TAU) * rad(28) or 0 -- freestyle body roll
		movers.ao.CFrame = CFrame.fromMatrix(Vector3.zero, d:Cross(back), d, back) * A(0, roll, 0)
	else
		movers.ao.CFrame = CFrame.lookAt(Vector3.zero, fl)
	end
end

---------------------------------------------------------------------------------------------- springboards
local boards = {}
local W0, ZETA = TAU * 2.0, 0.12 -- a loaded 1 m board rings at about 2 Hz
local function boardState(m)
	local st = boards[m]
	if st then
		return st
	end
	local pivot = m.PrimaryPart or m:FindFirstChild("Pivot")
	if not pivot then
		return nil
	end
	st = { pivot = pivot, rest = {}, theta = 0, omega = 0, L = m:GetAttribute("Length") or 9.2, W = m:GetAttribute("Width") or 2.0, on = {}, vy = {} }
	for _, p in m:GetDescendants() do
		if p:IsA("BasePart") and p ~= pivot then
			st.rest[p] = pivot.CFrame:ToObjectSpace(p.CFrame)
		end
	end
	boards[m] = st
	return st
end

-- where a character stands on a board: along (0 at the anchor .. L at the tip), or nil
local function onBoard(st, hrp, hum)
	local lp = st.pivot.CFrame:PointToObjectSpace(hrp.Position)
	local s = -lp.Z
	local feet = lp.Y - (hrp.Size.Y / 2 + hum.HipHeight)
	if s > -0.3 and s < st.L + 0.4 and math.abs(lp.X) < st.W / 2 + 0.5 and math.abs(feet - 0.25) < 0.8 then
		return s
	end
	return nil
end

local function overBoard(st, hrp)
	local lp = st.pivot.CFrame:PointToObjectSpace(hrp.Position)
	return -lp.Z < st.L + 0.6 and math.abs(lp.X) < st.W / 2 + 1.2
end

local function updateBoards(dt)
	for _, m in CollectionService:GetTagged("NC_DivingBoard") do
		if m:IsDescendantOf(workspace) then
			boardState(m)
		end
	end
	for m, st in boards do
		if not m:IsDescendantOf(workspace) then
			boards[m] = nil
			continue
		end
		local static = 0
		for _, p in Players:GetPlayers() do
			local hrp, hum = bodyOf(p.Character)
			if hrp then
				local s = onBoard(st, hrp, hum)
				if s then
					static += rad(3.2) * (s / st.L)
					local lastVy = st.vy[p] or 0
					if not st.on[p] and lastVy < -8 then -- landed: the board takes the hit
						st.omega += 0.026 * -lastVy * (s / st.L)
						sound(st.pivot, SND_BOARD, math.clamp(-lastVy / 30, 0.2, 0.8), 0.85, 80)
						if p == player then
							B.lastLand = os.clock()
						end
					end
				end
				st.on[p] = s
				st.vy[p] = hrp.AssemblyLinearVelocity.Y
			end
		end
		local acc = -W0 * W0 * (st.theta - static) - 2 * ZETA * W0 * st.omega
		st.omega += acc * dt
		st.theta = math.clamp(st.theta + st.omega * dt, -rad(4), rad(9))
		local base = st.pivot.CFrame * A(-st.theta, 0, 0) -- tip down for positive theta
		for p, off in st.rest do
			p.CFrame = base * off
		end
	end
end

local function boardJump(hrp, hum)
	for _, st in boards do
		local s = st.on[player]
		if s and s > st.L * 0.45 then
			local since = os.clock() - B.lastLand
			if since < 0.22 then
				B.level = math.min(#BOUNCE_VY, B.level + 1) -- rode the recoil
			elseif since > 1.0 then
				B.level = 1
			else
				B.level = math.max(1, B.level)
			end
			local fwd = flat(st.pivot.CFrame.LookVector).Unit
			local md = hum.MoveDirection
			local along = md:Dot(fwd)
			local horiz = fwd * (along > 0.3 and 6 or 0.6) + (md - fwd * along) * 2
			local vy = BOUNCE_VY[B.level] * (0.85 + 0.15 * s / st.L)
			B.pending = horiz + Vector3.new(0, vy, 0)
			B.air, B.diving, B.cannon, B.board = true, false, false, st
			B.right = fwd:Cross(Vector3.yAxis).Unit
			st.omega -= 0.03 * vy -- the board snaps up as it lets go
			gravityForce(true)
			return true
		end
	end
	return false
end

---------------------------------------------------------------------------------------------- character hookup
local function onCharacter(char)
	S.on, S.climb, S.pose = false, nil, nil
	B.air, B.diving, B.cannon, B.level = false, false, false, 0
	movers = {}
	local hum = char:WaitForChild("Humanoid", 10)
	if not hum then
		return
	end
	hum.StateChanged:Connect(function(_, new)
		local hrp = char:FindFirstChild("HumanoidRootPart")
		if not hrp then
			return
		end
		if new == Enum.HumanoidStateType.Jumping then
			if not boardJump(hrp, hum) and waterAt(hrp.Position) then
				-- an ordinary jump from the deck: normal jump physics, but C still tucks a cannonball
				B.air, B.diving, B.cannon, B.board = true, false, false, nil
				B.right = flat(workspace.CurrentCamera.CFrame.LookVector):Cross(Vector3.yAxis)
				B.right = B.right.Magnitude > 0.01 and B.right.Unit or Vector3.xAxis
			end
		elseif B.air and not B.diving and (new == Enum.HumanoidStateType.Landed or new == Enum.HumanoidStateType.Running) then
			endAir()
			setPose(nil)
		end
	end)
end
player.CharacterAdded:Connect(onCharacter)
if player.Character then
	task.spawn(onCharacter, player.Character)
end

UserInputService.InputBegan:Connect(function(input, gp)
	if gp then
		return
	end
	if (input.KeyCode == Enum.KeyCode.C or input.KeyCode == Enum.KeyCode.ButtonB) and B.air and not S.on then
		B.cannon = true
		setPose("cannon")
	end
end)

---------------------------------------------------------------------------------------------- the step
local poseState = setmetatable({}, { __mode = "k" }) -- char -> { phase, blend, last }
local track = setmetatable({}, { __mode = "k" }) -- char -> last HRP height (splash detection)
local frame = 0
local wade = { base = nil, set = nil }

RunService.Stepped:Connect(function(_, dt)
	frame += 1
	if frame % 30 == 1 then
		refreshFilter()
	end
	updateBoards(dt)
	local char = player.Character
	local hrp, hum, head = bodyOf(char)
	if hrp and hum.Health > 0 then
		if B.pending then
			hrp.AssemblyLinearVelocity = B.pending
			B.pending = nil
		end
		if not S.on and hrp.CFrame.UpVector.Y > 0.95 then
			S.height = (hrp.Size.Y / 2 + hum.HipHeight) + (head.Position.Y + head.Size.Y / 2 - hrp.Position.Y)
		end
		local w, surf = waterAt(hrp.Position)
		if S.on then
			if S.climb then
				climbStep(dt, hrp, hum)
			else
				swimStep(dt, hrp, hum)
			end
		else
			-- airborne over the pool: dive / cannonball attitude, then into the water
			if B.air then
				local vel = hrp.AssemblyLinearVelocity
				if w and not B.diving and vel.Y < -1 and B.board and not overBoard(B.board, hrp) then
					B.diving, B.diveStart = true, os.clock()
					hum:ChangeState(Enum.HumanoidStateType.Physics)
					makeMovers(hrp, false)
					setPose(B.cannon and "cannon" or "dive")
				end
				if B.diving and movers.ao then
					local right = B.right or Vector3.xAxis
					if B.cannon then
						local f = Vector3.yAxis:Cross(right) -- forward, off the end of the board
						movers.ao.CFrame = CFrame.lookAt(Vector3.zero, f) * A(rad(10), 0, 0)
					else
						-- head leads along the arc: upright on the way up, flat at the top, head-first at entry
						local u = vel.Magnitude > 1 and vel.Unit or Vector3.yAxis
						u = u - right * u:Dot(right)
						u = u.Magnitude > 0.05 and u.Unit or Vector3.yAxis
						movers.ao.CFrame = CFrame.fromMatrix(Vector3.zero, right, u, right:Cross(u))
					end
				end
				-- came down on the deck instead of the water: get back on your feet
				if B.diving and (not w or os.clock() - (B.diveStart or 0) > 3 or (vel.Magnitude < 2 and floorBelow(hrp.Position) > hrp.Position.Y - 3.5)) then
					clearMovers()
					endAir()
					setPose(nil)
					hum:ChangeState(Enum.HumanoidStateType.GettingUp)
				elseif os.clock() - B.lastLand > 6 and not w and not B.diving then
					endAir()
				end
			end
			-- into the water: swim when deeper than your chest (or arriving from the air)
			if w and hrp.Position.Y < surf then
				local feet = hrp.Position.Y - hrp.Size.Y / 2 - hum.HipHeight
				local sub = surf - feet
				local st = hum:GetState()
				local airborne = B.diving or st == Enum.HumanoidStateType.Freefall or st == Enum.HumanoidStateType.Jumping
				if B.diving then
					sub = surf - (hrp.Position.Y - 2) -- head-first: count from the hands
				end
				if (airborne and sub > 0.55 * S.height) or (sub > 0.62 * S.height and surf - floorBelow(hrp.Position) > 0.85 * S.height) then
					startSwim(hrp, hum)
				end
			end
			-- wading: chest-deep water drags at your legs
			local feet = hrp.Position.Y - hrp.Size.Y / 2 - hum.HipHeight
			local d = (w and not S.on) and (surf - feet) or 0
			if d > 0.4 and hum:GetAttribute("NC_Movement") then
				-- the movement system owns WalkSpeed: slow it through a speed factor instead
				hum:SetAttribute("SpeedFactor_Wade", 1 - 0.5 * math.clamp(d / 4, 0, 1))
				wade.attr = true
			elseif d > 0.4 then
				local mult = 1 - 0.5 * math.clamp(d / 4, 0, 1)
				if wade.set == nil or math.abs(hum.WalkSpeed - wade.set) > 0.01 then
					wade.base = hum.WalkSpeed
				end
				wade.set = wade.base * mult
				hum.WalkSpeed = wade.set
			elseif wade.attr then
				hum:SetAttribute("SpeedFactor_Wade", nil)
				wade.attr = nil
			elseif wade.set then
				if math.abs(hum.WalkSpeed - wade.set) < 0.01 then
					hum.WalkSpeed = wade.base
				end
				wade.set, wade.base = nil, nil
			end
		end
	end

	-- poses + splashes for every character (yours from the controller, others from their SwimPose)
	local camPos = workspace.CurrentCamera.CFrame.Position
	for _, p in Players:GetPlayers() do
		local c = p.Character
		local phrp, phum = bodyOf(c)
		if not phrp then
			continue
		end
		local isMe = p == player
		local pose = c:GetAttribute("SwimPose")
		local moving = flat(phrp.AssemblyLinearVelocity).Magnitude > 1.5
		local ph
		if isMe then
			pose = S.on and (S.climb and "climb" or "swim") or ((B.diving or (B.air and B.cannon)) and (B.cannon and "cannon" or "dive")) or nil
			moving = S.moving
		end
		local ps = poseState[c]
		if not ps then
			ps = { phase = 0, blend = 0 }
			poseState[c] = ps
		end
		if pose then
			ps.blend = math.min(1, ps.blend + dt * 6)
			local spd = phrp.AssemblyLinearVelocity.Magnitude
			local before = ps.phase
			ps.phase += dt * ((pose == "swim" and moving) and (0.55 + spd * 0.035) or 0.9)
			if isMe then
				S.phase = ps.phase
			end
			local J = jointsOf(c)
			if pose == "swim" then
				if moving then
					poseFreestyle(J, ps.phase, ps.blend)
					-- a hand enters the water twice per stroke cycle
					if math.floor(before * 2) ~= math.floor(ps.phase * 2) and (phrp.Position - camPos).Magnitude < 70 then
						local hand = c:FindFirstChild(math.floor(ps.phase * 2) % 2 == 0 and "RightHand" or "LeftHand")
						local _, surf = waterAt(phrp.Position)
						if hand and surf and math.abs(hand.Position.Y - surf) < 1.5 then
							strokeSplash(Vector3.new(hand.Position.X, surf, hand.Position.Z))
						end
					end
				else
					poseTread(J, ps.phase, ps.blend)
				end
			elseif pose == "dive" then
				poseDive(J, ps.blend)
			elseif pose == "cannon" then
				poseCannon(J, ps.blend)
			elseif pose == "climb" then
				poseClimb(J, isMe and (S.climbK or 0) or math.clamp(ps.phase % 1, 0, 1), ps.blend)
			end
		else
			ps.blend = 0
		end
		-- splash when anyone hits the water from above
		local w, surf = waterAt(phrp.Position, 1)
		local y = phrp.Position.Y
		local last = track[c]
		if w and last and last > surf + 1.5 and y <= surf + 1.5 then
			local vy = phrp.AssemblyLinearVelocity.Y
			if vy < -7 then -- a clean head-first entry throws far less water than feet or a cannonball
				splash(Vector3.new(phrp.Position.X, surf, phrp.Position.Z), pose == "dive" and -vy * 0.45 or -vy, pose == "cannon")
			end
		end
		track[c] = w and y or nil
	end
end)

---------------------------------------------------------------------------------------------- underwater view
local tint = Instance.new("ColorCorrectionEffect")
tint.Name = "NC_Underwater"
tint.TintColor = Color3.fromRGB(150, 214, 255)
tint.Saturation = 0.1
tint.Contrast = 0.05
tint.Brightness = -0.04
tint.Enabled = false
tint.Parent = Lighting
local blur = Instance.new("BlurEffect")
blur.Name = "NC_UnderwaterBlur"
blur.Size = 6
blur.Enabled = false
blur.Parent = Lighting
local reverbWas = nil
RunService.RenderStepped:Connect(function()
	local cp = workspace.CurrentCamera.CFrame.Position
	local w, surf = waterAt(cp)
	local under = w ~= nil and cp.Y < surf - 0.05
	tint.Enabled, blur.Enabled = under, under
	if under and reverbWas == nil then
		reverbWas = SoundService.AmbientReverb
		SoundService.AmbientReverb = Enum.ReverbType.UnderWater
	elseif not under and reverbWas ~= nil then
		SoundService.AmbientReverb = reverbWas
		reverbWas = nil
	end
end)

---------------------------------------------------------------------------------------------- unicorn hoops
HoopRE.OnClientEvent:Connect(function(floaty, who, count)
	local body = typeof(floaty) == "Instance" and floaty.PrimaryPart
	if not body then
		return
	end
	local a = fxAnchor(body.Position + Vector3.new(0, 1.2, 0))
	emitter(a, {
		Texture = TEX_SPARK, Count = 40, Speed = NumberRange.new(6, 14), SpreadAngle = Vector2.new(60, 60),
		Acceleration = Vector3.new(0, -12, 0), Lifetime = NumberRange.new(0.8, 1.4), Size = NumberSequence.new(0.7, 0.1),
		LightEmission = 0.6, Transparency = NumberSequence.new(0, 1), Rotation = NumberRange.new(0, 360),
		Color = ColorSequence.new({
			ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 134, 190)), ColorSequenceKeypoint.new(0.25, Color3.fromRGB(255, 230, 110)),
			ColorSequenceKeypoint.new(0.5, Color3.fromRGB(134, 230, 180)), ColorSequenceKeypoint.new(0.75, Color3.fromRGB(124, 190, 255)),
			ColorSequenceKeypoint.new(1, Color3.fromRGB(184, 150, 245)),
		}),
	})
	sound(a, SND_BOARD, 0.7, 2.2, 90) -- a squeaky boing
	local bb = Instance.new("BillboardGui")
	bb.Size = UDim2.fromOffset(260, 60)
	bb.StudsOffsetWorldSpace = Vector3.new(0, 3, 0)
	bb.AlwaysOnTop = true
	bb.MaxDistance = 120
	local t = Instance.new("TextLabel")
	t.Size = UDim2.fromScale(1, 1)
	t.BackgroundTransparency = 1
	t.Font = Enum.Font.GothamBlack
	t.TextScaled = true
	t.RichText = true
	t.TextColor3 = Color3.fromRGB(255, 190, 230)
	t.TextStrokeTransparency = 0.3
	t.Text = string.format("Unicorn hoop! x%d\n<font size=\"14\">%s</font>", count or 1, typeof(who) == "Instance" and who.DisplayName or "")
	t.Parent = bb
	bb.Parent = a
	TweenService:Create(bb, TweenInfo.new(1.6, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { StudsOffsetWorldSpace = Vector3.new(0, 6, 0) }):Play()
	TweenService:Create(t, TweenInfo.new(0.6, Enum.EasingStyle.Quad, Enum.EasingDirection.In, 0, false, 1.0), { TextTransparency = 1, TextStrokeTransparency = 1 }):Play()
end)
