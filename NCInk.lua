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
		Ink_Face = { 0, 0.3816, -0.1878, 0.46586, 0.21988, 0.63425 },
		Ink_LeftHand = { -0.43579, -0.37262, -0.0304, 0.13322, 0.25648, 0.95178 },
		Ink_LeftLowerArm = { -0.40047, -0.2132, -0.05722, 0.20394, 0.39302, 0.59082 },
		Ink_LeftLowerLeg = { -0.28772, -0.33924, -0.0293, 0.32147, 0.32119, 0.95398 },
		Ink_LeftUpperArm = { -0.38581, 0.21776, 0.00041, 0.23326, 0.52073, 1.01396 },
		Ink_LeftUpperLeg = { -0.24885, -0.3379, -0.10024, 0.43844, 0.32504, 0.70003 },
		Ink_NeckHead = { 0, 0.26967, 0.0187, 0.44177, 0.14814, 0.7886 },
		Ink_NeckUpperTorso = { 0, 0.36968, 0.10088, 1.00379, 0.26274, 0.74641 },
		Ink_RightHand = { 0.43579, -0.37262, -0.0304, 0.13322, 0.25648, 0.95178 },
		Ink_RightLowerArm = { 0.40047, -0.2132, -0.05722, 0.20394, 0.39302, 0.59082 },
		Ink_RightLowerLeg = { 0.28772, -0.33924, -0.0293, 0.32147, 0.32119, 0.95398 },
		Ink_RightUpperArm = { 0.38581, 0.21776, 0.00041, 0.23326, 0.52073, 1.01396 },
		Ink_RightUpperLeg = { 0.24884, -0.3379, -0.09769, 0.43843, 0.32504, 0.69714 },
	},
	Female_Average = {
		Ink_Face = { 0, 0.38799, -0.18781, 0.45047, 0.20801, 0.63421 },
		Ink_LeftHand = { -0.44313, -0.37453, 0.07838, 0.11848, 0.25263, 0.76474 },
		Ink_LeftLowerArm = { -0.40389, -0.16456, 0.08081, 0.19703, 0.35409, 0.46569 },
		Ink_LeftLowerLeg = { -0.28208, -0.33994, 0.00481, 0.32614, 0.31979, 0.93494 },
		Ink_LeftUpperArm = { -0.39141, 0.22507, 0.08331, 0.22207, 0.47056, 0.84577 },
		Ink_LeftUpperLeg = { -0.24651, -0.22126, -0.1108, 0.4462, 0.55838, 0.6963 },
		Ink_NeckHead = { 0, 0.28222, 0.01865, 0.42717, 0.13687, 0.78856 },
		Ink_NeckUpperTorso = { 0, 0.38459, 0.10818, 1.00377, 0.23278, 0.74073 },
		Ink_RightHand = { 0.44313, -0.37453, 0.07838, 0.11848, 0.25263, 0.76474 },
		Ink_RightLowerArm = { 0.40389, -0.16456, 0.08081, 0.19703, 0.35409, 0.46569 },
		Ink_RightLowerLeg = { 0.28208, -0.33994, 0.00481, 0.32614, 0.31979, 0.93494 },
		Ink_RightUpperArm = { 0.39141, 0.22507, 0.08331, 0.22207, 0.47056, 0.84577 },
		Ink_RightUpperLeg = { 0.24646, -0.22127, -0.11056, 0.44617, 0.55835, 0.69605 },
	},
	Female_Heavy = {
		Ink_Face = { 0, 0.38736, -0.19208, 0.3995, 0.20918, 0.62554 },
		Ink_LeftHand = { -0.43327, -0.37288, -0.04293, 0.13795, 0.25594, 0.914 },
		Ink_LeftLowerArm = { -0.40165, -0.16396, -0.01336, 0.20124, 0.35814, 0.60034 },
		Ink_LeftLowerLeg = { -0.24949, -0.34013, -0.0192, 0.30484, 0.31942, 0.97321 },
		Ink_LeftUpperArm = { -0.38494, 0.23246, 0.00042, 0.23467, 0.48554, 1.01175 },
		Ink_LeftUpperLeg = { -0.22963, -0.21959, -0.04143, 0.44792, 0.56171, 0.84413 },
		Ink_NeckHead = { 0, 0.28076, 0.01974, 0.37885, 0.1381, 0.79562 },
		Ink_NeckUpperTorso = { 0, 0.26443, 0.10319, 0.9281, 0.47325, 0.75455 },
		Ink_RightHand = { 0.43327, -0.37288, -0.04293, 0.13795, 0.25594, 0.914 },
		Ink_RightLowerArm = { 0.40165, -0.16396, -0.01336, 0.20124, 0.35814, 0.60034 },
		Ink_RightLowerLeg = { 0.24949, -0.34013, -0.0192, 0.30484, 0.31942, 0.97321 },
		Ink_RightUpperArm = { 0.38494, 0.23246, 0.00042, 0.23467, 0.48554, 1.01175 },
		Ink_RightUpperLeg = { 0.22963, -0.21959, -0.04139, 0.44792, 0.56171, 0.84408 },
	},
	Female_Muscular = {
		Ink_Face = { 0, 0.1821, -0.18781, 1.01203, 0.59038, 0.63422 },
		Ink_LeftHand = { -0.42246, -0.36595, 0.01976, 0.16153, 0.2699, 0.97698 },
		Ink_LeftLowerArm = { -0.35354, -0.26796, 0.13475, 0.29933, 0.46364, 0.7496 },
		Ink_LeftLowerLeg = { -0.25034, -0.33105, 0.00004, 0.5075, 0.33757, 1.01304 },
		Ink_LeftUpperArm = { -0.32609, 0.00122, 0.00032, 0.35391, 1.00336, 1.01186 },
		Ink_LeftUpperLeg = { -0.13223, -0.33179, -0.08928, 0.6561, 0.33735, 0.7338 },
		Ink_NeckHead = { 0, -0.12025, 0.03934, 0.9597, 0.39276, 0.82993 },
		Ink_NeckUpperTorso = { 0, 0.19173, 0.08434, 1.00358, 0.62117, 0.76966 },
		Ink_RightHand = { 0.42246, -0.36595, 0.01976, 0.16153, 0.2699, 0.97698 },
		Ink_RightLowerArm = { 0.35354, -0.26796, 0.13475, 0.29933, 0.46364, 0.7496 },
		Ink_RightLowerLeg = { 0.25034, -0.33105, 0.00004, 0.5075, 0.33757, 1.01304 },
		Ink_RightUpperArm = { 0.32609, 0.00122, 0.00032, 0.35391, 1.00336, 1.01186 },
		Ink_RightUpperLeg = { 0.13217, -0.33179, -0.08993, 0.65604, 0.33735, 0.73444 },
	},
	Female_Skinny = {
		Ink_Face = { 0, 0.38854, -0.1878, 0.48864, 0.20639, 0.63424 },
		Ink_LeftHand = { -0.42698, -0.37315, 0.06655, 0.15094, 0.2554, 0.79348 },
		Ink_LeftLowerArm = { -0.406, -0.15251, 0.07124, 0.19296, 0.35533, 0.44307 },
		Ink_LeftLowerLeg = { -0.3003, -0.33638, -0.00958, 0.29752, 0.32691, 0.84696 },
		Ink_LeftUpperArm = { -0.38926, 0.22481, 0.11164, 0.2265, 0.44904, 0.70534 },
		Ink_LeftUpperLeg = { -0.26711, -0.34224, -0.11091, 0.39123, 0.31604, 0.67642 },
		Ink_NeckHead = { 0, 0.28347, 0.01841, 0.4634, 0.13942, 0.78857 },
		Ink_NeckUpperTorso = { 0, 0.38968, 0.115, 1.00391, 0.22251, 0.70431 },
		Ink_RightHand = { 0.42698, -0.37315, 0.06655, 0.15094, 0.2554, 0.79348 },
		Ink_RightLowerArm = { 0.406, -0.15251, 0.07124, 0.19296, 0.35533, 0.44307 },
		Ink_RightLowerLeg = { 0.3003, -0.33638, -0.00958, 0.29752, 0.32691, 0.84696 },
		Ink_RightUpperArm = { 0.38926, 0.22481, 0.12135, 0.2265, 0.44904, 0.68593 },
		Ink_RightUpperLeg = { 0.26711, -0.34224, -0.11141, 0.39123, 0.31604, 0.67693 },
	},
	Male_Athletic = {
		Ink_Face = { 0, 0.28369, -0.18763, 0.54701, 0.4202, 0.63469 },
		Ink_LeftHand = { -0.42326, -0.37019, 0.00456, 0.15841, 0.26134, 1.00506 },
		Ink_LeftLowerArm = { -0.39258, -0.27232, -0.12389, 0.21984, 0.455, 0.74588 },
		Ink_LeftLowerLeg = { -0.3175, -0.33353, 0.00015, 0.37151, 0.33289, 1.01477 },
		Ink_LeftUpperArm = { -0.37246, -0.04726, 0.00033, 0.26018, 0.90621, 1.01322 },
		Ink_LeftUpperLeg = { -0.23178, -0.35097, -0.09328, 0.47773, 0.29792, 0.73147 },
		Ink_NeckHead = { 0, 0.05575, 0.03285, 0.53604, 0.33131, 0.8982 },
		Ink_NeckUpperTorso = { 0, 0.22501, 0.06927, 1.00349, 0.55226, 0.83153 },
		Ink_RightHand = { 0.42326, -0.37019, 0.00456, 0.15841, 0.26134, 1.00506 },
		Ink_RightLowerArm = { 0.39258, -0.27232, -0.12389, 0.21984, 0.455, 0.74588 },
		Ink_RightLowerLeg = { 0.3175, -0.33353, 0.00015, 0.37151, 0.33289, 1.01477 },
		Ink_RightUpperArm = { 0.37246, -0.04726, 0.00033, 0.26018, 0.90621, 1.01322 },
		Ink_RightUpperLeg = { 0.23177, -0.35097, -0.09317, 0.47773, 0.29792, 0.7314 },
	},
	Male_Average = {
		Ink_Face = { 0, 0.29056, -0.21929, 0.54313, 0.40683, 0.57036 },
		Ink_LeftHand = { -0.42362, -0.3716, -0.06239, 0.15767, 0.25853, 0.8718 },
		Ink_LeftLowerArm = { -0.39233, -0.27409, -0.20009, 0.22031, 0.45148, 0.61434 },
		Ink_LeftLowerLeg = { -0.31672, -0.33332, -0.03388, 0.37301, 0.33331, 0.94522 },
		Ink_LeftUpperArm = { -0.36968, -0.04879, -0.07367, 0.26571, 0.90306, 0.8654 },
		Ink_LeftUpperLeg = { -0.23063, -0.33807, -0.08916, 0.48359, 0.32354, 0.73835 },
		Ink_NeckHead = { 0, 0.07003, -0.0175, 0.53223, 0.32088, 0.81446 },
		Ink_NeckUpperTorso = { 0, 0.16664, 0.07132, 1.00338, 0.66916, 0.82759 },
		Ink_RightHand = { 0.42362, -0.3716, -0.06239, 0.15767, 0.25853, 0.8718 },
		Ink_RightLowerArm = { 0.39233, -0.27409, -0.20009, 0.22031, 0.45148, 0.61434 },
		Ink_RightLowerLeg = { 0.31672, -0.33332, -0.03388, 0.37301, 0.33331, 0.94522 },
		Ink_RightUpperArm = { 0.36968, -0.04879, -0.07367, 0.26571, 0.90306, 0.8654 },
		Ink_RightUpperLeg = { 0.23062, -0.33807, -0.08874, 0.48358, 0.32354, 0.73761 },
	},
	Male_Heavy = {
		Ink_Face = { 0, 0.2871, -0.22964, 0.58205, 0.41353, 0.54934 },
		Ink_LeftHand = { -0.42162, -0.37115, -0.08418, 0.1618, 0.25942, 0.82881 },
		Ink_LeftLowerArm = { -0.37905, -0.27116, -0.20025, 0.24695, 0.45757, 0.59313 },
		Ink_LeftLowerLeg = { -0.30057, -0.33505, -0.06089, 0.40546, 0.3298, 0.88997 },
		Ink_LeftUpperArm = { -0.35911, -0.04538, -0.05683, 0.28699, 0.91037, 0.89521 },
		Ink_LeftUpperLeg = { -0.21316, -0.35216, -0.0898, 0.51527, 0.29621, 0.71609 },
		Ink_NeckHead = { 0, 0.06102, -0.03883, 0.57036, 0.32769, 0.77734 },
		Ink_NeckUpperTorso = { 0, 0.06748, 0.03419, 1.00345, 0.86793, 0.88917 },
		Ink_RightHand = { 0.42162, -0.37115, -0.08418, 0.1618, 0.25942, 0.82881 },
		Ink_RightLowerArm = { 0.37905, -0.27116, -0.20025, 0.24695, 0.45757, 0.59313 },
		Ink_RightLowerLeg = { 0.30057, -0.33505, -0.06089, 0.40546, 0.3298, 0.88997 },
		Ink_RightUpperArm = { 0.35911, -0.04538, -0.05683, 0.28699, 0.91037, 0.89521 },
		Ink_RightUpperLeg = { 0.21315, -0.35216, -0.0893, 0.51526, 0.29621, 0.71543 },
	},
	Male_Muscular = {
		Ink_Face = { 0, 0.22931, -0.23626, 0.96946, 0.52581, 0.53588 },
		Ink_LeftHand = { -0.40873, -0.36572, -0.09798, 0.18839, 0.27034, 0.8008 },
		Ink_LeftLowerArm = { -0.35927, -0.25907, -0.19653, 0.28742, 0.48164, 0.58785 },
		Ink_LeftLowerLeg = { -0.25772, -0.33147, -0.06441, 0.49267, 0.33703, 0.88345 },
		Ink_LeftUpperArm = { -0.33697, -0.00846, -0.05171, 0.33202, 0.9841, 0.90512 },
		Ink_LeftUpperLeg = { -0.14298, -0.33951, -0.08945, 0.64505, 0.32111, 0.74406 },
		Ink_NeckHead = { 0, -0.05591, -0.04668, 0.95, 0.415, 0.7652 },
		Ink_NeckUpperTorso = { 0, 0.13975, 0.05163, 1.00296, 0.72285, 0.86884 },
		Ink_RightHand = { 0.40873, -0.36572, -0.09798, 0.18839, 0.27034, 0.8008 },
		Ink_RightLowerArm = { 0.35927, -0.25907, -0.19653, 0.28742, 0.48164, 0.58785 },
		Ink_RightLowerLeg = { 0.25772, -0.33147, -0.06441, 0.49267, 0.33703, 0.88345 },
		Ink_RightUpperArm = { 0.33697, -0.00846, -0.05171, 0.33202, 0.9841, 0.90512 },
		Ink_RightUpperLeg = { 0.14299, -0.33889, -0.08919, 0.64505, 0.32234, 0.74418 },
	},
	Male_Skinny = {
		Ink_Face = { -0.00861, 0.28791, -0.19239, 0.56065, 0.41198, 0.62501 },
		Ink_LeftHand = { -0.42309, -0.36896, -0.0017, 0.15876, 0.26384, 0.99264 },
		Ink_LeftLowerArm = { -0.40043, -0.26957, -0.11202, 0.20413, 0.46057, 0.61557 },
		Ink_LeftLowerLeg = { -0.3269, -0.33199, 0.00408, 0.35277, 0.33596, 1.00726 },
		Ink_LeftUpperArm = { -0.37589, -0.03712, -0.02122, 0.2534, 0.9265, 0.9727 },
		Ink_LeftUpperLeg = { -0.26418, -0.35392, -0.08358, 0.40573, 0.29185, 0.74546 },
		Ink_NeckHead = { -0.00861, 0.06911, 0.02448, 0.54941, 0.31569, 0.88368 },
		Ink_NeckUpperTorso = { 0, 0.19176, 0.07537, 1.00357, 0.61851, 0.80666 },
		Ink_RightHand = { 0.42214, -0.36896, -0.0017, 0.16071, 0.26384, 0.99264 },
		Ink_RightLowerArm = { 0.39919, -0.26957, -0.11202, 0.20668, 0.46057, 0.61557 },
		Ink_RightLowerLeg = { 0.32406, -0.33199, 0.00408, 0.35855, 0.33596, 1.00726 },
		Ink_RightUpperArm = { 0.37413, -0.03712, -0.02122, 0.25699, 0.9265, 0.9727 },
		Ink_RightUpperLeg = { 0.26026, -0.35392, -0.08345, 0.41238, 0.29185, 0.74493 },
	},
}

-- the R15 part sizes (studs) Ink.FIT was measured on; Attach warns when a body's part differs (wrong body file)
Ink.PART_SIZE = {
	Female_Athletic = {
		Head = Vector3.new(1.3229, 3.078, 0.7404),
		LeftHand = Vector3.new(1.524, 2.5225, 0.4599),
		LeftLowerArm = Vector3.new(1.5021, 2.1013, 0.4397),
		LeftLowerLeg = Vector3.new(1.3229, 4.7871, 0.5435),
		LeftUpperArm = Vector3.new(1.4619, 2.1013, 0.4668),
		LeftUpperLeg = Vector3.new(1.325, 3.3311, 0.8928),
		RightHand = Vector3.new(1.524, 2.5225, 0.4599),
		RightLowerArm = Vector3.new(1.5021, 2.1013, 0.4397),
		RightLowerLeg = Vector3.new(1.3229, 4.7871, 0.5435),
		RightUpperArm = Vector3.new(1.4619, 2.1013, 0.4668),
		RightUpperLeg = Vector3.new(1.325, 3.3311, 0.8965),
		UpperTorso = Vector3.new(1.402, 2.2204, 0.8067),
	},
	Female_Average = {
		Head = Vector3.new(1.3663, 3.2495, 0.7394),
		LeftHand = Vector3.new(1.5444, 2.5591, 0.5635),
		LeftLowerArm = Vector3.new(1.5187, 2.3158, 0.5635),
		LeftLowerLeg = Vector3.new(1.3663, 4.8168, 0.5635),
		LeftUpperArm = Vector3.new(1.4723, 2.3158, 0.5767),
		LeftUpperLeg = Vector3.new(1.3789, 3.3514, 0.9263),
		RightHand = Vector3.new(1.5444, 2.5591, 0.5635),
		RightLowerArm = Vector3.new(1.5187, 2.3158, 0.5635),
		RightLowerLeg = Vector3.new(1.3663, 4.8168, 0.5635),
		RightUpperArm = Vector3.new(1.4723, 2.3158, 0.5767),
		RightUpperLeg = Vector3.new(1.379, 3.3514, 0.9266),
		UpperTorso = Vector3.new(1.395, 2.3934, 0.8131),
	},
	Female_Heavy = {
		Head = Vector3.new(1.5409, 3.2319, 0.7496),
		LeftHand = Vector3.new(1.6319, 2.5306, 0.5024),
		LeftLowerArm = Vector3.new(1.6132, 2.2687, 0.4856),
		LeftLowerLeg = Vector3.new(1.5409, 4.7901, 0.5626),
		LeftUpperArm = Vector3.new(1.5786, 2.2687, 0.5259),
		LeftUpperLeg = Vector3.new(1.5409, 3.3271, 1.0192),
		RightHand = Vector3.new(1.6319, 2.5306, 0.5024),
		RightLowerArm = Vector3.new(1.6132, 2.2687, 0.4856),
		RightLowerLeg = Vector3.new(1.5409, 4.7901, 0.5626),
		RightUpperArm = Vector3.new(1.5786, 2.2687, 0.5259),
		RightUpperLeg = Vector3.new(1.5409, 3.3271, 1.0192),
		UpperTorso = Vector3.new(1.5409, 2.3835, 0.9079),
	},
	Female_Muscular = {
		Head = Vector3.new(0.6083, 1.1451, 0.7396),
		LeftHand = Vector3.new(1.1331, 2.3979, 0.4412),
		LeftLowerArm = Vector3.new(1.131, 1.788, 0.3827),
		LeftLowerLeg = Vector3.new(0.8782, 4.6567, 0.5476),
		LeftUpperArm = Vector3.new(1.0986, 1.1129, 0.5428),
		LeftUpperLeg = Vector3.new(0.9454, 3.2057, 0.9176),
		RightHand = Vector3.new(1.1331, 2.3979, 0.4412),
		RightLowerArm = Vector3.new(1.131, 1.788, 0.3827),
		RightLowerLeg = Vector3.new(0.8782, 4.6567, 0.5476),
		RightUpperArm = Vector3.new(1.0986, 1.1129, 0.5428),
		RightUpperLeg = Vector3.new(0.9454, 3.2057, 0.9168),
		UpperTorso = Vector3.new(1.4082, 1.289, 0.8704),
	},
	Female_Skinny = {
		Head = Vector3.new(1.2618, 3.281, 0.7402),
		LeftHand = Vector3.new(1.494, 2.5383, 0.5786),
		LeftLowerArm = Vector3.new(1.4669, 2.3215, 0.5786),
		LeftLowerLeg = Vector3.new(1.2618, 4.8051, 0.5786),
		LeftUpperArm = Vector3.new(1.4268, 2.3215, 0.5786),
		LeftUpperLeg = Vector3.new(1.2618, 3.3129, 0.7733),
		RightHand = Vector3.new(1.494, 2.5383, 0.5786),
		RightLowerArm = Vector3.new(1.4669, 2.3215, 0.5786),
		RightLowerLeg = Vector3.new(1.2618, 4.8051, 0.5786),
		RightUpperArm = Vector3.new(1.4268, 2.3215, 0.5786),
		RightUpperLeg = Vector3.new(1.2618, 3.3129, 0.7727),
		UpperTorso = Vector3.new(1.3638, 2.4148, 0.7862),
	},
	Male_Athletic = {
		Head = Vector3.new(1.2205, 1.6264, 0.8394),
		LeftHand = Vector3.new(1.6931, 3.1367, 0.5821),
		LeftLowerArm = Vector3.new(1.6633, 2.365, 0.4384),
		LeftLowerLeg = Vector3.new(1.2741, 5.569, 0.5508),
		LeftUpperArm = Vector3.new(1.6063, 1.3592, 0.5438),
		LeftUpperLeg = Vector3.new(1.3158, 3.8207, 0.8916),
		RightHand = Vector3.new(1.6931, 3.1367, 0.5821),
		RightLowerArm = Vector3.new(1.6633, 2.365, 0.4384),
		RightLowerLeg = Vector3.new(1.2741, 5.569, 0.5508),
		RightUpperArm = Vector3.new(1.6063, 1.3592, 0.5438),
		RightUpperLeg = Vector3.new(1.3158, 3.8207, 0.8917),
		UpperTorso = Vector3.new(1.7216, 1.4856, 0.8971),
	},
	Male_Average = {
		Head = Vector3.new(1.2327, 1.6846, 0.9366),
		LeftHand = Vector3.new(1.7073, 3.1507, 0.6732),
		LeftLowerArm = Vector3.new(1.6818, 2.3794, 0.5668),
		LeftLowerLeg = Vector3.new(1.2985, 5.5976, 0.5984),
		LeftUpperArm = Vector3.new(1.6283, 1.3845, 0.6312),
		LeftUpperLeg = Vector3.new(1.3497, 3.8259, 0.9245),
		RightHand = Vector3.new(1.7073, 3.1507, 0.6732),
		RightLowerArm = Vector3.new(1.6818, 2.3794, 0.5668),
		RightLowerLeg = Vector3.new(1.2985, 5.5976, 0.5984),
		RightUpperArm = Vector3.new(1.6283, 1.3845, 0.6312),
		RightUpperLeg = Vector3.new(1.3497, 3.8259, 0.9255),
		UpperTorso = Vector3.new(1.7208, 1.4873, 0.9211),
	},
	Male_Heavy = {
		Head = Vector3.new(1.1497, 1.6508, 0.972),
		LeftHand = Vector3.new(1.6635, 3.176, 0.7092),
		LeftLowerArm = Vector3.new(1.6592, 2.4017, 0.6194),
		LeftLowerLeg = Vector3.new(1.2662, 5.6206, 0.6372),
		LeftUpperArm = Vector3.new(1.5946, 1.3975, 0.7108),
		LeftUpperLeg = Vector3.new(1.3335, 3.8834, 1.0062),
		RightHand = Vector3.new(1.6635, 3.176, 0.7092),
		RightLowerArm = Vector3.new(1.6592, 2.4017, 0.6194),
		RightLowerLeg = Vector3.new(1.2662, 5.6206, 0.6372),
		RightUpperArm = Vector3.new(1.5946, 1.3975, 0.7108),
		RightUpperLeg = Vector3.new(1.3335, 3.8834, 1.0071),
		UpperTorso = Vector3.new(1.7619, 1.4456, 0.9967),
	},
	Male_Muscular = {
		Head = Vector3.new(0.6903, 1.3028, 0.9965),
		LeftHand = Vector3.new(1.4267, 3.0696, 0.7327),
		LeftLowerArm = Vector3.new(1.4047, 2.2922, 0.6306),
		LeftLowerLeg = Vector3.new(1.0261, 5.5088, 0.6667),
		LeftUpperArm = Vector3.new(1.3629, 1.2979, 0.6911),
		LeftUpperLeg = Vector3.new(1.0811, 3.7488, 0.9176),
		RightHand = Vector3.new(1.4267, 3.0696, 0.7327),
		RightLowerArm = Vector3.new(1.4047, 2.2922, 0.6306),
		RightLowerLeg = Vector3.new(1.0261, 5.5088, 0.6667),
		RightUpperArm = Vector3.new(1.3629, 1.2979, 0.6911),
		RightUpperLeg = Vector3.new(1.0811, 3.7488, 0.9175),
		UpperTorso = Vector3.new(1.6828, 1.4788, 0.982),
	},
	Male_Skinny = {
		Head = Vector3.new(1.1914, 1.6595, 0.8528),
		LeftHand = Vector3.new(1.691, 3.0907, 0.5897),
		LeftLowerArm = Vector3.new(1.6622, 2.321, 0.5185),
		LeftLowerLeg = Vector3.new(1.2721, 5.5262, 0.5385),
		LeftUpperArm = Vector3.new(1.5899, 1.3177, 0.537),
		LeftUpperLeg = Vector3.new(1.2668, 3.7552, 0.8307),
		RightHand = Vector3.new(1.6705, 3.0907, 0.5897),
		RightLowerArm = Vector3.new(1.6416, 2.321, 0.5185),
		RightLowerLeg = Vector3.new(1.2516, 5.5262, 0.5385),
		RightUpperArm = Vector3.new(1.5694, 1.3177, 0.537),
		RightUpperLeg = Vector3.new(1.2463, 3.7552, 0.8313),
		UpperTorso = Vector3.new(1.6938, 1.5128, 0.8778),
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
