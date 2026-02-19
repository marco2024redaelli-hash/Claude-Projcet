"""
Floor Plan – 10 × 5 m, two rooms, central door
================================================
Library: llmcad (BuildCAD AI)

Layout (top view):
 ┌────────────┬────────────┐
 │            ┊            │   5 m
 │   Room 1   ┊   Room 2   │
 │          [door]         │
 └────────────┴────────────┘
            10 m

Wall thickness : 0.20 m
Wall height    : 2.80 m
Door           : 0.90 m × 2.10 m (centred on the internal wall)
Floor slab     : 0.15 m thick
"""

import llmcad as cad
from llmcad.body import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut, Body
from llmcad.ops import gp_Trsf, gp_Vec, BRepBuilderAPI_Transform

# ─── Parameters ─────────────────────────────────────────
L = 10.0  # length along X  (m)
W = 5.0  # width  along Y  (m)
t = 0.2  # wall thickness   (m)
H = 2.8  # wall height      (m)
door_w = 0.9  # door width       (m)
door_h = 2.1  # door height      (m)
slab_h = 0.15  # floor slab depth (m)
floor_hole_d = 3.0  # floor hole diameter (m)

# ─── 1. Outer walls via shell ───────────────────────────
outer = cad.Box(L, W, H, name="outer")
walls = cad.shell(outer, t, open=[outer.top, outer.bottom], name="outer_walls")

# ─── 2. Internal dividing wall (full height at X centre) ─
mid_x = L / 2.0 - t / 2.0  # X origin of internal wall
iwall = cad.Box(t, W - 2 * t, H, name="iwall")

trsf = gp_Trsf()
trsf.SetTranslation(gp_Vec(mid_x, t, 0))
iwall_moved = BRepBuilderAPI_Transform(iwall.part, trsf, True).Shape()

# Fuse outer walls + internal wall
fused = BRepAlgoAPI_Fuse(walls.part, iwall_moved)
fused.Build()

# ─── 3. Door opening (centred on Y) ─────────────────────
door_y = (W - door_w) / 2.0
door_cut = cad.Box(t + 0.04, door_w, door_h, name="door_cut")

trsf2 = gp_Trsf()
trsf2.SetTranslation(gp_Vec(mid_x - 0.02, door_y, 0))
door_moved = BRepBuilderAPI_Transform(door_cut.part, trsf2, True).Shape()

cut = BRepAlgoAPI_Cut(fused.Shape(), door_moved)
cut.Build()

# ─── 4. Raise walls onto the floor slab ─────────────────
trsf3 = gp_Trsf()
trsf3.SetTranslation(gp_Vec(0, 0, slab_h))
walls_up = BRepBuilderAPI_Transform(cut.Shape(), trsf3, True).Shape()

# ─── 5. Floor slab ──────────────────────────────────────
floor = cad.Box(L, W, slab_h, name="floor")

# ─── 6. Combine everything ──────────────────────────────
final = BRepAlgoAPI_Fuse(floor.part, walls_up)
final.Build()

# ─── 7. 3 m hole at origin (X=0, Y=0) ────────────────────
floor_cyl = cad.Cylinder(floor_hole_d / 2.0, slab_h + 0.04, name="floor_hole")
trsf4 = gp_Trsf()
trsf4.SetTranslation(gp_Vec(0.0, 0.0, -0.02))
floor_hole_moved = BRepBuilderAPI_Transform(floor_cyl.part, trsf4, True).Shape()
fh_cut = BRepAlgoAPI_Cut(final.Shape(), floor_hole_moved)
fh_cut.Build()

# ─── 8. 3 m hole at X=-2.5, Y=0 ──────────────────────────
floor_cyl2 = cad.Cylinder(floor_hole_d / 2.0, slab_h + 0.04, name="floor_hole_2")
trsf5 = gp_Trsf()
trsf5.SetTranslation(gp_Vec(-2.5, 0.0, -0.02))
fh2_moved = BRepBuilderAPI_Transform(floor_cyl2.part, trsf5, True).Shape()
fh_cut2 = BRepAlgoAPI_Cut(fh_cut.Shape(), fh2_moved)
fh_cut2.Build()

# ─── 9. 3 m hole at X=2.5, Y=0 ───────────────────────────
floor_cyl3 = cad.Cylinder(floor_hole_d / 2.0, slab_h + 0.04, name="floor_hole_3")
trsf6 = gp_Trsf()
trsf6.SetTranslation(gp_Vec(2.5, 0.0, -0.02))
fh3_moved = BRepBuilderAPI_Transform(floor_cyl3.part, trsf6, True).Shape()
fh_cut3 = BRepAlgoAPI_Cut(fh_cut2.Shape(), fh3_moved)
fh_cut3.Build()

result = Body(fh_cut3.Shape(), name="floor_plan_10x5")
# Esporta il modello finale in formato STEP
cad.export_step(result, "planimetria_10x5.step")
cad.export_stl(result, "planimetria_10x5.stl")

print("File esportato con successo: planimetria_10x5.step")
cad.show(result)
