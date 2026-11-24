-- PhoneService: when a player opens their phone, everyone sees them raise their right hand holding it.
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local Remotes = RS:WaitForChild("Remotes")

local function makeProp(hand)
	local phone = Instance.new("Part"); phone.Name = "PhoneProp"
	phone.Size = Vector3.new(0.38, 0.75, 0.06); phone.Color = Color3.fromRGB(20, 20, 24); phone.Material = Enum.Material.SmoothPlastic
	phone.CanCollide = false; phone.CanTouch = false; phone.CanQuery = false; phone.Massless = true
	local screen = Instance.new("Part"); screen.Name = "PhoneScreen"
	screen.Size = Vector3.new(0.33, 0.68, 0.02); screen.Color = Color3.fromRGB(60, 200, 255); screen.Material = Enum.Material.Neon
	screen.CanCollide = false; screen.CanTouch = false; screen.CanQuery = false; screen.Massless = true
	-- held in the palm, screen facing the character's face
	local s = hand.Size
	phone.CFrame = hand.CFrame * CFrame.new(0, -s.Y * 0.35, -s.Z * 0.45) * CFrame.Angles(math.rad(-70), 0, 0)
	screen.CFrame = phone.CFrame * CFrame.new(0, 0, -0.04)
	local w1 = Instance.new("WeldConstraint"); w1.Part0 = hand; w1.Part1 = phone; w1.Parent = phone
	local w2 = Instance.new("WeldConstraint"); w2.Part0 = phone; w2.Part1 = screen; w2.Parent = screen
	screen.Parent = phone
	phone.Parent = hand.Parent
	return phone
end

-- Pose a joint on any rig. Classic bodies use Motor6D (C0); the starter bodies use AnimationConstraint, which we
-- pose by turning its parent-side attachment. Both replicate to every player.
local function poseJoint(j, rot)
	if not j then return end
	if j:IsA("Motor6D") then
		if not j:GetAttribute("RestC0") then j:SetAttribute("RestC0", j.C0) end
		j.C0 = j:GetAttribute("RestC0") * (rot or CFrame.identity)
	elseif j:IsA("AnimationConstraint") and j.Attachment0 then
		local a = j.Attachment0
		if not a:GetAttribute("RestCF") then a:SetAttribute("RestCF", a.CFrame) end
		a.CFrame = a:GetAttribute("RestCF") * (rot or CFrame.identity)
	end
end

local function setPhone(player, open)
	local char = player.Character
	if not char then return end
	local hum = char:FindFirstChildOfClass("Humanoid")
	if hum and hum.SeatPart and hum.SeatPart:IsA("VehicleSeat") then open = false end -- not while driving
	local old = char:FindFirstChild("PhoneProp"); if old then old:Destroy() end
	local upper = char:FindFirstChild("RightUpperArm")
	local lower = char:FindFirstChild("RightLowerArm")
	local shoulder = upper and upper:FindFirstChild("RightShoulder")
	local elbow = lower and lower:FindFirstChild("RightElbow")
	if open then
		poseJoint(shoulder, CFrame.Angles(math.rad(35), math.rad(-25), 0))
		poseJoint(elbow, CFrame.Angles(math.rad(80), 0, 0))
		local hand = char:FindFirstChild("RightHand")
		if hand then makeProp(hand) end
	else
		poseJoint(shoulder, nil)
		poseJoint(elbow, nil)
	end
	char:SetAttribute("PhoneOpen", open)
end

Remotes.PhoneState.OnServerEvent:Connect(function(player, open)
	setPhone(player, open == true)
end)
