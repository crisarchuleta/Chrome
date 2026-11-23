--!nonstrict
-- HouseClient: the client half of HouseInteractables. Spins every ceiling fan, opens the closet / gear / car screens,
-- and runs the TV: the picture is drawn on the TV's own screen (SurfaceGui), so when you play, your camera moves in
-- front of the TV and you play on it, and everyone else in the room sees your game live on the same screen.
-- Games: 1 SNAKE, 2 PONG (vs the TV). WASD / arrows to play, Q or Backspace to stand up.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UIS = game:GetService("UserInputService")
local RS = game:GetService("ReplicatedStorage")

local player = Players.LocalPlayer
local Remotes = RS:WaitForChild("Remotes")
local HouseUI = Remotes:WaitForChild("HouseUI")
local TVState = Remotes:WaitForChild("TVState")
local TVQuit = Remotes:WaitForChild("TVQuit")
local Signals = RS:WaitForChild("LocalSignals")

---------------------------------------------------------------------------- fans
local fanBase = setmetatable({}, { __mode = "k" })
local fanAngle = setmetatable({}, { __mode = "k" })
RunService.RenderStepped:Connect(function(dt)
	for _, fan in CollectionService:GetTagged("NC_Fan") do
		local blades = fan:FindFirstChild("Blades", true)
		if blades and blades:IsA("BasePart") then
			fanBase[blades] = fanBase[blades] or blades.CFrame
			local s = fan:GetAttribute("Speed") or 0
			local target = s == 2 and 11 or (s == 1 and 4.5 or 0)
			local cur = blades:GetAttribute("Spin") or 0
			cur += (target - cur) * math.min(1, dt * 1.5)          -- fans spin up and coast down
			blades:SetAttribute("Spin", cur)
			fanAngle[blades] = ((fanAngle[blades] or 0) + cur * dt) % (math.pi * 2)
			blades.CFrame = fanBase[blades] * CFrame.Angles(0, fanAngle[blades], 0)
		end
	end
end)

---------------------------------------------------------------------------- TV screens (everyone)
local W, H = 24, 14
local screens = setmetatable({}, { __mode = "k" })

local function screenOf(tv)
	local s = screens[tv]
	if s and s.gui.Parent then
		return s
	end
	local part = tv:FindFirstChild("Screen", true)
	if not (part and part:IsA("BasePart")) then
		return nil
	end
	local gui = Instance.new("SurfaceGui")
	gui.Name = "TVPicture"
	gui.Face = Enum.NormalId[tv:GetAttribute("ScreenFace") or "Front"]
	gui.CanvasSize = Vector2.new(480, 280)
	gui.LightInfluence = 0
	gui.Brightness = 1.6
	gui.Parent = part
	local bg = Instance.new("Frame")
	bg.Size = UDim2.fromScale(1, 1)
	bg.BackgroundColor3 = Color3.new(0, 0, 0)
	bg.BorderSizePixel = 0
	bg.Parent = gui
	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Font = Enum.Font.GothamBlack
	label.TextScaled = true
	label.TextColor3 = Color3.fromRGB(255, 90, 200)
	label.Parent = bg
	local score = Instance.new("TextLabel")
	score.Size = UDim2.new(1, 0, 0, 26)
	score.BackgroundTransparency = 1
	score.Font = Enum.Font.GothamBold
	score.TextSize = 22
	score.TextColor3 = Color3.new(1, 1, 1)
	score.ZIndex = 3
	score.Parent = bg
	s = { gui = gui, bg = bg, label = label, score = score, pool = {} }
	screens[tv] = s
	return s
end

local function pixel(s, i)
	local f = s.pool[i]
	if not f then
		f = Instance.new("Frame")
		f.BorderSizePixel = 0
		f.ZIndex = 2
		f.Parent = s.bg
		s.pool[i] = f
	end
	f.Visible = true
	return f
end

local function clearPixels(s, from)
	for i = from, #s.pool do
		s.pool[i].Visible = false
	end
end

local function drawSnake(s, state)
	-- "score|food|c1,c2,..."
	local sc, food, cells = state:match("^(%d+)|(%d+)|(.*)$")
	if not sc then
		return
	end
	s.label.Text = ""
	s.score.Text = "SNAKE   " .. sc
	local n = 0
	local function cell(idx, color)
		n += 1
		local f = pixel(s, n)
		local x, y = idx % W, idx // W
		f.Position = UDim2.fromScale(x / W, (y + 1) / (H + 1))
		f.Size = UDim2.fromScale(1 / W - 0.004, 1 / (H + 1) - 0.006)
		f.BackgroundColor3 = color
	end
	cell(tonumber(food), Color3.fromRGB(255, 90, 90))
	local first = true
	for c in cells:gmatch("%d+") do
		cell(tonumber(c), first and Color3.fromRGB(150, 255, 190) or Color3.fromRGB(60, 220, 130))
		first = false
	end
	clearPixels(s, n + 1)
end

local function drawPong(s, state)
	-- "ly|ry|bx|by|ls|rs" in 0..1000
	local v = {}
	for x in state:gmatch("%-?%d+") do
		table.insert(v, tonumber(x) / 1000)
	end
	if #v < 6 then
		return
	end
	s.label.Text = ""
	s.score.Text = string.format("PONG   %d  :  %d", v[5] * 1000, v[6] * 1000)
	local function rect(i, x, y, w, h, c)
		local f = pixel(s, i)
		f.AnchorPoint = Vector2.new(0.5, 0.5)
		f.Position = UDim2.fromScale(x, y)
		f.Size = UDim2.fromScale(w, h)
		f.BackgroundColor3 = c
	end
	rect(1, 0.04, v[1], 0.02, 0.22, Color3.fromRGB(80, 200, 255))
	rect(2, 0.96, v[2], 0.02, 0.22, Color3.fromRGB(255, 90, 200))
	rect(3, v[3], v[4], 0.025, 0.04, Color3.new(1, 1, 1))
	clearPixels(s, 4)
end

local function idle(tv)
	local s = screenOf(tv)
	if not s then
		return
	end
	clearPixels(s, 1)
	s.score.Text = ""
	if tv:GetAttribute("Power") then
		s.bg.BackgroundColor3 = Color3.fromRGB(20, 10, 40)
		s.label.Text = "NEON COAST TV"
	else
		s.bg.BackgroundColor3 = Color3.new(0, 0, 0)
		s.label.Text = ""
	end
end

local function hookTV(tv)
	idle(tv)
	tv:GetAttributeChangedSignal("Power"):Connect(function()
		idle(tv)
	end)
	tv:GetAttributeChangedSignal("PlayerId"):Connect(function()
		if not tv:GetAttribute("PlayerId") then
			idle(tv)
		end
	end)
end
for _, tv in CollectionService:GetTagged("NC_TV") do
	task.spawn(hookTV, tv)
end
CollectionService:GetInstanceAddedSignal("NC_TV"):Connect(hookTV)

TVState.OnClientEvent:Connect(function(tv, gameName, state)
	local s = tv and screenOf(tv)
	if not s then
		return
	end
	s.bg.BackgroundColor3 = Color3.fromRGB(8, 8, 14)
	if gameName == "Snake" then
		drawSnake(s, state)
	elseif gameName == "Pong" then
		drawPong(s, state)
	end
end)

---------------------------------------------------------------------------- playing (you)
local playing = nil -- { tv, game, ... }
local held = {}
UIS.InputBegan:Connect(function(input, gp)
	held[input.KeyCode] = true
	if not playing then
		return
	end
	local k = input.KeyCode
	if k == Enum.KeyCode.Q or k == Enum.KeyCode.Backspace then
		playing.quit = true
	elseif playing.menu and (k == Enum.KeyCode.One or k == Enum.KeyCode.KeypadOne) then
		playing.choose = "Snake"
	elseif playing.menu and (k == Enum.KeyCode.Two or k == Enum.KeyCode.KeypadTwo) then
		playing.choose = "Pong"
	elseif playing.game == "Snake" then
		local d = (k == Enum.KeyCode.W or k == Enum.KeyCode.Up) and Vector2.new(0, -1)
			or (k == Enum.KeyCode.S or k == Enum.KeyCode.Down) and Vector2.new(0, 1)
			or (k == Enum.KeyCode.A or k == Enum.KeyCode.Left) and Vector2.new(-1, 0)
			or (k == Enum.KeyCode.D or k == Enum.KeyCode.Right) and Vector2.new(1, 0)
		if d and d ~= -playing.dir then
			playing.nextDir = d
		end
	end
end)
UIS.InputEnded:Connect(function(input)
	held[input.KeyCode] = nil
end)

local function send(tv, name, state)
	TVState:FireServer(tv, name, state)
	local s = screenOf(tv)
	if s then
		s.bg.BackgroundColor3 = Color3.fromRGB(8, 8, 14)
		if name == "Snake" then
			drawSnake(s, state)
		else
			drawPong(s, state)
		end
	end
end

local function runSnake(p)
	p.game, p.dir, p.nextDir = "Snake", Vector2.new(1, 0), Vector2.new(1, 0)
	local body = { Vector2.new(6, 7), Vector2.new(5, 7), Vector2.new(4, 7) }
	local function freeCell()
		while true do
			local c = Vector2.new(math.random(0, W - 1), math.random(0, H - 1))
			local hit = false
			for _, b in body do
				if b == c then
					hit = true
				end
			end
			if not hit then
				return c
			end
		end
	end
	local food, score, step = freeCell(), 0, 0.14
	while not p.quit do
		task.wait(step)
		p.dir = p.nextDir
		local head = body[1] + p.dir
		local dead = head.X < 0 or head.Y < 0 or head.X >= W or head.Y >= H
		for i = 1, #body - 1 do
			if body[i] == head then
				dead = true
			end
		end
		if dead then
			body = { Vector2.new(6, 7), Vector2.new(5, 7), Vector2.new(4, 7) }
			p.dir, p.nextDir, score, step = Vector2.new(1, 0), Vector2.new(1, 0), 0, 0.14
		else
			table.insert(body, 1, head)
			if head == food then
				score += 1
				step = math.max(0.06, step - 0.004)
				food = freeCell()
			else
				table.remove(body)
			end
		end
		local cells = {}
		for _, b in body do
			table.insert(cells, tostring(b.Y * W + b.X))
		end
		send(p.tv, "Snake", string.format("%d|%d|%s", score, food.Y * W + food.X, table.concat(cells, ",")))
	end
end

local function runPong(p)
	p.game = "Pong"
	local ly, ry, bx, by = 0.5, 0.5, 0.5, 0.5
	local vx, vy = 0.55, 0.3
	local ls, rs = 0, 0
	local last = os.clock()
	local acc = 0
	while not p.quit do
		local dt = RunService.Heartbeat:Wait()
		local up = held[Enum.KeyCode.W] or held[Enum.KeyCode.Up]
		local down = held[Enum.KeyCode.S] or held[Enum.KeyCode.Down]
		ly = math.clamp(ly + ((down and 1 or 0) - (up and 1 or 0)) * dt * 0.9, 0.11, 0.89)
		ry = math.clamp(ry + math.clamp(by - ry, -1, 1) * dt * 2.2, 0.11, 0.89)   -- the TV is beatable
		bx += vx * dt
		by += vy * dt
		if by < 0.02 or by > 0.98 then
			vy = -vy
			by = math.clamp(by, 0.02, 0.98)
		end
		if bx < 0.06 and math.abs(by - ly) < 0.12 and vx < 0 then
			vx = -vx * 1.06
			vy += (by - ly) * 2
		elseif bx > 0.94 and math.abs(by - ry) < 0.12 and vx > 0 then
			vx = -vx * 1.04
			vy += (by - ry) * 2
		end
		if bx < 0 or bx > 1 then
			if bx < 0 then
				rs += 1
			else
				ls += 1
			end
			bx, by, vx, vy = 0.5, 0.5, (bx < 0 and 0.55 or -0.55), (math.random() - 0.5) * 0.6
		end
		acc += dt
		if acc > 1 / 15 then                          -- 15 pictures a second to everyone else
			acc = 0
			local r = function(x)
				return math.floor(x * 1000 + 0.5)
			end
			send(p.tv, "Pong", string.format("%d|%d|%d|%d|%d|%d", r(ly), r(ry), r(bx), r(by), ls * 1000, rs * 1000))
		end
	end
end

local function play(tv)
	if playing then
		return
	end
	local screen = tv:FindFirstChild("Screen", true)
	local s = screenOf(tv)
	if not (screen and s) then
		return
	end
	local char = player.Character
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	local cam = workspace.CurrentCamera
	local oldType, oldSubject = cam.CameraType, cam.CameraSubject
	local p = { tv = tv, menu = true }
	playing = p
	local saved
	if hum then
		if hum:GetAttribute("NC_Movement") then
			hum:SetAttribute("SpeedFactor_TV", 0) -- frozen through the movement system (0 also stops jumps)
		else
			saved = { hum.WalkSpeed, hum.JumpPower, hum.JumpHeight }
			hum.WalkSpeed, hum.JumpPower, hum.JumpHeight = 0, 0, 0
		end
	end
	local face = Vector3.FromNormalId(Enum.NormalId[tv:GetAttribute("ScreenFace") or "Front"])
	local normal = screen.CFrame:VectorToWorldSpace(face)
	local dist = math.max(screen.Size.X, screen.Size.Y) * 1.15
	cam.CameraType = Enum.CameraType.Scriptable
	cam.CFrame = CFrame.lookAt(screen.Position + normal * dist + Vector3.new(0, 0.6, 0), screen.Position)
	s.bg.BackgroundColor3 = Color3.fromRGB(20, 10, 40)
	clearPixels(s, 1)
	s.label.Text = "1  SNAKE      2  PONG"
	s.score.Text = "Q to stand up"
	while not (p.choose or p.quit) do
		task.wait()
	end
	p.menu = false
	if p.choose == "Snake" then
		runSnake(p)
	elseif p.choose == "Pong" then
		runPong(p)
	end
	TVQuit:FireServer(tv)
	cam.CameraType = oldType ~= Enum.CameraType.Scriptable and oldType or Enum.CameraType.Custom
	cam.CameraSubject = oldSubject or hum
	if hum then
		if hum:GetAttribute("NC_Movement") then
			hum:SetAttribute("SpeedFactor_TV", nil)
		elseif saved then
			hum.WalkSpeed, hum.JumpPower, hum.JumpHeight = saved[1], saved[2], saved[3] -- whatever they were before
		end
	end
	idle(tv)
	playing = nil
end

---------------------------------------------------------------------------- the server's "open this" messages
HouseUI.OnClientEvent:Connect(function(kind, model)
	if kind == "Closet" then
		local sig = Signals:FindFirstChild("OpenCharacterStudio")
		if sig then
			sig:Fire()
		end
	elseif kind == "Gear" then
		local sig = Signals:FindFirstChild("OpenArmory")
		if sig then
			sig:Fire()
		end
	elseif kind == "Cars" then
		local sig = Signals:FindFirstChild("OpenGarageList")
		if sig then
			sig:Fire()
		end
	elseif kind == "TV" and model then
		task.spawn(play, model)
	end
end)
