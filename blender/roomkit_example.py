# An example generated room (shown to Claude as a model of a good room script; also a roomgen test).
# A river meadow in late afternoon: the reader on a low rise, the river bending away in front.
soil = kit.mat("soil", (0.33, 0.27, 0.19), kind="soil")
grass_ground = kit.mat("meadow", (0.30, 0.38, 0.17), kind="grass")
blades = kit.mat("blades", (0.34, 0.45, 0.18), kind="foliage")
flowers = kit.mat("flowers", (0.85, 0.80, 0.55), kind="fabric")
bark = kit.mat("bark", (0.24, 0.19, 0.14), kind="bark")
leaves = kit.mat("leaves", (0.20, 0.30, 0.12), kind="foliage")
stone = kit.mat("stone", (0.36, 0.34, 0.30), kind="rock")
river = kit.mat("river", (0.10, 0.14, 0.13), kind="water")

kit.terrain("ground", (80, 80), grass_ground, res=90, relief=0.9, scale=18, seed=5, slope=(0.0, -0.01),
            flat=[(0, 0, 2.0, 0.3)], valley=(-30, 22, 30, 14, 5.0, 1.6))
kit.water("river", (80, 18), -0.6, river, centre=(0, 18))
for i, (x, y) in enumerate(kit.scatter((-25, 26, 25, 38), 7, seed=2, clusters=2, avoid=[(0, 0, 6)])):
    kit.tree(f"tree{i}", (x, y), kit.rng().uniform(7, 12), bark, leaves, kind="broadleaf", seed=i)
for i, (x, y) in enumerate(kit.scatter((-20, 6, 20, 14), 9, seed=3, clusters=3, avoid=[(0, 0, 3)])):
    kit.rock(f"rock{i}", (x, y), kit.rng().uniform(0.3, 1.1), stone, seed=i)
kit.groundcover("grass", blades, (-30, -25, 30, 13), near=(0, 0), blades=7000, height=0.5, seed=4, avoid=[(0, 0, 0.6)], flowers=flowers, flower_share=0.06)
kit.far_hills((0.26, 0.33, 0.24), radius=95, height=9)
kit.sun(22, 200, strength=3.5, color=(1.0, 0.88, 0.70))
kit.sky((0.36, 0.52, 0.78), (0.86, 0.82, 0.74), strength=0.9)
kit.reader((0, 0), (0, 12, 1.2))
