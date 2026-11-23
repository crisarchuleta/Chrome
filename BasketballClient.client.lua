--!nonstrict
-- BasketballClient: the shooter's side of the Basketball script, plus what everyone sees.
--   * Hold left click (Shoot on touch, R2 on a pad) to load the shot, let go at the top of the meter. The arc is
--     real ballistics at 37 studs/s^2 (real gravity) toward the nearest rim you're facing: about 52-58 degrees of
--     launch, backspin, and the human part comes from you: letting go early or late falls short or long, and
--     shooting on the move sprays it. G passes (lobs to a player you're looking at, or a chest pass).
--   * Every held ball is dribbled for every player (bounce speed follows the runner), the shooting pose and the
--     follow-through show on everyone, and a bucket snaps the net, swishes and pops "+2" / "+3" over the rim.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local CAS = game:GetService("ContextActionService")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")
local RS = game:GetService("ReplicatedStorage")

local player = Players.LocalPlayer
local Remotes = RS:WaitForChild("Remotes")
local ShootRE = Remotes:WaitForChild("BallShoot")
local PassRE = Remotes:WaitForChild("BallPass")
local PoseRE = Remotes:WaitForChild("BallPose")
local BucketRE = Remotes:WaitForChild("BallBucket")

local G = 37.0 -- real gravity in studs (the server flies the ball with the same number)
local BALL_R = 0.45
local CHARGE_T = 0.7 -- seconds from empty to the top of the meter (then it falls back: holding too long is late)
local SND_DRIBBLE = { "rbxasset://sounds/action_jump_land.mp3", 1.75 }
local SND_SWISH = { "rbxasset://sounds/action_swim.mp3", 1.9 }

local function sound(parent, def, volume, maxDist)
	local s = Instance.new("Sound")
	s.SoundId = def[1]
	s.PlaybackSpeed = def[2] * (0.95 + math.random() * 0.1)
	s.Volume = volume
	s.RollOffMinDistance = 5
	s.RollOffMaxDistance = maxDist or 90
	s.Parent = parent
	s:Play()
	Debris:AddItem(s, 2)
end

local function flat(v)
	return Vector3.new(v.X, 0, v.Z)
end

local function myBall()
	for _, b in CollectionService:GetTagged("NC_Basketball") do
		if b:GetAttribute("Holder") == player.UserId then
			return b
		end
	end
	return nil
end

local function body()
	local char = player.Character
	local hrp = char and char:FindFirstChild("HumanoidRootPart")
	local head = char and char:FindFirstChild("Head")
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if hrp and head and hum then
		return char, hrp, head, hum
	end
	return nil
end

-- the rim you mean: close, and roughly where the camera looks
local function pickRim(hrp)
	local look = flat(workspace.CurrentCamera.CFrame.LookVector)
	look = look.Magnitude > 0.01 and look.Unit or hrp.CFrame.LookVector
	local best, bestScore
	for _, court in CollectionService:GetTagged("NC_Hoop") do
		local rim = court:FindFirstChild("RimCenter", true)
		if rim then
			local d = flat(rim.WorldPosition - hrp.Position)
			local dist = d.Magnitude
			if dist < 55 then
				local facing = dist > 0.1 and d.Unit:Dot(look) or 1
				if facing > -0.25 then
					local s = dist * (2.2 - facing)
					if not bestScore or s < bestScore then
						best, bestScore = rim, s
					end
				end
			end
		end
	end
	return best
end

-- Launch angle and speed that drop the ball through the rim centre coming down at ENTRY degrees (no air drag,
-- gravity G). Good shooters come in at about 45-47 degrees: steep enough that the 9.4 in ball has room in the
-- 18 in rim (about +-2.5 in along the shot at 47), which works out to a 55-62 degree launch from Roblox height
-- and a 70+ degree lay-in up close. tan(launch) = tan(entry) + 2H/D for a parabola through the target.
local ENTRY = math.rad(47)
local function solveShot(origin, target)
	local d = target - origin
	local D = math.max(flat(d).Magnitude, 0.6)
	local H = d.Y
	local theta = math.min(math.atan(math.tan(ENTRY) + 2 * H / D), math.rad(84))
	local denom = 2 * math.cos(theta) ^ 2 * (D * math.tan(theta) - H)
	if denom <= 0.01 then
		return theta, nil
	end
	return theta, math.sqrt(G * D * D / denom)
end

---------------------------------------------------------------------------------------------- HUD
local gui = Instance.new("ScreenGui")
gui.Name = "BasketballHUD"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.Parent = player:WaitForChild("PlayerGui")

local meter = Instance.new("Frame")
meter.AnchorPoint = Vector2.new(0, 0.5)
meter.Position = UDim2.new(0.5, 70, 0.5, -20)
meter.Size = UDim2.fromOffset(12, 130)
meter.BackgroundColor3 = Color3.fromRGB(16, 18, 24)
meter.BackgroundTransparency = 0.25
meter.BorderSizePixel = 0
meter.Visible = false
meter.Parent = gui
Instance.new("UICorner", meter).CornerRadius = UDim.new(0, 6)
local sweet = Instance.new("Frame") -- the release window at the top
sweet.Size = UDim2.new(1, 0, 0.07, 0)
sweet.BackgroundColor3 = Color3.fromRGB(80, 220, 120)
sweet.BorderSizePixel = 0
sweet.Parent = meter
local fill = Instance.new("Frame")
fill.AnchorPoint = Vector2.new(0, 1)
fill.Position = UDim2.fromScale(0, 1)
fill.Size = UDim2.fromScale(1, 0)
fill.BackgroundColor3 = Color3.fromRGB(255, 255, 255)
fill.BorderSizePixel = 0
fill.Parent = meter
Instance.new("UICorner", fill).CornerRadius = UDim.new(0, 6)
local verdict = Instance.new("TextLabel")
verdict.AnchorPoint = Vector2.new(0, 0.5)
verdict.Position = UDim2.new(0.5, 92, 0.5, -70)
verdict.Size = UDim2.fromOffset(160, 28)
verdict.BackgroundTransparency = 1
verdict.Font = Enum.Font.GothamBlack
verdict.TextSize = 20
verdict.TextXAlignment = Enum.TextXAlignment.Left
verdict.TextStrokeTransparency = 0.5
verdict.TextTransparency = 1
verdict.Parent = gui

local stats = Instance.new("TextLabel")
stats.AnchorPoint = Vector2.new(0.5, 1)
stats.Position = UDim2.new(0.5, 0, 1, -128)
stats.Size = UDim2.fromOffset(360, 44)
stats.BackgroundColor3 = Color3.fromRGB(16, 18, 24)
stats.BackgroundTransparency = 0.35
stats.Font = Enum.Font.GothamBold
stats.TextSize = 15
stats.TextColor3 = Color3.fromRGB(240, 240, 240)
stats.RichText = true
stats.Visible = false
stats.Parent = gui
Instance.new("UICorner", stats).CornerRadius = UDim.new(0, 8)

local function showVerdict(text, color)
	verdict.Text = text
	verdict.TextColor3 = color
	verdict.TextTransparency = 0
	verdict.TextStrokeTransparency = 0.5
	TweenService:Create(verdict, TweenInfo.new(0.9, Enum.EasingStyle.Quad, Enum.EasingDirection.In, 0, false, 0.5), { TextTransparency = 1, TextStrokeTransparency = 1 }):Play()
end

---------------------------------------------------------------------------------------------- shooting
local charging, chargeStart, followUntil = false, 0, 0
local wasCharging, autoRotateWas = false, true
local aimRim = nil

local function chargeValue()
	local t = (os.clock() - chargeStart) / CHARGE_T
	return 1 - math.abs((t % 2) - 1), t > 1
end

local function shoot()
	local b = myBall()
	local char, hrp, head, hum = body()
	if not (b and char) then
		return
	end
	local c, late = chargeValue()
	local up = Vector3.yAxis
	local rim = pickRim(hrp)
	local origin, vel, spin
	if rim then
		local target = rim.WorldPosition
		local d = flat(target - hrp.Position)
		local fwd = d.Magnitude > 0.05 and d.Unit or hrp.CFrame.LookVector
		origin = head.Position + fwd * 1.1 + up * 1.0 -- arms up, ball off the fingertips above the forehead
		local theta, v = solveShot(origin, target)
		v = v or 18
		-- the human part: early is short and late is long (1% of speed is ~0.5 studs at 17 ft, so the green window
		-- swishes, "good" rattles, the rest is rim or air), a little hand jitter, and a lot more when moving
		local moving = math.clamp(flat(hrp.AssemblyLinearVelocity).Magnitude / 16, 0, 1.5)
		local m = 1 + (late and 1 or -1) * (1 - c) * 0.05 + (math.random() * 2 - 1) * (0.0015 + 0.012 * moving)
		local yaw = math.rad((math.random() * 2 - 1) * (0.35 + 1.5 * moving))
		local dir = CFrame.Angles(0, yaw, 0):VectorToWorldSpace(fwd)
		vel = (dir * math.cos(theta) + up * math.sin(theta)) * v * m
		spin = dir:Cross(up) * 12 -- about two turns a second of backspin: soft off the rim, true off the glass
		hrp.CFrame = CFrame.lookAt(hrp.Position, hrp.Position + fwd)
	else
		local look = flat(workspace.CurrentCamera.CFrame.LookVector)
		look = look.Magnitude > 0.01 and look.Unit or hrp.CFrame.LookVector
		origin = head.Position + look * 1.1 + up * 1.0
		vel = (look * math.cos(math.rad(50)) + up * math.sin(math.rad(50))) * (12 + 16 * c)
		spin = look:Cross(up) * 10
	end
	ShootRE:FireServer(b, origin, vel, spin)
	followUntil = os.clock() + 0.6
	if c >= 0.93 then
		showVerdict("Perfect", Color3.fromRGB(90, 230, 130))
	elseif c >= 0.8 then
		showVerdict("Good", Color3.fromRGB(240, 220, 90))
	else
		showVerdict(late and "Late" or "Early", Color3.fromRGB(240, 110, 90))
	end
end

local function pass()
	local b = myBall()
	local char, hrp, head = body()
	if not (b and char) then
		return
	end
	local cam = workspace.CurrentCamera
	local look = cam.CFrame.LookVector
	local fl = flat(look).Magnitude > 0.01 and flat(look).Unit or hrp.CFrame.LookVector
	local origin = head.Position + fl * 1.2 - Vector3.new(0, 0.7, 0) -- from the chest
	-- a player you're looking at gets it on the chest (exact ballistic lob), otherwise a chest pass that way
	local best, bestDot
	for _, other in Players:GetPlayers() do
		local oc = other ~= player and other.Character
		local ot = oc and oc:FindFirstChild("UpperTorso") or (oc and oc:FindFirstChild("HumanoidRootPart"))
		if ot then
			local d = ot.Position - origin
			if d.Magnitude < 60 then
				local dot = d.Unit:Dot(look)
				if dot > 0.93 and (not bestDot or dot > bestDot) then
					best, bestDot = ot, dot
				end
			end
		end
	end
	local vel
	if best then
		local target = best.Position + best.AssemblyLinearVelocity * 0.25
		local dist = (target - origin).Magnitude
		local t = math.clamp(dist / 30, 0.25, 1.6)
		vel = (target - origin) / t + Vector3.new(0, 0.5 * G * t, 0)
	else
		vel = (look + Vector3.new(0, 0.12, 0)).Unit * 30
	end
	if vel.Magnitude > 54 then
		vel = vel.Unit * 54
	end
	PassRE:FireServer(b, origin, vel)
end

local function onShoot(_, state)
	if state == Enum.UserInputState.Begin then
		if not myBall() then
			return Enum.ContextActionResult.Pass
		end
		charging, chargeStart = true, os.clock()
		PoseRE:FireServer("charge")
	elseif state == Enum.UserInputState.End then
		if charging then
			charging = false
			shoot()
		end
	elseif state == Enum.UserInputState.Cancel then -- (a touch button sends Change while the finger slides: ignore)
		if charging then
			charging = false
			PoseRE:FireServer(nil)
		end
	end
	return Enum.ContextActionResult.Sink
end

local function onPass(_, state)
	if state == Enum.UserInputState.Begin and myBall() then
		charging = false
		pass()
		return Enum.ContextActionResult.Sink
	end
	return Enum.ContextActionResult.Pass
end

local bound = false
local function setBound(on)
	if on == bound then
		return
	end
	bound = on
	if on then
		CAS:BindActionAtPriority("NC_Shoot", onShoot, true, 3000, Enum.UserInputType.MouseButton1, Enum.KeyCode.ButtonR2)
		CAS:SetTitle("NC_Shoot", "Shoot")
		CAS:BindActionAtPriority("NC_Pass", onPass, true, 3000, Enum.KeyCode.G, Enum.KeyCode.ButtonX)
		CAS:SetTitle("NC_Pass", "Pass")
	else
		CAS:UnbindAction("NC_Shoot")
		CAS:UnbindAction("NC_Pass")
		if charging then
			charging = false
			PoseRE:FireServer(nil)
		end
	end
end

---------------------------------------------------------------------------------------------- poses (all players)
-- Rotation-only joint override that works for Motor6D rigs and AnimationConstraint (starter body) rigs alike:
-- q is where Part1 should point relative to Part0; T = C0^-1 * q * C1 keeps the joint where it is.
local jointCache = setmetatable({}, { __mode = "k" })
local JOINTS = { RightShoulder = true, RightElbow = true, LeftShoulder = true, LeftElbow = true }
local function jointsOf(char)
	local e = jointCache[char]
	if e and (e.n == 4 or os.clock() - e.t < 2) then
		return e
	end
	e = { n = 0, t = os.clock() }
	for _, d in char:GetDescendants() do
		if JOINTS[d.Name] and (d:IsA("Motor6D") or d:IsA("AnimationConstraint")) and not e[d.Name] then
			e[d.Name] = d
			e.n += 1
		end
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

local rad = math.rad
local POSE = {
	-- set point: shooting upper arm out front, forearm straight up under the ball, guide hand on its side
	charge = {
		RightShoulder = CFrame.Angles(rad(100), 0, 0), RightElbow = CFrame.Angles(rad(90), 0, 0),
		LeftShoulder = CFrame.Angles(rad(95), 0, rad(25)), LeftElbow = CFrame.Angles(rad(80), 0, 0),
	},
	-- follow-through: arm up and out at the rim, wrist down
	follow = {
		RightShoulder = CFrame.Angles(rad(150), 0, 0), RightElbow = CFrame.Angles(rad(8), 0, 0),
		LeftShoulder = CFrame.Angles(rad(120), 0, rad(20)), LeftElbow = CFrame.Angles(rad(30), 0, 0),
	},
}

local dribble = setmetatable({}, { __mode = "k" }) -- ball -> { phase, blend }
local follow = setmetatable({}, { __mode = "k" }) -- char -> blend

local function thump(b)
	if (workspace.CurrentCamera.CFrame.Position - b.Position).Magnitude < 90 then
		sound(b, SND_DRIBBLE, 0.32, 70)
	end
end

local function animateHolder(b, char, dt, isLocal)
	local hrp = char:FindFirstChild("HumanoidRootPart")
	local head = char:FindFirstChild("Head")
	local hum = char:FindFirstChildOfClass("Humanoid")
	local w = b:FindFirstChild("BallHold")
	if not (hrp and head and hum and w and w.Part0 == hrp) then
		return
	end
	local st = dribble[b]
	if not st or st.char ~= char then
		st = { phase = 0.5, blend = 0, char = char }
		dribble[b] = st
	end
	st.blend = math.min(1, st.blend + dt * 6)
	local J = jointsOf(char)
	local pose = char:GetAttribute("BallPose")
	if isLocal then
		pose = charging and "charge" or nil -- the shooter sees it right away
	end
	if pose == "charge" then
		local c = isLocal and (chargeValue()) or 0.5
		local headL = hrp.CFrame:PointToObjectSpace(head.Position)
		w.C0 = w.C0:Lerp(CFrame.new(0.3, headL.Y + 0.5 + 0.1 * c, -0.9), math.min(1, dt * 18))
		for name, q in POSE.charge do
			setJoint(J[name], q, st.blend)
		end
		st.phase = 0.5
		return
	end
	-- dribble: ball between the hand and the floor, fastest at the floor (a real bounce), quicker on the run
	local speed = flat(hrp.AssemblyLinearVelocity).Magnitude
	local before = st.phase
	st.phase += dt * (1.3 + math.min(speed, 24) * 0.045)
	if math.floor(before + 0.5) ~= math.floor(st.phase + 0.5) then
		thump(b)
	end
	local hgt = math.abs(math.cos(math.pi * st.phase))
	local floorY = -(hrp.Size.Y / 2 + hum.HipHeight) + BALL_R
	local top = Vector3.new(1.0, -0.8, -0.9)
	local low = Vector3.new(1.15, floorY, -1.25 - math.min(speed, 24) * 0.03)
	w.C0 = CFrame.new(low:Lerp(top, hgt))
	setJoint(J.RightShoulder, CFrame.Angles(rad(25 + 25 * hgt), 0, rad(12)), st.blend)
	setJoint(J.RightElbow, CFrame.Angles(rad(20 + 45 * hgt), 0, 0), st.blend)
end

RunService.Stepped:Connect(function(_, dt)
	local holding = {}
	for _, b in CollectionService:GetTagged("NC_Basketball") do
		local id = b:GetAttribute("Holder")
		local p = id and Players:GetPlayerByUserId(id)
		local char = p and p.Character
		if char then
			holding[char] = true
			animateHolder(b, char, dt, p == player)
		end
	end
	-- follow-through after the shot, for everyone (the shooter's own from the local clock)
	for _, p in Players:GetPlayers() do
		local char = p.Character
		if char and not holding[char] then
			local on = (p == player and os.clock() < followUntil) or (p ~= player and char:GetAttribute("BallPose") == "follow")
			if on then
				follow[char] = math.min(1, (follow[char] or 0) + dt * 10)
				local J = jointsOf(char)
				for name, q in POSE.follow do
					setJoint(J[name], q, follow[char])
				end
			else
				follow[char] = nil
			end
		end
	end
end)

---------------------------------------------------------------------------------------------- per frame: HUD, aim
RunService.RenderStepped:Connect(function()
	local b = myBall()
	setBound(b ~= nil)
	local char, hrp, _, hum = body()
	if hum and charging ~= wasCharging then
		-- only while loading a shot, and put back whatever it was (other systems use AutoRotate too)
		if charging then
			autoRotateWas = hum.AutoRotate
			hum.AutoRotate = false
		else
			hum.AutoRotate = autoRotateWas ~= false
		end
		wasCharging = charging
	end
	if charging and hrp then
		-- square up to the rim while loading the shot (you can still drift)
		aimRim = pickRim(hrp)
		if aimRim then
			local d = flat(aimRim.WorldPosition - hrp.Position)
			if d.Magnitude > 0.1 then
				local want = CFrame.lookAt(hrp.Position, hrp.Position + d)
				hrp.CFrame = hrp.CFrame:Lerp(want, 0.35)
			end
		end
	end
	meter.Visible = charging
	if charging then
		local c = chargeValue()
		fill.Size = UDim2.fromScale(1, c)
		fill.BackgroundColor3 = c >= 0.93 and Color3.fromRGB(90, 230, 130) or Color3.fromRGB(255, 255, 255)
	end
	-- stats when you have the ball or stand near a hoop
	local near = b ~= nil
	if not near and hrp then
		for _, court in CollectionService:GetTagged("NC_Hoop") do
			local rim = court:FindFirstChild("RimCenter", true)
			if rim and flat(rim.WorldPosition - hrp.Position).Magnitude < 45 then
				near = true
				break
			end
		end
	end
	stats.Visible = near
	if near then
		local hint = UserInputService.TouchEnabled and not UserInputService.KeyboardEnabled and "Shoot / Pass buttons"
			or "Hold click: shoot · G: pass"
		if not b then
			hint = "Grab the ball (E) or run into it"
		end
		stats.Text = string.format("<b>PTS %d</b>   FG %d/%d\n<font size=\"12\" color=\"#BBBBBB\">%s</font>",
			player:GetAttribute("Buckets") or 0, player:GetAttribute("Makes") or 0, player:GetAttribute("Shots") or 0, hint)
	end
end)

---------------------------------------------------------------------------------------------- buckets
BucketRE.OnClientEvent:Connect(function(court, pts, who, swish, bank)
	if typeof(court) ~= "Instance" or not court:IsDescendantOf(workspace) then
		return
	end
	local rim = court:FindFirstChild("RimCenter", true)
	if not rim then
		return
	end
	-- the net snaps down and swings back
	local net = court:FindFirstChild("Net", true)
	if net and net:IsA("BasePart") then
		local base = net:GetAttribute("BaseCFrame")
		if not base then
			base = net.CFrame
			net:SetAttribute("BaseCFrame", base)
		end
		net.CFrame = base * CFrame.new(0, -0.35, 0)
		TweenService:Create(net, TweenInfo.new(0.7, Enum.EasingStyle.Elastic, Enum.EasingDirection.Out), { CFrame = base }):Play()
	end
	sound(rim, SND_SWISH, swish and 0.8 or 0.5, 100)
	-- "+2" / "SWISH +3" over the rim
	local bb = Instance.new("BillboardGui")
	bb.Size = UDim2.fromOffset(240, 70)
	bb.StudsOffsetWorldSpace = Vector3.new(0, 1.2, 0)
	bb.AlwaysOnTop = true
	bb.MaxDistance = 150
	bb.LightInfluence = 0
	local t = Instance.new("TextLabel")
	t.Size = UDim2.fromScale(1, 1)
	t.BackgroundTransparency = 1
	t.Font = Enum.Font.GothamBlack
	t.TextScaled = true
	t.RichText = true
	t.TextColor3 = pts == 3 and Color3.fromRGB(255, 200, 70) or Color3.fromRGB(255, 255, 255)
	t.TextStrokeTransparency = 0.3
	local head = pts > 0 and ((swish and "SWISH  " or bank and "BANK  " or "") .. "+" .. pts) or "Bucket!"
	t.Text = who and (head .. "\n<font size=\"16\">" .. who .. "</font>") or head
	t.Parent = bb
	bb.Parent = rim
	TweenService:Create(bb, TweenInfo.new(1.6, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { StudsOffsetWorldSpace = Vector3.new(0, 4, 0) }):Play()
	TweenService:Create(t, TweenInfo.new(0.6, Enum.EasingStyle.Quad, Enum.EasingDirection.In, 0, false, 1.0), { TextTransparency = 1, TextStrokeTransparency = 1 }):Play()
	Debris:AddItem(bb, 1.8)
	if who == player.DisplayName and pts > 0 then
		showVerdict((swish and "Swish! " or "") .. "+" .. pts, pts == 3 and Color3.fromRGB(255, 200, 70) or Color3.fromRGB(90, 230, 130))
	end
end)
