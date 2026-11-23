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

The rest of the city's lineup (VantorStrada, AurexHalcyon, KazumiK2, KazeRS8, HayatoTypeZ, NorrbyDL84,
MarloweDeville61, DusterRidge54, ShorelineSix, GeneralsCart, PoliceCruiser, ArmoredTruck; bikes last) is listed in
NCVehicles.lua and gets rebuilt under the same names with a spec each.

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
