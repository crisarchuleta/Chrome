--!nonstrict
-- NCWallet (ModuleScript in ServerScriptService): spend the player's earned money. Uses the game's own NC module
-- (ServerScriptService.NC: NC.GetCash -> leaderstats.Cash, NC.AddCash, NC.Notify), so every purchase lands in
-- the same Cash the jobs, robberies and pickups pay into (and the same DataStore saves it). Falls back to
-- leaderstats.Cash directly if NC isn't there.
local SSS = game:GetService("ServerScriptService")
local RS = game:GetService("ReplicatedStorage")

local NC
do
	local mod = SSS:FindFirstChild("NC") or SSS:WaitForChild("NC", 5)
	if mod then
		local ok, res = pcall(require, mod)
		if ok then
			NC = res
		end
	end
end

local W = {}

function W.Cash(player)
	if NC and NC.GetCash then
		return NC.GetCash(player)
	end
	local ls = player:FindFirstChild("leaderstats")
	return ls and ls:FindFirstChild("Cash")
end

function W.Balance(player)
	local c = W.Cash(player)
	return c and c.Value or 0
end

-- true if the player had the money and it was taken
function W.Spend(player, amount)
	local c = W.Cash(player)
	if not c or c.Value < amount then
		return false
	end
	if NC and NC.AddCash then
		NC.AddCash(player, -amount)
	else
		c.Value -= amount
	end
	return true
end

function W.Refund(player, amount)
	if NC and NC.AddCash then
		NC.AddCash(player, amount)
	else
		local c = W.Cash(player)
		if c then
			c.Value += amount
		end
	end
end

function W.Notify(player, text, color)
	if NC and NC.Notify then
		if pcall(NC.Notify, player, text, color) then
			return
		end
	end
	local remotes = RS:FindFirstChild("Remotes")
	local n = remotes and remotes:FindFirstChild("Notify")
	if n and n:IsA("RemoteEvent") then
		n:FireClient(player, text, color)
	end
end

return W
