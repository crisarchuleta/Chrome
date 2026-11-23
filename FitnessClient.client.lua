--!nonstrict
-- FitnessClient: the food menu, the Body panel (B), workouts as a timing game, and the poses everyone sees (lifting,
-- running on the treadmill, eating). It also hands your body's speed to the movement system (or, without it, to the
-- plain Humanoid).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local CAS = game:GetService("ContextActionService")
local RS = game:GetService("ReplicatedStorage")

local player = Players.LocalPlayer
local C = require(RS:WaitForChild("NCFitnessConfig"))
local Remotes = RS:WaitForChild("Remotes")
local BodyRE = Remotes:WaitForChild("BodyAction")
local BodyUI = Remotes:WaitForChild("BodyUI")
local rad = math.rad

---------------------------------------------------------------------------------------------- UI helpers
local gui = Instance.new("ScreenGui")
gui.Name = "BodyUI"
gui.ResetOnSpawn = false
gui.Parent = player:WaitForChild("PlayerGui")

local function frame(parent, size, pos, color, trans)
	local f = Instance.new("Frame")
	f.Size, f.Position = size, pos
	f.BackgroundColor3 = color or Color3.fromRGB(14, 16, 22)
	f.BackgroundTransparency = trans or 0.12
	f.BorderSizePixel = 0
	f.Parent = parent
	Instance.new("UICorner", f).CornerRadius = UDim.new(0, 10)
	return f
end
local function label(parent, text, size, pos, ts, color, font, align)
	local t = Instance.new("TextLabel")
	t.Size, t.Position = size, pos
	t.BackgroundTransparency = 1
	t.Text = text
	t.TextSize = ts or 16
	t.TextColor3 = color or Color3.fromRGB(240, 240, 240)
	t.Font = font or Enum.Font.GothamBold
	t.TextXAlignment = align or Enum.TextXAlignment.Left
	t.RichText = true
	t.Parent = parent
	return t
end
local function button(parent, text, size, pos, color)
	local b = Instance.new("TextButton")
	b.Size, b.Position = size, pos
	b.BackgroundColor3 = color or Color3.fromRGB(40, 44, 54)
	b.Text = text
	b.TextSize = 16
	b.TextColor3 = Color3.new(1, 1, 1)
	b.Font = Enum.Font.GothamBold
	b.AutoButtonColor = true
	b.BorderSizePixel = 0
	b.Parent = parent
	Instance.new("UICorner", b).CornerRadius = UDim.new(0, 8)
	return b
end

---------------------------------------------------------------------------------------------- food menu
local menu = frame(gui, UDim2.fromOffset(330, 60), UDim2.new(0.5, -165, 0.5, -150))
menu.Visible = false
local menuTitle = label(menu, "", UDim2.new(1, -20, 0, 30), UDim2.fromOffset(12, 6), 20, Color3.fromRGB(255, 190, 90), Enum.Font.GothamBlack)
local menuList = Instance.new("Frame")
menuList.BackgroundTransparency = 1
menuList.Size = UDim2.new(1, -20, 1, -80)
menuList.Position = UDim2.fromOffset(10, 40)
menuList.Parent = menu
local layout = Instance.new("UIListLayout", menuList)
layout.Padding = UDim.new(0, 6)
local closeMenu = button(menu, "Close", UDim2.new(1, -20, 0, 30), UDim2.new(0, 10, 1, -38), Color3.fromRGB(70, 40, 40))
closeMenu.MouseButton1Click:Connect(function()
	menu.Visible = false
end)
local menuStall
BodyUI.OnClientEvent:Connect(function(kind, a, b, c)
	if kind == "menu" then
		menuStall = a
		for _, ch in menuList:GetChildren() do
			if ch:IsA("TextButton") then
				ch:Destroy()
			end
		end
		menuTitle.Text = a and (a:GetAttribute("Title") or "Food") or "Food"
		for _, item in b or {} do
			local f = C.FOODS[item]
			if f then
				local btn = button(menuList, ("%s   $%d   %d kcal   +%d energy"):format(f.label, f.price, f.kcal, f.energy),
					UDim2.new(1, 0, 0, 34), UDim2.new(), f.junk and Color3.fromRGB(90, 60, 30) or Color3.fromRGB(30, 80, 50))
				btn.TextSize = 14
				btn.MouseButton1Click:Connect(function()
					BodyRE:FireServer("eat", menuStall, item)
				end)
			end
		end
		menu.Size = UDim2.fromOffset(330, 90 + #(b or {}) * 40)
		menu.Visible = true
	elseif kind == "workout" then
		startGame(a, b, c)
	elseif kind == "workoutEnd" then
		endGame(a, b)
	end
end)

---------------------------------------------------------------------------------------------- the Body panel
local panel = frame(gui, UDim2.fromOffset(300, 300), UDim2.new(0, 16, 0.5, -150))
panel.Visible = false
label(panel, "BODY", UDim2.new(1, -20, 0, 28), UDim2.fromOffset(12, 6), 22, Color3.fromRGB(255, 120, 60), Enum.Font.GothamBlack)
local buildLbl = label(panel, "", UDim2.new(1, -20, 0, 20), UDim2.fromOffset(12, 34), 16, Color3.fromRGB(200, 220, 255))
local bars = {}
for i, spec in { { "Strength", "BodyStr", 100, Color3.fromRGB(230, 80, 70) }, { "Stamina", "BodySta", 100, Color3.fromRGB(80, 200, 255) },
	{ "Body fat", "BodyFat", 40, Color3.fromRGB(240, 190, 80) }, { "Energy", "BodyEnergy", 100, Color3.fromRGB(110, 230, 120) } } do
	local y = 62 + (i - 1) * 36
	local name = label(panel, spec[1], UDim2.new(1, -20, 0, 16), UDim2.fromOffset(12, y), 14)
	local bg = frame(panel, UDim2.new(1, -24, 0, 8), UDim2.fromOffset(12, y + 18), Color3.fromRGB(40, 42, 50), 0)
	local fill = frame(bg, UDim2.fromScale(0, 1), UDim2.new(), spec[4], 0)
	bars[i] = { attr = spec[2], max = spec[3], name = name, fill = fill, title = spec[1] }
end
local infoLbl = label(panel, "", UDim2.new(1, -20, 0, 54), UDim2.fromOffset(12, 206), 13, Color3.fromRGB(210, 210, 210), Enum.Font.Gotham)
infoLbl.TextWrapped = true
infoLbl.TextYAlignment = Enum.TextYAlignment.Top
local tipLbl = label(panel, "", UDim2.new(1, -20, 0, 34), UDim2.fromOffset(12, 262), 12, Color3.fromRGB(255, 200, 140), Enum.Font.GothamMedium)
tipLbl.TextWrapped = true

local function refreshPanel()
	for _, b in bars do
		local v = player:GetAttribute(b.attr) or 0
		b.fill.Size = UDim2.fromScale(math.clamp(v / b.max, 0, 1), 1)
		b.name.Text = ("%s  <font color=\"#bbbbbb\">%s</font>"):format(b.title, b.attr == "BodyFat" and string.format("%.1f %%", v) or string.format("%d", v))
	end
	local build = player:GetAttribute("BodyBuild") or "Average"
	buildLbl.Text = "Build: " .. build .. (player:GetAttribute("BodyProtein") and "   (protein boost)" or "")
	infoLbl.Text = ("Speed %d%%   Sprint %.0f s   Climb %.1f studs\nToday: %d kcal in, %d kcal out"):format(
		math.floor((player:GetAttribute("BodySpeed") or 1) * 100 + 0.5), player:GetAttribute("BodySprintTime") or 12,
		player:GetAttribute("BodyClimbMax") or 9.2, player:GetAttribute("BodyKcalIn") or 0, player:GetAttribute("BodyKcalOut") or 0)
	tipLbl.Text = C.TIPS[build] or ""
end
local function togglePanel(_, state)
	if state == Enum.UserInputState.Begin then
		panel.Visible = not panel.Visible
		refreshPanel()
	end
	return Enum.ContextActionResult.Pass
end
CAS:BindAction("NC_BodyPanel", togglePanel, true, Enum.KeyCode.B)
CAS:SetTitle("NC_BodyPanel", "Body")
player.AttributeChanged:Connect(function(a)
	if panel.Visible and string.sub(a, 1, 4) == "Body" then
		refreshPanel()
	end
end)

---------------------------------------------------------------------------------------------- workouts: the timing game
local game_ = frame(gui, UDim2.fromOffset(380, 150), UDim2.new(0.5, -190, 1, -250))
game_.Visible = false
local gTitle = label(game_, "", UDim2.new(1, -20, 0, 26), UDim2.fromOffset(12, 6), 20, Color3.fromRGB(255, 120, 60), Enum.Font.GothamBlack)
local gInfo = label(game_, "", UDim2.new(1, -20, 0, 18), UDim2.fromOffset(12, 34), 14, Color3.fromRGB(220, 220, 220))
local track = frame(game_, UDim2.new(1, -24, 0, 22), UDim2.fromOffset(12, 60), Color3.fromRGB(40, 42, 50), 0)
local zone = frame(track, UDim2.fromScale(0.22, 1), UDim2.fromScale(0.39, 0), Color3.fromRGB(70, 200, 110), 0)
local marker = frame(track, UDim2.new(0, 6, 1, 6), UDim2.new(0, 0, 0, -3), Color3.fromRGB(255, 255, 255), 0)
local liftBtn = button(game_, "LIFT  (Space)", UDim2.new(0.62, -16, 0, 40), UDim2.fromOffset(12, 96), Color3.fromRGB(200, 80, 40))
local leaveBtn = button(game_, "Done (X)", UDim2.new(0.38, -12, 0, 40), UDim2.new(0.62, 4, 0, 96), Color3.fromRGB(60, 60, 70))

local G = { on = false }
function startGame(station, title, kind)
	G = { on = true, station = station, kind = kind, t0 = os.clock(), reps = 0, last = 0, speed = 0.75, zc = 0.5 }
	gTitle.Text = title
	game_.Visible = true
	menu.Visible = false
end
function endGame(reps, why)
	if G.on then
		G.on = false
		game_.Visible = false
		local msg = why == "empty" and "Out of energy: eat something." or ""
		gInfo.Text = msg
	end
end
local function markerPos()
	-- ping-pong across the track; heavier sets run the marker faster as you tire
	local t = (os.clock() - G.t0) * G.speed
	local x = t % 2
	return x <= 1 and x or 2 - x
end
local function lift()
	if not G.on then
		return
	end
	local now = os.clock()
	local ex = C.EXERCISES[G.kind]
	if now - G.last < (ex and ex.minRep or 1) then
		return
	end
	G.last = now
	local x = markerPos()
	local half = 0.11
	local q = math.clamp(1 - math.abs(x - (G.zc + half)) / (half * 2.2), 0, 1) -- 1 = dead centre of the green zone
	BodyRE:FireServer("rep", G.station, q)
	G.reps += 1
	G.speed = math.min(1.6, G.speed + 0.03)
	G.zc = 0.25 + math.random() * 0.5 - half
	zone.Position = UDim2.fromScale(G.zc, 0)
	gInfo.Text = ("Rep %d   %s"):format(G.reps, q > 0.8 and "Perfect form" or (q > 0.4 and "Good" or "Sloppy"))
end
liftBtn.MouseButton1Click:Connect(lift)
leaveBtn.MouseButton1Click:Connect(function()
	BodyRE:FireServer("leave")
end)
CAS:BindActionAtPriority("NC_Lift", function(_, st)
	if G.on and st == Enum.UserInputState.Begin then
		lift()
		return Enum.ContextActionResult.Sink
	end
	return Enum.ContextActionResult.Pass
end, false, 3500, Enum.KeyCode.Space, Enum.KeyCode.ButtonA)
CAS:BindActionAtPriority("NC_LeaveWorkout", function(_, st)
	if G.on and st == Enum.UserInputState.Begin then
		BodyRE:FireServer("leave")
		return Enum.ContextActionResult.Sink
	end
	return Enum.ContextActionResult.Pass
end, false, 3500, Enum.KeyCode.X, Enum.KeyCode.ButtonB)
RunService.RenderStepped:Connect(function()
	if G.on then
		marker.Position = UDim2.new(markerPos(), -3, 0, -3)
	end
end)

---------------------------------------------------------------------------------------------- poses everyone sees
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
local JN = { "Root", "Waist", "Neck", "RightShoulder", "LeftShoulder", "RightElbow", "LeftElbow", "RightHip", "LeftHip",
	"RightKnee", "LeftKnee", "RightAnkle", "LeftAnkle" }
local cache = setmetatable({}, { __mode = "k" })
local function jointsOf(char)
	local e = cache[char]
	if e and e.n >= #JN and not (e.Waist and e.Waist.Parent == nil) then
		return e
	end
	e = { n = 0 }
	for _, d in char:GetDescendants() do
		if (d:IsA("Motor6D") or d:IsA("AnimationConstraint")) and table.find(JN, d.Name) and not e[d.Name] then
			e[d.Name] = d
			e.n += 1
		end
	end
	cache[char] = e
	return e
end
local function A(x, y, z)
	return CFrame.Angles(rad(x), rad(y or 0), rad(z or 0))
end

local POSES = {}
function POSES.Bench(J, u, rootH)
	-- lying on the bench, pressing the bar up from the chest
	local down = math.sin(math.pi * u)               -- 0 = arms locked out, 1 = bar at the chest
	setJoint(J.Root, CFrame.new(0, -(rootH - 1.2), 0) * A(0, 180, 0) * A(90, 0, 0), 1)
	setJoint(J.RightShoulder, A(90 - 25 * down, 0, 35 * down), 1)
	setJoint(J.LeftShoulder, A(90 - 25 * down, 0, -35 * down), 1)
	setJoint(J.RightElbow, A(100 * down), 1)
	setJoint(J.LeftElbow, A(100 * down), 1)
	setJoint(J.RightHip, A(80, 0, 12), 1)
	setJoint(J.LeftHip, A(80, 0, -12), 1)
	setJoint(J.RightKnee, A(-90), 1)
	setJoint(J.LeftKnee, A(-90), 1)
	setJoint(J.Neck, A(-10), 1)
end
function POSES.Squat(J, u)
	local d = math.sin(math.pi * u)
	local h, k = rad(100 * d), rad(-115 * d)
	setJoint(J.RightHip, CFrame.Angles(h, 0, rad(10)), 1)
	setJoint(J.LeftHip, CFrame.Angles(h, 0, rad(-10)), 1)
	setJoint(J.RightKnee, CFrame.Angles(k, 0, 0), 1)
	setJoint(J.LeftKnee, CFrame.Angles(k, 0, 0), 1)
	setJoint(J.RightAnkle, CFrame.Angles(-(h + k), 0, 0), 1)
	setJoint(J.LeftAnkle, CFrame.Angles(-(h + k), 0, 0), 1)
	setJoint(J.Waist, A(-22 * d), 1)
	setJoint(J.Root, CFrame.new(0, -1.25 * d, 0.1 * d), 1)
	setJoint(J.RightShoulder, A(20, 0, 85), 1)               -- hands on the bar across the shoulders
	setJoint(J.LeftShoulder, A(20, 0, -85), 1)
	setJoint(J.RightElbow, A(115), 1)
	setJoint(J.LeftElbow, A(115), 1)
end
function POSES.Pullup(J, u, rootH)
	local pull = math.sin(math.pi * u)
	setJoint(J.Root, CFrame.new(0, 2.5 + 1.3 * pull, 0), 1)       -- hanging from the bar, chin up to it
	setJoint(J.RightShoulder, A(172 - 100 * pull, 0, 10 + 15 * pull), 1)
	setJoint(J.LeftShoulder, A(172 - 100 * pull, 0, -10 - 15 * pull), 1)
	setJoint(J.RightElbow, A(8 + 115 * pull), 1)
	setJoint(J.LeftElbow, A(8 + 115 * pull), 1)
	setJoint(J.RightHip, A(15), 1)
	setJoint(J.LeftHip, A(10), 1)
	setJoint(J.RightKnee, A(-35), 1)
	setJoint(J.LeftKnee, A(-40), 1)
	setJoint(J.Neck, A(10), 1)
end
function POSES.Curl(J, u, _, reps)
	local side = (reps or 0) % 2 == 0 and "Right" or "Left"
	local other = side == "Right" and "Left" or "Right"
	local c = math.sin(math.pi * u)
	setJoint(J[side .. "Shoulder"], A(8, 0, 0), 1)
	setJoint(J[side .. "Elbow"], A(10 + 130 * c), 1)
	setJoint(J[other .. "Shoulder"], A(5), 1)
	setJoint(J[other .. "Elbow"], A(12), 1)
end
function POSES.Bag(J, u, _, reps)
	local side = (reps or 0) % 2 == 0 and "Right" or "Left"
	local other = side == "Right" and "Left" or "Right"
	local s = side == "Right" and 1 or -1
	local p = math.sin(math.pi * math.min(1, u * 1.6))
	setJoint(J[side .. "Shoulder"], A(70 + 15 * p, 0, s * 10), 1)
	setJoint(J[side .. "Elbow"], A(110 - 100 * p), 1)
	setJoint(J[other .. "Shoulder"], A(80, 0, -s * 15), 1)       -- guard up
	setJoint(J[other .. "Elbow"], A(125), 1)
	setJoint(J.Waist, A(-6, s * 25 * p, 0), 1)
	setJoint(J.RightHip, A(12), 1)
	setJoint(J.LeftHip, A(-10), 1)
	setJoint(J.RightKnee, A(-20), 1)
	setJoint(J.LeftKnee, A(-15), 1)
end
function POSES.Treadmill(J, _, _, _, now)
	local t = now * 2.6 * math.pi
	local s = math.sin(t)
	setJoint(J.RightHip, A(30 * s), 1)
	setJoint(J.LeftHip, A(-30 * s), 1)
	setJoint(J.RightKnee, A(-(20 + 70 * math.max(0, -s))), 1) -- the knee folds as the leg swings back
	setJoint(J.LeftKnee, A(-(20 + 70 * math.max(0, s))), 1)
	setJoint(J.RightShoulder, A(-30 * s), 1)
	setJoint(J.LeftShoulder, A(30 * s), 1)
	setJoint(J.RightElbow, A(85), 1)
	setJoint(J.LeftElbow, A(85), 1)
	setJoint(J.Waist, A(-6), 1)
	setJoint(J.Root, CFrame.new(0, -0.15 + 0.12 * math.abs(math.cos(t)), 0), 1)
end

local FOODCOL = { Burger = Color3.fromRGB(160, 100, 50), Pizza = Color3.fromRGB(240, 190, 70), Tacos = Color3.fromRGB(230, 180, 80),
	Fries = Color3.fromRGB(240, 210, 80), Soda = Color3.fromRGB(200, 30, 40), EnergyDrink = Color3.fromRGB(40, 200, 255),
	Smoothie = Color3.fromRGB(240, 120, 170), Protein = Color3.fromRGB(240, 240, 240), Salad = Color3.fromRGB(90, 190, 80) }
local props = setmetatable({}, { __mode = "k" })
local repT = setmetatable({}, { __mode = "k" })

RunService.Stepped:Connect(function()
	local now = os.clock()
	local sNow = workspace:GetServerTimeNow()
	for _, p in Players:GetPlayers() do
		local char = p.Character
		local hrp = char and char:FindFirstChild("HumanoidRootPart")
		local hum = char and char:FindFirstChildOfClass("Humanoid")
		if not (hrp and hum) then
			continue
		end
		local J = jointsOf(char)
		local w = char:GetAttribute("Workout")
		if w and POSES[w] then
			local reps = char:GetAttribute("WorkoutRep") or 0
			local r = repT[char]
			if not r or r.reps ~= reps then
				repT[char] = { reps = reps, t = now }
				r = repT[char]
			end
			local u = math.clamp((now - r.t) / 0.9, 0, 1)
			POSES[w](J, reps > 0 and u or 0, hrp.Size.Y / 2 + hum.HipHeight, reps, now)
		end
		-- eating: hand to mouth with the food in it
		local e = char:GetAttribute("Eating")
		local item, t0
		if type(e) == "string" then
			item, t0 = string.match(e, "^(%a+)|([%d%.]+)$")
		end
		local age = t0 and (sNow - tonumber(t0)) or 99
		local hand = char:FindFirstChild("RightHand")
		if age < 1.8 and hand then
			local a = math.sin(math.pi * math.clamp(age / 1.8, 0, 1))
			setJoint(J.RightShoulder, A(105 * a, -20 * a, 0), math.min(1, a * 3))
			setJoint(J.RightElbow, A(125 * a), math.min(1, a * 3))
			setJoint(J.Neck, A(-6 * a), a)
			if not props[char] then
				local f = Instance.new("Part")
				f.Name = "NC_Food"
				f.Size = Vector3.new(0.5, 0.35, 0.5)
				f.Color = FOODCOL[item] or Color3.fromRGB(200, 160, 100)
				f.Material = Enum.Material.SmoothPlastic
				f.CanCollide, f.CanQuery, f.CanTouch, f.Massless, f.Anchored = false, false, false, true, false
				f.CFrame = hand.CFrame * CFrame.new(0, -0.35, -0.2)
				local wl = Instance.new("WeldConstraint")
				wl.Part0, wl.Part1 = hand, f
				wl.Parent = f
				f.Parent = workspace.CurrentCamera
				props[char] = f
			end
		elseif props[char] then
			props[char]:Destroy()
			props[char] = nil
		end
	end
end)

---------------------------------------------------------------------------------------------- your body's speed
-- with the movement system: a speed factor it multiplies in (it reads sprint time, jump and climbing itself);
-- without it: the plain Humanoid's walk speed and jump, only while nothing else has changed them
local last = {}
task.spawn(function()
	while true do
		task.wait(0.5)
		local char = player.Character
		local hum = char and char:FindFirstChildOfClass("Humanoid")
		if hum then
			local sp = player:GetAttribute("BodySpeed") or 1
			if hum:GetAttribute("NC_Movement") then
				hum:SetAttribute("SpeedFactor_Body", sp)
			elseif hum.Health > 0 then
				local want = 16 * sp
				if math.abs(hum.WalkSpeed - 16) < 0.01 or (last.ws and math.abs(hum.WalkSpeed - last.ws) < 0.01) then
					hum.WalkSpeed = want
					last.ws = want
				end
				local jh = 7.2 * (player:GetAttribute("BodyJump") or 1)
				if not hum.UseJumpPower and (math.abs(hum.JumpHeight - 7.2) < 0.01 or (last.jh and math.abs(hum.JumpHeight - last.jh) < 0.01)) then
					hum.JumpHeight = jh
					last.jh = jh
				end
			end
		end
	end
end)
player.CharacterAdded:Connect(function()
	last = {}
	if G.on then
		endGame(0, "respawn")
	end
end)
