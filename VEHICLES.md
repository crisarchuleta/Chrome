# Neon Coast vehicles

Every drivable vehicle runs on the lowrider's system: the same tuning menu at Low & Slow Kustoms, the same
paint / vinyl / parts / interior / lights options, saved per vehicle. All names are original (no real makes).

## Built so far

| id | name | type | doors | rear opening |
|---|---|---|---|---|
| royale | Royale Lowrider | lowrider (build_lowrider.py) | 2 | trunk |
| Ironclad | Ironclad SS | muscle coupe | 2 | trunk |
| IronhornTRX | Ironhorn TRX | full-size pickup | 4 | tailgate + open bed |
| KestrelGT | Kestrel GT | sports fastback | 2 | glass hatch |
| Dunewalker | Dunewalker | off-road SUV | 4 | liftgate |
| VantorStrada | Vantor Strada | sedan | 4 | trunk |
| AurexHalcyon | Aurex Halcyon | luxury sedan | 4 | trunk |
| KazumiK2 | Kazumi K2 | hatchback | 4 | glass hatch |
| KazeRS8 | Kaze RS8 | sports coupe | 2 | trunk |
| HayatoTypeZ | Hayato Type Z | sports fastback | 2 | glass hatch |
| NorrbyDL84 | Norrby DL84 | boxy 80s sedan | 4 | trunk |
| PoliceCruiser | Police Cruiser | police sedan (light bar, push bar) | 4 | trunk |
| MarloweDeville61 | Marlowe 61 | 60s cruiser with fins | 2 | trunk |
| DusterRidge54 | Duster Ridge 54 | 50s pickup | 2 | tailgate + open bed |
| ShorelineSix | Shoreline Six | six-seat van | 4 | liftgate |
| ArmoredTruck | Coast Patrol Armored Truck | armored truck (blind box body) | 2 | liftgate |
| GeneralsCart | Generals Cart | open utility cart (canopy, two benches) | none (open sides) | tailgate + small bed |
| DirtBike | Dirt Bike | motocross bike (build_bikes.py) | none | lifting seat + gas cap |
| SportBike | Sport Bike | sport bike with a race fairing (build_bikes.py) | none | lifting seat + gas cap |

These replace the old CarTemplates under the same names. A spec with `doors=0, opentop=True` gets
open step-in sides with trim, a canopy on posts and a second bench (the cart).

**Bikes** are built by `build_bikes.py` (`NC_BIKE=DirtBike` or `SportBike`) with the same outputs. Their data has
`Car.Bike = true` and only FL (front) / RL (rear) wheels. The driving script runs each spring twice on the centre line,
holds the bike upright, leans it into turns exactly as far as the corner needs, and Space holds a wheelie (bikes have
no hydraulics). Bike parts: handlebars (`part_Bars`), front fender (`part_Fender`), fairing / number plate
(`part_Fairing`), seat, headlight, taillight, exhaust, underglow and every wheel option. The seat lifts on a hinge
(storage tray under it) and the gas cap flips open. Riders use the normal seated pose for now; a riding animation
would look better.

A spec can set its own stock parts with `stock={...}` (merged over its flavour's defaults); the same parts go in
that vehicle's `defaults` in NCVehicles.lua.

## Every vehicle has

- **Opening panels on hinges:** every door, the hood, the rear (trunk / hatch / liftgate / tailgate) and a gas
  door. Door glass, mirrors and door cards ride on their door; hood scoops ride on the hood; spoilers ride on the
  rear. Data: `Car.Hinges` + `Car.HingeOf` (+ `hinge` in `Car.OptInfo`). The game opens a door when someone gets in
  or out and puts a prompt on each panel (`Kit.SetOpen`).
- **An open cabin** (seats, dash, door cards show through the glass) and **an engine bay** under the hood.
- **Swappable parts:** front / rear bumper, grille, headlights, taillights, hood, spoiler, side skirts / running
  boards, mirrors, exhaust, roof (sunroof, rack, light bar), underglow, truck bed (cover, roll bar, rack), seats,
  door cards, dash, steering wheel, shifter, headliner. Every lowrider rim, knock-off, tyre and whitewall, plus
  off-road tyres, scaled to the vehicle's wheel.
- **Vinyls:** the lowrider's liveries, UV-mapped onto each vehicle's own panels.

## Making one

```
NC_VEHICLE=Ironclad NC_PREVIEW_ENGINE=CYCLES NC_OUT=<folder> blender --background --factory-startup --python build_vehicles.py
```

Writes `<id>.glb` (pieces `<id>_*`, wheel `<id>Wheel_*`), `<id>Vinyls.glb`, `NCVehicleData_<id>.lua` and
`previews/<id>_*.png`. A new vehicle is a new entry in `SPECS` (build_vehicles.py) plus a line in NCVehicles.lua
(price, driving numbers, stock parts in `defaults`). Parts are in build_vehicle_parts.py; the shared mesh helpers are
in nc_car_kit.py (the lowrider uses them too).

## Installing in Studio (needs the PC)

1. Put `NCVehicles` and each `NCVehicleData_<id>` in ReplicatedStorage (with the updated NCLowriderKit /
   NCLowriderConfig / LowriderService / LowriderClient).
2. Import `<id>.glb` and `<id>Vinyls.glb`, then run in the command bar:
   `require(game.ReplicatedStorage.NCLowriderKit).Prepare(workspace.<ImportedModel>)` for each import.
3. They show up in the Garage list at Low & Slow Kustoms. Hooking them into CarSpawner / HomeService / PoliceAI /
   PhoneService (which find cars by name in ServerStorage.CarTemplates) is the last step.

## In the game (NCVehicleWorld)

The city's cars now come from this system. `CarSpawner`, `PoliceAI` and `HomeService` still call
`Spawner.MakeCar(cf, paint, glow, templateName)`; when `templateName` is an NCVehicles id whose meshes are imported
(`LowriderAssets/<id>/Car`), `NCVehicleWorld.Build` makes a Kit car instead of cloning `ServerStorage.CarTemplates`.
Anything it can't build falls back to the old template, so nothing breaks mid-install.

* Parked cars rest anchored on their spot. Sitting in the driver's seat unanchors the car and hands its physics to
  that player's LowriderClient. An empty car that stops for 25 s, or whose driver is 300 studs away or gone, settles
  (anchored, level, on the ground).
* F at any seat swings that door open, seats you and shuts it. Trunk / hood / gas door / doors have prompts
  (personal and garage cars: owner only; anyone can ride along, only the owner drives).
* Coast Patrol: `PoliceCruiser` and `ArmoredTruck` are driven on the server with the same suspension model
  (`NCVehicleSim`, shared with LowriderClient) through `World.AIDrive(car, throttle, steer, dt)`. The roof lights
  (`PoliceRed` / `PoliceBlue` pieces) flash.
* Garage: stored Kit cars show in the bays (`World.Display`); `HomeConfig.Cars` adds Ironclad SS and Dunewalker.
* NeonCoastClient leaves Kit cars to LowriderClient (no VectorVelocity driving, G stays three-wheel).

### Install (Studio)

1. ReplicatedStorage: add ModuleScript `NCVehicleSim` (NCVehicleSim.lua). Replace `NCLowriderKit`, `HomeConfig`.
2. ServerScriptService: add ModuleScript `NCVehicleWorld` (NCVehicleWorld.lua). Replace the sources of
   `CarSpawner`, `PoliceAI`, `HomeService`, `LowriderService`.
3. StarterPlayerScripts: replace `LowriderClient` and `NeonCoastClient`.
4. Make sure every vehicle's `NCVehicleData_<id>` module is in ReplicatedStorage and its GLBs are imported and run
   through `NCLowriderKit.Prepare` (VEHICLES.md, above). Vehicles not yet imported keep using the old templates.
5. Play test: parked cars, V for a personal car, F to get in, drive, get out (car settles), garage store + drive out,
   get a wanted level and check the patrol cars chase and bust.
