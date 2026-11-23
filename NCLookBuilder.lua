--!nonstrict
-- NCLookBuilder (ModuleScript in ReplicatedStorage): puts a Character Studio look on a character.
-- Used by the server (the real character everyone sees) and by the client (the preview mannequin in the studio).
--
-- A look is { [slotId] = { id = itemId, c1 = "#rrggbb", c2 = "#rrggbb" } }; items come from NCLookCatalog.
-- Two things happen:
--   1. Body regions are recoloured: skin on Head / bare arms / bare legs, the top on UpperTorso + arms, bottoms on
--      the hips and legs, shoes on the feet (with Fabric / Leather / Denim-like materials). Works on the Neon Coast
--      human body (one material per R15 MeshPart) and on standard R15 avatars.
--   2. Every item family below builds its 3D pieces (hair, beards, chains, grillz, hats, lapels, hoods, soles ...)
--      out of plain parts, welded to the body part they sit on and sized from the body's own attachments, so the
--      same item fits a 6.6-stud human and a stock Roblox avatar. All pieces are massless, no collision, no query.
--
-- Any item can instead name a real mesh: if the server passes opts.assets[itemId] (an Accessory it loaded with
-- InsertService, e.g. the creator's own Loose Bandana UGC), that accessory is worn and the pieces are skipped.
--
-- Tuning: the face points (eyes, mouth, ears) are fractions of the head radius below (FACE). If something sits a
-- little off on the final body, change the numbers there once; every item follows.
local B = {}

B.FOLDER = "NC_Look"

local V3 = Vector3.new
local rad = math.rad

-- face landmarks in head-radius units, head centre = origin, face toward -Z, up +Y
local FACE = {
	eyeY = 0.02, eyeX = 0.36, eyeZ = -0.97,
	mouthY = -0.64, mouthZ = -0.93,
	earX = 1.0, earY = -0.12, earZ = 0.05, lobeY = -0.36,
	browY = 0.30, chinY = -1.15,
}
B.FACE = FACE

---------------------------------------------------------------------------------------------------- colours
local function hex(h)
	if typeof(h) == "Color3" then
		return h
	end
	if type(h) ~= "string" then
		return Color3.new(1, 0, 1)
	end
	h = h:gsub("#", "")
	local r, g, b = tonumber(h:sub(1, 2), 16), tonumber(h:sub(3, 4), 16), tonumber(h:sub(5, 6), 16)
	if not (r and g and b) then
		return Color3.new(1, 0, 1)
	end
	return Color3.fromRGB(r, g, b)
end
B.hex = hex

local function mix(a, b, t)
	return a:Lerp(b, t)
end

local FIXED = {
	gold = Color3.fromRGB(226, 178, 64), rose = Color3.fromRGB(222, 150, 128), silver = Color3.fromRGB(212, 214, 220),
	black = Color3.fromRGB(22, 22, 24), white = Color3.fromRGB(240, 240, 236), brass = Color3.fromRGB(196, 152, 70),
	gem = Color3.fromRGB(236, 246, 255), pearl = Color3.fromRGB(240, 234, 222), red = Color3.fromRGB(196, 32, 38),
	sole = Color3.fromRGB(236, 232, 224), gum = Color3.fromRGB(160, 110, 62), neon = Color3.fromRGB(0, 255, 220),
	lens = Color3.fromRGB(30, 34, 40), steel = Color3.fromRGB(150, 154, 160), bone = Color3.fromRGB(230, 222, 200),
	tooth = Color3.fromRGB(246, 244, 236),
}

-- the always-on modesty base layer: undershirt on the torso, shorts on the hips and thighs (see Apply).
-- Only the head, arms, hands, lower legs and feet can ever show skin.
B.BASE_LAYER = {
	Torso = Color3.fromRGB(58, 60, 66),
	Hips = Color3.fromRGB(38, 40, 46),
	ULeg = Color3.fromRGB(38, 40, 46),
}

-- materials for colour keys that imply one (metal looks like metal everywhere)
local KEY_MAT = {
	gold = Enum.Material.Metal, rose = Enum.Material.Metal, silver = Enum.Material.Metal, brass = Enum.Material.Metal,
	steel = Enum.Material.Metal, gem = Enum.Material.Glass, pearl = Enum.Material.SmoothPlastic,
	lens = Enum.Material.Glass, neon = Enum.Material.Neon, metal = Enum.Material.Metal, stone = Enum.Material.Glass,
	tooth = Enum.Material.SmoothPlastic,
}
local KEY_REFL = { gold = 0.3, rose = 0.3, silver = 0.35, brass = 0.25, steel = 0.25, metal = 0.3, gem = 0.45, stone = 0.45,
	lens = 0.35, pearl = 0.15 }

---------------------------------------------------------------------------------------------------- piece DSL
-- p(shape, frame, size, offset, rotDeg, colourKey, extra)
--   shape: "Ball" | "Block" | "Cyl" (axis along X, size = length, diameter, diameter) | "Wedge" | "Corner"
--   frame: "head" | "neck" | "chest" | "back" | "hips" | "LWrist" | "RWrist" | "LHand" | "RHand" | "LAnkle" |
--          "RAnkle" | "LFoot" | "RFoot" | "LUpperArm" | "RUpperArm" | "LLowerArm" | "RLowerArm" | "LUpperLeg" | ...
--   size / offset are in the frame's unit (head radius, torso unit, limb thickness); extra.fit = true scales size
--   and offset by the part's own Size instead (for soles, gloves)
--   extra: m (Material), t (transparency), refl, top (hair volume a hat hides), lcf (a local CFrame instead of
--          offset/rot), txt = { text, color, face, font }, spark (iced twinkle), glow
local function p(sh, f, s, o, r, c, x)
	local t = x or {}
	t.sh, t.f, t.s, t.o, t.r, t.c = sh, f, s, o or Vector3.zero, r or Vector3.zero, c
	return t
end
B.p = p

local function mirror(list)
	-- duplicates pieces onto the other side: x flips, L/R frames swap, yaw and roll flip
	local out = {}
	for _, q in ipairs(list) do
		table.insert(out, q)
		local m = table.clone(q)
		m.o = V3(-q.o.X, q.o.Y, q.o.Z)
		m.r = V3(q.r.X, -q.r.Y, -q.r.Z)
		if type(q.f) == "string" then
			local first = q.f:sub(1, 1)
			if first == "L" and q.f:sub(2, 2):match("%u") then
				m.f = "R" .. q.f:sub(2)
			elseif first == "R" and q.f:sub(2, 2):match("%u") then
				m.f = "L" .. q.f:sub(2)
			end
		end
		if q.lcf then
			local pos = q.lcf.Position
			local rx, ry, rz = q.lcf:ToOrientation()
			m.lcf = CFrame.new(-pos.X, pos.Y, pos.Z) * CFrame.fromOrientation(rx, -ry, -rz)
		end
		table.insert(out, m)
	end
	return out
end
B.mirror = mirror

local function add(dst, src)
	for _, q in ipairs(src) do
		table.insert(dst, q)
	end
	return dst
end

-- a vertical cylinder (Roblox cylinders run along X)
local function cylY(f, len, d, o, c, x, tilt)
	return p("Cyl", f, V3(len, d, d), o, V3(tilt or 0, 0, 90), c, x)
end
-- a cylinder facing forward (axis along Z): coins, lenses, watch faces
local function cylZ(f, len, d, o, c, x, rot)
	return p("Cyl", f, V3(len, d, d), o, (rot or Vector3.zero) + V3(0, 90, 0), c, x)
end

-- a ring of n small pieces around a circle (radius rr) in a plane; axis "Y" (horizontal ring) or "Z" / "X"
local function ring(f, centre, rr, n, piece, c, axis, x, sz)
	local out = {}
	for i = 0, n - 1 do
		local a = i / n * math.pi * 2
		local off, lcf
		if axis == "Z" then
			off = V3(math.cos(a) * rr, math.sin(a) * rr, 0)
		elseif axis == "X" then
			off = V3(0, math.sin(a) * rr, math.cos(a) * rr)
		else
			off = V3(math.cos(a) * rr, 0, math.sin(a) * rr)
		end
		local pos = centre + off
		local tangent
		if axis == "Z" then
			tangent = V3(-math.sin(a), math.cos(a), 0)
		elseif axis == "X" then
			tangent = V3(0, math.cos(a), -math.sin(a))
		else
			tangent = V3(-math.sin(a), 0, math.cos(a))
		end
		lcf = CFrame.lookAt(pos, pos + tangent)
		if piece == "Cyl" then -- cylinders run along X: turn them to follow the ring
			lcf = lcf * CFrame.Angles(0, math.rad(90), 0)
		end
		local q = p(piece, f, sz or V3(0.1, 0.1, 0.1), nil, nil, c, x and table.clone(x) or {})
		q.lcf = lcf
		table.insert(out, q)
	end
	return out
end

-- pieces along a path of points (local units); each piece points along the path. style decides the link look.
local function along(f, pts, c, style, w, x)
	local out = {}
	for i = 1, #pts - 1 do
		local a, b = pts[i], pts[i + 1]
		local mid = (a + b) / 2
		local d = b - a
		local len = d.Magnitude
		if len > 1e-4 then
			local cf = CFrame.lookAt(mid, b)
			local q
			if style == "cuban" then
				q = p("Block", f, V3(w * 1.25, w * 0.42, len * 1.08), nil, nil, c, x and table.clone(x) or {})
				q.lcf = cf * CFrame.Angles(0, 0, (i % 2 == 0) and rad(18) or rad(-18))
			elseif style == "rope" then
				q = p("Cyl", f, V3(len * 1.15, w, w), nil, nil, c, x and table.clone(x) or {})
				q.lcf = cf * CFrame.Angles(0, rad(90), 0) * CFrame.Angles((i % 2 == 0) and rad(25) or rad(-25), 0, 0)
			elseif style == "box" then
				q = p("Block", f, V3(w, w, len * 0.92), nil, nil, c, x and table.clone(x) or {})
				q.lcf = cf
			elseif style == "figaro" then
				local long = (i % 4 == 0)
				q = p("Block", f, V3(w * 0.9, w * 0.35, len * (long and 1.1 or 0.8)), nil, nil, c, x and table.clone(x) or {})
				q.lcf = cf
			elseif style == "bead" or style == "tennis" or style == "pearl" then
				q = p("Ball", f, V3(w, w, w), nil, nil, c, x and table.clone(x) or {})
				q.lcf = cf
			elseif style == "puka" then
				q = p("Cyl", f, V3(w * 0.45, w, w), nil, nil, (i % 3 == 0) and "c2" or c, x and table.clone(x) or {})
				q.lcf = cf
			else -- cord / string
				q = p("Cyl", f, V3(len * 1.05, w, w), nil, nil, c, x and table.clone(x) or {})
				q.lcf = cf * CFrame.Angles(0, rad(90), 0)
			end
			table.insert(out, q)
		end
	end
	return out
end

local function bezier(p0, p1, p2, n)
	local pts = {}
	for i = 0, n do
		local t = i / n
		local u = 1 - t
		table.insert(pts, p0 * u * u + p1 * 2 * u * t + p2 * t * t)
	end
	return pts
end

---------------------------------------------------------------------------------------------------- item families
-- each family(p, item) returns pieces, bodyMap. bodyMap keys: Head Torso Hips UArm LArm Hand ULeg LLeg Foot,
-- values are colour keys ("c1", "c2", "skin", "under" = the top's colour) or { c = key, m = Material }.
local F = {}
B.FAMILIES = F

local FAB, LEA, SMO, MET, GLA, NEO, RUB = Enum.Material.Fabric, Enum.Material.Leather, Enum.Material.SmoothPlastic,
	Enum.Material.Metal, Enum.Material.Glass, Enum.Material.Neon, Enum.Material.Rubber

------------------------------------------------------------------ hair (frame "head", unit = head radius)
-- the scalp: a crown shell (hidden under hats) and a back/sides shell (fade colour when faded)
local function cap(th, sideKey, x)
	x = x or {}
	local m = x.m or FAB
	return {
		p("Ball", "head", V3(2 * (1.04 + th), 2 * (0.53 + th), 2 * (1.1 + th)), V3(0, 0.45, 0.14), nil, "c1", { m = m, top = true, refl = x.refl }),
		p("Ball", "head", V3(2 * (0.99 + th * 0.6), 1.7, 2 * (0.86 + th * 0.6)), V3(0, 0.02, 0.3), nil, sideKey or "c1", { m = m, refl = x.refl }),
		-- a low band so a hat never shows bald skin underneath
		p("Ball", "head", V3(2 * (1.0 + th * 0.4), 1.0, 2 * (1.0 + th * 0.4)), V3(0, 0.28, 0.12), nil, sideKey or "c1", { m = m }),
	}
end

local function strands(n, len, d, fromA, toA, y0, c, tips, x)
	-- hanging strands (locs, braids, twists) round the back of the head between two angles (0 = straight back)
	local out = {}
	for i = 0, n - 1 do
		local a = rad(fromA + (toA - fromA) * (n == 1 and 0.5 or i / (n - 1)))
		local px, pz = math.sin(a) * 1.0, math.cos(a) * 0.98 + 0.12
		local l = len * (0.85 + 0.3 * ((i * 37) % 10) / 10) -- slightly uneven like real hair
		local top = V3(px, y0, pz)
		local bot = V3(px * 1.12, y0 - l, pz * 1.12 + 0.12)
		local mid = (top + bot) / 2
		local q = p("Cyl", "head", V3(l, d, d), nil, nil, c, x and table.clone(x) or { m = FAB })
		q.lcf = CFrame.lookAt(mid, bot) * CFrame.Angles(0, rad(90), 0)
		table.insert(out, q)
		if tips then
			table.insert(out, p("Cyl", "head", V3(d * 1.6, d * 1.3, d * 1.3), nil, nil, tips, { m = MET, lcf = CFrame.lookAt(bot, bot + (bot - top)) * CFrame.Angles(0, rad(90), 0) }))
		end
	end
	return out
end

local function rows(n, c, d, x)
	-- cornrows: n raised rows running front to back over the scalp, each in three bent segments
	local out = {}
	for k = 1, n do
		local xx = (k - (n + 1) / 2) * (1.7 / n)
		local yTop = 0.98 * math.sqrt(math.max(0.05, 1 - (xx / 1.08) ^ 2))
		local pts = {}
		for j = 0, 5 do
			local a = rad(-60 + j * 34)
			table.insert(pts, V3(xx, yTop * math.cos(a) * 1.02 + 0.03, math.sin(a) * 1.08 + 0.05))
		end
		add(out, along("head", pts, c, "cord", d, x or { m = FAB }))
	end
	return out
end

F.bald = function()
	return {}
end
F.buzz = function(pp)
	return cap(pp.th or 0.012, pp.fade and "fade" or "c1", { m = FAB })
end
F.crew = function(pp)
	local t = cap(pp.th or 0.05, pp.fade and "fade" or "c1")
	table.insert(t, p("Ball", "head", V3(1.5, 0.35, 0.6), V3(0, 0.62, -0.72), V3(-20, 0, 0), "c1", { m = FAB, top = true }))
	return t
end
F.waves = function(pp)
	-- 360 waves: a close shiny crop, brushed (a faint ripple ring pattern on the crown)
	local t = cap(0.025, pp.fade and "fade" or "c1", { m = SMO, refl = 0.12 })
	for i = 1, 3 do
		add(t, ring("head", V3(0, 0.62 + i * 0.09, 0.12), 0.95 - i * 0.22, 14, "Block", "dark", "Y", { m = SMO, top = true }, V3(0.05, 0.02, 0.2)))
	end
	return t
end
F.fadetop = function(pp)
	-- skin / low / mid / high / taper fades: faded sides with a textured top
	local t = cap(0.02, "fade")
	local vol = pp.vol or 0.25
	table.insert(t, p("Ball", "head", V3(1.92, 0.55 + vol, 2.02), V3(0, 0.78 + vol * 0.3, 0.05), nil, "c1", { m = FAB, top = true }))
	if pp.fringe then
		table.insert(t, p("Ball", "head", V3(1.55, 0.32, 0.55), V3(0, 0.6, -0.82), V3(-25, 0, 0), "c1", { m = FAB, top = true }))
	end
	if pp.part then -- a hard part line shaved in
		table.insert(t, p("Block", "head", V3(0.04, 0.08, 1.4), V3(0.45, 0.9, 0.05), V3(0, 0, -25), "skin", { top = true }))
	end
	return t
end
F.edgar = function()
	-- blunt straight fringe across the forehead over a high skin fade
	local t = cap(0.015, "fade")
	table.insert(t, p("Ball", "head", V3(2.0, 0.7, 2.06), V3(0, 0.72, 0.02), nil, "c1", { m = FAB, top = true }))
	table.insert(t, p("Block", "head", V3(1.62, 0.3, 0.5), V3(0, 0.52, -0.82), V3(-6, 0, 0), "c1", { m = FAB, top = true }))
	return t
end
F.fringe = function(pp)
	-- textured / fluffy forward fringe (perm-friendly) or a French crop
	local t = cap(pp.th or 0.09, pp.fade and "fade" or "c1")
	local n = pp.n or 6
	for i = 1, n do
		local x = (i - (n + 1) / 2) * (1.5 / n)
		table.insert(t, p("Ball", "head", V3(0.42, 0.34, 0.42), V3(x, 0.52 - math.abs(x) * 0.12, -0.86 + math.abs(x) * 0.12), nil, "c1", { m = FAB, top = true }))
	end
	if pp.vol then
		table.insert(t, p("Ball", "head", V3(1.9, 0.55 + pp.vol, 2.0), V3(0, 0.82, 0.05), nil, "c1", { m = FAB, top = true }))
	end
	return t
end
F.curtains = function(pp)
	local t = cap(pp.th or 0.1)
	table.insert(t, mirror({ p("Ball", "head", V3(0.75, 0.55, 0.5), V3(0.42, 0.38, -0.86), V3(0, 0, 20), "c1", { m = FAB, top = true }) })[1])
	table.insert(t, mirror({ p("Ball", "head", V3(0.75, 0.55, 0.5), V3(0.42, 0.38, -0.86), V3(0, 0, 20), "c1", { m = FAB, top = true }) })[2])
	if pp.len then -- longer curtains past the ears
		add(t, mirror({ p("Block", "head", V3(0.3, pp.len, 0.6), V3(0.98, 0.2 - pp.len / 2, -0.25), V3(0, 0, 4), "c1", { m = FAB }) }))
	end
	return t
end
F.pomp = function(pp)
	local t = cap(0.06, pp.fade and "fade" or "c1", { m = SMO, refl = 0.08 })
	table.insert(t, p("Ball", "head", V3(1.55, 0.75 + (pp.vol or 0), 1.2), V3(0, 0.98, -0.45), V3(-15, 0, 0), "c1", { m = SMO, refl = 0.08, top = true }))
	return t
end
F.slick = function(pp)
	local t = cap(0.05, pp.fade and "fade" or "c1", { m = SMO, refl = 0.18 })
	table.insert(t, p("Ball", "head", V3(1.95, 0.5, 2.1), V3(0, 0.82, 0.18), nil, "c1", { m = SMO, refl = 0.18, top = true }))
	if pp.len then
		table.insert(t, p("Block", "head", V3(1.5, pp.len, 0.3), V3(0, -0.4 - pp.len / 2 + 0.3, 0.95), V3(8, 0, 0), "c1", { m = SMO, refl = 0.18 }))
	end
	return t
end
F.sidepart = function(pp)
	local t = cap(0.08, pp.fade and "fade" or "c1")
	table.insert(t, p("Ball", "head", V3(1.25, 0.5, 1.6), V3(-0.25, 0.85, -0.2), V3(0, 0, 10), "c1", { m = FAB, top = true }))
	table.insert(t, p("Block", "head", V3(0.03, 0.05, 1.3), V3(0.38, 0.93, 0.05), V3(0, 0, -22), "dark", { top = true }))
	return t
end
F.spiky = function(pp)
	local t = cap(0.07, pp.fade and "fade" or "c1")
	local n = pp.n or 9
	for i = 1, n do
		local a = rad(i / n * 360)
		local rr = (i % 2 == 0) and 0.45 or 0.2
		table.insert(t, p("Wedge", "head", V3(0.3, 0.45 + (pp.h or 0), 0.35), V3(math.cos(a) * rr, 1.02, math.sin(a) * rr), V3(0, math.deg(a), 0), "c1", { m = FAB, top = true }))
	end
	return t
end
F.mohawk = function(pp)
	local t = cap(0.01, "fade")
	local n = 7
	for i = 1, n do
		local a = rad(-70 + (i - 1) * (150 / (n - 1)))
		local h = (pp.h or 0.5) * (1 - math.abs(i - 4) * 0.08)
		table.insert(t, p("Block", "head", V3(0.3, h, 0.36), V3(0, math.cos(a) * 0.98 + h * 0.35, math.sin(a) * 1.02), V3(math.deg(a), 0, 0), "c1", { m = FAB, top = true }))
	end
	return t
end
F.mullet = function(pp)
	local t = cap(pp.th or 0.1, pp.fade and "fade" or "c1")
	table.insert(t, p("Ball", "head", V3(1.95, 0.6, 2.05), V3(0, 0.82, 0.0), nil, "c1", { m = FAB, top = true }))
	local l = pp.len or 0.9
	table.insert(t, p("Block", "head", V3(1.35, l, 0.38), V3(0, -0.55 - l / 2 + 0.25, 0.92), V3(10, 0, 0), "c1", { m = FAB }))
	table.insert(t, p("Ball", "head", V3(1.4, 0.4, 0.5), V3(0, -0.55 - l + 0.3, 1.0), nil, "c1", { m = FAB }))
	return t
end
F.twists = function(pp)
	-- sponge twists / short twists / two-strand coils on top of a taper
	local t = cap(0.04, pp.fade and "fade" or "c1")
	local len = pp.len or 0.22
	for i = -2, 2 do
		for j = -2, 2 do
			local x, z = i * 0.34, j * 0.36 + 0.05
			if x * x + z * z < 1.0 then
				local y = 0.98 * math.sqrt(math.max(0, 1 - x * x - z * z * 0.8))
				table.insert(t, cylY("head", len, 0.2, V3(x, y + len * 0.35, z), "c1", { m = FAB, top = true }))
			end
		end
	end
	return t
end
F.curlytop = function(pp)
	local t = cap(0.03, "fade")
	for i = 1, (pp.n or 14) do
		local a = rad(i * 137.5)
		local rr = 0.75 * math.sqrt(i / (pp.n or 14))
		table.insert(t, p("Ball", "head", V3(0.42, 0.38, 0.42), V3(math.cos(a) * rr, 0.95 - rr * 0.25 + (pp.vol or 0.1), math.sin(a) * rr + 0.05 - (i < 4 and 0.4 or 0)), nil, "c1", { m = FAB, top = true }))
	end
	return t
end
F.hightop = function(pp)
	local t = cap(0.02, "fade")
	local h = pp.h or 0.9
	table.insert(t, cylY("head", h, 1.75, V3(0, 0.82 + h / 2, 0.08), "c1", { m = FAB, top = true }))
	return t
end
F.afro = function(pp)
	local s = pp.size or 2.9
	local t = cap(0.08)
	table.insert(t, p("Ball", "head", V3(s, s * 0.88, s), V3(0, 0.55 + (s - 2.9) * 0.2, 0.45), nil, "c1", { m = FAB, top = true }))
	return t
end
F.puff = function(pp)
	local t = cap(0.05, nil, { m = SMO })
	local s = pp.size or 1.3
	if pp.two then
		add(t, mirror({ p("Ball", "head", V3(s, s, s), V3(0.7, 0.85, 0.2), nil, "c1", { m = FAB, top = true }) }))
	else
		table.insert(t, p("Ball", "head", V3(s * 1.2, s, s * 1.2), V3(0, 1.0, 0.55), nil, "c1", { m = FAB, top = true }))
	end
	return t
end
F.locs = function(pp)
	local t = cap(0.07)
	add(t, strands(pp.n or 15, pp.len or 1.6, pp.d or 0.17, -125, 125, 0.35, "c1", pp.tips and "c2", { m = FAB }))
	if pp.front then -- a few hanging forward over the face
		add(t, strands(4, (pp.len or 1.6) * 0.5, pp.d or 0.17, -165, -140, 0.5, "c1", nil, { m = FAB }))
		add(t, strands(4, (pp.len or 1.6) * 0.5, pp.d or 0.17, 140, 165, 0.5, "c1", nil, { m = FAB }))
	end
	if pp.up then -- tied up on top
		table.insert(t, p("Ball", "head", V3(0.9, 0.8, 0.9), V3(0, 1.15, 0.35), nil, "c1", { m = FAB, top = true }))
	end
	return t
end
F.braids = function(pp)
	local t = cap(0.02)
	add(t, rows(pp.rows or 7, "c1", 0.11, { m = FAB, top = true }))
	if pp.len and pp.len > 0 then
		add(t, strands(pp.n or 12, pp.len, pp.d or 0.12, -110, 110, 0.1, "c1", pp.tips and "c2", { m = FAB }))
	end
	return t
end
F.long = function(pp)
	local l = pp.len or 2.0
	local t = cap(pp.th or 0.09, nil, { m = pp.sleek and SMO or FAB, refl = pp.sleek and 0.12 or nil })
	local m = pp.sleek and SMO or FAB
	-- the fall down the back, rounded with a ball at the end
	table.insert(t, p("Block", "head", V3(1.85, l, 0.42), V3(0, 0.2 - l / 2, 0.86), V3(6, 0, 0), "c1", { m = m }))
	table.insert(t, p("Ball", "head", V3(1.85, 0.5, 0.5), V3(0, 0.2 - l, 0.95), nil, "c1", { m = m }))
	-- the sides framing the face and falling in front of the shoulders
	add(t, mirror({ p("Block", "head", V3(0.32, l * 0.85, 0.7), V3(0.95, 0.15 - l * 0.42, -0.1), V3(0, 0, 5), "c1", { m = m }) }))
	if pp.wavy then
		for i = 1, 4 do
			add(t, mirror({ p("Ball", "head", V3(0.42, 0.45, 0.5), V3(1.0, 0.1 - i * l * 0.2, 0.2 + (i % 2) * 0.25), nil, "c1", { m = m }) }))
		end
	end
	if pp.bangs then
		table.insert(t, p("Block", "head", V3(1.6, 0.36, 0.4), V3(0, 0.5, -0.84), V3(-8, 0, 0), "c1", { m = m, top = true }))
	end
	if pp.layers then -- butterfly / wolf: face-framing layers
		add(t, mirror({ p("Ball", "head", V3(0.6, 0.7, 0.55), V3(0.8, -0.15, -0.6), nil, "c1", { m = m }) }))
		add(t, mirror({ p("Ball", "head", V3(0.7, 0.8, 0.6), V3(0.95, -0.75, -0.3), nil, "c1", { m = m }) }))
	end
	return t
end
F.bob = function(pp)
	local t = cap(0.1)
	local l = pp.len or 0.55
	table.insert(t, p("Ball", "head", V3(2.3, 1.2 + l, 2.15), V3(0, -0.1, 0.32), nil, "c1", { m = SMO, refl = 0.05 }))
	add(t, mirror({ p("Block", "head", V3(0.3, 1.0 + l, 0.85), V3(0.97, -0.3 - l * 0.3, -0.2), nil, "c1", { m = SMO }) }))
	if pp.bangs then
		table.insert(t, p("Block", "head", V3(1.6, 0.34, 0.4), V3(0, 0.5, -0.84), V3(-8, 0, 0), "c1", { m = SMO, top = true }))
	end
	return t
end
F.pixie = function()
	local t = cap(0.08)
	table.insert(t, p("Ball", "head", V3(1.3, 0.45, 0.8), V3(-0.3, 0.6, -0.65), V3(-15, 0, 15), "c1", { m = FAB, top = true }))
	add(t, mirror({ p("Block", "head", V3(0.18, 0.5, 0.35), V3(0.98, -0.12, -0.35), nil, "c1", { m = FAB }) }))
	return t
end
F.pony = function(pp)
	local t = cap(0.05, nil, { m = SMO, refl = 0.06 })
	local hy = pp.high and 0.95 or 0.35
	local hz = pp.high and 0.55 or 0.98
	table.insert(t, p("Ball", "head", V3(0.38, 0.38, 0.38), V3(0, hy, hz), nil, "c2", { m = SMO }))
	local l = pp.len or 1.6
	local base = V3(0, hy, hz + 0.1)
	local tip = base + V3(0, -l, 0.35)
	local mid = (base + tip) / 2
	table.insert(t, p("Ball", "head", V3(0.55, l * 1.05, 0.55), nil, nil, "c1", { m = SMO, refl = 0.06, lcf = CFrame.lookAt(mid, tip) * CFrame.Angles(rad(90), 0, 0) }))
	if pp.braid then
		for i = 1, 6 do
			table.insert(t, p("Ball", "head", V3(0.4, 0.32, 0.4), base:Lerp(tip, i / 7), nil, "c1", { m = FAB }))
		end
	end
	return t
end
F.bun = function(pp)
	local t = cap(0.05, nil, { m = SMO, refl = 0.06 })
	if pp.two then -- space buns
		add(t, mirror({ p("Ball", "head", V3(0.72, 0.72, 0.72), V3(0.62, 0.92, 0.15), nil, "c1", { m = FAB, top = true }) }))
	elseif pp.low then -- man bun / low bun
		table.insert(t, p("Ball", "head", V3(0.62, 0.55, 0.55), V3(0, 0.55, 1.05), nil, "c1", { m = FAB }))
	else
		table.insert(t, p("Ball", "head", V3(0.85, 0.75, 0.85), V3(0, 1.12, 0.35), nil, "c1", { m = FAB, top = true }))
	end
	if pp.claw then -- claw clip
		table.insert(t, p("Block", "head", V3(0.7, 0.3, 0.18), V3(0, 0.5, 1.12), nil, "c2", { m = SMO }))
	end
	return t
end

------------------------------------------------------------------ facial hair (frame "head")
local function stache(w, thick, c, y, extra)
	return p("Ball", "head", V3(w, thick, 0.28), V3(0, y or -0.42, -0.94), V3(-10, 0, 0), c or "c1", extra or { m = FAB })
end
F.stubble = function(pp)
	return {
		p("Ball", "head", V3(2.0, 1.25, 1.86), V3(0, -0.68, -0.14), nil, "c1", { m = FAB, t = pp.t or 0.55 }),
		stache(0.8, 0.14, "c1", -0.42, { m = FAB, t = pp.t or 0.55 }),
	}
end
F.beard = function(pp)
	local len = pp.len or 0
	local t = {
		p("Ball", "head", V3(2.04, 1.15 + len * 0.6, 1.9), V3(0, -0.74 - len * 0.3, -0.16), nil, pp.fade and "fade" or "c1", { m = FAB }),
		p("Ball", "head", V3(1.25, 0.6 + len, 0.8), V3(0, -1.0 - len * 0.45, -0.62), nil, "c1", { m = FAB }),
		stache(0.82, 0.18, "c1"),
	}
	if pp.boxed then -- a squared-off neckline
		table.insert(t, p("Block", "head", V3(1.3, 0.25, 0.7), V3(0, -1.12, -0.55), nil, "c1", { m = FAB }))
	end
	if len > 0.6 then
		table.insert(t, p("Ball", "head", V3(0.95, len * 0.9, 0.6), V3(0, -1.2 - len * 0.7, -0.6), nil, "c1", { m = FAB }))
	end
	if pp.braid then
		for i = 1, 4 do
			table.insert(t, p("Ball", "head", V3(0.26, 0.24, 0.26), V3(0, -1.45 - len * 0.6 - i * 0.2, -0.62), nil, "c1", { m = FAB }))
		end
		table.insert(t, cylY("head", 0.12, 0.3, V3(0, -1.5 - len * 0.6 - 4 * 0.2, -0.62), "c2", { m = MET }))
	end
	return t
end
F.goatee = function(pp)
	local t = {
		p("Ball", "head", V3(0.7, 0.62 + (pp.len or 0), 0.5), V3(0, -1.0 - (pp.len or 0) * 0.4, -0.78), nil, "c1", { m = FAB }),
	}
	if not pp.nostache then
		table.insert(t, stache(0.75, 0.15, "c1"))
		add(t, mirror({ p("Block", "head", V3(0.1, 0.42, 0.12), V3(0.3, -0.68, -0.9), nil, "c1", { m = FAB }) }))
	end
	return t
end
F.chinstrap = function()
	local t = { p("Ball", "head", V3(0.7, 0.3, 0.4), V3(0, -1.12, -0.72), nil, "c1", { m = FAB }) }
	add(t, mirror({
		p("Block", "head", V3(0.12, 0.85, 0.16), V3(0.92, -0.62, -0.25), V3(-25, 0, -8), "c1", { m = FAB }),
		p("Block", "head", V3(0.12, 0.5, 0.16), V3(0.62, -1.0, -0.58), V3(-55, 25, -8), "c1", { m = FAB }),
	}))
	return t
end
F.mustache = function(pp)
	local t = { stache(pp.w or 0.85, pp.thick or 0.2, "c1") }
	if pp.horseshoe then
		add(t, mirror({ p("Block", "head", V3(0.13, 0.6, 0.14), V3(0.36, -0.72, -0.86), nil, "c1", { m = FAB }) }))
	end
	if pp.handlebar then
		add(t, mirror({ p("Ball", "head", V3(0.18, 0.18, 0.18), V3(0.5, -0.33, -0.86), nil, "c1", { m = FAB }) }))
	end
	return t
end
F.sideburns = function(pp)
	return mirror({ p("Block", "head", V3(0.16, pp.len or 0.55, 0.32), V3(0.98, -0.12, -0.15), nil, "c1", { m = FAB }) })
end
F.soulpatch = function()
	return { p("Ball", "head", V3(0.22, 0.2, 0.12), V3(0, -0.84, -0.9), nil, "c1", { m = FAB }) }
end

------------------------------------------------------------------ headwear (frame "head")
F.cap = function(pp)
	local t = {
		p("Ball", "head", V3(2.18, 1.35, 2.28), V3(0, 0.55, 0.08), nil, "c1", { m = FAB }),
		p("Ball", "head", V3(0.16, 0.1, 0.16), V3(0, 1.22, 0.08), nil, "c2", { m = FAB }),
	}
	local back = pp.back and -1 or 1
	if pp.flat then
		table.insert(t, p("Block", "head", V3(1.65, 0.06, 0.95), V3(0, 0.4, -1.32 * back), nil, "c2", { m = FAB }))
	else
		table.insert(t, p("Ball", "head", V3(1.6, 0.08, 1.1), V3(0, 0.38, -1.25 * back), V3(-8 * back, 0, 0), "c2", { m = FAB }))
	end
	if pp.trucker then -- mesh back panel
		table.insert(t, p("Ball", "head", V3(2.2, 1.2, 1.4), V3(0, 0.5, 0.55), nil, "white", { m = FAB, t = 0.1 }))
	end
	if pp.txt then
		table.insert(t, p("Block", "head", V3(1.0, 0.36, 0.05), V3(0, 0.72, -1.05 * back), V3(-28 * back, pp.back and 180 or 0, 0), "c1", { m = FAB, t = 1, txt = { text = pp.txt, color = "c2" } }))
	end
	return t
end
F.beanie = function(pp)
	local t = {
		p("Ball", "head", V3(2.22, pp.short and 1.2 or 1.65, 2.3), V3(0, pp.short and 0.7 or 0.52, 0.08), nil, "c1", { m = FAB }),
		cylY("head", 0.38, 2.24, V3(0, pp.short and 0.6 or 0.32, 0.08), "dark", { m = FAB }, -8),
	}
	if pp.pom then
		table.insert(t, p("Ball", "head", V3(0.5, 0.5, 0.5), V3(0, pp.short and 1.35 or 1.4, 0.1), nil, "c2", { m = FAB }))
	end
	return t
end
F.bucket = function()
	return {
		cylY("head", 0.75, 2.15, V3(0, 0.78, 0.06), "c1", { m = FAB }),
		cylY("head", 0.08, 3.0, V3(0, 0.42, 0.06), "c1", { m = FAB }, -4),
		cylY("head", 0.1, 2.17, V3(0, 0.52, 0.06), "c2", { m = FAB }),
	}
end
F.fedora = function(pp)
	return {
		cylY("head", 0.75, 1.95, V3(0, 1.0, 0.06), "c1", { m = FAB }),
		p("Ball", "head", V3(1.7, 0.35, 1.6), V3(0, 1.35, 0.06), nil, "c1", { m = FAB }),
		cylY("head", 0.05, pp.wide and 3.4 or 3.0, V3(0, 0.62, 0.06), "c1", { m = FAB }),
		cylY("head", 0.16, 1.98, V3(0, 0.72, 0.06), "c2", { m = FAB }),
	}
end
F.cowboy = function()
	local t = {
		cylY("head", 0.8, 1.95, V3(0, 1.0, 0.06), "c1", { m = LEA }),
		p("Ball", "head", V3(1.6, 0.35, 1.7), V3(0, 1.38, 0.06), nil, "c1", { m = LEA }),
		cylY("head", 0.05, 2.6, V3(0, 0.6, 0.06), "c1", { m = LEA }),
		cylY("head", 0.14, 1.98, V3(0, 0.72, 0.06), "c2", { m = LEA }),
	}
	add(t, mirror({ p("Block", "head", V3(0.9, 0.05, 2.6), V3(1.45, 0.78, 0.06), V3(0, 0, 35), "c1", { m = LEA }) }))
	return t
end
F.beret = function()
	return {
		p("Ball", "head", V3(2.45, 0.62, 2.4), V3(0.15, 0.92, 0.05), V3(0, 0, 10), "c1", { m = FAB }),
		cylY("head", 0.12, 2.1, V3(0, 0.62, 0.05), "c1", { m = FAB }),
	}
end
F.durag = function(pp)
	local m = pp.velvet and FAB or SMO
	local t = {
		p("Ball", "head", V3(2.14, 1.48, 2.24), V3(0, 0.43, 0.12), nil, "c1", { m = m, refl = pp.velvet and 0 or 0.1 }),
		cylY("head", 0.2, 2.12, V3(0, 0.28, 0.06), "c1", { m = m }, -6),
		p("Ball", "head", V3(0.4, 0.3, 0.3), V3(0, 0.15, 1.1), nil, "c1", { m = m }),
	}
	add(t, mirror({ p("Block", "head", V3(0.32, 1.6, 0.04), V3(0.14, -0.7, 1.1), V3(6, 0, 4), "c1", { m = m }) }))
	return t
end
F.headwrap = function()
	-- a bandana tied on the head, knot and tails at the back
	local t = {
		p("Ball", "head", V3(2.14, 1.42, 2.24), V3(0, 0.46, 0.12), nil, "c1", { m = FAB }),
		p("Ball", "head", V3(0.36, 0.3, 0.3), V3(0, 0.2, 1.12), nil, "c1", { m = FAB }),
		p("Block", "head", V3(1.0, 0.04, 0.04), V3(0, 0.62, -1.02), nil, "c2", { m = FAB }),
	}
	add(t, mirror({ p("Wedge", "head", V3(0.04, 0.6, 0.3), V3(0.15, -0.15, 1.15), V3(0, 90, 15), "c1", { m = FAB }) }))
	return t
end
F.headband = function()
	return { cylY("head", 0.24, 2.14, V3(0, 0.5, 0.06), "c1", { m = FAB }, -8) }
end
F.helmet = function(pp)
	local t = {
		p("Ball", "head", V3(2.4, 1.8, 2.55), V3(0, 0.45, 0.08), nil, "c1", { m = FAB }),
		cylY("head", 0.12, 2.36, V3(0, 0.0, 0.1), "c1", { m = FAB }, -6),
	}
	if pp.nvg then
		table.insert(t, p("Block", "head", V3(0.35, 0.3, 0.12), V3(0, 0.75, -1.15), nil, "black", { m = MET }))
		add(t, mirror({ cylZ("head", 0.35, 0.22, V3(0.14, 0.62, -1.38), "black", { m = MET }) }))
	end
	if pp.strap then
		add(t, mirror({ p("Block", "head", V3(0.08, 0.9, 0.1), V3(0.98, -0.5, -0.15), V3(-12, 0, 0), "black", { m = FAB }) }))
	end
	return t
end
F.hardhat = function()
	return {
		p("Ball", "head", V3(2.3, 1.55, 2.45), V3(0, 0.62, 0.06), nil, "c1", { m = SMO }),
		p("Ball", "head", V3(2.6, 0.12, 2.9), V3(0, 0.3, -0.05), nil, "c1", { m = SMO }),
		p("Block", "head", V3(0.18, 0.12, 2.2), V3(0, 1.36, 0.06), nil, "c1", { m = SMO }),
	}
end
F.tophat = function()
	return {
		cylY("head", 1.6, 1.85, V3(0, 1.4, 0.06), "c1", { m = FAB }),
		cylY("head", 0.05, 2.7, V3(0, 0.62, 0.06), "c1", { m = FAB }),
		cylY("head", 0.22, 1.87, V3(0, 0.78, 0.06), "c2", { m = FAB }),
	}
end
F.crown = function(pp)
	local t = { cylY("head", 0.35, 1.9, V3(0, 1.0, 0.06), "c1", { m = MET, refl = 0.3 }) }
	for i = 0, 7 do
		local a = i / 8 * math.pi * 2
		table.insert(t, p("Wedge", "head", V3(0.3, 0.45, 0.12), V3(math.sin(a) * 0.92, 1.38, math.cos(a) * 0.92 + 0.06), V3(0, math.deg(a), 0), "c1", { m = MET, refl = 0.3 }))
		table.insert(t, p("Ball", "head", V3(0.14, 0.14, 0.14), V3(math.sin(a) * 0.96, 1.0, math.cos(a) * 0.96 + 0.06), nil, "c2", { m = GLA, refl = 0.45, spark = (i == 0) and pp.iced or nil }))
	end
	return t
end
F.halo = function()
	local t = ring("head", V3(0, 1.6, 0.08), 0.8, 18, "Cyl", "c1", "Y", { m = NEO }, V3(0.32, 0.1, 0.1))
	return t
end
F.headphones = function(pp)
	local pts = {}
	for i = 0, 8 do
		local a = rad(-90 + i * 22.5)
		table.insert(pts, V3(math.sin(a) * 1.12, math.cos(a) * 1.12 + 0.1, 0.05))
	end
	local t = along("head", pts, "c1", "box", 0.14, { m = SMO })
	add(t, mirror({ cylZ("head", 0.4, 0.85, V3(1.08, -0.05, 0.05), "c1", { m = SMO }, V3(0, 90, 0)), cylZ("head", 0.1, 0.6, V3(1.3, -0.05, 0.05), "c2", { m = SMO, glow = pp.rgb }, V3(0, 90, 0)) }))
	return t
end
F.tiara = function(pp)
	local t = ring("head", V3(0, 0.72, 0.1), 1.02, 12, "Ball", "c1", "Y", { m = MET, refl = 0.3 }, V3(0.12, 0.12, 0.12))
	table.insert(t, p("Ball", "head", V3(0.22, 0.32, 0.12), V3(0, 1.0, -0.88), nil, "c2", { m = GLA, refl = 0.45, spark = pp.iced }))
	return t
end
F.visor = function()
	return {
		cylY("head", 0.2, 2.14, V3(0, 0.45, 0.06), "c1", { m = FAB }, -6),
		p("Ball", "head", V3(1.6, 0.07, 1.15), V3(0, 0.4, -1.22), V3(-10, 0, 0), "c2", { m = SMO }),
	}
end
F.ears = function(pp)
	-- cat / bunny / fox ears on a band
	local t = { cylY("head", 0.1, 2.15, V3(0, 0.8, 0.06), "c1", { m = SMO }, 20) }
	local h = pp.bunny and 1.3 or 0.5
	add(t, mirror({ p("Wedge", "head", V3(0.15, h, pp.bunny and 0.35 or 0.5), V3(0.55, 1.05 + h / 2, 0.0), V3(0, 0, -12), "c1", { m = FAB }) }))
	return t
end
F.horns = function()
	return mirror({
		p("Wedge", "head", V3(0.2, 0.55, 0.3), V3(0.55, 1.05, -0.1), V3(0, 0, -20), "c1", { m = SMO }),
	})
end
F.wizard = function()
	local t = { cylY("head", 0.05, 3.2, V3(0, 0.62, 0.06), "c1", { m = FAB }) }
	for i = 0, 5 do
		table.insert(t, cylY("head", 0.45, 1.9 - i * 0.3, V3(i * 0.04, 0.85 + i * 0.4, 0.06 + i * 0.03), "c1", { m = FAB }))
	end
	table.insert(t, cylY("head", 0.18, 1.92, V3(0, 0.75, 0.06), "c2", { m = FAB }))
	return t
end
F.tricorn = function()
	local t = { p("Ball", "head", V3(2.1, 1.2, 2.2), V3(0, 0.85, 0.06), nil, "c1", { m = FAB }) }
	for i = 0, 2 do
		local a = rad(i * 120)
		table.insert(t, p("Block", "head", V3(2.2, 0.55, 0.06), V3(math.sin(a) * 1.0, 1.0, math.cos(a) * 1.0 + 0.06), V3(-15, math.deg(a), 0), "c1", { m = FAB }))
	end
	table.insert(t, p("Block", "head", V3(1.9, 0.06, 0.06), V3(0, 1.28, 1.08), nil, "c2", { m = FAB }))
	return t
end
F.chef = function()
	return {
		cylY("head", 0.55, 2.12, V3(0, 0.7, 0.06), "c1", { m = FAB }),
		p("Ball", "head", V3(2.5, 1.3, 2.5), V3(0, 1.45, 0.06), nil, "c1", { m = FAB }),
	}
end
F.spacehelmet = function()
	return {
		p("Ball", "head", V3(3.0, 3.0, 3.0), V3(0, 0.0, 0.05), nil, "c2", { m = GLA, t = 0.6, refl = 0.4 }),
		cylY("head", 0.35, 2.6, V3(0, -1.35, 0.05), "c1", { m = SMO }),
	}
end
F.knighthelm = function()
	return {
		cylY("head", 2.4, 2.35, V3(0, 0.05, 0.05), "c1", { m = MET, refl = 0.25 }),
		p("Ball", "head", V3(2.35, 0.9, 2.35), V3(0, 1.25, 0.05), nil, "c1", { m = MET, refl = 0.25 }),
		p("Block", "head", V3(1.4, 0.12, 0.1), V3(0, 0.05, -1.2), nil, "black", { m = SMO }),
		p("Block", "head", V3(0.1, 1.2, 0.08), V3(0, -0.5, -1.2), nil, "c1", { m = MET }),
	}
end
F.hood = function(pp)
	local t = {
		p("Ball", "head", V3(2.55, 2.5, 2.65), V3(0, 0.25, 0.22), nil, "c1", { m = FAB }),
		cylZ("head", 0.2, 2.3, V3(0, 0.05, -0.95), "dark", { m = FAB }),
	}
	if pp.horn then -- unicorn hood: horn + ears
		table.insert(t, p("Wedge", "head", V3(0.3, 0.8, 0.3), V3(0, 1.75, -0.45), V3(-20, 0, 0), "gold", { m = MET }))
		add(t, mirror({ p("Wedge", "head", V3(0.15, 0.45, 0.35), V3(0.75, 1.45, 0.1), V3(0, 0, -15), "c1", { m = FAB }) }))
		for i = 1, 5 do
			table.insert(t, p("Ball", "head", V3(0.35, 0.45, 0.35), V3(0, 1.45 - i * 0.35, 0.9 + i * 0.12), nil, "c2", { m = FAB }))
		end
	end
	if pp.ears then
		add(t, mirror({ p("Wedge", "head", V3(0.18, 0.5, 0.45), V3(0.7, 1.45, 0.1), V3(0, 0, -15), "c1", { m = FAB }) }))
	end
	return t
end

------------------------------------------------------------------ eyewear (frame "head")
local function frameArms(c)
	return mirror({ p("Block", "head", V3(0.05, 0.06, 1.0), V3(0.98, FACE.eyeY + 0.05, -0.5), nil, c, { m = SMO }) })
end
F.glasses = function(pp)
	local shape = pp.shape or "round"
	local t = {}
	local lensX, lensZ = FACE.eyeX, FACE.eyeZ - 0.1
	local lensM = { m = GLA, t = pp.clear and 0.85 or 0.25, refl = 0.35 }
	if shape == "shield" then
		table.insert(t, p("Block", "head", V3(1.75, pp.tall or 0.42, 0.06), V3(0, FACE.eyeY, lensZ - 0.02), V3(0, 0, 0), "c2", lensM))
		table.insert(t, p("Block", "head", V3(1.8, 0.06, 0.08), V3(0, FACE.eyeY + 0.22, lensZ - 0.02), nil, "c1", { m = SMO }))
	else
		for _, sx in ipairs({ -1, 1 }) do
			local pos = V3(sx * lensX, FACE.eyeY, lensZ)
			if shape == "round" then
				table.insert(t, cylZ("head", 0.05, pp.size or 0.48, pos, "c2", lensM))
				table.insert(t, cylZ("head", 0.03, (pp.size or 0.48) + 0.06, pos + V3(0, 0, 0.01), "c1", { m = MET }))
			elseif shape == "rect" then
				table.insert(t, p("Block", "head", V3(0.6, pp.tall or 0.32, 0.05), pos, nil, "c2", lensM))
				table.insert(t, p("Block", "head", V3(0.66, 0.06, 0.06), pos + V3(0, (pp.tall or 0.32) / 2, 0), nil, "c1", { m = SMO }))
			elseif shape == "aviator" then
				table.insert(t, p("Ball", "head", V3(0.62, 0.52, 0.06), pos + V3(sx * 0.02, -0.04, 0), V3(0, 0, sx * -8), "c2", lensM))
				table.insert(t, p("Block", "head", V3(0.6, 0.03, 0.04), pos + V3(0, 0.2, 0), nil, "c1", { m = MET }))
			elseif shape == "cateye" then
				table.insert(t, p("Ball", "head", V3(0.62, 0.36, 0.06), pos, V3(0, 0, sx * 10), "c2", lensM))
				table.insert(t, p("Wedge", "head", V3(0.05, 0.16, 0.2), pos + V3(sx * 0.32, 0.14, 0), V3(0, sx * 90, 0), "c1", { m = SMO }))
			elseif shape == "oval" then -- tiny 90s / Y2K ovals
				table.insert(t, p("Ball", "head", V3(0.48, 0.24, 0.05), pos, nil, "c2", lensM))
			end
		end
		table.insert(t, p("Block", "head", V3(0.22, 0.04, 0.04), V3(0, FACE.eyeY + 0.04, lensZ), nil, "c1", { m = MET }))
	end
	add(t, frameArms("c1"))
	return t
end
F.goggles = function(pp)
	local t = {
		p("Ball", "head", V3(1.75, 0.6, 0.35), V3(0, FACE.eyeY + 0.05, FACE.eyeZ - 0.05), nil, "c2", { m = GLA, t = 0.2, refl = 0.5 }),
		cylY("head", 0.22, 2.16, V3(0, FACE.eyeY + 0.05, 0.05), "c1", { m = FAB }),
	}
	if pp.up then -- pushed up on the forehead
		for _, q in ipairs(t) do
			q.o = q.o + V3(0, 0.6, 0.12)
			q.r = V3(-18, 0, 0)
		end
	end
	return t
end
F.vrvisor = function()
	return {
		p("Block", "head", V3(1.75, 0.6, 0.55), V3(0, FACE.eyeY + 0.05, FACE.eyeZ - 0.2), nil, "c1", { m = SMO }),
		p("Block", "head", V3(1.55, 0.32, 0.04), V3(0, FACE.eyeY + 0.05, FACE.eyeZ - 0.48), nil, "c2", { m = NEO }),
		cylY("head", 0.2, 2.16, V3(0, FACE.eyeY + 0.1, 0.05), "black", { m = FAB }),
		p("Block", "head", V3(0.2, 0.2, 1.9), V3(0, 1.0, 0.05), V3(0, 0, 0), "black", { m = FAB }),
	}
end
F.eyepatch = function()
	return {
		p("Ball", "head", V3(0.45, 0.4, 0.08), V3(FACE.eyeX, FACE.eyeY, FACE.eyeZ - 0.03), nil, "c1", { m = LEA }),
		p("Block", "head", V3(0.04, 0.04, 2.3), V3(0, 0.25, 0.0), V3(0, 0, -25), "c1", { m = LEA }),
	}
end
F.monocle = function()
	return {
		cylZ("head", 0.04, 0.42, V3(FACE.eyeX, FACE.eyeY, FACE.eyeZ - 0.08), "c2", { m = GLA, t = 0.8, refl = 0.4 }),
		ring("head", V3(FACE.eyeX, FACE.eyeY, FACE.eyeZ - 0.08), 0.22, 10, "Ball", "c1", "Z", { m = MET }, V3(0.05, 0.05, 0.05))[1],
	}
end

------------------------------------------------------------------ masks (head / neck)
F.balaclava = function(pp)
	local t = {
		p("Ball", "head", V3(2.16, 2.45, 2.2), V3(0, -0.15, 0.04), nil, "c1", { m = FAB }),
		cylY("head", 0.9, 1.25, V3(0, -1.55, 0.05), "c1", { m = FAB }),
	}
	if pp.open then -- open face (eyes, nose and mouth show)
		table.insert(t, p("Ball", "head", V3(1.4, 1.35, 0.4), V3(0, -0.3, -1.0), nil, "skin", {}))
	else -- an eye slot
		table.insert(t, p("Block", "head", V3(1.35, 0.32, 0.12), V3(0, FACE.eyeY, -1.07), nil, "skin", {}))
	end
	if pp.pom then
		table.insert(t, p("Ball", "head", V3(0.5, 0.5, 0.5), V3(0, 1.15, 0.05), nil, "c2", { m = FAB }))
	end
	return t
end
F.bandanaface = function()
	-- an outlaw bandana pulled over the nose, point hanging below the chin
	local t = { p("Ball", "head", V3(2.22, 1.7, 2.28), V3(0, -0.72, -0.1), nil, "c1", { m = FAB }) }
	add(t, mirror({ p("Wedge", "head", V3(0.04, 0.7, 0.5), V3(0.25, -1.55, -0.95), V3(0, -90, 0), "c1", { m = FAB }) }))
	table.insert(t, p("Ball", "head", V3(0.3, 0.25, 0.25), V3(0, -0.2, 1.1), nil, "c1", { m = FAB }))
	return t
end
F.loosebandana = function(pp)
	-- folded into a triangle and tied loose round the neck, point down over the chest
	local t = {
		cylY("neck", 0.18, 0.62, V3(0, 0.02, 0.08), "c1", { m = FAB }, -12),
		p("Ball", "neck", V3(0.66, 0.2, 0.62), V3(0, -0.06, 0.02), nil, "c1", { m = FAB }),
	}
	local drop = pp.low and 0.62 or 0.42
	add(t, mirror({ p("Wedge", "neck", V3(0.03, drop, 0.26), V3(0.13, -0.1 - drop / 2, -0.4), V3(-12, -90, 0), "c1", { m = FAB }) }))
	table.insert(t, p("Ball", "neck", V3(0.14, 0.12, 0.12), V3(0, -0.02, 0.42), nil, "c1", { m = FAB }))
	return t
end
F.facemask = function()
	return {
		p("Ball", "head", V3(1.55, 1.05, 0.7), V3(0, -0.65, -0.72), nil, "c1", { m = FAB }),
		p("Block", "head", V3(0.04, 0.04, 1.2), V3(0.9, -0.4, -0.35), nil, "c1", { m = FAB }),
		p("Block", "head", V3(0.04, 0.04, 1.2), V3(-0.9, -0.4, -0.35), nil, "c1", { m = FAB }),
	}
end
F.gasmask = function()
	return {
		p("Ball", "head", V3(1.9, 1.9, 1.0), V3(0, -0.35, -0.65), nil, "c1", { m = RUB }),
		p("Block", "head", V3(1.25, 0.38, 0.1), V3(0, FACE.eyeY, -1.12), nil, "c2", { m = GLA, t = 0.3, refl = 0.4 }),
		cylZ("head", 0.45, 0.45, V3(0, -0.85, -1.25), "black", { m = RUB }),
		cylZ("head", 0.35, 0.4, V3(0.62, -0.75, -1.05), "black", { m = RUB }, V3(0, -35, 0)),
	}
end
F.goalie = function()
	local t = { p("Ball", "head", V3(2.0, 2.45, 1.25), V3(0, -0.15, -0.6), nil, "c1", { m = SMO }) }
	add(t, mirror({ p("Ball", "head", V3(0.36, 0.2, 0.1), V3(FACE.eyeX, FACE.eyeY, -1.2), nil, "black", { m = SMO }) }))
	for i = 1, 3 do
		table.insert(t, p("Ball", "head", V3(0.08, 0.08, 0.06), V3((i - 2) * 0.22, -0.6, -1.21), nil, "black", { m = SMO }))
	end
	add(t, mirror({ p("Wedge", "head", V3(0.04, 0.3, 0.16), V3(0.5, 0.45, -1.18), V3(0, -90, 20), "c2", { m = SMO }) }))
	return t
end
F.clown = function()
	local t = {
		p("Ball", "head", V3(2.08, 2.3, 1.3), V3(0, -0.15, -0.55), nil, "white", { m = SMO }),
		p("Ball", "head", V3(0.42, 0.42, 0.42), V3(0, -0.2, -1.3), nil, "red", { m = SMO }),
		p("Ball", "head", V3(1.0, 0.18, 0.1), V3(0, -0.72, -1.17), nil, "red", { m = SMO }),
	}
	add(t, mirror({
		p("Ball", "head", V3(0.3, 0.42, 0.06), V3(FACE.eyeX, FACE.eyeY, -1.2), nil, "c2", { m = SMO }),
		p("Ball", "head", V3(0.85, 0.9, 0.85), V3(1.15, 0.6, 0.25), nil, "c1", { m = FAB, top = true }),
	}))
	return t
end
F.skullmask = function()
	local t = { p("Ball", "head", V3(1.95, 1.25, 1.15), V3(0, -0.7, -0.55), nil, "bone", { m = SMO }) }
	for i = 0, 6 do
		table.insert(t, p("Block", "head", V3(0.02, 0.3, 0.05), V3((i - 3) * 0.14, -0.7, -1.12 + math.abs(i - 3) * 0.04), nil, "black", { m = SMO }))
	end
	return t
end
F.ninjamask = function()
	return {
		p("Ball", "head", V3(2.18, 1.6, 2.24), V3(0, -0.62, -0.02), nil, "c1", { m = FAB }),
		p("Ball", "head", V3(2.16, 1.25, 2.22), V3(0, 0.62, 0.1), nil, "c1", { m = FAB, top = true }),
		p("Block", "head", V3(1.5, 0.06, 0.06), V3(0, 0.45, -1.07), nil, "c2", { m = FAB }),
	}
end
F.masquerade = function()
	local t = { p("Block", "head", V3(1.7, 0.4, 0.08), V3(0, FACE.eyeY + 0.02, -1.02), nil, "c1", { m = SMO, refl = 0.2 }) }
	add(t, mirror({
		p("Ball", "head", V3(0.3, 0.2, 0.06), V3(FACE.eyeX, FACE.eyeY, -1.07), nil, "black", { m = SMO }),
		p("Wedge", "head", V3(0.06, 0.35, 0.3), V3(0.85, FACE.eyeY + 0.25, -0.9), V3(0, -90, 0), "c2", { m = SMO }),
	}))
	return t
end
F.foxmask = function()
	local t = {
		p("Ball", "head", V3(1.9, 2.0, 1.1), V3(0, -0.05, -0.62), nil, "c1", { m = SMO }),
		p("Wedge", "head", V3(0.6, 0.5, 0.7), V3(0, -0.35, -1.3), V3(180, 0, 0), "c1", { m = SMO }),
	}
	add(t, mirror({
		p("Block", "head", V3(0.32, 0.06, 0.05), V3(FACE.eyeX, FACE.eyeY, -1.17), V3(0, 0, -15), "c2", { m = SMO }),
		p("Wedge", "head", V3(0.12, 0.6, 0.45), V3(0.6, 1.1, -0.2), V3(0, 0, -10), "c1", { m = SMO }),
	}))
	return t
end
F.respirator = function()
	return {
		p("Ball", "head", V3(1.55, 0.95, 0.75), V3(0, -0.68, -0.75), nil, "c1", { m = SMO }),
		p("Block", "head", V3(0.9, 0.06, 0.06), V3(0, -0.6, -1.12), nil, "c2", { m = NEO }),
		p("Block", "head", V3(0.6, 0.06, 0.06), V3(0, -0.78, -1.1), nil, "c2", { m = NEO }),
		cylY("head", 0.12, 2.15, V3(0, -0.45, 0.05), "black", { m = RUB }, 10),
	}
end

------------------------------------------------------------------ neck: chains, pendants, ties (frame "chest")
-- in the chest frame the neck base sits at about (0, 0.78, 0.6), the chest surface at z = 0
local function chainPath(drop, n, spread)
	local s = spread or 0.3
	local left = bezier(V3(-s, 0.78, 0.44), V3(-s * 1.05, 0.78 - drop * 0.62, -0.1), V3(0, 0.78 - drop, -0.06), n)
	local right = bezier(V3(0, 0.78 - drop, -0.06), V3(s * 1.05, 0.78 - drop * 0.62, -0.1), V3(s, 0.78, 0.44), n)
	local pts = left
	for i = 2, #right do
		table.insert(pts, right[i])
	end
	return pts, V3(0, 0.78 - drop, -0.06)
end

local function pendant(kind, at, x)
	local t = {}
	local g = x.iced and "c2" or "c1"
	local gm = x.iced and { m = GLA, refl = 0.45, spark = true } or { m = MET, refl = 0.3 }
	local below = at + V3(0, -0.04, -0.03)
	if kind == "cross" then
		table.insert(t, p("Block", "chest", V3(0.05, 0.34, 0.03), below + V3(0, -0.17, 0), nil, g, gm))
		table.insert(t, p("Block", "chest", V3(0.2, 0.05, 0.03), below + V3(0, -0.1, 0), nil, g, gm))
	elseif kind == "medallion" then
		table.insert(t, cylZ("chest", 0.035, 0.32, below + V3(0, -0.17, 0), "c1", { m = MET, refl = 0.3 }))
		table.insert(t, cylZ("chest", 0.04, 0.16, below + V3(0, -0.17, -0.02), "c2", { m = GLA, refl = 0.45, spark = x.iced }))
	elseif kind == "diamond" then
		table.insert(t, p("Block", "chest", V3(0.14, 0.14, 0.06), below + V3(0, -0.12, 0), V3(0, 0, 45), "c2", { m = GLA, refl = 0.5, spark = true }))
	elseif kind == "crown" then
		table.insert(t, p("Block", "chest", V3(0.26, 0.1, 0.03), below + V3(0, -0.2, 0), nil, g, gm))
		for i = -1, 1 do
			table.insert(t, p("Wedge", "chest", V3(0.06, 0.12, 0.03), below + V3(i * 0.09, -0.1, 0), nil, g, gm))
		end
	elseif kind == "heart" then
		add(t, mirror({ p("Ball", "chest", V3(0.13, 0.13, 0.04), below + V3(0.045, -0.12, 0), nil, g, gm) }))
		table.insert(t, p("Block", "chest", V3(0.12, 0.12, 0.035), below + V3(0, -0.18, 0), V3(0, 0, 45), g, gm))
	elseif kind == "bolt" then
		table.insert(t, p("Block", "chest", V3(0.06, 0.2, 0.03), below + V3(0.03, -0.12, 0), V3(0, 0, -20), g, gm))
		table.insert(t, p("Block", "chest", V3(0.06, 0.2, 0.03), below + V3(-0.02, -0.26, 0), V3(0, 0, -20), g, gm))
	elseif kind == "lock" then
		table.insert(t, p("Block", "chest", V3(0.2, 0.16, 0.06), below + V3(0, -0.2, 0), nil, g, gm))
		table.insert(t, cylZ("chest", 0.03, 0.14, below + V3(0, -0.1, 0), "c1", { m = MET }))
	elseif kind == "dogtags" then
		table.insert(t, p("Block", "chest", V3(0.12, 0.2, 0.015), below + V3(-0.02, -0.12, 0), V3(0, 0, 8), "c1", { m = MET, refl = 0.2 }))
		table.insert(t, p("Block", "chest", V3(0.12, 0.2, 0.015), below + V3(0.03, -0.15, -0.01), V3(0, 0, -6), "c1", { m = MET, refl = 0.2 }))
	elseif kind == "piece" then -- a big iced square piece
		table.insert(t, p("Block", "chest", V3(0.36, 0.36, 0.05), below + V3(0, -0.2, 0), nil, "c1", { m = MET, refl = 0.3 }))
		for i = -1, 1 do
			for j = -1, 1 do
				table.insert(t, p("Ball", "chest", V3(0.09, 0.09, 0.04), below + V3(i * 0.1, -0.2 + j * 0.1, -0.03), nil, "c2", { m = GLA, refl = 0.5, spark = (i == 0 and j == 0) }))
			end
		end
	elseif kind == "money" then -- a money bag
		table.insert(t, p("Ball", "chest", V3(0.24, 0.26, 0.12), below + V3(0, -0.2, 0), nil, g, gm))
		table.insert(t, p("Ball", "chest", V3(0.1, 0.08, 0.08), below + V3(0, -0.07, 0), nil, g, gm))
	elseif kind == "letter" then -- a big iced initial / name plate
		table.insert(t, p("Block", "chest", V3(0.34, 0.34, 0.05), below + V3(0, -0.2, 0), nil, "c1", { m = MET, refl = 0.3, t = 0.0 }))
		table.insert(t, p("Block", "chest", V3(0.32, 0.32, 0.01), below + V3(0, -0.2, -0.03), nil, "c2", { m = GLA, refl = 0.5, t = 1, spark = true, txt = { text = x.letter or "N", color = "c2", face = "Front" } }))
	elseif kind == "palm" then -- a palm tree (Neon Coast)
		table.insert(t, p("Block", "chest", V3(0.04, 0.24, 0.03), below + V3(0, -0.2, 0), V3(0, 0, 6), g, gm))
		for i = 0, 4 do
			table.insert(t, p("Block", "chest", V3(0.16, 0.03, 0.03), below + V3(math.cos(rad(i * 45)) * 0.06, -0.08 + math.sin(rad(i * 45)) * 0.03, 0), V3(0, 0, i * 45 - 90), g, gm))
		end
	end
	return t
end

F.chain = function(pp)
	local drop = pp.drop or 0.6
	local pts, low = chainPath(drop, pp.n or 9, pp.spread)
	local style = pp.style or "cuban"
	local c = pp.iced and "c2" or "c1"
	local x = pp.iced and { m = GLA, refl = 0.45 } or { m = MET, refl = 0.3 }
	if style == "pearl" then
		x = { m = SMO, refl = 0.15 }
	elseif style == "puka" then
		x = { m = SMO }
	end
	local t = along("chest", pts, (style == "pearl" or style == "puka") and "c1" or c, style, pp.w or 0.06, x)
	if pp.iced and #t > 0 then
		t[math.floor(#t / 2)].spark = true
		t[1].spark = true
	end
	if pp.pendant then
		add(t, pendant(pp.pendant, low, pp))
	end
	if pp.layer then -- a second, shorter chain (layered look)
		local pts2 = chainPath(drop * 0.6, 7, (pp.spread or 0.3) * 0.95)
		add(t, along("chest", pts2, c, pp.layer, (pp.w or 0.06) * 0.8, x))
	end
	return t
end
F.choker = function(pp)
	return ring("neck", V3(0, -0.02, 0.06), 0.33, 16, pp.studs and "Ball" or "Block", "c1", "Y", { m = pp.studs and MET or LEA }, pp.studs and V3(0.06, 0.06, 0.06) or V3(0.05, 0.1, 0.16))
end
F.tie = function(pp)
	local t = {
		p("Block", "chest", V3(0.13, 0.11, 0.06), V3(0, 0.7, -0.08), nil, "c1", { m = FAB }),
	}
	if pp.bow then
		add(t, mirror({ p("Wedge", "chest", V3(0.04, 0.12, 0.16), V3(0.09, 0.7, -0.09), V3(0, -90, 0), "c1", { m = FAB }) }))
	else
		table.insert(t, p("Block", "chest", V3(0.15, 0.85, 0.03), V3(0, 0.22, -0.07), V3(-4, 0, 0), "c1", { m = FAB }))
		table.insert(t, p("Block", "chest", V3(0.15, 0.1, 0.03), V3(0, -0.24, -0.08), V3(0, 0, 45), "c1", { m = FAB }))
	end
	return t
end
F.scarf = function()
	local t = {
		cylY("neck", 0.3, 0.72, V3(0, 0.0, 0.06), "c1", { m = FAB }),
		p("Block", "chest", V3(0.24, 0.85, 0.07), V3(0.14, 0.25, -0.1), V3(-5, 0, 4), "c1", { m = FAB }),
		p("Block", "chest", V3(0.24, 0.6, 0.07), V3(-0.14, 0.35, -0.12), V3(-5, 0, -4), "c2", { m = FAB }),
	}
	return t
end

------------------------------------------------------------------ grillz (frame "head")
F.grillz = function(pp)
	local t = {}
	local function row(y, n, h)
		for i = 1, n do
			local a = rad((i - (n + 1) / 2) * (80 / n))
			local pos = V3(math.sin(a) * 0.55, y, FACE.mouthZ + 0.53 - math.cos(a) * 0.55)
			local key = pp.iced and "c2" or "c1"
			if pp.fang and (i == 2 or i == n - 1) then
				h = h * 1.5
			end
			local q = p("Block", "head", V3(0.105, h, 0.05), pos, V3(0, math.deg(a), 0), key, pp.iced and { m = GLA, refl = 0.5 } or { m = MET, refl = 0.35 })
			if pp.iced and i == math.ceil(n / 2) then
				q.spark = true
			end
			if pp.gap and i == math.ceil(n / 2) then
				q.c = "tooth"
				q.m = SMO
			end
			table.insert(t, q)
		end
	end
	row(FACE.mouthY + 0.06, pp.top or 6, 0.12)
	if (pp.bottom or 0) > 0 then
		row(FACE.mouthY - 0.07, pp.bottom, 0.1)
	end
	return t
end

------------------------------------------------------------------ earrings (frame "head")
F.earrings = function(pp)
	local lobe = V3(FACE.earX + 0.03, FACE.lobeY, FACE.earZ)
	local t = {}
	local kind = pp.kind or "stud"
	if kind == "stud" then
		table.insert(t, p("Ball", "head", V3(pp.size or 0.14, pp.size or 0.14, pp.size or 0.14), lobe, nil, "c2", { m = GLA, refl = 0.5, spark = true }))
	elseif kind == "hoop" then
		add(t, ring("head", lobe + V3(0.02, -(pp.size or 0.22), 0), pp.size or 0.22, 12, "Cyl", "c1", "X", { m = MET, refl = 0.35 }, V3(0.12, 0.04, 0.04)))
	elseif kind == "cross" then
		table.insert(t, p("Block", "head", V3(0.03, 0.24, 0.03), lobe + V3(0.02, -0.14, 0), nil, "c1", { m = MET, refl = 0.3 }))
		table.insert(t, p("Block", "head", V3(0.03, 0.03, 0.14), lobe + V3(0.02, -0.08, 0), nil, "c1", { m = MET, refl = 0.3 }))
	elseif kind == "pearl" then
		table.insert(t, p("Ball", "head", V3(0.15, 0.15, 0.15), lobe + V3(0.02, -0.08, 0), nil, "pearl", { m = SMO, refl = 0.15 }))
	elseif kind == "dangle" then
		table.insert(t, p("Block", "head", V3(0.03, 0.3, 0.03), lobe + V3(0.02, -0.15, 0), nil, "c1", { m = MET }))
		table.insert(t, p("Block", "head", V3(0.03, 0.14, 0.14), lobe + V3(0.02, -0.34, 0), V3(45, 0, 0), "c2", { m = GLA, refl = 0.5, spark = true }))
	end
	if pp.one then
		return t
	end
	return mirror(t)
end

------------------------------------------------------------------ wrists, hands (frames "LWrist"/"RWrist"/"LHand"/"RHand")
F.watch = function(pp)
	local f = pp.right and "RWrist" or "LWrist"
	local side = pp.right and 1 or -1
	local t = {
		cylY(f, 0.28, 1.14, V3(0, 0, 0), pp.iced and "c2" or "c1", pp.iced and { m = GLA, refl = 0.45 } or { m = pp.smart and RUB or MET, refl = 0.3 }),
	}
	if pp.smart then
		table.insert(t, p("Block", f, V3(0.12, 0.45, 0.4), V3(side * 0.56, 0, 0), nil, "black", { m = GLA, refl = 0.3 }))
		table.insert(t, p("Block", f, V3(0.02, 0.36, 0.3), V3(side * 0.63, 0, 0), nil, "c2", { glow = true, m = NEO }))
	else
		table.insert(t, p("Cyl", f, V3(0.12, 0.55, 0.55), V3(side * 0.56, 0, 0), nil, "c1", { m = MET, refl = 0.3 }))
		table.insert(t, p("Cyl", f, V3(0.06, 0.42, 0.42), V3(side * 0.62, 0, 0), nil, pp.iced and "c2" or "dial", { m = pp.iced and GLA or SMO, refl = 0.3, spark = pp.iced }))
	end
	return t
end
F.bracelet = function(pp)
	local f = pp.left and "LWrist" or "RWrist"
	local c = pp.iced and "c2" or "c1"
	local x = pp.iced and { m = GLA, refl = 0.45 } or { m = MET, refl = 0.3 }
	local t = ring(f, V3(0, 0.05, 0), 0.56, pp.n or 12, pp.beads and "Ball" or "Block", c, "Y", x, pp.beads and V3(0.16, 0.16, 0.16) or V3(0.14, 0.12, 0.34))
	if pp.iced then
		t[1].spark = true
	end
	if pp.both then
		local t2 = ring(pp.left and "RWrist" or "LWrist", V3(0, 0.05, 0), 0.56, pp.n or 12, pp.beads and "Ball" or "Block", c, "Y", x, pp.beads and V3(0.16, 0.16, 0.16) or V3(0.14, 0.12, 0.34))
		add(t, t2)
	end
	return t
end
F.rings = function(pp)
	local t = {}
	for i = 1, (pp.n or 2) do
		table.insert(t, cylY("RHand", 0.08, 0.32, V3(0.1 - i * 0.12, -0.3, -0.05), pp.iced and "c2" or "c1", pp.iced and { m = GLA, refl = 0.5, spark = (i == 1) } or { m = MET, refl = 0.35, fit = true }))
	end
	if pp.both then
		t = mirror(t)
	end
	for _, q in ipairs(t) do
		q.fit = true
	end
	return t
end
F.gloves = function(pp)
	local t = mirror({ cylY("RWrist", 0.3, 1.2, V3(0, 0.05, 0), "c1", { m = pp.leather and LEA or FAB }) })
	return t, { Hand = { c = "c1", m = pp.leather and LEA or FAB } }
end

------------------------------------------------------------------ back and waist (frames "back", "chest", "hips")
F.backpack = function(pp)
	local t = {
		p("Block", "back", V3(0.9, 1.05, 0.42), V3(0, -0.15, 0.24), nil, "c1", { m = FAB }),
		p("Block", "back", V3(0.8, 0.4, 0.15), V3(0, -0.4, 0.5), nil, "c2", { m = FAB }),
	}
	add(t, mirror({ p("Block", "chest", V3(0.1, 0.9, 0.04), V3(0.28, 0.3, -0.02), V3(-6, 0, 0), "c1", { m = FAB }) }))
	if pp.mini then
		for _, q in ipairs(t) do
			if q.f == "back" then
				q.s = q.s * 0.65
			end
		end
	end
	return t
end
F.duffel = function()
	-- a heist duffel slung across the back, strap across the chest
	local t = {
		p("Cyl", "back", V3(1.25, 0.6, 0.6), V3(0, -0.35, 0.36), V3(0, 0, 25), "c1", { m = FAB }),
		p("Block", "back", V3(1.1, 0.06, 0.04), V3(0, -0.12, 0.66), V3(0, 0, 25), "c2", { m = MET }),
		p("Block", "chest", V3(0.1, 1.5, 0.04), V3(0, 0.1, -0.03), V3(0, 0, 35), "c1", { m = FAB }),
	}
	return t
end
F.sling = function()
	return {
		p("Block", "chest", V3(0.1, 1.5, 0.04), V3(0, 0.1, -0.03), V3(0, 0, -38), "c1", { m = FAB }),
		p("Block", "chest", V3(0.5, 0.3, 0.16), V3(0.12, 0.1, -0.1), V3(0, 0, -38), "c1", { m = FAB }),
		p("Block", "chest", V3(0.46, 0.03, 0.02), V3(0.12, 0.13, -0.19), V3(0, 0, -38), "c2", { m = MET }),
	}
end
F.cape = function(pp)
	local l = pp.len or 2.6
	return {
		p("Block", "back", V3(1.35, l, 0.05), V3(0, 0.55 - l / 2, 0.14), V3(-6, 0, 0), "c1", { m = FAB }),
		p("Block", "back", V3(1.4, 0.15, 0.25), V3(0, 0.6, 0.06), nil, "c2", { m = FAB }),
	}
end
F.wings = function(pp)
	local t = {}
	for i = 1, 3 do
		add(t, mirror({ p("Wedge", "back", V3(0.06, 1.2 - i * 0.15, 0.9 + i * 0.2), V3(0.45 + i * 0.35, 0.25 - i * 0.15, 0.35), V3(0, -100, 25 + i * 10), i == 1 and "c2" or "c1", { m = pp.neon and NEO or FAB }) }))
	end
	return t
end
F.jetpack = function()
	local t = { p("Block", "back", V3(0.6, 0.8, 0.3), V3(0, -0.1, 0.25), nil, "c1", { m = MET, refl = 0.2 }) }
	add(t, mirror({
		cylY("back", 1.1, 0.42, V3(0.4, -0.1, 0.35), "c1", { m = MET, refl = 0.25 }),
		cylY("back", 0.15, 0.3, V3(0.4, -0.72, 0.35), "c2", { m = NEO }),
	}))
	return t
end
F.guitar = function()
	return {
		p("Ball", "back", V3(0.9, 1.1, 0.3), V3(0.1, -0.55, 0.3), V3(0, 0, 20), "c1", { m = SMO }),
		p("Block", "back", V3(0.14, 1.4, 0.12), V3(-0.2, 0.4, 0.3), V3(0, 0, 20), "c2", { m = SMO }),
	}
end
F.sword = function()
	return {
		p("Block", "back", V3(0.1, 2.0, 0.06), V3(0, -0.1, 0.25), V3(0, 0, 30), "c1", { m = LEA }),
		p("Block", "back", V3(0.08, 0.5, 0.08), V3(-0.53, 0.85, 0.25), V3(0, 0, 30), "c2", { m = FAB }),
		cylY("back", 0.04, 0.24, V3(-0.4, 0.62, 0.25), "gold", { m = MET }, 0),
	}
end
F.belt = function(pp)
	local t = ring("hips", V3(0, 0.25, 0), 0.62, 18, "Block", "c1", "Y", { m = LEA }, V3(0.05, 0.14, 0.24))
	for _, q in ipairs(t) do -- flatten the ring to the hips' oval
		local pos = q.lcf.Position
		q.lcf = CFrame.new(pos.X * 1.05, pos.Y, pos.Z * 0.7) * (q.lcf - pos)
	end
	table.insert(t, p("Block", "hips", V3(pp.big and 0.32 or 0.16, pp.big and 0.2 or 0.13, 0.04), V3(0, 0.25, -0.46), nil, "c2", { m = MET, refl = 0.35, spark = pp.iced }))
	return t
end
F.pocketbandana = function()
	return { p("Wedge", "hips", V3(0.03, 0.5, 0.3), V3(0.35, -0.2, 0.46), V3(180, 90, 0), "c1", { m = FAB }) }
end
F.beltbag = function()
	return {
		p("Block", "hips", V3(0.6, 0.3, 0.22), V3(0.15, 0.25, -0.55), nil, "c1", { m = FAB }),
		p("Block", "hips", V3(0.56, 0.03, 0.02), V3(0.15, 0.3, -0.67), nil, "c2", { m = MET }),
	}
end
F.utility = function()
	local t = F.belt({})
	for i = -2, 2 do
		table.insert(t, p("Block", "hips", V3(0.18, 0.2, 0.12), V3(i * 0.24, 0.18, -0.5 + math.abs(i) * 0.07), nil, "c1", { m = FAB }))
	end
	return t
end
F.walletchain = function()
	local pts = bezier(V3(0.35, 0.25, -0.45), V3(0.6, -0.35, -0.3), V3(0.6, 0.1, 0.25), 8)
	return along("hips", pts, "c1", "cuban", 0.05, { m = MET, refl = 0.3 })
end

------------------------------------------------------------------ tops (body + details on "chest"/"neck"/"back")
local SLEEVE = {
	tank = { Torso = "c1", UArm = "skin", LArm = "skin" },
	tee = { Torso = "c1", UArm = "c1", LArm = "skin" },
	long = { Torso = "c1", UArm = "c1", LArm = "c1" },
}
local function bodyOf(sleeve, m)
	local b = {}
	for k, v in pairs(SLEEVE[sleeve or "tee"]) do
		b[k] = (v == "skin") and "skin" or { c = v, m = m or FAB }
	end
	return b
end
local function collarRing(c, h, d)
	return cylY("neck", h or 0.07, d or 0.62, V3(0, -0.02, 0.06), c or "dark", { m = FAB })
end
local function textPlate(f, text, o, size, color, face, rot)
	return p("Block", f, size or V3(0.7, 0.34, 0.02), o, rot, "c1", { t = 1, txt = { text = text, color = color or "c2", face = face or "Front" } })
end

local function camo(n, seed)
	-- irregular blotches over the chest, back and sleeves (camo prints, splatter, tie-dye)
	local out = {}
	for i = 1, n do
		local k = (i * 7919 + (seed or 0) * 104729) % 1000
		local x = ((k % 10) - 4.5) * 0.11
		local y = (math.floor(k / 10) % 10 - 4.5) * 0.13
		local sz = 0.18 + (k % 7) * 0.035
		local key = (i % 3 == 0) and "dark" or "c2"
		table.insert(out, p("Ball", (i % 2 == 0) and "chest" or "back", V3(sz * 1.5, sz, 0.03), V3(x, y, (i % 2 == 0) and -0.035 or 0.035), V3(0, 0, (k % 90) - 45), key, { m = FAB }))
		if i % 4 == 0 then
			table.insert(out, p("Ball", (i % 8 == 0) and "RUpperArm" or "LUpperArm", V3(0.5, 0.35, 0.04), V3((i % 8 == 0) and 0.5 or -0.5, y * 0.4, 0), V3(0, 90, 0), key, { m = FAB, fit = true }))
		end
	end
	return out
end
B.camo = camo

F.tee = function(pp)
	local t = { collarRing("dark") }
	if pp.text then
		table.insert(t, textPlate("chest", pp.text, V3(0, 0.08, -0.04), V3(0.75, 0.38, 0.02), "c2"))
	end
	if pp.pocket then
		table.insert(t, p("Block", "chest", V3(0.2, 0.22, 0.02), V3(0.22, 0.32, -0.035), nil, "c2", { m = FAB }))
	end
	if pp.stripe then
		table.insert(t, p("Block", "chest", V3(1.05, 0.14, 0.02), V3(0, 0.15, -0.035), nil, "c2", { m = FAB }))
	end
	return t, bodyOf(pp.sleeve or "tee")
end
F.hoodie = function(pp)
	local t = {
		p("Ball", "neck", V3(1.0, 0.5, 0.6), V3(0, -0.02, 0.42), nil, "c1", { m = FAB }),
		p("Block", "chest", V3(0.8, 0.32, 0.03), V3(0, -0.5, -0.04), nil, "dark", { m = FAB }),
	}
	add(t, mirror({ cylY("chest", 0.45, 0.04, V3(0.12, 0.45, -0.05), "c2", { m = FAB }) }))
	if pp.zip then
		table.insert(t, p("Block", "chest", V3(0.04, 1.4, 0.03), V3(0, 0.05, -0.045), nil, "silver", { m = MET }))
	end
	if pp.text then
		table.insert(t, textPlate("chest", pp.text, V3(0, 0.1, -0.05), V3(0.75, 0.3, 0.02), "c2"))
	end
	if pp.camo then
		add(t, camo(pp.camo, 3))
	end
	if pp.puff then -- a big puff-print graphic across the chest
		table.insert(t, p("Block", "chest", V3(0.7, 0.5, 0.025), V3(0, 0.1, -0.045), nil, "c2", { m = FAB }))
		table.insert(t, p("Block", "chest", V3(0.5, 0.3, 0.03), V3(0, 0.1, -0.05), nil, "dark", { m = FAB }))
	end
	return t, bodyOf("long")
end
F.sweater = function(pp)
	local t = { collarRing("dark", 0.1, 0.64) }
	if pp.chunky then
		for i = -2, 2 do
			table.insert(t, p("Block", "chest", V3(0.06, 1.2, 0.03), V3(i * 0.2, 0.0, -0.04), nil, "dark", { m = FAB }))
		end
	end
	if pp.vneck then
		add(t, mirror({ p("Wedge", "chest", V3(0.02, 0.3, 0.16), V3(0.08, 0.6, -0.04), V3(180, -90, 0), "under", { m = FAB }) }))
	end
	if pp.qzip then -- quarter-zip: a stand collar and a short zip
		t[1] = cylY("neck", 0.22, 0.66, V3(0, 0.04, 0.06), "c1", { m = FAB })
		table.insert(t, p("Block", "chest", V3(0.035, 0.45, 0.03), V3(0, 0.55, -0.05), nil, "silver", { m = MET }))
	end
	if pp.turtle then
		t[1] = cylY("neck", 0.38, 0.64, V3(0, 0.12, 0.06), "c1", { m = FAB })
	end
	return t, bodyOf("long")
end
F.shirt = function(pp)
	local t = {
		p("Block", "chest", V3(0.1, 1.4, 0.025), V3(0, 0.05, -0.04), nil, pp.placket or "c1", { m = FAB }),
	}
	add(t, mirror({ p("Wedge", "neck", V3(0.03, 0.2, 0.18), V3(0.13, -0.08, -0.25), V3(150, -90, 0), "c2", { m = FAB }) }))
	for i = 0, 3 do
		table.insert(t, p("Ball", "chest", V3(0.04, 0.04, 0.02), V3(0, 0.55 - i * 0.35, -0.055), nil, "white", { m = SMO }))
	end
	if pp.open then -- open collar over a white undershirt
		table.insert(t, p("Wedge", "chest", V3(0.24, 0.3, 0.02), V3(0, 0.62, -0.05), V3(180, 0, 0), "white", { m = FAB }))
	end
	if pp.print then -- a few blooms on a resort / Hawaiian shirt
		for i = 1, 6 do
			table.insert(t, p("Ball", "chest", V3(0.12, 0.12, 0.02), V3(((i * 37) % 9 - 4) * 0.1, ((i * 53) % 7 - 3) * 0.17, -0.04), nil, "c2", { m = FAB }))
		end
	end
	return t, bodyOf(pp.sleeve or "long")
end
F.polo = function(pp)
	local t = {
		p("Block", "chest", V3(0.12, 0.35, 0.025), V3(0, 0.6, -0.04), nil, "c1", { m = FAB }),
	}
	add(t, mirror({ p("Wedge", "neck", V3(0.03, 0.18, 0.18), V3(0.13, -0.08, -0.25), V3(150, -90, 0), "c2", { m = FAB }) }))
	return t, bodyOf("tee")
end
F.jersey = function(pp)
	local t = {
		textPlate("chest", pp.num or "23", V3(0, 0.05, -0.04), V3(0.6, 0.55, 0.02), "c2"),
		textPlate("back", pp.num or "23", V3(0, 0.05, 0.04), V3(0.6, 0.55, 0.02), "c2", "Back"),
		collarRing("c2", 0.06, 0.66),
	}
	if pp.sleeve == "long" then -- hockey stripes
		add(t, mirror({ cylY("RLowerArm", 0.18, 1.12, V3(0, -0.1, 0), "c2", { m = FAB }) }))
	end
	return t, bodyOf(pp.sleeve or "tank")
end
F.croptop = function(pp)
	local t = { collarRing("c1", 0.05, 0.6) }
	if pp.bow then
		add(t, mirror({ p("Wedge", "chest", V3(0.03, 0.1, 0.14), V3(0.07, 0.62, -0.06), V3(0, -90, 0), "c2", { m = SMO }) }))
	end
	return t, { Torso = { c = "c1", m = FAB }, UArm = pp.sleeve and { c = "c1", m = FAB } or "skin", LArm = "skin" }
end
F.corset = function()
	local t = {}
	for i = 0, 4 do
		table.insert(t, p("Block", "chest", V3(0.24, 0.02, 0.02), V3(0, 0.2 - i * 0.16, -0.045), V3(0, 0, (i % 2 == 0) and 25 or -25), "c2", { m = FAB }))
	end
	add(t, mirror({ p("Block", "chest", V3(0.05, 0.4, 0.04), V3(0.32, 0.88, 0.0), nil, "c1", { m = FAB }) }))
	return t, { Torso = { c = "c1", m = FAB }, UArm = { c = "c1", m = FAB }, LArm = "skin" }
end
F.vest = function(pp)
	-- a tactical vest / plate carrier over whatever top is worn (keeps the top's sleeves)
	local t = {
		p("Block", "chest", V3(1.0, 1.05, 0.2), V3(0, 0.05, -0.04), nil, "c1", { m = FAB }),
		p("Block", "back", V3(1.0, 1.05, 0.2), V3(0, 0.05, 0.04), nil, "c1", { m = FAB }),
	}
	add(t, mirror({ p("Block", "neck", V3(0.18, 0.12, 1.05), V3(0.3, -0.06, 0.06), nil, "c1", { m = FAB }) }))
	for i = -1, 1 do
		table.insert(t, p("Block", "chest", V3(0.24, 0.3, 0.14), V3(i * 0.28, -0.3, -0.18), nil, "dark", { m = FAB }))
	end
	if pp.text then
		table.insert(t, textPlate("back", pp.text, V3(0, 0.25, 0.15), V3(0.8, 0.22, 0.02), "c2", "Back"))
		table.insert(t, textPlate("chest", pp.text, V3(0, 0.3, -0.15), V3(0.5, 0.14, 0.02), "c2"))
	end
	if pp.suit then -- a suit waistcoat instead (no pouches, buttons)
		t = {
			p("Block", "chest", V3(0.95, 0.95, 0.06), V3(0, 0.0, -0.035), nil, "c1", { m = FAB }),
			p("Wedge", "chest", V3(0.3, 0.4, 0.02), V3(0, 0.55, -0.07), V3(180, 0, 0), "under", { m = FAB }),
		}
		for i = 0, 3 do
			table.insert(t, p("Ball", "chest", V3(0.04, 0.04, 0.02), V3(0, 0.3 - i * 0.2, -0.075), nil, "c2", { m = MET }))
		end
	end
	return t
end
F.overalls = function()
	local t = {
		p("Block", "chest", V3(0.6, 0.6, 0.04), V3(0, -0.15, -0.04), nil, "c1", { m = FAB }),
	}
	add(t, mirror({
		p("Block", "chest", V3(0.08, 0.7, 0.04), V3(0.24, 0.45, -0.04), nil, "c1", { m = FAB }),
		p("Ball", "chest", V3(0.06, 0.06, 0.03), V3(0.24, 0.16, -0.07), nil, "brass", { m = MET }),
		p("Block", "back", V3(0.08, 1.0, 0.04), V3(0.18, 0.1, 0.04), V3(0, 0, 10), "c1", { m = FAB }),
	}))
	return t, { Hips = { c = "c1", m = FAB }, ULeg = { c = "c1", m = FAB }, LLeg = { c = "c1", m = FAB } }
end
F.jumpsuit = function(pp)
	-- coveralls, prison orange, flight suits, scrubs, spacesuits: one colour head to toe (but the hands and head)
	local m = pp.m == "leather" and LEA or (pp.m == "smooth" and SMO or FAB)
	local t = { p("Block", "chest", V3(0.04, 1.4, 0.025), V3(0, -0.05, -0.045), nil, pp.zip or "c2", { m = MET }) }
	add(t, mirror({ p("Wedge", "neck", V3(0.03, 0.18, 0.2), V3(0.14, -0.08, -0.25), V3(150, -90, 0), "c1", { m = m }) }))
	if pp.text then
		table.insert(t, textPlate("back", pp.text, V3(0, 0.25, 0.05), V3(0.9, 0.25, 0.02), "c2", "Back"))
	end
	if pp.patches then
		add(t, mirror({ p("Block", "LUpperArm", V3(0.5, 0.4, 0.04), V3(-0.52, 0.1, 0), V3(0, 90, 0), "c2", { m = FAB }) }))
	end
	if pp.space then -- life-support pack, collar ring, hose
		table.insert(t, p("Block", "back", V3(0.95, 1.1, 0.45), V3(0, -0.05, 0.25), nil, "c1", { m = SMO }))
		table.insert(t, cylY("neck", 0.2, 0.95, V3(0, -0.02, 0.06), "c2", { m = MET }))
		table.insert(t, p("Block", "chest", V3(0.5, 0.35, 0.12), V3(0, -0.25, -0.1), nil, "c2", { m = SMO }))
	end
	local b = { Torso = { c = "c1", m = m }, UArm = { c = "c1", m = m }, LArm = { c = "c1", m = m }, Hips = { c = "c1", m = m },
		ULeg = { c = "c1", m = m }, LLeg = { c = "c1", m = m } }
	if pp.shortSleeve then
		b.LArm = "skin"
	end
	return t, b
end
F.armor = function(pp)
	-- bronze cuirass (ancient Greek / Mediterranean epic), knight plate or sci-fi trooper armour
	local mm = pp.scifi and SMO or MET
	local t = {
		p("Block", "chest", V3(1.05, 1.1, 0.18), V3(0, 0.0, -0.04), nil, "c1", { m = mm, refl = pp.scifi and 0.05 or 0.2 }),
		p("Block", "back", V3(1.05, 1.1, 0.18), V3(0, 0.0, 0.04), nil, "c1", { m = mm, refl = pp.scifi and 0.05 or 0.2 }),
	}
	add(t, mirror({ p("Ball", "RUpperArm", V3(1.5, 0.9, 1.5), V3(0, 0.3, 0), nil, "c1", { m = mm, refl = 0.2 }) }))
	if pp.skirt then -- pteruges: leather strips round the hips
		for i = 0, 9 do
			local a = i / 10 * math.pi * 2
			table.insert(t, p("Block", "hips", V3(0.2, 0.75, 0.05), V3(math.sin(a) * 0.6, -0.3, math.cos(a) * 0.42), V3(0, math.deg(a), 0), "c2", { m = LEA }))
		end
	end
	if pp.scifi then
		table.insert(t, p("Block", "chest", V3(0.5, 0.05, 0.02), V3(0, 0.3, -0.14), nil, "neon", { m = NEO }))
		add(t, mirror({ p("Block", "RLowerLeg", V3(1.2, 0.8, 1.2), V3(0, 0.1, 0), nil, "c1", { m = SMO }) }))
	end
	return t, { UArm = { c = pp.under or "c2", m = FAB }, LArm = { c = "c2", m = FAB } }
end
F.robe = function(pp)
	local l = pp.len or 2.4
	local t = {}
	for i = 0, 11 do
		local a = i / 12 * math.pi * 2
		table.insert(t, p("Block", "hips", V3(0.36, l, 0.05), V3(math.sin(a) * 0.62, 0.1 - l / 2, math.cos(a) * 0.48), V3(math.cos(a) * -6, math.deg(a), 0), "c1", { m = FAB }))
	end
	if pp.belt then
		table.insert(t, cylY("hips", 0.12, 1.28, V3(0, 0.2, 0), "c2", { m = FAB }))
	end
	if pp.hood then
		table.insert(t, p("Ball", "neck", V3(1.1, 0.55, 0.7), V3(0, -0.02, 0.42), nil, "c1", { m = FAB }))
	end
	return t, { Torso = { c = "c1", m = FAB }, UArm = { c = "c1", m = FAB }, LArm = { c = "c1", m = FAB }, Hips = { c = "c1", m = FAB } }
end
F.dress = function(pp)
	local l = pp.len or 1.4
	local t = {}
	for i = 0, 11 do
		local a = i / 12 * math.pi * 2
		local flare = pp.flare or 10
		table.insert(t, p("Block", "hips", V3(0.36, l, 0.04), V3(math.sin(a) * 0.62, 0.1 - l / 2, math.cos(a) * 0.48), V3(-flare * math.cos(0), math.deg(a), 0), "c1", { m = pp.sequin and Enum.Material.Foil or FAB, refl = pp.sequin and 0.2 or 0 }))
	end
	return t, { Torso = { c = "c1", m = pp.sequin and Enum.Material.Foil or FAB }, UArm = pp.sleeve and { c = "c1", m = FAB } or "skin", LArm = "skin",
		Hips = { c = "c1", m = FAB }, ULeg = "skin", LLeg = "skin" }
end

------------------------------------------------------------------ outerwear (over the top)
local function lapels(c, deep)
	return mirror({ p("Wedge", "chest", V3(0.03, deep or 0.65, 0.22), V3(0.11, 0.42, -0.06), V3(180, -90, 0), c, { m = FAB }) })
end
local function openFront(w, c)
	return p("Block", "chest", V3(w or 0.3, 1.25, 0.02), V3(0, 0.05, -0.04), nil, c or "under", { m = FAB })
end
F.blazer = function(pp)
	local t = { openFront(0.28, "under") }
	add(t, lapels(pp.satin and "c2" or "dark", 0.7))
	for i = 0, (pp.double and 3 or 1) do
		local col = pp.double and ((i % 2 == 0) and -0.12 or 0.12) or 0.17
		table.insert(t, p("Ball", "chest", V3(0.05, 0.05, 0.02), V3(col, -0.15 - math.floor(i / (pp.double and 2 or 1)) * 0.25, -0.05), nil, pp.brass and "brass" or "dark", { m = pp.brass and MET or SMO }))
	end
	table.insert(t, p("Block", "chest", V3(0.16, 0.07, 0.02), V3(0.3, 0.45, -0.045), nil, "c2", { m = FAB })) -- pocket square
	return t, { Torso = { c = "c1", m = FAB }, UArm = { c = "c1", m = FAB }, LArm = { c = "c1", m = FAB } }
end
F.jacket = function(pp)
	-- denim, bomber, moto, field, track, racing, varsity, windbreaker, flannel, suede: one family with options
	local m = (pp.m == "leather" and LEA) or (pp.m == "smooth" and SMO) or FAB
	local t = {}
	if pp.open ~= false then
		table.insert(t, openFront(pp.openW or 0.26, "under"))
	end
	if pp.collar == "lapel" then
		add(t, lapels(pp.collarC or "dark", 0.45))
	elseif pp.collar == "rib" then
		table.insert(t, cylY("neck", 0.14, 0.68, V3(0, -0.01, 0.06), pp.collarC or "c2", { m = FAB }))
	elseif pp.collar == "funnel" then
		table.insert(t, cylY("neck", 0.4, 0.74, V3(0, 0.1, 0.06), "c1", { m = m }))
	elseif pp.collar == "fur" then
		for i = 0, 7 do
			local a = rad(-110 + i * 31)
			table.insert(t, p("Ball", "neck", V3(0.32, 0.3, 0.32), V3(math.sin(a) * 0.36, -0.04, -math.cos(a) * 0.34 + 0.06), nil, pp.collarC or "c2", { m = FAB }))
		end
	elseif pp.collar == "stand" then
		table.insert(t, cylY("neck", 0.2, 0.7, V3(0, 0.02, 0.06), pp.collarC or "c1", { m = m }))
	elseif pp.collar == "hood" then
		table.insert(t, p("Ball", "neck", V3(1.0, 0.5, 0.6), V3(0, -0.02, 0.42), nil, "c1", { m = m }))
	end
	if pp.zip then
		local zx = pp.zip == "diag" and 0.12 or 0
		table.insert(t, p("Block", "chest", V3(0.035, 1.3, 0.03), V3(zx, 0.0, -0.05), V3(0, 0, pp.zip == "diag" and -12 or 0), "silver", { m = MET }))
	end
	if pp.cuffs then
		add(t, mirror({ cylY("RLowerArm", 0.16, 1.12, V3(0, -0.42, 0), pp.cuffC or "c2", { m = FAB }) }))
	end
	if pp.stripes then -- stripes down the sleeves
		add(t, mirror({
			p("Block", "RUpperArm", V3(0.08, 1.0, 0.1), V3(0.52, 0, 0), nil, "c2", { m = FAB, fit = true }),
			p("Block", "RLowerArm", V3(0.08, 1.0, 0.1), V3(0.52, 0, 0), nil, "c2", { m = FAB, fit = true }),
		}))
	end
	if pp.pockets then
		add(t, mirror({ p("Block", "chest", V3(0.24, 0.22, 0.03), V3(0.25, 0.3, -0.05), nil, "dark", { m = m }) }))
	end
	if pp.puffer then
		for i = 0, 3 do
			table.insert(t, p("Block", "chest", V3(1.05, 0.08, 0.06), V3(0, 0.55 - i * 0.35, -0.04), nil, "dark", { m = SMO }))
			table.insert(t, p("Block", "back", V3(1.05, 0.08, 0.06), V3(0, 0.55 - i * 0.35, 0.04), nil, "dark", { m = SMO }))
		end
		table.insert(t, p("Block", "chest", V3(1.12, 1.4, 0.16), V3(0, 0, -0.02), nil, "c1", { m = SMO }))
		table.insert(t, p("Block", "back", V3(1.12, 1.4, 0.16), V3(0, 0, 0.02), nil, "c1", { m = SMO }))
		add(t, mirror({ p("Ball", "RUpperArm", V3(1.35, 1.0, 1.35), V3(0, 0, 0), nil, "c1", { m = SMO }) }))
		m = SMO
	end
	if pp.fur then -- a full statement fur coat
		for i = 0, 5 do
			add(t, mirror({ p("Ball", "chest", V3(0.36, 0.4, 0.2), V3(0.3 + (i % 2) * 0.1, 0.5 - i * 0.22, -0.08), nil, "c1", { m = FAB }) }))
		end
		add(t, mirror({ cylY("RLowerArm", 0.4, 1.35, V3(0, -0.38, 0), "c1", { m = FAB }) }))
	end
	if pp.letter then
		table.insert(t, textPlate("chest", pp.letter, V3(0.27, 0.32, -0.06), V3(0.3, 0.3, 0.02), "c2"))
	end
	if pp.camo then
		add(t, camo(pp.camo, 5))
	end
	if pp.back then
		table.insert(t, textPlate("back", pp.back, V3(0, 0.25, 0.05), V3(0.95, 0.28, 0.02), "c2", "Back"))
	end
	if pp.epaulettes then
		add(t, mirror({ p("Block", "neck", V3(0.28, 0.06, 0.36), V3(0.45, -0.1, 0.06), nil, "brass", { m = MET }) }))
	end
	if pp.neon then -- cyber trim
		add(t, mirror({ p("Block", "chest", V3(0.03, 1.2, 0.02), V3(0.16, 0.0, -0.055), nil, "neon", { m = NEO }) }))
		add(t, mirror({ cylY("RLowerArm", 0.06, 1.12, V3(0, -0.3, 0), "neon", { m = NEO }) }))
	end
	if pp.long then -- coat skirt down to mid-thigh / knee
		local l = pp.long
		for i = 0, 9 do
			local a = i / 10 * math.pi * 2
			if math.abs(math.sin(a)) > 0.2 or math.cos(a) > 0 then -- open at the front
				table.insert(t, p("Block", "hips", V3(0.4, l, 0.05), V3(math.sin(a) * 0.62, 0.0 - l / 2, math.cos(a) * 0.48), V3(math.cos(a) * -5, math.deg(a), 0), "c1", { m = m }))
			end
		end
		if pp.belted then
			table.insert(t, cylY("hips", 0.12, 1.3, V3(0, 0.32, 0), "c1", { m = m }))
		end
	end
	local b = { Torso = { c = "c1", m = m }, UArm = { c = pp.sleeveC or "c1", m = pp.sleeveM == "leather" and LEA or m },
		LArm = { c = pp.sleeveC or "c1", m = pp.sleeveM == "leather" and LEA or m } }
	if pp.vest then -- sleeveless (puffer vest, denim vest): keep the top's arms
		b.UArm, b.LArm = nil, nil
		for i = #t, 1, -1 do
			if t[i].f == "RUpperArm" or t[i].f == "LUpperArm" or t[i].f == "RLowerArm" or t[i].f == "LLowerArm" then
				table.remove(t, i)
			end
		end
	end
	return t, b
end
F.labcoat = function(pp)
	return F.jacket({ open = true, collar = "lapel", collarC = "c1", long = pp.long or 1.3, pockets = true, back = pp.back })
end

------------------------------------------------------------------ bottoms (body: Hips ULeg LLeg)
F.pants = function(pp)
	local m = pp.m == "leather" and LEA or FAB
	local t = {}
	if pp.stack then -- baggy jeans stacking over the shoes
		add(t, mirror({ p("Ball", "RAnkle", V3(1.45, 0.75, 1.45), V3(0, 0.25, 0), nil, "c1", { m = m }) }))
	end
	if pp.cuff then -- joggers' ribbed cuff
		add(t, mirror({ cylY("RAnkle", 0.3, 1.1, V3(0, 0.2, 0), "dark", { m = FAB }) }))
	end
	if pp.cargo then
		add(t, mirror({ p("Block", "RUpperLeg", V3(0.12, 0.3, 0.4), V3(0.55, -0.1, 0), nil, "c1", { m = m, fit = true }) }))
	end
	if pp.rips then
		add(t, mirror({ p("Block", "RLowerLeg", V3(1.02, 0.12, 0.5), V3(0, 0.38, -0.25), nil, "skin", { fit = true }) }))
	end
	if pp.stripe then -- track pants side stripes
		add(t, mirror({
			p("Block", "RUpperLeg", V3(0.06, 1.0, 0.16), V3(0.51, 0, 0), nil, "c2", { m = FAB, fit = true }),
			p("Block", "RLowerLeg", V3(0.06, 1.0, 0.16), V3(0.51, 0, 0), nil, "c2", { m = FAB, fit = true }),
		}))
	end
	if pp.wide then -- barrel / wide-leg: volume round the knee and shin
		add(t, mirror({ p("Ball", "RLowerLeg", V3(1.35, 1.1, 1.35), V3(0, 0.15, 0), nil, "c1", { m = m, fit = true }) }))
	end
	if pp.crease then
		add(t, mirror({ p("Block", "RLowerLeg", V3(0.02, 1.0, 0.02), V3(0, 0, -0.5), nil, "dark", { m = FAB, fit = true }) }))
	end
	return t, { Hips = { c = "c1", m = m }, ULeg = { c = "c1", m = m }, LLeg = { c = "c1", m = m } }
end
F.shorts = function(pp)
	local t = {}
	if pp.long then -- long basketball shorts / jorts past the knee
		add(t, mirror({ cylY("RLowerLeg", 0.35, 1.2, V3(0, 0.3, 0), "c1", { m = FAB, fit = true }) }))
	end
	if pp.stripe then
		add(t, mirror({ p("Block", "RUpperLeg", V3(0.06, 1.0, 0.16), V3(0.51, 0, 0), nil, "c2", { m = FAB, fit = true }) }))
	end
	if pp.socks then -- long shorts with tall white socks pulled up to the knee
		return t, { Hips = { c = "c1", m = FAB }, ULeg = { c = "c1", m = FAB }, LLeg = { c = "c2", m = FAB } }
	end
	return t, { Hips = { c = "c1", m = FAB }, ULeg = { c = "c1", m = FAB }, LLeg = "skin" }
end
F.skirt = function(pp)
	local l = pp.len or 0.9
	local t = {}
	local n = pp.pleats and 16 or 12
	for i = 0, n - 1 do
		local a = i / n * math.pi * 2
		table.insert(t, p("Block", "hips", V3(0.3, l, 0.04), V3(math.sin(a) * 0.62, 0.15 - l / 2, math.cos(a) * 0.46), V3(-(pp.flare or 8), math.deg(a), 0), (pp.pleats and i % 2 == 0) and "dark" or "c1", { m = FAB }))
	end
	local b = { Hips = { c = "c1", m = FAB }, ULeg = "skin", LLeg = "skin" }
	if pp.tights then
		b.ULeg, b.LLeg = { c = "c2", m = FAB }, { c = "c2", m = FAB }
	end
	return t, b
end
F.leggings = function()
	return {}, { Hips = { c = "c1", m = SMO }, ULeg = { c = "c1", m = SMO }, LLeg = { c = "c1", m = SMO } }
end

------------------------------------------------------------------ shoes (frames LFoot/RFoot with fit, LAnkle/RAnkle)
F.shoes = function(pp)
	local h = pp.sole or 0.16
	local m = pp.m == "leather" and LEA or (pp.m == "rubber" and RUB or FAB)
	local t = {
		p("Block", "RFoot", V3(1.0, h, 1.02), V3(0, -0.5 - h / 2 + 0.06, 0), nil, pp.gum and "gum" or pp.soleC or "c2", { m = RUB, fit = true }),
	}
	if pp.panel then
		table.insert(t, p("Block", "RFoot", V3(0.06, 0.35, 0.6), V3(0.52, -0.1, 0.05), nil, "c2", { m = m, fit = true }))
	end
	if pp.high then
		table.insert(t, cylY("RAnkle", 0.55, 1.18, V3(0, 0.15, 0), "c1", { m = m }))
	end
	if pp.boot then
		table.insert(t, cylY("RAnkle", pp.boot, 1.22, V3(0, pp.boot / 2 - 0.1, 0), "c1", { m = m }))
		table.insert(t, cylY("RAnkle", 0.1, 1.28, V3(0, pp.boot - 0.1, 0), pp.collarC or "dark", { m = m }))
	end
	if pp.heel then
		table.insert(t, p("Block", "RFoot", V3(0.2, pp.heel, 0.2), V3(0, -0.5 - pp.heel / 2, 0.38), nil, "c2", { m = SMO, fit = true }))
	end
	if pp.wedge then
		table.insert(t, p("Wedge", "RFoot", V3(0.9, 0.45, 0.9), V3(0, -0.6, 0.05), V3(0, 180, 0), "c2", { m = FAB, fit = true }))
	end
	if pp.laces then
		table.insert(t, p("Block", "RFoot", V3(0.3, 0.05, 0.4), V3(0, 0.45, -0.15), nil, "white", { m = FAB, fit = true }))
	end
	local foot = { c = "c1", m = m }
	if pp.slides then -- slides over socks
		t = {
			p("Block", "RFoot", V3(1.08, 0.18, 1.06), V3(0, -0.56, 0), nil, "c1", { m = RUB, fit = true }),
			p("Block", "RFoot", V3(1.1, 0.35, 0.45), V3(0, 0.0, -0.15), nil, "c1", { m = RUB, fit = true }),
		}
		foot = { c = "c2", m = FAB }
	elseif pp.sandal then
		t = {
			p("Block", "RFoot", V3(1.06, 0.12, 1.04), V3(0, -0.56, 0), nil, "c1", { m = LEA, fit = true }),
			p("Block", "RFoot", V3(1.1, 0.12, 0.2), V3(0, 0.1, -0.2), nil, "c1", { m = LEA, fit = true }),
		}
		foot = "skin"
	end
	return mirror(t), { Foot = foot }
end

------------------------------------------------------------------ tattoos (ink that only shows on bare skin)
-- q.skin = the body region the ink sits on; Apply drops the piece if that region is covered by clothes
local function ink(f, region, s, o, r, x)
	local t = x or {}
	t.skin, t.fit, t.m = region, true, SMO
	t.t = t.t or 0.15
	return p("Ball", f, s, o, r, "c1", t)
end
local function inkText(f, region, text, o, size, rot, face, fit)
	return p("Block", f, size, o, rot, "c1", { fit = fit ~= false, t = 1, skin = region,
		txt = { text = text, color = "c1", face = face or "Right", font = "Fantasy" } })
end
local function armSleeve(side, limbs, n, seed)
	-- black-and-grey sleeve: a soft grey wash that fades out at the ends, then flowing linework and a few
	-- solid motifs laid flat on the skin (each piece faces out from the limb)
	local t = {}
	for li, pr in ipairs(limbs) do
		local f, region = side .. pr[1], pr[2]
		table.insert(t, ink(f, region, V3(1.06, 0.94, 1.06), V3(0, 0, 0), nil, { t = 0.68 }))
		for i = 1, n do
			local k = (i * 7919 + seed * 131 + li * 17) % 211
			local ang = (k % 16) / 16 * math.pi * 2 + li
			local y = ((k % 11) - 5) * 0.075
			local solid = (i % 4 == 0)
			local s = solid and V3(0.05, 0.16 + (k % 3) * 0.04, 0.2 + (k % 2) * 0.08) or V3(0.04, 0.24 + (k % 4) * 0.05, 0.05)
			local lcf = CFrame.new(math.cos(ang) * 0.52, y, math.sin(ang) * 0.52) * CFrame.Angles(0, -ang, 0)
				* CFrame.Angles(math.rad((k % 70) - 35), 0, 0)
			table.insert(t, ink(f, region, s, nil, nil, { lcf = lcf, t = solid and 0.12 or 0.05 }))
		end
	end
	return t
end
F.tattoo = function(pp)
	local t = {}
	local kind = pp.kind
	local sides = pp.both and { "R", "L" } or { "R" }
	for si, side in ipairs(sides) do
		local sx = side == "R" and 1 or -1
		local face = side == "R" and "Right" or "Left"
		if kind == "sleeve" then
			add(t, armSleeve(side, { { "UpperArm", "UArm" }, { "LowerArm", "LArm" } }, 22, si))
		elseif kind == "half" then
			add(t, armSleeve(side, { { "LowerArm", "LArm" } }, 18, si + 2))
		elseif kind == "forearm" then
			table.insert(t, inkText(side .. "LowerArm", "LArm", (si == 2 and pp.text2) or pp.text or "FAMILIA", V3(0, -0.08, -0.37), V3(1.14, 0.24, 0.02), V3(0, 0, 90), "Front"))
		elseif kind == "rose" then -- a rose with leaves on the forearm
			table.insert(t, ink(side .. "LowerArm", "LArm", V3(0.1, 0.22, 0.4), V3(sx * 0.47, 0.1, 0), V3(0, 0, 0), { t = 0.05 }))
			table.insert(t, ink(side .. "LowerArm", "LArm", V3(0.1, 0.3, 0.12), V3(sx * 0.48, -0.12, 0.08), V3(30, 0, 0), { t = 0.2 }))
			table.insert(t, ink(side .. "LowerArm", "LArm", V3(0.1, 0.3, 0.12), V3(sx * 0.48, -0.12, -0.08), V3(-30, 0, 0), { t = 0.2 }))
		elseif kind == "calf" then
			add(t, armSleeve(side, { { "LowerLeg", "LLeg" } }, 16, si + 5))
		elseif kind == "hands" then
			table.insert(t, inkText(side .. "Hand", "Hand", (si == 2 and pp.text2) or pp.text or "LOVE", V3(0, 0.05, 0.51), V3(0.8, 0.35, 0.02), V3(0, 0, 0), "Back"))
		end
	end
	if kind == "neck" then
		table.insert(t, inkText("neck", "Head", pp.text or "FAMILIA", V3(0, 0.1, -0.31), V3(0.6, 0.2, 0.02), V3(-6, 0, 0), "Front", false))
	elseif kind == "face" then
		local ex = FACE.eyeX + 0.06
		local mark = pp.mark or "star"
		if mark == "star" then
			table.insert(t, p("Block", "head", V3(0.1, 0.1, 0.02), V3(ex, FACE.eyeY - 0.3, -0.93), V3(0, 0, 45), "c1", { m = SMO, skin = "Head" }))
			table.insert(t, p("Block", "head", V3(0.1, 0.1, 0.02), V3(ex, FACE.eyeY - 0.3, -0.931), nil, "c1", { m = SMO, skin = "Head" }))
		elseif mark == "cross" then
			table.insert(t, p("Block", "head", V3(0.03, 0.14, 0.02), V3(ex, FACE.eyeY - 0.3, -0.93), nil, "c1", { m = SMO, skin = "Head" }))
			table.insert(t, p("Block", "head", V3(0.09, 0.03, 0.02), V3(ex, FACE.eyeY - 0.27, -0.931), nil, "c1", { m = SMO, skin = "Head" }))
		elseif mark == "dots" then
			for i = 0, 2 do
				table.insert(t, p("Ball", "head", V3(0.04, 0.04, 0.02), V3(ex + i * 0.06, FACE.eyeY - 0.28, -0.93), nil, "c1", { m = SMO, skin = "Head" }))
			end
		elseif mark == "script" then -- a small word over the eyebrow
			table.insert(t, p("Block", "head", V3(0.42, 0.1, 0.02), V3(ex, FACE.browY + 0.1, -0.95), V3(-15, 0, 0), "c1", { t = 1, skin = "Head",
				txt = { text = pp.text or "BLESSED", color = "c1", face = "Front", font = "Fantasy" } }))
		end
	end
	return t
end

------------------------------------------------------------------ lowrider pieces
F.suspenders = function()
	local t = mirror({
		p("Block", "chest", V3(0.07, 1.25, 0.03), V3(0.24, 0.05, -0.05), V3(0, 0, 3), "c1", { m = FAB }),
		p("Block", "back", V3(0.07, 1.25, 0.03), V3(0.16, 0.05, 0.05), V3(0, 0, -12), "c1", { m = FAB }),
		p("Block", "chest", V3(0.09, 0.06, 0.04), V3(0.24, -0.55, -0.06), nil, "c2", { m = MET }),
	})
	return t
end
F.hairnet = function()
	return { p("Ball", "head", V3(2.16, 1.5, 2.26), V3(0, 0.44, 0.12), nil, "c1", { m = FAB, t = 0.55 }) }
end
F.foldedband = function()
	-- a bandana folded flat and tied low across the forehead, knot at the back
	local t = {
		cylY("head", 0.26, 2.14, V3(0, 0.38, 0.06), "c1", { m = FAB }, -10),
		p("Ball", "head", V3(0.3, 0.26, 0.26), V3(0, 0.25, 1.1), nil, "c1", { m = FAB }),
	}
	add(t, mirror({ p("Wedge", "head", V3(0.04, 0.45, 0.22), V3(0.12, -0.05, 1.14), V3(0, 90, 12), "c1", { m = FAB }) }))
	return t
end

---------------------------------------------------------------------------------------------------- frames
local function attWorld(part, name)
	local a = part and part:FindFirstChild(name)
	if a and a:IsA("Attachment") then
		return a.WorldPosition
	end
	return nil
end

function B.frames(char)
	local fr = {}
	local head = char:FindFirstChild("Head")
	if head then
		local rot = head.CFrame - head.CFrame.Position
		local c = attWorld(head, "FaceCenterAttachment") or head.Position
		local f = attWorld(head, "FaceFrontAttachment")
		local R = f and (f - c).Magnitude or head.Size.X * 0.5
		R = math.clamp(R, head.Size.X * 0.3, head.Size.X * 0.75)
		fr.head = { part = head, cf = CFrame.new(c) * rot, u = R }
	end
	local ut = char:FindFirstChild("UpperTorso") or char:FindFirstChild("Torso")
	if ut then
		local rot = ut.CFrame - ut.CFrame.Position
		local n = attWorld(ut, "NeckAttachment") or (ut.CFrame * CFrame.new(0, ut.Size.Y / 2, 0)).Position
		local bf = attWorld(ut, "BodyFrontAttachment") or (ut.CFrame * CFrame.new(0, 0, -ut.Size.Z / 2)).Position
		local bb = attWorld(ut, "BodyBackAttachment") or (ut.CFrame * CFrame.new(0, 0, ut.Size.Z / 2)).Position
		local u = (bf - n).Magnitude
		fr.neck = { part = ut, cf = CFrame.new(n) * rot, u = u }
		fr.chest = { part = ut, cf = CFrame.new(bf) * rot, u = u }
		fr.back = { part = ut, cf = CFrame.new(bb) * rot, u = u }
	end
	local lt = char:FindFirstChild("LowerTorso")
	if lt and fr.neck then
		local rot = lt.CFrame - lt.CFrame.Position
		local w = attWorld(lt, "WaistCenterAttachment") or lt.Position
		fr.hips = { part = lt, cf = CFrame.new(w) * rot, u = fr.neck.u }
	end
	for _, side in ipairs({ "Left", "Right" }) do
		local s = side:sub(1, 1)
		for _, limb in ipairs({ "UpperArm", "LowerArm", "Hand", "UpperLeg", "LowerLeg", "Foot" }) do
			local part = char:FindFirstChild(side .. limb)
			if part then
				fr[s .. limb] = { part = part, cf = part.CFrame, u = math.min(part.Size.X, part.Size.Z), size = part.Size }
			end
		end
		local la = char:FindFirstChild(side .. "LowerArm")
		if la then
			local w = attWorld(la, side .. "WristRigAttachment")
			local cf = w and (CFrame.new(w) * (la.CFrame - la.CFrame.Position)) or (la.CFrame * CFrame.new(0, -la.Size.Y * 0.42, 0))
			fr[s .. "Wrist"] = { part = la, cf = cf, u = math.min(la.Size.X, la.Size.Z) }
		end
		local ll = char:FindFirstChild(side .. "LowerLeg")
		if ll then
			local a = attWorld(ll, side .. "AnkleRigAttachment")
			local cf = a and (CFrame.new(a) * (ll.CFrame - ll.CFrame.Position)) or (ll.CFrame * CFrame.new(0, -ll.Size.Y * 0.45, 0))
			fr[s .. "Ankle"] = { part = ll, cf = cf, u = math.min(ll.Size.X, ll.Size.Z) }
		end
	end
	return fr
end

---------------------------------------------------------------------------------------------------- build
local REGION_PARTS = {
	Head = { "Head" },
	Torso = { "UpperTorso", "Torso" },
	Hips = { "LowerTorso" },
	UArm = { "LeftUpperArm", "RightUpperArm" },
	LArm = { "LeftLowerArm", "RightLowerArm" },
	Hand = { "LeftHand", "RightHand" },
	ULeg = { "LeftUpperLeg", "RightUpperLeg" },
	LLeg = { "LeftLowerLeg", "RightLowerLeg" },
	Foot = { "LeftFoot", "RightFoot" },
}
B.REGION_PARTS = REGION_PARTS

local function colourFor(key, ctx)
	if typeof(key) == "Color3" then
		return key
	end
	if key == "c1" then
		return ctx.c1
	elseif key == "c2" then
		return ctx.c2
	elseif key == "skin" then
		return ctx.skin
	elseif key == "under" then
		return ctx.under or ctx.c1
	elseif key == "dark" then
		return mix(ctx.c1, Color3.new(0, 0, 0), 0.35)
	elseif key == "light" then
		return mix(ctx.c1, Color3.new(1, 1, 1), 0.3)
	elseif key == "fade" then
		return mix(ctx.c1, ctx.skin, 0.55)
	elseif key == "dial" then
		return mix(ctx.c1, Color3.new(0, 0, 0), 0.7)
	elseif key == "hair" then
		return ctx.hair or ctx.c1
	end
	return FIXED[key] or ctx.c1
end

-- where a piece goes: its size and world CFrame, from its frame
function B.place(q, fr)
	local scale
	if q.fit and fr.size then
		scale = fr.size
	else
		scale = V3(fr.u, fr.u, fr.u)
	end
	local sizeScale = scale
	if q.sh == "Cyl" and q.fit and fr.size then
		-- a fitted cylinder: its length follows whichever limb axis it lies along and its diameter hugs the
		-- limb's thickest side (a Roblox cylinder is always round, so a stretched one would shrink inside the limb)
		local rot = q.lcf and (q.lcf - q.lcf.Position) or CFrame.Angles(rad(q.r.X), rad(q.r.Y), rad(q.r.Z))
		local ax = rot * V3(1, 0, 0) - rot.Position
		local a = { math.abs(ax.X), math.abs(ax.Y), math.abs(ax.Z) }
		local dims = { fr.size.X, fr.size.Y, fr.size.Z }
		local i = (a[1] >= a[2] and a[1] >= a[3]) and 1 or ((a[2] >= a[3]) and 2 or 3)
		local d = 0
		for k = 1, 3 do
			if k ~= i then
				d = math.max(d, dims[k])
			end
		end
		sizeScale = V3(dims[i], d, d)
	end
	local size = q.s * sizeScale
	size = V3(math.max(size.X, 0.02), math.max(size.Y, 0.02), math.max(size.Z, 0.02))
	local cf
	if q.lcf then
		cf = fr.cf * CFrame.new(q.lcf.Position * scale) * (q.lcf - q.lcf.Position)
	else
		cf = fr.cf * CFrame.new(q.o * scale) * CFrame.Angles(rad(q.r.X), rad(q.r.Y), rad(q.r.Z))
	end
	return size, cf
end

B.colourFor, B.KEY_MAT, B.KEY_REFL = colourFor, KEY_MAT, KEY_REFL

local function makePart(q, fr, ctx, model, item)
	local sh = q.sh
	local part
	if sh == "Wedge" then
		part = Instance.new("WedgePart")
	elseif sh == "Corner" then
		part = Instance.new("CornerWedgePart")
	else
		part = Instance.new("Part")
		if sh == "Ball" then
			-- a Ball-shaped Part is always a perfect sphere; a block with a sphere mesh stretches to any size, so
			-- hair caps, puffers and pendants keep their egg / ellipsoid shapes
			part.Shape = Enum.PartType.Block
			local mesh = Instance.new("SpecialMesh")
			mesh.MeshType = Enum.MeshType.Sphere
			mesh.Parent = part
		elseif sh == "Cyl" then
			part.Shape = Enum.PartType.Cylinder
		else
			part.Shape = Enum.PartType.Block
		end
	end
	local size, cf = B.place(q, fr)
	part.Size = size
	part.CFrame = cf
	part.Color = colourFor(q.c, ctx)
	part.Material = q.m or KEY_MAT[q.c] or (item.mat and Enum.Material[item.mat]) or FAB
	part.Reflectance = q.refl or KEY_REFL[q.c] or 0
	part.Transparency = q.t or 0
	part.CastShadow = (part.Size.Magnitude > 0.25 * fr.u)
	part.Anchored = false
	part.CanCollide = false
	part.CanQuery = false
	part.CanTouch = false
	part.Massless = true
	part.TopSurface, part.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
	part.Name = sh
	if q.txt then
		local sg = Instance.new("SurfaceGui")
		sg.Face = Enum.NormalId[q.txt.face or "Front"]
		sg.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
		sg.PixelsPerStud = 60
		sg.LightInfluence = 1
		local tl = Instance.new("TextLabel")
		tl.BackgroundTransparency = 1
		tl.Size = UDim2.fromScale(1, 1)
		tl.Text = q.txt.text
		tl.TextScaled = true
		tl.Font = Enum.Font[q.txt.font or "GothamBlack"]
		tl.TextColor3 = colourFor(q.txt.color or "c2", ctx)
		tl.Parent = sg
		sg.Parent = part
	end
	if q.spark and ctx.sparkle then
		local pe = Instance.new("ParticleEmitter")
		pe.Texture = "rbxasset://textures/particles/sparkles_main.dds"
		pe.Rate = 1.6
		pe.Lifetime = NumberRange.new(0.25, 0.45)
		pe.Speed = NumberRange.new(0)
		pe.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0), NumberSequenceKeypoint.new(0.5, 0.18 * fr.u), NumberSequenceKeypoint.new(1, 0) })
		pe.LightEmission = 1
		pe.Color = ColorSequence.new(Color3.new(1, 1, 1))
		pe.Parent = part
	end
	if q.glow and ctx.sparkle then
		local l = Instance.new("PointLight")
		l.Range, l.Brightness, l.Color = 3, 0.6, part.Color
		l.Parent = part
	end
	local w = Instance.new("WeldConstraint")
	w.Part0, w.Part1 = fr.part, part
	w.Parent = part
	part.Parent = model
	return part
end

-- resolve a look against the catalog: returns a list of { slot, item, c1, c2 } in the order they layer
function B.resolve(look, Catalog)
	local out = {}
	for _, slot in ipairs(Catalog.SLOTS) do
		local e = look[slot.id]
		local item = e and Catalog.ITEMS_BY_ID[e.id]
		if item and item.slot == slot.id then
			table.insert(out, {
				slot = slot.id,
				item = item,
				c1 = hex(e.c1 or item.def1 or "#808080"),
				c2 = hex(e.c2 or item.def2 or item.def1 or "#808080"),
			})
		end
	end
	return out
end

-- strip anything on the torso / hips / thighs that could show skin (a skin texture, a SurfaceAppearance) and
-- put the plain base layer on. Safe to call on any character at any time; Apply calls it too.
function B.ApplyBaseLayer(char)
	for region, colour in pairs(B.BASE_LAYER) do
		for _, name in ipairs(REGION_PARTS[region]) do
			local part = char:FindFirstChild(name)
			if part and part:IsA("BasePart") then
				for _, ch in ipairs(part:GetChildren()) do
					if ch:IsA("SurfaceAppearance") or ch:IsA("Decal") or ch:IsA("Texture") then
						ch:Destroy()
					end
				end
				if part:IsA("MeshPart") then
					pcall(function()
						part.TextureID = ""
					end)
				end
				part.Color = colour
				part.Material = FAB
			end
		end
	end
end

function B.Clear(char)
	local old = char:FindFirstChild(B.FOLDER)
	if old then
		old:Destroy()
	end
	for _, a in ipairs(char:GetChildren()) do
		if a:IsA("Accessory") and a:GetAttribute("NC_Look") then
			a:Destroy()
		end
	end
end

-- Plan(look, Catalog, opts) -> regions, builds: the pure part of Apply (no Instances), also used by the offline
-- preview renderer. regions[name] = { colour, material, bare }; builds = { { e, item, ctx, pieces, skip } }
function B.Plan(look, Catalog, opts)
	opts = opts or {}
	local entries = B.resolve(look, Catalog)

	-- skin first, then which slots hide others (helmets / ski masks hide hair; hats flatten hair volume)
	local skin = Color3.fromRGB(198, 140, 105)
	local hairColour
	local hideHair, hatOn, hideBeard = false, false, false
	local topColour
	for _, e in ipairs(entries) do
		if e.slot == "Skin" then
			skin = e.c1
		elseif e.slot == "Hair" then
			hairColour = e.c1
		elseif e.slot == "Top" then
			topColour = e.c1
		end
		local pp = e.item.p or {}
		if pp.hideHair then
			hideHair = true
		end
		if pp.hideBeard then
			hideBeard = true
		end
		if e.slot == "Head" and not pp.noFlatten then
			hatOn = true
		end
	end

	-- body regions. NO NUDITY, EVER (Roblox rules): the torso, hips and thighs start dressed in a plain base
	-- layer (undershirt + boxer shorts) and can never be set to skin by any item, so even a broken or empty look,
	-- a failed load or a missing top/bottom still shows a clothed body. Only arms, lower legs, hands, feet and the
	-- head may show skin.
	local regions = {}
	for name in pairs(REGION_PARTS) do
		regions[name] = { colour = skin, material = Enum.Material.SmoothPlastic }
	end
	for name, colour in pairs(B.BASE_LAYER) do
		regions[name] = { colour = colour, material = FAB }
	end

	-- pass 1: every item's body colours (so pass 2 knows which regions are bare skin, for tattoos)
	local built = {}
	for name, st in pairs(regions) do
		st.bare = not B.BASE_LAYER[name]
	end
	for _, e in ipairs(entries) do
		local item = e.item
		local ctx = { c1 = e.c1, c2 = e.c2, skin = skin, hair = hairColour, under = topColour, sparkle = opts.sparkle ~= false }
		local fam = F[item.fam]
		if not fam then
			warn("NCLookBuilder: no family " .. tostring(item.fam) .. " for " .. item.id)
			continue
		end
		local pieces, body = fam(item.p or {}, item)
		if body then
			for region, v in pairs(body) do
				local key, m = v, nil
				if type(v) == "table" then
					key, m = v.c, v.m
				end
				if key == "skin" and B.BASE_LAYER[region] then
					continue -- never bare: the base layer stays (under skirts and dresses it reads as bike shorts)
				end
				regions[region] = { colour = colourFor(key, ctx), material = m or (key == "skin" and Enum.Material.SmoothPlastic or FAB), bare = key == "skin" }
			end
		end
		local skip = (e.slot == "Hair" and hideHair) or (e.slot == "FacialHair" and hideBeard)
		table.insert(built, { e = e, item = item, ctx = ctx, pieces = pieces, skip = skip })
	end

	return regions, built, hatOn, hideHair, hideBeard
end

-- should this piece of this build be made? (hats flatten hair, clothes cover tattoos)
function B.wants(b, q, regions, hatOn)
	if q.skin and not (regions[q.skin] and regions[q.skin].bare) then
		return false
	end
	if q.top and hatOn and b.e.slot == "Hair" then
		return false
	end
	return true
end

-- Apply(char, look, Catalog, opts) -> the folder of built pieces
--   opts.assets: { [itemId] = Accessory } real meshes to wear instead of the procedural pieces
--   opts.sparkle: particle twinkles on iced pieces and small lights on glowing parts (default true)
--   opts.stripAvatar: remove the Roblox avatar's own clothing, accessories and BodyColors (default true)
function B.Apply(char, look, Catalog, opts)
	opts = opts or {}
	B.Clear(char)
	if opts.stripAvatar ~= false then
		for _, d in ipairs(char:GetChildren()) do
			if d:IsA("Shirt") or d:IsA("Pants") or d:IsA("ShirtGraphic") or d:IsA("BodyColors") then
				d:Destroy()
			elseif d:IsA("Accessory") and not d:GetAttribute("NC_Keep") then
				d:Destroy()
			end
		end
	end
	B.ApplyBaseLayer(char)
	local folder = Instance.new("Folder")
	folder.Name = B.FOLDER
	local fr = B.frames(char)
	local regions, built, hatOn = B.Plan(look, Catalog, opts)
	for _, b in ipairs(built) do
		local item, ctx, pieces, skip = b.item, b.ctx, b.pieces, b.skip
		local asset = opts.assets and opts.assets[item.id]
		if asset and not skip then
			local acc = asset:Clone()
			acc:SetAttribute("NC_Look", item.id)
			local hum = char:FindFirstChildOfClass("Humanoid")
			if hum then
				hum:AddAccessory(acc)
			end
		elseif not skip and pieces and #pieces > 0 then
			local model = Instance.new("Model")
			model.Name = item.id
			for _, q in ipairs(pieces) do
				if B.wants(b, q, regions, hatOn) then
					local f = fr[q.f]
					if f then
						makePart(q, f, ctx, model, item)
					end
				end
			end
			model.Parent = folder
		end
	end

	for region, st in pairs(regions) do
		for _, name in ipairs(REGION_PARTS[region]) do
			local part = char:FindFirstChild(name)
			if part and part:IsA("BasePart") then
				part.Color = st.colour
				part.Material = st.material
				-- standard avatar heads carry a mesh with its own texture: keep the face decal, drop the texture
				if part:IsA("MeshPart") and region ~= "Head" then
					pcall(function()
						part.TextureID = ""
					end)
					local sa = part:FindFirstChildOfClass("SurfaceAppearance")
					if sa then
						sa:Destroy()
					end
				end
			end
		end
	end
	folder.Parent = char
	char:SetAttribute("NC_LookApplied", os.clock())
	return folder
end

return B
