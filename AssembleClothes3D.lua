-- AssembleClothes3D.lua: paste in Studio's command bar after importing NC_Cloth_<Body>__<itemId>.fbx files.
-- Select the imported models first (or leave nothing selected to take every "NC_Cloth_*" model in Workspace).
-- Each garment's MeshParts go to ReplicatedStorage.NC_Clothes3D.<Body>.<itemId>; the imported rig (and any Bones the
-- importer put inside a MeshPart, which happens for one-mesh garments) is thrown away, so the clones bind to the
-- character's own bones. Re-running replaces an item's folder, so re-importing one file is enough to update one item.
local RS = game:GetService("ReplicatedStorage")
local Sel = game:GetService("Selection")

local REF_BONES = { "NC_SpineMid", "LowerTorso", "UpperTorso" } -- the first one found is the placement reference

local root = RS:FindFirstChild("NC_Clothes3D") or Instance.new("Folder")
root.Name = "NC_Clothes3D"
root.Parent = RS

local models = {}
for _, m in ipairs(Sel:Get()) do
	if m:IsA("Model") then
		table.insert(models, m)
	end
end
if #models == 0 then
	for _, m in ipairs(workspace:GetChildren()) do
		if m:IsA("Model") and m.Name:match("^NC_Cloth_") then
			table.insert(models, m)
		end
	end
end

local function findBone(m)
	for _, nm in ipairs(REF_BONES) do
		for _, d in ipairs(m:GetDescendants()) do
			if d:IsA("Bone") and d.Name == nm then
				return d
			end
		end
	end
	return nil
end

local done, parts, stripped = 0, 0, 0
for _, m in ipairs(models) do
	local body, item = m.Name:match("^NC_Cloth_(.-)__(.+)$")
	if not body then
		warn("AssembleClothes3D: skipped " .. m:GetFullName() .. " (name is not NC_Cloth_<Body>__<itemId>)")
		continue
	end
	local bone = findBone(m)
	if not bone then
		warn("AssembleClothes3D: skipped " .. m.Name .. " (no NC_SpineMid / LowerTorso bone in the import)")
		continue
	end
	local refCF = bone.WorldCFrame -- edit mode: no animation, so this is the rest pose
	local bf = root:FindFirstChild(body) or Instance.new("Folder")
	bf.Name = body
	bf.Parent = root
	local old = bf:FindFirstChild(item)
	if old then
		old:Destroy()
	end
	local f = Instance.new("Folder")
	f.Name = item
	for _, d in ipairs(m:GetDescendants()) do
		if d:IsA("MeshPart") and d.Name:find("__", 1, true) then
			d.Anchored = true
			d.CanCollide = false
			d.CanQuery = false
			d.CanTouch = false
			d.Massless = true
			pcall(function()
				d.DoubleSided = true -- (the game copy has no thickness, so the inside of sleeves must render)
			end)
			d:SetAttribute("NC_RelBone", bone.Name)
			d:SetAttribute("NC_Rel", refCF:ToObjectSpace(d.CFrame))
			d:SetAttribute("NC_RelTo", nil)
			for _, s in ipairs(d:GetDescendants()) do
				if s:IsA("SurfaceAppearance") then
					s:Destroy() -- one flat colour a part; NCClothes3D tints it from the look and the part's name
				end
			end
			for _, s in ipairs(d:GetDescendants()) do
				if s:IsA("Bone") then
					stripped += 1
					s:Destroy()
				end
			end
			d.TextureID = ""
			d.Parent = f
			parts += 1
		end
	end
	f.Parent = bf
	m:Destroy()
	done += 1
end
print(("AssembleClothes3D: %d garments, %d meshes filed under ReplicatedStorage.NC_Clothes3D (%d stray bones removed)")
	:format(done, parts, stripped))
