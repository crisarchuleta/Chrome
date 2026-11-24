-- AssembleClothes3D.lua: paste in Studio's command bar after importing NC_Cloth_<Body>__<itemId>.fbx files.
-- Select the imported models first (or leave nothing selected to take every "NC_Cloth_*" model in Workspace).
-- Each garment's MeshParts go to ReplicatedStorage.NC_Clothes3D.<Body>.<itemId>; the imported rig parts are thrown
-- away. Re-running replaces an item's folder, so re-importing one file is enough to update one item.
local RS = game:GetService("ReplicatedStorage")
local Sel = game:GetService("Selection")

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

local done, parts = 0, 0
for _, m in ipairs(models) do
	local body, item = m.Name:match("^NC_Cloth_(.-)__(.+)$")
	if not body then
		warn("AssembleClothes3D: skipped " .. m:GetFullName() .. " (name is not NC_Cloth_<Body>__<itemId>)")
		continue
	end
	local bf = root:FindFirstChild(body) or Instance.new("Folder")
	bf.Name = body
	bf.Parent = root
	local old = bf:FindFirstChild(item)
	if old then
		old:Destroy()
	end
	local f = Instance.new("Folder")
	f.Name = item
	-- the rest pose reference: the imported rig's LowerTorso (or the model's pivot when the importer made none)
	local ref = m:FindFirstChild("LowerTorso", true)
	local refCF = (ref and ref:IsA("BasePart")) and ref.CFrame or m:GetPivot()
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
			d:SetAttribute("NC_RelTo", "LowerTorso")
			d:SetAttribute("NC_Rel", refCF:ToObjectSpace(d.CFrame))
			for _, s in ipairs(d:GetChildren()) do
				if s:IsA("SurfaceAppearance") then
					s:Destroy() -- one flat colour a part; NCClothes3D tints it from the look
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
print(("AssembleClothes3D: %d garments, %d meshes filed under ReplicatedStorage.NC_Clothes3D"):format(done, parts))
