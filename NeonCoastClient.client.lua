-- Neon Coast client: driving, HUD, job marker, busted screen
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UIS = game:GetService("UserInputService")
local TweenService = game:GetService("TweenService")
local RS = game:GetService("ReplicatedStorage")
local Remotes = RS:WaitForChild("Remotes")
local player = Players.LocalPlayer

------------------------------------------------------------ HUD
local gui = Instance.new("ScreenGui"); gui.Name = "NeonCoastHUD"; gui.ResetOnSpawn = false; gui.IgnoreGuiInset = true; gui.Parent = player:WaitForChild("PlayerGui")
local FONT = Enum.Font.FredokaOne
local function label(props)
	local l = Instance.new("TextLabel"); l.BackgroundTransparency = 1; l.Font = FONT; l.TextScaled = true; l.TextStrokeTransparency = 0.2
	for k, v in pairs(props) do l[k] = v end
	l.Parent = props.Parent or gui; return l
end

local logo = label({Size = UDim2.fromOffset(260, 46), Position = UDim2.new(0, 16, 0, 50), Text = "NEON COAST", TextColor3 = Color3.fromRGB(255,90,220), TextXAlignment = Enum.TextXAlignment.Left})
local cashL = label({Size = UDim2.fromOffset(260, 44), Position = UDim2.new(1, -276, 0, 50), Text = "$0", TextColor3 = Color3.fromRGB(80,255,140), TextXAlignment = Enum.TextXAlignment.Right})
local starsFrame = Instance.new("Frame"); starsFrame.BackgroundTransparency = 1; starsFrame.Size = UDim2.fromOffset(220, 40); starsFrame.Position = UDim2.new(1, -236, 0, 96); starsFrame.Parent = gui
local layout = Instance.new("UIListLayout"); layout.FillDirection = Enum.FillDirection.Horizontal; layout.HorizontalAlignment = Enum.HorizontalAlignment.Right; layout.Parent = starsFrame
local stars = {}
for k = 1, 5 do stars[k] = label({Parent = starsFrame, Size = UDim2.fromOffset(40, 40), Text = "★", TextColor3 = Color3.fromRGB(80,80,90), LayoutOrder = k}) end

local hint = label({Size = UDim2.new(0, 820, 0, 22), Position = UDim2.new(0.5, -410, 1, -34), Text = "V: get a car   E: get in   C: character   Driving: Shift handbrake   R window   H horn   L lights   Z/C/Q signals", TextColor3 = Color3.fromRGB(230,220,255), TextTransparency = 0.15})
local jobL = label({Size = UDim2.fromOffset(340, 30), Position = UDim2.new(0, 16, 0, 100), Text = "", TextColor3 = Color3.fromRGB(60,230,255), TextXAlignment = Enum.TextXAlignment.Left})
local speedL = label({Size = UDim2.fromOffset(200, 60), Position = UDim2.new(1, -216, 1, -110), Text = "", TextColor3 = Color3.fromRGB(255,230,80), TextXAlignment = Enum.TextXAlignment.Right})
local nitroBar = Instance.new("Frame"); nitroBar.Size = UDim2.fromOffset(180, 8); nitroBar.Position = UDim2.new(1, -196, 1, -46); nitroBar.BackgroundColor3 = Color3.fromRGB(40,30,60); nitroBar.Visible = false; nitroBar.Parent = gui
local nitroFill = Instance.new("Frame"); nitroFill.Size = UDim2.fromScale(1, 1); nitroFill.BackgroundColor3 = Color3.fromRGB(60,230,255); nitroFill.BorderSizePixel = 0; nitroFill.Parent = nitroBar
Instance.new("UICorner", nitroBar); Instance.new("UICorner", nitroFill)

local toast = label({Size = UDim2.fromOffset(640, 40), Position = UDim2.new(0.5, -320, 0, 140), Text = "", TextColor3 = Color3.new(1,1,1), TextTransparency = 1, TextStrokeTransparency = 1})
local toastId = 0
Remotes.Notify.OnClientEvent:Connect(function(text, color)
	toastId += 1
	local id = toastId
	toast.Text = text; toast.TextColor3 = color or Color3.new(1,1,1)
	toast.TextTransparency = 0; toast.TextStrokeTransparency = 0.2
	task.delay(3.5, function()
		if id ~= toastId then return end
		TweenService:Create(toast, TweenInfo.new(0.6), {TextTransparency = 1, TextStrokeTransparency = 1}):Play()
	end)
end)

-- title splash
local splash = label({Size = UDim2.fromScale(1, 0.25), Position = UDim2.fromScale(0, 0.3), Text = "NEON COAST", TextColor3 = Color3.fromRGB(255,90,220)})
local sub = label({Size = UDim2.fromScale(1, 0.05), Position = UDim2.fromScale(0, 0.55), Text = "grab a ride. make some cash. stay one step ahead.", TextColor3 = Color3.fromRGB(60,230,255)})
task.delay(3, function()
	TweenService:Create(splash, TweenInfo.new(1), {TextTransparency = 1, TextStrokeTransparency = 1}):Play()
	TweenService:Create(sub, TweenInfo.new(1), {TextTransparency = 1, TextStrokeTransparency = 1}):Play()
end)

-- cash + stars
local function hookCash()
	local ls = player:WaitForChild("leaderstats")
	local cash = ls:WaitForChild("Cash")
	local function upd() cashL.Text = "$" .. tostring(cash.Value) end
	cash.Changed:Connect(upd); upd()
end
task.spawn(hookCash)
local flashT = 0
RunService.RenderStepped:Connect(function(dt)
	flashT += dt
	local s = player:GetAttribute("Stars") or 0
	local blink = math.floor(flashT * 3) % 2 == 0
	for k = 1, 5 do
		stars[k].TextColor3 = k <= s and (blink and Color3.fromRGB(255,230,80) or Color3.fromRGB(255,140,60)) or Color3.fromRGB(80,80,90)
	end
end)

------------------------------------------------------------ job marker
local marker
Remotes.JobUpdate.OnClientEvent:Connect(function(pos, reward)
	if marker then marker:Destroy() marker = nil end
	if not pos then jobL.Text = "" return end
	marker = Instance.new("Part"); marker.Anchored = true; marker.CanCollide = false; marker.CanQuery = false; marker.CanTouch = false
	marker.Size = Vector3.new(14, 200, 14); marker.Shape = Enum.PartType.Block; marker.Material = Enum.Material.Neon
	marker.Color = Color3.fromRGB(60,230,255); marker.Transparency = 0.6; marker.Position = pos + Vector3.new(0, 100, 0)
	local bb = Instance.new("BillboardGui"); bb.AlwaysOnTop = true; bb.Size = UDim2.fromOffset(160, 50); bb.StudsOffsetWorldSpace = Vector3.new(0, -90, 0); bb.Parent = marker
	label({Parent = bb, Size = UDim2.fromScale(1, 1), Text = "DROP-OFF", TextColor3 = Color3.fromRGB(60,230,255)})
	marker.Parent = workspace
	jobL:SetAttribute("Reward", reward)
end)

------------------------------------------------------------ busted screen
Remotes.Busted.OnClientEvent:Connect(function(seconds, fine)
	local f = Instance.new("Frame"); f.Size = UDim2.fromScale(1, 1); f.BackgroundColor3 = Color3.fromRGB(20, 30, 80); f.BackgroundTransparency = 0.35; f.Parent = gui
	label({Parent = f, Size = UDim2.fromScale(1, 0.2), Position = UDim2.fromScale(0, 0.3), Text = "BUSTED!", TextColor3 = Color3.fromRGB(80,160,255)})
	local t = label({Parent = f, Size = UDim2.fromScale(1, 0.06), Position = UDim2.fromScale(0, 0.52), Text = "", TextColor3 = Color3.new(1,1,1)})
	for s = seconds, 1, -1 do
		t.Text = ("Fine paid: $%d   |   Released in %ds"):format(fine, s)
		if s == seconds - 2 then f.BackgroundTransparency = 0.75 end
		task.wait(1)
	end
	f:Destroy()
end)

------------------------------------------------------------ driving
UIS.InputBegan:Connect(function(input, processed)
	if processed then return end
	if input.KeyCode == Enum.KeyCode.V then Remotes.SpawnCar:FireServer() end
	if input.KeyCode == Enum.KeyCode.G then
		-- in one of the new vehicles G is three-wheel (LowriderClient); the panels have their own prompts there
		local hum = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
		local seat = hum and hum.SeatPart
		if seat and seat.Name == "DriveSeat" and seat.Parent and seat.Parent:GetAttribute("NCLowrider") then return end
		Remotes.ToggleDoors:FireServer()
	end
end)

------------------------------------------------------------ rolling + steering wheels (visual only, per client)
do
	local wheelCache = setmetatable({}, {__mode = "k"})
	local spin = setmetatable({}, {__mode = "k"})
	local leanCache = setmetatable({}, {__mode = "k"})
	local leanNow = setmetatable({}, {__mode = "k"})
	local function wheelsOf(car)
		local list = wheelCache[car]
		if list then return list end
		list = {}
		for _, m in ipairs(car:GetDescendants()) do
			if m:IsA("Motor6D") and m:GetAttribute("Wheel") then table.insert(list, {motor = m, front = m:GetAttribute("Wheel"):sub(1, 1) == "F"}) end
			if m:IsA("Motor6D") and m.Name == "Lean" then leanCache[car] = m end
		end
		wheelCache[car] = list
		return list
	end
	local folders = {}
	task.spawn(function()
		local r = workspace:WaitForChild("NeonCoast")
		folders = {r:WaitForChild("Cars"), r:WaitForChild("Police")}
	end)
	RunService.RenderStepped:Connect(function(dt)
		local cam = workspace.CurrentCamera.CFrame.Position
		for _, f in ipairs(folders) do
			for _, car in ipairs(f:GetChildren()) do
				local ch = car.PrimaryPart
				if ch and (ch.Position - cam).Magnitude < 250 then
					local v = ch.AssemblyLinearVelocity
					local fwd = v:Dot(ch.CFrame.LookVector)
					local yaw = ch.AssemblyAngularVelocity.Y
					local list = wheelsOf(car)
					local r = 1.4
					spin[car] = ((spin[car] or 0) - fwd / r * dt) % (math.pi * 2)
					local steer = math.clamp(yaw * 0.35, -0.5, 0.5)
					for _, w in ipairs(list) do
						local roll = CFrame.Angles(spin[car], 0, 0)
						w.motor.Transform = w.front and (CFrame.Angles(0, steer, 0) * roll) or roll
					end
					-- bikes lean into corners (visual only)
					local leanMotor = leanCache[car]
					if leanMotor then
						local target = math.clamp(yaw * math.abs(fwd) * 0.006, -0.55, 0.55)
						leanNow[car] = (leanNow[car] or 0) + (target - (leanNow[car] or 0)) * math.min(1, dt * 6)
						leanMotor.Transform = CFrame.Angles(0, 0, leanNow[car])
					end
				end
			end
		end
	end)
end

------------------------------------------------------------ gun ports: first-person view out of the slot while manned
do
	local portSeat
	local saved
	RunService.Heartbeat:Connect(function()
		local hum = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
		local seat = hum and hum.SeatPart
		local isPort = seat and seat:GetAttribute("GunPort")
		if isPort and seat ~= portSeat then
			portSeat = seat
			local sight = seat.Parent:FindFirstChild(seat:GetAttribute("Sight"))
			local cam = workspace.CurrentCamera
			saved = {subject = cam.CameraSubject, mode = player.CameraMode, maxZoom = player.CameraMaxZoomDistance}
			if sight then cam.CameraSubject = sight end
			player.CameraMode = Enum.CameraMode.LockFirstPerson
		elseif not isPort and portSeat then
			portSeat = nil
			local cam = workspace.CurrentCamera
			if saved then
				player.CameraMode = saved.mode or Enum.CameraMode.Classic
				player.CameraMaxZoomDistance = saved.maxZoom or 128
			end
			if hum then cam.CameraSubject = hum end
		end
	end)
end

local MAX_FWD, MAX_REV, NITRO_SPEED = 115, 35, 175
local speed, nitro = 0, 1
local currentCar

RunService.Heartbeat:Connect(function(dt)
	local char = player.Character
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	local hrp = char and char:FindFirstChild("HumanoidRootPart")

	-- job distance readout
	if marker and hrp then
		local d = (marker.Position * Vector3.new(1,0,1) - hrp.Position * Vector3.new(1,0,1)).Magnitude
		jobL.Text = ("Delivery: %dm  ($%d)"):format(math.floor(d), jobL:GetAttribute("Reward") or 0)
	end

	local seat = hum and hum.SeatPart
	-- the new vehicles (NCLowrider) are driven by LowriderClient with their own suspension, HUD and controls
	if seat and seat.Name == "DriveSeat" and seat:IsA("VehicleSeat") and not seat.Parent:GetAttribute("NCLowrider") then
		local car = seat.Parent
		local chassis = car.PrimaryPart
		if car ~= currentCar then currentCar = car; speed = 0 end
		local throttle, steer = seat.ThrottleFloat, seat.SteerFloat
		local boosting = UIS:IsKeyDown(Enum.KeyCode.LeftShift) and throttle > 0 and nitro > 0
		if boosting then nitro = math.max(0, nitro - dt * 0.35) else nitro = math.min(1, nitro + dt * 0.12) end
		-- per-vehicle handling (bikes are quick and nimble, the armored truck is heavy)
		local top = car:GetAttribute("TopSpeed") or MAX_FWD
		local accelMul = (car:GetAttribute("Accel") or 45) / 45
		local turnMul = (car:GetAttribute("TurnRate") or 1.9) / 1.9
		local maxF = boosting and top * (NITRO_SPEED / MAX_FWD) or top
		local target = throttle > 0 and maxF * throttle or (throttle < 0 and -MAX_REV or 0)
		local rate
		if throttle == 0 then rate = 35
		elseif math.sign(target) ~= math.sign(speed) and math.abs(speed) > 1 then rate = 120
		else rate = (boosting and 80 or 45) * accelMul end
		speed += math.clamp(target - speed, -rate * dt, rate * dt)
		local look = chassis.CFrame.LookVector * Vector3.new(1, 0, 1)
		if look.Magnitude > 0.01 then look = look.Unit end
		chassis.Drive.VectorVelocity = look * speed
		local grip = math.clamp(math.abs(speed) / 18, 0, 1)
		local turnRate = (1.9 - math.clamp(math.abs(speed) / 140, 0, 0.8)) * turnMul
		chassis.Turn.AngularVelocity = Vector3.new(0, -steer * turnRate * grip * (speed < 0 and -1 or 1), 0)
		speedL.Text = tostring(math.floor(math.abs(chassis.AssemblyLinearVelocity.Magnitude) * 0.6)) .. " MPH"
		nitroBar.Visible = true
		nitroFill.Size = UDim2.fromScale(nitro, 1)
		nitroFill.BackgroundColor3 = boosting and Color3.fromRGB(255,90,220) or Color3.fromRGB(60,230,255)
	else
		local ch = currentCar and currentCar.PrimaryPart
		local drive, turn = ch and ch:FindFirstChild("Drive"), ch and ch:FindFirstChild("Turn")
		if drive and drive:IsA("LinearVelocity") then drive.VectorVelocity = Vector3.zero end
		if turn and turn:IsA("AngularVelocity") then turn.AngularVelocity = Vector3.zero end
		currentCar = nil
		speed = 0
		speedL.Text = ""
		nitroBar.Visible = false
	end
end)
