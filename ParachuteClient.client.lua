--!nonstrict
-- ParachuteClient: skydiving and the parachute, the way the big battle-royale shooters do it.
--   * Own a parachute (buy one at a parachute kiosk) and step off anything tall: once you're falling with
--     40+ studs of air under you, you go into a skydive automatically.
--   * Freefall: the camera steers. Hold W looking at the horizon to track forward fast; look straight down and
--     hold W to dive head-first (much faster fall, the wind screams, the view stretches); let go to fall belly-
--     down; S slows you and A/D slide sideways. Altitude and speed on screen.
--   * SPACE opens the canopy (at least 10 studs up): a hard opening jolt, the canopy cracks open over you. Under
--     canopy the chute follows where you look; W pushes it forward faster and steeper, S brakes and floats, A/D
--     bank into tighter turns. C (or the Cut button) cuts it away and you're back in freefall, and you can open
--     again: cut and redeploy as often as you like. Leave it too long and it opens on its own near the ground.
--   * Land soft under canopy (it folds away), or splash into a pool (the swim script takes over).
--   * Everyone sees everyone: the pack on your back, the skydive poses, the canopy and the cutaway.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local CAS = game:GetService("ContextActionService")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")
local RS = game:GetService("ReplicatedStorage")

local player = Players.LocalPlayer
local StateRE = RS:WaitForChild("Remotes"):WaitForChild("ParachuteState")

-- tuning, studs/s (about 3.8 studs to a metre)
local FF = { bellyFall = 58, bellyDrift = 7, trackFall = 46, trackFwd = 50, diveFall = 128, diveFwd = 26, backFall = 55, backFwd = -8, strafe = 18, respH = 1.5, respV = 2.0 }
local CN = { fall = 13, fwd = 32, diveFall = 23, diveFwd = 47, brakeFall = 8.5, brakeFwd = 15, turn = math.rad(85), bank = math.rad(75), respH = 2.0, respV = 2.4, openTime = 0.8 }
local START_AGL, MIN_DEPLOY = 40, 10
local SND_WIND = "rbxasset://sounds/action_falling.ogg"
local SND_POP = "rbxasset://sounds/action_jump_land.mp3"
local rad = math.rad

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

---------------------------------------------------------------------------------------------- the world below
local rayParams = RaycastParams.new()
rayParams.FilterType = Enum.RaycastFilterType.Exclude
local function refreshFilter()
	local list = { workspace.CurrentCamera }
	for _, p in Players:GetPlayers() do
		if p.Character then
			table.insert(list, p.Character)
		end
	end
	local f = workspace:FindFirstChild("NC_LocalChutes")
	if f then
		table.insert(list, f)
	end
	rayParams.FilterDescendantsInstances = list
end

local function feetAGL(hrp, hum)
	local feet = hrp.Position.Y - hrp.Size.Y / 2 - hum.HipHeight
	local hit = workspace:Raycast(hrp.Position, Vector3.new(0, -3000, 0), rayParams)
	if not hit then
		return 3000
	end
	return feet - hit.Position.Y
end

local function inWater(pos)
	for _, w in CollectionService:GetTagged("NC_Water") do
		if w:IsA("BasePart") and w:IsDescendantOf(workspace) then
			local lp = w.CFrame:PointToObjectSpace(pos)
			local h = w.Size / 2
			if math.abs(lp.X) <= h.X and math.abs(lp.Z) <= h.Z and lp.Y <= h.Y and lp.Y >= -h.Y then
				return true
			end
		end
	end
	return false
end

---------------------------------------------------------------------------------------------- joints and poses
local JOINTS = { "RightShoulder", "RightElbow", "LeftShoulder", "LeftElbow", "RightHip", "RightKnee", "LeftHip", "LeftKnee", "Neck", "Waist" }
local JSET = {}
for _, n in JOINTS do
	JSET[n] = true
end
local jointCache = setmetatable({}, { __mode = "k" })
local function jointsOf(char)
	local e = jointCache[char]
	if e and (e.n >= 8 or os.clock() - e.t < 2) then
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
local function lerpA(a, b, t)
	return a + (b - a) * t
end

-- belly-to-earth arch blending into a head-down dive (arms swept back, legs together)
local function poseFreefall(J, dive, w)
	local sh = lerpA(20, -20, dive)
	setJoint(J.RightShoulder, A(rad(sh), 0, rad(lerpA(82, 16, dive))), w)
	setJoint(J.LeftShoulder, A(rad(sh), 0, rad(-lerpA(82, 16, dive))), w)
	setJoint(J.RightElbow, A(rad(lerpA(70, 6, dive)), 0, 0), w)
	setJoint(J.LeftElbow, A(rad(lerpA(70, 6, dive)), 0, 0), w)
	setJoint(J.RightHip, A(rad(lerpA(-22, -4, dive)), 0, rad(lerpA(16, 3, dive))), w)
	setJoint(J.LeftHip, A(rad(lerpA(-22, -4, dive)), 0, rad(-lerpA(16, 3, dive))), w)
	setJoint(J.RightKnee, A(rad(lerpA(-62, -6, dive)), 0, 0), w)
	setJoint(J.LeftKnee, A(rad(lerpA(-62, -6, dive)), 0, 0), w)
	setJoint(J.Neck, A(rad(lerpA(30, 10, dive)), 0, 0), w) -- head up, looking where you're going
end

-- hanging in the harness, hands up on the toggles; braking pulls them down, a turn pulls one side
local function poseCanopy(J, brake, turn, w)
	local r = lerpA(158, 115, math.clamp(brake + math.max(0, turn), 0, 1))
	local l = lerpA(158, 115, math.clamp(brake + math.max(0, -turn), 0, 1))
	setJoint(J.RightShoulder, A(rad(r), 0, rad(-14)), w)
	setJoint(J.LeftShoulder, A(rad(l), 0, rad(14)), w)
	setJoint(J.RightElbow, A(rad(40), 0, 0), w)
	setJoint(J.LeftElbow, A(rad(40), 0, 0), w)
	setJoint(J.RightHip, A(rad(18), 0, rad(4)), w)
	setJoint(J.LeftHip, A(rad(14), 0, rad(-4)), w)
	setJoint(J.RightKnee, A(rad(-22), 0, 0), w)
	setJoint(J.LeftKnee, A(rad(-26), 0, 0), w)
end

---------------------------------------------------------------------------------------------- visuals (canopy, pack)
local localFolder = workspace:FindFirstChild("NC_LocalChutes") or Instance.new("Folder")
localFolder.Name = "NC_LocalChutes"
localFolder.Parent = workspace

local function ghost(p)
	p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.Massless = false, false, false, false, true
	return p
end

local PINK, BLACK, TEAL = Color3.fromRGB(255, 56, 158), Color3.fromRGB(18, 18, 22), Color3.fromRGB(26, 216, 216)

local function newCanopy()
	local assets = RS:FindFirstChild("ParachuteAssets")
	if assets and assets:FindFirstChild("Canopy") then
		return assets.Canopy:Clone()
	end
	-- built from parts until the Blender canopy is uploaded: 9 arched ram-air cells with rounded noses,
	-- stabilisers, two rows of lines per rib down to four risers
	local m = Instance.new("Model")
	m.Name = "Canopy"
	local root = ghost(Instance.new("Part"))
	root.Name = "Harness"
	root.Size = Vector3.one * 0.2
	root.Transparency = 1
	root.Parent = m
	m.PrimaryPart = root
	local SPAN, CHORD, H0, DROP, N = 20, 7.6, 15, 2.6, 9
	local function arc(x)
		return H0 - DROP * (x / (SPAN / 2)) ^ 2
	end
	local function add(p)
		ghost(p)
		p.TopSurface, p.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
		p.Parent = m
		local w = Instance.new("WeldConstraint")
		w.Part0, w.Part1 = root, p
		w.Parent = p
		return p
	end
	for i = 0, N - 1 do
		local x = -SPAN / 2 + SPAN * (i + 0.5) / N
		local roll = math.atan(-2 * DROP * x / (SPAN / 2) ^ 2)
		local cf = root.CFrame * CFrame.new(x, arc(x), 0) * CFrame.Angles(0, 0, roll)
		local col = i == 4 and TEAL or (i % 2 == 0 and PINK or BLACK)
		local cell = Instance.new("Part")
		cell.Size = Vector3.new(SPAN / N + 0.04, 1.0, CHORD - 0.6)
		cell.CFrame = cf * CFrame.new(0, 0, 0.3)
		cell.Color = col
		cell.Material = Enum.Material.Fabric
		add(cell)
		local nose = Instance.new("Part")
		nose.Shape = Enum.PartType.Cylinder
		nose.Size = Vector3.new(SPAN / N + 0.04, 1.2, 1.2)
		nose.CFrame = cf * CFrame.new(0, 0.05, -CHORD / 2 + 0.6)
		nose.Color = col
		nose.Material = Enum.Material.Fabric
		add(nose)
	end
	for s = -1, 1, 2 do
		local x = s * SPAN / 2
		local stab = Instance.new("WedgePart")
		stab.Size = Vector3.new(0.12, 3.0, CHORD * 0.7)
		stab.CFrame = root.CFrame * CFrame.new(x, arc(x) - 1.9, 0.2) * CFrame.Angles(math.pi, 0, 0)
		stab.Color = BLACK
		stab.Material = Enum.Material.Fabric
		add(stab)
	end
	local risers = { [-1] = Vector3.new(-0.9, 3.2, 0), [1] = Vector3.new(0.9, 3.2, 0) }
	for r = 0, N do
		local x = -SPAN / 2 + SPAN * r / N
		local side = x < 0 and -1 or 1
		for _, zf in { -CHORD * 0.3, CHORD * 0.25 } do
			local a = Vector3.new(x, arc(x) - 0.55, zf)
			local b = risers[side] + Vector3.new(0, 0, zf * 0.05)
			local line = Instance.new("Part")
			line.Size = Vector3.new(0.06, 0.06, (a - b).Magnitude)
			line.CFrame = root.CFrame * CFrame.lookAt((a + b) / 2, b)
			line.Color = Color3.fromRGB(225, 225, 218)
			line.Material = Enum.Material.SmoothPlastic
			add(line)
		end
	end
	for s = -1, 1, 2 do
		local riser = Instance.new("Part")
		riser.Size = Vector3.new(0.28, 3.2, 0.08)
		riser.CFrame = root.CFrame * CFrame.new(s * 0.82, 1.65, 0)
		riser.Color = BLACK
		add(riser)
	end
	return m
end

local function newPack()
	local assets = RS:FindFirstChild("ParachuteAssets")
	if assets and assets:FindFirstChild("Pack") then
		return assets.Pack:Clone()
	end
	local m = Instance.new("Model")
	m.Name = "Pack"
	local body = ghost(Instance.new("Part"))
	body.Name = "Body"
	body.Size = Vector3.new(1.6, 2.0, 0.7)
	body.Color = Color3.fromRGB(36, 38, 44)
	body.Material = Enum.Material.Fabric
	body.Parent = m
	m.PrimaryPart = body
	local seam = ghost(Instance.new("Part"))
	seam.Size = Vector3.new(1.62, 0.1, 0.3)
	seam.CFrame = body.CFrame * CFrame.new(0, 1.0, 0)
	seam.Color = PINK
	seam.Material = Enum.Material.Neon
	seam.Parent = m
	local handle = ghost(Instance.new("Part"))
	handle.Size = Vector3.new(0.3, 0.3, 0.2)
	handle.CFrame = body.CFrame * CFrame.new(0.45, -0.85, 0.42)
	handle.Color = Color3.fromRGB(240, 190, 30)
	handle.Parent = m
	for _, p in { seam, handle } do
		local w = Instance.new("WeldConstraint")
		w.Part0, w.Part1 = body, p
		w.Parent = p
	end
	return m
end

local vis = {} -- character -> { pack = model, canopy = model, weld = Weld, t0 = open time, state = last state }

local function playPop(char)
	local hrp = char:FindFirstChild("HumanoidRootPart")
	if not hrp then
		return
	end
	local s = Instance.new("Sound")
	s.SoundId = SND_POP
	s.PlaybackSpeed = 0.45
	s.Volume = 1.2
	s.RollOffMaxDistance = 160
	s.Parent = hrp
	s:Play()
	Debris:AddItem(s, 2)
end

local function releaseCanopy(v, how)
	local m = v.canopy
	if not m then
		return
	end
	v.canopy, v.weld = nil, nil
	if how == "cut" then
		-- cut away: it flies off up and back, tumbling, then it's gone
		for _, d in m:GetDescendants() do
			if d:IsA("Weld") and d.Name == "ChuteWeld" then
				d:Destroy()
			end
		end
		local root = m.PrimaryPart
		if root then
			for _, p in m:GetDescendants() do
				if p:IsA("BasePart") then
					p.Massless = false
				end
			end
			root.AssemblyLinearVelocity = Vector3.new(0, 25, 0) + root.CFrame.LookVector * -20
			root.AssemblyAngularVelocity = Vector3.new(1.5, 0.6, 0.8)
		end
		Debris:AddItem(m, 4)
	else
		-- landed: the canopy folds down and fades
		local t0 = os.clock()
		local base = m:GetScale()
		local conn
		conn = RunService.RenderStepped:Connect(function()
			local t = (os.clock() - t0) / 0.7
			if t >= 1 or not m.Parent then
				conn:Disconnect()
				m:Destroy()
				return
			end
			pcall(function()
				m:ScaleTo(math.max(0.05, base * (1 - t)))
			end)
		end)
	end
end

local function attach(char, model, partName, offset)
	local p = char:FindFirstChild(partName) or char:FindFirstChild("HumanoidRootPart")
	if not (p and model.PrimaryPart) then
		model:Destroy()
		return nil
	end
	model:PivotTo(p.CFrame * offset)
	local w = Instance.new("Weld")
	w.Name = "ChuteWeld"
	w.Part0, w.Part1 = p, model.PrimaryPart
	w.C0 = offset
	w.Parent = model.PrimaryPart
	model.Parent = localFolder
	return w
end

---------------------------------------------------------------------------------------------- local controller
local S = { mode = nil, v = Vector3.zero, fwd = Vector3.new(0, 0, -1), deployT = 0, cutT = -9, dive = 0, brake = 0, turn = 0, fov = nil, shake = 0 }
local movers = {}

local function setState(st)
	S.mode = st
	StateRE:FireServer(st)
end

local function clearMovers()
	for _, m in movers do
		if typeof(m) == "Instance" then
			m:Destroy()
		end
	end
	movers = {}
end

local function makeMovers(hrp)
	clearMovers()
	local att = Instance.new("Attachment")
	att.Name = "NC_ChuteAtt"
	att.Parent = hrp
	local lv = Instance.new("LinearVelocity")
	lv.Attachment0 = att
	lv.VelocityConstraintMode = Enum.VelocityConstraintMode.Vector
	lv.RelativeTo = Enum.ActuatorRelativeTo.World
	lv.MaxForce = hrp.AssemblyMass * 4000
	lv.VectorVelocity = hrp.AssemblyLinearVelocity
	lv.Parent = hrp
	local ao = Instance.new("AlignOrientation")
	ao.Mode = Enum.OrientationAlignmentMode.OneAttachment
	ao.Attachment0 = att
	ao.Responsiveness = 10
	ao.MaxTorque = math.huge
	ao.CFrame = hrp.CFrame.Rotation
	ao.Parent = hrp
	movers = { att = att, lv = lv, ao = ao }
end

-- HUD: altitude, speed, the keys
local gui = Instance.new("ScreenGui")
gui.Name = "SkydiveHUD"
gui.ResetOnSpawn = false
gui.Enabled = false
gui.Parent = player:WaitForChild("PlayerGui")
local readout = Instance.new("TextLabel")
readout.AnchorPoint = Vector2.new(0.5, 1)
readout.Position = UDim2.new(0.5, 0, 1, -150)
readout.Size = UDim2.fromOffset(420, 60)
readout.BackgroundTransparency = 1
readout.Font = Enum.Font.GothamBlack
readout.TextColor3 = Color3.fromRGB(255, 255, 255)
readout.TextStrokeTransparency = 0.4
readout.TextSize = 30
readout.RichText = true
readout.Parent = gui
local hint = Instance.new("TextLabel")
hint.AnchorPoint = Vector2.new(0.5, 1)
hint.Position = UDim2.new(0.5, 0, 1, -118)
hint.Size = UDim2.fromOffset(520, 26)
hint.BackgroundTransparency = 1
hint.Font = Enum.Font.GothamBold
hint.TextColor3 = Color3.fromRGB(230, 230, 230)
hint.TextStrokeTransparency = 0.5
hint.TextSize = 16
hint.Parent = gui

local wind = Instance.new("Sound")
wind.Name = "SkydiveWind"
wind.SoundId = SND_WIND
wind.Looped = true
wind.Volume = 0
wind.Parent = workspace.CurrentCamera

local function deploy()
	local char = player.Character
	local hrp, hum = bodyOf(char)
	if S.mode ~= "freefall" or not hrp then
		return
	end
	if feetAGL(hrp, hum) < MIN_DEPLOY or os.clock() - S.cutT < 0.6 then
		return
	end
	S.deployT = os.clock()
	S.shake = 1.0
	setState("canopy")
end

local function cut()
	if S.mode ~= "canopy" then
		return
	end
	S.cutT = os.clock()
	setState("freefall")
	local v = vis[player.Character]
	if v then
		releaseCanopy(v, "cut")
		v.state = "freefall"
	end
end

local function onDeployAction(_, st)
	if st == Enum.UserInputState.Begin then
		deploy()
	end
	return Enum.ContextActionResult.Sink
end
local function onCutAction(_, st)
	if st == Enum.UserInputState.Begin then
		cut()
	end
	return Enum.ContextActionResult.Sink
end

local function bindKeys(on)
	if on then
		CAS:BindActionAtPriority("NC_ChuteDeploy", onDeployAction, true, 3000, Enum.KeyCode.Space, Enum.KeyCode.ButtonA)
		CAS:SetTitle("NC_ChuteDeploy", "Open")
		CAS:BindActionAtPriority("NC_ChuteCut", onCutAction, true, 3000, Enum.KeyCode.C, Enum.KeyCode.LeftControl, Enum.KeyCode.ButtonB)
		CAS:SetTitle("NC_ChuteCut", "Cut")
	else
		CAS:UnbindAction("NC_ChuteDeploy")
		CAS:UnbindAction("NC_ChuteCut")
	end
end

local function startFreefall(hrp, hum)
	S.v = hrp.AssemblyLinearVelocity
	local fl = flat(workspace.CurrentCamera.CFrame.LookVector)
	S.fwd = fl.Magnitude > 0.01 and fl.Unit or flat(hrp.CFrame.LookVector).Unit
	S.dive, S.brake, S.turn = 0, 0, 0
	hum:ChangeState(Enum.HumanoidStateType.Physics)
	local animator = hum:FindFirstChildOfClass("Animator")
	if animator then
		for _, t in animator:GetPlayingAnimationTracks() do
			t:Stop(0.3)
		end
	end
	makeMovers(hrp)
	-- (minus the sprint view-widening the movement script adds, which it takes back off as the skydive starts)
	S.fov = S.fov or (workspace.CurrentCamera.FieldOfView - (workspace.CurrentCamera:GetAttribute("NC_FovOffset") or 0))
	wind:Play()
	gui.Enabled = true
	bindKeys(true)
	setState("freefall")
end

local function finish(hum, hrp, intoWater)
	clearMovers()
	bindKeys(false)
	gui.Enabled = false
	wind:Stop()
	local v = vis[player.Character]
	if v and v.canopy then
		releaseCanopy(v, "land")
		v.state = nil
	end
	setState(nil)
	if hrp then
		hrp.AssemblyLinearVelocity = flat(S.v) * 0.4 + Vector3.new(0, intoWater and S.v.Y or 0, 0)
	end
	if hum then
		hum:ChangeState(intoWater and Enum.HumanoidStateType.Freefall or Enum.HumanoidStateType.Landed)
		hum.CameraOffset = Vector3.zero
	end
	if S.fov then
		TweenService:Create(workspace.CurrentCamera, TweenInfo.new(0.6), { FieldOfView = S.fov }):Play()
		S.fov = nil
	end
end

local function approach(cur, target, kH, kV, dt)
	local h = flat(cur):Lerp(flat(target), 1 - math.exp(-kH * dt))
	local y = cur.Y + (target.Y - cur.Y) * (1 - math.exp(-kV * dt))
	return Vector3.new(h.X, y, h.Z)
end

local function turnToward(cur, want, maxAngle)
	local c, w = Vector3.new(cur.X, 0, cur.Z).Unit, Vector3.new(want.X, 0, want.Z)
	if w.Magnitude < 0.01 then
		return c, 0
	end
	w = w.Unit
	local ang = math.atan2(c:Cross(w).Y, c:Dot(w))
	local step = math.clamp(ang, -maxAngle, maxAngle)
	local r = CFrame.Angles(0, step, 0):VectorToWorldSpace(c) -- positive step turns c toward w when (c x w).Y > 0
	return r, step
end

local frame = 0
RunService.Stepped:Connect(function(_, dt)
	frame += 1
	if frame % 30 == 1 then
		refreshFilter()
	end
	local char = player.Character
	local hrp, hum = bodyOf(char)
	if not hrp then
		return
	end
	local cam = workspace.CurrentCamera
	if S.mode == nil then
		if player:GetAttribute("HasParachute") and hum.Health > 0 and hum:GetState() == Enum.HumanoidStateType.Freefall
			and hrp.AssemblyLinearVelocity.Y < -14 and not inWater(hrp.Position) and feetAGL(hrp, hum) > START_AGL then
			startFreefall(hrp, hum)
		end
		return
	end
	if hum.Health <= 0 then
		finish(hum, nil, false)
		return
	end
	if inWater(hrp.Position) then
		finish(hum, hrp, true)
		return
	end
	local agl = feetAGL(hrp, hum)
	local look = cam.CFrame.LookVector
	local fl = flat(look).Magnitude > 0.01 and flat(look).Unit or S.fwd
	local md = hum.MoveDirection
	local w = md:Dot(S.fwd)
	local right = S.fwd:Cross(Vector3.yAxis).Unit
	local side = md:Dot(right)
	local now = os.clock()
	if S.mode == "freefall" then
		-- the camera steers; W tracks forward or, looking down, dives head-first
		S.fwd = select(1, turnToward(S.fwd, fl, rad(150) * dt))
		local pitchDown = -look.Y
		local target
		if w > 0.2 then
			S.dive = S.dive + (math.clamp((pitchDown - 0.15) / 0.6, 0, 1) - S.dive) * math.min(1, dt * 3)
			local fall = lerpA(FF.trackFall, FF.diveFall, S.dive)
			local fwd = lerpA(FF.trackFwd, FF.diveFwd, S.dive) * w
			target = S.fwd * fwd + right * side * FF.strafe + Vector3.new(0, -fall, 0)
		elseif w < -0.2 then
			S.dive = S.dive * (1 - math.min(1, dt * 3))
			target = S.fwd * FF.backFwd + right * side * FF.strafe + Vector3.new(0, -FF.backFall, 0)
		else
			S.dive = S.dive * (1 - math.min(1, dt * 3))
			target = S.fwd * FF.bellyDrift + right * side * FF.strafe + Vector3.new(0, -FF.bellyFall, 0)
		end
		S.v = approach(S.v, target, FF.respH, FF.respV, dt)
		movers.lv.VectorVelocity = S.v
		-- body: belly to earth, tipping head-down as you dive, banking into a slide
		local a = rad(65) * S.dive
		local up = S.fwd * math.cos(a) - Vector3.yAxis * math.sin(a)
		local back = Vector3.yAxis * math.cos(a) + S.fwd * math.sin(a)
		movers.ao.CFrame = CFrame.fromMatrix(Vector3.zero, up:Cross(back), up, back) * CFrame.Angles(0, rad(-25) * side, 0)
		-- it opens on its own if you leave it too late
		if agl < math.max(30, -S.v.Y * 0.7) then
			deploy()
		end
		if agl < 2.5 then
			finish(hum, hrp, false)
			return
		end
	elseif S.mode == "canopy" then
		local open = math.clamp((now - S.deployT) / CN.openTime, 0, 1)
		-- steering: the chute swings round toward where you look; A/D bank it into a harder turn
		local _, step = turnToward(S.fwd, fl, CN.turn * dt)
		local bankStep = side * CN.bank * dt
		S.fwd = CFrame.Angles(0, step - bankStep, 0):VectorToWorldSpace(S.fwd)
		-- S.turn: +1 = hard right, -1 = hard left (a right turn is a negative yaw step)
		S.turn = S.turn + (-(step - bankStep) / math.max(dt, 1e-3) / CN.turn - S.turn) * math.min(1, dt * 4)
		S.brake = S.brake + ((w < -0.2 and 1 or 0) - S.brake) * math.min(1, dt * 4)
		local fwd, fall
		if w > 0.2 then
			fwd, fall = CN.diveFwd, CN.diveFall
		elseif w < -0.2 then
			fwd, fall = CN.brakeFwd, CN.brakeFall
		else
			fwd, fall = CN.fwd, CN.fall
		end
		local target = S.fwd * fwd + Vector3.new(0, -fall, 0)
		local k = open < 1 and 3.6 or 1 -- the opening jolt bleeds the freefall speed off hard
		S.v = approach(S.v, target, CN.respH * k, CN.respV * k, dt)
		movers.lv.VectorVelocity = S.v
		local lean = rad(10 + (w > 0.2 and 12 or 0) - (w < -0.2 and 10 or 0))
		-- swing out under the wing into the turn (right turn: right side drops)
		movers.ao.CFrame = CFrame.lookAt(Vector3.zero, S.fwd) * CFrame.Angles(-lean, 0, rad(-28) * math.clamp(S.turn, -1, 1))
		if agl < 2.4 then
			finish(hum, hrp, false)
			return
		end
	end
	-- camera: the view stretches with speed, a jolt on opening
	local spd = S.v.Magnitude
	local wantFov = S.mode == "freefall" and (S.fov or 70) + math.clamp((spd - 50) / 80, 0, 1) * 22 or (S.fov or 70) + 4
	cam.FieldOfView += (wantFov - cam.FieldOfView) * math.min(1, dt * 3)
	S.shake = math.max(0, S.shake - dt * 2.5)
	local jitter = S.mode == "freefall" and math.clamp((spd - 90) / 60, 0, 1) * 0.08 or 0
	local amp = S.shake * 0.45 + jitter
	hum.CameraOffset = amp > 0 and Vector3.new(math.noise(now * 18, 1) * amp, math.noise(now * 18, 2) * amp, 0) or Vector3.zero
	wind.Volume = math.clamp(spd / 110, 0.08, 1) * (S.mode == "canopy" and 0.35 or 1)
	wind.PlaybackSpeed = 0.75 + math.clamp(spd / 260, 0, 0.6)
	-- readout
	local metres = math.floor(math.max(0, agl) / 3.8)
	readout.Text = string.format("ALT <font color=\"#7CF5FF\">%d m</font>    SPD <font color=\"#FF6EC7\">%d km/h</font>", metres, math.floor(spd / 3.8 * 3.6))
	hint.Text = S.mode == "freefall" and "SPACE  open   ·   W + look down  dive   ·   S  slow" or "C  cut away   ·   W  speed   ·   S  brake   ·   A / D  turn"
end)

---------------------------------------------------------------------------------------------- everyone's visuals and poses
RunService.Stepped:Connect(function(_, dt)
	local now = os.clock()
	for _, p in Players:GetPlayers() do
		local char = p.Character
		local hrp = char and char:FindFirstChild("HumanoidRootPart")
		if not hrp then
			continue
		end
		local v = vis[char]
		if not v then
			v = {}
			vis[char] = v
			char.AncestryChanged:Connect(function(_, parent)
				if not parent then
					if v.pack then
						v.pack:Destroy()
					end
					if v.canopy then
						v.canopy:Destroy()
					end
					vis[char] = nil
				end
			end)
		end
		-- the pack on the back of anyone who owns a parachute
		if p:GetAttribute("HasParachute") and not v.pack then
			local pk = newPack()
			if attach(char, pk, "UpperTorso", CFrame.new(0, 0, 0.85)) then
				v.pack = pk
			end
		end
		local st = p == player and S.mode or char:GetAttribute("ChuteState")
		if st == "canopy" and not v.canopy then
			local m = newCanopy()
			v.weld = attach(char, m, "HumanoidRootPart", CFrame.new(0, 1.3, 0.35))
			if v.weld then
				v.canopy = m
				v.t0 = now
				pcall(function()
					m:ScaleTo(0.08)
				end)
				playPop(char)
			end
		elseif st ~= "canopy" and v.canopy then
			releaseCanopy(v, st == "freefall" and "cut" or "land")
		end
		v.state = st
		-- the canopy cracking open (scale with a little overshoot) and swaying over the jumper
		if v.canopy and v.weld then
			local t = (now - (v.t0 or now)) / CN.openTime
			if t < 1.25 then
				local s = t < 1 and (0.08 + 0.98 * (1 - (1 - t) ^ 3)) or (1.06 - 0.06 * (t - 1) / 0.25)
				pcall(function()
					v.canopy:ScaleTo(math.clamp(s, 0.08, 1.06))
				end)
			end
			v.weld.C0 = CFrame.new(0, 1.3, 0.35) * CFrame.Angles(math.sin(now * 1.3) * 0.035, 0, math.sin(now * 0.9) * 0.05)
		end
		-- poses
		if st then
			local J = jointsOf(char)
			local vel = hrp.AssemblyLinearVelocity
			if st == "freefall" then
				local dive = p == player and S.dive or math.clamp((-vel.Y - 70) / 50, 0, 1)
				poseFreefall(J, dive, 1)
			else
				local brake = p == player and S.brake or 0
				local turn = p == player and S.turn or 0
				poseCanopy(J, brake, turn, 1)
			end
		end
	end
end)

player.CharacterAdded:Connect(function()
	clearMovers()
	bindKeys(false)
	gui.Enabled = false
	wind:Stop()
	S.mode = nil
end)
