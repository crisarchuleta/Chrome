--!nonstrict
-- FitnessService (server): your body. Strength, Stamina, Body fat and Energy, saved, changed by what you do and eat.
--   * Activity: the server watches every character. Sprinting and swimming build stamina, climbing builds a little
--     strength, everything burns calories (more the harder you go) on top of a base burn.
--   * Food (stalls tagged NC_Food with a Menu attribute): pay with Cash, the calories digest over a few minutes;
--     more than you burn turns slowly into fat, less burns it off. Energy refills; soda gives a sugar rush then a crash;
--     a protein shake boosts your next workouts.
--   * Gyms (stations tagged NC_Gym with an Exercise attribute): a short rhythm workout per set; good form gains more,
--     low energy gains less, the stronger you are the slower it comes.
--   * Your body changes what you can do (speed, sprint time, jump, climb, fall damage, swim, carry, health) and how
--     you look (width / depth), for everyone: player attributes Body* (MovementClient, missions and others read them).
--   * Builds the Iron Tide Gym and Muscle Beach on the sand and food stands around downtown if the map has none.
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local SSS = game:GetService("ServerScriptService")
local CollectionService = game:GetService("CollectionService")
local DataStoreService = game:GetService("DataStoreService")

local C = require(RS:WaitForChild("NCFitnessConfig"))
local NC
pcall(function()
	NC = require(SSS:WaitForChild("NC", 5))
end)

local Remotes = RS:FindFirstChild("Remotes") or Instance.new("Folder")
Remotes.Name = "Remotes"
Remotes.Parent = RS
local function remote(name)
	local r = Remotes:FindFirstChild(name) or Instance.new("RemoteEvent")
	r.Name = name
	r.Parent = Remotes
	return r
end
local BodyRE = remote("BodyAction")   -- client -> server: eat / workout reps / leave
local BodyUI = remote("BodyUI")       -- server -> client: open a menu, start a workout, messages

local store
pcall(function()
	store = DataStoreService:GetDataStore("NeonCoast_Body_v1")
end)

local function notify(p, text, color)
	if NC and NC.Notify then
		pcall(NC.Notify, p, text, color)
	end
end
local function cashOf(p)
	if NC and NC.GetCash then
		return NC.GetCash(p)
	end
	local ls = p:FindFirstChild("leaderstats")
	return ls and ls:FindFirstChild("Cash")
end
local function spend(p, amount)
	local c = cashOf(p)
	if not c or c.Value < amount then
		return false
	end
	if NC and NC.AddCash then
		NC.AddCash(p, -amount)
	else
		c.Value -= amount
	end
	return true
end

---------------------------------------------------------------------------------------------- per-player body
local B = {} -- player -> state

local function publish(p, st, force)
	local e = C.Effects(st.str, st.sta, st.fat)
	p:SetAttribute("BodyStr", math.floor(st.str * 10) / 10)
	p:SetAttribute("BodySta", math.floor(st.sta * 10) / 10)
	p:SetAttribute("BodyFat", math.floor(st.fat * 10) / 10)
	p:SetAttribute("BodyEnergy", math.floor(st.energy))
	p:SetAttribute("BodyBuild", C.Build(st.str, st.sta, st.fat))
	p:SetAttribute("BodyKcalIn", math.floor(st.kcalIn))
	p:SetAttribute("BodyKcalOut", math.floor(st.kcalOut))
	local now = os.clock()
	local rush = (st.rushUntil and now < st.rushUntil) and 1.05 or ((st.crashUntil and now < st.crashUntil) and 0.95 or 1)
	local tired = st.energy < 15 and 0.92 or 1
	p:SetAttribute("BodySpeed", e.speed * rush * tired)
	p:SetAttribute("BodySprintTime", e.sprintTime * (st.energy < 15 and 0.6 or 1))
	p:SetAttribute("BodyRegen", e.regen)
	p:SetAttribute("BodyJump", e.jump)
	p:SetAttribute("BodyClimbMax", e.climbMax)
	p:SetAttribute("BodyClimbSpeed", e.climbSpeed)
	p:SetAttribute("BodyFall", e.fall)
	p:SetAttribute("BodySwim", e.swim)
	p:SetAttribute("BodyCarry", e.carry)
	p:SetAttribute("BodyPunch", e.punch)
	p:SetAttribute("BodyProtein", (st.proteinUntil and now < st.proteinUntil) or nil)
	-- the body you can see: max health, and the frame (only when it has changed enough to show)
	local char = p.Character
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if hum and hum.Health > 0 then
		local mh = math.floor(e.maxHealth)
		if math.abs(hum.MaxHealth - mh) >= 1 then
			local frac = hum.Health / math.max(1, hum.MaxHealth)
			hum.MaxHealth = mh
			hum.Health = math.min(mh, mh * frac)
		end
		local w, d = C.Shape(st.str, st.sta, st.fat)
		if force or math.abs(w - (st.shapeW or 0)) > 0.015 or math.abs(d - (st.shapeD or 0)) > 0.015 then
			st.shapeW, st.shapeD = w, d
			for name, mul in { BodyWidthScale = w, BodyDepthScale = d } do
				local v = hum:FindFirstChild(name)
				if v and v:IsA("NumberValue") then
					-- remember the look's own build (Character Studio) and scale on top of it
					local base = v:GetAttribute("NC_LookBase")
					if not base or math.abs(v.Value - (v:GetAttribute("NC_Set") or -1)) > 1e-3 then
						base = v.Value
						v:SetAttribute("NC_LookBase", base)
					end
					v.Value = base * mul
					v:SetAttribute("NC_Set", v.Value)
				end
			end
		end
	end
end

local function load(p)
	local st = { str = C.START.str, sta = C.START.sta, fat = C.START.fat, energy = C.START.energy, stomach = 0, stomachE = 0,
		kcalIn = 0, kcalOut = 0, dayT = 0, lastSave = os.clock() }
	if store then
		local ok, data = pcall(function()
			return store:GetAsync("u" .. p.UserId)
		end)
		if ok and type(data) == "table" then
			for _, k in { "str", "sta", "fat", "energy" } do
				if type(data[k]) == "number" then
					st[k] = data[k]
				end
			end
		end
	end
	B[p] = st
	publish(p, st, true)
end

local function save(p)
	local st = B[p]
	if not (store and st) then
		return
	end
	local data = { str = st.str, sta = st.sta, fat = st.fat, energy = st.energy }
	for _ = 1, 3 do
		if pcall(function()
			store:SetAsync("u" .. p.UserId, data)
		end) then
			return
		end
		task.wait(1)
	end
end

local function train(st, stat, amount)
	-- the more you have, the slower it comes
	local cur = st[stat]
	st[stat] = math.min(100, cur + amount * (1 - cur / 110))
end

---------------------------------------------------------------------------------------------- the body clock
local lastPos = {}
task.spawn(function()
	while true do
		local dt = task.wait(1)
		for _, p in Players:GetPlayers() do
			local st = B[p]
			local char = p.Character
			local hrp = char and char:FindFirstChild("HumanoidRootPart")
			local hum = char and char:FindFirstChildOfClass("Humanoid")
			if not (st and hrp and hum) then
				continue
			end
			-- what are you doing?
			local pos = hrp.Position
			local prev = lastPos[p]
			lastPos[p] = pos
			local moved = prev and Vector3.new(pos.X - prev.X, 0, pos.Z - prev.Z).Magnitude or 0
			local speed = moved / dt
			local burn = C.BASE_KCAL_PER_DAY / C.DAY_SECONDS
			local seated = hum.SeatPart ~= nil
			local swimming = char:GetAttribute("SwimPose") ~= nil or hum:GetState() == Enum.HumanoidStateType.Swimming
			if seated or speed > 120 then
				-- driving, or a teleport: no exercise
			elseif swimming then
				burn += C.BURN.swim
				train(st, "sta", math.min(moved, 40) * C.STA_PER_STUD_SWIM)
			elseif speed > 19 then
				burn += C.BURN.sprint
				train(st, "sta", math.min(moved, 40) * C.STA_PER_STUD_SPRINT)
			elseif speed > 9 then
				burn += C.BURN.jog
				train(st, "sta", math.min(moved, 40) * C.STA_PER_STUD_SPRINT * 0.25)
			elseif speed > 1.5 then
				burn += C.BURN.walk
			end
			local act = char:GetAttribute("MoveAct")
			if type(act) == "string" and act ~= st.lastAct then
				st.lastAct = act
				if act:sub(1, 5) == "climb" or act:sub(1, 6) == "mantle" then
					train(st, "str", C.STR_PER_CLIMB)
					burn += C.BURN.climb
				end
			end
			-- digestion: calories and energy reach the body a little at a time
			local dig = math.min(st.stomach, C.DIGEST_KCAL_PER_SEC * dt)
			local digE = st.stomach > 0 and st.stomachE * (dig / st.stomach) or 0
			st.stomach -= dig
			st.stomachE -= digE
			st.kcalIn += dig
			st.kcalOut += burn * dt
			-- surplus becomes fat, a deficit burns it (slowly, like a real body)
			st.fat = math.clamp(st.fat + (dig - burn * dt) / C.KCAL_PER_FAT_PERCENT, 8, 40)
			st.energy = math.clamp(st.energy + digE - burn * dt * C.ENERGY_PER_KCAL_BURNED, 0, 100)
			-- untrained muscle and wind fade, slowly
			local decay = C.DECAY_PER_HOUR / 3600 * dt
			if st.str > 10 then
				st.str -= decay
			end
			if st.sta > 10 then
				st.sta -= decay
			end
			-- a new day: reset the calorie counters
			st.dayT += dt
			if st.dayT >= C.DAY_SECONDS then
				st.dayT, st.kcalIn, st.kcalOut = 0, 0, 0
			end
			if st.energy <= 0 and not st.warnedEmpty then
				st.warnedEmpty = true
				notify(p, "You're running on empty. Eat something.", Color3.fromRGB(255, 170, 80))
			elseif st.energy > 20 then
				st.warnedEmpty = false
			end
			publish(p, st)
			if os.clock() - st.lastSave > 150 then
				st.lastSave = os.clock()
				task.spawn(save, p)
			end
		end
	end
end)

---------------------------------------------------------------------------------------------- food
local function setupFood(part)
	if part:GetAttribute("NC_FoodReady") or not part:IsDescendantOf(workspace) then
		return
	end
	part:SetAttribute("NC_FoodReady", true)
	local pp = Instance.new("ProximityPrompt")
	pp.Name = "Order"
	pp.ActionText = "Order"
	pp.ObjectText = part:GetAttribute("Title") or "Food"
	pp.HoldDuration = 0
	pp.MaxActivationDistance = 10
	pp.RequiresLineOfSight = false
	pp.Parent = part
	pp.Triggered:Connect(function(p)
		BodyUI:FireClient(p, "menu", part, C.MENUS[part:GetAttribute("Menu")] or C.MENUS.Vending)
	end)
end

local function eat(p, stall, item)
	local st = B[p]
	local f = C.FOODS[item]
	local char = p.Character
	local hrp = char and char:FindFirstChild("HumanoidRootPart")
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if not (st and f and hrp and hum and typeof(stall) == "Instance" and CollectionService:HasTag(stall, "NC_Food")) then
		return
	end
	local menu = C.MENUS[stall:GetAttribute("Menu")] or C.MENUS.Vending
	if not table.find(menu, item) or (stall.Position - hrp.Position).Magnitude > 14 then
		return
	end
	if st.stomach > 2400 then
		notify(p, "You're stuffed. Give it a minute.", Color3.fromRGB(255, 200, 120))
		return
	end
	if not spend(p, f.price) then
		notify(p, ("%s costs $%d."):format(f.label, f.price), Color3.fromRGB(255, 120, 90))
		return
	end
	st.stomach += f.kcal
	st.stomachE += f.energy
	hum.Health = math.min(hum.MaxHealth, hum.Health + f.health)
	local now = os.clock()
	if f.rush then
		st.rushUntil = now + C.RUSH_SECONDS
		st.crashUntil = now + C.RUSH_SECONDS + C.CRASH_SECONDS
	end
	if f.protein then
		st.proteinUntil = now + C.PROTEIN_SECONDS
	end
	char:SetAttribute("Eating", item .. "|" .. string.format("%.2f", workspace:GetServerTimeNow()))
	notify(p, ("%s: +%d kcal"):format(f.label, f.kcal), f.junk and Color3.fromRGB(255, 190, 90) or Color3.fromRGB(120, 230, 140))
	publish(p, st)
end

---------------------------------------------------------------------------------------------- gyms
local sessions = {} -- player -> { station, last, reps }

local function endWorkout(p, why)
	local s = sessions[p]
	if not s then
		return
	end
	sessions[p] = nil
	s.station:SetAttribute("User", nil)
	local char = p.Character
	if char then
		char:SetAttribute("Workout", nil)
		char:SetAttribute("WorkoutRep", nil)
		local hrp = char:FindFirstChild("HumanoidRootPart")
		if hrp then
			hrp.Anchored = false
		end
	end
	BodyUI:FireClient(p, "workoutEnd", s.reps, why)
end

local function startWorkout(p, station)
	local st = B[p]
	local ex = C.EXERCISES[station:GetAttribute("Exercise")]
	local char = p.Character
	local hrp = char and char:FindFirstChild("HumanoidRootPart")
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if not (st and ex and hrp and hum) or hum.SeatPart or sessions[p] then
		return
	end
	if station:GetAttribute("User") then
		notify(p, "Someone's using that. Wait your turn.", Color3.fromRGB(255, 200, 120))
		return
	end
	if st.energy < 5 then
		notify(p, "No energy to train. Eat first.", Color3.fromRGB(255, 170, 80))
		return
	end
	station:SetAttribute("User", p.UserId)
	sessions[p] = { station = station, last = 0, reps = 0 }
	local spot = station:FindFirstChild("Spot")
	if spot and spot:IsA("Attachment") then
		local rootH = hrp.Size.Y / 2 + hum.HipHeight
		local cf = spot.WorldCFrame
		hrp.CFrame = cf + Vector3.new(0, rootH, 0)
	end
	hrp.Anchored = true
	char:SetAttribute("Workout", station:GetAttribute("Exercise"))
	char:SetAttribute("WorkoutRep", 0)
	BodyUI:FireClient(p, "workout", station, ex.label, station:GetAttribute("Exercise"))
end

local function rep(p, station, quality)
	local s = sessions[p]
	local st = B[p]
	if not (s and st and s.station == station and typeof(quality) == "number") then
		return
	end
	local ex = C.EXERCISES[station:GetAttribute("Exercise")]
	local now = os.clock()
	if now - s.last < ex.minRep * 0.9 then
		return -- faster than a real rep
	end
	s.last = now
	quality = math.clamp(quality, 0, 1)
	local fuel = st.energy > 30 and 1 or (st.energy > 10 and 0.6 or 0.25)
	local protein = (st.proteinUntil and now < st.proteinUntil and ex.stat == "str") and C.PROTEIN_BONUS or 1
	train(st, ex.stat, ex.gain * (0.3 + 0.7 * quality) * fuel * protein)
	if ex.alsoSta then
		train(st, "sta", ex.alsoSta * quality * fuel)
	end
	st.energy = math.max(0, st.energy - ex.energy)
	st.kcalOut += ex.kcal
	st.fat = math.clamp(st.fat - ex.kcal / C.KCAL_PER_FAT_PERCENT, 8, 40)
	s.reps += 1
	local char = p.Character
	if char then
		char:SetAttribute("WorkoutRep", s.reps)
	end
	publish(p, st)
	if st.energy <= 0 then
		endWorkout(p, "empty")
	end
end

local function setupGym(station)
	if station:GetAttribute("NC_GymReady") or not station:IsDescendantOf(workspace) then
		return
	end
	station:SetAttribute("NC_GymReady", true)
	local ex = C.EXERCISES[station:GetAttribute("Exercise")]
	local pp = Instance.new("ProximityPrompt")
	pp.Name = "Workout"
	pp.ActionText = "Work out"
	pp.ObjectText = ex and ex.label or "Gym"
	pp.HoldDuration = 0.2
	pp.MaxActivationDistance = 8
	pp.RequiresLineOfSight = false
	pp.Parent = station
	pp.Triggered:Connect(function(p)
		startWorkout(p, station)
	end)
end

BodyRE.OnServerEvent:Connect(function(p, kind, a, b)
	if kind == "eat" then
		eat(p, a, b)
	elseif kind == "rep" then
		rep(p, a, b)
	elseif kind == "leave" then
		endWorkout(p, "left")
	end
end)

---------------------------------------------------------------------------------------------- places to train and eat
local function ground(x, z)
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = {}
	local hit = workspace:Raycast(Vector3.new(x, 600, z), Vector3.new(0, -1200, 0), params)
	return hit and hit.Position or Vector3.new(x, 0, z)
end

local function P(parent, name, size, cf, color, mat, shape)
	local p = Instance.new("Part")
	p.Name = name
	p.Size = size
	p.CFrame = cf
	p.Anchored = true
	p.Color = color
	p.Material = mat or Enum.Material.SmoothPlastic
	p.TopSurface, p.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
	if shape then
		p.Shape = shape
	end
	p.Parent = parent
	return p
end

local STEEL, BLACK, RED = Color3.fromRGB(150, 155, 160), Color3.fromRGB(28, 28, 32), Color3.fromRGB(190, 40, 40)

-- one piece of equipment at cf (cf faces the way the user faces); returns the station part
local function equipment(parent, kind, cf)
	local m = Instance.new("Model")
	m.Name = kind
	m.Parent = parent
	local station
	if kind == "Bench" then
		station = P(m, "Bench", Vector3.new(1.6, 0.5, 5), cf * CFrame.new(0, 1.6, 0), BLACK, Enum.Material.Fabric)
		for _, z in { -2, 2 } do
			P(m, "Leg", Vector3.new(1.2, 1.4, 0.3), cf * CFrame.new(0, 0.7, z), STEEL, Enum.Material.Metal)
		end
		for _, x in { -1.6, 1.6 } do
			P(m, "Upright", Vector3.new(0.25, 4.2, 0.25), cf * CFrame.new(x, 2.1, -2.0), STEEL, Enum.Material.Metal)
		end
		P(m, "Bar", Vector3.new(6, 0.18, 0.18), cf * CFrame.new(0, 4.0, -2.0), STEEL, Enum.Material.Metal, Enum.PartType.Cylinder)
		for _, x in { -2.6, 2.6 } do
			P(m, "Plate", Vector3.new(0.3, 1.5, 1.5), cf * CFrame.new(x, 4.0, -2.0), BLACK, Enum.Material.Metal, Enum.PartType.Cylinder)
		end
		-- lying on the bench, head under the bar
		local spot = Instance.new("Attachment")
		spot.Name = "Spot"
		spot.CFrame = CFrame.new(0, 1.85, -0.3)
		spot.Parent = station
	elseif kind == "Squat" or kind == "Pullup" then
		station = P(m, kind == "Squat" and "SquatRack" or "PullupBar", Vector3.new(5, 0.3, 4), cf * CFrame.new(0, 0.15, 0), Color3.fromRGB(60, 60, 66), Enum.Material.Rubber)
		for _, x in { -2.2, 2.2 } do
			P(m, "Post", Vector3.new(0.35, 9, 0.35), cf * CFrame.new(x, 4.5, -1.2), STEEL, Enum.Material.Metal)
		end
		P(m, "Bar", Vector3.new(4.6, 0.2, 0.2), cf * CFrame.new(0, kind == "Squat" and 5.6 or 8.6, -1.2), STEEL, Enum.Material.Metal)
		if kind == "Squat" then
			for _, x in { -2.0, 2.0 } do
				P(m, "Plate", Vector3.new(0.3, 1.6, 1.6), cf * CFrame.new(x, 5.6, -1.2), RED, Enum.Material.Metal, Enum.PartType.Cylinder)
			end
		end
		local spot = Instance.new("Attachment")
		spot.Name = "Spot"
		spot.CFrame = CFrame.new(0, 0.3, kind == "Squat" and -0.9 or -1.2)
		spot.Parent = station
	elseif kind == "Curl" then
		station = P(m, "DumbbellRack", Vector3.new(4, 2.4, 1.4), cf * CFrame.new(0, 1.2, -1.5), BLACK, Enum.Material.Metal)
		for i = -1, 1 do
			P(m, "Dumbbell", Vector3.new(1.0, 0.35, 0.35), cf * CFrame.new(i * 1.2, 2.6, -1.5), STEEL, Enum.Material.Metal, Enum.PartType.Cylinder)
		end
		local spot = Instance.new("Attachment")
		spot.Name = "Spot"
		spot.CFrame = CFrame.new(0, -1.2, 1.7)
		spot.Parent = station
	elseif kind == "Bag" then
		station = P(m, "BagStand", Vector3.new(4, 0.3, 4), cf * CFrame.new(0, 0.15, 0), Color3.fromRGB(60, 60, 66), Enum.Material.Rubber)
		P(m, "Arm", Vector3.new(0.3, 0.3, 2.4), cf * CFrame.new(0, 9, -1.6), STEEL, Enum.Material.Metal)
		P(m, "Post", Vector3.new(0.35, 9, 0.35), cf * CFrame.new(0, 4.5, -2.8), STEEL, Enum.Material.Metal)
		P(m, "Chain", Vector3.new(0.08, 1.4, 0.08), cf * CFrame.new(0, 8.2, -1.2), STEEL, Enum.Material.Metal)
		P(m, "PunchingBag", Vector3.new(4.2, 1.6, 1.6), cf * CFrame.new(0, 5.4, -1.2) * CFrame.Angles(0, 0, math.rad(90)), RED, Enum.Material.Leather, Enum.PartType.Cylinder)
		local spot = Instance.new("Attachment")
		spot.Name = "Spot"
		spot.CFrame = CFrame.new(0, 0.3, 0.6)
		spot.Parent = station
	elseif kind == "Treadmill" then
		station = P(m, "Treadmill", Vector3.new(2.6, 0.6, 6), cf * CFrame.new(0, 0.3, 0), BLACK, Enum.Material.Rubber)
		P(m, "Belt", Vector3.new(2.0, 0.05, 5.2), cf * CFrame.new(0, 0.62, 0), Color3.fromRGB(40, 40, 44), Enum.Material.Fabric)
		for _, x in { -1.2, 1.2 } do
			P(m, "Rail", Vector3.new(0.2, 3.6, 0.2), cf * CFrame.new(x, 2.1, -2.6), STEEL, Enum.Material.Metal)
		end
		P(m, "Console", Vector3.new(2.6, 0.9, 0.5), cf * CFrame.new(0, 3.9, -2.7) * CFrame.Angles(math.rad(-25), 0, 0), Color3.fromRGB(30, 30, 34), Enum.Material.SmoothPlastic)
		local spot = Instance.new("Attachment")
		spot.Name = "Spot"
		spot.CFrame = CFrame.new(0, 0.35, 0.4)
		spot.Parent = station
	end
	station:SetAttribute("Exercise", kind)
	CollectionService:AddTag(station, "NC_Gym")
	return station
end

local function stall(parent, title, menu, cf, color)
	local m = Instance.new("Model")
	m.Name = title
	m.Parent = parent
	local counter = P(m, "Counter", Vector3.new(6, 3.4, 2.4), cf * CFrame.new(0, 1.7, 0), color, Enum.Material.SmoothPlastic)
	P(m, "Top", Vector3.new(6.4, 0.3, 2.8), cf * CFrame.new(0, 3.55, 0), Color3.fromRGB(235, 232, 225), Enum.Material.Marble)
	for _, x in { -2.9, 2.9 } do
		P(m, "Pole", Vector3.new(0.2, 4.6, 0.2), cf * CFrame.new(x, 5.9, 0.9), STEEL, Enum.Material.Metal)
	end
	P(m, "Awning", Vector3.new(7, 0.3, 3.4), cf * CFrame.new(0, 8.3, 0.4) * CFrame.Angles(math.rad(-8), 0, 0), color, Enum.Material.Fabric)
	local sign = P(m, "Sign", Vector3.new(5, 1.2, 0.2), cf * CFrame.new(0, 9.2, 1.9), Color3.fromRGB(20, 20, 24), Enum.Material.SmoothPlastic)
	local g = Instance.new("SurfaceGui")
	g.Face = Enum.NormalId.Back
	g.Parent = sign
	local t = Instance.new("TextLabel")
	t.Size = UDim2.fromScale(1, 1)
	t.BackgroundTransparency = 1
	t.Text = title
	t.TextScaled = true
	t.Font = Enum.Font.GothamBlack
	t.TextColor3 = color:Lerp(Color3.new(1, 1, 1), 0.4)
	t.Parent = g
	counter:SetAttribute("Menu", menu)
	counter:SetAttribute("Title", title)
	CollectionService:AddTag(counter, "NC_Food")
	return counter
end

local function vending(parent, cf)
	local m = Instance.new("Model")
	m.Name = "VendingMachine"
	m.Parent = parent
	local body = P(m, "Vending", Vector3.new(3, 6.4, 2.4), cf * CFrame.new(0, 3.2, 0), Color3.fromRGB(200, 30, 50), Enum.Material.SmoothPlastic)
	P(m, "Window", Vector3.new(2.2, 3.6, 0.1), cf * CFrame.new(-0.2, 3.9, 1.22), Color3.fromRGB(140, 200, 230), Enum.Material.Glass).Transparency = 0.3
	P(m, "Glow", Vector3.new(0.4, 2.2, 0.08), cf * CFrame.new(1.15, 3.6, 1.24), Color3.fromRGB(80, 220, 255), Enum.Material.Neon)
	body:SetAttribute("Menu", "Vending")
	body:SetAttribute("Title", "Vending machine")
	CollectionService:AddTag(body, "NC_Food")
	return body
end

local function buildWorld()
	if #CollectionService:GetTagged("NC_Gym") > 0 and #CollectionService:GetTagged("NC_Food") > 0 then
		return
	end
	local root = workspace:FindFirstChild("NeonCoast") or workspace
	local folder = Instance.new("Folder")
	folder.Name = "NC_BodyPlaces"
	folder.Parent = root
	-- Iron Tide Gym: an open-air gym on the sand east of downtown, facing the city
	local function gymAt(name, x, z, kinds, withShop)
		local g = ground(x, z)
		local base = CFrame.new(g) * CFrame.Angles(0, math.rad(90), 0)       -- users face west, toward the city
		local m = Instance.new("Model")
		m.Name = name
		m.Parent = folder
		P(m, "Floor", Vector3.new(48, 0.4, 30), base * CFrame.new(0, 0.2, 0), Color3.fromRGB(70, 74, 80), Enum.Material.Rubber)
		local sign = P(m, "Sign", Vector3.new(20, 3, 0.4), base * CFrame.new(0, 12, 15), Color3.fromRGB(20, 20, 24))
		local sg = Instance.new("SurfaceGui")
		sg.Face = Enum.NormalId.Back
		sg.Parent = sign
		local tl = Instance.new("TextLabel")
		tl.Size, tl.BackgroundTransparency, tl.Text, tl.TextScaled = UDim2.fromScale(1, 1), 1, name, true
		tl.Font, tl.TextColor3 = Enum.Font.GothamBlack, Color3.fromRGB(255, 120, 60)
		tl.Parent = sg
		for _, x in { -9.5, 9.5 } do
			P(m, "SignPost", Vector3.new(0.5, 12, 0.5), base * CFrame.new(x, 6, 15), STEEL, Enum.Material.Metal)
		end
		for i, k in kinds do
			local col, row = (i - 1) % 4, math.floor((i - 1) / 4)
			equipment(m, k, base * CFrame.new(-18 + col * 12, 0.4, -6 + row * 12))
		end
		if withShop then
			stall(m, "Iron Tide Fuel", "Gym", base * CFrame.new(18, 0.4, 10) * CFrame.Angles(0, math.rad(180), 0), Color3.fromRGB(255, 120, 60))
		end
	end
	gymAt("IRON TIDE GYM", 4300, -40, { "Bench", "Squat", "Pullup", "Curl", "Bag", "Treadmill", "Treadmill", "Bench" }, true)
	gymAt("MUSCLE BEACH", 4300, -620, { "Pullup", "Curl", "Bag", "Squat" }, false)
	-- food around downtown and the beach
	local spots = {}
	local jp = root:FindFirstChild("JobPoints")
	if jp then
		for _, d in jp:GetChildren() do
			if d:IsA("BasePart") then
				table.insert(spots, d.Position)
			end
		end
	end
	local stalls = {
		{ "SOL'S TACOS", "Taco", Color3.fromRGB(255, 150, 40) }, { "COAST BURGER", "Burger", Color3.fromRGB(220, 50, 40) },
		{ "SLICE CITY", "Pizza", Color3.fromRGB(240, 200, 60) }, { "SUNRISE CAFE", "Cafe", Color3.fromRGB(150, 100, 70) },
		{ "GREEN WAVE", "Healthy", Color3.fromRGB(70, 200, 110) },
	}
	for i, s in stalls do
		local pos = spots[(i * 3) % math.max(1, #spots) + 1]
		if pos then
			local g = ground(pos.X + 6, pos.Z + 6)
			stall(folder, s[1], s[2], CFrame.new(g) * CFrame.Angles(0, math.rad(45 * i), 0), s[3])
		end
	end
	for _, xz in { { 2470, -40 }, { 4300, -10 }, { 4300, -600 }, { 1850, -40 } } do
		vending(folder, CFrame.new(ground(xz[1], xz[2])) * CFrame.Angles(0, math.rad(90), 0))
	end
end

task.spawn(function()
	buildWorld()
	while true do
		for _, f in CollectionService:GetTagged("NC_Food") do
			setupFood(f)
		end
		for _, g in CollectionService:GetTagged("NC_Gym") do
			setupGym(g)
		end
		task.wait(3)
	end
end)

---------------------------------------------------------------------------------------------- players
local function onPlayer(p)
	load(p)
	p.CharacterAdded:Connect(function(char)
		endWorkout(p, "respawn")
		local st = B[p]
		if st then
			st.shapeW, st.shapeD = nil, nil
			-- let the look (Character Studio) apply first, then put the body on top
			task.delay(2.5, function()
				if B[p] and p.Character == char then
					publish(p, B[p], true)
				end
			end)
		end
	end)
end
Players.PlayerAdded:Connect(onPlayer)
for _, p in Players:GetPlayers() do
	task.spawn(onPlayer, p)
end
Players.PlayerRemoving:Connect(function(p)
	endWorkout(p, "left")
	save(p)
	B[p], lastPos[p] = nil, nil
end)
game:BindToClose(function()
	for _, p in Players:GetPlayers() do
		save(p)
	end
end)

-- for missions and other scripts: shared.NCBody.Get(player) -> { str, sta, fat, energy }; .Train(player, stat, amount)
shared.NCBody = {
	Get = function(p)
		local st = B[p]
		return st and { str = st.str, sta = st.sta, fat = st.fat, energy = st.energy } or nil
	end,
	Train = function(p, stat, amount)
		local st = B[p]
		if st and (stat == "str" or stat == "sta") then
			train(st, stat, amount)
			publish(p, st)
		end
	end,
}
