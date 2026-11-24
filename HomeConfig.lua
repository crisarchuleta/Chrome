-- Shared home + garage options (client UI and server)
local H = {}

H.Layouts = {
	{id = 1, name = "Open Concept", blurb = "Big living space flowing into the kitchen"},
	{id = 2, name = "Classic Family", blurb = "Separate rooms, fireplace lounge, two bedrooms"},
	{id = 3, name = "City Loft", blurb = "Studio living with a raised bedroom platform"},
}

H.Palettes = {
	{name = "Coastal", wall = Color3.fromRGB(226,238,242), floor = Color3.fromRGB(214,190,150), floorMat = "WoodPlanks", trim = Color3.fromRGB(255,255,255),
		accent = Color3.fromRGB(40,170,180), fabric = Color3.fromRGB(150,200,210), wood = Color3.fromRGB(205,180,140), counter = Color3.fromRGB(245,245,240), cabinet = Color3.fromRGB(250,250,248)},
	{name = "Modern Gray", wall = Color3.fromRGB(205,206,210), floor = Color3.fromRGB(80,62,50), floorMat = "WoodPlanks", trim = Color3.fromRGB(40,40,44),
		accent = Color3.fromRGB(255,90,200), fabric = Color3.fromRGB(70,72,80), wood = Color3.fromRGB(60,50,44), counter = Color3.fromRGB(235,235,238), cabinet = Color3.fromRGB(45,46,52)},
	{name = "Warm Classic", wall = Color3.fromRGB(240,226,200), floor = Color3.fromRGB(170,120,75), floorMat = "WoodPlanks", trim = Color3.fromRGB(250,246,236),
		accent = Color3.fromRGB(140,35,45), fabric = Color3.fromRGB(150,60,55), wood = Color3.fromRGB(120,80,50), counter = Color3.fromRGB(190,170,140), cabinet = Color3.fromRGB(240,232,214)},
	{name = "Neon Nights", wall = Color3.fromRGB(48,30,72), floor = Color3.fromRGB(30,28,38), floorMat = "Marble", trim = Color3.fromRGB(20,18,26),
		accent = Color3.fromRGB(60,230,255), fabric = Color3.fromRGB(150,60,200), wood = Color3.fromRGB(35,30,40), counter = Color3.fromRGB(25,25,30), cabinet = Color3.fromRGB(30,28,40)},
}

-- cars you can buy at your garage (template names = NCVehicles ids; old ServerStorage.CarTemplates names still work)
H.Cars = {
	{template = "DirtBike", name = "MX Dirtbike", price = 1200},
	{template = "SportBike", name = "Sport Bike", price = 6500},
	{template = "GeneralsCart", name = "The General's Cart", price = 600},
	{template = "ShorelineSix", name = "Shoreline Six", price = 900},
	{template = "NorrbyDL84", name = "Norrby DL '84", price = 1500},
	{template = "DusterRidge54", name = "Duster Ridge '54", price = 2500},
	{template = "MarloweDeville61", name = "Marlowe Deville '61", price = 4000},
	{template = "KazumiK2", name = "Kazumi K2", price = 5000},
	{template = "IronhornTRX", name = "Ironhorn TRX", price = 6000},
	{template = "Ironclad", name = "Ironclad SS", price = 6500},
	{template = "Dunewalker", name = "Dunewalker", price = 7000},
	{template = "VantorStrada", name = "Vantor Strada", price = 7500},
	{template = "HayatoTypeZ", name = "Hayato Type-Z", price = 8500},
	{template = "KazeRS8", name = "Kaze RS-8", price = 9000},
	{template = "KestrelGT", name = "Kestrel GT", price = 11000},
	{template = "AurexHalcyon", name = "Aurex Halcyon", price = 14000},
	{template = "ArmoredTruck", name = "Armored Truck (4 gun ports)", price = 25000},
}
H.Paints = {
	Color3.fromRGB(230,40,50), Color3.fromRGB(30,90,200), Color3.fromRGB(245,245,245), Color3.fromRGB(25,25,30), Color3.fromRGB(255,190,40),
	Color3.fromRGB(40,160,90), Color3.fromRGB(255,90,200), Color3.fromRGB(60,230,255), Color3.fromRGB(150,150,160), Color3.fromRGB(255,120,40),
}
H.GarageSlots = 6

return H
