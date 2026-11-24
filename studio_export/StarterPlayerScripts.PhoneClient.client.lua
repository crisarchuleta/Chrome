-- Neon Coast phone (Up arrow / P) + main menu (M).
-- A 3D phone held in a hand; the thumb pivots from its base and follows your cursor/finger, tapping on click.
-- Layering: phone < app icons < thumb < app names, so the thumb never covers text.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UIS = game:GetService("UserInputService")
local TweenService = game:GetService("TweenService")
local Lighting = game:GetService("Lighting")
local HttpService = game:GetService("HttpService")
local RS = game:GetService("ReplicatedStorage")
local Remotes = RS:WaitForChild("Remotes")
local Signals = RS:WaitForChild("LocalSignals")
local HomeConfig = require(RS:WaitForChild("HomeConfig"))
-- (old LookConfig retired: the phone hand now takes its skin tone from the character's head)
local player = Players.LocalPlayer
local FONT, FONT_B = Enum.Font.Gotham, Enum.Font.GothamBold
local PINK, CYAN = Color3.fromRGB(255,90,220), Color3.fromRGB(60,230,255)

local gui = Instance.new("ScreenGui"); gui.Name = "PhoneUI"; gui.ResetOnSpawn = false; gui.IgnoreGuiInset = true; gui.DisplayOrder = 30
gui.Parent = player:WaitForChild("PlayerGui")

local function text(parent, t, size, pos, color, z, font, align)
	local l = Instance.new("TextLabel"); l.BackgroundTransparency = 1; l.Text = t; l.TextScaled = true; l.Font = font or FONT_B
	l.Size = size; l.Position = pos; l.TextColor3 = color or Color3.new(1,1,1); l.ZIndex = z or 8; l.TextXAlignment = align or Enum.TextXAlignment.Center
	l.Parent = parent
	return l
end

------------------------------------------------------------------ phone body (3D, in a ViewportFrame)
local phoneAsset = RS:WaitForChild("PhoneAssets"):WaitForChild("Phone")
local PW, PH, PD = phoneAsset:GetAttribute("Width"), phoneAsset:GetAttribute("Height"), phoneAsset:GetAttribute("Depth")
local holder = Instance.new("Frame"); holder.Name = "PhoneHolder"; holder.BackgroundTransparency = 1; holder.AnchorPoint = Vector2.new(1, 1)
holder.Size = UDim2.new(0, 0, 0.74, 0); holder.Position = UDim2.new(1, -40, 1, 900); holder.Visible = false; holder.Parent = gui
local aspect = Instance.new("UIAspectRatioConstraint"); aspect.AspectRatio = (PW / PH) * 1.55; aspect.DominantAxis = Enum.DominantAxis.Height; aspect.Parent = holder
holder.Size = UDim2.new(1, 0, 0.74, 0)
local vp = Instance.new("ViewportFrame"); vp.Name = "PhoneView"; vp.BackgroundTransparency = 1; vp.Size = UDim2.fromScale(1 / 1.55, 1); vp.Position = UDim2.fromScale(0, 0)
vp.Ambient = Color3.fromRGB(150, 150, 160); vp.LightColor = Color3.new(1, 1, 1); vp.LightDirection = Vector3.new(-0.3, -0.6, 1); vp.ZIndex = 2; vp.Parent = holder
local phoneModel = phoneAsset:Clone(); phoneModel.Parent = vp
local vcam = Instance.new("Camera"); vcam.FieldOfView = 20; vcam.Parent = vp; vp.CurrentCamera = vcam
local camDist = (PH / 2) / math.tan(math.rad(vcam.FieldOfView) / 2) / 0.94
vcam.CFrame = CFrame.lookAt(Vector3.new(0, 0, -camDist), Vector3.new(0, 0, 0))

local function project(world)
	local p = vcam.CFrame:PointToObjectSpace(world)
	local size = vp.AbsoluteSize
	local tanY = math.tan(math.rad(vcam.FieldOfView) / 2)
	local x = p.X / (-p.Z * tanY * (size.X / size.Y))
	local y = p.Y / (-p.Z * tanY)
	-- p is already in camera space (+X = screen right), so no mirroring here
	return Vector2.new((x + 1) / 2 * size.X, (1 - y) / 2 * size.Y)
end

-- the touch screen area (inside the bezel), laid over the 3D phone
local screen = Instance.new("Frame"); screen.Name = "Screen"; screen.BackgroundColor3 = Color3.fromRGB(12, 10, 22); screen.ZIndex = 3; screen.ClipsDescendants = true; screen.Parent = holder
Instance.new("UICorner", screen).CornerRadius = UDim.new(0.06, 0)
local wall = Instance.new("UIGradient"); wall.Rotation = 120
wall.Color = ColorSequence.new({ColorSequenceKeypoint.new(0, Color3.fromRGB(80, 30, 120)), ColorSequenceKeypoint.new(0.6, Color3.fromRGB(20, 20, 60)), ColorSequenceKeypoint.new(1, Color3.fromRGB(10, 60, 90))})
wall.Parent = screen
-- labels live on their own layer ABOVE the thumb (same rect as the screen, clipped the same way)
local labelLayer = Instance.new("Frame"); labelLayer.Name = "Labels"; labelLayer.BackgroundTransparency = 1; labelLayer.ZIndex = 8; labelLayer.ClipsDescendants = true; labelLayer.Parent = holder
local function layoutScreen()
	local tl = project(Vector3.new(PW * 0.455, PH * 0.47, -PD / 2))
	local br = project(Vector3.new(-PW * 0.455, -PH * 0.47, -PD / 2))
	local pos = vp.AbsolutePosition - holder.AbsolutePosition
	for _, f in ipairs({screen, labelLayer}) do
		f.Position = UDim2.fromOffset(pos.X + tl.X, pos.Y + tl.Y)
		f.Size = UDim2.fromOffset(br.X - tl.X, br.Y - tl.Y)
	end
end
vp:GetPropertyChangedSignal("AbsoluteSize"):Connect(layoutScreen)
holder:GetPropertyChangedSignal("AbsolutePosition"):Connect(layoutScreen)

------------------------------------------------------------------ hand (fingers wrap the right edge, palm below) + thumb
local function skinColor()
	local char = player.Character
	local head = char and char:FindFirstChild("Head")
	if head and head:IsA("BasePart") then return head.Color end
	return Color3.fromRGB(198, 140, 100)
end
local handLayer = Instance.new("Frame"); handLayer.Name = "Hand"; handLayer.BackgroundTransparency = 1; handLayer.Size = UDim2.fromScale(1, 1); handLayer.ZIndex = 4; handLayer.Parent = holder
local skinParts = {}
local function skinPiece(parent, name, size, pos, z, rot, radius)
	local f = Instance.new("Frame"); f.Name = name; f.Size = size; f.Position = pos; f.ZIndex = z; f.Rotation = rot or 0; f.BorderSizePixel = 0
	f.Parent = parent
	Instance.new("UICorner", f).CornerRadius = UDim.new(radius or 0.5, 0)
	local g = Instance.new("UIGradient"); g.Rotation = 90
	g.Transparency = NumberSequence.new(0)
	g.Parent = f
	local s = Instance.new("UIStroke"); s.Thickness = 1.5; s.Transparency = 0.55; s.Parent = f
	table.insert(skinParts, f)
	return f
end
-- palm wraps the lower right corner; four fingers curl over the right edge
local palm = skinPiece(handLayer, "Palm", UDim2.fromScale(0.62, 0.30), UDim2.fromScale(0.38, 0.78), 1, -8, 0.35)
local fingers = {}
for i = 1, 4 do
	fingers[i] = skinPiece(handLayer, "Finger" .. i, UDim2.fromScale(0.34, 0.055), UDim2.fromScale(0.55, 0.36 + i * 0.085), 9, -4 + i * 2, 0.5)
	local nail = Instance.new("Frame"); nail.Name = "Nail"; nail.Size = UDim2.fromScale(0.16, 0.62); nail.Position = UDim2.fromScale(0.02, 0.19)
	nail.BackgroundColor3 = Color3.fromRGB(245, 215, 210); nail.BackgroundTransparency = 0.25; nail.ZIndex = 10; nail.Parent = fingers[i]
	Instance.new("UICorner", nail).CornerRadius = UDim.new(0.5, 0)
end
-- thumb: pivots around its base (bottom right of the screen) and stretches toward the target
local thumbPivot = Instance.new("Frame"); thumbPivot.Name = "ThumbPivot"; thumbPivot.BackgroundTransparency = 1; thumbPivot.Size = UDim2.fromOffset(0, 0); thumbPivot.ZIndex = 6; thumbPivot.Parent = holder
local thumb = skinPiece(thumbPivot, "Thumb", UDim2.fromOffset(62, 200), UDim2.fromOffset(0, 0), 6, 0, 0.5)
thumb.AnchorPoint = Vector2.new(0.5, 1)
local thumbNail = Instance.new("Frame"); thumbNail.Name = "Nail"; thumbNail.AnchorPoint = Vector2.new(0.5, 0); thumbNail.Size = UDim2.new(0.62, 0, 0, 38)
thumbNail.Position = UDim2.new(0.5, 0, 0, 7); thumbNail.BackgroundColor3 = Color3.fromRGB(248, 222, 218); thumbNail.BackgroundTransparency = 0.15; thumbNail.ZIndex = 7; thumbNail.Parent = thumb
Instance.new("UICorner", thumbNail).CornerRadius = UDim.new(0.45, 0)
local crease = Instance.new("Frame"); crease.Name = "Knuckle"; crease.AnchorPoint = Vector2.new(0.5, 0.5); crease.Size = UDim2.new(0.55, 0, 0, 2)
crease.Position = UDim2.new(0.5, 0, 0, 78); crease.BackgroundTransparency = 0.55; crease.ZIndex = 7; crease.BorderSizePixel = 0; crease.Parent = thumb
local function paintSkin()
	local c = skinColor()
	for _, f in ipairs(skinParts) do
		f.BackgroundColor3 = c
		local g = f:FindFirstChildOfClass("UIGradient")
		g.Color = ColorSequence.new({ColorSequenceKeypoint.new(0, c:Lerp(Color3.new(0,0,0), 0.22)), ColorSequenceKeypoint.new(0.45, c:Lerp(Color3.new(1,1,1), 0.12)), ColorSequenceKeypoint.new(1, c:Lerp(Color3.new(0,0,0), 0.3))})
		f:FindFirstChildOfClass("UIStroke").Color = c:Lerp(Color3.new(0,0,0), 0.45)
	end
	thumb:FindFirstChildOfClass("UIGradient").Rotation = 0
	crease.BackgroundColor3 = c:Lerp(Color3.new(0,0,0), 0.5)
end
player:GetAttributeChangedSignal("LookJson"):Connect(paintSkin)
player.CharacterAdded:Connect(function(c) local h = c:WaitForChild("Head", 10); if h then task.wait(1); paintSkin(); h:GetPropertyChangedSignal("Color"):Connect(paintSkin) end end)
paintSkin()

------------------------------------------------------------------ home screen + apps
local function clock()
	local t = Lighting.ClockTime
	local h = math.floor(t); local m = math.floor((t - h) * 60)
	local ap = h >= 12 and "PM" or "AM"
	h = h % 12; if h == 0 then h = 12 end
	return ("%d:%02d %s"):format(h, m, ap)
end
local statusTime = text(labelLayer, clock(), UDim2.new(0.4, 0, 0.035, 0), UDim2.new(0.04, 0, 0.012, 0), Color3.new(1,1,1), 8, FONT_B, Enum.TextXAlignment.Left)
text(labelLayer, "NEON  ●●●  83%", UDim2.new(0.5, 0, 0.03, 0), UDim2.new(0.46, 0, 0.014, 0), Color3.fromRGB(220,220,235), 8, FONT, Enum.TextXAlignment.Right)
local bigTime = text(labelLayer, clock(), UDim2.new(0.9, 0, 0.09, 0), UDim2.new(0.05, 0, 0.07, 0), Color3.new(1,1,1), 8, FONT_B)

local targets = {}       -- {button, labelRef} for thumb + gamepad
local pages = {}
local currentPage = "home"
local homePage = Instance.new("Frame"); homePage.Name = "Home"; homePage.BackgroundTransparency = 1; homePage.Size = UDim2.fromScale(1, 1); homePage.ZIndex = 4; homePage.Parent = screen
local homeLabels = Instance.new("Frame"); homeLabels.Name = "HomeLabels"; homeLabels.BackgroundTransparency = 1; homeLabels.Size = UDim2.fromScale(1, 1); homeLabels.ZIndex = 8; homeLabels.Parent = labelLayer

local tapAndRun -- forward
local apps = {
	{id = "map", name = "Map", glyph = "M", c1 = Color3.fromRGB(40,180,120), c2 = Color3.fromRGB(20,110,80)},
	{id = "garage", name = "Garage", glyph = "G", c1 = Color3.fromRGB(255,140,40), c2 = Color3.fromRGB(200,80,20)},
	{id = "jobs", name = "Jobs", glyph = "$", c1 = Color3.fromRGB(80,200,255), c2 = Color3.fromRGB(30,110,200)},
	{id = "look", name = "Look", glyph = "L", c1 = Color3.fromRGB(255,90,200), c2 = Color3.fromRGB(170,40,150)},
	{id = "home", name = "Home", glyph = "H", c1 = Color3.fromRGB(250,210,80), c2 = Color3.fromRGB(210,150,30)},
	{id = "ride", name = "Ride", glyph = "R", c1 = Color3.fromRGB(150,110,255), c2 = Color3.fromRGB(90,60,200)},
	{id = "settings", name = "Settings", glyph = "S", c1 = Color3.fromRGB(150,150,165), c2 = Color3.fromRGB(80,80,95)},
	{id = "help", name = "Help", glyph = "?", c1 = Color3.fromRGB(240,90,90), c2 = Color3.fromRGB(170,40,50)},
	{id = "arms", name = "Arms", glyph = "A", c1 = Color3.fromRGB(90,90,100), c2 = Color3.fromRGB(30,30,38)},
}
for i, a in ipairs(apps) do
	local col, row = (i - 1) % 4, math.floor((i - 1) / 4)
	local x, y = 0.06 + col * 0.235, 0.24 + row * 0.17
	local icon = Instance.new("TextButton"); icon.Name = a.id; icon.Text = ""; icon.AutoButtonColor = false
	icon.Size = UDim2.new(0.18, 0, 0.1, 0); icon.Position = UDim2.new(x, 0, y, 0); icon.ZIndex = 4; icon.BackgroundColor3 = a.c1; icon.Parent = homePage
	local r = Instance.new("UIAspectRatioConstraint"); r.AspectRatio = 1; r.Parent = icon
	Instance.new("UICorner", icon).CornerRadius = UDim.new(0.26, 0)
	local g = Instance.new("UIGradient"); g.Rotation = 90; g.Color = ColorSequence.new(a.c1, a.c2); g.Parent = icon
	local gl = Instance.new("TextLabel"); gl.BackgroundTransparency = 1; gl.Size = UDim2.fromScale(1, 1); gl.Text = a.glyph; gl.TextScaled = true; gl.Font = FONT_B
	gl.TextColor3 = Color3.new(1,1,1); gl.TextTransparency = 0.05; gl.ZIndex = 5; gl.Parent = icon
	local pad = Instance.new("UIPadding"); pad.PaddingTop = UDim.new(0.2, 0); pad.PaddingBottom = UDim.new(0.2, 0); pad.Parent = gl
	-- the name sits on the label layer, above the thumb
	local nm = text(homeLabels, a.name, UDim2.new(0.22, 0, 0.032, 0), UDim2.new(x - 0.02, 0, y + 0.105, 0), Color3.new(1,1,1), 8, FONT_B)
	nm.TextStrokeTransparency = 0.5
	icon.MouseButton1Click:Connect(function() tapAndRun(icon, a.id) end)
	table.insert(targets, {button = icon, id = a.id})
end

-- simple page factory (content on the screen layer, text on the label layer)
local function page(id, title)
	local p = Instance.new("Frame"); p.Name = id; p.BackgroundTransparency = 1; p.Size = UDim2.fromScale(1, 1); p.ZIndex = 4; p.Visible = false; p.Parent = screen
	local l = Instance.new("Frame"); l.Name = id; l.BackgroundTransparency = 1; l.Size = UDim2.fromScale(1, 1); l.ZIndex = 8; l.Visible = false; l.Parent = labelLayer
	text(l, title, UDim2.new(0.8, 0, 0.05, 0), UDim2.new(0.1, 0, 0.065, 0), Color3.new(1,1,1), 8, FONT_B)
	local back = Instance.new("TextButton"); back.Name = "Back"; back.Text = ""; back.AutoButtonColor = false; back.Size = UDim2.new(0.5, 0, 0.055, 0)
	back.Position = UDim2.new(0.25, 0, 0.92, 0); back.BackgroundColor3 = Color3.fromRGB(255,255,255); back.BackgroundTransparency = 0.82; back.ZIndex = 4; back.Parent = p
	Instance.new("UICorner", back).CornerRadius = UDim.new(0.5, 0)
	text(l, "Back", UDim2.new(0.5, 0, 0.035, 0), UDim2.new(0.25, 0, 0.93, 0), Color3.new(1,1,1), 8, FONT_B)
	back.MouseButton1Click:Connect(function() tapAndRun(back, "back") end)
	pages[id] = {frame = p, labels = l, back = back}
	return p, l
end
local function actionButton(p, l, caption, y, color, id)
	local b = Instance.new("TextButton"); b.Name = id; b.Text = ""; b.AutoButtonColor = false; b.Size = UDim2.new(0.8, 0, 0.075, 0); b.Position = UDim2.new(0.1, 0, y, 0)
	b.BackgroundColor3 = color; b.ZIndex = 4; b.Parent = p
	Instance.new("UICorner", b).CornerRadius = UDim.new(0.3, 0)
	local t = text(l, caption, UDim2.new(0.7, 0, 0.04, 0), UDim2.new(0.15, 0, y + 0.018, 0), Color3.new(1,1,1), 8, FONT_B)
	b.MouseButton1Click:Connect(function() tapAndRun(b, id) end)
	return b, t
end

-- MAP
local mapP, mapL = page("map", "Map")
local mapArea = Instance.new("Frame"); mapArea.Size = UDim2.new(0.9, 0, 0.72, 0); mapArea.Position = UDim2.new(0.05, 0, 0.14, 0); mapArea.BackgroundColor3 = Color3.fromRGB(30, 110, 170); mapArea.ZIndex = 4; mapArea.ClipsDescendants = true; mapArea.Parent = mapP
Instance.new("UICorner", mapArea).CornerRadius = UDim.new(0.04, 0)
local WX0, WX1, WZ0, WZ1 = -17000, 13000, -16000, 14000
local function mapXY(x, z) return UDim2.fromScale((x - WX0) / (WX1 - WX0), (z - WZ0) / (WZ1 - WZ0)) end
local function mapRect(x0, z0, x1, z1, color)
	local f = Instance.new("Frame"); f.BorderSizePixel = 0; f.BackgroundColor3 = color; f.ZIndex = 4
	local a, b = mapXY(x0, z0), mapXY(x1, z1)
	f.Position = a; f.Size = UDim2.fromScale(b.X.Scale - a.X.Scale, b.Y.Scale - a.Y.Scale); f.Parent = mapArea
	return f
end
mapRect(-12000, -11000, 5000, 9000, Color3.fromRGB(90, 150, 80))
mapRect(-12000, -11000, -4500, -4500, Color3.fromRGB(120, 120, 115))  -- mountains
mapRect(-12000, -4500, -4500, 2500, Color3.fromRGB(220, 185, 120))    -- desert
mapRect(-12000, 2500, -4500, 9000, Color3.fromRGB(70, 95, 60))        -- swamp
mapRect(1500, -1000, 3700, 1000, Color3.fromRGB(70, 60, 90))          -- downtown
mapRect(1150, -5800, 3600, -1250, Color3.fromRGB(150, 175, 120))      -- Palmgrove
mapRect(4000, -11000, 5000, 6500, Color3.fromRGB(240, 215, 160))      -- beach
mapRect(-4800, -6470, 5000, -6330, Color3.fromRGB(60, 150, 210))      -- river
-- islands (positions shipped in workspace.NeonCoast.IslandData: X, radius, Z)
task.spawn(function()
	local data = workspace:WaitForChild("NeonCoast"):WaitForChild("IslandData", 10)
	local list = data and data:GetChildren() or {}
	local big = {{-15000, -1500, 1000}, {-15300, -9300, 750}, {-14900, 7100, 870}, {-4300, 12600, 800}, {11600, -6200, 520}, {-2600, -13900, 800}}
	for _, v in ipairs(list) do table.insert(big, {v.Value.X, v.Value.Z, v.Value.Y}) end
	for _, b in ipairs(big) do
		local d = Instance.new("Frame"); d.BorderSizePixel = 0; d.AnchorPoint = Vector2.new(0.5, 0.5); d.BackgroundColor3 = Color3.fromRGB(200, 190, 130); d.ZIndex = 4
		local s = math.max(0.006, b[3] * 2 / (WX1 - WX0))
		d.Size = UDim2.fromScale(s, s * (WX1 - WX0) / (WZ1 - WZ0)); d.Position = mapXY(b[1], b[2]); d.Parent = mapArea
		Instance.new("UICorner", d).CornerRadius = UDim.new(1, 0)
	end
	-- barrier islands off the beach
	for _, seg in ipairs({{6400, -10300, -7200}, {6450, -6800, -4300}, {6380, -3900, -1600}}) do
		local a, b2 = mapXY(seg[1] - 150, seg[2]), mapXY(seg[1] + 150, seg[3])
		local f = Instance.new("Frame"); f.BorderSizePixel = 0; f.BackgroundColor3 = Color3.fromRGB(230, 205, 150); f.ZIndex = 4
		f.Position = a; f.Size = UDim2.fromScale(b2.X.Scale - a.X.Scale, b2.Y.Scale - a.Y.Scale); f.Parent = mapArea
	end
end)
local homeDot = Instance.new("Frame"); homeDot.Size = UDim2.fromOffset(10, 10); homeDot.AnchorPoint = Vector2.new(0.5, 0.5); homeDot.BackgroundColor3 = Color3.fromRGB(250, 210, 80); homeDot.ZIndex = 5; homeDot.Position = mapXY(2186, -2210); homeDot.Parent = mapArea
Instance.new("UICorner", homeDot).CornerRadius = UDim.new(1, 0)
local meDot = Instance.new("Frame"); meDot.Size = UDim2.fromOffset(12, 12); meDot.AnchorPoint = Vector2.new(0.5, 0.5); meDot.BackgroundColor3 = PINK; meDot.ZIndex = 6; meDot.Parent = mapArea
Instance.new("UICorner", meDot).CornerRadius = UDim.new(1, 0)
local ms = Instance.new("UIStroke"); ms.Color = Color3.new(1,1,1); ms.Thickness = 2; ms.Parent = meDot
text(mapL, "you", UDim2.new(0.3, 0, 0.03, 0), UDim2.new(0.05, 0, 0.87, 0), PINK, 8, FONT_B, Enum.TextXAlignment.Left)
text(mapL, "home", UDim2.new(0.3, 0, 0.03, 0), UDim2.new(0.65, 0, 0.87, 0), Color3.fromRGB(250,210,80), 8, FONT_B, Enum.TextXAlignment.Right)

-- GARAGE
local garP, garL = page("garage", "Garage")
local garRows = {}
local function renderGarage(list)
	for _, r in ipairs(garRows) do r:Destroy() end
	garRows = {}
	if #list == 0 then
		local t = text(garL, "No cars yet. Buy one at your garage, or drive any car up to your garage door.", UDim2.new(0.8, 0, 0.12, 0), UDim2.new(0.1, 0, 0.3, 0), Color3.fromRGB(210,200,230), 8, FONT)
		t.TextWrapped = true; table.insert(garRows, t)
		return
	end
	for i, e in ipairs(list) do
		if i > 6 then break end
		local name = e.template
		for _, c in ipairs(HomeConfig.Cars) do if c.template == e.template then name = c.name end end
		local b, t = actionButton(garP, garL, (e.out and "(out) " or "Drive: ") .. name, 0.14 + (i - 1) * 0.11, e.out and Color3.fromRGB(70,60,90) or Color3.fromRGB(40,120,190), "drive" .. e.index)
		b:SetAttribute("Index", e.index)
		b:SetAttribute("Out", e.out)
		table.insert(garRows, b); table.insert(garRows, t)
	end
end

-- JOBS
local jobsP, jobsL = page("jobs", "Jobs")
actionButton(jobsP, jobsL, "Start a delivery", 0.2, Color3.fromRGB(40,150,90), "startjob")
local jobStatus = text(jobsL, "", UDim2.new(0.8, 0, 0.1, 0), UDim2.new(0.1, 0, 0.33, 0), Color3.fromRGB(210,200,230), 8, FONT)
jobStatus.TextWrapped = true

-- SETTINGS
local setP, setL = page("settings", "Settings")
local fovLabel = text(setL, "", UDim2.new(0.8, 0, 0.04, 0), UDim2.new(0.1, 0, 0.16, 0), Color3.new(1,1,1), 8, FONT_B)
actionButton(setP, setL, "Field of view -", 0.22, Color3.fromRGB(70,60,110), "fovdown")
actionButton(setP, setL, "Field of view +", 0.32, Color3.fromRGB(70,60,110), "fovup")
local hintBtn, hintText = actionButton(setP, setL, "Controls hint: on", 0.45, Color3.fromRGB(70,60,110), "hint")

-- HELP
local helpP, helpL = page("help", "Help")
local helpT = text(helpL, "WASD drive or walk\nF drive  •  E ride / interact\nG doors  •  V call a ride\nShift nitro  •  Space hop out\nC character  •  M menu\nUp arrow / P phone\n1-9 guns  •  LMB fire  •  RMB aim  •  R reload", UDim2.new(0.84, 0, 0.5, 0), UDim2.new(0.08, 0, 0.16, 0), Color3.new(1,1,1), 8, FONT)
helpT.TextWrapped = true

local function showPage(id)
	currentPage = id
	homePage.Visible = id == "home"; homeLabels.Visible = id == "home"; bigTime.Visible = id == "home"
	for pid, p in pairs(pages) do p.frame.Visible = pid == id; p.labels.Visible = pid == id end
end

------------------------------------------------------------------ open / close
local isOpen = false
local function setOpen(open)
	if open == isOpen then return end
	if open then
		local hum = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
		if hum and hum.SeatPart and hum.SeatPart:IsA("VehicleSeat") then return end -- eyes on the road
	end
	isOpen = open
	Remotes.PhoneState:FireServer(open)
	if open then
		showPage("home")
		holder.Visible = true
		holder.Position = UDim2.new(1, -40, 1, holder.AbsoluteSize.Y + 40)
		TweenService:Create(holder, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Position = UDim2.new(1, -40, 1, 40)}):Play()
		task.delay(0.05, layoutScreen)
	else
		local tw = TweenService:Create(holder, TweenInfo.new(0.25, Enum.EasingStyle.Quad, Enum.EasingDirection.In), {Position = UDim2.new(1, -40, 1, holder.AbsoluteSize.Y + 60)})
		tw:Play()
		tw.Completed:Connect(function() if not isOpen then holder.Visible = false end end)
	end
end
Signals.OpenPhone.Event:Connect(function(appId) setOpen(true); if appId then task.delay(0.4, function() showPage(appId) end) end end)

------------------------------------------------------------------ thumb motion
local thumbBase = Vector2.new()
local thumbTip = Vector2.new()
local tapUntil = 0
local selected = 1
local usingPad = false
local function screenRect()
	return screen.AbsolutePosition, screen.AbsoluteSize
end
local function restPoint()
	local pos, size = screenRect()
	return pos + Vector2.new(size.X * 0.62, size.Y * 0.78)
end
local function buttonCenter(b)
	return b.AbsolutePosition + b.AbsoluteSize / 2
end
RunService.RenderStepped:Connect(function(dt)
	if not holder.Visible then return end
	statusTime.Text = clock(); bigTime.Text = clock()
	local pos, size = screenRect()
	-- the thumb's knuckle sits just off the bottom-right of the screen
	thumbBase = pos + Vector2.new(size.X * 1.02, size.Y * 1.04)
	local goal
	local mouse = UIS:GetMouseLocation() - Vector2.new(0, 0)
	local inside = mouse.X > pos.X and mouse.X < pos.X + size.X and mouse.Y > pos.Y and mouse.Y < pos.Y + size.Y
	if usingPad then
		local list = currentPage == "home" and targets or {}
		local t = list[selected]
		goal = t and buttonCenter(t.button) or restPoint()
	elseif inside then
		goal = mouse
	else
		goal = restPoint()
	end
	thumbTip = thumbTip:Lerp(goal, math.min(1, dt * 14))
	local d = thumbTip - thumbBase
	local len = math.clamp(d.Magnitude + 26, 120, size.Y * 0.95)
	if os.clock() < tapUntil then len -= 10 end
	local hp = holder.AbsolutePosition
	thumbPivot.Position = UDim2.fromOffset(thumbBase.X - hp.X, thumbBase.Y - hp.Y)
	thumbPivot.Rotation = math.deg(math.atan2(d.X, -d.Y))
	thumb.Size = UDim2.fromOffset(math.clamp(size.X * 0.2, 44, 70), len)
	-- the pressing pad darkens slightly on a tap
	thumbNail.BackgroundTransparency = os.clock() < tapUntil and 0.45 or 0.15
	-- live map dot
	if currentPage == "map" then
		local hrp = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
		if hrp then meDot.Position = mapXY(hrp.Position.X, hrp.Position.Z) end
	end
	if currentPage == "jobs" then
		local t = player:GetAttribute("JobTarget")
		jobStatus.Text = t and ("Active delivery: $" .. tostring(player:GetAttribute("JobReward") or 0) .. " reward. Follow the blue beam.") or "No active delivery."
	end
	if currentPage == "settings" then fovLabel.Text = ("Field of view: %d"):format(workspace.CurrentCamera.FieldOfView) end
end)

-- a tap: the thumb jumps to the button, presses, then the action runs
tapAndRun = function(button, id)
	if not isOpen then return end
	thumbTip = buttonCenter(button)
	tapUntil = os.clock() + 0.16
	task.wait(0.17)
	if id == "back" then showPage("home")
	elseif id == "map" then showPage("map")
	elseif id == "garage" then
		showPage("garage")
		local ok, list = Remotes.GarageAction:InvokeServer("list")
		if ok then renderGarage(list) end
	elseif id:sub(1, 5) == "drive" then
		if button:GetAttribute("Out") then return end
		setOpen(false)
		Remotes.GarageAction:InvokeServer("driveout", button:GetAttribute("Index"))
	elseif id == "jobs" then showPage("jobs")
	elseif id == "startjob" then Remotes.StartJob:FireServer()
	elseif id == "look" then setOpen(false); Signals.OpenCharacterStudio:Fire()
	elseif id == "home" then setOpen(false); Remotes.GoHome:FireServer()
	elseif id == "ride" then setOpen(false); Remotes.SpawnCar:FireServer()
	elseif id == "arms" then setOpen(false); task.delay(0.3, function() Signals.OpenArmory:Fire() end)
	elseif id == "settings" then showPage("settings")
	elseif id == "fovdown" then workspace.CurrentCamera.FieldOfView = math.max(60, workspace.CurrentCamera.FieldOfView - 5)
	elseif id == "fovup" then workspace.CurrentCamera.FieldOfView = math.min(100, workspace.CurrentCamera.FieldOfView + 5)
	elseif id == "hint" then
		local hud = player.PlayerGui:FindFirstChild("NeonCoastHUD")
		if hud then for _, l in ipairs(hud:GetChildren()) do if l:IsA("TextLabel") and l.Text:find("get a car") then l.Visible = not l.Visible; hintText.Text = "Controls hint: " .. (l.Visible and "on" or "off") end end end
	elseif id == "help" then showPage("help")
	end
end

------------------------------------------------------------------ main menu (M)
local menu = Instance.new("Frame"); menu.Name = "Menu"; menu.AnchorPoint = Vector2.new(0.5, 0.5); menu.Position = UDim2.fromScale(0.5, 0.5); menu.Size = UDim2.fromOffset(380, 470)
menu.BackgroundColor3 = Color3.fromRGB(16, 10, 28); menu.BackgroundTransparency = 0.05; menu.Visible = false; menu.ZIndex = 20; menu.Parent = gui
Instance.new("UICorner", menu).CornerRadius = UDim.new(0, 18)
local mst = Instance.new("UIStroke"); mst.Color = PINK; mst.Thickness = 2; mst.Parent = menu
text(menu, "NEON COAST", UDim2.new(1, -40, 0, 46), UDim2.fromOffset(20, 18), PINK, 21, Enum.Font.FredokaOne)
local function menuButton(caption, i, fn)
	local b = Instance.new("TextButton"); b.Text = caption; b.Font = Enum.Font.FredokaOne; b.TextScaled = true; b.TextColor3 = Color3.new(1,1,1)
	b.Size = UDim2.new(1, -60, 0, 50); b.Position = UDim2.fromOffset(30, 80 + (i - 1) * 62); b.BackgroundColor3 = Color3.fromRGB(60, 40, 90); b.ZIndex = 21; b.Parent = menu
	Instance.new("UICorner", b).CornerRadius = UDim.new(0, 12)
	local pad = Instance.new("UIPadding"); pad.PaddingTop = UDim.new(0, 10); pad.PaddingBottom = UDim.new(0, 10); pad.Parent = b
	b.MouseButton1Click:Connect(function() menu.Visible = false; fn() end)
end
menuButton("Resume", 1, function() end)
menuButton("Phone", 2, function() setOpen(true) end)
menuButton("Map", 3, function() setOpen(true); task.delay(0.4, function() showPage("map") end) end)
menuButton("Character Studio", 4, function() Signals.OpenCharacterStudio:Fire() end)
menuButton("Settings", 5, function() setOpen(true); task.delay(0.4, function() showPage("settings") end) end)
menuButton("Controls", 6, function() setOpen(true); task.delay(0.4, function() showPage("help") end) end)

------------------------------------------------------------------ input
UIS.InputBegan:Connect(function(input, processed)
	if processed then return end
	if input.KeyCode == Enum.KeyCode.Up or input.KeyCode == Enum.KeyCode.P then
		if input.KeyCode == Enum.KeyCode.Up and isOpen and usingPad then return end
		setOpen(not isOpen)
	elseif input.KeyCode == Enum.KeyCode.M then
		menu.Visible = not menu.Visible
	elseif input.KeyCode == Enum.KeyCode.Backspace and isOpen then
		if currentPage ~= "home" then showPage("home") else setOpen(false) end
	elseif isOpen and currentPage == "home" and (input.KeyCode == Enum.KeyCode.Right or input.KeyCode == Enum.KeyCode.Left or input.KeyCode == Enum.KeyCode.Down or input.KeyCode == Enum.KeyCode.DPadRight or input.KeyCode == Enum.KeyCode.DPadLeft or input.KeyCode == Enum.KeyCode.DPadDown or input.KeyCode == Enum.KeyCode.DPadUp) then
		usingPad = true
		local k = input.KeyCode
		if k == Enum.KeyCode.Right or k == Enum.KeyCode.DPadRight then selected = math.min(#targets, selected + 1)
		elseif k == Enum.KeyCode.Left or k == Enum.KeyCode.DPadLeft then selected = math.max(1, selected - 1)
		elseif k == Enum.KeyCode.Down or k == Enum.KeyCode.DPadDown then selected = math.min(#targets, selected + 4)
		elseif k == Enum.KeyCode.DPadUp then selected = math.max(1, selected - 4) end
	elseif isOpen and usingPad and (input.KeyCode == Enum.KeyCode.Return or input.KeyCode == Enum.KeyCode.ButtonA) and currentPage == "home" then
		local t = targets[selected]
		if t then task.spawn(tapAndRun, t.button, t.id) end
	end
end)
UIS.InputChanged:Connect(function(input)
	if input.UserInputType == Enum.UserInputType.MouseMovement or input.UserInputType == Enum.UserInputType.Touch then usingPad = false end
end)
-- phone closes if you get in the driver's seat
RunService.Heartbeat:Connect(function()
	if not isOpen then return end
	local hum = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
	if hum and hum.SeatPart and hum.SeatPart:IsA("VehicleSeat") then setOpen(false) end
end)
player.CharacterAdded:Connect(function() if isOpen then isOpen = false; holder.Visible = false end end)
