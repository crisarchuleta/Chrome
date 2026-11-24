-- Neon Coast: parked cars + personal car on V. Doors rest closed and swing open/shut on hinges.
-- Cars come from the customization system (NCVehicleWorld: every NCVehicles vehicle whose meshes are imported);
-- any name it can't build falls back to the old ServerStorage.CarTemplates.
local Players = game:GetService("Players")
local SS = game:GetService("ServerStorage")
local RS = game:GetService("ReplicatedStorage")
local Remotes = RS:WaitForChild("Remotes")
local NC = require(script.Parent:WaitForChild("NC"))
local World = require(script.Parent:WaitForChild("NCVehicleWorld"))

local root = workspace:WaitForChild("NeonCoast")
local template = SS:WaitForChild("CarTemplate")
local templatesFolder = SS:FindFirstChild("CarTemplates")
local function pickTemplate(name)
	if templatesFolder and #templatesFolder:GetChildren() > 0 then
		if name and templatesFolder:FindFirstChild(name) then return templatesFolder[name] end
		-- random civilian vehicles only (never the police cruiser or armored truck)
		local list = {}
		for _, t in ipairs(templatesFolder:GetChildren()) do if not t:GetAttribute("Police") then table.insert(list, t) end end
		return list[math.random(#list)]
	end
	return template
end
local carsFolder = root:WaitForChild("Cars")

local PAINTS = {
	Color3.fromRGB(255,60,200), Color3.fromRGB(60,230,255), Color3.fromRGB(180,90,255),
	Color3.fromRGB(255,140,60), Color3.fromRGB(80,255,170), Color3.fromRGB(255,230,80),
	Color3.fromRGB(240,240,250), Color3.fromRGB(30,30,40), Color3.fromRGB(255,80,80),
}
local GLOWS = {Color3.fromRGB(60,230,255), Color3.fromRGB(255,60,200), Color3.fromRGB(80,255,170), Color3.fromRGB(180,90,255)}

local Spawner = {}
local TweenService = game:GetService("TweenService")
local DOOR_TWEEN = TweenInfo.new(0.35, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)

-- The cars use their original Halfmile hinges: Motor6D "Hinge" joints tagged Panel = DoorFL/DoorFR/DoorRL/DoorRR/Hood/Trunk/Tailgate.
-- Each joint already pivots on the real hinge line; opening = rotate its C0 about X by OpenDegrees (C0 replicates to everyone).
-- id: FL FR RL RR Hood Trunk Tailgate
local PANEL_IDS = {"FL", "FR", "RL", "RR", "Hood", "Trunk", "Tailgate"}
local function panelName(id)
	if id == "Hood" or id == "Trunk" or id == "Tailgate" then return id end
	return "Door" .. tostring(id)
end
function Spawner.SetDoor(car, id, open)
	if World.IsKit(car) then
		return World.SetDoor(car, id, open)
	end
	local panel = panelName(id)
	local found = false
	for _, m in ipairs(car:GetDescendants()) do
		if m:IsA("Motor6D") and m.Name == "Hinge" and m:GetAttribute("Panel") == panel then
			local base = m:GetAttribute("BaseC0")
			if not base then base = m.C0; m:SetAttribute("BaseC0", base) end
			local ang = math.rad(m:GetAttribute("OpenDegrees") or 60)
			TweenService:Create(m, DOOR_TWEEN, {C0 = base * CFrame.Angles(open and ang or 0, 0, 0)}):Play()
			found = true
		end
	end
	if found then car:SetAttribute("Open_" .. panel, open) end
	return found
end

function Spawner.PulseDoor(car, id)
	Spawner.SetDoor(car, id, true)
	task.delay(0.9, function() if car.Parent then Spawner.SetDoor(car, id, false) end end)
end

function Spawner.ToggleAll(car)
	if World.IsKit(car) then
		return World.ToggleAll(car)
	end
	local anyOpen = false
	for _, id in ipairs(PANEL_IDS) do if car:GetAttribute("Open_" .. panelName(id)) then anyOpen = true end end
	for _, id in ipairs(PANEL_IDS) do Spawner.SetDoor(car, id, not anyOpen) end
end

-- opts.parked: a Kit car rests anchored until someone gets in (parked spots)
function Spawner.MakeCar(cf, paint, glow, templateName, opts)
	-- the new vehicles: by name, or a random civilian one
	local name = templateName
	if not name then
		local pool = World.CivilianPool()
		if #pool > 0 then
			name = pool[math.random(#pool)]
		end
	end
	if name and World.Has(name) then
		local kit = World.Build(name, cf, { paint = paint, parked = opts and opts.parked })
		kit.Parent = carsFolder
		return kit
	end
	-- old templates: cf is a ground-level position; lift it by this car's ride height so it lands on its wheels
	local car = pickTemplate(templateName):Clone()
	cf = cf + Vector3.new(0, (car:GetAttribute("RideHeight") or 2.7) + 0.3, 0)
	paint = paint or PAINTS[math.random(#PAINTS)]
	for _, p in ipairs(car:GetDescendants()) do
		if p:IsA("BasePart") then
			if p:GetAttribute("Paint") then p.Color = paint end
			if p.Name == "Underglow" then p.Color = glow or GLOWS[math.random(#GLOWS)] end
		end
	end
	car:SetAttribute("TemplateName", car.Name)
	car:SetAttribute("PaintColor", paint)
	car:PivotTo(cf)
	for _, p in ipairs(car:GetDescendants()) do
		if p:IsA("BasePart") then p.Anchored = false end
	end
	car.Parent = carsFolder
	local seat = car.DriveSeat
	-- every seat: prompt opens its door, seats you, door closes. Getting out swings the door too.
	for _, s in ipairs(car:GetChildren()) do
		if s:IsA("Seat") or s:IsA("VehicleSeat") then
			local doorId = s:GetAttribute("Door")
			local pp = s:FindFirstChild("EnterPrompt")
			local last = s.Occupant
			if pp then
				pp.Triggered:Connect(function(player)
					local hrp, hum = NC.GetRoot(player)
					if not hum or hum.SeatPart or s.Occupant or s.Disabled then return end
					Spawner.SetDoor(car, doorId, true)
					task.wait(0.35)
					if s.Occupant == nil and hum.Parent then s:Sit(hum) end
					task.wait(0.5)
					Spawner.SetDoor(car, doorId, false)
				end)
			end
			s:GetPropertyChangedSignal("Occupant"):Connect(function()
				if pp then pp.Enabled = s.Occupant == nil end
				if last and not s.Occupant then Spawner.PulseDoor(car, doorId) end -- hopping out
				last = s.Occupant
			end)
		end
	end
	-- hand physics to the driver for smooth handling; take it back when empty
	seat:GetPropertyChangedSignal("Occupant"):Connect(function()
		local hum = seat.Occupant
		local player = hum and Players:GetPlayerFromCharacter(hum.Parent)
		if player then
			car:SetAttribute("LastUsed", os.clock())
			pcall(function() car.PrimaryPart:SetNetworkOwner(player) end)
		else
			-- old cars only (Kit cars return early in MakeCar)
			car.PrimaryPart.Drive.VectorVelocity = Vector3.zero
			car.PrimaryPart.Turn.AngularVelocity = Vector3.zero
			pcall(function() car.PrimaryPart:SetNetworkOwnershipAuto() end)
		end
	end)
	return car
end

-- parked cars
local parked = {}
local function fillSpot(spot)
	local car = Spawner.MakeCar(spot.CFrame - Vector3.new(0, 2.2, 0), nil, nil, nil, { parked = true })
	car.Name = "ParkedCar"
	parked[spot] = car
end
for _, spot in ipairs(root.CarSpawns:GetChildren()) do fillSpot(spot) end

-- personal cars
local personal = {}
local lastSpawn = {}
Remotes.SpawnCar.OnServerEvent:Connect(function(player)
	if player:GetAttribute("Jailed") then return end
	if lastSpawn[player] and os.clock() - lastSpawn[player] < 5 then
		NC.Notify(player, "Hold on, your ride is on the way...", Color3.fromRGB(255,200,80))
		return
	end
	local hrp, hum = NC.GetRoot(player)
	if not hrp or not hum or hum.Health <= 0 or hum.SeatPart then return end
	lastSpawn[player] = os.clock()
	if personal[player] then personal[player]:Destroy() end
	local look = hrp.CFrame.LookVector * Vector3.new(1, 0, 1)
	if look.Magnitude < 0.1 then look = Vector3.new(0, 0, -1) end
	look = look.Unit
	local right = look:Cross(Vector3.yAxis)
	-- try spots round the player until one is clear: ground under it, nothing solid where the car would stand
	local params = RaycastParams.new(); params.FilterDescendantsInstances = {player.Character, carsFolder}
	local overlap = OverlapParams.new(); overlap.FilterDescendantsInstances = {player.Character}
	local function clearAt(pos)
		local hit = workspace:Raycast(pos + Vector3.new(0, 30, 0), Vector3.new(0, -80, 0), params)
		if not hit or math.abs(hit.Position.Y - (hrp.Position.Y - 3)) > 12 then return nil end
		local at = CFrame.lookAt(hit.Position, hit.Position + look)
		-- the car's footprint (about 9 x 21 studs), from just above the ground to roof height
		for _, part in workspace:GetPartBoundsInBox(at * CFrame.new(0, 3.6, 0), Vector3.new(9.5, 6, 21.5), overlap) do
			if part.CanCollide and part ~= hit.Instance then return nil end
		end
		return at
	end
	local spot
	for _, off in ipairs({ right * 12, -right * 12, right * 18, -right * 18, look * 16, -look * 16, right * 26, -right * 26,
		look * 26 + right * 12, look * 26 - right * 12, -look * 26 + right * 12, -look * 26 - right * 12 }) do
		spot = clearAt(hrp.Position + off)
		if spot then break end
	end
	if not spot then
		lastSpawn[player] = nil
		NC.Notify(player, "No room for a car here. Try somewhere more open.", Color3.fromRGB(255,200,80))
		return
	end
	local car = Spawner.MakeCar(spot)
	car.Name = player.Name .. "'s Car"
	car:SetAttribute("Owner", player.UserId)
	personal[player] = car
	NC.Notify(player, "Your ride is here! Press F at a door to hop in.", Color3.fromRGB(60,230,255))
end)

-- G while seated: toggle all doors + trunk on the car you're in
Remotes.ToggleDoors.OnServerEvent:Connect(function(player)
	local _, hum = NC.GetRoot(player)
	local seat = hum and hum.SeatPart
	local car = seat and seat.Parent
	if car and car:GetAttribute("IsCar") and not car:IsDescendantOf(root.Police) then Spawner.ToggleAll(car) end
end)
Players.PlayerRemoving:Connect(function(player)
	if personal[player] then personal[player]:Destroy() personal[player] = nil end
	lastSpawn[player] = nil
end)

-- housekeeping: respawn parked cars that were driven off/abandoned, clean up fallen cars
task.spawn(function()
	while true do
		task.wait(10)
		for spot, car in pairs(parked) do
			local gone = not car.Parent or not car.PrimaryPart
			local abandoned = not gone and not car.DriveSeat.Occupant
				and (car.PrimaryPart.Position - spot.Position).Magnitude > 30
				and os.clock() - (car:GetAttribute("LastUsed") or 0) > 90
			if gone or abandoned then
				if car.Parent then car:Destroy() end
				fillSpot(spot)
			end
		end
		for _, car in ipairs(carsFolder:GetChildren()) do
			if car.PrimaryPart and car.PrimaryPart.Position.Y < -40 then car:Destroy() end
		end
	end
end)

_G.NeonCoastSpawner = Spawner
