-- Neon Coast: Coast Patrol cars chase wanted players and bust them (no weapons, no injuries)
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local NC = require(script.Parent:WaitForChild("NC"))

local root = workspace:WaitForChild("NeonCoast")
local policeFolder = root:WaitForChild("Police")
local waypoints = root:WaitForChild("Waypoints"):GetChildren()
while not _G.NeonCoastSpawner do task.wait() end
local Spawner = _G.NeonCoastSpawner

local MAX_PER_PLAYER = 3
local CHASE_SPEED = 100
local BUST_RANGE = 16

local cops = {} -- car -> state

local SS = game:GetService("ServerStorage")
local function spawnCop(player, hrp, heavy)
	-- pick an intersection 180-420 studs away so it arrives from off-screen
	local best
	for _ = 1, 30 do
		local w = waypoints[math.random(#waypoints)]
		local d = (w.Position - hrp.Position).Magnitude
		if d > 180 and d < 420 then best = w break end
		best = best or w
	end
	local pos = best.Position + Vector3.new(0, 0.5, 0)
	-- regular patrols use the Coast Patrol cruiser; at 4+ stars an armored truck joins in
	local templateName = heavy and SS.CarTemplates:FindFirstChild("ArmoredTruck") and "ArmoredTruck" or "PoliceCruiser"
	if not SS.CarTemplates:FindFirstChild(templateName) then templateName = "NorrbyDL84" end
	local car = Spawner.MakeCar(CFrame.lookAt(pos, Vector3.new(hrp.Position.X, pos.Y, hrp.Position.Z)), Color3.fromRGB(30, 50, 120), Color3.fromRGB(80,160,255), templateName)
	car.Name = heavy and "ArmoredUnit" or "PatrolCar"
	car.Parent = policeFolder
	local chassisPart = car.PrimaryPart
	local function bar(name, x, color)
		local bbCF, bbSize = car:GetBoundingBox()
		local roofTop = CFrame.new(chassisPart.Position.X, bbCF.Position.Y + bbSize.Y / 2, chassisPart.Position.Z) * chassisPart.CFrame.Rotation * CFrame.new(0, 0, 1)
		local p = Instance.new("Part"); p.Name = name; p.Size = Vector3.new(2.6, 0.6, 1); p.Material = Enum.Material.Neon; p.Color = color
		p.CanCollide = false; p.Massless = true; p.CFrame = roofTop * CFrame.new(x, 0.3, 0); p.Parent = car
		local w = Instance.new("WeldConstraint"); w.Part0 = chassisPart; w.Part1 = p; w.Parent = p
		local l = Instance.new("PointLight"); l.Range = 22; l.Brightness = 3; l.Color = color; l.Parent = p
		return p
	end
	-- the cruiser + armored truck come with their own light bars
	local red = car:FindFirstChild("SirenRed", true) or bar("SirenRed", -1.4, Color3.fromRGB(255,40,60))
	local blue = car:FindFirstChild("SirenBlue", true) or bar("SirenBlue", 1.4, Color3.fromRGB(40,120,255))
	-- the seat is AI-driven: nobody can sit in it
	car.DriveSeat.Disabled = true
	for _, s in ipairs(car:GetChildren()) do if s:IsA("Seat") then s.Disabled = true end end
	for _, d in ipairs(car:GetDescendants()) do if d:IsA("ProximityPrompt") then d:Destroy() end end
	pcall(function() car.PrimaryPart:SetNetworkOwner(nil) end)
	cops[car] = {target = player, red = red, blue = blue, stuck = 0, reverseUntil = 0, speed = 0, born = os.clock()}
end

local function removeCop(car)
	cops[car] = nil
	if car.Parent then car:Destroy() end
end

-- manage how many cops chase each player
task.spawn(function()
	while true do
		task.wait(1)
		local counts, heavyCount = {}, {}
		for car, st in pairs(cops) do
			local stars = st.target.Parent and (st.target:GetAttribute("Stars") or 0) or 0
			if not car.Parent or not car.PrimaryPart or stars == 0 or st.target:GetAttribute("Jailed") or car.PrimaryPart.Position.Y < -30 then
				removeCop(car)
			else
				counts[st.target] = (counts[st.target] or 0) + 1
				if car.Name == "ArmoredUnit" then heavyCount[st.target] = (heavyCount[st.target] or 0) + 1 end
			end
		end
		for _, player in ipairs(Players:GetPlayers()) do
			local stars = player:GetAttribute("Stars") or 0
			local want = math.min(stars, MAX_PER_PLAYER)
			local hrp = NC.GetRoot(player)
			if hrp and not player:GetAttribute("Jailed") then
				if (counts[player] or 0) < want then
					spawnCop(player, hrp, false)
				elseif stars >= 4 and (heavyCount[player] or 0) == 0 then
					spawnCop(player, hrp, true) -- one armored truck on top of the patrol cars
				end
			end
		end
	end
end)

-- drive every patrol car toward its target
local flash = 0
RunService.Heartbeat:Connect(function(dt)
	flash += dt
	local on = math.floor(flash * 6) % 2 == 0
	local now = os.clock()
	for car, st in pairs(cops) do
		local chassis = car.PrimaryPart
		local hrp, hum = NC.GetRoot(st.target)
		if chassis and hrp and hum then
			st.red.Transparency = on and 0 or 0.8
			st.blue.Transparency = on and 0.8 or 0
			local pos = chassis.Position
			local toT = (hrp.Position - pos) * Vector3.new(1, 0, 1)
			local dist = toT.Magnitude
			local look = chassis.CFrame.LookVector * Vector3.new(1, 0, 1)
			look = look.Magnitude > 0.01 and look.Unit or Vector3.new(0, 0, -1)
			local dir = dist > 0.1 and toT.Unit or look
			local cross = look:Cross(dir).Y
			local angle = math.acos(math.clamp(look:Dot(dir), -1, 1))
			local turn = math.sign(cross) * math.min(angle * 2.5, 2.2)
			local targetSpeed = dist > 60 and CHASE_SPEED or math.max(20, dist * 1.1)
			if angle > 1.4 then targetSpeed = math.min(targetSpeed, 35) end

			-- unstick: if barely moving for a while, back up while turning
			local actual = (chassis.AssemblyLinearVelocity * Vector3.new(1, 0, 1)).Magnitude
			if now < st.reverseUntil then
				targetSpeed = -30
				turn = -turn
			elseif actual < 6 and now - st.born > 2 then
				st.stuck += dt
				if st.stuck > 1.2 then st.reverseUntil = now + 1.3; st.stuck = 0 end
			else
				st.stuck = 0
			end
			st.speed += math.clamp(targetSpeed - st.speed, -90 * dt, 45 * dt)
			chassis.Drive.VectorVelocity = look * st.speed
			chassis.Turn.AngularVelocity = Vector3.new(0, turn * math.clamp(math.abs(st.speed) / 20, 0.3, 1) * (st.speed < 0 and -1 or 1), 0)

			-- bust check: close to the player and they are slow (on foot or crawling in a car)
			if dist < BUST_RANGE then
				local tv = hum.SeatPart and hum.SeatPart.AssemblyLinearVelocity or hrp.AssemblyLinearVelocity
				if (tv * Vector3.new(1, 0, 1)).Magnitude < 22 and not st.target:GetAttribute("Jailed") then
					task.spawn(NC.Bust, st.target)
					NC.Notify(st.target, "BUSTED by the Coast Patrol!", Color3.fromRGB(80,160,255))
				end
			end
		end
	end
end)
