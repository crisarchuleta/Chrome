--!nonstrict
-- LowriderClient: drives the lowrider, runs the hydraulics / air bags, poses every lowrider's wheels, the hop pit
-- meter, and the Low & Slow Kustoms shop screen (live preview of paint, art and wheels before you pay).
--
-- Driving model: raycast suspension. Each corner casts down from the body; a spring + damper pushes the body up
-- at that corner, and the tyre pushes sideways (grip) and forwards (drive / brakes) at its contact point. All of
-- it goes into the chassis's one VectorForce + Torque, on the client that owns the car's physics (the driver, or
-- the owner while it's parked). The hydraulics just move each corner's ride height:
--   arrows / D-pad   lift front / back / left / right (two at once = one corner)
--   SPACE (hold, let go)  front hop; let go just as the front lands to hop higher
--   B                body hop (all four)
--   G                three-wheel (the front corner on the side you're steering, else the left)
--   X                ride height: ride -> laid frame -> lifted
--   V                dance (competition hopper only)
--   F                get out
-- Air bags: smooth lifts and lay frame, no hopping. Stock springs: just drive.
local ContextActionService = game:GetService("ContextActionService")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")

local Config = require(RS:WaitForChild("NCLowriderConfig"))
local Data = require(RS:WaitForChild("NCLowriderData"))
local Kit = require(RS:WaitForChild("NCLowriderKit"))
local Remotes = RS:WaitForChild("Remotes")
local ShopRF = Remotes:WaitForChild("LowriderShop")
local StateRE = Remotes:WaitForChild("LowriderState")
local UiRE = Remotes:WaitForChild("LowriderUI")
local HopRE = Remotes:WaitForChild("LowriderHop")

local player = Players.LocalPlayer
local camera = workspace.CurrentCamera
local D = Config.Drive
local R = Data.Car.WheelRadius
local CORNERS = { "FL", "FR", "RL", "RR" }
local REST = {}
for _, c in CORNERS do
	local p = Data.Car.Wheels[c]
	REST[c] = Vector3.new(p[1], p[2], p[3])
end
local RAY_UP = 2.5 -- the ray starts this far above the wheel centre's rest height

local function notify(text, color)
	local remotesNotify = Remotes:FindFirstChild("Notify")
	if remotesNotify and remotesNotify:IsA("BindableEvent") then
		remotesNotify:Fire(text, color)
	end
	pcall(function()
		game:GetService("StarterGui"):SetCore("SendNotification", { Title = "Low & Slow", Text = text, Duration = 4 })
	end)
end

---------------------------------------------------------------------------------------------------- per-car state
local state = setmetatable({}, { __mode = "k" }) -- [car] = { e = {}, target = {}, spin = {}, ... }

local function st(car)
	local s = state[car]
	if not s then
		s = { e = {}, target = {}, spin = {}, vis = {}, ground = {}, landed = {}, steer = 0, mode = "ride", threeWheel = nil, dance = false,
			charge = 0, charging = false, lastSend = 0, hopPeak = nil, frontAirT = 0 }
		for _, c in CORNERS do
			s.e[c], s.target[c], s.spin[c], s.vis[c], s.ground[c], s.landed[c] = 0, 0, 0, 0, false, -1
		end
		state[car] = s
	end
	return s
end

local function susp(car)
	return Config.Susp(car:GetAttribute("Susp"))
end

local function rayParams(car)
	local rp = RaycastParams.new()
	local ignore = { car }
	local lr = workspace:FindFirstChild("Lowriders")
	if lr then
		table.insert(ignore, lr) -- other lowriders: the bodies collide anyway; this keeps wheels off roofs
	end
	for _, p in Players:GetPlayers() do
		if p.Character then
			table.insert(ignore, p.Character)
		end
	end
	rp.FilterDescendantsInstances = ignore
	rp.FilterType = Enum.RaycastFilterType.Exclude
	rp.IgnoreWater = false
	return rp
end

---------------------------------------------------------------------------------------------------- wheels (everyone)
-- casts every corner, poses the wheels; returns per-corner { hit, d, point, normal } in world space
local function castWheels(car, s, origin, rp, sp)
	local up = origin.UpVector
	local out = {}
	local drop = sp.drop
	for _, c in CORNERS do
		local rest = REST[c]
		local start = origin:PointToWorldSpace(Vector3.new(rest.X, rest.Y + RAY_UP, rest.Z))
		local len = RAY_UP + R + math.max(0, s.e[c]) + D.Droop + 0.6
		local hit = workspace:Raycast(start, -up * len, rp)
		local d, grounded = s.e[c] + D.Droop, false
		if hit then
			local h = (hit.Position - start):Dot(-up)
			local dd = h - RAY_UP - R
			if dd <= s.e[c] + D.Droop then
				d, grounded = math.max(dd, -drop - D.BumpStop), true
			end
		end
		out[c] = { hit = hit, d = d, grounded = grounded, start = start }
	end
	return out
end

local function poseWheels(car, s, origin, casts, steerAngle, fwdSpeed, dt)
	local ch = car.PrimaryPart
	for _, c in CORNERS do
		local w = car:FindFirstChild("W_" .. c)
		local hub = w and w.PrimaryPart
		local weld = hub and hub:FindFirstChild("WheelWeld")
		if weld then
			local rest = REST[c]
			local cast = casts[c]
			-- ease the visual so a missed ray doesn't snap
			s.vis[c] = s.vis[c] + (cast.d - s.vis[c]) * math.min(1, dt * 30)
			s.spin[c] = (s.spin[c] + fwdSpeed / R * dt) % (math.pi * 2)
			local isRight = rest.X > 0
			local steer = rest.Z < 0 and steerAngle or 0
			local local_ = ch.Origin.CFrame * CFrame.new(rest.X, rest.Y - s.vis[c], rest.Z) * CFrame.Angles(0, -steer, 0)
				* (isRight and CFrame.Angles(0, math.pi, 0) or CFrame.identity) * CFrame.Angles((isRight and 1 or -1) * s.spin[c], 0, 0)
			weld.C0 = local_
		end
	end
end

---------------------------------------------------------------------------------------------------- physics (the car I simulate)
local function simulate(car, s, dt, input)
	local ch = car.PrimaryPart
	local drive, turn = ch:FindFirstChild("Drive"), ch:FindFirstChild("Turn")
	if not (drive and turn) then
		return
	end
	local sp = susp(car)
	local origin = ch.CFrame * ch.Origin.CFrame
	local up, fwd, right = origin.UpVector, origin.LookVector, origin.RightVector
	local mass = ch.AssemblyMass
	local g = workspace.Gravity
	local k = mass * g / 4 / D.SpringSag
	local cdamp = 2 * D.Damping * math.sqrt(k * mass / 4)
	local com = ch.AssemblyCenterOfMass
	local vel = ch.AssemblyLinearVelocity
	local fwdSpeed = vel:Dot(fwd)
	local rp = rayParams(car)

	-- hydraulics: move each corner toward its target
	for _, c in CORNERS do
		local t = math.clamp(s.target[c], -sp.drop, sp.lift)
		local rate = sp.speed > 0 and sp.speed * (t < s.e[c] and 1.8 or 1) or 4
		local diff = t - s.e[c]
		s.e[c] = s.e[c] + math.clamp(diff, -rate * dt, rate * dt)
		if sp.kit == "none" then
			s.e[c] = 0
		end
	end

	-- steering eases in; less lock at speed
	local speedFrac = math.clamp(math.abs(fwdSpeed) / D.TopSpeed, 0, 1)
	local maxSteer = math.rad(D.SteerMax + (D.SteerFast - D.SteerMax) * speedFrac)
	s.steer = s.steer + (input.steer * maxSteer - s.steer) * math.min(1, dt * 8)

	local casts = castWheels(car, s, origin, rp, sp)
	local F, T = Vector3.zero, Vector3.zero
	local grounded = 0
	for _, c in CORNERS do
		if casts[c].grounded then
			grounded += 1
		end
	end
	for _, c in CORNERS do
		local cast = casts[c]
		local rest = REST[c]
		local disabled = s.threeWheel == c
		if cast.grounded and not disabled then
			local contact = cast.hit.Position
			local attach = origin:PointToWorldSpace(Vector3.new(rest.X, rest.Y, rest.Z))
			local pv = ch:GetVelocityAtPosition(attach)
			local x = (s.e[c] + D.SpringSag) - cast.d
			local spring = k * x - cdamp * pv:Dot(up)
			if cast.d <= -sp.drop - D.BumpStop + 0.02 then
				spring += k * 4 * (-sp.drop - D.BumpStop + 0.02 - cast.d) + cdamp * math.max(0, -pv:Dot(up))
			end
			spring = math.clamp(spring, 0, mass * g * 4)
			local N = spring
			local f = up * spring
			-- tyre: the wheel's own forward / side directions on the ground
			local isFront = rest.Z < 0
			local steer = isFront and s.steer or 0
			local wf = (CFrame.fromAxisAngle(up, -steer) * fwd)
			local wr = wf:Cross(up)
			local cv = ch:GetVelocityAtPosition(contact)
			local vLat = cv:Dot(wr)
			local vLong = cv:Dot(wf)
			local share = mass / math.max(grounded, 1)
			local grip = (isFront and D.Grip or D.RearGrip) * share
			local mu = 1.15 * N
			local lat = math.clamp(-vLat * grip, -mu, mu)
			local long = 0
			if input.throttle > 0.05 then
				if not isFront and fwdSpeed < D.TopSpeed then
					long = mass * D.Accel * input.throttle / 2
				end
				if fwdSpeed < -1 then
					long += mass * D.Brake * 0.25
				end
			elseif input.throttle < -0.05 then
				if fwdSpeed > 1 then
					long = -mass * D.Brake * 0.25 * -input.throttle
				elseif not isFront and fwdSpeed > -D.ReverseSpeed then
					long = mass * D.Accel * 0.6 * input.throttle / 2
				end
			elseif input.park then
				long = -vLong * share * 10 -- parked: hold it still (clamped by grip below)
			else
				long = -math.sign(vLong) * math.min(math.abs(vLong) * share * 2, mass * D.Coast / 4)
			end
			long = math.clamp(long, -mu, mu)
			f += wr * lat + wf * long
			F += f
			T += (contact - com):Cross(f)
		end
	end

	-- three-wheel: hold the lifted corner up with a torque about the diagonal the car balances on
	if s.threeWheel and grounded >= 2 then
		local c = s.threeWheel
		local diag = { FL = { "FR", "RL" }, FR = { "FL", "RR" } }
		local a, b = diag[c][1], diag[c][2]
		local pa = origin:PointToWorldSpace(Vector3.new(REST[a].X, 0, REST[a].Z))
		local pb = origin:PointToWorldSpace(Vector3.new(REST[b].X, 0, REST[b].Z))
		local pc = origin:PointToWorldSpace(Vector3.new(REST[c].X, 0, REST[c].Z))
		local axis = (pb - pa).Unit
		if axis:Cross(pc - pa).Y < 0 then
			axis = -axis
		end
		local ground = casts[a].hit and casts[a].hit.Position.Y or pa.Y
		local height = pc.Y - ground -- the lifted corner's underside above the road
		local target = 2.4
		local w = ch.AssemblyAngularVelocity:Dot(axis)
		local inertia = mass * 10
		local torque = inertia * (10 * (target - height) - 8 * w)
		T += axis * math.clamp(torque, -inertia * 60, inertia * 60)
	end

	-- a little yaw damping so it doesn't spin out at a standstill
	local yawRate = ch.AssemblyAngularVelocity:Dot(up)
	if grounded >= 3 and math.abs(input.steer) < 0.05 then
		T += up * (-yawRate * mass * 4)
	end

	drive.Force = F
	turn.Torque = T

	-- for the wheels + hop meter
	s.casts, s.fwdSpeed, s.grounded = casts, fwdSpeed, grounded
	for _, c in CORNERS do
		local was = s.ground[c]
		s.ground[c] = casts[c].grounded
		if s.ground[c] and not was then
			s.landed[c] = os.clock()
		end
	end
	poseWheels(car, s, origin, casts, s.steer, fwdSpeed, dt)

	-- tell the server my corner heights (other players' wheels follow them)
	if os.clock() - s.lastSend > 0.1 then
		s.lastSend = os.clock()
		StateRE:FireServer(car, s.e.FL, s.e.FR, s.e.RL, s.e.RR, s.threeWheel and ("3w" .. s.threeWheel) or (s.dance and "dance" or s.mode))
	end
end

---------------------------------------------------------------------------------------------------- controls
local held = { up = false, down = false, left = false, right = false }
local myCar = nil -- the car I'm driving
local danceT = 0

local function myDriveSeat()
	local char = player.Character
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	local seat = hum and hum.SeatPart
	if seat and seat.Name == "DriveSeat" and seat.Parent and seat.Parent:GetAttribute("NCLowrider") then
		return seat, hum
	end
	return nil, hum
end

local function baseHeight(s, sp)
	if s.mode == "laid" then
		return -sp.drop
	elseif s.mode == "lifted" then
		return sp.lift * 0.7
	end
	return 0
end

-- turns the held buttons into a target height for every corner
local function updateTargets(car, s, dt)
	local sp = susp(car)
	local base = baseHeight(s, sp)
	for _, c in CORNERS do
		s.target[c] = base
	end
	if sp.kit == "none" then
		return
	end
	local v = held.up and 1 or (held.down and -1 or 0)
	local h = held.left and -1 or (held.right and 1 or 0)
	local function lift(c)
		s.target[c] = sp.lift
	end
	if v ~= 0 and h ~= 0 then
		lift((v > 0 and "F" or "R") .. (h < 0 and "L" or "R"))
	elseif v > 0 then
		lift("FL")
		lift("FR")
	elseif v < 0 then
		lift("RL")
		lift("RR")
	elseif h < 0 then
		lift("FL")
		lift("RL")
	elseif h > 0 then
		lift("FR")
		lift("RR")
	end
	if s.threeWheel then
		local opp = { FL = "RR", FR = "RL" }
		local side = { FL = "RL", FR = "RR" }
		local other = { FL = "FR", FR = "FL" }
		s.target[opp[s.threeWheel]] = -sp.drop
		s.target[side[s.threeWheel]] = sp.lift * 0.8
		s.target[other[s.threeWheel]] = sp.lift * 0.5
		s.target[s.threeWheel] = sp.lift
	end
	if s.dance and sp.dance then
		danceT += dt
		local pattern = math.floor(danceT / 4) % 3
		local w = 7
		for _, c in CORNERS do
			local ph
			if pattern == 0 then -- side to side
				ph = c:sub(2) == "L" and 0 or math.pi
			elseif pattern == 1 then -- front-back seesaw
				ph = c:sub(1, 1) == "F" and 0 or math.pi
			else -- round the corners
				ph = ({ FL = 0, FR = math.pi / 2, RR = math.pi, RL = math.pi * 1.5 })[c]
			end
			s.target[c] = sp.lift * 0.5 * (1 + math.sin(danceT * w + ph))
		end
	end
	if s.charging then
		s.target.FL, s.target.FR = -sp.drop, -sp.drop
		s.charge = math.min(1, s.charge + dt / 0.6)
	end
end

local function hop(car, s, which)
	local sp = susp(car)
	if sp.hop <= 0 then
		notify(sp.kit == "bags" and "Air bags can't hop. Get hydraulics at Low & Slow Kustoms." or "Stock springs can't hop. Get hydraulics at Low & Slow Kustoms.")
		return
	end
	local ch = car.PrimaryPart
	local origin = ch.CFrame * ch.Origin.CFrame
	local mass = ch.AssemblyMass
	-- timing: let go right as the front lands (springs loaded) for a bigger hop
	local now = os.clock()
	local bonus = 1
	if now - math.max(s.landed.FL, s.landed.FR) < 0.2 and s.lastHop and now - s.lastHop < 2.5 then
		bonus = 1.35
	end
	s.lastHop = now
	local power = sp.hop * (0.45 + 0.55 * s.charge) * bonus
	if which == "front" then
		local p = origin:PointToWorldSpace(Vector3.new(0, 1, REST.FL.Z))
		ch:ApplyImpulseAtPosition(origin.UpVector * mass * power * 0.62, p)
		s.e.FL, s.e.FR = sp.lift, sp.lift
	else
		ch:ApplyImpulse(origin.UpVector * mass * power * 0.55)
		for _, c in CORNERS do
			s.e[c] = sp.lift
		end
	end
	local snd = Config.Sounds.Hop
	if snd ~= "" then
		local so = Instance.new("Sound")
		so.SoundId = snd
		so.Parent = ch
		so:Play()
		game:GetService("Debris"):AddItem(so, 3)
	end
end

local ACTIONS = {}
local function bind()
	local function act(name, fn, ...)
		ContextActionService:BindActionAtPriority(name, function(_, stateIn, obj)
			fn(stateIn == Enum.UserInputState.Begin, stateIn, obj)
			return Enum.ContextActionResult.Sink
		end, false, 3000, ...)
		table.insert(ACTIONS, name)
	end
	act("LR_Up", function(b, si)
		held.up = si == Enum.UserInputState.Begin or (si == Enum.UserInputState.Change and held.up)
	end, Enum.KeyCode.Up, Enum.KeyCode.KeypadEight, Enum.KeyCode.DPadUp)
	act("LR_Down", function(b, si)
		held.down = si == Enum.UserInputState.Begin or (si == Enum.UserInputState.Change and held.down)
	end, Enum.KeyCode.Down, Enum.KeyCode.KeypadTwo, Enum.KeyCode.DPadDown)
	act("LR_Left", function(b, si)
		held.left = si == Enum.UserInputState.Begin or (si == Enum.UserInputState.Change and held.left)
	end, Enum.KeyCode.Left, Enum.KeyCode.KeypadFour, Enum.KeyCode.DPadLeft)
	act("LR_Right", function(b, si)
		held.right = si == Enum.UserInputState.Begin or (si == Enum.UserInputState.Change and held.right)
	end, Enum.KeyCode.Right, Enum.KeyCode.KeypadSix, Enum.KeyCode.DPadRight)
	act("LR_Hop", function(b, si)
		if not myCar then
			return
		end
		local s = st(myCar)
		if b then
			if susp(myCar).hop > 0 then
				s.charging, s.charge = true, 0
			else
				hop(myCar, s, "front")
			end
		elseif si == Enum.UserInputState.End and s.charging then
			s.charging = false
			hop(myCar, s, "front")
		end
	end, Enum.KeyCode.Space, Enum.KeyCode.ButtonA)
	act("LR_BodyHop", function(b)
		if b and myCar then
			local s = st(myCar)
			s.charge = 0.8
			hop(myCar, s, "body")
		end
	end, Enum.KeyCode.B, Enum.KeyCode.ButtonX)
	act("LR_3W", function(b)
		if not (b and myCar) then
			return
		end
		local s = st(myCar)
		local sp = susp(myCar)
		if s.threeWheel then
			s.threeWheel = nil
			return
		end
		if not sp.threeWheel then
			notify("Three-wheel needs the 3-pump or 4-pump hydraulics.")
			return
		end
		local seat = myCar:FindFirstChild("DriveSeat")
		local steer = seat and seat.SteerFloat or 0
		s.threeWheel = (steer > 0.2 or held.right) and "FR" or "FL"
		s.dance = false
	end, Enum.KeyCode.G, Enum.KeyCode.ButtonY)
	act("LR_Height", function(b)
		if not (b and myCar) then
			return
		end
		local s = st(myCar)
		if susp(myCar).kit == "none" then
			notify("Stock springs. Air bags or hydraulics can lay it out.")
			return
		end
		s.mode = s.mode == "ride" and "laid" or (s.mode == "laid" and "lifted" or "ride")
	end, Enum.KeyCode.X, Enum.KeyCode.ButtonL3)
	act("LR_Dance", function(b)
		if not (b and myCar) then
			return
		end
		local s = st(myCar)
		if not susp(myCar).dance then
			notify("Dancing needs the 4-pump competition setup.")
			return
		end
		s.dance = not s.dance
		s.threeWheel = nil
		danceT = 0
	end, Enum.KeyCode.V, Enum.KeyCode.ButtonR3)
	act("LR_Exit", function(b)
		if b then
			local _, hum = myDriveSeat()
			if hum then
				hum.Sit = false
				task.defer(function()
					hum.Jump = true
				end)
			end
		end
	end, Enum.KeyCode.F, Enum.KeyCode.ButtonB)
end

local function unbind()
	for _, n in ACTIONS do
		ContextActionService:UnbindAction(n)
	end
	table.clear(ACTIONS)
	for k in held do
		held[k] = false
	end
end

---------------------------------------------------------------------------------------------------- HUD
local gui = Instance.new("ScreenGui")
gui.Name = "LowriderHUD"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.Parent = player:WaitForChild("PlayerGui")

local hud = Instance.new("Frame")
hud.Name = "Hydraulics"
hud.AnchorPoint = Vector2.new(0, 1)
hud.Position = UDim2.new(0, 16, 1, -16)
hud.Size = UDim2.fromOffset(250, 150)
hud.BackgroundColor3 = Color3.fromRGB(14, 12, 20)
hud.BackgroundTransparency = 0.2
hud.Visible = false
hud.Parent = gui
Instance.new("UICorner", hud).CornerRadius = UDim.new(0, 12)
local hudStroke = Instance.new("UIStroke", hud)
hudStroke.Color = Color3.fromRGB(255, 64, 166)
hudStroke.Thickness = 2

local function label(parent, text, pos, size, color, font, align)
	local t = Instance.new("TextLabel")
	t.BackgroundTransparency = 1
	t.Position, t.Size = pos, size
	t.Text = text
	t.TextColor3 = color or Color3.new(1, 1, 1)
	t.Font = font or Enum.Font.GothamMedium
	t.TextScaled = true
	t.TextXAlignment = align or Enum.TextXAlignment.Left
	t.Parent = parent
	return t
end
local title = label(hud, "HYDRAULICS", UDim2.fromOffset(12, 6), UDim2.fromOffset(150, 20), Color3.fromRGB(40, 242, 242), Enum.Font.GothamBlack)
local modeL = label(hud, "", UDim2.fromOffset(12, 28), UDim2.fromOffset(226, 16), Color3.fromRGB(255, 214, 70))
local bars = {}
-- a top-down car with four corner bars
local carIcon = Instance.new("Frame")
carIcon.Position = UDim2.fromOffset(170, 8)
carIcon.Size = UDim2.fromOffset(66, 118)
carIcon.BackgroundColor3 = Color3.fromRGB(150, 8, 24)
carIcon.Parent = hud
Instance.new("UICorner", carIcon).CornerRadius = UDim.new(0, 14)
for _, c in CORNERS do
	local b = Instance.new("Frame")
	b.Size = UDim2.fromOffset(10, 30)
	b.AnchorPoint = Vector2.new(0.5, 1)
	b.Position = UDim2.new(c:sub(2) == "L" and 0 or 1, c:sub(2) == "L" and -9 or 9, c:sub(1, 1) == "F" and 0.32 or 0.92, 0)
	b.BackgroundColor3 = Color3.fromRGB(40, 40, 46)
	b.Parent = carIcon
	local fill = Instance.new("Frame")
	fill.AnchorPoint = Vector2.new(0, 1)
	fill.Position = UDim2.fromScale(0, 1)
	fill.Size = UDim2.fromScale(1, 0.3)
	fill.BackgroundColor3 = Color3.fromRGB(40, 242, 242)
	fill.BorderSizePixel = 0
	fill.Parent = b
	bars[c] = fill
end
local help = label(hud, "", UDim2.fromOffset(12, 48), UDim2.fromOffset(150, 96), Color3.fromRGB(220, 220, 228), Enum.Font.Gotham)
help.TextWrapped = true
help.TextYAlignment = Enum.TextYAlignment.Top
local chargeBar = Instance.new("Frame")
chargeBar.Position = UDim2.new(0, 12, 1, -10)
chargeBar.Size = UDim2.fromOffset(0, 4)
chargeBar.BackgroundColor3 = Color3.fromRGB(255, 64, 166)
chargeBar.BorderSizePixel = 0
chargeBar.Parent = hud

local hopPop = label(gui, "", UDim2.new(0.5, -160, 0.18, 0), UDim2.fromOffset(320, 60), Color3.fromRGB(255, 214, 70), Enum.Font.GothamBlack, Enum.TextXAlignment.Center)
hopPop.TextStrokeTransparency = 0.3
hopPop.Visible = false

-- phone buttons
local touch = Instance.new("Frame")
touch.BackgroundTransparency = 1
touch.AnchorPoint = Vector2.new(1, 1)
touch.Position = UDim2.new(1, -20, 1, -170)
touch.Size = UDim2.fromOffset(230, 200)
touch.Visible = false
touch.Parent = gui
local function tbutton(text, pos, onDown, onUp)
	local b = Instance.new("TextButton")
	b.Size = UDim2.fromOffset(62, 46)
	b.Position = pos
	b.Text = text
	b.Font = Enum.Font.GothamBold
	b.TextScaled = true
	b.TextColor3 = Color3.new(1, 1, 1)
	b.BackgroundColor3 = Color3.fromRGB(30, 24, 40)
	b.BackgroundTransparency = 0.15
	b.Parent = touch
	Instance.new("UICorner", b).CornerRadius = UDim.new(0, 10)
	b.MouseButton1Down:Connect(onDown)
	if onUp then
		b.MouseButton1Up:Connect(onUp)
		b.MouseLeave:Connect(onUp)
	end
	return b
end
tbutton("FRONT", UDim2.fromOffset(84, 0), function() held.up = true end, function() held.up = false end)
tbutton("BACK", UDim2.fromOffset(84, 100), function() held.down = true end, function() held.down = false end)
tbutton("LEFT", UDim2.fromOffset(16, 50), function() held.left = true end, function() held.left = false end)
tbutton("RIGHT", UDim2.fromOffset(152, 50), function() held.right = true end, function() held.right = false end)
tbutton("HOP", UDim2.fromOffset(84, 50), function()
	if myCar and susp(myCar).hop > 0 then
		local s = st(myCar)
		s.charging, s.charge = true, 0
	end
end, function()
	if myCar then
		local s = st(myCar)
		if s.charging then
			s.charging = false
			hop(myCar, s, "front")
		end
	end
end)
tbutton("3-WHEEL", UDim2.fromOffset(16, 150), function()
	if myCar then
		local s = st(myCar)
		if s.threeWheel then
			s.threeWheel = nil
		elseif susp(myCar).threeWheel then
			s.threeWheel = "FL"
		end
	end
end)
tbutton("LAY", UDim2.fromOffset(84, 150), function()
	if myCar and susp(myCar).kit ~= "none" then
		local s = st(myCar)
		s.mode = s.mode == "ride" and "laid" or (s.mode == "laid" and "lifted" or "ride")
	end
end)
tbutton("EXIT", UDim2.fromOffset(152, 150), function()
	local _, hum = myDriveSeat()
	if hum then
		hum.Sit = false
		task.defer(function()
			hum.Jump = true
		end)
	end
end)

local function updateHud(car, s)
	local sp = susp(car)
	title.Text = sp.kit == "bags" and "AIR BAGS" or (sp.kit == "hyd" and "HYDRAULICS" or "STOCK")
	local mode = s.threeWheel and "Three-wheel" or (s.dance and "Dancing" or ({ ride = "Ride height", laid = "Laid frame", lifted = "Lifted" })[s.mode])
	local spd = math.floor(math.abs(s.fwdSpeed or 0) / 1.15 * 0.6818 + 0.5)
	modeL.Text = ("%s · %d mph"):format(mode, spd)
	local lines = { "Arrows: lift front/back/sides", "X: ride / laid / lifted", "F: get out" }
	if sp.hop > 0 then
		table.insert(lines, 1, "SPACE: hop (hold, let go)  B: body hop")
	end
	if sp.threeWheel then
		table.insert(lines, 3, "G: three-wheel")
	end
	if sp.dance then
		table.insert(lines, 4, "V: dance")
	end
	if sp.kit == "none" then
		lines = { "Stock springs.", "Get bags or hydraulics at Low & Slow Kustoms.", "F: get out" }
	end
	help.Text = table.concat(lines, "\n")
	for _, c in CORNERS do
		local span = math.max(sp.lift + sp.drop, 0.01)
		bars[c].Size = UDim2.fromScale(1, math.clamp((s.e[c] + sp.drop) / span, 0.05, 1))
	end
	chargeBar.Size = UDim2.fromOffset(226 * (s.charging and s.charge or 0), 4)
	carIcon.BackgroundColor3 = Config.Paint((function()
		local ok, look = pcall(HttpService.JSONDecode, HttpService, car:GetAttribute("Look") or "")
		return ok and type(look) == "table" and look.paint or "candy_sunset"
	end)()).color
end

---------------------------------------------------------------------------------------------------- hop pit meter
local function inZone(zone, pos)
	local lp = zone.CFrame:PointToObjectSpace(pos)
	local h = zone.Size / 2
	return math.abs(lp.X) <= h.X and math.abs(lp.Z) <= h.Z and lp.Y > -h.Y - 2 and lp.Y < h.Y + 30
end

local function hopMeter(car, s, dt)
	local ch = car.PrimaryPart
	local origin = ch.CFrame * ch.Origin.CFrame
	local zone
	for _, shop in workspace:GetChildren() do
		local z = shop.Name == "LowSlowKustoms" and shop:FindFirstChild("HopPitZone")
		if z and inZone(z, origin.Position) then
			zone = z
			break
		end
	end
	if not zone then
		s.hopPeak = nil
		return
	end
	local floorY = (zone.CFrame * CFrame.new(0, -zone.Size.Y / 2, 0)).Position.Y
	local bumper = origin:PointToWorldSpace(Vector3.new(Data.Car.FrontBumper[1], Data.Car.FrontBumper[2], Data.Car.FrontBumper[3]))
	local lift = bumper.Y - floorY - Data.Car.FrontBumper[2]
	if not (s.ground.FL or s.ground.FR) then
		s.frontAirT += dt
		s.hopPeak = math.max(s.hopPeak or 0, lift)
	elseif s.frontAirT > 0.15 and s.hopPeak and s.hopPeak > 0.4 then
		local inches = Config.Inches(s.hopPeak)
		local best = math.max(player:GetAttribute("BestHop") or 0, inches)
		hopPop.Text = ("%d in!   best %d in"):format(inches, best)
		hopPop.Visible = true
		task.delay(2.2, function()
			hopPop.Visible = false
		end)
		HopRE:FireServer(inches)
		s.frontAirT = 0
		s.hopPeak = 0
	else
		s.frontAirT = 0
	end
end

---------------------------------------------------------------------------------------------------- main loop
local camPrev = nil
RunService.PreSimulation:Connect(function(dt)
	dt = math.min(dt, 1 / 20)
	local seat = myDriveSeat()
	local car = seat and seat.Parent or nil
	if car ~= myCar then
		if myCar then
			unbind()
			local s = st(myCar)
			s.charging, s.dance = false, false
		end
		myCar = car
		if car then
			bind()
		end
		hud.Visible = car ~= nil
		touch.Visible = car ~= nil and UserInputService.TouchEnabled
	end
	local lr = workspace:FindFirstChild("Lowriders")
	if not lr then
		return
	end
	local camPos = camera.CFrame.Position
	for _, c in lr:GetChildren() do
		local ch = c.PrimaryPart
		if not (ch and c:GetAttribute("NCLowrider")) then
			continue
		end
		local s = st(c)
		if c:GetAttribute("Sim") == player.UserId then
			local input = { throttle = 0, steer = 0, park = c ~= myCar }
			if c == myCar then
				input.throttle = seat.ThrottleFloat
				input.steer = seat.SteerFloat
				updateTargets(c, s, dt)
			else
				-- parked: keep its last ride height, drop out of three-wheel and dancing
				s.threeWheel, s.dance, s.charging = nil, false, false
			end
			simulate(c, s, dt, input)
			if c == myCar then
				updateHud(c, s)
				hopMeter(c, s, dt)
			end
		elseif (ch.Position - camPos).Magnitude < 350 then
			-- someone else's car: follow their corner heights and pose the wheels from my own rays
			local f, r = c:GetAttribute("HydF") or Vector2.zero, c:GetAttribute("HydR") or Vector2.zero
			local tgt = { FL = f.X, FR = f.Y, RL = r.X, RR = r.Y }
			for _, k in CORNERS do
				s.e[k] = s.e[k] + (tgt[k] - s.e[k]) * math.min(1, dt * 12)
			end
			local origin = ch.CFrame * ch.Origin.CFrame
			local casts = castWheels(c, s, origin, rayParams(c), susp(c))
			local ds = c:FindFirstChild("DriveSeat")
			local steer = (ds and ds.SteerFloat or 0) * math.rad(24)
			poseWheels(c, s, origin, casts, steer, ch.AssemblyLinearVelocity:Dot(origin.LookVector), dt)
		end
	end
end)

---------------------------------------------------------------------------------------------------- the shop screen
local shopGui = Instance.new("ScreenGui")
shopGui.Name = "LowSlowKustoms"
shopGui.ResetOnSpawn = false
shopGui.Enabled = false
shopGui.Parent = player.PlayerGui

local panel = Instance.new("Frame")
panel.AnchorPoint = Vector2.new(1, 0.5)
panel.Position = UDim2.new(1, -16, 0.5, 0)
panel.Size = UDim2.new(0, 380, 0.86, 0)
panel.BackgroundColor3 = Color3.fromRGB(14, 12, 20)
panel.BackgroundTransparency = 0.08
panel.Parent = shopGui
Instance.new("UICorner", panel).CornerRadius = UDim.new(0, 14)
local ps = Instance.new("UIStroke", panel)
ps.Color = Color3.fromRGB(255, 64, 166)
ps.Thickness = 2
label(panel, "LOW & SLOW", UDim2.fromOffset(16, 10), UDim2.new(1, -32, 0, 30), Color3.fromRGB(255, 64, 166), Enum.Font.GothamBlack, Enum.TextXAlignment.Center)
label(panel, "KUSTOMS", UDim2.fromOffset(16, 40), UDim2.new(1, -32, 0, 18), Color3.fromRGB(40, 242, 242), Enum.Font.GothamBlack, Enum.TextXAlignment.Center)
local cashL = label(panel, "", UDim2.fromOffset(16, 62), UDim2.new(1, -32, 0, 16), Color3.fromRGB(150, 230, 140), Enum.Font.GothamMedium, Enum.TextXAlignment.Center)

local tabsBar = Instance.new("Frame")
tabsBar.Position = UDim2.fromOffset(10, 84)
tabsBar.Size = UDim2.new(1, -20, 0, 58)
tabsBar.BackgroundTransparency = 1
tabsBar.Parent = panel
local tl = Instance.new("UIGridLayout", tabsBar)
tl.CellSize = UDim2.new(0.25, -4, 0, 26)
tl.CellPadding = UDim2.fromOffset(4, 4)

local list = Instance.new("ScrollingFrame")
list.Position = UDim2.fromOffset(10, 148)
list.Size = UDim2.new(1, -20, 1, -238)
list.BackgroundTransparency = 1
list.ScrollBarThickness = 6
list.AutomaticCanvasSize = Enum.AutomaticSize.Y
list.CanvasSize = UDim2.new()
list.Parent = panel
local ll = Instance.new("UIListLayout", list)
ll.Padding = UDim.new(0, 6)
ll.SortOrder = Enum.SortOrder.LayoutOrder

local totalL = label(panel, "", UDim2.new(0, 16, 1, -84), UDim2.new(1, -32, 0, 20), Color3.fromRGB(255, 214, 70), Enum.Font.GothamBold, Enum.TextXAlignment.Center)
local function bigButton(text, pos, color)
	local b = Instance.new("TextButton")
	b.Position = pos
	b.Size = UDim2.new(0.5, -20, 0, 40)
	b.Text = text
	b.Font = Enum.Font.GothamBlack
	b.TextScaled = true
	b.TextColor3 = Color3.new(1, 1, 1)
	b.BackgroundColor3 = color
	b.Parent = panel
	Instance.new("UICorner", b).CornerRadius = UDim.new(0, 10)
	return b
end
local buyB = bigButton("BUY & APPLY", UDim2.new(0, 14, 1, -56), Color3.fromRGB(200, 30, 120))
local closeB = bigButton("CLOSE", UDim2.new(0.5, 6, 1, -56), Color3.fromRGB(50, 50, 60))

local draft, saved, shopOpen, activeTab = nil, nil, false, "Car"

local function myLowrider()
	local lr = workspace:FindFirstChild("Lowriders")
	if not lr then
		return nil
	end
	for _, c in lr:GetChildren() do
		if c:GetAttribute("Owner") == player.UserId then
			return c
		end
	end
	return nil
end

local function decode(attr)
	local ok, v = pcall(HttpService.JSONDecode, HttpService, attr or "")
	return ok and type(v) == "table" and v or nil
end

-- mirror of the server's price check (the server has the final say)
local LIST_FOR = { paint = "Paints", finish = "Finishes", art = "Art", wheels = "Wheels", susp = "Suspension", artColor = "Paints", stripeColor = "Paints" }
local function quote(look)
	local unlocked = decode(player:GetAttribute("LowriderUnlocked")) or {}
	local total = 0
	for key, l in LIST_FOR do
		if look[key] ~= saved[key] then
			local it = Config.ById[l][look[key]]
			local tag, price = l .. ":" .. look[key], it and it.price or 0
			if key == "artColor" or key == "stripeColor" then
				tag, price = key .. ":" .. look[key], Config.ArtColorPrice
			end
			if not unlocked[tag] and price > 0 then
				total += price
			end
		end
	end
	for key, price in { pinstripe = Config.PinstripePrice, whitewall = Config.WhitewallPrice, continental = Config.ContinentalPrice, trunkSetup = Config.TrunkSetupPrice } do
		if look[key] and not saved[key] and not unlocked["Extra:" .. key] then
			total += price
		end
	end
	return total
end

local render -- forward
local function preview()
	local car = myLowrider()
	if car and draft then
		Kit.ApplyLook(car, draft)
	end
	local total = draft and saved and quote(draft) or 0
	totalL.Text = total > 0 and ("Build total: $%d"):format(total) or "No changes yet"
end

local function row(text, sub, selected, onClick, swatch)
	local b = Instance.new("TextButton")
	b.Size = UDim2.new(1, -8, 0, 42)
	b.AutoButtonColor = true
	b.Text = ""
	b.BackgroundColor3 = selected and Color3.fromRGB(70, 20, 60) or Color3.fromRGB(30, 26, 40)
	b.LayoutOrder = #list:GetChildren()
	b.Parent = list
	Instance.new("UICorner", b).CornerRadius = UDim.new(0, 8)
	if selected then
		local s = Instance.new("UIStroke", b)
		s.Color = Color3.fromRGB(40, 242, 242)
		s.Thickness = 2
	end
	local x = 10
	if swatch then
		local sw = Instance.new("Frame")
		sw.Position = UDim2.fromOffset(8, 7)
		sw.Size = UDim2.fromOffset(28, 28)
		sw.BackgroundColor3 = swatch
		sw.Parent = b
		Instance.new("UICorner", sw).CornerRadius = UDim.new(1, 0)
		x = 44
	end
	label(b, text, UDim2.fromOffset(x, 4), UDim2.new(1, -x - 90, 0, 20), Color3.new(1, 1, 1), Enum.Font.GothamMedium)
	label(b, sub or "", UDim2.new(1, -88, 0, 11), UDim2.fromOffset(80, 18), Color3.fromRGB(255, 214, 70), Enum.Font.GothamBold, Enum.TextXAlignment.Right)
	b.MouseButton1Click:Connect(onClick)
	return b
end

local function header(text)
	local t = label(list, text, UDim2.new(), UDim2.new(1, -8, 0, 22), Color3.fromRGB(40, 242, 242), Enum.Font.GothamBlack)
	t.LayoutOrder = #list:GetChildren()
end

local function priceTag(price, tag)
	local unlocked = decode(player:GetAttribute("LowriderUnlocked")) or {}
	if price <= 0 or unlocked[tag] then
		return "owned"
	end
	return "$" .. price
end

local TABS = { "Car", "Paint", "Art", "Stripes", "Wheels", "Hydraulics", "Extras" }
render = function()
	for _, ch in list:GetChildren() do
		if ch:IsA("GuiObject") then
			ch:Destroy()
		end
	end
	for _, ch in tabsBar:GetChildren() do
		if ch:IsA("TextButton") then
			ch:Destroy()
		end
	end
	for _, name in TABS do
		local b = Instance.new("TextButton")
		b.Text = name
		b.Font = Enum.Font.GothamBold
		b.TextScaled = true
		b.TextColor3 = Color3.new(1, 1, 1)
		b.BackgroundColor3 = name == activeTab and Color3.fromRGB(200, 30, 120) or Color3.fromRGB(40, 34, 52)
		b.Parent = tabsBar
		Instance.new("UICorner", b).CornerRadius = UDim.new(0, 6)
		b.MouseButton1Click:Connect(function()
			activeTab = name
			render()
		end)
	end
	cashL.Text = (function()
		local ls = player:FindFirstChild("leaderstats")
		local c = ls and ls:FindFirstChild("Cash")
		return c and ("Cash: $%d"):format(c.Value) or ""
	end)()
	local owns = player:GetAttribute("OwnsLowrider")
	buyB.Visible = owns == true and draft ~= nil
	if activeTab == "Car" or not owns or not draft then
		header(Config.CarName)
		if not owns then
			row("Buy the " .. Config.CarName, "$" .. Config.CarPrice, false, function()
				local ok, msg = ShopRF:InvokeServer("buyCar")
				notify(msg)
				task.wait(0.5)
				render()
			end)
			label(list, "Long, low two-door hardtop. Comes on stock springs with Classic Wire 100-Spoke wheels. Customize everything here after.", UDim2.new(), UDim2.new(1, -8, 0, 60), Color3.fromRGB(200, 200, 210), Enum.Font.Gotham).TextWrapped = true
		else
			row("Bring my lowrider out", "", false, function()
				local ok, msg = ShopRF:InvokeServer("spawn")
				if not ok then
					notify(msg or "Couldn't get it out.")
				end
			end)
			label(list, "Park it on the paint turntable (left bay) to customize. Take it to the hop pit (right bay) to measure your hops.", UDim2.new(), UDim2.new(1, -8, 0, 60), Color3.fromRGB(200, 200, 210), Enum.Font.Gotham).TextWrapped = true
		end
		return
	end
	if activeTab == "Paint" then
		header("Candy paint")
		for _, p in Config.Paints do
			row(p.name, priceTag(p.price, "Paints:" .. p.id), draft.paint == p.id, function()
				draft.paint = p.id
				preview()
				render()
			end, p.color)
		end
		header("Finish")
		for _, f in Config.Finishes do
			row(f.name, priceTag(f.price, "Finishes:" .. f.id), draft.finish == f.id, function()
				draft.finish = f.id
				preview()
				render()
			end)
		end
	elseif activeTab == "Art" then
		header("Artwork")
		for _, a in Config.Art do
			row(a.name, priceTag(a.price, "Art:" .. a.id), draft.art == a.id, function()
				draft.art = a.id
				preview()
				render()
			end)
		end
		header("Art colour")
		for _, p in Config.Paints do
			row(p.name, priceTag(Config.ArtColorPrice, "artColor:" .. p.id), draft.artColor == p.id, function()
				draft.artColor = p.id
				preview()
				render()
			end, p.color)
		end
	elseif activeTab == "Stripes" then
		header("Pinstripes")
		row(draft.pinstripe and "Pinstripes: ON" or "Pinstripes: OFF", priceTag(Config.PinstripePrice, "Extra:pinstripe"), draft.pinstripe, function()
			draft.pinstripe = not draft.pinstripe
			preview()
			render()
		end)
		header("Stripe colour")
		for _, p in Config.Paints do
			row(p.name, priceTag(Config.ArtColorPrice, "stripeColor:" .. p.id), draft.stripeColor == p.id, function()
				draft.stripeColor = p.id
				draft.pinstripe = true
				preview()
				render()
			end, p.color)
		end
	elseif activeTab == "Wheels" then
		header("Classic Wire 100-Spoke")
		for _, w in Config.Wheels do
			local f = Config.WheelFinish[w.spokes]
			row(w.name, priceTag(w.price, "Wheels:" .. w.id), draft.wheels == w.id, function()
				draft.wheels = w.id
				preview()
				render()
			end, f and f[2] or Config.Paint(draft.paint).color)
		end
		header("Tyres")
		row(draft.whitewall and "Thin whitewalls: ON" or "Thin whitewalls: OFF", priceTag(Config.WhitewallPrice, "Extra:whitewall"), draft.whitewall, function()
			draft.whitewall = not draft.whitewall
			preview()
			render()
		end)
	elseif activeTab == "Hydraulics" then
		header("Suspension")
		for _, sp in Config.Suspension do
			row(sp.name, priceTag(sp.price, "Suspension:" .. sp.id), draft.susp == sp.id, function()
				draft.susp = sp.id
				preview()
				render()
			end)
		end
		local t = label(list, "Air bags lay the frame and lift smoothly. Hydraulics lift fast and hop. 3-pump adds three-wheel; the 4-pump competition setup hops highest and dances.", UDim2.new(), UDim2.new(1, -8, 0, 64), Color3.fromRGB(200, 200, 210), Enum.Font.Gotham)
		t.TextWrapped = true
		t.LayoutOrder = 999
	elseif activeTab == "Extras" then
		header("Extras")
		row(draft.continental and "Continental kit: ON" or "Continental kit: OFF", priceTag(Config.ContinentalPrice, "Extra:continental"), draft.continental, function()
			draft.continental = not draft.continental
			preview()
			render()
		end)
		row(draft.trunkSetup and "Chrome pump setup in the trunk: ON" or "Chrome pump setup in the trunk: OFF", priceTag(Config.TrunkSetupPrice, "Extra:trunkSetup"), draft.trunkSetup, function()
			draft.trunkSetup = not draft.trunkSetup
			preview()
			render()
		end)
	end
end

local orbit = 0
local orbitConn
local function closeShop()
	shopOpen = false
	shopGui.Enabled = false
	local car = myLowrider()
	if car then
		Kit.ApplyLook(car, decode(car:GetAttribute("Look")) or Config.StarterLook)
	end
	if orbitConn then
		orbitConn:Disconnect()
		orbitConn = nil
	end
	camera.CameraType = camPrev or Enum.CameraType.Custom
end

local function openShop(shop)
	saved = decode(player:GetAttribute("LowriderLook")) or table.clone(Config.StarterLook)
	draft = table.clone(saved)
	if not player:GetAttribute("OwnsLowrider") then
		draft = nil
	end
	activeTab = player:GetAttribute("OwnsLowrider") and "Paint" or "Car"
	local car = myLowrider()
	if draft and not car then
		activeTab = "Car"
	end
	shopOpen = true
	shopGui.Enabled = true
	render()
	preview()
	-- slow orbit around your car while you shop (if it's parked here)
	if car and shop and shop.PrimaryPart and (car.PrimaryPart.Position - shop.PrimaryPart.Position).Magnitude < Config.CustomizeRadius + 30 then
		camPrev = camera.CameraType
		camera.CameraType = Enum.CameraType.Scriptable
		orbitConn = RunService.RenderStepped:Connect(function(dt)
			if not car.Parent then
				closeShop()
				return
			end
			orbit += dt * 0.25
			local centre = Kit.Origin(car).Position + Vector3.new(0, 2.5, 0)
			local eye = centre + Vector3.new(math.cos(orbit) * 22, 7, math.sin(orbit) * 22)
			camera.CFrame = CFrame.lookAt(eye, centre)
		end)
	end
end

buyB.MouseButton1Click:Connect(function()
	if not draft then
		return
	end
	buyB.Text = "..."
	local ok, msg = ShopRF:InvokeServer("buyLook", draft)
	buyB.Text = "BUY & APPLY"
	notify(msg or (ok and "Done!" or "Couldn't do that."))
	if ok then
		saved = table.clone(draft)
	end
	render()
	preview()
end)
closeB.MouseButton1Click:Connect(closeShop)

UiRE.OnClientEvent:Connect(function(kind, shop)
	if kind == "open" then
		if shopOpen then
			closeShop()
		end
		openShop(shop)
	end
end)

player.CharacterRemoving:Connect(function()
	if shopOpen then
		closeShop()
	end
end)
