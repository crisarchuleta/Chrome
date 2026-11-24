--!nonstrict
-- NCHead (ModuleScript, ReplicatedStorage): real mesh hair and face pieces for the MakeHuman heads.
--
-- The pieces are made by build_heads.py from each head's own scalp and face, so the hair grows out of a soft
-- hairline instead of sitting on top like a helmet, and every piece fits that head exactly:
--   Hair_<Style>        the hair (Male: Buzz, Crop, TaperFade, HighFade, SidePart, CurlyTop, Locs, Twists, FlatTwists;
--                       Female: Pixie, Locs, LowBun, Ponytail, LongStraight, Bob)
--   Hair_<Style>_Cap    the same style pressed flat and trimmed, worn under a hat
--   Hair_<Style>_Cards / _CapCards   hair-card styles: strand cards over the painted scalp (and their under-hat cut);
--                                    big sets add _Cards_2, _Cards_3 ...
--   Brows_<Shape>       Natural, Thick, Arched, Straight, Thin
--   LashLine, Lips      on every face (the lips are tinted from the skin colour)
--   Stubble, StubbleHeavy   (Male)
-- Studio setup: import NC_Head_Male.fbx and NC_Head_Female.fbx and run AssembleHeads.lua, which files them in
-- ReplicatedStorage.NC_HeadAssets.<Gender>. NCHeadData holds where each piece sits.
--
-- Hair, brows and stubble carry a greyscale SurfaceAppearance (AlphaMode Transparency): its edges are single hairs
-- that thin out onto the skin, so there is no rim at the hairline. SurfaceAppearance.Color tints it to the chosen
-- colour, and the part needs a Transparency of at least 0.02 for the soft alpha to show.
-- Every piece is placed from the point between the eyes (the NC_FaceEyeL/R bones in the head) and scaled by
-- the distance between the eyes, so the same pieces fit all five builds of each body.
local RS = game:GetService("ReplicatedStorage")

local H = {}
H.FOLDER = "NC_Face"
H.SOFT_T = 0.02 -- the smallest Transparency that turns on the soft alpha of a SurfaceAppearance
-- Transparency of the scalp shell under a hair-card style. Two see-through parts are sorted by their centres, and the
-- shell's and the cards' centres are ~0.04 studs apart, so from some angles the shell drew over the cards (a smooth
-- glossy front, and strands only past its silhouette like a crest). An opaque shell is always drawn first. If skin
-- fades go hard-edged with it, set this back to H.SOFT_T.
H.CARD_SHELL_T = 0
-- styles whose cards are only loose hairs round locs or twists keep the soft shell: the shell's soft edge is their
-- fade/band edge (opaque, it went hard and dark under Flat Twists), and loose wisps don't suffer from the sort
H.SOFT_SHELL = { Locs = true, Twists = true, FlatTwists = true }
H.LIP_TINT = Color3.fromRGB(150, 62, 70)
H.LASH = Color3.fromRGB(22, 16, 14)

local Data
local function data()
	if Data == nil then
		local m = RS:FindFirstChild("NCHeadData")
		Data = m and require(m) or false
	end
	return Data or nil
end

-- "Male" / "Female" for a MakeHuman body (NCBodyService tags it NC_BodyId = "<Gender>_<Build>"), else nil
function H.gender(char)
	local id = char and char:GetAttribute("NC_BodyId")
	if type(id) == "string" then
		return id:match("^(%a+)_")
	end
	return nil
end

-- an Attachment's or Bone's rest position (before any face shape slider moved it)
local function rest(inst)
	local r = inst:GetAttribute("NC_Rest")
	if typeof(r) ~= "Vector3" then
		r = inst.Position
		inst:SetAttribute("NC_Rest", r)
	end
	return r
end

-- the face bones of a character, by name (cached on the character until its head changes)
local boneCache = setmetatable({}, { __mode = "k" })
function H.bones(char)
	local head = char:FindFirstChild("Head")
	local c = boneCache[char]
	if c and c.head == head then
		return c.bones
	end
	local bones = {}
	for _, d in ipairs(char:GetDescendants()) do
		if d:IsA("Bone") and d.Name:sub(1, 7) == "NC_Face" then
			bones[d.Name] = d
		end
	end
	boneCache[char] = { head = head, bones = bones }
	return bones
end

-- how far a set of face bones has moved from rest, on average (head space)
function H.delta(char, names)
	local bones = H.bones(char)
	local sum, n = Vector3.zero, 0
	for _, name in ipairs(names) do
		local b = bones[name]
		if b then
			sum += b.Position - rest(b)
			n += 1
		end
	end
	return n > 0 and sum / n or Vector3.zero
end

-- what each face piece follows when the face shape changes (and how much)
H.FOLLOW = {
	Brows = { { "NC_FaceBrowL", "NC_FaceBrowR" }, 1 },
	LashLine = { { "NC_FaceEyeL", "NC_FaceEyeR" }, 1 },
	Lips = { { "NC_FaceLipUpper", "NC_FaceLipLower", "NC_FaceMouthL", "NC_FaceMouthR" }, 1 },
	Stubble = { { "NC_FaceChin", "NC_FaceJawL", "NC_FaceJawR" }, 0.5 },
	StubbleHeavy = { { "NC_FaceChin", "NC_FaceJawL", "NC_FaceJawR" }, 0.5 },
}

-- face shape: shape = { v = { [slider id] = -1 .. 1 } } (NCLookCatalog.FACE_SLIDERS). Moves the face bones from
-- rest and the eyes' attachments with their bones (ApplyEyes then rebuilds the eyeballs there). Safe on any body.
function H.ApplyShape(char, shape, sliders, scale)
	local bones = H.bones(char)
	if next(bones) == nil then
		return false
	end
	scale = scale or 1
	local move = {}
	local v = shape and shape.v or {}
	for _, sl in ipairs(sliders or {}) do
		local x = v[sl.id]
		if type(x) == "number" and x ~= 0 then
			for bone, d in pairs(sl.moves) do
				move[bone] = (move[bone] or Vector3.zero) + d * math.clamp(x, -1, 1) * scale
			end
		end
	end
	for name, b in pairs(bones) do
		b.Position = rest(b) + (move[name] or Vector3.zero)
	end
	local head = char:FindFirstChild("Head")
	if head then
		for side, bone in pairs({ Left = "NC_FaceEyeL", Right = "NC_FaceEyeR" }) do
			local at = head:FindFirstChild("NC_" .. side .. "EyeAttachment")
			if at then
				at.Position = rest(at) + (move[bone] or Vector3.zero)
			end
		end
	end
	return true
end

-- the head part, the CFrame of the point between the eyes (head's rotation) and the scale, or nil on a body
-- without the pieces (stock avatars, or before the assets are installed)
function H.frame(char)
	local g = H.gender(char)
	local D = data()
	local assets = RS:FindFirstChild("NC_HeadAssets")
	if not (g and D and D[g] and assets and assets:FindFirstChild(g)) then
		return nil
	end
	local head = char:FindFirstChild("Head")
	if not (head and head:IsA("BasePart")) then
		return nil
	end
	-- the face's eye bones are the exact points the pieces were built around (older bodies: the eye attachments)
	local L = head:FindFirstChild("NC_FaceEyeL", true) or head:FindFirstChild("NC_LeftEyeAttachment")
	local R = head:FindFirstChild("NC_FaceEyeR", true) or head:FindFirstChild("NC_RightEyeAttachment")
	if not (L and R) or L.Parent ~= R.Parent then
		return nil
	end
	local l, r = rest(L), rest(R) -- (part space: both sit directly in the Head; the eyes may have been moved by a face shape slider; the hair goes by the skull)
	local mid = (l + r) / 2
	local scale = (l - r).Magnitude / D[g].eyeSpan
	return { char = char, head = head, cf = head.CFrame * CFrame.new(mid), rel = CFrame.new(mid), scale = scale, g = g, D = D[g], assets = assets[g] }
end

-- is there a mesh piece for this name on this body?
function H.has(fr, name)
	return fr and fr.D.pieces[name] ~= nil and fr.assets:FindFirstChild(name) ~= nil
end

-- clone one piece onto the head, welded. props: Color, Transparency, Material
function H.put(fr, name, parent, props)
	local info = fr.D.pieces[name]
	local template = fr.assets:FindFirstChild(name)
	if not (info and template) then
		return nil
	end
	local part = template:Clone()
	part.Size = template.Size * fr.scale
	local follow = H.FOLLOW[info.kind]
	local shift = follow and H.delta(fr.char, follow[1]) * follow[2] or Vector3.zero
	local rel = fr.rel * CFrame.new(info.offset * fr.scale + shift) -- where it sits in the Head's own frame
	part.CFrame = fr.head.CFrame * rel
	part.Anchored = false
	part.CanCollide, part.CanTouch, part.CanQuery, part.Massless = false, false, false, true
	part.Color = props.Color or part.Color
	part.Material = props.Material or Enum.Material.SmoothPlastic
	part.Transparency = props.Transparency or 0
	local sa = part:FindFirstChildOfClass("SurfaceAppearance")
	if sa then
		-- the greyscale texture takes the colour; the part colour only shows where the texture is see-through
		pcall(function()
			sa.Color = props.Color or part.Color
		end)
		if not props.Opaque then
			part.Transparency = math.max(part.Transparency, H.SOFT_T)
		end
	end
	part.CastShadow = props.CastShadow or false
	-- a classic Weld holds the exact offset from the Head (C0), whatever the parts' positions are when it is made;
	-- a WeldConstraint would freeze whatever gap there was at that moment (e.g. mid-teleport on these rigs)
	local w = Instance.new("Weld")
	w.Part0, w.Part1 = fr.head, part
	w.C0 = rel
	w.C1 = CFrame.identity
	w.Parent = part
	part.Parent = parent
	return part
end

-- which mesh name an item wants on this body: p.Male / p.Female (per body), or p.piece (both)
function H.pieceFor(fr, pp)
	return pp[fr.g] or pp.piece
end

local function mix(a, b, t)
	return Color3.new(a.R + (b.R - a.R) * t, a.G + (b.G - a.G) * t, a.B + (b.B - a.B) * t)
end
H.mix = mix

-- the hair for item params pp: the style (or its under-cap version when a hat is on).
-- Returns true when it wore mesh hair (so the procedural fallback is skipped).
function H.WearHair(fr, pp, parent, hair, skin, hatOn)
	local style = H.pieceFor(fr, pp)
	if not style then
		return false
	end
	local name = "Hair_" .. style
	if hatOn and H.has(fr, name .. "_Cap") then
		name ..= "_Cap"
	end
	-- hair-card styles: the strand cards lie over the painted scalp (Hair_<Style>_Cards, or the flattened
	-- Hair_<Style>_CapCards under a hat). They are thin, so they don't cast shadows.
	local cards = "Hair_" .. style .. (hatOn and "_CapCards" or "_Cards")
	local hasCards = H.has(fr, cards)
	if H.SOFT_SHELL[style] then
		hasCards = hasCards and "wisps"
	end
	local opaque = hasCards == true and H.CARD_SHELL_T < H.SOFT_T
	-- (the shell casts no shadow: Roblox's shadow ignores its soft edge, so the geometric edge of the shell, which
	--  reaches past the visible hairline, printed a dark sliver on the forehead and an outline at the fade)
	if not H.put(fr, name, parent, { Color = hair, Material = Enum.Material.SmoothPlastic, CastShadow = false,
		Transparency = opaque and H.CARD_SHELL_T or nil, Opaque = opaque }) then
		return false
	end
	if hasCards then
		H.put(fr, cards, parent, { Color = hair, Material = Enum.Material.SmoothPlastic })
		-- big card sets come in several parts (Roblox's 20k triangles a MeshPart): <name>_2, _3 ...
		local k = 2
		while H.has(fr, cards .. "_" .. k) do
			H.put(fr, cards .. "_" .. k, parent, { Color = hair, Material = Enum.Material.SmoothPlastic })
			k += 1
		end
	end
	return true
end

-- a face piece (brows, stubble) for item params pp. Returns true when it was worn, false when this body has no
-- mesh version (the caller then uses the procedural one), and "none" when this body simply doesn't get one
-- (a female body has no stubble).
function H.WearPiece(fr, pp, parent, colour)
	local name = H.pieceFor(fr, pp)
	if not name then
		return "none"
	end
	return H.put(fr, name, parent, { Color = colour, Transparency = pp.t }) ~= nil
end

-- lips and the lash line, on every MakeHuman face. Kept in their own folder, rebuilt when the skin changes.
function H.ApplyFace(char, skin)
	local old = char:FindFirstChild(H.FOLDER)
	if old then
		old:Destroy()
	end
	local fr = H.frame(char)
	if not fr then
		return nil
	end
	local folder = Instance.new("Folder")
	folder.Name = H.FOLDER
	H.put(fr, "Lips", folder, { Color = mix(skin, H.LIP_TINT, 0.28) })
	H.put(fr, "LashLine", folder, { Color = H.LASH })
	folder.Parent = char
	return folder
end

return H
