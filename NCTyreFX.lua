--!nonstrict
-- NCTyreFX (ModuleScript, ReplicatedStorage): tyre smoke, skid marks and tyre squeal for every vehicle on the
-- customization system. LowriderClient calls FX.Update every frame for each nearby Kit car with how hard each
-- tyre is slipping (0..1): its own car from the driving model (NCVehicleSim's s.slip), everyone else's from the
-- SlipF / SlipR attributes the server copies from the driver.
--   smoke   a ParticleEmitter per tyre at the contact patch (rate follows the slip)
--   marks   a Trail per tyre between two attachments either side of the contact patch, laid flat on the road
--   squeal  one looped Sound per car (Config.Sounds.Skid; silent until a sound id is set there)
local RS = game:GetService("ReplicatedStorage")
local Config = require(RS:WaitForChild("NCLowriderConfig"))

local FX = {}
local CORNERS = { "FL", "FR", "RL", "RR" }
local SMOKE_TEX = "rbxasset://textures/particles/smoke_main.dds"
local HALF_TREAD = 0.42 -- half the tyre's tread width (studs), for the skid mark ribbon

local rigs = setmetatable({}, { __mode = "k" }) -- [car] = { [corner] = { at, a, b, smoke, trail }, sound = Sound }

local function rig(car, s)
	local r = rigs[car]
	if r then
		return r
	end
	local ch = car.PrimaryPart
	if not ch or not ch:FindFirstChild("Origin") then
		return nil
	end
	r = {}
	for _, c in CORNERS do
		if s.bike and c:sub(2) == "R" then
			continue -- one tyre per axle on a bike
		end
		local at = Instance.new("Attachment")
		at.Name = "Tyre_" .. c
		at.Parent = ch
		local a = Instance.new("Attachment")
		a.Name = "SkidA_" .. c
		a.Parent = ch
		local b = Instance.new("Attachment")
		b.Name = "SkidB_" .. c
		b.Parent = ch

		local pe = Instance.new("ParticleEmitter")
		pe.Name = "TyreSmoke"
		pe.Texture = SMOKE_TEX
		pe.Color = ColorSequence.new(Color3.fromRGB(235, 235, 238), Color3.fromRGB(200, 200, 205))
		pe.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1.2), NumberSequenceKeypoint.new(0.4, 4.5), NumberSequenceKeypoint.new(1, 8) })
		pe.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.55), NumberSequenceKeypoint.new(0.3, 0.45), NumberSequenceKeypoint.new(1, 1) })
		pe.Lifetime = NumberRange.new(1.6, 2.8)
		pe.Speed = NumberRange.new(1.5, 4)
		pe.SpreadAngle = Vector2.new(50, 50)
		pe.EmissionDirection = Enum.NormalId.Top
		pe.Acceleration = Vector3.new(0, 1.6, 0)
		pe.Drag = 1.2
		pe.Rotation = NumberRange.new(0, 360)
		pe.RotSpeed = NumberRange.new(-35, 35)
		pe.LightInfluence = 1
		pe.Rate = 0
		pe.Parent = at

		local tr = Instance.new("Trail")
		tr.Name = "SkidMark"
		tr.Attachment0, tr.Attachment1 = a, b
		tr.Color = ColorSequence.new(Color3.fromRGB(18, 18, 20))
		tr.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.35), NumberSequenceKeypoint.new(0.75, 0.45), NumberSequenceKeypoint.new(1, 1) })
		tr.Lifetime = 9
		tr.MinLength = 0.15
		tr.FaceCamera = false
		tr.LightInfluence = 1
		tr.Enabled = false
		tr.Parent = ch
		r[c] = { at = at, a = a, b = b, smoke = pe, trail = tr }
	end
	local id = Config.Sounds and Config.Sounds.Skid or ""
	if id ~= "" then
		local snd = Instance.new("Sound")
		snd.Name = "TyreSqueal"
		snd.SoundId = id
		snd.Looped = true
		snd.Volume = 0
		snd.RollOffMaxDistance = 220
		snd.Parent = ch
		r.sound = snd
	end
	rigs[car] = r
	return r
end

-- slip = { FL = 0..1, ... }; s = the car's NCVehicleSim state (rest positions, wheel radius, suspension travel)
function FX.Update(car, s, slip, dt)
	local r = rig(car, s)
	if not r then
		return
	end
	local ch = car.PrimaryPart
	local o = ch.Origin.CFrame
	local loud = 0
	for _, c in CORNERS do
		local t = r[c]
		if t then
			local rest = s.REST[c]
			local d = s.vis and s.vis[c] or 0
			local grounded = s.ground == nil or s.ground[c] ~= false
			local k = grounded and (slip[c] or 0) or 0
			-- the contact patch moves with the suspension
			local foot = Vector3.new(rest.X, rest.Y - d - s.R + 0.06, rest.Z)
			t.at.CFrame = o * CFrame.new(foot)
			t.a.CFrame = o * CFrame.new(foot + Vector3.new(-HALF_TREAD, -0.03, 0))
			t.b.CFrame = o * CFrame.new(foot + Vector3.new(HALF_TREAD, -0.03, 0))
			t.smoke.Rate = k > 0.15 and 12 + 70 * k or 0
			t.trail.Enabled = k > 0.35
			loud = math.max(loud, k)
		end
	end
	if r.sound then
		local want = loud > 0.25 and 0.25 + 0.6 * loud or 0
		r.sound.Volume += (want - r.sound.Volume) * math.min(1, dt * 8)
		r.sound.PlaybackSpeed = 0.9 + 0.25 * loud
		if r.sound.Volume > 0.02 and not r.sound.IsPlaying then
			r.sound:Play()
		elseif r.sound.Volume <= 0.02 and r.sound.IsPlaying then
			r.sound:Stop()
		end
	end
end

-- stops everything on a car (it went out of range / got parked)
function FX.Quiet(car)
	local r = rigs[car]
	if not r then
		return
	end
	for _, c in CORNERS do
		local t = r[c]
		if t then
			t.smoke.Rate = 0
			t.trail.Enabled = false
		end
	end
	if r.sound then
		r.sound.Volume = 0
		r.sound:Stop()
	end
end

return FX
