--!nonstrict
-- NCInk (ModuleScript in ReplicatedStorage): real tattoo ink for the MakeHuman bodies.
--
-- How it works (same idea as the car vinyls): every body has 13 thin "ink layer" MeshParts that sit 1 mm above the
-- skin, one per R15 part. They are rigid (no skin weights) and welded to their part, like the R15 body parts. A tattoo is just a
-- transparent PNG set as the layer's TextureID. Clothes sit above the layer, so anything covered by clothes hides
-- the ink with no extra code. Nothing is ever printed on the torso.
--
-- Pieces:
--   NC_Ink_<Body>.fbx      the 13 layers (Ink_LeftUpperArm ... Ink_Face) as plain meshes, no rig. Import each with
--                          the 3D Importer (Rig: none) into ReplicatedStorage.NCInkRigs as a Model named <Body>
--                          (e.g. "Male_Average"). Where it lands doesn't matter: Attach places every layer itself.
--   NCInkSwatches_1.glb + NCInkSwatches_2.glb      every tattoo PNG on its own plane. Import it once into Workspace, run
--                          NCInkSetup.Prepare(model) from the command bar: it saves each texture's asset id into
--                          ReplicatedStorage.NCInkIds (StringValues named after the file) and you can delete the model.
--   NCInkCatalog           the tattoo list (generated from ink_catalog.json).
--
-- A look's ink is a table:
--   { L = { upper = id, lower = id, hand = id, leg = id }, R = { ... }, neck = id, face = id }
-- A full sleeve (zone "full") fills both upper and lower on that arm; a leg sleeve fills the thigh and calf.
local RS = game:GetService("ReplicatedStorage")
local Catalog = require(RS:WaitForChild("NCInkCatalog"))

local Ink = {}

-- which layers each area/zone prints on (layer names without the side)
Ink.ZONES = {
	Arm = { upper = { "UpperArm" }, lower = { "LowerArm" }, full = { "UpperArm", "LowerArm" } },
	Leg = { lower = { "LowerLeg" }, full = { "UpperLeg", "LowerLeg" } },
	Hand = { hand = { "Hand" } },
	Neck = { neck = { "NeckHead", "NeckUpperTorso" } },
	Face = { face = { "Face" } },
}
Ink.LAYERS = {
	"Ink_LeftUpperArm", "Ink_LeftLowerArm", "Ink_LeftHand", "Ink_LeftUpperLeg", "Ink_LeftLowerLeg",
	"Ink_RightUpperArm", "Ink_RightLowerArm", "Ink_RightHand", "Ink_RightUpperLeg", "Ink_RightLowerLeg",
	"Ink_NeckHead", "Ink_NeckUpperTorso", "Ink_Face",
}

-- where each layer sits on its body part, measured in Blender from NC_Ink_<Body>.fbx and the body's R15 parts:
-- { offset of the layer's centre from the part's centre, layer size } both as fractions of the part's Size, in the
-- part's own axes. Fractions keep it right at any body scale. (tools/ink/ink_fit.py writes this table.)
Ink.FIT = {
	Female_Athletic = {
		Ink_Face = { 0, 0.15735, -0.1878, 1.01204, 0.63635, 0.63425 },
		Ink_LeftHand = { -0.03494, -0.00135, 0.00087, 0.96496, 1.004, 1.01516 },
		Ink_LeftLowerArm = { -0.00008, -0.00253, 0.00009, 1.02433, 1.00618, 1.02881 },
		Ink_LeftLowerLeg = { -0.01407, -0.03524, 0.01716, 0.98852, 1.01381, 0.97941 },
		Ink_LeftUpperArm = { -0.02072, 0.03996, 0.03946, 0.97906, 1.05587, 0.92574 },
		Ink_LeftUpperLeg = { -0.00003, -0.02103, 0, 1.01264, 1.04273, 1.01167 },
		Ink_NeckHead = { 0, -0.1666, 0.0187, 0.95971, 0.42872, 0.7886 },
		Ink_NeckUpperTorso = { 0, 0.35713, 0.06838, 0.96158, 0.31051, 0.70603 },
		Ink_RightHand = { 0.03494, -0.00135, 0.00087, 0.96496, 1.004, 1.01516 },
		Ink_RightLowerArm = { 0.00008, -0.00253, 0.00009, 1.02433, 1.00618, 1.02881 },
		Ink_RightLowerLeg = { 0.01407, -0.03524, 0.01716, 0.98852, 1.01381, 0.97941 },
		Ink_RightUpperArm = { 0.02072, 0.03996, 0.03946, 0.97906, 1.05587, 0.92574 },
		Ink_RightUpperLeg = { 0.00003, -0.02103, 0, 1.01264, 1.04273, 1.01167 },
	},
	Female_Average = {
		Ink_Face = { 0, 0.16619, -0.18781, 1.01202, 0.61992, 0.63421 },
		Ink_LeftHand = { -0.06279, -0.00131, 0.00102, 0.91085, 1.00406, 1.01509 },
		Ink_LeftLowerArm = { -0.00012, -0.00282, -0.00001, 1.02476, 1.006, 1.02809 },
		Ink_LeftLowerLeg = { -0.0103, -0.03726, 0.02797, 0.99552, 1.00941, 0.95733 },
		Ink_LeftUpperArm = { -0.04149, 0.03651, 0.04782, 0.93772, 1.05398, 0.9178 },
		Ink_LeftUpperLeg = { -0.00005, -0.00929, -0.00078, 1.01189, 1.01996, 1.00981 },
		Ink_NeckHead = { 0, -0.14903, 0.01865, 0.9597, 0.40792, 0.78856 },
		Ink_NeckUpperTorso = { 0, 0.36657, 0.05842, 0.96122, 0.29777, 0.68012 },
		Ink_RightHand = { 0.06279, -0.00131, 0.00102, 0.91085, 1.00406, 1.01509 },
		Ink_RightLowerArm = { 0.00012, -0.00282, -0.00001, 1.02476, 1.006, 1.02809 },
		Ink_RightLowerLeg = { 0.0103, -0.03726, 0.02797, 0.99552, 1.00941, 0.95733 },
		Ink_RightUpperArm = { 0.04149, 0.03651, 0.04782, 0.93772, 1.05398, 0.9178 },
		Ink_RightUpperLeg = { 0.00005, -0.00929, -0.00078, 1.01189, 1.01996, 1.0098 },
	},
	Female_Heavy = {
		Ink_Face = { 0, 0.1662, -0.19692, 1.01203, 0.61989, 0.6157 },
		Ink_LeftHand = { -0.08625, -0.00129, 0.00403, 0.85531, 1.00408, 1.00791 },
		Ink_LeftLowerArm = { -0.0002, 0.00612, -0.00015, 1.02265, 0.98822, 1.02542 },
		Ink_LeftLowerLeg = { -0.00971, -0.03722, 0.02902, 0.99599, 1.00861, 0.95472 },
		Ink_LeftUpperArm = { -0.0955, 0.0311, 0.07405, 0.82501, 1.06986, 0.86264 },
		Ink_LeftUpperLeg = { 0.00013, -0.00994, -0.00047, 1.01033, 1.02105, 1.00748 },
		Ink_NeckHead = { 0, -0.14968, 0.01156, 0.9597, 0.40925, 0.78311 },
		Ink_NeckUpperTorso = { 0, 0.20791, 0.05259, 0.96133, 0.59087, 0.67971 },
		Ink_RightHand = { 0.08625, -0.00129, 0.00403, 0.85531, 1.00408, 1.00791 },
		Ink_RightLowerArm = { 0.0002, 0.00612, -0.00015, 1.02265, 0.98822, 1.02542 },
		Ink_RightLowerLeg = { 0.00971, -0.03722, 0.02902, 0.99599, 1.00861, 0.95472 },
		Ink_RightUpperArm = { 0.0955, 0.0311, 0.07405, 0.82501, 1.06986, 0.86264 },
		Ink_RightUpperLeg = { -0.00013, -0.00994, -0.00047, 1.01033, 1.02105, 1.00748 },
	},
	Female_Muscular = {
		Ink_Face = { 0, 0.15586, -0.2002, 1.01203, 0.63911, 0.60905 },
		Ink_LeftHand = { -0.07623, -0.00123, 0.00102, 0.88284, 1.00421, 1.01509 },
		Ink_LeftLowerArm = { -0.00014, -0.00252, 0.00001, 1.02161, 1.00652, 1.02613 },
		Ink_LeftLowerLeg = { -0.0192, -0.02453, 0.00004, 0.97736, 1.0353, 1.01304 },
		Ink_LeftUpperArm = { 0.0004, 0.02573, 0.0329, 1.0183, 1.05241, 0.94589 },
		Ink_LeftUpperLeg = { -0.00003, -0.02269, 0.00001, 1.0118, 1.04653, 1.01091 },
		Ink_NeckHead = { 0, -0.17144, 0.01794, 0.9597, 0.42518, 0.797 },
		Ink_NeckUpperTorso = { 0, 0.29412, 0.07036, 0.97838, 0.41485, 0.75125 },
		Ink_RightHand = { 0.07623, -0.00123, 0.00102, 0.88284, 1.00421, 1.01509 },
		Ink_RightLowerArm = { 0.00014, -0.00252, 0.00001, 1.02161, 1.00652, 1.02613 },
		Ink_RightLowerLeg = { 0.0192, -0.02453, 0.00004, 0.97736, 1.0353, 1.01304 },
		Ink_RightUpperArm = { -0.0004, 0.02573, 0.0329, 1.0183, 1.05241, 0.94589 },
		Ink_RightUpperLeg = { 0.00003, -0.02269, 0.00001, 1.0118, 1.04653, 1.01091 },
	},
	Female_Skinny = {
		Ink_Face = { 0, 0.15754, -0.1878, 1.01203, 0.63411, 0.63424 },
		Ink_LeftHand = { -0.08617, -0.00126, 0.00403, 0.85548, 1.00417, 1.00795 },
		Ink_LeftLowerArm = { -0.00444, -0.0021, 0.00012, 1.03525, 1.00557, 1.02918 },
		Ink_LeftLowerLeg = { -0.00699, -0.02676, 0.00003, 1.00533, 1.03082, 1.01498 },
		Ink_LeftUpperArm = { -0.0089, 0.01378, 0.04509, 1.00443, 1.01891, 0.95417 },
		Ink_LeftUpperLeg = { -0.00008, -0.00377, -0.00007, 1.01487, 1.0076, 1.01398 },
		Ink_NeckHead = { 0, -0.16528, 0.01841, 0.95975, 0.42837, 0.78857 },
		Ink_NeckUpperTorso = { 0, 0.37179, 0.09041, 0.96723, 0.28851, 0.67614 },
		Ink_RightHand = { 0.08617, -0.00126, 0.00403, 0.85548, 1.00417, 1.00795 },
		Ink_RightLowerArm = { 0.00444, -0.0021, 0.00012, 1.03525, 1.00557, 1.02918 },
		Ink_RightLowerLeg = { 0.00699, -0.02676, 0.00003, 1.00533, 1.03082, 1.01498 },
		Ink_RightUpperArm = { 0.02504, 0.01378, 0.07882, 0.97141, 1.01891, 0.88465 },
		Ink_RightUpperLeg = { 0.00008, -0.00377, -0.00007, 1.01487, 1.0076, 1.01398 },
	},
	Male_Athletic = {
		Ink_Face = { 0, 0.18704, -0.18763, 1.01249, 0.60794, 0.63469 },
		Ink_LeftHand = { -0.09276, -0.00147, 0.00456, 0.8406, 1.00371, 1.00506 },
		Ink_LeftLowerArm = { -0.00294, 0.0054, 0.00005, 1.02918, 1.01089, 1.02604 },
		Ink_LeftLowerLeg = { -0.00012, -0.02163, 0.03409, 1.01759, 1.06157, 0.94588 },
		Ink_LeftUpperArm = { -0.12941, 0.03139, 0.01245, 0.75602, 1.03836, 0.80968 },
		Ink_LeftUpperLeg = { -0.00005, 0.00789, 0.00002, 1.01331, 0.98409, 1.01269 },
		Ink_NeckHead = { 0, -0.14274, 0.03285, 0.99219, 0.47934, 0.8982 },
		Ink_NeckUpperTorso = { 0, 0.31518, 0.06828, 0.98221, 0.38096, 0.83008 },
		Ink_RightHand = { 0.09276, -0.00147, 0.00456, 0.8406, 1.00371, 1.00506 },
		Ink_RightLowerArm = { 0.00294, 0.0054, 0.00005, 1.02918, 1.01089, 1.02604 },
		Ink_RightLowerLeg = { 0.00012, -0.02163, 0.03409, 1.01759, 1.06157, 0.94588 },
		Ink_RightUpperArm = { 0.12941, 0.03139, 0.01245, 0.75602, 1.03836, 0.80968 },
		Ink_RightUpperLeg = { 0.00005, 0.00789, 0.00002, 1.01331, 0.98409, 1.01269 },
	},
	Male_Average = {
		Ink_Face = { 0, 0.18689, -0.18761, 1.01251, 0.60823, 0.63473 },
		Ink_LeftHand = { -0.09272, -0.00501, 0.00453, 0.84068, 0.99669, 1.00512 },
		Ink_LeftLowerArm = { -0.0002, -0.01246, 0.01105, 1.02272, 0.98685, 1.00165 },
		Ink_LeftLowerLeg = { -0.0001, -0.02315, 0.03606, 1.01736, 1.05817, 0.94176 },
		Ink_LeftUpperArm = { -0.12462, 0.01466, -0.04468, 0.76538, 1.063, 0.78856 },
		Ink_LeftUpperLeg = { -0.00004, 0.01363, 0.00003, 1.01288, 0.97333, 1.01216 },
		Ink_NeckHead = { 0, -0.14281, 0.03696, 0.99217, 0.47973, 0.90638 },
		Ink_NeckUpperTorso = { 0, 0.2702, 0.05293, 0.97425, 0.46128, 0.80095 },
		Ink_RightHand = { 0.09272, -0.00501, 0.00453, 0.84068, 0.99669, 1.00512 },
		Ink_RightLowerArm = { 0.0002, -0.01246, 0.01105, 1.02272, 0.98685, 1.00165 },
		Ink_RightLowerLeg = { 0.0001, -0.02315, 0.03606, 1.01736, 1.05817, 0.94176 },
		Ink_RightUpperArm = { 0.12462, 0.01466, -0.02677, 0.76538, 1.063, 0.76262 },
		Ink_RightUpperLeg = { 0.00004, 0.01363, 0.00003, 1.01288, 0.97333, 1.01216 },
	},
	Male_Heavy = {
		Ink_Face = { 0, 0.18764, -0.19244, 1.01251, 0.6067, 0.62492 },
		Ink_LeftHand = { -0.09328, -0.00139, 0.00441, 0.83953, 1.00391, 1.0054 },
		Ink_LeftLowerArm = { -0.00024, 0.0023, 0.00002, 1.02033, 0.99608, 1.0232 },
		Ink_LeftLowerLeg = { -0.00005, -0.02633, 0.03621, 1.01644, 1.05109, 0.94141 },
		Ink_LeftUpperArm = { -0.09642, 0.02576, 0.06092, 0.82207, 1.05282, 0.80456 },
		Ink_LeftUpperLeg = { 0, -0.00203, -0.00001, 1.0122, 1.00358, 1.01154 },
		Ink_NeckHead = { 0, -0.14405, 0.02462, 0.99218, 0.48077, 0.88429 },
		Ink_NeckUpperTorso = { 0, 0.21342, 0.02069, 0.98708, 0.57508, 0.85764 },
		Ink_RightHand = { 0.09328, -0.00139, 0.00441, 0.83953, 1.00391, 1.0054 },
		Ink_RightLowerArm = { 0.00024, 0.0023, 0.00002, 1.02033, 0.99608, 1.0232 },
		Ink_RightLowerLeg = { 0.00005, -0.02633, 0.03621, 1.01644, 1.05109, 0.94141 },
		Ink_RightUpperArm = { 0.09642, 0.02576, 0.06092, 0.82207, 1.05282, 0.80456 },
		Ink_RightUpperLeg = { 0, -0.00203, -0.00001, 1.0122, 1.00358, 1.01154 },
	},
	Male_Muscular = {
		Ink_Face = { 0, 0.18667, -0.20426, 1.0125, 0.60864, 0.60091 },
		Ink_LeftHand = { -0.0928, 0.00022, 0.00456, 0.84055, 1.00708, 1.00505 },
		Ink_LeftLowerArm = { -0.00003, 0.00234, 0.00011, 1.0211, 0.9964, 1.02285 },
		Ink_LeftLowerLeg = { -0.00014, -0.0261, 0.02981, 1.01643, 1.05204, 0.9539 },
		Ink_LeftUpperArm = { -0.11531, 0.02601, 0.02714, 0.78344, 1.07495, 0.85862 },
		Ink_LeftUpperLeg = { -0.00005, 0.00001, 0.00001, 1.01203, 1.0004, 1.01235 },
		Ink_NeckHead = { 0, -0.14348, 0.00833, 0.99217, 0.48037, 0.85806 },
		Ink_NeckUpperTorso = { 0, 0.25644, 0.05163, 0.92219, 0.4887, 0.86884 },
		Ink_RightHand = { 0.0928, 0.00022, 0.00456, 0.84055, 1.00708, 1.00505 },
		Ink_RightLowerArm = { 0.00003, 0.00234, 0.00011, 1.0211, 0.9964, 1.02285 },
		Ink_RightLowerLeg = { 0.00014, -0.0261, 0.02981, 1.01643, 1.05204, 0.9539 },
		Ink_RightUpperArm = { 0.12283, 0.02601, 0.02714, 0.76814, 1.07495, 0.85862 },
		Ink_RightUpperLeg = { 0.00005, 0, 0.00001, 1.01203, 1.00038, 1.01235 },
	},
	Male_Skinny = {
		Ink_Face = { 0, 0.18776, -0.18762, 1.01249, 0.60655, 0.6347 },
		Ink_LeftHand = { -0.09273, -0.00473, 0.00455, 0.84066, 0.99718, 1.00508 },
		Ink_LeftLowerArm = { -0.00623, -0.00253, -0.00018, 1.03763, 1.00754, 1.02643 },
		Ink_LeftLowerLeg = { -0.00009, -0.02644, 0.03773, 1.01878, 1.05128, 0.93891 },
		Ink_LeftUpperArm = { -0.14352, 0.02061, -0.04874, 0.72784, 1.04207, 0.83624 },
		Ink_LeftUpperLeg = { -0.00001, 0.01299, -0.00003, 1.01643, 0.97378, 1.01332 },
		Ink_NeckHead = { 0, -0.13438, 0.03261, 0.99218, 0.46477, 0.89737 },
		Ink_NeckUpperTorso = { 0, 0.29921, 0.06699, 0.97626, 0.44813, 0.79491 },
		Ink_RightHand = { 0.09273, -0.00473, 0.00455, 0.84066, 0.99718, 1.00508 },
		Ink_RightLowerArm = { 0.00623, -0.00253, -0.00018, 1.03763, 1.00754, 1.02643 },
		Ink_RightLowerLeg = { 0.00009, -0.02644, 0.03773, 1.01878, 1.05128, 0.93891 },
		Ink_RightUpperArm = { 0.04318, 0.02061, 0.02302, 0.93269, 1.04207, 0.9692 },
		Ink_RightUpperLeg = { 0.00001, 0.01299, -0.00003, 1.01643, 0.97378, 1.01332 },
	},
}

-- the R15 part sizes (studs) Ink.FIT was measured on (character-studio/rig/NeonCoast_MakeHumanRig.blend, 2026-11-23 18:54 build); Attach warns when a body's part differs (wrong body file)
Ink.PART_SIZE = {
	Female_Athletic = {
		Head = Vector3.new(0.6089, 1.0635, 0.7404),
		LeftHand = Vector3.new(0.2104, 0.6444, 0.4312),
		LeftLowerArm = Vector3.new(0.2991, 0.8208, 0.2525),
		LeftLowerLeg = Vector3.new(0.4302, 1.5166, 0.5294),
		LeftUpperArm = Vector3.new(0.3483, 1.0363, 0.5113),
		LeftUpperLeg = Vector3.new(0.5737, 1.0384, 0.6178),
		RightHand = Vector3.new(0.2104, 0.6444, 0.4312),
		RightLowerArm = Vector3.new(0.2991, 0.8208, 0.2525),
		RightLowerLeg = Vector3.new(0.4302, 1.5166, 0.5294),
		RightUpperArm = Vector3.new(0.3483, 1.0363, 0.5113),
		RightUpperLeg = Vector3.new(0.5737, 1.0384, 0.6178),
		UpperTorso = Vector3.new(1.4635, 1.8788, 0.8529),
	},
	Female_Average = {
		Head = Vector3.new(0.6082, 1.0904, 0.7394),
		LeftHand = Vector3.new(0.2009, 0.6439, 0.4245),
		LeftLowerArm = Vector3.new(0.292, 0.8151, 0.2552),
		LeftLowerLeg = Vector3.new(0.4476, 1.526, 0.5503),
		LeftUpperArm = Vector3.new(0.3487, 1.0339, 0.5315),
		LeftUpperLeg = Vector3.new(0.608, 1.8348, 0.6387),
		RightHand = Vector3.new(0.2009, 0.6439, 0.4245),
		RightLowerArm = Vector3.new(0.292, 0.8151, 0.2552),
		RightLowerLeg = Vector3.new(0.4476, 1.526, 0.5503),
		RightUpperArm = Vector3.new(0.3487, 1.0339, 0.5315),
		RightUpperLeg = Vector3.new(0.608, 1.8347, 0.6387),
		UpperTorso = Vector3.new(1.4568, 1.871, 0.8856),
	},
	Female_Heavy = {
		Head = Vector3.new(0.6083, 1.0906, 0.7616),
		LeftHand = Vector3.new(0.2632, 0.645, 0.4556),
		LeftLowerArm = Vector3.new(0.3175, 0.8222, 0.2843),
		LeftLowerLeg = Vector3.new(0.4716, 1.517, 0.5735),
		LeftUpperArm = Vector3.new(0.449, 1.0296, 0.6168),
		LeftUpperLeg = Vector3.new(0.6832, 1.8303, 0.8539),
		RightHand = Vector3.new(0.2632, 0.645, 0.4556),
		RightLowerArm = Vector3.new(0.3175, 0.8222, 0.2843),
		RightLowerLeg = Vector3.new(0.4716, 1.517, 0.5735),
		RightUpperArm = Vector3.new(0.449, 1.0296, 0.6168),
		RightUpperLeg = Vector3.new(0.6832, 1.8304, 0.8539),
		UpperTorso = Vector3.new(1.4877, 1.909, 1.0079),
	},
	Female_Muscular = {
		Head = Vector3.new(0.6083, 1.0578, 0.7701),
		LeftHand = Vector3.new(0.2073, 0.6445, 0.4247),
		LeftLowerArm = Vector3.new(0.3314, 0.8236, 0.2796),
		LeftLowerLeg = Vector3.new(0.456, 1.5184, 0.5476),
		LeftUpperArm = Vector3.new(0.3818, 1.061, 0.5806),
		LeftUpperLeg = Vector3.new(0.613, 1.0334, 0.666),
		RightHand = Vector3.new(0.2073, 0.6445, 0.4247),
		RightLowerArm = Vector3.new(0.3314, 0.8236, 0.2796),
		RightLowerLeg = Vector3.new(0.456, 1.5184, 0.5476),
		RightUpperArm = Vector3.new(0.3818, 1.061, 0.5806),
		RightUpperLeg = Vector3.new(0.613, 1.0334, 0.666),
		UpperTorso = Vector3.new(1.4445, 1.9301, 0.8917),
	},
	Female_Skinny = {
		Head = Vector3.new(0.6092, 1.0679, 0.7402),
		LeftHand = Vector3.new(0.2636, 0.6456, 0.4555),
		LeftLowerArm = Vector3.new(0.2734, 0.8203, 0.2491),
		LeftLowerLeg = Vector3.new(0.3734, 1.5239, 0.4828),
		LeftUpperArm = Vector3.new(0.3217, 1.0231, 0.4277),
		LeftUpperLeg = Vector3.new(0.4864, 1.0391, 0.5158),
		RightHand = Vector3.new(0.2636, 0.6456, 0.4555),
		RightLowerArm = Vector3.new(0.2734, 0.8203, 0.2491),
		RightLowerLeg = Vector3.new(0.3734, 1.5239, 0.4828),
		RightUpperArm = Vector3.new(0.3327, 1.0231, 0.4487),
		RightUpperLeg = Vector3.new(0.4864, 1.0391, 0.5158),
		UpperTorso = Vector3.new(1.4155, 1.8624, 0.819),
	},
	Male_Athletic = {
		Head = Vector3.new(0.6594, 1.1242, 0.8394),
		LeftHand = Vector3.new(0.3191, 0.8167, 0.5821),
		LeftLowerArm = Vector3.new(0.3553, 1.0645, 0.3187),
		LeftLowerLeg = Vector3.new(0.4652, 1.7463, 0.5909),
		LeftUpperArm = Vector3.new(0.5528, 1.1863, 0.6805),
		LeftUpperLeg = Vector3.new(0.6203, 1.1567, 0.644),
		RightHand = Vector3.new(0.3191, 0.8167, 0.5821),
		RightLowerArm = Vector3.new(0.3553, 1.0645, 0.3187),
		RightLowerLeg = Vector3.new(0.4652, 1.7463, 0.5909),
		RightUpperArm = Vector3.new(0.5528, 1.1863, 0.6805),
		RightUpperLeg = Vector3.new(0.6203, 1.1567, 0.644),
		UpperTorso = Vector3.new(1.7588, 2.1536, 0.8987),
	},
	Male_Average = {
		Head = Vector3.new(0.6612, 1.1268, 0.8416),
		LeftHand = Vector3.new(0.3202, 0.8173, 0.5839),
		LeftLowerArm = Vector3.new(0.3623, 1.0886, 0.3476),
		LeftLowerLeg = Vector3.new(0.4761, 1.7631, 0.6006),
		LeftUpperArm = Vector3.new(0.5653, 1.1762, 0.6927),
		LeftUpperLeg = Vector3.new(0.6444, 1.2717, 0.6744),
		RightHand = Vector3.new(0.3202, 0.8173, 0.5839),
		RightLowerArm = Vector3.new(0.3623, 1.0886, 0.3476),
		RightLowerLeg = Vector3.new(0.4761, 1.7631, 0.6006),
		RightUpperArm = Vector3.new(0.5653, 1.1762, 0.7163),
		RightUpperLeg = Vector3.new(0.6444, 1.2717, 0.6744),
		UpperTorso = Vector3.new(1.7722, 2.1575, 0.9517),
	},
	Male_Heavy = {
		Head = Vector3.new(0.6609, 1.1252, 0.8545),
		LeftHand = Vector3.new(0.3206, 0.8207, 0.5846),
		LeftLowerArm = Vector3.new(0.4016, 1.1033, 0.3591),
		LeftLowerLeg = Vector3.new(0.5051, 1.7635, 0.6024),
		LeftUpperArm = Vector3.new(0.5567, 1.2085, 0.7909),
		LeftUpperLeg = Vector3.new(0.6788, 1.1462, 0.7123),
		RightHand = Vector3.new(0.3206, 0.8207, 0.5846),
		RightLowerArm = Vector3.new(0.4016, 1.1033, 0.3591),
		RightLowerLeg = Vector3.new(0.5051, 1.7635, 0.6024),
		RightUpperArm = Vector3.new(0.5567, 1.2085, 0.7909),
		RightUpperLeg = Vector3.new(0.6788, 1.1462, 0.7123),
		UpperTorso = Vector3.new(1.7911, 2.1817, 1.0334),
	},
	Male_Muscular = {
		Head = Vector3.new(0.6609, 1.1255, 0.8886),
		LeftHand = Vector3.new(0.3198, 0.824, 0.5838),
		LeftLowerArm = Vector3.new(0.3954, 1.108, 0.3624),
		LeftLowerLeg = Vector3.new(0.4974, 1.7648, 0.6175),
		LeftUpperArm = Vector3.new(0.5776, 1.1882, 0.7285),
		LeftUpperLeg = Vector3.new(0.6891, 1.2033, 0.6745),
		RightHand = Vector3.new(0.3198, 0.824, 0.5838),
		RightLowerArm = Vector3.new(0.3954, 1.108, 0.3624),
		RightLowerLeg = Vector3.new(0.4974, 1.7648, 0.6175),
		RightUpperArm = Vector3.new(0.5891, 1.1882, 0.7285),
		RightUpperLeg = Vector3.new(0.6891, 1.2079, 0.6745),
		UpperTorso = Vector3.new(1.8302, 2.1873, 0.982),
	},
	Male_Skinny = {
		Head = Vector3.new(0.6597, 1.1272, 0.8398),
		LeftHand = Vector3.new(0.3193, 0.8178, 0.5824),
		LeftLowerArm = Vector3.new(0.327, 1.061, 0.3109),
		LeftLowerLeg = Vector3.new(0.4405, 1.766, 0.5777),
		LeftUpperArm = Vector3.new(0.5535, 1.1716, 0.6247),
		LeftUpperLeg = Vector3.new(0.5057, 1.1255, 0.6112),
		RightHand = Vector3.new(0.3193, 0.8178, 0.5824),
		RightLowerArm = Vector3.new(0.327, 1.061, 0.3109),
		RightLowerLeg = Vector3.new(0.4405, 1.766, 0.5777),
		RightUpperArm = Vector3.new(0.4324, 1.1716, 0.539),
		RightUpperLeg = Vector3.new(0.5057, 1.1255, 0.6112),
		UpperTorso = Vector3.new(1.7411, 2.088, 0.8908),
	},
}

local function textureId(file)
	local ids = RS:FindFirstChild("NCInkIds")
	local v = ids and ids:FindFirstChild(file)
	return v and v.Value or ""
end

-- the body part each layer rides on
local function partFor(layer)
	local n = layer:gsub("^Ink_", "")
	if n == "Face" or n == "NeckHead" then
		return "Head"
	elseif n == "NeckUpperTorso" then
		return "UpperTorso"
	end
	return n
end

-- clone the body's ink layers into a character (call once after the body is built or swapped).
-- Each layer is placed from its own body part on the character (Ink.FIT), never from where the rig model happens to
-- sit in ReplicatedStorage, and held by a classic Weld (C0 = the exact offset), so it can't freeze a wrong gap the
-- way a WeldConstraint did. The layers have no skin weights (skinned layers came in scattered from the importer).
function Ink.Attach(character, bodyName)
	local rigs = RS:FindFirstChild("NCInkRigs")
	local src = rigs and rigs:FindFirstChild(bodyName)
	if not src then
		warn("[NCInk] no ink layers for body", bodyName)
		return false
	end
	local fit = Ink.FIT[bodyName] or {}
	local srcRoot = src:IsA("Model") and src.PrimaryPart or src:FindFirstChild("RootPart", true) or src:FindFirstChild("HumanoidRootPart", true)
	local hrp = character:FindFirstChild("HumanoidRootPart")
	local folder = character:FindFirstChild("NCInk")
	if folder then
		folder:Destroy()
	end
	folder = Instance.new("Model")
	folder.Name = "NCInk"
	-- FIT is in the usual R15 frame (front -Z, the character's left -X). If this body was imported turned round,
	-- flip X and Z together (a turn never mirrors).
	local flip = 1
	local ut, lua = character:FindFirstChild("UpperTorso"), character:FindFirstChild("LeftUpperArm")
	if ut and lua and ut:IsA("BasePart") and lua:IsA("BasePart") and ut.CFrame:PointToObjectSpace(lua.Position).X > 0 then
		flip = -1
	end
	local placed, warned = 0, {}
	for _, name in ipairs(Ink.LAYERS) do
		local mp = src:FindFirstChild(name, true)
		local part = character:FindFirstChild(partFor(name))
		if mp and mp:IsA("MeshPart") and part and part:IsA("BasePart") then
			local c = mp:Clone()
			c.Anchored = false
			c.CanCollide = false
			c.CanQuery = false
			c.CanTouch = false
			c.Massless = true
			c.CastShadow = false
			c.TextureID = ""
			c.Transparency = 1
			for _, j in ipairs(c:GetChildren()) do -- no stray joints from the rig file
				if j:IsA("JointInstance") or j:IsA("WeldConstraint") then
					j:Destroy()
				end
			end
			local f = fit[name]
			local want = (Ink.PART_SIZE[bodyName] or {})[part.Name]
			if want and not warned[part.Name] then
				local r = part.Size / want
				if math.abs(r.X - 1) > 0.05 or math.abs(r.Y - 1) > 0.05 or math.abs(r.Z - 1) > 0.05 then
					warned[part.Name] = true
					warn(("[NCInk] %s %s is %s, the ink was fitted to %s: placement scales with it, but a different mesh will put the ink off"):format(
						bodyName, part.Name, tostring(part.Size), tostring(want)))
				end
			end
			local rel
			if f then
				c.Size = part.Size * Vector3.new(f[4], f[5], f[6])
				rel = CFrame.new(part.Size * Vector3.new(f[1] * flip, f[2], f[3] * flip))
			elseif srcRoot and hrp then
				-- no measured fit: keep the layer's offset from the rig root, carried over to the character's root
				rel = part.CFrame:Inverse() * hrp.CFrame * (srcRoot.CFrame:Inverse() * mp.CFrame)
			else
				rel = CFrame.identity
			end
			c.CFrame = part.CFrame * rel
			local w = Instance.new("Weld")
			w.Name = "NCInkWeld"
			w.Part0, w.Part1 = part, c
			w.C0 = rel
			w.C1 = CFrame.identity
			w.Parent = c
			c.Parent = folder
			placed += 1
		end
	end
	folder.Parent = character
	return placed > 0
end

-- Studio/command-bar check: prints every layer's part, sizes and where it sits from its part, and what it shows
function Ink.Debug(character)
	local folder = character:FindFirstChild("NCInk")
	if not folder then
		print("[NCInk] no NCInk folder on", character:GetFullName())
		return
	end
	for _, name in ipairs(Ink.LAYERS) do
		local mp = folder:FindFirstChild(name)
		local part = character:FindFirstChild(partFor(name))
		if mp and part then
			local rel = part.CFrame:Inverse() * mp.CFrame
			local sa = mp:FindFirstChildOfClass("SurfaceAppearance")
			print(("[NCInk] %-20s on %-14s part %s layer %s offset %s  T=%.2f tex=%s sa=%s"):format(name, part.Name, tostring(part.Size),
				tostring(mp.Size), tostring(rel.Position), mp.Transparency, mp.TextureID, sa and sa.ColorMap or "-"))
		else
			print("[NCInk]", name, "missing", mp == nil and "layer" or "part")
		end
	end
end

-- the texture each layer gets for an ink table (layer name -> file name)
function Ink.Resolve(ink)
	local out = {}
	local function put(item, side)
		if not item then
			return
		end
		local zones = Ink.ZONES[item.area] and Ink.ZONES[item.area][item.zone]
		if not zones then
			return
		end
		local file = item.files[side] or item.files.C
		for _, z in ipairs(zones) do
			local layer = (side == "L" and "Ink_Left" or side == "R" and "Ink_Right" or "Ink_") .. z
			out[layer] = file
		end
	end
	ink = ink or {}
	for _, side in ipairs({ "L", "R" }) do
		local s = ink[side] or {}
		local up, lo = Catalog.BY_ID[s.upper or ""], Catalog.BY_ID[s.lower or ""]
		-- a full sleeve wins both halves of the arm
		if up and up.zone == "full" then
			put(up, side)
		elseif lo and lo.zone == "full" then
			put(lo, side)
		else
			put(up, side)
			put(lo, side)
		end
		put(Catalog.BY_ID[s.hand or ""], side)
		put(Catalog.BY_ID[s.leg or ""], side)
	end
	put(Catalog.BY_ID[ink.neck or ""], "C")
	put(Catalog.BY_ID[ink.face or ""], "C")
	return out
end

-- show the ink on a character that already has its layers attached
function Ink.Apply(character, ink)
	local folder = character:FindFirstChild("NCInk")
	if not folder then
		return
	end
	local want = Ink.Resolve(ink)
	for _, name in ipairs(Ink.LAYERS) do
		local mp = folder:FindFirstChild(name)
		if mp then
			local file = want[name]
			local old = mp:FindFirstChildOfClass("SurfaceAppearance")
			if old then
				old:Destroy()
			end
			-- prefer the saved SurfaceAppearance (alpha mode Transparency), fall back to TextureID
			local sas = RS:FindFirstChild("NCInkSA")
			local sa = file and sas and sas:FindFirstChild(file)
			if sa then
				sa:Clone().Parent = mp
				mp.TextureID = ""
				mp.Transparency = 0
			else
				local id = file and textureId(file) or ""
				mp.TextureID = id
				mp.Transparency = (id ~= "") and 0 or 1
			end
		end
	end
end

-- server check: is this a valid ink table? (only catalog ids, right area for each spot)
function Ink.Validate(ink)
	if type(ink) ~= "table" then
		return false
	end
	local ok = { upper = "Arm", lower = "Arm", hand = "Hand", leg = "Leg" }
	for _, side in ipairs({ "L", "R" }) do
		local s = ink[side]
		if s ~= nil then
			if type(s) ~= "table" then
				return false
			end
			for k, id in pairs(s) do
				local it = Catalog.BY_ID[id]
				if not ok[k] or not it or it.area ~= ok[k] then
					return false
				end
				if k == "upper" and it.zone == "lower" or k == "lower" and it.zone == "upper" then
					return false
				end
			end
		end
	end
	for k, area in pairs({ neck = "Neck", face = "Face" }) do
		if ink[k] ~= nil then
			local it = Catalog.BY_ID[ink[k]]
			if not it or it.area ~= area then
				return false
			end
		end
	end
	return true
end

-- total price of an ink table (each tattoo counted once, even if it covers two layers)
function Ink.Price(ink)
	local seen, total = {}, 0
	local function add(id)
		local it = id and Catalog.BY_ID[id]
		if it and not seen[id] then
			seen[id] = true
			total += it.price
		end
	end
	for _, side in ipairs({ "L", "R" }) do
		for _, id in pairs((ink or {})[side] or {}) do
			add(id)
		end
	end
	add((ink or {}).neck)
	add((ink or {}).face)
	return total
end

return Ink
