--!nonstrict
-- LookStudioClient (LocalScript in StarterPlayerScripts): the Character Studio screen.
-- Opens from any closet ("Change outfit" fires ReplicatedStorage.LocalSignals.OpenCharacterStudio), on a player's
-- very first spawn (so new players make their character), and optionally from a hotkey.
--   Left: a live 3D preview of YOUR body (drag to spin, Face / Body zoom) wearing what you're trying on.
--   Right: Looks (one-tap preset outfits by collection), Body / Clothes / Headwear / Bling / Extras (every slot),
--          Saved (8 outfit slots). Search, collection filter, Trending and Owned filters, two colour rows per item.
--   Trying things on is free; "Wear" buys anything you don't own yet (Cash) and puts it on for everyone.
-- Attributes on this script: HotKey (string, KeyCode name, "" = none), OpenOnFirstJoin (bool, default true).
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local UIS = game:GetService("UserInputService")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local GuiService = game:GetService("GuiService")

local player = Players.LocalPlayer
local Catalog = require(RS:WaitForChild("NCLookCatalog"))
local Builder = require(RS:WaitForChild("NCLookBuilder"))
local Remotes = RS:WaitForChild("Remotes")
local LookRF = Remotes:WaitForChild("LookStudio")

local Signals = RS:FindFirstChild("LocalSignals")
if not Signals then
	Signals = Instance.new("Folder")
	Signals.Name = "LocalSignals"
	Signals.Parent = RS -- client-side only; the closet script finds it here
end
local OpenSig = Signals:FindFirstChild("OpenCharacterStudio")
if not OpenSig then
	OpenSig = Instance.new("BindableEvent")
	OpenSig.Name = "OpenCharacterStudio"
	OpenSig.Parent = Signals
end
if script:GetAttribute("OpenOnFirstJoin") == nil then
	script:SetAttribute("OpenOnFirstJoin", true)
end

---------------------------------------------------------------------------------------------------- theme
local COL = {
	bg = Color3.fromRGB(12, 14, 20), panel = Color3.fromRGB(22, 25, 34), card = Color3.fromRGB(32, 36, 48),
	cardHi = Color3.fromRGB(44, 50, 66), text = Color3.fromRGB(240, 242, 248), dim = Color3.fromRGB(150, 156, 172),
	accent = Color3.fromRGB(0, 230, 200), pink = Color3.fromRGB(255, 60, 200), gold = Color3.fromRGB(240, 196, 80),
	bad = Color3.fromRGB(255, 90, 90), good = Color3.fromRGB(110, 230, 140),
}
local FONT, FONT_B = Enum.Font.GothamMedium, Enum.Font.GothamBlack

local function new(class, props, children)
	local o = Instance.new(class)
	for k, v in pairs(props or {}) do
		o[k] = v
	end
	for _, c in ipairs(children or {}) do
		c.Parent = o
	end
	return o
end
local function corner(r)
	return new("UICorner", { CornerRadius = UDim.new(0, r or 10) })
end
local function stroke(c, t)
	return new("UIStroke", { Color = c or COL.cardHi, Thickness = t or 1, ApplyStrokeMode = Enum.ApplyStrokeMode.Border })
end
local function pad(p)
	return new("UIPadding", { PaddingLeft = UDim.new(0, p), PaddingRight = UDim.new(0, p), PaddingTop = UDim.new(0, p), PaddingBottom = UDim.new(0, p) })
end
local function label(text, size, color, font, props)
	local l = new("TextLabel", { BackgroundTransparency = 1, Text = text, TextSize = size or 14, TextColor3 = color or COL.text,
		Font = font or FONT, TextXAlignment = Enum.TextXAlignment.Left, TextWrapped = true })
	for k, v in pairs(props or {}) do
		l[k] = v
	end
	return l
end
local function button(text, color, props)
	local b = new("TextButton", { AutoButtonColor = true, BackgroundColor3 = color or COL.card, Text = text, TextSize = 15,
		TextColor3 = COL.text, Font = FONT_B }, { corner(8) })
	for k, v in pairs(props or {}) do
		b[k] = v
	end
	return b
end

---------------------------------------------------------------------------------------------------- state
local S = {
	server = nil, -- last state from the server { look, owned, outfits, cash, free }
	owned = {},
	draft = {}, -- what you're trying on
	tab = "Looks",
	slot = nil,
	search = "",
	collection = nil,
	trendOnly = false,
	ownedOnly = false,
	open = false,
}

local function copyLook(look)
	local out = {}
	for k, e in pairs(look or {}) do
		out[k] = { id = e.id, c1 = e.c1, c2 = e.c2 }
	end
	return out
end

local function refreshServer(st)
	if type(st) ~= "table" then
		return
	end
	S.server = st
	S.owned = {}
	for _, id in ipairs(st.owned or {}) do
		S.owned[id] = true
	end
end

---------------------------------------------------------------------------------------------------- screen
local gui = new("ScreenGui", { Name = "NCLookStudio", ResetOnSpawn = false, IgnoreGuiInset = true, Enabled = false, DisplayOrder = 20,
	ZIndexBehavior = Enum.ZIndexBehavior.Sibling })
local scale = new("UIScale", { Parent = gui })
local root = new("Frame", { Size = UDim2.fromScale(1, 1), BackgroundColor3 = COL.bg, BackgroundTransparency = 0.08, Parent = gui })
new("UIGradient", { Rotation = 90, Color = ColorSequence.new(Color3.fromRGB(18, 20, 30), Color3.fromRGB(8, 9, 14)), Parent = root })

-- preview side
local left = new("Frame", { BackgroundTransparency = 1, Parent = root })
local vp = new("ViewportFrame", { Size = UDim2.new(1, 0, 1, -118), BackgroundColor3 = COL.panel, Ambient = Color3.fromRGB(150, 150, 160),
	LightColor = Color3.fromRGB(255, 246, 232), LightDirection = Vector3.new(-0.4, -0.8, -0.6), Parent = left }, { corner(16) })
new("UIGradient", { Rotation = 90, Color = ColorSequence.new(Color3.fromRGB(40, 46, 64), Color3.fromRGB(16, 18, 26)), Parent = vp })
local world = new("WorldModel", { Parent = vp })
local cam = new("Camera", { FieldOfView = 30, Parent = vp })
vp.CurrentCamera = cam
local title = label("CHARACTER STUDIO", 22, COL.text, FONT_B, { Position = UDim2.fromOffset(16, 12), Size = UDim2.new(1, -32, 0, 28), Parent = vp })
local hint = label("drag to spin", 12, COL.dim, FONT, { Position = UDim2.fromOffset(16, 40), Size = UDim2.new(1, -32, 0, 16), Parent = vp })
local zoomRow = new("Frame", { BackgroundTransparency = 1, Position = UDim2.new(0, 12, 1, -48), Size = UDim2.new(1, -24, 0, 36), Parent = vp },
	{ new("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 8) }) })
local bBody = button("Body", COL.card, { Size = UDim2.fromOffset(70, 36), Parent = zoomRow })
local bFace = button("Face", COL.card, { Size = UDim2.fromOffset(70, 36), Parent = zoomRow })
local bRandom = button("🎲 Random", COL.card, { Size = UDim2.fromOffset(110, 36), Parent = zoomRow })

local footer = new("Frame", { BackgroundColor3 = COL.panel, Position = UDim2.new(0, 0, 1, -108), Size = UDim2.new(1, 0, 0, 108), Parent = left }, { corner(16), pad(12) })
local costLabel = label("", 16, COL.text, FONT_B, { Size = UDim2.new(1, -100, 0, 22), Parent = footer })
local cashLabel = label("", 13, COL.dim, FONT, { Position = UDim2.fromOffset(0, 22), Size = UDim2.new(1, -100, 0, 18), Parent = footer })
local bWear = button("WEAR IT", COL.accent, { Position = UDim2.new(0, 0, 1, -44), Size = UDim2.new(0.62, -6, 0, 44), TextColor3 = COL.bg, TextSize = 18, Parent = footer })
local bReset = button("Undo all", COL.card, { Position = UDim2.new(0.62, 6, 1, -44), Size = UDim2.new(0.38, -6, 0, 44), Parent = footer })
local bClose = button("✕", COL.card, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, 0, 0, 0), Size = UDim2.fromOffset(40, 40), TextSize = 18, Parent = footer })

-- browser side
local right = new("Frame", { BackgroundColor3 = COL.panel, Parent = root }, { corner(16), pad(12) })
local tabsBar = new("ScrollingFrame", { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, 40), CanvasSize = UDim2.new(), AutomaticCanvasSize = Enum.AutomaticSize.X,
	ScrollingDirection = Enum.ScrollingDirection.X, ScrollBarThickness = 0, Parent = right },
	{ new("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 6), SortOrder = Enum.SortOrder.LayoutOrder }) })
local slotBar = new("ScrollingFrame", { BackgroundTransparency = 1, Position = UDim2.fromOffset(0, 46), Size = UDim2.new(1, 0, 0, 34), CanvasSize = UDim2.new(),
	AutomaticCanvasSize = Enum.AutomaticSize.X, ScrollingDirection = Enum.ScrollingDirection.X, ScrollBarThickness = 0, Parent = right },
	{ new("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 6), SortOrder = Enum.SortOrder.LayoutOrder }) })
local filterBar = new("Frame", { BackgroundTransparency = 1, Position = UDim2.fromOffset(0, 86), Size = UDim2.new(1, 0, 0, 34), Parent = right })
local searchBox = new("TextBox", { BackgroundColor3 = COL.card, PlaceholderText = "🔎 search (chain, locs, suit...)", Text = "", ClearTextOnFocus = false,
	TextColor3 = COL.text, PlaceholderColor3 = COL.dim, Font = FONT, TextSize = 14, Size = UDim2.new(0.4, -6, 1, 0), TextXAlignment = Enum.TextXAlignment.Left,
	Parent = filterBar }, { corner(8), pad(8) })
local bCollection = button("All worlds ▾", COL.card, { Position = UDim2.new(0.4, 0, 0, 0), Size = UDim2.new(0.28, -6, 1, 0), TextSize = 13, Parent = filterBar })
local bTrend = button("🔥 Trending", COL.card, { Position = UDim2.new(0.68, 0, 0, 0), Size = UDim2.new(0.18, -6, 1, 0), TextSize = 13, Parent = filterBar })
local bOwned = button("Owned", COL.card, { Position = UDim2.new(0.86, 0, 0, 0), Size = UDim2.new(0.14, 0, 1, 0), TextSize = 13, Parent = filterBar })

local grid = new("ScrollingFrame", { BackgroundTransparency = 1, Position = UDim2.fromOffset(0, 128), Size = UDim2.new(1, 0, 1, -128 - 112), CanvasSize = UDim2.new(),
	AutomaticCanvasSize = Enum.AutomaticSize.Y, ScrollBarThickness = 6, ScrollBarImageColor3 = COL.cardHi, Parent = right })
local gridLayout = new("UIGridLayout", { CellSize = UDim2.fromOffset(150, 96), CellPadding = UDim2.fromOffset(8, 8), SortOrder = Enum.SortOrder.LayoutOrder, Parent = grid })
new("UIPadding", { PaddingRight = UDim.new(0, 8), PaddingBottom = UDim.new(0, 8), Parent = grid })

local colourPanel = new("Frame", { BackgroundColor3 = COL.card, Position = UDim2.new(0, 0, 1, -104), Size = UDim2.new(1, 0, 0, 104), Parent = right }, { corner(12), pad(8) })
local selLabel = label("", 14, COL.text, FONT_B, { Size = UDim2.new(1, -110, 0, 20), Parent = colourPanel })
local bRemove = button("Take off", COL.cardHi, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, 0, 0, 0), Size = UDim2.fromOffset(100, 24), TextSize = 12, Parent = colourPanel })
local function swatchRow(y)
	local row = new("ScrollingFrame", { BackgroundTransparency = 1, Position = UDim2.fromOffset(0, y), Size = UDim2.new(1, 0, 0, 34), CanvasSize = UDim2.new(),
		AutomaticCanvasSize = Enum.AutomaticSize.X, ScrollingDirection = Enum.ScrollingDirection.X, ScrollBarThickness = 0, Parent = colourPanel },
		{ new("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 5), VerticalAlignment = Enum.VerticalAlignment.Center }) })
	return row
end
local row1 = swatchRow(24)
local row2 = swatchRow(60)

local toast = label("", 15, COL.text, FONT_B, { AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0, 14), Size = UDim2.fromOffset(420, 40),
	BackgroundColor3 = COL.card, BackgroundTransparency = 0, TextXAlignment = Enum.TextXAlignment.Center, Visible = false, ZIndex = 10, Parent = root })
corner(10).Parent = toast

-- collection picker (overlay list)
local picker = new("ScrollingFrame", { BackgroundColor3 = COL.panel, Visible = false, ZIndex = 20, Size = UDim2.fromOffset(260, 360), CanvasSize = UDim2.new(),
	AutomaticCanvasSize = Enum.AutomaticSize.Y, ScrollBarThickness = 6, Parent = root }, { corner(12), stroke(COL.cardHi), pad(8),
	new("UIListLayout", { Padding = UDim.new(0, 4), SortOrder = Enum.SortOrder.LayoutOrder }) })

gui.Parent = player:WaitForChild("PlayerGui")

local toastToken = 0
local function say(text, color)
	toastToken += 1
	local my = toastToken
	toast.Text = text
	toast.TextColor3 = color or COL.text
	toast.Visible = true
	task.delay(2.4, function()
		if my == toastToken then
			toast.Visible = false
		end
	end)
end

---------------------------------------------------------------------------------------------------- layout (desktop / phone)
local function layout()
	local cam0 = workspace.CurrentCamera
	local vs = cam0 and cam0.ViewportSize or Vector2.new(1280, 720)
	local portrait = vs.Y > vs.X * 1.05
	local s = math.clamp(math.min(vs.X / 1280, vs.Y / 720), 0.62, 1.25)
	if portrait then
		s = math.clamp(vs.X / 520, 0.6, 1.2)
	end
	scale.Scale = s
	local W, H = vs.X / s, vs.Y / s
	local inset = GuiService:GetGuiInset().Y / s
	local m = 14
	if portrait then
		left.Position = UDim2.fromOffset(m, inset + m)
		left.Size = UDim2.fromOffset(W - m * 2, H * 0.42 - inset)
		right.Position = UDim2.fromOffset(m, H * 0.42 + m)
		right.Size = UDim2.fromOffset(W - m * 2, H * 0.58 - m * 2)
	else
		local lw = math.clamp(W * 0.36, 300, 520)
		left.Position = UDim2.fromOffset(m, inset + m)
		left.Size = UDim2.fromOffset(lw, H - inset - m * 2)
		right.Position = UDim2.fromOffset(lw + m * 2, inset + m)
		right.Size = UDim2.fromOffset(W - lw - m * 3, H - inset - m * 2)
	end
	local gw = right.Size.X.Offset - 24 - 14
	local cols = math.max(2, math.floor(gw / 158))
	gridLayout.CellSize = UDim2.fromOffset(math.floor((gw - (cols - 1) * 8) / cols), 96)
	picker.Position = UDim2.fromOffset(right.Position.X.Offset + right.Size.X.Offset * 0.4, right.Position.Y.Offset + 128)
end

---------------------------------------------------------------------------------------------------- preview mannequin
local dummy
local yaw = math.rad(200)
local zoom = "body"
local function buildDummy()
	if dummy then
		dummy:Destroy()
		dummy = nil
	end
	local char = player.Character
	if not char then
		return
	end
	local was = char.Archivable
	char.Archivable = true
	local ok, c = pcall(function()
		return char:Clone()
	end)
	char.Archivable = was
	if not ok or not c then
		return
	end
	for _, d in ipairs(c:GetDescendants()) do
		if d:IsA("Script") or d:IsA("LocalScript") or d:IsA("ModuleScript") or d:IsA("Sound") or d:IsA("ForceField") or d:IsA("Tool") then
			d:Destroy()
		elseif d:IsA("BasePart") then
			d.Anchored = false
		end
	end
	local hrp = c:FindFirstChild("HumanoidRootPart")
	if hrp then
		hrp.Anchored = true
		c.PrimaryPart = hrp
		c:PivotTo(CFrame.new(0, 3.7, 0))
	end
	local hum = c:FindFirstChildOfClass("Humanoid")
	if hum then
		hum.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
		hum.PlatformStand = true
	end
	c.Parent = world
	dummy = c
end

local function placeCamera()
	if not dummy then
		return
	end
	local cf, size = dummy:GetBoundingBox()
	local head = dummy:FindFirstChild("Head")
	local target, dist
	if zoom == "face" and head then
		target = head.Position + Vector3.new(0, 0.05, 0)
		dist = head.Size.Y * 6.5
	else
		target = cf.Position
		dist = math.max(size.Y, 4) * 2.15
	end
	cam.CFrame = CFrame.new(target + Vector3.new(math.sin(yaw) * dist, (zoom == "face") and 0.1 or size.Y * 0.08, math.cos(yaw) * dist), target)
end

local function renderDraft()
	if not dummy or not dummy.Parent then
		buildDummy()
	end
	if dummy then
		local ok, err = pcall(Builder.Apply, dummy, S.draft, Catalog, { sparkle = true })
		if not ok then
			warn("LookStudio preview: " .. tostring(err))
		end
		placeCamera()
	end
end

-- drag to spin
local dragging, lastX = false, 0
vp.InputBegan:Connect(function(input)
	if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
		dragging, lastX = true, input.Position.X
	end
end)
UIS.InputChanged:Connect(function(input)
	if dragging and (input.UserInputType == Enum.UserInputType.MouseMovement or input.UserInputType == Enum.UserInputType.Touch) then
		yaw -= (input.Position.X - lastX) * 0.012
		lastX = input.Position.X
		placeCamera()
	end
end)
UIS.InputEnded:Connect(function(input)
	if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
		dragging = false
	end
end)
bBody.MouseButton1Click:Connect(function()
	zoom = "body"
	placeCamera()
end)
bFace.MouseButton1Click:Connect(function()
	zoom = "face"
	yaw = math.rad(180)
	placeCamera()
end)
-- a slow idle spin when nobody's touching it
RunService.RenderStepped:Connect(function(dt)
	if S.open and not dragging and zoom == "body" then
		yaw += dt * 0.12
		placeCamera()
	end
end)

---------------------------------------------------------------------------------------------------- cost / footer
local function updateFooter()
	local cost, missing = Catalog.Cost(S.draft, S.owned)
	local free = S.server and S.server.free
	if free then
		costLabel.Text = #missing > 0 and ("Unlock %d new item%s: FREE"):format(#missing, #missing == 1 and "" or "s") or "Everything here is yours"
	else
		costLabel.Text = cost > 0 and ("$%s for %d new item%s"):format(tostring(cost), #missing, #missing == 1 and "" or "s") or "Everything here is yours"
	end
	local cash = S.server and S.server.cash or 0
	cashLabel.Text = free and "Free mode" or ("Your cash: $" .. tostring(cash))
	costLabel.TextColor3 = (not free and cost > cash) and COL.bad or COL.text
	bWear.Text = (cost > 0 and not free) and ("BUY & WEAR  $" .. cost) or "WEAR IT"
end

---------------------------------------------------------------------------------------------------- colours
local function colourPanelFor(slotId)
	for _, r in ipairs({ row1, row2 }) do
		for _, ch in ipairs(r:GetChildren()) do
			if ch:IsA("GuiObject") then
				ch:Destroy()
			end
		end
	end
	local e = slotId and S.draft[slotId]
	local item = e and Catalog.ITEMS_BY_ID[e.id]
	local slotDef = slotId and Catalog.SLOT_BY_ID[slotId]
	bRemove.Visible = item ~= nil and slotDef and not slotDef.required
	if not item then
		selLabel.Text = slotDef and (slotDef.name .. ": nothing on") or "Pick something to try on"
		return
	end
	selLabel.Text = item.name
	local function fill(r, which)
		local pal = Catalog.PALETTES[which == 1 and item.pal1 or item.pal2 or ""]
		if not pal then
			r.Visible = false
			return
		end
		r.Visible = true
		new("TextLabel", { BackgroundTransparency = 1, Size = UDim2.fromOffset(46, 30), Text = which == 1 and "Main" or "Accent", TextColor3 = COL.dim,
			Font = FONT, TextSize = 12, Parent = r })
		local cur = (which == 1 and e.c1 or e.c2) or (which == 1 and item.def1 or item.def2)
		for _, h in ipairs(pal) do
			local sw = new("TextButton", { Text = "", AutoButtonColor = false, Size = UDim2.fromOffset(28, 28), BackgroundColor3 = Builder.hex(h), Parent = r },
				{ new("UICorner", { CornerRadius = UDim.new(1, 0) }) })
			if cur and cur:upper() == h:upper() then
				stroke(COL.accent, 3).Parent = sw
			else
				stroke(Color3.fromRGB(0, 0, 0), 1).Parent = sw
			end
			sw.MouseButton1Click:Connect(function()
				if which == 1 then
					e.c1 = h
					-- keep the beard matching the hair if it was matching
					if slotId == "Hair" and S.draft.FacialHair then
						S.draft.FacialHair.c1 = h
					end
				else
					e.c2 = h
				end
				renderDraft()
				colourPanelFor(slotId)
			end)
		end
	end
	fill(row1, 1)
	fill(row2, 2)
	if not row2.Visible then
		row1.Position = UDim2.fromOffset(0, 34)
	else
		row1.Position = UDim2.fromOffset(0, 24)
	end
end

---------------------------------------------------------------------------------------------------- grid
local refreshGrid -- forward
local function clearGrid()
	for _, ch in ipairs(grid:GetChildren()) do
		if ch:IsA("GuiObject") then
			ch:Destroy()
		end
	end
	grid.CanvasPosition = Vector2.zero
end

local function matches(item)
	if S.search ~= "" then
		local q = S.search:lower()
		if not item.name:lower():find(q, 1, true) and not item.id:find(q, 1, true) then
			local hit = false
			for _, c in ipairs(item.cols) do
				if c:find(q, 1, true) then
					hit = true
				end
			end
			if not hit then
				return false
			end
		end
	end
	if S.collection and not table.find(item.cols, S.collection) then
		return false
	end
	if S.trendOnly and not item.trend then
		return false
	end
	if S.ownedOnly and not (S.owned[item.id] or item.price == 0) then
		return false
	end
	return true
end

local function itemCard(item, order)
	local worn = S.draft[item.slot] and S.draft[item.slot].id == item.id
	local card = new("TextButton", { Text = "", AutoButtonColor = true, BackgroundColor3 = worn and COL.cardHi or COL.card, LayoutOrder = order, Parent = grid },
		{ corner(10), stroke(worn and COL.accent or COL.cardHi, worn and 2 or 1) })
	local col = Builder.hex(item.def1 or "#808080")
	new("Frame", { BackgroundColor3 = col, Position = UDim2.fromOffset(8, 8), Size = UDim2.fromOffset(30, 30), Parent = card },
		{ new("UICorner", { CornerRadius = UDim.new(1, 0) }), stroke(Color3.new(0, 0, 0), 1) })
	if item.def2 and item.pal2 then
		new("Frame", { BackgroundColor3 = Builder.hex(item.def2), Position = UDim2.fromOffset(28, 26), Size = UDim2.fromOffset(14, 14), Parent = card },
			{ new("UICorner", { CornerRadius = UDim.new(1, 0) }), stroke(Color3.new(0, 0, 0), 1) })
	end
	local badge = (item.trend and "🔥" or "") .. (item.new and "✨" or "")
	label(badge, 14, COL.text, FONT, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -6, 0, 6), Size = UDim2.fromOffset(40, 18),
		TextXAlignment = Enum.TextXAlignment.Right, Parent = card })
	label(item.name, 13, COL.text, FONT_B, { Position = UDim2.fromOffset(8, 42), Size = UDim2.new(1, -16, 0, 32), TextYAlignment = Enum.TextYAlignment.Top, Parent = card })
	local priceText, pc
	if S.owned[item.id] then
		priceText, pc = "Owned", COL.good
	elseif item.price == 0 then
		priceText, pc = "Free", COL.good
	else
		priceText, pc = "$" .. item.price, COL.gold
	end
	label(priceText, 12, pc, FONT_B, { Position = UDim2.new(0, 8, 1, -20), Size = UDim2.new(1, -16, 0, 16), Parent = card })
	card.MouseButton1Click:Connect(function()
		local prev = S.draft[item.slot]
		if prev and prev.id == item.id and not Catalog.SLOT_BY_ID[item.slot].required then
			S.draft[item.slot] = nil -- tap again to take it off
		else
			-- keep the colour you picked if the new item uses the same palette (e.g. switching hairstyles)
			local prevItem = prev and Catalog.ITEMS_BY_ID[prev.id]
			local c1 = (prevItem and prevItem.pal1 == item.pal1 and item.pal1 ~= nil) and prev.c1 or item.def1
			local c2 = (prevItem and prevItem.pal2 == item.pal2 and item.pal2 ~= nil) and prev.c2 or item.def2
			if item.slot == "FacialHair" and S.draft.Hair and not prev then
				c1 = S.draft.Hair.c1 -- new beards start in your hair colour
			end
			S.draft[item.slot] = { id = item.id, c1 = c1, c2 = c2 }
		end
		S.slot = item.slot
		renderDraft()
		updateFooter()
		refreshGrid()
	end)
end

local function lookCard(lk, order)
	local card = new("TextButton", { Text = "", AutoButtonColor = true, BackgroundColor3 = COL.card, LayoutOrder = order, Parent = grid }, { corner(10), stroke(COL.cardHi) })
	local coll
	for _, c in ipairs(Catalog.COLLECTIONS) do
		if c.id == lk.col then
			coll = c
		end
	end
	-- a strip of the outfit's main colours
	local strip = new("Frame", { BackgroundTransparency = 1, Position = UDim2.fromOffset(8, 8), Size = UDim2.new(1, -16, 0, 14), Parent = card },
		{ new("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 3) }) })
	for _, slotId in ipairs({ "Hair", "Head", "Top", "Outer", "Bottom", "Shoes", "Neck" }) do
		local en = lk.look[slotId]
		local it = en and Catalog.ITEMS_BY_ID[en.id]
		if it then
			new("Frame", { BackgroundColor3 = Builder.hex(en.c1 or it.def1), Size = UDim2.fromOffset(14, 14), Parent = strip }, { new("UICorner", { CornerRadius = UDim.new(1, 0) }) })
		end
	end
	local trend = table.find(lk.tags, "trend") and "🔥" or ""
	label(trend .. lk.name, 14, COL.text, FONT_B, { Position = UDim2.fromOffset(8, 28), Size = UDim2.new(1, -16, 0, 36), TextYAlignment = Enum.TextYAlignment.Top, Parent = card })
	local cost = Catalog.Cost(lk.look, S.owned)
	label((coll and coll.name or "") .. "  ·  " .. (cost > 0 and ("$" .. cost) or "Owned"), 11, COL.dim, FONT, { Position = UDim2.new(0, 8, 1, -20), Size = UDim2.new(1, -16, 0, 16), Parent = card })
	card.MouseButton1Click:Connect(function()
		local skin = S.draft.Skin
		S.draft = copyLook(lk.look)
		if skin then
			S.draft.Skin = skin -- presets never change who you are
		end
		-- keep your own hair colour when the look doesn't specify one
		renderDraft()
		updateFooter()
		say("Trying on: " .. lk.name)
	end)
end

local function outfitCard(i, order)
	local o = S.server and S.server.outfits and S.server.outfits[i]
	local card = new("Frame", { BackgroundColor3 = COL.card, LayoutOrder = order, Parent = grid }, { corner(10), stroke(COL.cardHi) })
	label(o and o.name or ("Empty slot " .. i), 14, o and COL.text or COL.dim, FONT_B, { Position = UDim2.fromOffset(8, 8), Size = UDim2.new(1, -16, 0, 34), Parent = card })
	local bSave = button(o and "Overwrite" or "Save here", COL.cardHi, { Position = UDim2.new(0, 6, 1, -34), Size = UDim2.new(0.5, -9, 0, 28), TextSize = 12, Parent = card })
	bSave.MouseButton1Click:Connect(function()
		-- saving stores what you're WEARING (bought), not an unbought try-on
		local ok, msg, st = LookRF:InvokeServer("SaveOutfit", i, (o and o.name) or ("Outfit " .. i))
		refreshServer(st)
		say(ok and "Saved what you're wearing to slot " .. i or msg, ok and COL.good or COL.bad)
		refreshGrid()
	end)
	if o then
		local bTry = button("Try on", COL.accent, { Position = UDim2.new(0.5, 3, 1, -34), Size = UDim2.new(0.5, -9, 0, 28), TextSize = 12, TextColor3 = COL.bg, Parent = card })
		bTry.MouseButton1Click:Connect(function()
			S.draft = copyLook(o.look)
			renderDraft()
			updateFooter()
		end)
		local bDel = button("🗑", COL.card, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -4, 0, 4), Size = UDim2.fromOffset(26, 22), TextSize = 12, Parent = card })
		bDel.MouseButton1Click:Connect(function()
			local _, _, st = LookRF:InvokeServer("DeleteOutfit", i)
			refreshServer(st)
			refreshGrid()
		end)
	end
end

local function setChip(b, on)
	b.BackgroundColor3 = on and COL.accent or COL.card
	b.TextColor3 = on and COL.bg or COL.text
end

local tabButtons, slotButtons = {}, {}
local function buildSlotBar()
	for _, b in ipairs(slotButtons) do
		b:Destroy()
	end
	slotButtons = {}
	local tabDef
	for _, t in ipairs(Catalog.TABS) do
		if t.name == S.tab then
			tabDef = t
		end
	end
	slotBar.Visible = tabDef ~= nil
	if not tabDef then
		return
	end
	if not S.slot or not table.find(tabDef.slots, S.slot) then
		S.slot = tabDef.slots[1]
	end
	for i, slotId in ipairs(tabDef.slots) do
		local sd = Catalog.SLOT_BY_ID[slotId]
		local b = button(sd.icon .. " " .. sd.name, COL.card, { Size = UDim2.fromOffset(0, 32), AutomaticSize = Enum.AutomaticSize.X, TextSize = 13, LayoutOrder = i, Parent = slotBar })
		pad(10).Parent = b
		setChip(b, slotId == S.slot)
		b.MouseButton1Click:Connect(function()
			S.slot = slotId
			buildSlotBar()
			refreshGrid()
		end)
		table.insert(slotButtons, b)
	end
	-- the body frame (NCBodyService): Male / Female MakeHuman body; the build comes from your fitness
	local BodyRF = tabDef.name == "Body" and Remotes:FindFirstChild("NCBody")
	if BodyRF then
		local cur = player:GetAttribute("BodyGender") or "Male"
		for i, g in ipairs({ "Male", "Female" }) do
			local b = button((g == "Male" and "♂ " or "♀ ") .. g .. " body", COL.card, { Size = UDim2.fromOffset(0, 32), AutomaticSize = Enum.AutomaticSize.X, TextSize = 13, LayoutOrder = 100 + i, Parent = slotBar })
			pad(10).Parent = b
			setChip(b, g == cur)
			b.MouseButton1Click:Connect(function()
				if g == (player:GetAttribute("BodyGender") or "Male") then
					return
				end
				local before = player.Character
				local ok, msg = BodyRF:InvokeServer("SetGender", g)
				if not ok then
					say(msg or "Couldn't change body", COL.bad or Color3.fromRGB(255, 120, 110))
					return
				end
				local t0 = os.clock()
				while player.Character == before and os.clock() - t0 < 3 do
					task.wait(0.05)
				end
				task.wait(0.3) -- let the new body get dressed
				buildDummy()
				renderDraft()
				buildSlotBar()
			end)
			table.insert(slotButtons, b)
		end
	end
end

function refreshGrid()
	clearGrid()
	for name, b in pairs(tabButtons) do
		setChip(b, name == S.tab)
	end
	filterBar.Visible = S.tab ~= "Saved"
	if S.tab == "Looks" then
		local n = 0
		for _, lk in ipairs(Catalog.LOOKS) do
			local ok = true
			if S.collection and lk.col ~= S.collection then
				ok = false
			end
			if S.trendOnly and not table.find(lk.tags, "trend") then
				ok = false
			end
			if S.search ~= "" and not lk.name:lower():find(S.search:lower(), 1, true) then
				ok = false
			end
			if ok then
				n += 1
				lookCard(lk, n)
			end
		end
		colourPanelFor(nil)
		selLabel.Text = "Tap a look to try the whole outfit. Then fine-tune any piece in the other tabs."
	elseif S.tab == "Saved" then
		for i = 1, 8 do
			outfitCard(i, i)
		end
		colourPanelFor(nil)
		selLabel.Text = "Saved outfits store what you're wearing. Wear a look first, then save it here."
	else
		local list = Catalog.ITEMS_BY_SLOT[S.slot] or {}
		local n = 0
		-- trending first, then by price
		local sorted = table.clone(list)
		table.sort(sorted, function(a, b)
			if a.trend ~= b.trend then
				return a.trend
			end
			return a.price < b.price
		end)
		for _, item in ipairs(sorted) do
			if matches(item) then
				n += 1
				itemCard(item, n)
			end
		end
		if n == 0 then
			label("Nothing matches. Clear the search or filters.", 14, COL.dim, FONT, { Size = UDim2.fromOffset(300, 40), Parent = grid })
		end
		colourPanelFor(S.slot)
	end
end

-- tabs
local TAB_NAMES = { "Looks" }
for _, t in ipairs(Catalog.TABS) do
	table.insert(TAB_NAMES, t.name)
end
table.insert(TAB_NAMES, "Saved")
for i, name in ipairs(TAB_NAMES) do
	local icon = ({ Looks = "✨ ", Body = "🧍 ", Clothes = "👕 ", Headwear = "🧢 ", Bling = "💎 ", Extras = "🎒 ", Saved = "💾 " })[name] or ""
	local b = button(icon .. name, COL.card, { Size = UDim2.fromOffset(0, 38), AutomaticSize = Enum.AutomaticSize.X, LayoutOrder = i, Parent = tabsBar })
	pad(12).Parent = b
	tabButtons[name] = b
	b.MouseButton1Click:Connect(function()
		S.tab = name
		buildSlotBar()
		refreshGrid()
	end)
end

-- filters
searchBox:GetPropertyChangedSignal("Text"):Connect(function()
	S.search = searchBox.Text
	refreshGrid()
end)
bTrend.MouseButton1Click:Connect(function()
	S.trendOnly = not S.trendOnly
	setChip(bTrend, S.trendOnly)
	refreshGrid()
end)
bOwned.MouseButton1Click:Connect(function()
	S.ownedOnly = not S.ownedOnly
	setChip(bOwned, S.ownedOnly)
	refreshGrid()
end)
local function buildPicker()
	for _, ch in ipairs(picker:GetChildren()) do
		if ch:IsA("GuiObject") then
			ch:Destroy()
		end
	end
	local function opt(id, name, blurb, order)
		local b = button("", S.collection == id and COL.cardHi or COL.card, { Size = UDim2.new(1, 0, 0, blurb and 50 or 34), LayoutOrder = order, ZIndex = 21, Parent = picker })
		label(name, 14, COL.text, FONT_B, { Position = UDim2.fromOffset(10, 4), Size = UDim2.new(1, -20, 0, 18), ZIndex = 22, Parent = b })
		if blurb then
			label(blurb, 11, COL.dim, FONT, { Position = UDim2.fromOffset(10, 22), Size = UDim2.new(1, -20, 0, 26), ZIndex = 22, Parent = b })
		end
		b.MouseButton1Click:Connect(function()
			S.collection = id
			bCollection.Text = (name or "All worlds") .. " ▾"
			setChip(bCollection, id ~= nil)
			picker.Visible = false
			refreshGrid()
		end)
	end
	opt(nil, "All worlds", nil, 0)
	for i, c in ipairs(Catalog.COLLECTIONS) do
		opt(c.id, c.name, c.blurb, i)
	end
end
bCollection.MouseButton1Click:Connect(function()
	buildPicker()
	picker.Visible = not picker.Visible
end)

---------------------------------------------------------------------------------------------------- actions
bRemove.MouseButton1Click:Connect(function()
	if S.slot and not Catalog.SLOT_BY_ID[S.slot].required then
		S.draft[S.slot] = nil
		renderDraft()
		updateFooter()
		refreshGrid()
	end
end)
bReset.MouseButton1Click:Connect(function()
	S.draft = copyLook(S.server and S.server.look or Catalog.DEFAULT_LOOK)
	renderDraft()
	updateFooter()
	refreshGrid()
end)

local function pick(list)
	return list[math.random(1, #list)]
end
bRandom.MouseButton1Click:Connect(function()
	-- a random look that hangs together: pick a world, then mostly items from it
	local coll = pick(Catalog.COLLECTIONS).id
	local d = { Skin = S.draft.Skin }
	for _, s in ipairs(Catalog.SLOTS) do
		if s.id ~= "Skin" then
			local pool = {}
			for _, it in ipairs(Catalog.ITEMS_BY_SLOT[s.id]) do
				if table.find(it.cols, coll) then
					table.insert(pool, it)
				end
			end
			local chance = s.required and 1 or ((s.id == "Hair") and 0.95 or (#pool > 0 and 0.55 or 0.12))
			if #pool == 0 then
				pool = Catalog.ITEMS_BY_SLOT[s.id]
			end
			if #pool > 0 and math.random() < chance and s.id ~= "Neck2" then
				local it = pick(pool)
				local p1, p2 = Catalog.PALETTES[it.pal1 or ""], Catalog.PALETTES[it.pal2 or ""]
				d[s.id] = { id = it.id, c1 = (p1 and math.random() < 0.5) and pick(p1) or it.def1, c2 = (p2 and math.random() < 0.4) and pick(p2) or it.def2 }
			end
		end
	end
	if d.Hair and d.FacialHair then
		d.FacialHair.c1 = d.Hair.c1
	end
	S.draft = d
	renderDraft()
	updateFooter()
	refreshGrid()
	for _, c in ipairs(Catalog.COLLECTIONS) do
		if c.id == coll then
			say("🎲 " .. c.name)
		end
	end
end)

local busy = false
bWear.MouseButton1Click:Connect(function()
	if busy then
		return
	end
	busy = true
	bWear.Text = "..."
	local ok, msg, st = LookRF:InvokeServer("Wear", S.draft)
	busy = false
	refreshServer(st)
	if ok then
		say("✅ " .. (msg or "Looking good"), COL.good)
		S.draft = copyLook(S.server.look)
	else
		say(msg or "Couldn't do that", COL.bad)
	end
	updateFooter()
	refreshGrid()
end)

local function close()
	S.open = false
	gui.Enabled = false
	picker.Visible = false
	if dummy then
		dummy:Destroy()
		dummy = nil
	end
end
bClose.MouseButton1Click:Connect(close)

local function open()
	if S.open then
		return
	end
	local ok, msg, st = LookRF:InvokeServer("Get")
	if not ok then
		say(msg or "Closet not ready", COL.bad)
		return
	end
	refreshServer(st)
	S.draft = copyLook(S.server.look)
	S.open = true
	layout()
	gui.Enabled = true
	buildDummy()
	buildSlotBar()
	renderDraft()
	updateFooter()
	refreshGrid()
end

OpenSig.Event:Connect(open)
UIS.InputBegan:Connect(function(input, gp)
	if gp then
		return
	end
	local key = script:GetAttribute("HotKey")
	if type(key) == "string" and key ~= "" and input.KeyCode.Name == key then
		if S.open then
			close()
		else
			open()
		end
	elseif S.open and input.KeyCode == Enum.KeyCode.Escape then
		close()
	end
end)
workspace.CurrentCamera:GetPropertyChangedSignal("ViewportSize"):Connect(function()
	if S.open then
		layout()
		refreshGrid()
	end
end)
player.CharacterAdded:Connect(function()
	if S.open then
		task.wait(0.5)
		buildDummy()
		renderDraft()
	end
end)

-- first ever join: open the studio so new players make their character
task.spawn(function()
	if not script:GetAttribute("OpenOnFirstJoin") then
		return
	end
	local char = player.Character or player.CharacterAdded:Wait()
	char:WaitForChild("Head", 10)
	task.wait(3)
	local ok, _, st = LookRF:InvokeServer("Get")
	if ok and st and not st.made then
		open()
		say("Welcome! Make your character. Try a look, then tap WEAR IT.")
	end
end)
