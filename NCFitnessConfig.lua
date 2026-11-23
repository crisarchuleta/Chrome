--!nonstrict
-- NCFitnessConfig (ModuleScript in ReplicatedStorage): every number the body system runs on, in one place.
-- Strength and Stamina 0..100, Body fat 8..40 %, Energy 0..100. One game day = DAY_SECONDS real seconds.
local C = {}

C.DAY_SECONDS = 1440                -- 24 real minutes
C.BASE_KCAL_PER_DAY = 2000          -- what a body burns doing nothing
C.KCAL_PER_FAT_PERCENT = 3500       -- surplus (or deficit) calories per 1 % body fat
C.DIGEST_KCAL_PER_SEC = 12          -- food reaches the body over a few minutes, not instantly
C.ENERGY_PER_KCAL_BURNED = 0.03     -- 2000 kcal of living drains 60 energy
C.START = { str = 15, sta = 15, fat = 18, energy = 80 }
C.DECAY_PER_HOUR = 0.5              -- strength / stamina you lose per hour of play without training (above 10)

-- extra burn per second by activity, on top of the base
C.BURN = { walk = 0.45, jog = 1.4, sprint = 3.4, swim = 3.8, climb = 6.0, workout = 0 }
-- stamina training from moving (per stud), strength from climbing (per climb)
C.STA_PER_STUD_SPRINT = 0.0016
C.STA_PER_STUD_SWIM = 0.003
C.STR_PER_CLIMB = 0.25

-- food: price, calories, energy, health, plus extras
C.FOODS = {
	Soda = { price = 5, kcal = 250, energy = 10, health = 2, junk = true, rush = true, label = "Soda" },
	Candy = { price = 4, kcal = 280, energy = 12, health = 2, junk = true, label = "Candy bar" },
	Fries = { price = 8, kcal = 400, energy = 15, health = 4, junk = true, label = "Fries" },
	Burger = { price = 14, kcal = 900, energy = 35, health = 12, junk = true, label = "Burger" },
	Pizza = { price = 6, kcal = 300, energy = 12, health = 5, junk = true, label = "Pizza slice" },
	Tacos = { price = 12, kcal = 600, energy = 30, health = 10, junk = true, label = "Tacos (3)" },
	Pastry = { price = 6, kcal = 420, energy = 14, health = 4, junk = true, label = "Pastry" },
	Coffee = { price = 5, kcal = 60, energy = 12, health = 1, label = "Coffee" },
	EnergyDrink = { price = 9, kcal = 150, energy = 25, health = 2, rush = true, label = "Energy drink" },
	Salad = { price = 11, kcal = 250, energy = 20, health = 10, label = "Salad" },
	Smoothie = { price = 10, kcal = 300, energy = 25, health = 8, label = "Smoothie" },
	Protein = { price = 12, kcal = 200, energy = 15, health = 5, protein = true, label = "Protein shake" },
	Water = { price = 2, kcal = 0, energy = 4, health = 2, label = "Water" },
}
C.MENUS = {
	Taco = { "Tacos", "Fries", "Soda", "Water" },
	Burger = { "Burger", "Fries", "Soda", "Water" },
	Pizza = { "Pizza", "Soda", "Water" },
	Cafe = { "Coffee", "Pastry", "Smoothie", "Water" },
	Vending = { "Soda", "Candy", "EnergyDrink", "Water" },
	Healthy = { "Salad", "Smoothie", "Protein", "Water" },
	Gym = { "Protein", "EnergyDrink", "Water" },
}

-- workouts: which stat, gain per good rep (shrinks as the stat grows), energy and calories per rep, the fastest a
-- real rep can be (seconds), and how it looks
C.EXERCISES = {
	Bench = { stat = "str", gain = 0.20, energy = 1.4, kcal = 8, minRep = 1.0, label = "Bench press" },
	Squat = { stat = "str", gain = 0.20, energy = 1.6, kcal = 10, minRep = 1.1, label = "Squats" },
	Pullup = { stat = "str", gain = 0.24, energy = 1.6, kcal = 9, minRep = 1.2, label = "Pull-ups" },
	Curl = { stat = "str", gain = 0.12, energy = 0.9, kcal = 5, minRep = 0.8, label = "Dumbbell curls" },
	Bag = { stat = "str", gain = 0.10, energy = 1.0, kcal = 9, minRep = 0.55, label = "Punching bag", alsoSta = 0.05 },
	Treadmill = { stat = "sta", gain = 0.16, energy = 1.2, kcal = 11, minRep = 0.8, label = "Treadmill" },
}
C.PROTEIN_BONUS = 1.35             -- strength gains after a protein shake (for PROTEIN_SECONDS)
C.PROTEIN_SECONDS = 240
C.RUSH_SECONDS, C.CRASH_SECONDS = 20, 30

local function clamp01(x)
	return math.clamp(x, 0, 1)
end

-- what a body can do, from its three numbers
function C.Effects(str, sta, fat)
	local s, t = str / 100, sta / 100
	local over = math.max(0, fat - 20)             -- fat above a healthy 20 %
	local heavy = math.max(0, fat - 22)
	return {
		speed = (1 + 0.06 * t) * (1 - 0.009 * over),                       -- top speed
		sprintTime = (8 + 16 * t) * (1 - 0.02 * over),                      -- seconds of sprinting
		regen = 0.8 + 0.6 * t,                                              -- stamina refill speed
		jump = 1 - 0.012 * heavy,
		climbMax = 9.2 - 0.12 * heavy + 0.6 * s,                            -- highest wall you can climb (studs)
		climbSpeed = (0.75 + 0.35 * s) * (1 - 0.01 * heavy),
		fall = (1 + 0.02 * heavy) * (1 - 0.15 * s),                         -- fall damage multiplier
		swim = (1 + 0.15 * t) * (1 - 0.006 * over),
		carry = str,                                                        -- missions check this
		punch = 0.6 + 0.8 * s + 0.004 * over,                               -- heavy keeps some punch
		maxHealth = 100 + 25 * s + math.max(0, fat - 20) * 0.8,
	}
end

-- how it looks: Humanoid width / depth scale multipliers
function C.Shape(str, sta, fat)
	local fatN = clamp01((fat - 15) / 25)
	local mus = clamp01((str - 30) / 70)
	local skinny = (fat < 12 and str < 25) and clamp01((12 - fat) / 4) or 0
	return 1 + 0.28 * fatN + 0.10 * mus - 0.08 * skinny, 1 + 0.38 * fatN + 0.06 * mus - 0.06 * skinny
end

function C.Build(str, sta, fat)
	if fat >= 28 and str < 55 then
		return "Heavy"
	elseif str >= 55 and fat >= 22 then
		return "Bulky"
	elseif str >= 65 then
		return "Muscular"
	elseif fat < 13 and str < 30 then
		return "Skinny"
	elseif sta >= 50 and fat < 18 then
		return "Athletic"
	end
	return "Average"
end

C.TIPS = {
	Heavy = "Dante: \"Cut the soda, hit the treadmill. You'll feel it in a week.\"",
	Bulky = "Dante: \"Strong as an ox. Now let's get you moving: cardio.\"",
	Muscular = "Dante: \"Good. Keep the protein up and don't skip leg day.\"",
	Skinny = "Dante: \"You can run all day, but you can't lift the bar. Eat, then lift.\"",
	Athletic = "Dante: \"That's a fighter's build. Keep it.\"",
	Average = "Dante: \"Pick a goal. Lift for power, run for wind.\"",
}

return C
