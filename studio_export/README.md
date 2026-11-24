# Studio export (read-only snapshot)

Exact source of the live Studio scripts that spawn, store, chase or drive the old cars, copied from place
92271668154197 (version 105, 2026-11-24) for the vehicle rebuild. Byte sizes match the Studio copies.

| File | Studio location |
|---|---|
| ServerScriptService.CarSpawner.server.lua | ServerScriptService.CarSpawner |
| ServerScriptService.HomeService.server.lua | ServerScriptService.HomeService |
| ReplicatedStorage.HomeConfig.lua | ReplicatedStorage.HomeConfig |
| ServerScriptService.PoliceAI.server.lua | ServerScriptService.PoliceAI |
| ServerScriptService.PhoneService.server.lua | ServerScriptService.PhoneService |
| StarterPlayerScripts.PhoneClient.client.lua | StarterPlayer.StarterPlayerScripts.PhoneClient |
| StarterPlayerScripts.NeonCoastClient.client.lua | StarterPlayer.StarterPlayerScripts.NeonCoastClient |

Also reference CarTemplates / IsCar / CarName / CarScale / HinglessDoors but were not exported (ask if needed):
ServerScriptService.Pedestrians (6 KB, reacts to IsCar), ServerStorage.MeshCarBuilder (11 KB),
ServerStorage.VehicleBuilder (10 KB), ServerStorage.HalfmileAdapter (8 KB) and
ServerStorage.HalfmileShared.CarPhysics (31 KB): the old builders that made the CarTemplates, not used at runtime by
the spawner. NCVehicles, NCLowriderConfig and LowriderService are already in the repo.
