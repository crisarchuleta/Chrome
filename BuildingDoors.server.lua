--!nonstrict
-- BuildingDoors: runs every Blender-built door. NC_Door models swing 95 degrees on their hinge, away from whoever
-- opened them, and close by themselves after a while. NC_GarageDoor models roll up flat under the garage ceiling.
-- Works on doors added at any time (houses streamed in, placed later).
local CollectionService = game:GetService("CollectionService")
local TweenService = game:GetService("TweenService")

local SWING = TweenInfo.new(0.45, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local ROLL = TweenInfo.new(1.6, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut)
local AUTO_CLOSE = 12

local function animate(model, closed, from, to, info, make)
	local v = Instance.new("NumberValue")
	v.Value = from
	local conn = v.Changed:Connect(function(x)
		model:PivotTo(closed * make(x))
	end)
	local tw = TweenService:Create(v, info, { Value = to })
	tw:Play()
	tw.Completed:Wait()
	conn:Disconnect()
	v:Destroy()
end

local function hookDoor(dm)
	local hinge = dm.PrimaryPart
	local leaf = dm:FindFirstChild("Leaf")
	local prompt = leaf and leaf:FindFirstChildOfClass("ProximityPrompt")
	if not (hinge and prompt) then
		return
	end
	local closed = dm:GetPivot()
	local angle = 0
	local busy = false
	local token = 0
	local function setAngle(target)
		busy = true
		local rot = function(a)
			return CFrame.Angles(0, math.rad(a), 0)
		end
		animate(dm, closed, angle, target, SWING, rot)
		angle = target
		prompt.ActionText = angle == 0 and "Open" or "Close"
		busy = false
	end
	prompt.Triggered:Connect(function(player)
		if busy then
			return
		end
		if angle ~= 0 then
			setAngle(0)
			return
		end
		-- swing away from the player: try both ways and keep the one that moves the leaf away from them
		local hrp = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
		local c = closed:PointToObjectSpace(leaf.Position)
		local best, bestScore = 95, -math.huge
		for _, a in { 95, -95 } do
			local moved = closed:PointToWorldSpace(CFrame.Angles(0, math.rad(a), 0) * c) - leaf.Position
			local score = hrp and -moved:Dot((hrp.Position - leaf.Position).Unit) or a
			if score > bestScore then
				best, bestScore = a, score
			end
		end
		setAngle(best)
		token += 1
		local my = token
		task.delay(AUTO_CLOSE, function()
			if token == my and angle ~= 0 and not busy then
				setAngle(0)
			end
		end)
	end)
end

local function hookGarage(gm)
	local top = gm.PrimaryPart
	local leaf = gm:FindFirstChild("Leaf")
	if not (top and leaf) then
		return
	end
	local closed = gm:GetPivot()
	local h = gm:GetAttribute("Height") or leaf.Size.Y
	local isOpen = false
	-- the door's thin axis points out of the opening; open = turn 90 degrees about the top edge so it lies flat inside
	local thin = (leaf.Size.X < leaf.Size.Z) and Vector3.xAxis or Vector3.zAxis
	local axis = thin:Cross(Vector3.yAxis).Unit
	local bottom = closed:PointToObjectSpace(leaf.Position) - Vector3.new(0, h / 2, 0)
	local pp = Instance.new("ProximityPrompt")
	pp.ActionText = "Open"
	pp.ObjectText = "Garage Door"
	pp.HoldDuration = 0.3
	pp.MaxActivationDistance = 14
	pp.RequiresLineOfSight = false
	pp.Parent = leaf
	-- which way is inside: the side the building's centre is on
	local building = gm:FindFirstAncestorOfClass("Model")
	local centre = building and building.PrimaryPart and building:GetBoundingBox().Position or closed.Position
	local inward = closed:VectorToObjectSpace(centre - closed.Position)
	local sign = 1
	local test = CFrame.fromAxisAngle(axis, math.rad(90)) * bottom
	if (test - bottom):Dot(inward) < 0 then
		sign = -1
	end
	local busy = false
	pp.Triggered:Connect(function()
		if busy then
			return
		end
		busy = true
		isOpen = not isOpen
		local make = function(t)
			return CFrame.fromAxisAngle(axis, math.rad(90 * sign) * t)
		end
		animate(gm, closed, isOpen and 0 or 1, isOpen and 1 or 0, ROLL, make)
		pp.ActionText = isOpen and "Close" or "Open"
		busy = false
	end)
end

for _, d in CollectionService:GetTagged("NC_Door") do
	task.spawn(hookDoor, d)
end
CollectionService:GetInstanceAddedSignal("NC_Door"):Connect(hookDoor)
for _, g in CollectionService:GetTagged("NC_GarageDoor") do
	task.spawn(hookGarage, g)
end
CollectionService:GetInstanceAddedSignal("NC_GarageDoor"):Connect(hookGarage)
