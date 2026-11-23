--!nonstrict
-- NCAnimPlayer (ModuleScript in ReplicatedStorage): plays the Blender-made movement animations (NCAnimations, from
-- build_anims.py / NeonCoast_Animations.blend) straight onto the body joints, on every screen, for every player.
-- No uploads: the clips are data, sampled and blended here and written to Motor6D.Transform by MovementClient.
--   locomotion(): idle -> walk -> jog -> sprint blended by speed, all on one shared step cycle that advances at
--   speed / stride, so the planted foot moves with the ground at any speed (no skating); out of breath, the idle
--   bends over into hands-on-knees; in the air it crossfades through the jump into the falling loop.
--   blendInto(): any clip (loops wrap, one-shots clamp) at a point in time, mixed into a pose with a weight.
local RS = game:GetService("ReplicatedStorage")

local P = { ok = false }
local clips = {}

local function build(data)
	for name, c in data.clips do
		local frames = table.create(c.n)
		for i = 1, c.n do
			local f = {}
			local k, pk = (i - 1) * 4, (i - 1) * 3
			for jn, q in c.q do
				if jn == "Root" then
					f[jn] = CFrame.new(c.p[pk + 1], c.p[pk + 2], c.p[pk + 3], q[k + 1], q[k + 2], q[k + 3], q[k + 4])
				else
					f[jn] = CFrame.new(0, 0, 0, q[k + 1], q[k + 2], q[k + 3], q[k + 4])
				end
			end
			frames[i] = f
		end
		clips[name] = { dur = c.dur, loop = c.loop, n = c.n, frames = frames, speed = c.speed, stride = c.stride,
			blendIn = c.blendIn or 0.1, blendOut = c.blendOut or 0.15 }
	end
end

function P.init()
	local mod = RS:FindFirstChild("NCAnimations") or RS:WaitForChild("NCAnimations", 8)
	if not mod then
		return false
	end
	local ok, data = pcall(require, mod)
	if ok and type(data) == "table" and data.clips then
		build(data)
		P.ok = clips.Idle ~= nil and clips.Walk ~= nil and clips.Jog ~= nil and clips.Sprint ~= nil
	end
	return P.ok
end

function P.has(name)
	return clips[name] ~= nil
end
function P.clip(name)
	return clips[name]
end

-- the clip's pose at u (0..1; loops wrap, one-shots clamp), mixed into out with weight w
function P.blendInto(out, name, u, w)
	local c = clips[name]
	if not c or w <= 0 then
		return out
	end
	local fa, fb, t
	if c.loop then
		local x = (u % 1) * c.n
		local a = math.floor(x)
		t = x - a
		fa, fb = c.frames[a + 1], c.frames[(a + 1) % c.n + 1]
	else
		local x = math.clamp(u, 0, 1) * (c.n - 1)
		local a = math.min(math.floor(x), c.n - 2)
		t = x - a
		fa, fb = c.frames[a + 1], c.frames[a + 2]
	end
	for jn, cfa in fa do
		local cf = cfa:Lerp(fb[jn], t)
		if w >= 1 then
			out[jn] = cf
		else
			out[jn] = (out[jn] or CFrame.identity):Lerp(cf, w)
		end
	end
	return out
end

local function mix(out, pose, w)
	if w <= 0 then
		return
	end
	for jn, cf in pose do
		out[jn] = w >= 1 and cf or (out[jn] or CFrame.identity):Lerp(cf, w)
	end
end

-- cs: the per-character state table (phase, idle clock, air and tired weights live in it)
function P.locomotion(cs, speed, grounded, dt, now, tired)
	local out = {}
	local walk, jog, sprint = clips.Walk, clips.Jog, clips.Sprint
	cs.idleT = (cs.idleT or 0) + dt
	cs.tiredW = (cs.tiredW or 0) + ((tired and 1 or 0) - (cs.tiredW or 0)) * math.min(1, dt * 1.5)
	P.blendInto(out, "Idle", cs.idleT / clips.Idle.dur, 1)
	if cs.tiredW > 0.01 and clips.TiredIdle then
		P.blendInto(out, "TiredIdle", cs.idleT / clips.TiredIdle.dur, cs.tiredW)
	end
	if speed > 0.1 then
		local A, B, w
		if speed <= walk.speed then
			A, B, w = "Walk", "Walk", 0
		elseif speed <= jog.speed then
			A, B, w = "Walk", "Jog", (speed - walk.speed) / (jog.speed - walk.speed)
		else
			A, B, w = "Jog", "Sprint", math.min(1, (speed - jog.speed) / (sprint.speed - jog.speed))
		end
		local stride = clips[A].stride + (clips[B].stride - clips[A].stride) * w
		cs.phase = ((cs.phase or 0) + speed / stride * dt) % 1
		local g = P.blendInto({}, A, cs.phase, 1)
		if w > 0 then
			P.blendInto(g, B, cs.phase, w)
		end
		mix(out, g, math.clamp(speed / 1.5, 0, 1))
	end
	cs.airW = (cs.airW or 0) + ((grounded and 0 or 1) - (cs.airW or 0)) * math.min(1, dt * (grounded and 14 or 8))
	if cs.airW > 0.01 and clips.Fall then
		local a = {}
		local since = cs.takeoffT and (now - cs.takeoffT) or 99
		local jd = clips.JumpUp and clips.JumpUp.dur or 0
		if since < jd then
			P.blendInto(a, "JumpUp", since / jd, 1)
		else
			P.blendInto(a, "Fall", cs.idleT / clips.Fall.dur, 1)
			if clips.JumpUp and since < jd + 0.3 then
				local j = P.blendInto({}, "JumpUp", 1, 1)
				mix(j, a, (since - jd) / 0.3)
				a = j
			end
		end
		mix(out, a, cs.airW)
	end
	return out
end

return P
