--!nonstrict
-- NCVehicleSim: the raycast-suspension driving model shared by every vehicle on the customization system.
-- LowriderClient runs it for the cars a player simulates; NCVehicleWorld runs it on the server for AI cars
-- (Coast Patrol). See LowriderClient for how the model works.
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")

local Config = require(RS:WaitForChild("NCLowriderConfig"))
local Vehicles = require(RS:WaitForChild("NCVehicles"))

local Sim = {}
local CORNERS = { "FL", "FR", "RL", "RR" }
local RAY_UP = 2.5 -- the ray starts this far above the wheel centre's rest height
Sim.CORNERS = CORNERS

-- every folder that holds Kit cars: Low & Slow rides, the world's parked / personal / garage cars, and Coast Patrol
function Sim.Folders()
	local list = {}
	local lr = workspace:FindFirstChild("Lowriders")
	if lr then
		table.insert(list, lr)
	end
	local nc = workspace:FindFirstChild("NeonCoast")
	if nc then
		for _, n in { "Cars", "Police" } do
			local f = nc:FindFirstChild(n)
			if f then
				table.insert(list, f)
			end
		end
	end
	return list
end

local state = {} -- strong; cleared on Destroying. [car] = { e = {}, target = {}, spin = {}, ... }

function Sim.State(car)
	local s = state[car]
	if not s then
		s = { e = {}, target = {}, spin = {}, vis = {}, ground = {}, landed = {}, steer = 0, mode = "ride", threeWheel = nil, dance = false,
			charge = 0, charging = false, lastSend = 0, hopPeak = nil, frontAirT = 0,
			drift = 0, wspin = {}, slip = {} }
		for _, c in CORNERS do
			s.e[c], s.target[c], s.spin[c], s.vis[c], s.ground[c], s.landed[c] = 0, 0, 0, 0, false, -1
		end
		-- this car's own geometry + driving numbers (every vehicle has its own data module)
		local vid = Vehicles.Of(car)
		local vd = Vehicles.Data(vid) or Vehicles.Data(Vehicles.Default)
		s.R = vd.Car.WheelRadius
		s.REST = {}
		s.bike = vd.Car.Bike == true -- two wheels: FL = front, RL = rear; each spring runs twice on the centre line
		for _, c in CORNERS do
			local p = vd.Car.Wheels[c] or (s.bike and vd.Car.Wheels[c:sub(1, 1) .. "L"])
			s.REST[c] = Vector3.new(p[1], p[2], p[3])
		end
		local fb = vd.Car.FrontBumper or { 0, vd.Car.Wheels.FL[2], vd.Car.Wheels.FL[3] - 3 }
		s.bumper = Vector3.new(fb[1], fb[2], fb[3])
		s.D = Vehicles.Drive(vid, Config.Drive)
		state[car] = s
		car.Destroying:Once(function()
			state[car] = nil
		end)
	end
	return s
end

function Sim.Susp(car)
	return Config.Susp(car:GetAttribute("Susp"))
end

function Sim.RayParams(car)
	local rp = RaycastParams.new()
	local ignore = { car }
	for _, f in Sim.Folders() do
		table.insert(ignore, f) -- other cars: the bodies collide anyway; this keeps wheels off roofs
	end
	for _, p in Players:GetPlayers() do
		if p.Character then
			table.insert(ignore, p.Character)
		end
	end
	rp.FilterDescendantsInstances = ignore
	rp.FilterType = Enum.RaycastFilterType.Exclude
	rp.IgnoreWater = false
	return rp
end

---------------------------------------------------------------------------------------------------- wheels (everyone)
-- casts every corner, poses the wheels; returns per-corner { hit, d, point, normal } in world space
function Sim.Cast(car, s, origin, rp, sp)
	local R, REST, D = s.R, s.REST, s.D
	local up = origin.UpVector
	local out = {}
	local drop = sp.drop
	for _, c in CORNERS do
		local rest = REST[c]
		local start = origin:PointToWorldSpace(Vector3.new(rest.X, rest.Y + RAY_UP, rest.Z))
		local len = RAY_UP + R + math.max(0, s.e[c]) + D.Droop + 0.6
		local hit = workspace:Raycast(start, -up * len, rp)
		local d, grounded = s.e[c] + D.Droop, false
		if hit then
			local h = (hit.Position - start):Dot(-up)
			local dd = h - RAY_UP - R
			if dd <= s.e[c] + D.Droop then
				d, grounded = math.max(dd, -drop - D.BumpStop), true
			end
		end
		out[c] = { hit = hit, d = d, grounded = grounded, start = start }
	end
	return out
end

function Sim.Pose(car, s, origin, casts, steerAngle, fwdSpeed, dt)
	local R, REST = s.R, s.REST
	local ch = car.PrimaryPart
	for _, c in CORNERS do
		local w = car:FindFirstChild("W_" .. c)
		local hub = w and w.PrimaryPart
		local weld = hub and hub:FindFirstChild("WheelWeld")
		if weld then
			local rest = REST[c]
			local cast = casts[c]
			-- ease the visual so a missed ray doesn't snap
			s.vis[c] = s.vis[c] + (cast.d - s.vis[c]) * math.min(1, dt * 30)
			local rate = (s.wspin and s.wspin[c]) or fwdSpeed / R -- burnouts spin the wheels faster than the road, the handbrake locks them
			s.spin[c] = (s.spin[c] + rate * dt) % (math.pi * 2)
			local isRight = rest.X > 0
			local steer = rest.Z < 0 and steerAngle or 0
			local local_ = ch.Origin.CFrame * CFrame.new(rest.X, rest.Y - s.vis[c], rest.Z) * CFrame.Angles(0, -steer, 0)
				* (isRight and CFrame.Angles(0, math.pi, 0) or CFrame.identity) * CFrame.Angles((isRight and 1 or -1) * s.spin[c], 0, 0)
			weld.C0 = local_
		end
	end
end

---------------------------------------------------------------------------------------------------- physics (the car I simulate)
function Sim.Step(car, s, dt, input, noPose)
	local REST, D = s.REST, s.D
	local ch = car.PrimaryPart
	local drive, turn = ch:FindFirstChild("Drive"), ch:FindFirstChild("Turn")
	if not (drive and turn) then
		return
	end
	local sp = Sim.Susp(car)
	local origin = ch.CFrame * ch.Origin.CFrame
	local up, fwd, right = origin.UpVector, origin.LookVector, origin.RightVector
	local mass = ch.AssemblyMass
	local g = workspace.Gravity
	local k = mass * g / 4 / D.SpringSag
	local cdamp = 2 * D.Damping * math.sqrt(k * mass / 4)
	local com = ch.AssemblyCenterOfMass
	local vel = ch.AssemblyLinearVelocity
	local fwdSpeed = vel:Dot(fwd)
	local rp = Sim.RayParams(car)

	-- hydraulics: move each corner toward its target
	for _, c in CORNERS do
		local t = math.clamp(s.target[c], -sp.drop, sp.lift)
		local rate = sp.speed > 0 and sp.speed * (t < s.e[c] and 1.8 or 1) or 4
		local diff = t - s.e[c]
		s.e[c] = s.e[c] + math.clamp(diff, -rate * dt, rate * dt)
		if sp.kit == "none" then
			s.e[c] = 0
		end
	end

	local eng = Config.Engine(car:GetAttribute("Engine"))
	local topSpeed, accel = D.TopSpeed * eng.speed, D.Accel * eng.accel
	local speedFrac = math.clamp(math.abs(fwdSpeed) / topSpeed, 0, 1)

	local casts = Sim.Cast(car, s, origin, rp, sp)
	local F, T = Vector3.zero, Vector3.zero
	local grounded = 0
	for _, c in CORNERS do
		if casts[c].grounded then
			grounded += 1
		end
	end

	-- tricks. gas / brake are the raw pedals (both at once = burnout); handbrake locks the rear wheels.
	--   burnout       gas + brake from a stop: the fronts hold, the rears spin and smoke
	--   donut         burnout + steer: the rear swings round the front wheels (spinning burnout)
	--   drift         tap the handbrake into a turn: the rear lets go, and staying on the gas keeps it sliding;
	--                 steer into it for a drifting donut, counter-steer to hold the angle, lift off to catch it
	local gas = input.gas or math.max(input.throttle, 0)
	local brk = input.brake or math.max(-input.throttle, 0)
	local hb = input.handbrake == true
	local absV = math.abs(fwdSpeed)
	local burnout = gas > 0.5 and brk > 0.5 and absV < 14 and grounded >= 2 and not input.park
	local donut = burnout and math.abs(input.steer) > 0.2 and not s.bike
	local rearZ = s.REST.RL.Z
	local vr = ch:GetVelocityAtPosition(origin:PointToWorldSpace(Vector3.new(0, 0, rearZ)))
	local slipAngle = math.atan2(math.abs(vr:Dot(right)), math.max(math.abs(vr:Dot(fwd)), 1))
	local driftWant = 0
	if (hb and absV > 10) or (s.drift > 0.15 and gas > 0.4 and slipAngle > 0.07 and absV > 8) then
		driftWant = 1
	end
	if s.bike or grounded < 2 then
		driftWant = 0
	end
	s.drift += (driftWant - s.drift) * math.min(1, dt * (driftWant > s.drift and 4 or 1.6))
	s.burnout, s.donut, s.handbrake = burnout, donut, hb
	local rearMul = 1 - 0.55 * s.drift -- rear grip left while sliding
	if hb then
		rearMul = math.min(rearMul, 0.3)
	end
	if donut then
		rearMul = 0.12
	end

	-- steering eases in; less lock at speed (full lock back while drifting, for counter-steer)
	local maxSteer = math.rad(D.SteerMax + (D.SteerFast - D.SteerMax) * speedFrac * (1 - s.drift))
	s.steer = s.steer + (input.steer * maxSteer - s.steer) * math.min(1, dt * 8)
	s.wspin = s.wspin or {}
	s.slip = s.slip or {}
	for _, c in CORNERS do
		local cast = casts[c]
		local rest = REST[c]
		local disabled = s.threeWheel == c
		s.slip[c] = 0
		s.wspin[c] = nil
		if cast.grounded and not disabled then
			local contact = cast.hit.Position
			local attach = origin:PointToWorldSpace(Vector3.new(rest.X, rest.Y, rest.Z))
			local pv = ch:GetVelocityAtPosition(attach)
			local x = (s.e[c] + D.SpringSag) - cast.d
			local spring = k * x - cdamp * pv:Dot(up)
			if cast.d <= -sp.drop - D.BumpStop + 0.02 then
				spring += k * 4 * (-sp.drop - D.BumpStop + 0.02 - cast.d) + cdamp * math.max(0, -pv:Dot(up))
			end
			spring = math.clamp(spring, 0, mass * g * 4)
			local N = spring
			local f = up * spring
			-- tyre: the wheel's own forward / side directions on the ground
			local isFront = rest.Z < 0
			local steer = isFront and s.steer or 0
			local wf = (CFrame.fromAxisAngle(up, -steer) * fwd)
			local wr = wf:Cross(up)
			local cv = ch:GetVelocityAtPosition(contact)
			local vLat = cv:Dot(wr)
			local vLong = cv:Dot(wf)
			local share = mass / math.max(grounded, 1)
			local mul = isFront and 1 or rearMul
			local grip = (isFront and D.Grip or D.RearGrip) * share * mul
			local mu = 1.15 * N
			local muLat = mu * (0.4 + 0.6 * mul)
			local lat = math.clamp(-vLat * grip, -muLat, muLat)
			local long = 0
			local R = s.R
			local spinSlip = 0
			if burnout then
				if isFront then
					long = donut and 0 or -vLong * share * 10 -- straight: the front brakes hold it; donut: they roll round
				else
					long = donut and mass * accel * 0.35 / 2 or 0
					s.wspin[c] = 48
					spinSlip = 1
				end
			elseif hb and not isFront then
				long = -math.sign(vLong) * math.min(math.abs(vLong) * share * 4, mu * 0.7) -- locked: sliding
				s.wspin[c] = 0
				spinSlip = math.clamp((math.abs(vLong) - 3) / 20, 0, 1)
			elseif input.throttle > 0.05 then
				if not isFront and fwdSpeed < topSpeed then
					long = mass * accel * input.throttle / 2
				end
				if fwdSpeed < -1 then
					long += mass * D.Brake * 0.25
				end
			elseif input.throttle < -0.05 then
				if fwdSpeed > 1 then
					long = -mass * D.Brake * 0.25 * -input.throttle
				elseif not isFront and fwdSpeed > -D.ReverseSpeed then
					long = mass * accel * 0.6 * input.throttle / 2
				end
			elseif input.park then
				long = -vLong * share * 10 -- parked: hold it still (clamped by grip below)
			elseif absV < 3 then
				-- no pedals, nearly stopped: the tyres hold it, like park. (A rolling-resistance-only coast let the
				-- spring force's sideways share on a slight pitch push a seated car along at about 0.4 studs/s.)
				long = -vLong * share * 10
			else
				long = -math.sign(vLong) * math.min(math.abs(vLong) * share * 2, mass * D.Coast / 4)
			end
			if not isFront and s.drift > 0.3 and gas > 0.3 and not hb then
				s.wspin[c] = vLong / R + 22 * gas * s.drift -- spinning up on the gas through the slide
				spinSlip = 0.5 * s.drift
			end
			long = math.clamp(long, -mu, mu)
			f += wr * lat + wf * long
			s.slip[c] = math.clamp(math.max((math.abs(vLat) - 5) / 12, spinSlip), 0, 1)
			F += f
			T += (contact - com):Cross(f)
		end
	end

	-- standstill hold: no pedals and nearly stopped, so the tyres grip the road where the car stopped. Damping alone
	-- only balances a constant push (the springs' share along a slightly pitched body), so it crept; this latches
	-- the stop point and pulls back to it, sideways too, capped by what the tyres can hold. Re-latches if shoved.
	local idle = grounded >= 2 and not burnout and not hb and math.abs(input.throttle) <= 0.05 and gas <= 0.05 and brk <= 0.05
	local vh = vel - up * vel:Dot(up)
	if idle and (s.latch or vh.Magnitude < 1.5) and vh.Magnitude < 3 then
		local here = ch.Position
		if not s.latch or (here - s.latch).Magnitude > 1.5 then
			s.latch = here
		end
		local off = here - s.latch
		off -= up * off:Dot(up)
		local hold = -off * mass * 30 - vh * mass * 9
		local cap = mass * g * 0.9
		if hold.Magnitude > cap then
			hold = hold.Unit * cap
		end
		F += hold
		T += -up * ch.AssemblyAngularVelocity:Dot(up) * mass * 80 -- and it doesn't slowly turn on the spot
	else
		s.latch = nil
	end

	-- three-wheel: hold the lifted corner up with a torque about the diagonal the car balances on
	if s.threeWheel and grounded >= 2 then
		local c = s.threeWheel
		local diag = { FL = { "FR", "RL" }, FR = { "FL", "RR" } }
		local a, b = diag[c][1], diag[c][2]
		local pa = origin:PointToWorldSpace(Vector3.new(REST[a].X, 0, REST[a].Z))
		local pb = origin:PointToWorldSpace(Vector3.new(REST[b].X, 0, REST[b].Z))
		local pc = origin:PointToWorldSpace(Vector3.new(REST[c].X, 0, REST[c].Z))
		local axis = (pb - pa).Unit
		if axis:Cross(pc - pa).Y < 0 then
			axis = -axis
		end
		local ground = casts[a].hit and casts[a].hit.Position.Y or pa.Y
		local height = pc.Y - ground -- the lifted corner's underside above the road
		local target = 2.4
		local w = ch.AssemblyAngularVelocity:Dot(axis)
		local inertia = mass * 10
		local torque = inertia * (10 * (target - height) - 8 * w)
		T += axis * math.clamp(torque, -inertia * 60, inertia * 60)
	end

	-- bikes: stay upright and lean into turns. The target "up" is gravity plus the turn's centripetal pull, so the
	-- bike leans exactly as far as the corner needs; Space holds a wheelie
	if s.bike then
		local wv = ch.AssemblyAngularVelocity
		local yaw = wv:Dot(Vector3.yAxis)
		local flatFwd = Vector3.new(fwd.X, 0, fwd.Z)
		flatFwd = flatFwd.Magnitude > 0.01 and flatFwd.Unit or fwd
		local flatRight = flatFwd:Cross(Vector3.yAxis)
		local lean = math.clamp(-yaw * fwdSpeed / g, -0.75, 0.75) -- tan of the lean angle
		local want = (Vector3.yAxis + flatRight * lean).Unit
		local rollErr = up:Cross(want):Dot(fwd)
		local inertia = mass * 3
		T += fwd * math.clamp(inertia * (40 * rollErr - 9 * wv:Dot(fwd)), -inertia * 80, inertia * 80)
		if grounded >= 2 and math.abs(input.steer) < 0.05 then
			T += Vector3.yAxis * (-yaw * mass * 3)
		end
		if s.wheelie and casts.RL.grounded and fwdSpeed > 4 then
			local pitch = math.asin(math.clamp(fwd.Y, -1, 1)) -- nose up = positive
			local target = math.rad(22)
			T += right * math.clamp(inertia * (14 * (target - pitch) - 5 * wv:Dot(right)), -inertia * 30, inertia * 30)
		end
	end

	-- a little yaw damping so it doesn't spin out at a standstill
	local yawRate = ch.AssemblyAngularVelocity:Dot(up)
	if grounded >= 3 and math.abs(input.steer) < 0.05 and s.drift < 0.3 then
		T += up * (-yawRate * mass * 4)
	end
	-- drifting: past ~20 degrees of slide the yaw is damped, so a held drift doesn't snap round into a spin
	if s.drift > 0 and not donut then
		T += up * (-yawRate * mass * 14 * s.drift * math.max(0, slipAngle - 0.35) / 0.35)
	end
	-- donut: swing the tail round at a steady rate (steer > 0 = clockwise from above)
	if donut and grounded >= 3 then
		local want = -input.steer * 2.6
		T += up * math.clamp(mass * 90 * (want - yawRate), -mass * 320, mass * 320)
	end

	drive.Force = F
	turn.Torque = T

	-- for the wheels + hop meter
	s.casts, s.fwdSpeed, s.grounded = casts, fwdSpeed, grounded
	for _, c in CORNERS do
		local was = s.ground[c]
		s.ground[c] = casts[c].grounded
		if s.ground[c] and not was then
			s.landed[c] = os.clock()
		end
	end
	if not noPose then
		Sim.Pose(car, s, origin, casts, s.steer, fwdSpeed, dt)
	end

end

return Sim
