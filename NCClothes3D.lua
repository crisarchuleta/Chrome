-- NCClothes3D (ModuleScript, ReplicatedStorage): real 3D catalog clothes on the MakeHuman bodies.
--
-- AssembleClothes3D.lua files the imported garments as ReplicatedStorage.NC_Clothes3D.<BodyId>.<itemId> (a Folder of
-- skinned MeshParts). NCLookBuilder asks Template(char, itemId); when one exists the item is worn as these meshes
-- instead of painting the body parts. The base layer (tank top + shorts in the body mesh) always stays underneath.
--
-- Each MeshPart is named <itemId>__<role>__<key>__<n>. key = which look colour it takes: c1, c2, mix (half way between
-- them) or fix (keeps its imported colour: camo patches, zip teeth). Attribute NC_Rel (CFrame) is the part's rest
-- offset from the body part named in NC_RelTo, so it starts in place before the skin binds it to the bones.

local RS = game:GetService("ReplicatedStorage")

local M = {}
M.FOLDER = "NC_Clothes3D"
M.Enabled = true

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

local function keyOf(name)
	local parts = string.split(name, "__")
	return parts[3] or "c1"
end

-- Wear(char, template, ctx, parent) -> the Folder of worn meshes. ctx.c1 / ctx.c2 are the look's Color3s.
function M.Wear(char, tpl, ctx, parent)
	local folder = Instance.new("Folder") -- a Folder, not a Model: the skinned meshes must sit in the character's Model
	folder.Name = tpl.Name
	for _, src in ipairs(tpl:GetChildren()) do
		if src:IsA("MeshPart") then
			local mp = src:Clone()
			local key = keyOf(src.Name)
			local c1, c2 = ctx.c1, ctx.c2 or ctx.c1
			if key == "c1" and c1 then
				mp.Color = c1
			elseif key == "c2" and c2 then
				mp.Color = c2
			elseif key == "mix" and c1 and c2 then
				mp.Color = c1:Lerp(c2, 0.5)
			end
			mp.Material = Enum.Material.Fabric
			mp.Anchored = false
			mp.CanCollide = false
			mp.CanQuery = false
			mp.CanTouch = false
			mp.Massless = true
			local relTo = char:FindFirstChild(src:GetAttribute("NC_RelTo") or "LowerTorso")
			local rel = src:GetAttribute("NC_Rel")
			if relTo and relTo:IsA("BasePart") then
				if typeof(rel) == "CFrame" then
					mp.CFrame = relTo.CFrame * rel
				end
				local w = Instance.new("Weld") -- holds it with the body; the skin weights do the bending
				w.Part0 = relTo
				w.Part1 = mp
				w.C0 = typeof(rel) == "CFrame" and rel or relTo.CFrame:ToObjectSpace(mp.CFrame)
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
