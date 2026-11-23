--!nonstrict
-- NCHead (ModuleScript, ReplicatedStorage): real mesh hair and face pieces for the MakeHuman heads.
--
-- The pieces are made by build_heads.py from each head's own scalp and face, so the hair grows out of a soft
-- hairline instead of sitting on top like a helmet, and every piece fits that head exactly:
--   Hair_<Style>        the hair (Male: Buzz, Crop, TaperFade, HighFade, SidePart, CurlyTop, Locs, Twists;
--                       Female: Pixie, Locs, LowBun, Ponytail, LongStraight, Bob)
--   Hair_<Style>_Cap    the same style pressed flat and trimmed, worn under a hat
--   Hair_<Style>_Fade   a see-through band along the hairline, so the hair fades into the skin
--   Brows_<Shape>       Natural, Thick, Arched, Straight, Thin
--   LashLine, Lips      on every face (the lips are tinted from the skin colour)
--   Stubble, StubbleHeavy   (Male)
-- Studio setup: import NC_Head_Male.fbx and NC_Head_Female.fbx and run AssembleHeads.lua, which files them in
-- ReplicatedStorage.NC_HeadAssets.<Gender>. NCHeadData holds where each piece sits.
--
-- Every piece is placed from the point between the eyes (the two NC_<Side>EyeAttachment on the head) and scaled by
-- the distance between the eyes, so the same pieces fit all five builds of each body.
local RS = game:GetService("ReplicatedStorage")

local H = {}
H.FOLDER = "NC_Face"
H.FADE_T = 0.45 -- how see-through the hairline band is
H.STUBBLE_T = { Stubble = 0.35, StubbleHeavy = 0.15 }
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
	local L = head:FindFirstChild("NC_LeftEyeAttachment")
	local R = head:FindFirstChild("NC_RightEyeAttachment")
	if not (L and R) then
		return nil
	end
	local l, r = rest(L), rest(R) -- (the eyes may have been moved by a face shape slider; the hair goes by the skull)
	local mid = (l + r) / 2
	local scale = (l - r).Magnitude / D[g].eyeSpan
	return { char = char, head = head, cf = head.CFrame * CFrame.new(mid), scale = scale, g = g, D = D[g], assets = assets[g] }
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
	part.CFrame = fr.cf * CFrame.new(info.offset * fr.scale + shift)
	part.Anchored = false
	part.CanCollide, part.CanTouch, part.CanQuery, part.Massless = false, false, false, true
	part.Color = props.Color or part.Color
	part.Material = props.Material or Enum.Material.SmoothPlastic
	part.Transparency = props.Transparency or 0
	part.CastShadow = props.CastShadow or false
	local w = Instance.new("WeldConstraint")
	w.Part0, w.Part1 = fr.head, part
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

-- the hair for item params pp: the style (or its under-cap version when a hat is on) and its hairline fade.
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
	if not H.put(fr, name, parent, { Color = hair, Material = Enum.Material.SmoothPlastic, CastShadow = true }) then
		return false
	end
	H.put(fr, "Hair_" .. style .. "_Fade", parent, { Color = mix(hair, skin, 0.25), Transparency = H.FADE_T })
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
	local t = pp.t or H.STUBBLE_T[name] or 0
	return H.put(fr, name, parent, { Color = colour, Transparency = t }) ~= nil
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
