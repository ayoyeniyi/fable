# Fields to Netherfield after rain: early overcast morning, footpath toward a stile, cart ruts with puddles.
soil = kit.mat("mud", (0.24, 0.19, 0.14), kind="soil", rough=0.35)
meadow = kit.mat("meadow", (0.25, 0.30, 0.17), kind="grass")
blades = kit.mat("wetgrass", (0.28, 0.37, 0.18), kind="foliage")
dryblades = kit.mat("dryblades", (0.40, 0.41, 0.25), kind="foliage")
seedheads = kit.mat("seedheads", (0.55, 0.52, 0.40), kind="fabric")
hedgeleaf = kit.mat("hedgeleaf", (0.19, 0.24, 0.13), kind="foliage")
hedgeleaf2 = kit.mat("hedgeleaf2", (0.24, 0.26, 0.15), kind="foliage")
bark = kit.mat("bark", (0.22, 0.19, 0.16), kind="bark")
farleaf = kit.mat("farleaf", (0.30, 0.33, 0.27), kind="foliage")
wood = kit.mat("oldwood", (0.38, 0.34, 0.29), kind="wood")
iron = kit.mat("iron", (0.16, 0.15, 0.14), kind="metal")
stone = kit.mat("stone", (0.40, 0.38, 0.34), kind="rock")
puddle = kit.mat("puddle", (0.36, 0.39, 0.42), kind="water", rough=0.08)
hwall = kit.mat("housewall", (0.72, 0.68, 0.60), kind="plaster")
hroof = kit.mat("houseroof", (0.34, 0.33, 0.33), kind="slate")
trim = kit.mat("trim", (0.84, 0.82, 0.77), kind="plaster")
glass = kit.mat("glass", (0.20, 0.22, 0.25), kind="glass")

rng = kit.rng()

RX, RY = -1.3, 0.0  # reader stands on the grass beside the path

kit.terrain("fields", (200, 200), meadow, res=70, relief=0.7, scale=25, seed=7,
            slope=(0.0, -0.012), flat=[(RX, RY, 2.5, 0.5), (45, 105, 22, -1.2)],
            centre=(0, 40))

# Hedges: left of this field (set back), across its far end with stile and gate, right field, far, behind.
kit.hedge("hedge_left", [(-7.5, -30), (-7.0, -12), (-7.8, 0), (-7.0, 8), (-6.5, 12.5)],
          hedgeleaf, height=2.2, width=1.6, seed=2, near=(RX, RY), stems=bark, detail=1)
kit.hedge("hedge_cross", [(-6.5, 12.5), (5, 12.2), (15, 13), (32, 12)],
          hedgeleaf2, height=1.8, width=1.5, seed=3, near=(RX, RY), stems=bark,
          gaps=[(3.5, 12.3, 1.2), (9.5, 12.6, 3.6)])
kit.hedge("hedge_right", [(24, -24), (23, -8), (25, 4), (24, 12.2)], hedgeleaf, height=2.0,
          width=1.5, seed=9, near=(RX, RY), stems=bark)
kit.hedge("hedge_far", [(-60, 48), (0, 45), (60, 50)], hedgeleaf, height=2.0, seed=4,
          near=(RX, RY), detail=0, gaps=[(12, 46, 4)])
kit.hedge("hedge_back", [(-40, -26), (-6, -24), (0, -23.5), (30, -25)], hedgeleaf2, height=1.9,
          seed=6, near=(RX, RY), detail=0, gaps=[(0.6, -24, 1.4), (7, -24.5, 3.5)])

# Shrubs pushing out of the hedge foot to break its line.
for i, (x, y, s) in enumerate([(-6.2, -6, 0.9), (-6.0, 3.5, 0.6), (-5.4, 10.8, 1.0), (13, 12.0, 0.8),
                               (20, 11.6, 1.1), (22.6, -3, 0.9), (23.2, 7, 0.7)]):
    kit.shrub(f"hshrub{i}", (x, y), s, hedgeleaf2 if i % 2 else hedgeleaf, seed=20 + i, stems=bark)

kit.stile("stile", (3.5, 12.3), wood, rot=3, kind="step")
kit.stile("stile_back", (0.6, -24), wood, rot=0, kind="step")
kit.gate("gate", (9.5, 12.6), wood, rot=4, width=3.2, open_deg=25, iron=iron)
kit.fence("fence_right", [(10, -22), (9.6, -5), (10.2, 11)], wood, kind="rail", seed=5)

# Footpath and the rutted cart track with puddles.
kit.footpath("path", [(0.6, -30), (0.4, -10), (0.3, 0), (1.5, 7), (3.5, 12.3), (5, 25), (8, 44)],
             soil, width=0.8, seed=1, wear=0.7, puddles=puddle)
kit.footpath("track", [(7, -30), (6.6, -8), (6.8, 4), (9.5, 12.6), (12, 30), (12, 46), (25, 80), (40, 98)],
             soil, width=2.8, ruts=True, puddles=puddle, seed=2, wear=0.6)

# Bare hedgerow trees, and clumps of trees about the house.
kit.tree("oak_left", (-8.2, 6), 11, bark, farleaf, kind="dead", seed=3, lean=4, detail=1)
kit.tree("oak_right", (14, 13.6), 12, bark, farleaf, kind="dead", seed=8, lean=7, detail=1)
kit.tree("ash_left", (-7.8, -14), 9, bark, farleaf, kind="dead", seed=12, lean=9, detail=1)
kit.tree("ash_right", (24.5, -6), 10, bark, farleaf, kind="dead", seed=17, lean=5, detail=1)
kit.tree("elm_back", (-14, -24.5), 13, bark, farleaf, kind="dead", seed=15, lean=3, detail=0)
for i, (x, y, h) in enumerate([(-24, 47, 13), (-19, 49, 10), (-28, 50, 11), (30, 49, 14), (34, 51, 11),
                               (28, 100, 15), (32, 104, 12), (62, 110, 16), (66, 104, 12), (-10, 100, 13)]):
    kit.tree(f"far_tree{i}", (x, y), h * rng.uniform(0.9, 1.1), bark, farleaf, kind="broadleaf",
             seed=10 + i, lean=rng.uniform(2, 8), detail=0)

kit.house("netherfield", (45, 108), (30, 16), hwall, hroof, trim, glass, storeys=3, bays=7,
          roof_kind="hipped", rot=-12, detail=0, seed=2)

# Stones by the stile and gateway, wet grass tufts along the path, hedge foot and right field.
for i, (x, y) in enumerate(kit.scatter((2, 9, 11, 12), 5, seed=6, clusters=2, avoid=[(3.5, 12.3, 0.9), (9.5, 12.6, 1.8)])):
    kit.rock(f"stone{i}", (x, y), rng.uniform(0.2, 0.5), stone, seed=i)
kit.tufts("tufts_stile", (2.4, 11.2), 1.2, 70, 0.6, blades, seed=3, flowers=seedheads, flower_share=0.1)
kit.tufts("tufts_path", (1.4, 3.5), 0.9, 50, 0.5, dryblades, seed=4)
kit.tufts("tufts_hedgefoot", (-5.8, -2.5), 1.4, 80, 0.7, dryblades, seed=7, flowers=seedheads, flower_share=0.08)
kit.tufts("tufts_fence", (8.8, 2), 1.3, 60, 0.6, dryblades, seed=8)
for i, (x, y) in enumerate(kit.scatter((12, -15, 22, 10), 6, seed=11, clusters=3, avoid=[(RX, RY, 3)])):
    kit.tufts(f"tuss{i}", (x, y), rng.uniform(0.5, 1.0), 40, rng.uniform(0.4, 0.65), dryblades, seed=30 + i)
kit.groundcover("grass", blades, (-30, -24, 30, 30), near=(RX, RY), blades=9500, height=0.45, seed=5,
                avoid=[(RX, RY, 0.7)], flowers=seedheads, flower_share=0.02, patchiness=0.45)

kit.far_hills((0.42, 0.46, 0.42), radius=140, height=9)
kit.sun(14, -20, strength=1.8, color=(1.0, 0.93, 0.84), softness=8.0)
kit.sky((0.60, 0.64, 0.70), (0.83, 0.83, 0.80), strength=1.0, radius=160)
kit.reader((RX, RY), (0.5, 14, 1.4))
