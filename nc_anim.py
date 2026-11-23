# nc_anim: the Neon Coast movement animations as pure maths, for any body (no bpy here).
# A rig dict R describes the body: L1/L2 (hip->knee, knee->ankle), hipY (hip joint height), ankY (ankle height),
# heelLift, S (size factor for heights and offsets, 1 = the blocky Roblox body), shZ0 (how far the arms hang out
# from the body in the rest pose, degrees), gaits (per-gait timing and style), extras (optional: a function that
# adds the extra real joints - spine, neck, collarbones, forearm twist, fingers, toes - to each pose).
# Poses are {jointName: (x, y, z) degrees as CFrame.Angles, jointName + "Pos": (x, y, z) translation}, in the
# Roblox joint frame (X right, Y up, Z back; +X lifts arms/thighs forward and bends elbows, knees bend negative,
# +X tips the head/torso back, +Y turns left, +Z tips the right arm out).
import math

D2R = math.pi / 180
STATS = {"over": {}}


def clamp(x, a=-1.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def hermite(p0, p1, m0, m1, u):
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * m0 + (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * m1


def leg_ik(R, dz, dy, clip):
    """ankle relative to the hip (forward = -z, below = -y) -> thigh angle from vertical (forward +), knee flex"""
    L1, L2 = R["L1"], R["L2"]
    D = math.hypot(dz, dy)
    lmax = (L1 + L2) * 0.999
    STATS["over"][clip] = max(STATS["over"].get(clip, 0.0), D - lmax)
    D = min(max(D, 0.35 * R["S"]), lmax)
    phi = math.atan2(-dz, -dy)
    alpha = math.acos(clamp((L1 * L1 + D * D - L2 * L2) / (2 * L1 * D)))
    inner = math.acos(clamp((L1 * L1 + L2 * L2 - D * D) / (2 * L1 * L2)))
    return phi + alpha, math.pi - inner


def leg_pose(R, P, side, foot_z, foot_y, pitch, root_y, pelvis_x, clip, root_z=0.0, hip_y=0.0, hip_z=0.0):
    thigh, kflex = leg_ik(R, foot_z - root_z, foot_y - (R["hipY"] + root_y), clip)
    P[side + "Hip"] = (thigh / D2R - pelvis_x, hip_y, hip_z)
    P[side + "Knee"] = (-kflex / D2R, 0, 0)
    P[side + "Ankle"] = (pitch - (thigh - kflex) / D2R, 0, 0)
    P["_pitch" + side] = pitch


# ------------------------------------------------------------------------------------------------ gaits
def foot_state(R, g, t):
    t %= 1.0
    s, T, v = g["stance"], g["T"], g["v"]
    ank, hl = R["ankY"], R["heelLift"]
    travel = v * s * T
    zf, zb = g["c"] - travel / 2, g["c"] + travel / 2
    if t < s:                                           # planted: rolls heel -> flat -> toe as the body passes over
        u = t / s
        z, y, p = zf + travel * u, ank, 0.0
        if u < 0.15:
            k = 1 - smooth(u / 0.15)
            p, y = g["heel"] * k, y + hl * k
        if u > g["rollS"]:
            r = smooth((u - g["rollS"]) / (1 - g["rollS"]))
            y, p = y + g["toe_rise"] * r, -g["toe_off"] * r
        return z, y, p, True
    u = (t - s) / (1 - s)                               # swing: the foot loops up and forward to meet the ground
    m = v * (1 - s) * T * g["hk"]
    z = hermite(zb, zf, m, m, u)
    y0, y1 = ank + g["toe_rise"], ank + hl
    y = y0 + (y1 - y0) * u + g["lift"] * math.sin(math.pi * u ** g["skew"])
    p = -g["toe_off"] + (g["heel"] + g["toe_off"]) * smooth(u) + 8 * math.sin(math.pi * u)
    return z, y, p, False


def gait_pose(R, name, t):
    g = R["gaits"][name]
    c1, c2 = math.cos(2 * math.pi * t), math.cos(4 * math.pi * t)
    if g["run"]:
        ry_ = -g["drop"] - g["bob"] * math.cos(4 * math.pi * (t - g["stance"] / 2))   # lowest mid-stance, highest in flight
    else:
        ry_ = -g["drop"] - g["bob"] * c2                                               # highest mid-stance
    P = {}
    px, pyaw, proll = g["pelvisX"], g["yaw"] * c1, g["proll"] * math.sin(2 * math.pi * t)
    P["Root"] = (px, pyaw, proll)
    P["RootPos"] = (g["lat"] * math.sin(2 * math.pi * t), ry_, 0.0)
    for side, ph in (("Right", 0.0), ("Left", 0.5)):
        z, y, p, planted_ = foot_state(R, g, t + ph)
        leg_pose(R, P, side, z, y, p, ry_, px, name, hip_y=-pyaw, hip_z=-proll)
        P["_stance" + side] = planted_
    waist_x = g["lean"] - 1.0 * c2
    waist_y = -(g["yaw"] + g["thorax"]) * c1
    P["Waist"] = (waist_x, waist_y, 0)
    P["Neck"] = (-(px + waist_x), g["thorax"] * c1, 0)
    for side, ph, sgn in (("Right", 0.0, 1), ("Left", 0.5, -1)):
        ca = math.cos(2 * math.pi * (t + ph - 0.03))
        sh = g["arm_mean"] - g["arm_amp"] * ca
        el = g["e0"] + (g["eamp"] * ca if g["run"] else -g["eamp"] * ca)
        P[side + "Shoulder"] = (sh, 0, sgn * (g["shZ"] + 2 * ca))
        P[side + "Elbow"] = (el, 0, 0)
        P[side + "Wrist"] = (6, 0, 0)
    return P


def idle_pose(R, t):
    S = R["S"]
    s1, s2 = math.sin(2 * math.pi * t), math.sin(4 * math.pi * t)
    P = {}
    rx, ry_ = 0.05 * S, -0.03 * S
    rz = 1.5 * s1
    P["Root"], P["RootPos"] = (0, 0, rz), (rx * s1 / 1.0, ry_, 0)
    for side, sx in (("Right", 1), ("Left", -1)):
        lean_in = -math.atan2(rx * s1, R["hipY"] - R["ankY"]) / D2R
        bend = 4 * max(0.0, -s1 * sx)
        leg_pose(R, P, side, -0.02 * S, R["ankY"], 0, ry_ - bend * 0.004 * S, 0, "Idle", hip_z=-rz + lean_in)
    P["Waist"] = (-1 + 1.1 * math.sin(2 * math.pi * t + 0.6), 3 * s1, 0)
    P["Neck"] = (1.0 * math.sin(2 * math.pi * t + 1.2), -5 * s1 + 2.5 * s2, 0)
    for side, sgn in (("Right", 1), ("Left", -1)):
        P[side + "Shoulder"] = (2 + 1.5 * math.sin(2 * math.pi * t + 0.6), 0, sgn * (5 + 1.0 * s1))
        P[side + "Elbow"] = (10 + 2 * math.sin(2 * math.pi * t + 0.6), 0, 0)
        P[side + "Wrist"] = (5, 0, 0)
    return P


def tired_pose(R, t):
    S = R["S"]
    b = math.sin(4 * math.pi * t)
    P = {}
    ry_, rz_, px = (-0.42 + 0.02 * b) * S, 0.30 * S, -12
    P["Root"], P["RootPos"] = (px, 0, 0), (0, ry_, rz_)
    for side in ("Right", "Left"):
        leg_pose(R, P, side, -0.05 * S, R["ankY"], 0, ry_, px, "TiredIdle", root_z=rz_)
    P["Waist"] = (-40 + 3 * b, 0, 0)
    P["Neck"] = (38 - 2 * b, 0, 0)
    for side, sgn in (("Right", 1), ("Left", -1)):
        P[side + "Shoulder"] = (52 + 3 * b, 0, sgn * 10)
        P[side + "Elbow"] = (22, 0, 0)
        P[side + "Wrist"] = (-12, 0, 0)
    return P


def fall_pose(R, t):
    s = math.sin(2 * math.pi * t)
    P = {"Root": (-4, 0, 0), "RootPos": (0, 0, 0)}
    P["RightHip"], P["RightKnee"] = (28 + 10 * s, 0, 0), (-(55 + 15 * s), 0, 0)
    P["LeftHip"], P["LeftKnee"] = (12 - 10 * s, 0, 0), (-(35 - 12 * s), 0, 0)
    P["RightAnkle"] = P["LeftAnkle"] = (10, 0, 0)
    P["Waist"], P["Neck"] = (-6, 0, 0), (6, 0, 0)
    for side, sgn, ph in (("Right", 1, 0), ("Left", -1, 0.5)):
        w = math.sin(2 * math.pi * (t + ph) + 1)
        P[side + "Shoulder"] = (30 + 8 * w, 0, sgn * (48 + 6 * w))
        P[side + "Elbow"] = (35 + 10 * w, 0, 0)
    return P


# ------------------------------------------------------------------------------------------------ one-shot moves
def arms(sh, el, z=0, sh_l=None, el_l=None, z_l=None):
    return {"RightShoulder": (sh, 0, z), "LeftShoulder": (sh if sh_l is None else sh_l, 0, -(z if z_l is None else z_l)),
            "RightElbow": (el, 0, 0), "LeftElbow": (el if el_l is None else el_l, 0, 0)}


def crouch_key(R, drop, back=0.0, px=0.0, waist=0.0, neck=0.0, a=None, foot=(-0.02, -0.02), clip=""):
    S = R["S"]
    P = {"Root": (px, 0, 0), "RootPos": (0, -drop * S, back * S), "Waist": (waist, 0, 0), "Neck": (neck, 0, 0)}
    for side, fz in (("Right", foot[0]), ("Left", foot[1])):
        leg_pose(R, P, side, fz * S, R["ankY"], 0, P["RootPos"][1], px, clip, root_z=P["RootPos"][2])
    if a:
        P.update(a)
    return P


def roll_keys(R):
    S = R["S"]
    c_stand = R["hipY"] + 0.8 * S
    keys = []
    for i in range(9):
        t = i / 8
        th = -360 * smooth(t)
        a = math.sin(math.pi * t)
        c = c_stand - 1.5 * S * a ** 1.1                  # the tucked body's middle, low along the ground
        pv = 0.8 * S
        P = {"Root": (th, 0, 0), "RootPos": (0, c - c_stand + pv * (1 - math.cos(th * D2R)), -pv * math.sin(th * D2R))}
        P.update({"RightHip": (115 * a, 0, 0), "LeftHip": (115 * a, 0, 0), "RightKnee": (-135 * a, 0, 0), "LeftKnee": (-135 * a, 0, 0),
                  "Waist": (-30 * a, 0, 0), "Neck": (-40 * a, 0, 0)})
        P.update(arms(70 * a, 100 * a, 15 * a))
        keys.append((t, P))
    return keys


def oneshots(R):
    S = R["S"]
    C = {}
    C["JumpUp"] = dict(dur=0.4, keys=[
        (0.0, dict(RightHip=(15, 0, 0), LeftHip=(15, 0, 0), RightKnee=(-25, 0, 0), LeftKnee=(-25, 0, 0), Waist=(-6, 0, 0), **arms(10, 20, 6))),
        (0.3, dict(RightHip=(8, 0, 0), LeftHip=(2, 0, 0), RightKnee=(-6, 0, 0), LeftKnee=(-4, 0, 0), RightAnkle=(-25, 0, 0), LeftAnkle=(-25, 0, 0),
                   Waist=(-3, 0, 0), **arms(70, 25, 25))),
        (1.0, dict(RightHip=(38, 0, 0), LeftHip=(22, 0, 0), RightKnee=(-58, 0, 0), LeftKnee=(-40, 0, 0), RightAnkle=(5, 0, 0), LeftAnkle=(5, 0, 0),
                   Waist=(-5, 0, 0), **arms(40, 30, 35))),
    ])
    C["Land"] = dict(dur=0.32, keys=[
        (0.0, crouch_key(R, 0.0, clip="Land")),
        (0.35, crouch_key(R, 0.42, waist=-12, neck=8, a=arms(25, 30, 12), clip="Land")),
        (1.0, crouch_key(R, 0.03, clip="Land")),
    ])
    C["LandHard"] = dict(dur=0.7, keys=[
        (0.0, crouch_key(R, 0.1, clip="LandHard")),
        (0.18, crouch_key(R, 0.95, px=-10, waist=-30, neck=28, a=arms(55, 35, 15), clip="LandHard")),
        (0.55, crouch_key(R, 0.85, px=-8, waist=-26, neck=24, a=arms(45, 30, 12), clip="LandHard")),
        (1.0, crouch_key(R, 0.03, clip="LandHard")),
    ])
    C["Stumble"] = dict(dur=0.45, keys=[
        (0.0, crouch_key(R, 0.05, clip="Stumble")),
        (0.3, crouch_key(R, 0.45, waist=-14, neck=10, a=arms(30, 35, 40), clip="Stumble")),
        (1.0, crouch_key(R, 0.03, clip="Stumble")),
    ])
    C["Roll"] = dict(dur=0.65, keys=roll_keys(R))
    C["Vault"] = dict(dur=0.55, keys=[
        (0.0, dict(RightHip=(20, 0, 0), LeftHip=(-10, 0, 0), RightKnee=(-25, 0, 0), LeftKnee=(-30, 0, 0), **arms(30, 25, 8, sh_l=-5))),
        (0.25, dict(Root=(0, 15, -22), RightHip=(75, 0, 0), LeftHip=(70, 0, 0), RightKnee=(-95, 0, 0), LeftKnee=(-92, 0, 0),
                    Waist=(-18, -10, 0), Neck=(-10, 10, 0), **arms(65, 5, 25, sh_l=40, el_l=30, z_l=70))),
        (0.5, dict(Root=(0, 20, -28), RightHip=(85, 0, 0), LeftHip=(82, 0, 0), RightKnee=(-100, 0, 0), LeftKnee=(-98, 0, 0),
                   Waist=(-14, -12, 0), Neck=(-6, 12, 0), **arms(35, 8, 35, sh_l=30, el_l=25, z_l=85))),
        (0.75, dict(Root=(0, 6, -8), RightHip=(30, 0, 0), LeftHip=(40, 0, 0), RightKnee=(-35, 0, 0), LeftKnee=(-50, 0, 0),
                    Waist=(-6, -4, 0), **arms(20, 15, 20, sh_l=15, z_l=50))),
        (1.0, dict(RightHip=(15, 0, 0), LeftHip=(-5, 0, 0), RightKnee=(-20, 0, 0), LeftKnee=(-25, 0, 0), **arms(10, 20, 6))),
    ])
    C["Mantle"] = dict(dur=0.75, keys=[
        (0.0, dict(**arms(10, 15, 6))),
        (0.25, dict(RightHip=(25, 0, 0), LeftHip=(25, 0, 0), RightKnee=(-40, 0, 0), LeftKnee=(-40, 0, 0), Waist=(-10, 0, 0), Neck=(12, 0, 0), **arms(150, 25, 10))),
        (0.45, dict(RightHip=(60, 0, 0), LeftHip=(20, 0, 0), RightKnee=(-100, 0, 0), LeftKnee=(-40, 0, 0), Waist=(-30, 0, 0), Neck=(18, 0, 0), **arms(70, 95, 10))),
        (0.7, dict(RightHip=(105, 0, 0), LeftHip=(20, 0, 0), RightKnee=(-120, 0, 0), LeftKnee=(-50, 0, 0), Waist=(-25, 0, 0), Neck=(10, 0, 0), **arms(25, 10, 8))),
        (1.0, dict(**arms(4, 10, 5))),
    ])
    C["Climb"] = dict(dur=1.3, keys=[
        (0.0, dict(**arms(5, 10, 5))),
        (0.12, dict(RightHip=(30, 0, 0), LeftHip=(30, 0, 0), RightKnee=(-50, 0, 0), LeftKnee=(-50, 0, 0), Waist=(-12, 0, 0), **arms(40, 30, 8))),
        (0.26, dict(RightHip=(15, 0, 0), LeftHip=(10, 0, 0), RightKnee=(-25, 0, 0), LeftKnee=(-20, 0, 0), Neck=(25, 0, 0), **arms(155, 8, 8))),
        (0.38, dict(RightHip=(8, 0, 0), LeftHip=(14, 0, 0), RightKnee=(-15, 0, 0), LeftKnee=(-22, 0, 0), Neck=(22, 0, 0), **arms(152, 12, 8))),
        (0.5, dict(RightHip=(30, 0, 0), LeftHip=(38, 0, 0), RightKnee=(-55, 0, 0), LeftKnee=(-62, 0, 0), Neck=(15, 0, 0), **arms(150, 60, 8))),
        (0.62, dict(RightHip=(36, 0, 0), LeftHip=(42, 0, 0), RightKnee=(-58, 0, 0), LeftKnee=(-64, 0, 0), Waist=(-10, 0, 0), Neck=(5, 0, 0), **arms(90, 115, 10))),
        (0.72, dict(RightHip=(40, 0, 0), LeftHip=(40, 0, 0), RightKnee=(-60, 0, 0), LeftKnee=(-60, 0, 0), Waist=(-12, 0, 0), **arms(35, 75, 10))),
        (0.86, dict(RightHip=(105, 0, 0), LeftHip=(10, 0, 0), RightKnee=(-118, 0, 0), LeftKnee=(-40, 0, 0), Waist=(-22, 0, 0), **arms(10, 15, 10))),
        (1.0, dict(**arms(4, 10, 5))),
    ])
    gk = {"Root": (-10, 0, 0), "RootPos": (0, -0.85 * S, 0.1 * S), "Waist": (-25, 0, 0), "Neck": (18, 0, 0),
          "RightHip": (-2, 0, 4), "RightKnee": (-92, 0, 0), "RightAnkle": (-40, 0, 0)}
    leg_pose(R, gk, "Left", -0.95 * S, R["ankY"], 0, -0.85 * S, -10, "GetUp", root_z=0.1 * S)
    gk.update(arms(45, 30, 6, sh_l=50, el_l=20))
    gm = {"Root": (-6, 0, 0), "RootPos": (0, -0.45 * S, 0.05 * S), "Waist": (-15, 0, 0), "Neck": (10, 0, 0)}
    leg_pose(R, gm, "Right", 0.15 * S, R["ankY"], 0, -0.45 * S, -6, "GetUp", root_z=0.05 * S)
    leg_pose(R, gm, "Left", -0.55 * S, R["ankY"], 0, -0.45 * S, -6, "GetUp", root_z=0.05 * S)
    gm.update(arms(25, 20, 6))
    C["GetUp"] = dict(dur=0.9, keys=[(0.0, gk), (0.5, gm), (1.0, crouch_key(R, 0.03, clip="GetUp", a=arms(4, 10, 5)))])
    C["Bump"] = dict(dur=0.45, keys=[
        (0.0, dict(**arms(10, 20, 6))),
        (0.3, dict(Root=(4, 0, 0), RootPos=(0, -0.15 * S, 0.1 * S), Waist=(16, 0, 0), Neck=(22, 0, 0), RightHip=(-10, 0, 0), LeftHip=(20, 0, 0),
                   RightKnee=(-20, 0, 0), LeftKnee=(-25, 0, 0), **arms(60, 85, 20))),
        (1.0, dict(**arms(5, 12, 5))),
    ])
    sk = {"Root": (12, 0, 0), "RootPos": (0, -0.4 * S, 0.15 * S), "Waist": (4, 0, 0), "Neck": (-8, 0, 0),
          "RightHip": (38, 0, 0), "RightKnee": (-12, 0, 0), "RightAnkle": (18, 0, 0),
          "LeftHip": (-22, 0, 0), "LeftKnee": (-55, 0, 0), "LeftAnkle": (-10, 0, 0)}
    sk.update(arms(45, 40, 28))
    sk2 = dict(sk)
    sk2.update({"RootPos": (0, -0.3 * S, 0.1 * S), "Root": (8, 0, 0)})
    C["Skid"] = dict(dur=0.55, keys=[(0.0, dict(**arms(20, 70, 8))), (0.25, sk), (0.7, sk2), (1.0, dict(**arms(6, 14, 5)))])
    pv = dict(sk)
    pv.update({"Root": (8, -20, 0), "RootPos": (0, -0.5 * S, 0.1 * S), "Waist": (0, 18, 0)})
    C["Pivot"] = dict(dur=0.38, keys=[(0.0, dict(**arms(15, 60, 8))), (0.4, pv), (1.0, dict(**arms(10, 50, 8)))])
    return C


def loops(R):
    g = R["gaits"]
    return {  # name: (pose function of normalised time, duration s, samples per loop)
        "Idle": (lambda t: idle_pose(R, t), 4.0, 48), "TiredIdle": (lambda t: tired_pose(R, t), 2.0, 32),
        "Fall": (lambda t: fall_pose(R, t), 1.2, 24),
        "Walk": (lambda t: gait_pose(R, "Walk", t), g["Walk"]["T"], 24),
        "Jog": (lambda t: gait_pose(R, "Jog", t), g["Jog"]["T"], 24),
        "Sprint": (lambda t: gait_pose(R, "Sprint", t), g["Sprint"]["T"], 24),
    }


BLEND = {"Vault": (0.1, 0.12), "Mantle": (0.08, 0.12), "Climb": (0.08, 0.1), "Roll": (0.0, 0.0), "Land": (0.05, 0.25),
         "LandHard": (0.04, 0.2), "Stumble": (0.04, 0.25), "GetUp": (0.0, 0.25), "Bump": (0.1, 0.3), "Skid": (0.12, 0.3),
         "Pivot": (0.15, 0.3), "JumpUp": (0.15, 0.0)}


def finalize(R, P, clip, t):
    """rest-pose arm offset, then the body's extra joints (if it has them); drops the private _keys"""
    out = dict(P)
    z0 = R.get("shZ0", 0)
    if z0:
        for side, sgn in (("Right", 1), ("Left", -1)):
            x, y, z = out.get(side + "Shoulder", (0, 0, 0))
            out[side + "Shoulder"] = (x, y, z - sgn * z0)
    if R.get("extras"):
        R["extras"](R, out, P, clip, t)
    return {k: v for k, v in out.items() if not k.startswith("_")}


# ------------------------------------------------------------------------------------------------ blocky R15
GAITS_R15 = {
    "Walk": dict(v=5.0, T=0.64, stance=0.62, c=0.10, drop=0.16, bob=0.045, run=False, heel=12, toe_off=32, rollS=0.62,
                 toe_rise=0.30, lift=0.26, skew=1.0, hk=1.0, pelvisX=-1, yaw=5, proll=3, lat=0.05, lean=-3, thorax=7,
                 arm_mean=2, arm_amp=16, e0=14, eamp=10, shZ=6),
    "Jog": dict(v=16.0, T=0.50, stance=0.27, c=0.12, drop=0.26, bob=0.10, run=True, heel=4, toe_off=38, rollS=0.45,
                toe_rise=0.25, lift=0.75, skew=0.6, hk=0.6, pelvisX=-4, yaw=7, proll=4, lat=0.04, lean=-7, thorax=10,
                arm_mean=6, arm_amp=30, e0=82, eamp=8, shZ=10),
    "Sprint": dict(v=25.0, T=0.42, stance=0.21, c=0.05, drop=0.30, bob=0.09, run=True, heel=-6, toe_off=42, rollS=0.35,
                   toe_rise=0.30, lift=1.15, skew=0.55, hk=0.6, pelvisX=-6, yaw=8, proll=3, lat=0.03, lean=-13, thorax=12,
                   arm_mean=8, arm_amp=52, e0=92, eamp=22, shZ=8),
}
RIG_R15 = dict(L1=1.0, L2=0.7, hipY=2.0, ankY=0.3, heelLift=0.05, S=1.0, shZ0=0, gaits=GAITS_R15)
