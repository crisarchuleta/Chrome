--!nonstrict
-- HouseInteractables: the little things players poke at in houses. Tag-driven (CollectionService), so any model in
-- the place can use it: Blender furniture is tagged by BuildingKit.PrepareProps, Studio furniture by hand/InteriorKit.
-- State lives in attributes on each model (they replicate), so every player sees the same lights, fans, water, TV.
--   NC_Light     parts named "Bulb" (glow when on) + any Light objects inside. Attribute Group: one switch flips
--                every light with the same Group inside the same building.
--   NC_Fan       a part named "Blades" (every client spins it) and optional "Bulb"s. Off / Low / High.
--   NC_Sink      an Attachment named "Spout": a water stream and running-water sound while on.
--   NC_Window    a part (or model) named "Sash" that slides up to open.
--   NC_TV        a part named "Screen". Power on/off; "Play" starts the TV game on the player's client (TVClient),
--                which streams its picture back here so everyone watching the TV sees the same game.
--   NC_Closet    "Change outfit" opens the Character Studio, "Gear" opens the Arms shop.
--   NC_CarPanel  "Pick a car" opens the garage list (HomeService does the rest).
--   NC_NightLight lights that switch on at dusk and off at dawn by themselves (porch, coach, street lights).
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local Lighting = game:GetService("Lighting")
local TweenService = game:GetService("TweenService")
local RS = game:GetService("ReplicatedStorage")

local Remotes = RS:WaitForChild("Remotes")
local function remote(name, class)
	local r = Remotes:FindFirstChild(name)
	if not r then
		r = Instance.new(class or "RemoteEvent")
		r.Name = name
		r.Parent = Remotes
	end
	return r
end
local HouseUI = remote("HouseUI")
local TVState = remote("TVState", "UnreliableRemoteEvent")
local TVQuit = remote("TVQuit")

local WARM = Color3.fromRGB(255, 236, 200)

local function promptPart(model)
	local p = model:FindFirstChild("Prompt", true)
	if p and p:IsA("BasePart") then
		return p
	end
	if model:IsA("BasePart") then
		return model
	end
	return model.PrimaryPart or model:FindFirstChildWhichIsA("BasePart", true)
end

local function addPrompt(model, action, object, key, hold)
	local part = promptPart(model)
	if not part then
		return nil
	end
	local pp = Instance.new("ProximityPrompt")
	pp.ActionText = action
	pp.ObjectText = object or ""
	pp.HoldDuration = hold or 0
	pp.MaxActivationDistance = 9
	pp.RequiresLineOfSight = false
	if key then
		pp.KeyboardKeyCode = key
		pp.UIOffset = Vector2.new(0, -72)
	end
	pp.Parent = part
	return pp
end

local function buildingOf(model)
	local cur = model.Parent
	while cur and cur ~= workspace do
		if cur:IsA("Model") and (cur:GetAttribute("Style") or cur:GetAttribute("Interior") or cur:GetAttribute("OwnerId")) then
			return cur
		end
		cur = cur.Parent
	end
	return model.Parent
end

---------------------------------------------------------------------------- lights
local function applyLight(model, on)
	for _, d in model:GetDescendants() do
		if d:IsA("Light") then
			d.Enabled = on
		elseif d:IsA("BasePart") and d.Name == "Bulb" then
			if d:GetAttribute("OffColor") == nil then
				d:SetAttribute("OffColor", d.Color)
				d:SetAttribute("OffMaterial", d.Material.Name)
			end
			d.Material = on and Enum.Material.Neon or Enum.Material[d:GetAttribute("OffMaterial")]
			d.Color = on and WARM or d:GetAttribute("OffColor")
		end
	end
end

local function ensureLight(model)
	if model:FindFirstChildWhichIsA("Light", true) then
		return
	end
	local bulb = model:FindFirstChild("Bulb", true) or promptPart(model)
	if bulb then
		local l = Instance.new("PointLight")
		l.Color = WARM
		l.Range = model:GetAttribute("Range") or 18
		l.Brightness = model:GetAttribute("Brightness") or 1.4
		l.Shadows = true
		l.Parent = bulb
	end
end

local function hookLight(model)
	ensureLight(model)
	local on = model:GetAttribute("On") == true
	applyLight(model, on)
	model:GetAttributeChangedSignal("On"):Connect(function()
		applyLight(model, model:GetAttribute("On") == true)
	end)
	if model:GetAttribute("NoSwitch") then
		return
	end
	local pp = addPrompt(model, on and "Lights off" or "Lights on", "Light", Enum.KeyCode.E)
	if not pp then
		return
	end
	pp.Triggered:Connect(function()
		local now = not (model:GetAttribute("On") == true)
		local group = model:GetAttribute("Group")
		if group then
			for _, other in CollectionService:GetTagged("NC_Light") do
				if other:GetAttribute("Group") == group and buildingOf(other) == buildingOf(model) then
					other:SetAttribute("On", now)
				end
			end
		else
			model:SetAttribute("On", now)
		end
	end)
	model:GetAttributeChangedSignal("On"):Connect(function()
		pp.ActionText = model:GetAttribute("On") and "Lights off" or "Lights on"
	end)
end

---------------------------------------------------------------------------- ceiling fans (clients spin the blades)
local FAN_TEXT = { [0] = "Fan: low", [1] = "Fan: high", [2] = "Fan: off" }
local function hookFan(model)
	model:SetAttribute("Speed", model:GetAttribute("Speed") or 0)
	local pp = addPrompt(model, FAN_TEXT[model:GetAttribute("Speed")], "Ceiling Fan", Enum.KeyCode.F)
	if not pp then
		return
	end
	pp.Triggered:Connect(function()
		local s = ((model:GetAttribute("Speed") or 0) + 1) % 3
		model:SetAttribute("Speed", s)
		pp.ActionText = FAN_TEXT[s]
	end)
end

---------------------------------------------------------------------------- sinks
local function hookSink(model)
	local spout = model:FindFirstChild("Spout", true)
	if not (spout and spout:IsA("Attachment")) then
		return
	end
	local pe = Instance.new("ParticleEmitter")
	pe.Name = "Water"
	pe.Texture = "rbxasset://textures/particles/sparkles_main.dds"
	pe.Color = ColorSequence.new(Color3.fromRGB(190, 225, 255))
	pe.LightEmission = 0.3
	pe.Transparency = NumberSequence.new(0.35, 0.8)
	pe.Size = NumberSequence.new(0.18, 0.08)
	pe.Lifetime = NumberRange.new(0.25, 0.35)
	pe.Rate = 160
	pe.Speed = NumberRange.new(2.5, 3)
	pe.SpreadAngle = Vector2.new(4, 4)
	pe.EmissionDirection = Enum.NormalId.Bottom
	pe.Acceleration = Vector3.new(0, -30, 0)
	pe.Enabled = false
	pe.Parent = spout
	local snd = Instance.new("Sound")
	snd.Name = "Running"
	snd.SoundId = "rbxasset://sounds/action_swim.mp3"
	snd.Looped = true
	snd.Volume = 0.35
	snd.PlaybackSpeed = 1.6
	snd.RollOffMaxDistance = 40
	snd.Parent = spout
	local pp = addPrompt(model, "Turn on water", "Sink", Enum.KeyCode.E)
	if not pp then
		return
	end
	local function apply()
		local on = model:GetAttribute("On") == true
		pe.Enabled = on
		if on then
			snd:Play()
		else
			snd:Stop()
		end
		pp.ActionText = on and "Turn off water" or "Turn on water"
	end
	model:GetAttributeChangedSignal("On"):Connect(apply)
	apply()
	local token = 0
	pp.Triggered:Connect(function()
		model:SetAttribute("On", not model:GetAttribute("On"))
		token += 1
		local my = token
		task.delay(60, function() -- nobody leaves a tap running forever
			if token == my then
				model:SetAttribute("On", false)
			end
		end)
	end)
end

---------------------------------------------------------------------------- windows
local function hookWindow(model)
	local sash = model:FindFirstChild("Sash", true)
	if not sash then
		return
	end
	local isModel = sash:IsA("Model")
	local closed = isModel and sash:GetPivot() or sash.CFrame
	local size = isModel and select(2, sash:GetBoundingBox()) or sash.Size
	local lift = model:GetAttribute("Slide") or math.max(size.Y * 0.45, 1)
	local pp = addPrompt(model, "Open window", "Window", Enum.KeyCode.E)
	if not pp then
		return
	end
	local busy = false
	pp.Triggered:Connect(function()
		if busy then
			return
		end
		busy = true
		local open = not model:GetAttribute("Open")
		model:SetAttribute("Open", open)
		local target = closed * CFrame.new(0, open and lift or 0, 0)
		if isModel then
			local v = Instance.new("CFrameValue")
			v.Value = sash:GetPivot()
			v.Changed:Connect(function(cf)
				sash:PivotTo(cf)
			end)
			local tw = TweenService:Create(v, TweenInfo.new(0.6, Enum.EasingStyle.Quad), { Value = target })
			tw:Play()
			tw.Completed:Wait()
			v:Destroy()
		else
			local tw = TweenService:Create(sash, TweenInfo.new(0.6, Enum.EasingStyle.Quad), { CFrame = target })
			tw:Play()
			tw.Completed:Wait()
		end
		pp.ActionText = open and "Close window" or "Open window"
		busy = false
	end)
end

---------------------------------------------------------------------------- TVs
local function hookTV(model)
	model:SetAttribute("Power", model:GetAttribute("Power") == true)
	local power = addPrompt(model, model:GetAttribute("Power") and "Turn off" or "Turn on", "TV", Enum.KeyCode.F)
	local play = addPrompt(model, "Play a game", "TV", Enum.KeyCode.E)
	if not (power and play) then
		return
	end
	power.Triggered:Connect(function()
		local on = not model:GetAttribute("Power")
		model:SetAttribute("Power", on)
		power.ActionText = on and "Turn off" or "Turn on"
		if not on then
			model:SetAttribute("PlayerId", nil)
		end
	end)
	play.Triggered:Connect(function(player)
		local current = model:GetAttribute("PlayerId")
		if current and current ~= player.UserId and Players:GetPlayerByUserId(current) then
			return -- somebody else is playing; they can watch
		end
		model:SetAttribute("Power", true)
		power.ActionText = "Turn off"
		model:SetAttribute("PlayerId", player.UserId)
		HouseUI:FireClient(player, "TV", model)
	end)
end

TVState.OnServerEvent:Connect(function(player, tv, game, state)
	if typeof(tv) ~= "Instance" or not CollectionService:HasTag(tv, "NC_TV") then
		return
	end
	if tv:GetAttribute("PlayerId") ~= player.UserId or typeof(state) ~= "string" or #state > 600 then
		return
	end
	tv:SetAttribute("Game", typeof(game) == "string" and game:sub(1, 16) or nil)
	for _, p in Players:GetPlayers() do
		if p ~= player then
			TVState:FireClient(p, tv, game, state)
		end
	end
end)
TVQuit.OnServerEvent:Connect(function(player, tv)
	if typeof(tv) == "Instance" and tv:GetAttribute("PlayerId") == player.UserId then
		tv:SetAttribute("PlayerId", nil)
		tv:SetAttribute("Game", nil)
	end
end)
Players.PlayerRemoving:Connect(function(player)
	for _, tv in CollectionService:GetTagged("NC_TV") do
		if tv:GetAttribute("PlayerId") == player.UserId then
			tv:SetAttribute("PlayerId", nil)
		end
	end
end)

---------------------------------------------------------------------------- closet, car panel
local function hookCloset(model)
	local outfit = addPrompt(model, "Change outfit", "Closet", Enum.KeyCode.E)
	local gear = addPrompt(model, "Gear", "Closet", Enum.KeyCode.F)
	if outfit then
		outfit.Triggered:Connect(function(player)
			model:SetAttribute("Open", true)
			HouseUI:FireClient(player, "Closet", model)
			task.delay(4, function()
				model:SetAttribute("Open", false)
			end)
		end)
	end
	if gear then
		gear.Triggered:Connect(function(player)
			HouseUI:FireClient(player, "Gear", model)
		end)
	end
	-- the closet doors swing open while someone is changing (any parts named DoorL / DoorR)
	local doors = {}
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") and (d.Name == "DoorL" or d.Name == "DoorR") then
			doors[d] = d.CFrame
		end
	end
	model:GetAttributeChangedSignal("Open"):Connect(function()
		local open = model:GetAttribute("Open")
		for d, base in doors do
			local s = d.Name == "DoorL" and -1 or 1
			local hinge = base * CFrame.new(s * d.Size.X / 2, 0, 0)
			-- swings out of the front (+Z for Blender props after import): left door -100 degrees, right door +100
			local target = open and (hinge * CFrame.Angles(0, math.rad(100 * s), 0) * CFrame.new(-s * d.Size.X / 2, 0, 0)) or base
			TweenService:Create(d, TweenInfo.new(0.5, Enum.EasingStyle.Quad), { CFrame = target }):Play()
		end
	end)
end

local function hookCarPanel(model)
	local pp = addPrompt(model, "Pick a car", "Garage", Enum.KeyCode.E)
	if pp then
		pp.Triggered:Connect(function(player)
			HouseUI:FireClient(player, "Cars", model)
		end)
	end
end

---------------------------------------------------------------------------- dusk-to-dawn lights
local function isNight()
	local t = Lighting.ClockTime
	return t < 6.4 or t > 18.1
end
local nightOn = nil
local function applyNight(model)
	for _, d in model:GetDescendants() do
		if d:IsA("Light") then
			d.Enabled = isNight()
		elseif d:IsA("ObjectValue") and d.Value and d.Value:IsA("Light") then
			d.Value.Enabled = isNight() -- BuildingKit keeps the lantern lights on the building root and points here
		end
	end
end
task.spawn(function()
	while true do
		local n = isNight()
		if n ~= nightOn then
			nightOn = n
			for _, m in CollectionService:GetTagged("NC_NightLight") do
				applyNight(m)
			end
		end
		task.wait(5)
	end
end)

---------------------------------------------------------------------------- wiring
local HOOKS = {
	NC_Light = hookLight, NC_Fan = hookFan, NC_Sink = hookSink, NC_Window = hookWindow, NC_TV = hookTV,
	NC_Closet = hookCloset, NC_CarPanel = hookCarPanel, NC_NightLight = applyNight,
}
for tag, fn in HOOKS do
	for _, m in CollectionService:GetTagged(tag) do
		task.spawn(fn, m)
	end
	CollectionService:GetInstanceAddedSignal(tag):Connect(fn)
end
