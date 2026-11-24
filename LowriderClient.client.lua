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
local Vehicles = require(RS:WaitForChild("NCVehicles"))
local Kit = require(RS:WaitForChild("NCLowriderKit"))
local Remotes = RS:WaitForChild("Remotes")
local ShopRF = Remotes:WaitForChild("LowriderShop")
local StateRE = Remotes:WaitForChild("LowriderState")
local UiRE = Remotes:WaitForChild("LowriderUI")
local HopRE = Remotes:WaitForChild("LowriderHop")
local WindowRE = Remotes:WaitForChild("VehicleWindow")

local player = Players.LocalPlayer
local camera = workspace.CurrentCamera
local CORNERS = { "FL", "FR", "RL", "RR" }

local function notify(text, color)
	local remotesNotify = Remotes:FindFirstChild("Notify")
	if remotesNotify and remotesNotify:IsA("BindableEvent") then
		remotesNotify:Fire(text, color)
	end
	pcall(function()
		game:GetService("StarterGui"):SetCore("SendNotification", { Title = "Low & Slow", Text = text, Duration = 4 })
	end)
end

---------------------------------------------------------------------------------------------------- per-car state + physics
-- the driving model lives in NCVehicleSim (shared with the server's AI cars)
local Sim = require(RS:WaitForChild("NCVehicleSim"))
local TyreFX = require(RS:WaitForChild("NCTyreFX"))
local CarLife = require(RS:WaitForChild("NCCarLife"))
local ControlRE = Remotes:WaitForChild("VehicleControl")
local st, susp, rayParams, castWheels, poseWheels = Sim.State, Sim.Susp, Sim.RayParams, Sim.Cast, Sim.Pose

local function simulate(car, s, dt, input)
	Sim.Step(car, s, dt, input)
	-- tell the server my corner heights (other players' wheels follow them)
	if os.clock() - s.lastSend > 0.1 then
		s.lastSend = os.clock()
		local sl = s.slip or {}
		StateRE:FireServer(car, s.e.FL, s.e.FR, s.e.RL, s.e.RR, s.threeWheel and ("3w" .. s.threeWheel) or (s.dance and "dance" or s.mode),
			Vector2.new(sl.FL or 0, sl.FR or 0), Vector2.new(sl.RL or 0, sl.RR or 0))
	end
end

---------------------------------------------------------------------------------------------------- controls
local held = { up = false, down = false, left = false, right = false, handbrake = false, burn = false }

-- the raw pedals (the seat's ThrottleFloat cancels to 0 when gas and brake are both down, which is a burnout)
local function trigger(key)
	local ok, list = pcall(UserInputService.GetGamepadState, UserInputService, Enum.UserInputType.Gamepad1)
	if ok then
		for _, io in list do
			if io.KeyCode == key then
				return io.Position.Z
			end
		end
	end
	return 0
end
local function pedals(seat)
	local th = seat.ThrottleFloat
	local gas = math.max(th, UserInputService:IsKeyDown(Enum.KeyCode.W) and 1 or 0, trigger(Enum.KeyCode.ButtonR2), held.burn and 1 or 0)
	local brk = math.max(-th, UserInputService:IsKeyDown(Enum.KeyCode.S) and 1 or 0, trigger(Enum.KeyCode.ButtonL2), held.burn and 1 or 0)
	return gas, brk
end
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
		local p = origin:PointToWorldSpace(Vector3.new(0, 1, s.REST.FL.Z))
		ch:ApplyImpulseAtPosition(origin.UpVector * mass * power * 0.62, p)
		s.e.FL, s.e.FR = sp.lift, sp.lift
	else
		ch:ApplyImpulse(origin.UpVector * mass * power * 0.55)
		for _, c in CORNERS do
			s.e[c] = sp.lift
		end
	end
	local snd = Config.Sounds.hyd_hop or ""
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
		if s.bike then
			s.wheelie = b or (si == Enum.UserInputState.Change and s.wheelie) -- bikes: hold Space to wheelie
			return
		end
		if susp(myCar).hop <= 0 then
			held.handbrake = b or (si == Enum.UserInputState.Change and held.handbrake) -- no hydraulics: Space is the handbrake
			return
		end
		if b then
			s.charging, s.charge = true, 0
		elseif si == Enum.UserInputState.End and s.charging then
			s.charging = false
			hop(myCar, s, "front")
		end
	end, Enum.KeyCode.Space, Enum.KeyCode.ButtonA)
	-- horn (hold), lights, indicators / hazards, siren (Coast Patrol)
	act("LR_Horn", function(b, si)
		if si == Enum.UserInputState.Begin or si == Enum.UserInputState.End or si == Enum.UserInputState.Cancel then
			ControlRE:FireServer("horn", si == Enum.UserInputState.Begin)
		end
	end, Enum.KeyCode.H, Enum.KeyCode.ButtonR1)
	act("LR_Lights", function(b)
		if b and myCar then
			local t = game:GetService("Lighting").ClockTime
			local cur = myCar:GetAttribute("Lights") or ((t > 18.3 or t < 6.4) and 1 or 0)
			local nxt = (cur + 1) % 3
			ControlRE:FireServer("lights", nxt)
			notify(({ [0] = "Lights off", "Headlights on", "High beams" })[nxt])
		end
	end, Enum.KeyCode.L)
	local function signal(which)
		return function(b)
			if b and myCar then
				local cur = myCar:GetAttribute("Signal") or ""
				ControlRE:FireServer("signal", cur == which and "" or which)
			end
		end
	end
	act("LR_SignalL", signal("L"), Enum.KeyCode.Z)
	act("LR_SignalR", signal("R"), Enum.KeyCode.C)
	act("LR_Hazards", signal("H"), Enum.KeyCode.Q)
	act("LR_Siren", function(b)
		if b and myCar and myCar:GetAttribute("Police") then
			ControlRE:FireServer("siren", ((myCar:GetAttribute("Siren") or 0) + 1) % 3)
		end
	end, Enum.KeyCode.E)
	act("LR_Handbrake", function(b, si)
		held.handbrake = b or (si == Enum.UserInputState.Change and held.handbrake)
	end, Enum.KeyCode.LeftShift, Enum.KeyCode.ButtonL1)
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
	ControlRE:FireServer("horn", false)
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
tbutton("HORN", UDim2.fromOffset(16, 0), function() ControlRE:FireServer("horn", true) end, function() ControlRE:FireServer("horn", false) end)
tbutton("LIGHTS", UDim2.fromOffset(152, 0), function()
	if myCar then
		local t = game:GetService("Lighting").ClockTime
		local cur = myCar:GetAttribute("Lights") or ((t > 18.3 or t < 6.4) and 1 or 0)
		ControlRE:FireServer("lights", (cur + 1) % 3)
	end
end)
tbutton("E-BRAKE", UDim2.fromOffset(152, 100), function() held.handbrake = true end, function() held.handbrake = false end)
tbutton("BURNOUT", UDim2.fromOffset(16, 100), function() held.burn = true end, function() held.burn = false end)
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
	local tricks = "W+S: burnout (+steer: donut)  SHIFT: handbrake / drift\nH: horn  L: lights  Z/C: indicators  Q: hazards" .. (car:GetAttribute("Police") and "  E: siren" or "")
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
	table.insert(lines, 1, tricks)
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
	local bumper = origin:PointToWorldSpace(s.bumper)
	local lift = bumper.Y - floorY - s.bumper.Y
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
-- the steering wheel follows the driver's steering, and the dash shows the gear: P parked / nobody driving,
-- R backing up, N stopped with no throttle, D driving, L creeping forward under 8 mph in a lowrider on the juice
local function dashLive(car, s, seat, fwd)
	local ds = seat or car:FindFirstChild("DriveSeat")
	local driven = ds and ds.Occupant ~= nil
	s.wheelSteer = (s.wheelSteer or 0) + (((ds and ds.SteerFloat) or 0) - (s.wheelSteer or 0)) * 0.25
	Kit.SetSteer(car, s.wheelSteer)
	local gear = "P"
	if driven then
		local th = ds.ThrottleFloat
		if fwd < -0.5 or (th < -0.05 and fwd < 1) then
			gear = "R"
		elseif math.abs(fwd) < 0.5 and math.abs(th) < 0.05 then
			gear = "N"
		elseif fwd < 6 and (s.mode == "lifted" or s.threeWheel) then
			gear = "L"
		else
			gear = "D"
		end
	end
	Kit.SetGear(car, gear)
end

-- every Kit car in the world: Low & Slow rides plus the city's parked, personal, garage and Coast Patrol cars
local function cars()
	local list = {}
	for _, f in Sim.Folders() do
		for _, c in f:GetChildren() do
			table.insert(list, c)
		end
	end
	return list
end

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
		if myCar then
			for _, pp in myCar:GetDescendants() do -- my own car's prompts come back once I'm out
				if pp:IsA("ProximityPrompt") and pp:GetAttribute("HiddenWhileDriving") then
					pp.Enabled = true
					pp:SetAttribute("HiddenWhileDriving", nil)
				end
			end
		end
		myCar = car
		if car then
			bind()
			-- while driving, the car's own door / trunk prompts stay out of the way (E is the siren, F gets out)
			for _, pp in car:GetDescendants() do
				if pp:IsA("ProximityPrompt") and pp.Enabled then
					pp.Enabled = false
					pp:SetAttribute("HiddenWhileDriving", true)
				end
			end
		end
		hud.Visible = car ~= nil
		touch.Visible = car ~= nil and UserInputService.TouchEnabled
	end
	local camPos = camera.CFrame.Position
	for _, c in cars() do
		local ch = c.PrimaryPart
		if not (ch and c:GetAttribute("NCLowrider")) or ch.Anchored then
			if ch and c:GetAttribute("NCLowrider") and (ch.Position - camera.CFrame.Position).Magnitude < 300 then
				TyreFX.Quiet(c)
				CarLife.Parked(c, st(c))
			end
			continue -- parked world cars sit anchored until someone gets in
		end
		local s = st(c)
		if c:GetAttribute("Sim") == player.UserId then
			local input = { throttle = 0, steer = 0, park = c ~= myCar }
			if c == myCar then
				input.throttle = seat.ThrottleFloat
				input.steer = seat.SteerFloat
				input.gas, input.brake = pedals(seat)
				input.handbrake = held.handbrake
				updateTargets(c, s, dt)
			else
				-- parked: keep its last ride height, drop out of three-wheel and dancing
				s.threeWheel, s.dance, s.charging = nil, false, false
			end
			local eBefore = (s.e.FL + s.e.FR + s.e.RL + s.e.RR) / 4
			simulate(c, s, dt, input)
			if (ch.Position - camPos).Magnitude < 350 then
				TyreFX.Update(c, s, s.slip or {}, dt)
				local sl = s.slip or {}
				local gas, brk = input.gas or math.max(input.throttle, 0), input.brake or math.max(-input.throttle, 0)
				CarLife.Update(c, s, {
					fwd = s.fwdSpeed or 0, top = s.D.TopSpeed, throttle = s.burnout and 1 or (gas > 0.05 and gas or -brk),
					burnout = s.burnout, braking = (brk > 0.3 and (s.fwdSpeed or 0) > 1) or input.handbrake == true,
					slip = math.max(sl.FL or 0, sl.FR or 0, sl.RL or 0, sl.RR or 0), spin = s.burnout and 1 or 0,
					hyd = ((s.e.FL + s.e.FR + s.e.RL + s.e.RR) / 4 - eBefore) / dt, inside = c == myCar,
				}, dt)
			else
				TyreFX.Quiet(c)
				CarLife.Quiet(c)
			end
			if c == myCar then
				updateHud(c, s)
				hopMeter(c, s, dt)
			end
			Kit.SetSpeed(c, math.abs(s.fwdSpeed or 0) / 1.15 * 0.6818) -- studs/s -> mph
			dashLive(c, s, c == myCar and seat or nil, s.fwdSpeed or 0)
		elseif (ch.Position - camPos).Magnitude >= 350 then
			TyreFX.Quiet(c)
			CarLife.Quiet(c)
		else
			-- someone else's car: follow their corner heights and pose the wheels from my own rays
			local f, r = c:GetAttribute("HydF") or Vector2.zero, c:GetAttribute("HydR") or Vector2.zero
			local tgt = { FL = f.X, FR = f.Y, RL = r.X, RR = r.Y }
			local eBefore = (s.e.FL + s.e.FR + s.e.RL + s.e.RR) / 4
			for _, k in CORNERS do
				s.e[k] = s.e[k] + (tgt[k] - s.e[k]) * math.min(1, dt * 12)
			end
			local origin = ch.CFrame * ch.Origin.CFrame
			local casts = castWheels(c, s, origin, rayParams(c), susp(c))
			local ds = c:FindFirstChild("DriveSeat")
			local steer = (ds and ds.SteerFloat or 0) * math.rad(24)
			local v = ch.AssemblyLinearVelocity:Dot(origin.LookVector)
			-- their tyres: smoke and marks from the slip the driver reports; a burnout spins the rear wheels in place
			local sf, sr = c:GetAttribute("SlipF") or Vector2.zero, c:GetAttribute("SlipR") or Vector2.zero
			local slip = { FL = sf.X, FR = sf.Y, RL = sr.X, RR = sr.Y }
			s.wspin = s.wspin or {}
			local burning = math.abs(v) < 10 and math.max(sr.X, sr.Y) > 0.6
			s.wspin.RL, s.wspin.RR = burning and 48 or nil, burning and 48 or nil
			s.vis = s.vis or {}
			for _, k in CORNERS do
				s.ground[k] = casts[k].grounded
			end
			poseWheels(c, s, origin, casts, steer, v, dt)
			TyreFX.Update(c, s, slip, dt)
			local th = ds and ds.ThrottleFloat or 0
			local hum = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
			CarLife.Update(c, s, {
				fwd = v, top = s.D.TopSpeed, throttle = burning and 1 or th, burnout = burning, braking = th < -0.05 and v > 1,
				slip = math.max(sf.X, sf.Y, sr.X, sr.Y), spin = burning and 1 or 0,
				hyd = ((s.e.FL + s.e.FR + s.e.RL + s.e.RR) / 4 - eBefore) / dt,
				inside = hum ~= nil and hum.SeatPart ~= nil and hum.SeatPart.Parent == c,
			}, dt)
			if (ch.Position - camPos).Magnitude < 40 then
				Kit.SetSpeed(c, math.abs(v) / 1.15 * 0.6818)
				dashLive(c, s, ds, v)
			end
		end
	end
end)

---------------------------------------------------------------------------------------------------- the tuning menu
-- Low & Slow Kustoms: categories -> mods -> options, built from Config.Mods. Everything you pick shows on your car
-- right away (only on your screen) with the camera on that part; BUY pays for the whole build at once.
local PINK, CYAN, GOLD = Color3.fromRGB(255, 64, 166), Color3.fromRGB(40, 242, 242), Color3.fromRGB(255, 214, 70)
local shopGui = Instance.new("ScreenGui")
shopGui.Name = "LowSlowKustoms"
shopGui.ResetOnSpawn = false
shopGui.Enabled = false
shopGui.IgnoreGuiInset = true
shopGui.Parent = player.PlayerGui

local panel = Instance.new("Frame")
panel.Position = UDim2.new(0, 18, 0, 60)
panel.Size = UDim2.new(0, 360, 1, -150)
panel.BackgroundColor3 = Color3.fromRGB(12, 10, 18)
panel.BackgroundTransparency = 0.12
panel.Parent = shopGui
Instance.new("UICorner", panel).CornerRadius = UDim.new(0, 12)
local sizeLimit = Instance.new("UISizeConstraint", panel)
sizeLimit.MaxSize = Vector2.new(360, 760)
local banner = Instance.new("Frame")
banner.Size = UDim2.new(1, 0, 0, 64)
banner.BackgroundColor3 = PINK
banner.Parent = panel
Instance.new("UICorner", banner).CornerRadius = UDim.new(0, 12)
local bg = Instance.new("UIGradient", banner)
bg.Color = ColorSequence.new(PINK, Color3.fromRGB(120, 30, 200))
label(banner, "LOW & SLOW KUSTOMS", UDim2.fromOffset(14, 8), UDim2.new(1, -28, 0, 30), Color3.new(1, 1, 1), Enum.Font.GothamBlack)
local crumbL = label(banner, "", UDim2.fromOffset(14, 38), UDim2.new(1, -28, 0, 18), Color3.fromRGB(255, 230, 250), Enum.Font.GothamBold)
local cashL = label(panel, "", UDim2.new(0, 14, 0, 70), UDim2.new(1, -28, 0, 18), Color3.fromRGB(150, 230, 140), Enum.Font.GothamBold, Enum.TextXAlignment.Right)
local backB = Instance.new("TextButton")
backB.Position = UDim2.fromOffset(12, 68)
backB.Size = UDim2.fromOffset(90, 22)
backB.Text = "< BACK"
backB.Font = Enum.Font.GothamBold
backB.TextScaled = true
backB.TextColor3 = CYAN
backB.BackgroundTransparency = 1
backB.Parent = panel

local list = Instance.new("ScrollingFrame")
list.Position = UDim2.fromOffset(10, 96)
list.Size = UDim2.new(1, -20, 1, -96 - 108)
list.BackgroundTransparency = 1
list.BorderSizePixel = 0
list.ScrollBarThickness = 5
list.ScrollBarImageColor3 = PINK
list.AutomaticCanvasSize = Enum.AutomaticSize.Y
list.CanvasSize = UDim2.new()
list.Parent = panel
local ll = Instance.new("UIListLayout", list)
ll.Padding = UDim.new(0, 4)
ll.SortOrder = Enum.SortOrder.LayoutOrder

-- cart bar
local cartL = label(panel, "", UDim2.new(0, 14, 1, -102), UDim2.new(1, -28, 0, 18), GOLD, Enum.Font.GothamBold)
local function bigButton(text, pos, size, color)
	local b = Instance.new("TextButton")
	b.Position = pos
	b.Size = size
	b.Text = text
	b.Font = Enum.Font.GothamBlack
	b.TextScaled = true
	b.TextColor3 = Color3.new(1, 1, 1)
	b.BackgroundColor3 = color
	b.Parent = panel
	Instance.new("UICorner", b).CornerRadius = UDim.new(0, 8)
	local pad = Instance.new("UIPadding", b)
	pad.PaddingTop, pad.PaddingBottom = UDim.new(0, 8), UDim.new(0, 8)
	return b
end
local buyB = bigButton("BUY BUILD", UDim2.new(0, 12, 1, -78), UDim2.new(0.5, -16, 0, 40), Color3.fromRGB(200, 30, 120))
local resetB = bigButton("UNDO ALL", UDim2.new(0.5, 4, 1, -78), UDim2.new(0.5, -16, 0, 40), Color3.fromRGB(50, 46, 64))
local closeB = bigButton("EXIT", UDim2.new(0, 12, 1, -32), UDim2.new(1, -24, 0, 24), Color3.fromRGB(34, 30, 44))
local hintL = label(shopGui, "Drag (or right stick) to turn the camera", UDim2.new(0.5, -200, 1, -36), UDim2.fromOffset(400, 20), Color3.fromRGB(230, 230, 236), Enum.Font.GothamMedium, Enum.TextXAlignment.Center)
hintL.TextStrokeTransparency = 0.5

local draft, saved, shopOpen = nil, nil, false
local view = { level = "cats", cat = nil, mod = nil }
local hoverValue = nil -- option the pointer is over (previewed without picking it)

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

-- the vehicle the menu is working on: the one I have out, else the last one I drove
local function curVid()
	local car = myLowrider()
	if car then
		return Vehicles.Of(car)
	end
	local a = player:GetAttribute("ActiveVehicle")
	return Vehicles.ById[a] and a or Vehicles.Default
end

local function garageOf(vid)
	local g = decode(player:GetAttribute("Garage")) or {}
	return type(g[vid]) == "table" and g[vid] or {}
end

local function buildsOf(vid)
	local b = decode(player:GetAttribute("LowriderBuilds")) or {}
	return type(b[vid]) == "table" and b[vid] or {}
end

local function modsNow()
	return Config.ModsFor(curVid())
end

local function unlockedNow()
	return garageOf(curVid()).unlocked or {}
end

-- saved look + draft for whichever vehicle is out now (nil draft = nothing to customize)
local function reloadDraft()
	local vid = curVid()
	local g = garageOf(vid)
	saved = Config.CleanLook(g.look, vid)
	draft = (g.owned and myLowrider()) and table.clone(saved) or nil
end

local function cashNow()
	local ls = player:FindFirstChild("leaderstats")
	local c = ls and ls:FindFirstChild("Cash")
	return c and c.Value or 0
end

local function priceText(key, value)
	local price = Config.PriceOf(key, value)
	if saved and saved[key] == value then
		return "ON", CYAN
	end
	if price <= 0 or unlockedNow()[key .. "=" .. value] then
		return "owned", Color3.fromRGB(150, 230, 140)
	end
	return "$" .. price, GOLD
end

local render -- forward
local function preview()
	local car = myLowrider()
	if car and draft then
		local look = draft
		if hoverValue and view.mod then
			look = table.clone(draft)
			look[view.mod.key] = hoverValue
		end
		Kit.ApplyLook(car, look)
	end
	if draft and saved then
		local total, items = Config.Quote(saved, draft, unlockedNow())
		local n = 0
		for key in Config.ModByKey do
			if draft[key] ~= saved[key] then
				n += 1
			end
		end
		cartL.Text = n == 0 and "No changes yet" or ("%d change%s   ·   $%d"):format(n, n == 1 and "" or "s", total)
		cartL.TextColor3 = total > cashNow() and Color3.fromRGB(255, 90, 90) or GOLD
	end
	cashL.Text = ("$%d"):format(cashNow())
end

local order = 0
local function nextOrder()
	order += 1
	return order
end

local function row(text, sub, subColor, selected, onClick, swatch, onHover)
	local b = Instance.new("TextButton")
	b.Size = UDim2.new(1, -6, 0, 38)
	b.AutoButtonColor = false
	b.Text = ""
	b.BackgroundColor3 = selected and Color3.fromRGB(80, 22, 70) or Color3.fromRGB(28, 24, 38)
	b.LayoutOrder = nextOrder()
	b.Selectable = true
	b.Parent = list
	Instance.new("UICorner", b).CornerRadius = UDim.new(0, 6)
	local stroke = Instance.new("UIStroke", b)
	stroke.Color = CYAN
	stroke.Thickness = selected and 2 or 0
	local x = 12
	if swatch then
		local sw = Instance.new("Frame")
		sw.Position = UDim2.fromOffset(8, 7)
		sw.Size = UDim2.fromOffset(24, 24)
		sw.BackgroundColor3 = swatch
		sw.Parent = b
		Instance.new("UICorner", sw).CornerRadius = UDim.new(1, 0)
		Instance.new("UIStroke", sw).Color = Color3.fromRGB(255, 255, 255)
		x = 40
	end
	label(b, text, UDim2.fromOffset(x, 0), UDim2.new(1, -x - 84, 1, 0), Color3.new(1, 1, 1), Enum.Font.GothamMedium)
	if sub then
		label(b, sub, UDim2.new(1, -86, 0, 0), UDim2.new(0, 76, 1, 0), subColor or GOLD, Enum.Font.GothamBold, Enum.TextXAlignment.Right)
	end
	local function hi(on)
		b.BackgroundColor3 = on and Color3.fromRGB(60, 40, 80) or (selected and Color3.fromRGB(80, 22, 70) or Color3.fromRGB(28, 24, 38))
	end
	b.MouseEnter:Connect(function()
		hi(true)
		if onHover then
			onHover(true)
		end
	end)
	b.MouseLeave:Connect(function()
		hi(false)
		if onHover then
			onHover(false)
		end
	end)
	b.SelectionGained:Connect(function()
		hi(true)
		if onHover then
			onHover(true)
		end
	end)
	b.SelectionLost:Connect(function()
		hi(false)
	end)
	b.MouseButton1Click:Connect(onClick)
	return b
end

local function note(text, h)
	local t = label(list, text, UDim2.new(), UDim2.new(1, -6, 0, h or 44), Color3.fromRGB(200, 200, 212), Enum.Font.Gotham)
	t.TextWrapped = true
	t.LayoutOrder = nextOrder()
	return t
end

-- current value's display name
local function valueName(m, v)
	local o = Config.OptionOf[m.key][v]
	if o then
		return o.name
	end
	return Config.CustomColor(v) and "Custom" or "?"
end

---------------------------------------------------------------- custom colour picker (hue bar + saturation/value square + hex)
local picker = Instance.new("Frame")
picker.Size = UDim2.new(1, -6, 0, 196)
picker.BackgroundColor3 = Color3.fromRGB(24, 20, 34)
Instance.new("UICorner", picker).CornerRadius = UDim.new(0, 6)
local sv = Instance.new("ImageButton")
sv.Position = UDim2.fromOffset(10, 10)
sv.Size = UDim2.new(1, -70, 0, 140)
sv.AutoButtonColor = false
sv.BackgroundColor3 = Color3.new(1, 0, 0)
sv.Parent = picker
local white = Instance.new("Frame", sv)
white.Size = UDim2.fromScale(1, 1)
white.BackgroundColor3 = Color3.new(1, 1, 1)
local wg = Instance.new("UIGradient", white)
wg.Transparency = NumberSequence.new(0, 1)
local black = Instance.new("Frame", sv)
black.Size = UDim2.fromScale(1, 1)
black.BackgroundColor3 = Color3.new(0, 0, 0)
local bgr = Instance.new("UIGradient", black)
bgr.Rotation = 90
bgr.Transparency = NumberSequence.new(1, 0)
local svDot = Instance.new("Frame", sv)
svDot.AnchorPoint = Vector2.new(0.5, 0.5)
svDot.Size = UDim2.fromOffset(12, 12)
svDot.ZIndex = 3
Instance.new("UICorner", svDot).CornerRadius = UDim.new(1, 0)
Instance.new("UIStroke", svDot).Color = Color3.new(1, 1, 1)
local hue = Instance.new("ImageButton")
hue.Position = UDim2.new(1, -50, 0, 10)
hue.Size = UDim2.fromOffset(40, 140)
hue.AutoButtonColor = false
hue.BackgroundColor3 = Color3.new(1, 1, 1)
hue.Parent = picker
local hg = Instance.new("UIGradient", hue)
hg.Rotation = 90
local keys = {}
for i = 0, 6 do
	table.insert(keys, ColorSequenceKeypoint.new(i / 6, Color3.fromHSV((i / 6) % 1, 1, 1)))
end
hg.Color = ColorSequence.new(keys)
local hueBar = Instance.new("Frame", hue)
hueBar.AnchorPoint = Vector2.new(0, 0.5)
hueBar.Size = UDim2.new(1, 0, 0, 3)
hueBar.BackgroundColor3 = Color3.new(1, 1, 1)
local hexBox = Instance.new("TextBox")
hexBox.Position = UDim2.new(0, 10, 0, 158)
hexBox.Size = UDim2.new(0.5, -14, 0, 28)
hexBox.Font = Enum.Font.Code
hexBox.TextScaled = true
hexBox.TextColor3 = Color3.new(1, 1, 1)
hexBox.BackgroundColor3 = Color3.fromRGB(40, 36, 52)
hexBox.ClearTextOnFocus = false
hexBox.Parent = picker
local useB = Instance.new("TextButton")
useB.Position = UDim2.new(0.5, 4, 0, 158)
useB.Size = UDim2.new(0.5, -14, 0, 28)
useB.Font = Enum.Font.GothamBlack
useB.TextScaled = true
useB.TextColor3 = Color3.new(1, 1, 1)
useB.BackgroundColor3 = Color3.fromRGB(200, 30, 120)
useB.Parent = picker
Instance.new("UICorner", useB).CornerRadius = UDim.new(0, 6)
local H, S, V = 0, 1, 1
local dragging = nil

local function pickerColor()
	return Color3.fromHSV(H, S, V)
end

local function refreshPicker(live)
	sv.BackgroundColor3 = Color3.fromHSV(H, 1, 1)
	svDot.Position = UDim2.fromScale(S, 1 - V)
	svDot.BackgroundColor3 = pickerColor()
	hueBar.Position = UDim2.fromScale(0, H)
	hexBox.Text = "#" .. pickerColor():ToHex():upper()
	if live and view.mod then
		hoverValue = Config.ToCustom(pickerColor())
		preview()
	end
end

local function dragAt(pos)
	if dragging == "sv" then
		S = math.clamp((pos.X - sv.AbsolutePosition.X) / sv.AbsoluteSize.X, 0, 1)
		V = 1 - math.clamp((pos.Y - sv.AbsolutePosition.Y) / sv.AbsoluteSize.Y, 0, 1)
	elseif dragging == "hue" then
		H = math.clamp((pos.Y - hue.AbsolutePosition.Y) / hue.AbsoluteSize.Y, 0, 0.999)
	end
	refreshPicker(true)
end

for which, btn in { sv = sv, hue = hue } do
	btn.InputBegan:Connect(function(io)
		if io.UserInputType == Enum.UserInputType.MouseButton1 or io.UserInputType == Enum.UserInputType.Touch then
			dragging = which
			dragAt(io.Position)
		end
	end)
end
-- R: roll your window up -> half way -> down (driver: Shift+R does every window). Works in any seat of a Kit vehicle.
UserInputService.InputBegan:Connect(function(io, processed)
	if processed or (io.KeyCode ~= Enum.KeyCode.R and io.KeyCode ~= Enum.KeyCode.DPadLeft) then
		return
	end
	local hum = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
	local seat = hum and hum.SeatPart
	if not (seat and seat.Parent and seat.Parent:GetAttribute("NCLowrider")) then
		return
	end
	if io.KeyCode == Enum.KeyCode.DPadLeft and seat.Name == "DriveSeat" then
		return -- the driver's d-pad steers the hydraulics
	end
	local shift = UserInputService:IsKeyDown(Enum.KeyCode.LeftShift) or UserInputService:IsKeyDown(Enum.KeyCode.RightShift)
	WindowRE:FireServer(shift)
end)

UserInputService.InputChanged:Connect(function(io)
	if dragging and (io.UserInputType == Enum.UserInputType.MouseMovement or io.UserInputType == Enum.UserInputType.Touch) then
		dragAt(io.Position)
	end
end)
UserInputService.InputEnded:Connect(function(io)
	if io.UserInputType == Enum.UserInputType.MouseButton1 or io.UserInputType == Enum.UserInputType.Touch then
		dragging = nil
	end
end)
hexBox.FocusLost:Connect(function()
	local hex = hexBox.Text:gsub("#", ""):match("^%x%x%x%x%x%x$")
	if hex then
		H, S, V = Color3.fromHex(hex):ToHSV()
	end
	refreshPicker(true)
end)
useB.MouseButton1Click:Connect(function()
	if view.mod and draft then
		draft[view.mod.key] = Config.ToCustom(pickerColor())
		hoverValue = nil
		preview()
		render()
	end
end)

---------------------------------------------------------------- screens
render = function()
	for _, ch in list:GetChildren() do
		if ch:IsA("GuiObject") and ch ~= picker then
			ch:Destroy()
		end
	end
	picker.Parent = nil
	order = 0
	preview()
	local owns = player:GetAttribute("OwnsLowrider")
	local car = myLowrider()
	buyB.Visible, resetB.Visible, cartL.Visible = draft ~= nil, draft ~= nil, draft ~= nil
	backB.Visible = view.level ~= "cats"
	if view.level == "garage" or not owns or not draft or not car then
		crumbL.Text = "Garage"
		backB.Visible = draft ~= nil and car ~= nil
		buyB.Visible, resetB.Visible, cartL.Visible = false, false, false
		local out = car and Vehicles.Of(car)
		for _, veh in Vehicles.Available() do
			local g = garageOf(veh.id)
			local sub, col
			if out == veh.id then
				sub, col = "OUT", CYAN
			elseif g.owned then
				sub, col = "owned", Color3.fromRGB(150, 230, 140)
			else
				sub, col = "$" .. veh.price, GOLD
			end
			row(veh.name, sub, col, out == veh.id, function()
				if out == veh.id then
					return
				end
				local ok, msg = ShopRF:InvokeServer(g.owned and "spawn" or "buyCar", veh.id)
				if msg then
					notify(msg)
				elseif not ok then
					notify("Couldn't get it out.")
				end
				task.wait(0.6)
				reloadDraft()
				view = { level = draft and "cats" or "garage" }
				render()
			end)
		end
		note("Every ride here takes the same full customization: body kit, wheels, interior, lights, suspension. Park it on the turntable (left bay) to customize. The hop pit (right bay) measures your hops.", 74)
		return
	end
	if view.level == "cats" then
		crumbL.Text = Vehicles.Get(curVid()).name .. "  >  pick a category"
		row("Garage (buy or switch rides)", nil, nil, false, function()
			view.level = "garage"
			render()
		end)
		for _, cat in modsNow().cats do
			local changed = 0
			for _, m in cat.mods do
				if draft[m.key] ~= saved[m.key] then
					changed += 1
				end
			end
			row(cat.name, changed > 0 and (changed .. " changed") or ("%d mods"):format(#cat.mods), changed > 0 and GOLD or Color3.fromRGB(160, 160, 176), false, function()
				view.level, view.cat = "mods", cat
				render()
			end)
		end
		-- saved designs + quick builds
		local hdr = label(list, "MY BUILDS", UDim2.new(), UDim2.new(1, -6, 0, 24), CYAN, Enum.Font.GothamBlack)
		hdr.LayoutOrder = nextOrder()
		local builds = buildsOf(curVid())
		for i = 1, Config.BuildSlots do
			local b = builds[i]
			row(("Build %d"):format(i), type(b) == "table" and "saved" or "empty", type(b) == "table" and CYAN or Color3.fromRGB(160, 160, 176), false, function()
				view.level, view.slot = "build", i
				render()
			end, type(b) == "table" and Config.ColorOf("paint", b.paint) or nil)
		end
		row("Surprise me (random build)", "preview", Color3.fromRGB(160, 160, 176), false, function()
			for key, m in modsNow().byKey do
				if key ~= "susp" and key ~= "engine" then
					draft[key] = m.options[math.random(1, #m.options)].id
				end
			end
			render()
		end)
		row("Back to stock", "preview", Color3.fromRGB(160, 160, 176), false, function()
			for key, m in modsNow().byKey do
				if key ~= "susp" and key ~= "engine" then
					draft[key] = m.default
				end
			end
			render()
		end)
	elseif view.level == "build" then
		local i = view.slot
		crumbL.Text = ("My builds  >  Build %d"):format(i)
		local vid = curVid()
		local builds = buildsOf(vid)
		local b = type(builds[i]) == "table" and builds[i] or nil
		if b then
			local cost = Config.Quote(saved, Config.CleanLook(b, vid), unlockedNow())
			row("Load it (preview + cart)", cost > 0 and ("$" .. cost) or "owned", cost > 0 and GOLD or Color3.fromRGB(150, 230, 140), false, function()
				draft = Config.CleanLook(b, vid)
				view.level, view.slot = "cats", nil
				render()
			end, Config.ColorOf("paint", b.paint))
		end
		row(b and "Save what's on my car now over it" or "Save what's on my car now", nil, nil, false, function()
			local ok, msg = ShopRF:InvokeServer("saveBuild", { slot = i, vehicle = vid, look = draft })
			notify(msg or (ok and "Saved." or "Couldn't save."))
			task.wait(0.2)
			render()
		end)
		if b then
			row("Clear this slot", nil, nil, false, function()
				local ok, msg = ShopRF:InvokeServer("saveBuild", { slot = i, vehicle = vid })
				notify(msg or "")
				task.wait(0.2)
				render()
			end)
		end
		note("A build saves the whole design (everything in the menu, even parts you haven't bought yet). Loading one puts it in your cart.", 56)
	elseif view.level == "mods" then
		crumbL.Text = view.cat.name
		for _, m in view.cat.mods do
			local v = draft[m.key]
			local changed = v ~= saved[m.key]
			row(m.name, valueName(m, v), changed and GOLD or CYAN, changed, function()
				view.level, view.mod = "opts", m
				hoverValue = nil
				render()
			end, Config.ColorOf(m.key, v))
		end
		if view.cat.id == "vinyls" then
			local missing = false
			local vid = curVid()
			local vd = Vehicles.Data(vid)
			for liv, panels in (vd and vd.Car.Vinyls or {}) do
				if panels[1] and Kit.VinylId(liv, panels[1], vid) == "" then
					missing = true
				end
			end
			note(missing and "Some vinyl images aren't uploaded yet (import this ride's Vinyls GLB in Studio and run NCLowriderKit.Prepare on it)." or "Printed right on the paint. Clear parts show your candy colour through, so every vinyl works with every paint.", 60)
		elseif view.cat.id == "hydraulics" then
			note("Air bags lay the frame and lift smoothly. Hydraulics lift fast and hop. 3-pump adds three-wheel; the 4-pump competition setup hops highest and dances.", 60)
		end
	else
		local m = view.mod
		crumbL.Text = view.cat.name .. "  >  " .. m.name
		for _, o in m.options do
			local t, col = priceText(m.key, o.id)
			row(o.name, t, col, draft[m.key] == o.id, function()
				draft[m.key] = o.id
				hoverValue = nil
				render()
			end, o.color, function(on)
				hoverValue = on and o.id or nil
				preview()
			end)
		end
		if m.custom then
			local cur = Config.CustomColor(draft[m.key])
			if cur then
				row("Custom colour", priceText(m.key, draft[m.key]), CYAN, true, function() end, cur)
			end
			local hdr = label(list, ("CUSTOM COLOUR   ·   $%d"):format(m.custom), UDim2.new(), UDim2.new(1, -6, 0, 20), CYAN, Enum.Font.GothamBlack)
			hdr.LayoutOrder = nextOrder()
			local base = cur or Config.ColorOf(m.key, draft[m.key]) or Color3.new(1, 0, 0)
			H, S, V = base:ToHSV()
			useB.Text = "USE THIS COLOUR"
			picker.LayoutOrder = nextOrder()
			picker.Parent = list
			refreshPicker(false)
		end
	end
end

---------------------------------------------------------------- camera: each category looks at its part
local CAMS = {
	front34 = { Vector3.new(14, 6, -20), Vector3.new(0, 2, -2) },
	side = { Vector3.new(24, 4.5, 0), Vector3.new(0, 2.2, 0) },
	front = { Vector3.new(0, 4.5, -19), Vector3.new(0, 2.2, -8) },
	rear34 = { Vector3.new(-13, 7, 21), Vector3.new(0, 2, 5) },
	interior = { Vector3.new(-6.8, 4.6, 0.8), Vector3.new(0.6, 2.4, -1.2) },
}
-- the wheel close-up depends on where this vehicle's front wheel sits
local function wheelCam(car)
	local vd = Vehicles.Data(Vehicles.Of(car)) or Vehicles.Data(Vehicles.Default)
	local fl = vd.Car.Wheels.FL
	local w = Vector3.new(fl[1], fl[2], fl[3])
	local out = w.X >= 0 and 1 or -1
	return { w + Vector3.new(out * 7, 1.2, -2.8), w }
end
local CAM_OF_MOD = { -- a few mods look somewhere else than their category
	part_RearBumper = "rear34", part_Spoiler = "rear34", part_Exhaust = "rear34", part_Continental = "rear34", part_Skirts = "side",
	part_Mirrors = "front34", part_Visor = "front34", part_Glow = "side", taillights = "rear34", part_Trunk = "rear34",
	fin_Trunk = "rear34", part_Plaque = "rear34", part_Taillights = "rear34", part_SideTrim = "side", part_Audio = "rear34", plaque = "rear34", part_Dice = "interior", col_Fur = "interior",
}
local camConn, camEye, camTgt, yaw = nil, nil, nil, 0
local camPrevType

local function camKey()
	if view.mod and CAM_OF_MOD[view.mod.key] then
		return CAM_OF_MOD[view.mod.key]
	end
	return view.cat and view.cat.cam or "front34"
end

local dragCam = false
UserInputService.InputBegan:Connect(function(io, gp)
	if shopOpen and not gp and (io.UserInputType == Enum.UserInputType.MouseButton1 or io.UserInputType == Enum.UserInputType.MouseButton2 or io.UserInputType == Enum.UserInputType.Touch) then
		dragCam = true
	end
end)
UserInputService.InputEnded:Connect(function(io)
	if io.UserInputType == Enum.UserInputType.MouseButton1 or io.UserInputType == Enum.UserInputType.MouseButton2 or io.UserInputType == Enum.UserInputType.Touch then
		dragCam = false
	end
end)
UserInputService.InputChanged:Connect(function(io, gp)
	if not shopOpen then
		return
	end
	if dragCam and (io.UserInputType == Enum.UserInputType.MouseMovement or io.UserInputType == Enum.UserInputType.Touch) then
		yaw -= io.Delta.X * 0.008
	elseif io.KeyCode == Enum.KeyCode.Thumbstick2 and math.abs(io.Position.X) > 0.2 then
		yaw -= io.Position.X * 0.05
	end
end)

local function closeShop()
	shopOpen = false
	shopGui.Enabled = false
	hoverValue = nil
	local car = myLowrider()
	if car then
		Kit.ApplyLook(car, decode(car:GetAttribute("Look")) or Config.StarterLook)
	end
	if camConn then
		camConn:Disconnect()
		camConn = nil
	end
	camera.CameraType = camPrevType or Enum.CameraType.Custom
end

local function openShop(shop)
	reloadDraft()
	view = { level = draft and "cats" or "garage" }
	yaw = 0
	local car = myLowrider()
	shopOpen = true
	shopGui.Enabled = true
	render()
	if car and shop and shop.PrimaryPart and (car.PrimaryPart.Position - shop.PrimaryPart.Position).Magnitude < Config.CustomizeRadius + 30 then
		camPrevType = camera.CameraType
		camera.CameraType = Enum.CameraType.Scriptable
		camEye, camTgt = nil, nil
		camConn = RunService.RenderStepped:Connect(function(dt)
			if not car.Parent then
				closeShop()
				return
			end
			local o = Kit.Origin(car)
			local key = camKey()
			local preset = key == "wheel" and wheelCam(car) or CAMS[key] or CAMS.front34
			local tgtL = preset[2]
			local eyeL = tgtL + CFrame.Angles(0, yaw, 0):VectorToWorldSpace(preset[1] - tgtL)
			local eye, tgt = o:PointToWorldSpace(eyeL), o:PointToWorldSpace(tgtL)
			local a = math.min(1, dt * 5)
			camEye = camEye and camEye:Lerp(eye, a) or eye
			camTgt = camTgt and camTgt:Lerp(tgt, a) or tgt
			camera.CFrame = CFrame.lookAt(camEye, camTgt)
		end)
	end
end

backB.MouseButton1Click:Connect(function()
	hoverValue = nil
	if view.level == "opts" then
		view.level, view.mod = "mods", nil
	else
		view.level, view.cat, view.slot = "cats", nil, nil
	end
	yaw = 0
	render()
end)
buyB.MouseButton1Click:Connect(function()
	if not draft then
		return
	end
	buyB.Text = "..."
	local ok, msg = ShopRF:InvokeServer("buyLook", draft)
	buyB.Text = "BUY BUILD"
	notify(msg or (ok and "Done!" or "Couldn't do that."))
	if ok then
		saved = table.clone(draft)
		task.delay(1.5, function() -- the server's parts have replicated by now: drop my local preview copies
			if shopOpen then
				preview()
			end
		end)
	end
	render()
end)
resetB.MouseButton1Click:Connect(function()
	if saved then
		draft = table.clone(saved)
		hoverValue = nil
		render()
	end
end)
closeB.MouseButton1Click:Connect(closeShop)
-- gamepad B / Backspace goes back a level
ContextActionService:BindActionAtPriority("NCShopBack", function(_, stateIn)
	if stateIn ~= Enum.UserInputState.Begin or not shopOpen then
		return Enum.ContextActionResult.Pass
	end
	if view.level == "cats" then
		closeShop()
	else
		hoverValue = nil
		if view.level == "opts" then
			view.level, view.mod = "mods", nil
		else
			view.level, view.cat, view.slot = "cats", nil, nil
		end
		render()
	end
	return Enum.ContextActionResult.Sink
end, false, 4000, Enum.KeyCode.ButtonB, Enum.KeyCode.Backspace)

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

-- ================================================================ seated pose
-- The stock sit animation leaves the shins hanging straight down, and car seats sit low over the floor, so feet
-- went through it. Anyone seated in a kit car (not bikes) gets a driving pose each frame, on top of the sit
-- animation: body lifted a little, thighs up and splayed round the steering wheel, shins reaching forward to the
-- footwell, and the driver's hands toward the wheel. Works on Motor6D and AnimationConstraint joints. Tunables:
-- (values tuned live on the K2 with Male_Average, place v126)
local SEAT_POSE = {
	lift = 0.1, -- studs the body rises off the seat
	hip = 96, -- thigh, degrees forward from hanging straight down
	shin = 70, -- shin, degrees forward of straight down
	splay = 8, -- knees apart (degrees)
	shoulder = 10, -- driver's arms forward
	shoulderIn = 28, -- driver's arms inward
	elbow = 90,
}
do
	local JOINTS = { "Root", "RightHip", "LeftHip", "RightKnee", "LeftKnee", "RightAnkle", "LeftAnkle", "RightShoulder",
		"LeftShoulder", "RightElbow", "LeftElbow", "RightWrist", "LeftWrist" }
	local WANT = {}
	for _, n in JOINTS do
		WANT[n] = true
	end
	local cache = {} -- [character] = { [jointName] = joint }
	local function jointsOf(char)
		local e = cache[char]
		if e and e.RightHip and e.RightHip.Parent then
			return e
		end
		e = {}
		for _, d in char:GetDescendants() do
			if WANT[d.Name] and (d:IsA("Motor6D") or d:IsA("AnimationConstraint")) and not e[d.Name] then
				e[d.Name] = d
			end
		end
		if not cache[char] then
			char.Destroying:Once(function()
				cache[char] = nil
			end)
		end
		cache[char] = e
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
	-- the child's rotation q relative to its rest pose (parent's axes), plus an optional offset
	local function setJoint(j, q, off)
		if not j then
			return
		end
		local c0, c1 = frames(j)
		if not c0 then
			return
		end
		local t = c0:Inverse() * q * c1
		j.Transform = off and (CFrame.new(c0:Inverse() * off) * t) or t
	end
	local rad, A = math.rad, CFrame.Angles
	local function pivot(j)
		if j:IsA("Motor6D") then
			return j.Part0 and (j.Part0.CFrame * j.C0).Position
		end
		return j.Attachment0 and j.Attachment0.WorldPosition
	end
	-- two-bone reach: puts the hand (palm about 0.2 past the wrist) on a world point, elbow dropping down and out.
	-- Rotations are the limb's own axes in its parent's frame (rest: arm hanging along -Y), as setJoint expects.
	local function reach(shoulder, elbow, wrist, target, side)
		if not (shoulder and elbow and wrist) then
			return false
		end
		local torso = shoulder:IsA("Motor6D") and shoulder.Part0
			or (shoulder.Attachment0 and shoulder.Attachment0:FindFirstAncestorWhichIsA("BasePart"))
		local ps, pe, pw = pivot(shoulder), pivot(elbow), pivot(wrist)
		if not (torso and ps and pe and pw) then
			return false
		end
		local la, lf = (pe - ps).Magnitude, (pw - pe).Magnitude + 0.06
		local v = torso.CFrame:VectorToObjectSpace(target - ps)
		local d = math.clamp(v.Magnitude, math.abs(la - lf) + 0.05, la + lf - 0.02)
		local dir = v.Unit
		-- the elbow hangs below the line and a little outward
		local hang = (Vector3.new(side * 0.35, -1, 0) - dir * dir:Dot(Vector3.new(side * 0.35, -1, 0))).Unit
		local a = math.acos(math.clamp((la * la + d * d - lf * lf) / (2 * la * d), -1, 1))
		local u = (dir * math.cos(a) + hang * math.sin(a)).Unit -- upper arm direction
		local w = dir - u * dir:Dot(u)
		if w.Magnitude < 1e-3 then
			w = Vector3.new(0, 0, -1)
		end
		local Yl, Zl = -u, -w.Unit
		local Xl = Yl:Cross(Zl)
		setJoint(shoulder, CFrame.fromMatrix(Vector3.zero, Xl, Yl, Zl))
		local bend = math.pi - math.acos(math.clamp((la * la + lf * lf - d * d) / (2 * la * lf), -1, 1))
		setJoint(elbow, A(bend, 0, 0))
		return true
	end
	local function wheelGrips(car)
		local vd = Vehicles.Data(car:GetAttribute("Vehicle"))
		local st = vd and vd.Car.Steer
		local ch = car.PrimaryPart
		if not (st and ch and ch:FindFirstChild("Origin")) then
			return nil
		end
		local o = ch.CFrame * ch.Origin.CFrame
		local c = Vector3.new(st.Centre[1], st.Centre[2], st.Centre[3])
		local ax = Vector3.new(st.Axis[1], st.Axis[2], st.Axis[3]).Unit
		local r = ax:Cross(Vector3.yAxis).Unit
		local up = r:Cross(ax).Unit
		if up.Y < 0 then
			up = -up
		end
		-- the right hand is the grip on the car's right (+X in the car frame), picked before turning so the hands
		-- never swap; they turn with the wheel up to a quarter turn and then let it slide through them
		local sxR = (r * 0.866 + up * 0.5).X > 0 and 1 or -1
		local turn = CFrame.fromAxisAngle(ax, math.clamp(-(Kit.SteerNow[car] or 0) * rad(250), -rad(90), rad(90)))
		local function grip(sx)
			return o * (c + turn * ((r * sx * 0.866 + up * 0.5) * 0.4))
		end
		return grip(sxR), grip(-sxR)
	end
	local BIKE = {}
	for _, v in Vehicles.List do
		if v.bike then
			BIKE[v.id] = true
		end
	end
	RunService.Stepped:Connect(function()
		local P = SEAT_POSE
		local camPos = workspace.CurrentCamera.CFrame.Position
		for _, plr in Players:GetPlayers() do
			local char = plr.Character
			local hum = char and char:FindFirstChildOfClass("Humanoid")
			local seat = hum and hum.Health > 0 and hum.SeatPart
			local car = seat and seat.Parent
			if not (car and car:GetAttribute("NCLowrider")) or BIKE[car:GetAttribute("Vehicle")] then
				continue
			end
			if (seat.Position - camPos).Magnitude > 200 then
				continue
			end
			local J = jointsOf(char)
			local h, sh, sp = rad(P.hip), rad(P.shin), rad(P.splay)
			setJoint(J.Root, CFrame.identity, Vector3.new(0, P.lift, 0))
			setJoint(J.RightHip, A(h, 0, sp))
			setJoint(J.LeftHip, A(h, 0, -sp))
			setJoint(J.RightKnee, A(sh - h, 0, 0))
			setJoint(J.LeftKnee, A(sh - h, 0, 0))
			setJoint(J.RightAnkle, A(-sh + rad(10), 0, 0))
			setJoint(J.LeftAnkle, A(-sh + rad(10), 0, 0))
			local gr, gl
			if seat.Name == "DriveSeat" then
				gr, gl = wheelGrips(car)
			end
			if gr and reach(J.RightShoulder, J.RightElbow, J.RightWrist, gr, 1) then
				reach(J.LeftShoulder, J.LeftElbow, J.LeftWrist, gl, -1)
			elseif seat.Name == "DriveSeat" then -- no wheel data / rig: the fixed pose
				setJoint(J.RightShoulder, A(rad(P.shoulder), 0, -rad(P.shoulderIn)))
				setJoint(J.LeftShoulder, A(rad(P.shoulder), 0, rad(P.shoulderIn)))
				setJoint(J.RightElbow, A(rad(P.elbow), 0, 0))
				setJoint(J.LeftElbow, A(rad(P.elbow), 0, 0))
			end
		end
	end)
end
