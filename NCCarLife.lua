--!nonstrict
-- NCCarLife (ModuleScript, ReplicatedStorage): the sounds and lights that make the customization-system vehicles
-- feel alive. Runs on every client, for every nearby Kit car (LowriderClient calls CarLife.Update each frame):
--   engine     three seamless loops per engine type (low / mid / high rpm) crossfaded by a simulated gearbox, a
--              start-up and shut-down, rev-matched upshifts and exhaust pops (with a flash) when you lift off high
--   lights     headlights (off / on / high beams; on by themselves at night), dim tail lights with the headlights,
--              bright brake lights, white reverse lights, amber indicators and hazards
--   horn       held while the driver holds H (car, truck and bike horns)
--   siren      Coast Patrol: wail / yelp and the light bar flashing red and blue
--   hydraulics pump whine while a corner lifts, a dump hiss when it drops fast
-- What the driver sets (horn, lights, indicators, siren) lives in car attributes the server sets from the
-- VehicleControl remote (LowriderService): Horn (bool), Lights (0 off / 1 on / 2 high; nil = automatic),
-- Signal ("L" / "R" / "H" / ""), Siren (0 off / 1 wail / 2 yelp). Brake and reverse lights come from the seat.
-- Sound ids: NCLowriderConfig.Sounds[<file name>] (sounds/*.ogg from make_vehicle_sounds.py, uploaded in Studio).
-- A sound with no id yet is simply silent.
local RS = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local Lighting = game:GetService("Lighting")

local Config = require(RS:WaitForChild("NCLowriderConfig"))
local Vehicles = require(RS:WaitForChild("NCVehicles"))
local Kit = require(RS:WaitForChild("NCLowriderKit"))

local Life = {}

-- engine type per class (a vehicle can set engine = "..." in NCVehicles to override)
local ENGINE_OF = {
	lowrider = "v8", muscle = "v8", cruiser = "v8", luxury = "v8", sports = "v8", boxy = "i4", sedan = "i4", hatch = "i4",
	jdm = "i4", pickup = "truck", pickup50s = "truck", suv = "truck", van = "truck", armored = "diesel", cart = "electric",
}
local ENGINE_BY_ID = { KazeRS8 = "i4", PoliceCruiser = "v8", DirtBike = "single", SportBike = "sport4" }
-- the rpm each loop was recorded at (must match ENGINES in make_vehicle_sounds.py)
local SAMPLE_RPM = {
	v8 = { 900, 2800, 5600 }, truck = { 750, 2300, 4600 }, i4 = { 1000, 4000, 8000 }, diesel = { 700, 1800, 3200 },
	single = { 1500, 5000, 9500 }, sport4 = { 1500, 7000, 13000 },
}
local HORN_OF = { pickup = "horn_truck", pickup50s = "horn_truck", suv = "horn_truck", van = "horn_truck", armored = "horn_truck", bike = "horn_bike" }
local GEAR_TOP = { 0.17, 0.34, 0.53, 0.75, 1.0 } -- top of each gear as a fraction of top speed
local AMBER = Color3.fromRGB(255, 150, 20)

local function sid(name)
	return Config.Sounds and Config.Sounds[name] or ""
end

local function makeSound(parent, name, looped, vol, minD, maxD)
	local id = sid(name)
	if id == "" then
		return nil
	end
	local s = Instance.new("Sound")
	s.Name = "CL_" .. name
	s.SoundId = id
	s.Looped = looped
	s.Volume = vol or 0.6
	s.RollOffMode = Enum.RollOffMode.InverseTapered
	s.RollOffMinDistance = minD or 12
	s.RollOffMaxDistance = maxD or 260
	s.Parent = parent
	return s
end

local function oneShot(parent, name, vol, speed)
	local id = sid(name)
	if id == "" or not parent then
		return
	end
	local s = Instance.new("Sound")
	s.SoundId = id
	s.Volume = vol or 0.7
	s.PlaybackSpeed = speed or 1
	s.RollOffMode = Enum.RollOffMode.InverseTapered
	s.RollOffMinDistance = 12
	s.RollOffMaxDistance = 260
	s.Parent = parent
	s:Play()
	game:GetService("Debris"):AddItem(s, 4)
end

local function loopTo(s, want, playing, dt, rate)
	if not s then
		return
	end
	s.Volume += (want - s.Volume) * math.min(1, dt * (rate or 8))
	if playing and s.Volume > 0.01 then
		if not s.IsPlaying then
			s:Play()
		end
	elseif s.IsPlaying and s.Volume <= 0.01 then
		s:Stop()
	end
end

---------------------------------------------------------------------------------------------------- per-car rig
local rigs = {} -- strong (weak Instance keys got collected and rigs were rebuilt); cleared on Destroying

-- the car-frame half width of a part along the car's X axis
local function halfX(ch, p)
	local r = ch.CFrame:ToObjectSpace(p.CFrame)
	local sx = p.Size
	return math.abs(r.RightVector.X) * sx.X / 2 + math.abs(r.UpVector.X) * sx.Y / 2 + math.abs(-r.LookVector.X) * sx.Z / 2
end

-- light positions (chassis space) for a set of lamp parts: one per side, even if one mesh holds both lamps
local function lampSpots(ch, parts)
	local l, r = nil, nil
	for _, p in parts do
		local pos = ch.CFrame:PointToObjectSpace(p.Position)
		local hx = halfX(ch, p)
		local spots = math.abs(pos.X) < 0.6 and hx > 1 and { pos - Vector3.new(hx - 0.35, 0, 0), pos + Vector3.new(hx - 0.35, 0, 0) } or { pos }
		for _, q in spots do
			if q.X < 0 then
				l = l and (math.abs(q.X) > math.abs(l.X) and q or l) or q
			else
				r = r and (q.X > r.X and q or r) or q
			end
		end
	end
	local out = {}
	if l then
		table.insert(out, l)
	end
	if r then
		table.insert(out, r)
	end
	return out
end

local function attach(ch, name, pos, tilt)
	local a = Instance.new("Attachment")
	a.Name = name
	a.CFrame = CFrame.new(pos) * (tilt or CFrame.identity)
	a.Parent = ch
	return a
end

local function light(class, parent, color, range, bright)
	local l = Instance.new(class)
	l.Color = color
	l.Range = range
	l.Brightness = 0
	l.Shadows = false
	l.Parent = parent
	l:SetAttribute("Max", bright)
	return l
end

local function collectLamps(car)
	local heads, tails, red, blue = {}, {}, {}, {}
	for _, p in car:GetDescendants() do
		if p:IsA("BasePart") and p:GetAttribute("Role") then
			local mat = Kit.MatOf(car, p:GetAttribute("Role"))
			if mat == "Headlight" or mat == "Head" then
				table.insert(heads, p)
			elseif mat == "Taillight" or mat == "Tail" then
				table.insert(tails, p)
			elseif mat == "PoliceRed" then
				table.insert(red, p)
			elseif mat == "PoliceBlue" then
				table.insert(blue, p)
			end
		end
	end
	return heads, tails, red, blue
end

local function teardownLamps(r)
	for _, inst in r.made or {} do
		inst:Destroy()
	end
	r.made = {}
end

local function rigLamps(car, r)
	local ch = car.PrimaryPart
	teardownLamps(r)
	local heads, tails, red, blue = collectLamps(car)
	r.heads, r.tails, r.red, r.blue = heads, tails, red, blue
	r.base = {}
	for _, p in heads do
		r.base[p] = { p.Color, p.Material }
	end
	for _, p in tails do
		r.base[p] = { p.Color, p.Material }
	end
	r.beams, r.tailL, r.revL, r.sigF, r.sigR, r.bar = {}, {}, {}, {}, {}, {}
	for i, pos in lampSpots(ch, heads) do
		local a = attach(ch, "Beam" .. i, pos + Vector3.new(0, 0, -0.2), CFrame.Angles(-math.rad(7), 0, 0))
		table.insert(r.made, a)
		local sp = light("SpotLight", a, Color3.fromRGB(255, 244, 222), 50, 4)
		sp.Face = Enum.NormalId.Front
		sp.Angle = 70
		table.insert(r.beams, sp)
		table.insert(r.sigF, light("PointLight", a, AMBER, 7, 2.5))
	end
	for i, pos in lampSpots(ch, tails) do
		local a = attach(ch, "Tail" .. i, pos + Vector3.new(0, 0, 0.25))
		table.insert(r.made, a)
		table.insert(r.tailL, light("PointLight", a, Color3.fromRGB(255, 20, 20), 9, 2.2))
		table.insert(r.revL, light("PointLight", a, Color3.fromRGB(240, 240, 255), 12, 1.6))
		table.insert(r.sigR, light("PointLight", a, AMBER, 7, 2.5))
	end
	for _, list in { red, blue } do
		for _, p in list do
			local l = light("PointLight", p, list == red and Color3.fromRGB(255, 30, 40) or Color3.fromRGB(40, 90, 255), 26, 4)
			table.insert(r.made, l)
			table.insert(r.bar, { p, l, list == red, p.Color })
		end
	end
	r.lampKey = car:GetAttribute("Look")
	r.lampState = nil
	r.lampCount = #heads + #tails
end

local function rig(car, s)
	local r = rigs[car]
	if r then
		return r
	end
	local ch = car.PrimaryPart
	if not ch then
		return nil
	end
	local v = Vehicles.Get(Vehicles.Of(car))
	r = { made = {}, rpm = 0.15, gear = 1, prevThrottle = 0, nextPop = 0, blinkT = 0, sirenT = 0 }
	r.engine = v.engine or ENGINE_BY_ID[v.id] or (v.bike and "single") or ENGINE_OF[v.class] or "v8"
	r.horn = makeSound(ch, HORN_OF[v.class] or "horn_car", true, 0, 14, 300)
	if r.engine == "electric" or r.engine == "ev" then
		r.loops = { makeSound(ch, r.engine == "ev" and "engine_ev" or "engine_electric", true, 0, 8, 140) }
	else
		r.loops = {}
		for i, tag in { "low", "mid", "high" } do
			r.loops[i] = makeSound(ch, ("engine_%s_%s"):format(r.engine, tag), true, 0, 14, 320)
		end
	end
	r.squeal = makeSound(ch, "tyre_squeal", true, 0, 12, 240)
	r.scrub = makeSound(ch, "tyre_scrub", true, 0, 10, 200)
	r.siren = { makeSound(ch, "siren_wail", true, 0, 30, 600), makeSound(ch, "siren_yelp", true, 0, 30, 600) }
	r.pump = makeSound(ch, "hyd_pump", true, 0, 10, 160)
	r.ch = ch
	-- exhaust pop flash
	local rb = s and s.REST and s.REST.RL
	local back = attach(ch, "ExhaustFlash", Vector3.new(rb and rb.X * 0.4 or 0, rb and rb.Y - 0.2 or 1, (rb and rb.Z or 6) + 2.4))
	r.popLight = light("PointLight", back, Color3.fromRGB(255, 140, 40), 10, 5)
	table.insert(r.made, back)
	rigLamps(car, r)
	-- start-up / shut-down as someone takes or leaves the driver's seat
	local ds = car:FindFirstChild("DriveSeat")
	if ds then
		r.occupied = ds.Occupant ~= nil
		ds:GetPropertyChangedSignal("Occupant"):Connect(function()
			local occ = ds.Occupant ~= nil
			if occ == r.occupied then
				return
			end
			r.occupied = occ
			local cam = workspace.CurrentCamera
			if cam and (cam.CFrame.Position - ch.Position).Magnitude < 260 then
				oneShot(ch, occ and "engine_start" or "engine_off", 0.7)
			end
			r.startT = occ and os.clock() or nil
		end)
	end
	rigs[car] = r
	car.Destroying:Once(function()
		rigs[car] = nil
	end)
	return r
end

---------------------------------------------------------------------------------------------------- engine
local function rpmFrom(r, speedFrac, throttle, burnout, dt)
	local target
	if burnout then
		target = 0.88 + 0.06 * math.sin(os.clock() * 13)
	elseif speedFrac < 0.02 then
		target = throttle > 0.05 and 0.45 or 0.12 -- revving on the spot / idle
	else
		local g = 1
		while g < #GEAR_TOP and speedFrac > GEAR_TOP[g] do
			g += 1
		end
		if g ~= r.gear then
			if g > r.gear and throttle > 0.6 and r.rpm > 0.75 then
				r.shiftPop = true
			end
			r.gear = g
		end
		local lo = g == 1 and 0 or GEAR_TOP[g - 1]
		local within = (speedFrac - lo) / (GEAR_TOP[g] - lo)
		target = (g == 1 and 0.2 or 0.42) + (g == 1 and 0.75 or 0.55) * within
		target = target * (0.9 + 0.1 * throttle)
	end
	local rate = target > r.rpm and 3.5 or 2.2
	r.rpm += (target - r.rpm) * math.min(1, dt * rate)
	return r.rpm
end

local function engine(car, r, info, dt)
	local ds = car:FindFirstChild("DriveSeat")
	local running = (ds and ds.Occupant ~= nil) or car:GetAttribute("EngineOn") == true
	r.running = running
	local throttle = math.clamp(info.throttle or 0, 0, 1)
	local speedFrac = math.clamp(math.abs(info.fwd or 0) / math.max(info.top or 70, 1), 0, 1.2)
	local rpm = rpmFrom(r, speedFrac, throttle, info.burnout, dt)
	local starting = r.startT and os.clock() - r.startT < 1.0 and running
	local vol = (running and not starting) and (0.45 + 0.4 * throttle) or 0
	if r.engine == "electric" or r.engine == "ev" then
		local s = r.loops[1]
		if s then
			s.PlaybackSpeed = 0.5 + 1.6 * speedFrac
		end
		loopTo(s, running and (0.15 + 0.45 * speedFrac) or 0, running, dt)
	else
		local sr = SAMPLE_RPM[r.engine]
		local idle, red = sr[1], sr[3] * 1.12
		local actual = idle + (red - idle) * math.clamp((rpm - 0.12) / 0.88, 0, 1)
		local w = { 0, 0, 0 }
		if actual <= sr[2] then
			local k = math.clamp((actual - sr[1]) / (sr[2] - sr[1]), 0, 1)
			w[1], w[2] = math.cos(k * math.pi / 2), math.sin(k * math.pi / 2)
		else
			local k = math.clamp((actual - sr[2]) / (sr[3] - sr[2]), 0, 1)
			w[2], w[3] = math.cos(k * math.pi / 2), math.sin(k * math.pi / 2)
		end
		for i, s in r.loops do
			if s then
				s.PlaybackSpeed = math.clamp(actual / sr[i], 0.5, 2)
			end
			loopTo(s, vol * w[i], running, dt, 12)
		end
	end
	-- exhaust pops: lifting off the gas high in the revs, or a hard upshift
	local lift = r.prevThrottle > 0.7 and throttle < 0.1 and rpm > 0.65
	r.prevThrottle = throttle
	local now = os.clock()
	if running and r.engine ~= "electric" and r.engine ~= "ev" and (lift or r.shiftPop) and now > r.nextPop then
		r.shiftPop = false
		r.nextPop = now + 0.12
		local pops = lift and math.random(1, 3) or 1
		for i = 1, pops do
			task.delay((i - 1) * (0.07 + math.random() * 0.08), function()
				if r.ch.Parent then
					oneShot(r.ch, "backfire_" .. math.random(1, 3), 0.55, 0.9 + math.random() * 0.25)
					r.popLight.Brightness = r.popLight:GetAttribute("Max")
					task.delay(0.05, function()
						r.popLight.Brightness = 0
					end)
				end
			end)
		end
	end
	r.shiftPop = false
end

---------------------------------------------------------------------------------------------------- lights
local function setLamp(p, base, lit, color)
	if lit then
		p.Material = Enum.Material.Neon
		p.Color = color or base[1]
	else
		p.Material = Enum.Material.Glass
		p.Color = (color or base[1]):Lerp(Color3.new(0, 0, 0), 0.45)
	end
end

local function lights(car, r, info, dt)
	if car:GetAttribute("Look") ~= r.lampKey then
		-- the look changed (shop): lamps may be different parts now
		r.lampKey = car:GetAttribute("Look")
		task.defer(function()
			if car.Parent then
				rigLamps(car, r)
			end
		end)
		return
	end
	local mode = car:GetAttribute("Lights")
	local t = Lighting.ClockTime
	local night = t > 18.3 or t < 6.4
	if mode == nil then
		mode = (night and r.running) and 1 or 0
	end
	local fwd, thr = info.fwd or 0, info.throttle or 0
	local braking = r.running and ((thr < -0.05 and fwd > 1) or info.braking == true)
	local reversing = r.running and fwd < -0.5 and thr < -0.05
	-- indicators blink at 1.5 Hz
	local sig = car:GetAttribute("Signal") or ""
	r.blinkT += dt
	local on = sig ~= "" and (r.blinkT % 0.66) < 0.38
	if sig ~= r.lastSig then
		r.lastSig, r.blinkT = sig, 0
	end
	if on ~= r.blinkOn then
		r.blinkOn = on
		if sig ~= "" and info.inside then
			oneShot(r.ch, on and "indicator_tick" or "indicator_tock", 0.35)
		end
	end
	local left = on and (sig == "L" or sig == "H")
	local right = on and (sig == "R" or sig == "H")
	for i, b in r.beams do
		b.Brightness = mode == 0 and 0 or (mode == 2 and 7 or 4)
		b.Range = mode == 2 and 80 or 50
		b.Angle = mode == 2 and 50 or 70
		local isLeft = b.Parent.CFrame.Position.X < 0
		r.sigF[i].Brightness = ((isLeft and left) or (not isLeft and right)) and r.sigF[i]:GetAttribute("Max") or 0
	end
	for i, l in r.tailL do
		l.Brightness = braking and 2.4 or (mode > 0 and 0.8 or 0)
		r.revL[i].Brightness = reversing and 1.6 or 0
		local isLeft = l.Parent.CFrame.Position.X < 0
		r.sigR[i].Brightness = ((isLeft and left) or (not isLeft and right)) and r.sigR[i]:GetAttribute("Max") or 0
	end
	local key = ("%d%s%s"):format(mode, tostring(braking), tostring(reversing))
	if key ~= r.lampState then
		r.lampState = key
		for _, p in r.heads do
			setLamp(p, r.base[p], mode > 0)
		end
		for _, p in r.tails do
			local base = r.base[p]
			if braking then
				setLamp(p, base, true, Color3.fromRGB(255, 25, 25))
			else
				setLamp(p, base, mode > 0, base[1]:Lerp(Color3.new(0, 0, 0), mode > 0 and 0.25 or 0))
			end
		end
	end
	-- Coast Patrol light bar: red / blue double flash while the siren is on
	local siren = car:GetAttribute("Siren") or 0
	if #r.bar > 0 then
		r.sirenT += dt
		local ph = r.sirenT % 0.8
		local redOn = siren > 0 and (ph < 0.08 or (ph > 0.16 and ph < 0.24))
		local blueOn = siren > 0 and ((ph > 0.4 and ph < 0.48) or (ph > 0.56 and ph < 0.64))
		for _, it in r.bar do
			local p, l, isRed, col = it[1], it[2], it[3], it[4]
			local lit = isRed and redOn or (not isRed and blueOn)
			l.Brightness = lit and l:GetAttribute("Max") or 0
			p.Material = (lit or siren == 0) and Enum.Material.Neon or Enum.Material.Glass
			p.Color = (lit or siren == 0) and col or col:Lerp(Color3.new(0, 0, 0), 0.6)
		end
	end
	for i, s in r.siren do
		loopTo(s, siren == i and 1 or 0, siren == i, dt, 10)
	end
end

---------------------------------------------------------------------------------------------------- per frame
-- info = { fwd = forward speed (studs/s), top = top speed, throttle = -1..1, burnout = bool, braking = bool,
--          slip = 0..1 (hardest-slipping tyre), spin = 0..1 (burnout / wheelspin), hyd = corner speed (studs/s,
--          + up / - down), inside = the local player sits in this car }
function Life.Update(car, s, info, dt)
	local r = rig(car, s)
	if not r then
		return
	end
	engine(car, r, info, dt)
	lights(car, r, info, dt)
	loopTo(r.horn, car:GetAttribute("Horn") and 0.9 or 0, car:GetAttribute("Horn") == true, dt, 30)
	local slip = info.slip or 0
	if r.squeal then
		r.squeal.PlaybackSpeed = 0.92 + 0.2 * slip
	end
	loopTo(r.squeal, slip > 0.3 and (0.2 + 0.6 * slip) or 0, slip > 0.3, dt)
	loopTo(r.scrub, (info.spin or 0) > 0.5 and 0.55 or 0, (info.spin or 0) > 0.5, dt)
	local hyd = info.hyd or 0
	loopTo(r.pump, hyd > 0.4 and 0.6 or 0, hyd > 0.4, dt, 14)
	if hyd < -3 and (not r.lastDump or os.clock() - r.lastDump > 0.6) then
		r.lastDump = os.clock()
		oneShot(r.ch, "hyd_dump", 0.6)
	end
end

-- silence a car that went out of range (lights stay as they are)
function Life.Quiet(car)
	local r = rigs[car]
	if not r then
		return
	end
	for _, s in { r.horn, r.squeal, r.scrub, r.pump, r.siren[1], r.siren[2], table.unpack(r.loops) } do
		if s then
			s.Volume = 0
			s:Stop()
		end
	end
end

-- a parked (anchored) car: make sure its rig exists so the start-up plays when someone gets in; lamps off
function Life.Parked(car, s)
	local r = rig(car, s)
	if r and r.lampState ~= "parked" then
		r.lampState = "parked"
		for _, p in r.heads do
			setLamp(p, r.base[p], false)
		end
		for _, p in r.tails do
			setLamp(p, r.base[p], false)
		end
		for _, list in { r.beams, r.tailL, r.revL, r.sigF, r.sigR } do
			for _, l in list do
				l.Brightness = 0
			end
		end
		Life.Quiet(car)
	end
end

return Life
