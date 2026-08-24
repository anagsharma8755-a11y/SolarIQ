import type { BuildingInput, DemoBuilding } from "./types";

// ─── Building B001: Standard Box (20×20×10) ───
const B001: DemoBuilding = {
  building_id: "B001",
  name: "Standard Office Block",
  surfaces: [
    { surface_id: "B001-S001", vertices: [[0,0,10],[20,0,10],[20,20,10],[0,20,10]] },
    { surface_id: "B001-S002", vertices: [[0,0,0],[0,20,0],[0,20,10],[0,0,10]] },
    { surface_id: "B001-S003", vertices: [[20,0,0],[20,0,10],[20,20,10],[20,20,0]] },
    { surface_id: "B001-S004", vertices: [[0,0,0],[20,0,0],[20,0,10],[0,0,10]] },
    { surface_id: "B001-S005", vertices: [[0,20,0],[0,20,10],[20,20,10],[20,20,0]] },
    { surface_id: "B001-S006", vertices: [[0,0,0],[0,20,0],[20,20,0],[20,0,0]] },
  ],
};

// ─── Building B002: Compact Tower Base (15×15×15) ───
const B002: DemoBuilding = {
  building_id: "B002",
  name: "Compact Commercial",
  surfaces: [
    { surface_id: "B002-S001", vertices: [[30,0,15],[45,0,15],[45,15,15],[30,15,15]] },
    { surface_id: "B002-S002", vertices: [[30,0,0],[30,15,0],[30,15,15],[30,0,15]] },
    { surface_id: "B002-S003", vertices: [[45,0,0],[45,0,15],[45,15,15],[45,15,0]] },
  ],
};

// ─── Building B003: L-Shape (two connected rectangular sections) ───
// Main wing: x=55-75, z=0-10, height=12
// Side wing: x=55-65, z=10-20, height=12
const B003: DemoBuilding = {
  building_id: "B003",
  name: "L-Shaped Residential",
  surfaces: [
    // Roof: main wing
    { surface_id: "B003-R001", vertices: [[55,12,0],[75,12,0],[75,12,10],[55,12,10]] },
    // Roof: side wing
    { surface_id: "B003-R002", vertices: [[55,12,10],[65,12,10],[65,12,20],[55,12,20]] },
    // South facade (main wing front)
    { surface_id: "B003-F001", vertices: [[55,0,0],[75,0,0],[75,12,0],[55,12,0]] },
    // East facade (main wing right)
    { surface_id: "B003-F002", vertices: [[75,0,0],[75,0,10],[75,12,10],[75,12,0]] },
    // Inner corner east (main→side transition)
    { surface_id: "B003-F003", vertices: [[75,0,10],[65,0,10],[65,12,10],[75,12,10]] },
    // Inner corner north (side wing east)
    { surface_id: "B003-F004", vertices: [[65,0,10],[65,0,20],[65,12,20],[65,12,10]] },
    // North facade (side wing back)
    { surface_id: "B003-F005", vertices: [[55,0,20],[65,0,20],[65,12,20],[55,12,20]] },
    // West facade (full height, both wings)
    { surface_id: "B003-F006", vertices: [[55,0,0],[55,0,20],[55,12,20],[55,12,0]] },
  ],
};

// ─── Building B004: Tall Tower (8×8×30) ───
const B004: DemoBuilding = {
  building_id: "B004",
  name: "High-Rise Tower",
  surfaces: [
    { surface_id: "B004-R001", vertices: [[85,30,0],[93,30,0],[93,30,8],[85,30,8]] },
    { surface_id: "B004-F001", vertices: [[85,0,0],[93,0,0],[93,30,0],[85,30,0]] },
    { surface_id: "B004-F002", vertices: [[93,0,0],[93,0,8],[93,30,8],[93,30,0]] },
    { surface_id: "B004-F003", vertices: [[85,0,8],[93,0,8],[93,30,8],[85,30,8]] },
    { surface_id: "B004-F004", vertices: [[85,0,0],[85,0,8],[85,30,8],[85,30,0]] },
  ],
};

// ─── Building B005: Stepped / Terraced (two levels) ───
// Base level: x=0-20, z=30-50, height=6
// Upper level: x=0-14, z=30-50, height=12
const B005: DemoBuilding = {
  building_id: "B005",
  name: "Terraced Complex",
  surfaces: [
    // Lower roof (terrace level)
    { surface_id: "B005-R001", vertices: [[0,6,30],[20,6,30],[20,6,50],[0,6,50]] },
    // Upper roof
    { surface_id: "B005-R002", vertices: [[0,12,30],[14,12,30],[14,12,50],[0,12,50]] },
    // South facade: base level
    { surface_id: "B005-F001", vertices: [[0,0,30],[20,0,30],[20,6,30],[0,6,30]] },
    // South facade: upper level step
    { surface_id: "B005-F002", vertices: [[0,6,30],[14,6,30],[14,12,30],[0,12,30]] },
    // East facade: base level
    { surface_id: "B005-F003", vertices: [[20,0,30],[20,0,50],[20,6,50],[20,6,30]] },
    // East facade: upper level (visible above base)
    { surface_id: "B005-F004", vertices: [[14,6,30],[14,6,50],[14,12,50],[14,12,30]] },
    // North facade: base level
    { surface_id: "B005-F005", vertices: [[0,0,50],[20,0,50],[20,6,50],[0,6,50]] },
    // North facade: upper level
    { surface_id: "B005-F006", vertices: [[0,6,50],[14,6,50],[14,12,50],[0,12,50]] },
    // West facade (full height)
    { surface_id: "B005-F007", vertices: [[0,0,30],[0,0,50],[0,12,50],[0,12,30]] },
  ],
};

// ─── Building B006: Wide Warehouse (30×20×6) ───
const B006: DemoBuilding = {
  building_id: "B006",
  name: "Industrial Warehouse",
  surfaces: [
    { surface_id: "B006-R001", vertices: [[30,6,30],[60,6,30],[60,6,50],[30,6,50]] },
    { surface_id: "B006-F001", vertices: [[30,0,30],[60,0,30],[60,6,30],[30,6,30]] },
    { surface_id: "B006-F002", vertices: [[60,0,30],[60,0,50],[60,6,50],[60,6,30]] },
    { surface_id: "B006-F003", vertices: [[30,0,50],[60,0,50],[60,6,50],[30,6,50]] },
    { surface_id: "B006-F004", vertices: [[30,0,30],[30,0,50],[30,6,50],[30,6,30]] },
  ],
};

// ─── Building B007: Gabled / Pitched Roof ───
// Ridge runs along z-axis at x=10, y=14 (6m above 8m walls)
// Two sloped roof surfaces meet at a central ridge
const B007: DemoBuilding = {
  building_id: "B007",
  name: "Gabled Residence",
  surfaces: [
    // South-facing roof slope
    { surface_id: "B007-R001", vertices: [[0,8,65],[10,14,65],[10,14,80],[0,8,80]] },
    // North-facing roof slope
    { surface_id: "B007-R002", vertices: [[10,14,65],[20,8,65],[20,8,80],[10,14,80]] },
    // South wall
    { surface_id: "B007-F001", vertices: [[0,0,65],[20,0,65],[20,8,65],[0,8,65]] },
    // North wall
    { surface_id: "B007-F002", vertices: [[0,0,80],[20,0,80],[20,8,80],[0,8,80]] },
    // East wall (rectangle below roofline)
    { surface_id: "B007-F003", vertices: [[20,0,65],[20,0,80],[20,8,80],[20,8,65]] },
    // East gable (triangle above roofline)
    { surface_id: "B007-F004", vertices: [[20,8,65],[20,8,80],[20,14,72.5]] },
    // West wall (rectangle below roofline)
    { surface_id: "B007-F005", vertices: [[0,0,65],[0,0,80],[0,8,80],[0,8,65]] },
    // West gable (triangle above roofline)
    { surface_id: "B007-F006", vertices: [[0,8,65],[0,8,80],[0,14,72.5]] },
  ],
};

// ─── Building B008: Butterfly / V-Shape Roof ───
// Two slopes dip inward to a central valley at x=35, y=6
// Eaves at x=25,y=12 and x=45,y=12
const B008: DemoBuilding = {
  building_id: "B008",
  name: "Butterfly Modernist",
  surfaces: [
    // Left roof slope (dips to valley)
    { surface_id: "B008-R001", vertices: [[25,12,65],[35,6,65],[35,6,80],[25,12,80]] },
    // Right roof slope (dips to valley)
    { surface_id: "B008-R002", vertices: [[35,6,65],[45,12,65],[45,12,80],[35,6,80]] },
    // South wall
    { surface_id: "B008-F001", vertices: [[25,0,65],[45,0,65],[45,12,65],[25,12,65]] },
    // North wall
    { surface_id: "B008-F002", vertices: [[25,0,80],[45,0,80],[45,12,80],[25,12,80]] },
    // East wall
    { surface_id: "B008-F003", vertices: [[45,0,65],[45,0,80],[45,12,80],[45,12,65]] },
    // West wall
    { surface_id: "B008-F004", vertices: [[25,0,65],[25,0,80],[25,12,80],[25,12,65]] },
  ],
};

// ─── Building B009: Barrel Vault / Curved Roof ───
// Half-cylinder running along z-axis, approximated with strips
// Center: x=65, radius=10, wall height=4, peak height=14
const B009: DemoBuilding = {
  building_id: "B009",
  name: "Vaulted Exhibition Hall",
  surfaces: [
    // Curved roof strips (8 segments approximating the arc)
    { surface_id: "B009-C001", vertices: [[55,4,65],[57.5,7.7,65],[57.5,7.7,80],[55,4,80]] },
    { surface_id: "B009-C002", vertices: [[57.5,7.7,65],[60,10.4,65],[60,10.4,80],[57.5,7.7,80]] },
    { surface_id: "B009-C003", vertices: [[60,10.4,65],[62.5,12.3,65],[62.5,12.3,80],[60,10.4,80]] },
    { surface_id: "B009-C004", vertices: [[62.5,12.3,65],[65,14,65],[65,14,80],[62.5,12.3,80]] },
    { surface_id: "B009-C005", vertices: [[65,14,65],[67.5,12.3,65],[67.5,12.3,80],[65,14,80]] },
    { surface_id: "B009-C006", vertices: [[67.5,12.3,65],[70,10.4,65],[70,10.4,80],[67.5,12.3,80]] },
    { surface_id: "B009-C007", vertices: [[70,10.4,65],[72.5,7.7,65],[72.5,7.7,80],[70,10.4,80]] },
    { surface_id: "B009-C008", vertices: [[72.5,7.7,65],[75,4,65],[75,4,80],[72.5,7.7,80]] },
    // South end cap (arc profile)
    { surface_id: "B009-E001", vertices: [[55,4,65],[57.5,7.7,65],[60,10.4,65],[62.5,12.3,65],[65,14,65],[67.5,12.3,65],[70,10.4,65],[72.5,7.7,65],[75,4,65]] },
    // North end cap (arc profile)
    { surface_id: "B009-E002", vertices: [[55,4,80],[57.5,7.7,80],[60,10.4,80],[62.5,12.3,80],[65,14,80],[67.5,12.3,80],[70,10.4,80],[72.5,7.7,80],[75,4,80]] },
    // South wall (rectangular below vault)
    { surface_id: "B009-F001", vertices: [[55,0,65],[75,0,65],[75,4,65],[55,4,65]] },
    // North wall
    { surface_id: "B009-F002", vertices: [[55,0,80],[75,0,80],[75,4,80],[55,4,80]] },
    // East wall
    { surface_id: "B009-F003", vertices: [[75,0,65],[75,0,80],[75,4,80],[75,4,65]] },
    // West wall
    { surface_id: "B009-F004", vertices: [[55,0,65],[55,0,80],[55,4,80],[55,4,65]] },
  ],
};

export const DEMO_BUILDINGS: DemoBuilding[] = [B001, B002, B003, B004, B005, B006, B007, B008, B009];

export function toBuildingInput(b: DemoBuilding): BuildingInput {
  return {
    building_id: b.building_id,
    name: b.name,
    surfaces: b.surfaces,
  };
}

export function getAllBuildingInputs(): BuildingInput[] {
  return DEMO_BUILDINGS.map(toBuildingInput);
}
