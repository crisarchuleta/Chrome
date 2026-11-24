-- NCClothes3D (ModuleScript, ReplicatedStorage): real 3D catalog clothes on the MakeHuman bodies.
--
-- AssembleClothes3D.lua files the imported garments as ReplicatedStorage.NC_Clothes3D.<BodyId>.<itemId> (a Folder of
-- skinned MeshParts, their imported bones removed). NCLookBuilder asks Template(char, itemId); when one exists the
-- item is worn as these meshes instead of painting the body parts. The base layer (tank top + shorts in the body mesh)
-- always stays underneath.
--
-- Each MeshPart is named <itemId>__<role>__<key>__<n>. key = which look colour it takes: c1, c2, mix (half way between
-- them), dk2 (a darker c2, camo shadows) or fix-RRGGBB (a fixed colour: zip teeth, trims). Role endings say when a
-- part is left off: "-arm" (a top's sleeve) and "-under" (the top's body a jacket covers) under a 3D jacket, so a top
-- can never poke through one; "-hip" (a bottom above the hip line) under a long 3D top, whose parts end in "__L".
-- Attribute NC_Rel (CFrame) is the part's rest offset from the bone named in NC_RelBone (rest pose, no animation), so
-- the skinned mesh starts bound in place on every body; NC_RelTo (a body part name) is the older fallback.

local RS = game:GetService("ReplicatedStorage")

local M = {}
M.FOLDER = "NC_Clothes3D"
M.Enabled = true
M.Material = Enum.Material.SmoothPlastic -- (Fabric draws a chunky knit on everything, jeans included)

local function root()
	return RS:FindFirstChild(M.FOLDER)
end

function M.Template(char, itemId)
	if not M.Enabled or not char or not itemId then
		return nil
	end
	local r = root()
	local body = char:GetAttribute("NC_BodyId")
	if not (r and body) then
		return nil
	end
	local b = r:FindFirstChild(body)
	local t = b and b:FindFirstChild(itemId)
	if t and #t:GetChildren() > 0 then
		return t
	end
	return nil
end

local function nameParts(name)
	local parts = string.split(name, "__")
	return parts[2] or "", parts[3] or "c1"
end

local function roleEnds(name, suffix)
	local role = nameParts(name)
	return string.sub(role, -#suffix) == suffix
end

function M.IsSleeve(name)
	return roleEnds(name, "-arm")
end

-- true when a top template reaches far enough down to cover a bottom's "-hip" parts
function M.IsLongTop(tpl)
	for _, c in ipairs(tpl:GetChildren()) do
		if string.sub(c.Name, -3) == "__L" then
			return true
		end
	end
	return false
end

local function hidden(name, opts)
	if opts.hideSleeves and (roleEnds(name, "-arm") or roleEnds(name, "-under")) then
		return true
	end
	return opts.hideHip and roleEnds(name, "-hip") or false
end

-- the bone's rest frame in world space: its part's CFrame times the chain of Bone.CFrame (Transform, the animated
-- offset, left out), so the garment binds to the rest pose even while the character is moving
local function boneRest(char, boneName)
	if not boneName then
		return nil
	end
	for _, d in ipairs(char:GetDescendants()) do
		if d:IsA("Bone") and d.Name == boneName then
			local cf = d.CFrame
			local p = d.Parent
			while p and p:IsA("Bone") do
				cf = p.CFrame * cf
				p = p.Parent
			end
			if p and p:IsA("BasePart") then
				return p, cf -- part, rest offset of the bone in that part's space
			end
			return nil
		end
	end
	return nil
end

-- Wear(char, template, ctx, parent, opts) -> the Folder of worn meshes. ctx.c1 / ctx.c2 are the look's Color3s;
-- opts.hideSleeves leaves out a top's "-arm" and "-under" parts (a 3D jacket is worn over it); opts.hideHip leaves
-- out a bottom's "-hip" parts (a long 3D top is worn over it).
function M.Wear(char, tpl, ctx, parent, opts)
	opts = opts or {}
	local folder = Instance.new("Folder") -- a Folder, not a Model: the skinned meshes must sit in the character's Model
	folder.Name = tpl.Name
	local boneCache = {}
	for _, src in ipairs(tpl:GetChildren()) do
		if src:IsA("MeshPart") and not hidden(src.Name, opts) then
			local mp = src:Clone()
			for _, d in ipairs(mp:GetDescendants()) do
				if d:IsA("Bone") then
					d:Destroy() -- (bones inside a skinned clone keep it stiff and scramble the body's own skin)
				end
			end
			local _, key = nameParts(src.Name)
			local c1, c2 = ctx.c1, ctx.c2 or ctx.c1
			if key == "c1" and c1 then
				mp.Color = c1
			elseif key == "c2" and c2 then
				mp.Color = c2
			elseif key == "mix" and c1 and c2 then
				mp.Color = c1:Lerp(c2, 0.5)
			elseif key == "dk2" and c2 then
				mp.Color = Color3.new(c2.R * 0.55, c2.G * 0.55, c2.B * 0.55)
			elseif string.sub(key, 1, 4) == "fix-" then
				local ok, col = pcall(Color3.fromHex, string.sub(key, 5))
				if ok then
					mp.Color = col
				end
			end
			mp.Material = M.Material
			mp.Anchored = false
			mp.CanCollide = false
			mp.CanQuery = false
			mp.CanTouch = false
			mp.Massless = true
			mp.CastShadow = true
			local rel = src:GetAttribute("NC_Rel")
			local boneName = src:GetAttribute("NC_RelBone")
			local part, off
			if boneName then
				local hit = boneCache[boneName]
				if hit == nil then
					local p, cf = boneRest(char, boneName)
					hit = p and { p, cf } or false
					boneCache[boneName] = hit
				end
				if hit then
					part, off = hit[1], hit[2]
				end
			end
			if not part then -- older installs: offset from a body part
				local relTo = char:FindFirstChild(src:GetAttribute("NC_RelTo") or "LowerTorso")
				if relTo and relTo:IsA("BasePart") then
					part, off = relTo, CFrame.new()
				end
			end
			if part then
				local c0 = typeof(rel) == "CFrame" and (off * rel) or part.CFrame:ToObjectSpace(mp.CFrame)
				mp.CFrame = part.CFrame * c0
				local w = Instance.new("Weld") -- holds it with the body; the skin weights do the bending
				w.Part0 = part
				w.Part1 = mp
				w.C0 = c0
				w.Parent = mp
			end
			mp:SetAttribute("NC_Look", tpl.Name)
			mp.Parent = folder
		end
	end
	folder.Parent = parent
	return folder
end

return M
