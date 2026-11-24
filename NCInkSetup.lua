--!nonstrict
-- NCInkSetup (ModuleScript, Studio only): one-time setup for the tattoo textures.
--
-- 1. File > Import 3D: NCInkSwatches_1.glb and NCInkSwatches_2.glb (every tattoo PNG on a plane named after the
--    file, split in two so each file stays under the 20 MB upload limit). Studio uploads the images as it imports.
-- 2. Command bar (once per swatch model; the missing-list is only complete after the second):
--      require(game.ServerStorage.NCInkSetup).Prepare(workspace.NCInkSwatches_1)
--      require(game.ServerStorage.NCInkSetup).Prepare(workspace.NCInkSwatches_2)
--    Each plane's texture asset id is saved to ReplicatedStorage.NCInkIds as a StringValue named after the file
--    (e.g. "sl_rosas_nubes_L"). The report lists anything missing. Delete the swatch model afterwards.
-- 3. Import NC_Ink_<Body>.fbx for each of the 10 bodies (3D Importer, Rig: none; they are plain rigid meshes) into
--    ReplicatedStorage.NCInkRigs as Models named <Body>. Replace any older skinned copies.
local RS = game:GetService("ReplicatedStorage")

local S = {}

local function texOf(mp)
	if mp.TextureID ~= "" then
		return mp.TextureID
	end
	local sa = mp:FindFirstChildOfClass("SurfaceAppearance")
	if sa and sa.ColorMap ~= "" then
		return sa.ColorMap
	end
	return ""
end

function S.Prepare(model)
	local ids = RS:FindFirstChild("NCInkIds") or Instance.new("Folder")
	ids.Name = "NCInkIds"
	ids.Parent = RS
	local n, missing = 0, {}
	for _, mp in ipairs(model:GetDescendants()) do
		if mp:IsA("MeshPart") then
			local name = mp.Name:gsub("^Swatch_", "")
			local id = texOf(mp)
			if id ~= "" then
				local v = ids:FindFirstChild(name) or Instance.new("StringValue")
				v.Name = name
				v.Value = id
				v.Parent = ids
				n += 1
			else
				table.insert(missing, name)
			end
		end
	end
	-- check against the catalog
	local ok, Catalog = pcall(require, RS:FindFirstChild("NCInkCatalog"))
	if ok then
		for _, it in ipairs(Catalog.ITEMS) do
			for _, file in pairs(it.files) do
				if not ids:FindFirstChild(file) then
					table.insert(missing, file)
				end
			end
		end
	end
	print(("[NCInkSetup] saved %d tattoo textures, %d missing"):format(n, #missing))
	for _, m in ipairs(missing) do
		print("   missing:", m)
	end
	return n, missing
end

return S
