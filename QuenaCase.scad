// AgnuQuena carrying case
// Self-contained OpenSCAD model inspired by common hinged enclosure patterns:
// rounded shell, mating rim, magnet pockets, and fitted internal channels.

$fn = 64;

// Select "bottom", "lid", or "preview". Override from the CLI with:
// openscad -D 'part="bottom"' -o QuenaCaseBottom.stl QuenaCase.scad
part = "preview";

// Quena dimensions copied from Quena.scad so the case can be rendered alone.
shell_width = 1.5;
id = 17.5;
od = id + shell_width * 2;
mouthpiece_total_length = 30;
pitch_raise_cents = 12;
length_tuning_scale = pow(2, -pitch_raise_cents / 1200);
function tuned_length(length) = length * length_tuning_scale;
acoustic_length = tuned_length(396);
unacoustic_length = 6;
mouthpiece_active_length = mouthpiece_total_length - unacoustic_length;
non_mouthpiece_acoustic_length = acoustic_length - mouthpiece_active_length;
tube_part_1_length = 230;
tube_part_2_length = non_mouthpiece_acoustic_length - tube_part_1_length;

// Case fit and print parameters.
part_clearance = 2.25;
channel_d = od + part_clearance * 2;
end_clearance = 7;
wall = 3;
floor_thickness = 2.8;
lid_roof_thickness = 2.8;
corner_r = 7;

slot_gap = 8;
slot_pitch = channel_d + slot_gap;
longest_slot = tube_part_1_length + end_clearance * 2;
case_inner_l = longest_slot;
case_inner_w = slot_pitch * 2 + channel_d;
case_outer_l = case_inner_l + wall * 2;
case_outer_w = case_inner_w + wall * 2;
case_outer_h = channel_d / 2 + floor_thickness + 4;
slot_z = floor_thickness + channel_d / 2;

rim_h = 2.4;
rim_wall = 1.4;
rim_clearance = 0.35;

magnet_d = 6.2;
magnet_h = 2.2;
magnet_margin_l = 22;
magnet_margin_w = 12;

slot_lengths = [tube_part_1_length, tube_part_2_length, mouthpiece_total_length];
slot_names = ["TUBE 1", "TUBE 2", "MOUTH"];

function slot_y(i) = -slot_pitch + i * slot_pitch;

module rounded_box(size, r) {
    hull() {
        for (x = [-size[0] / 2 + r, size[0] / 2 - r])
        for (y = [-size[1] / 2 + r, size[1] / 2 - r])
            translate([x, y, 0])
                cylinder(h = size[2], r = r);
    }
}

module channel_cut(length, extra_depth = 0) {
    rotate([0, 90, 0])
        cylinder(h = length + end_clearance * 2, d = channel_d, center = true);

    // Flat relief above the half-round keeps the part easy to remove.
    translate([0, 0, channel_d / 4])
        cube([length + end_clearance * 2, channel_d, channel_d / 2 + extra_depth], center = true);
}

module all_channel_cuts(extra_depth = 0) {
    for (i = [0 : 2])
        translate([0, slot_y(i), slot_z])
            channel_cut(slot_lengths[i], extra_depth);
}

module magnet_pockets(z, pocket_h) {
    for (x = [-case_outer_l / 2 + magnet_margin_l, case_outer_l / 2 - magnet_margin_l])
    for (y = [-case_outer_w / 2 + magnet_margin_w, case_outer_w / 2 - magnet_margin_w])
        translate([x, y, z])
            cylinder(h = pocket_h, d = magnet_d);
}

module bottom_rim() {
    translate([0, 0, case_outer_h - rim_h])
    difference() {
        rounded_box([case_outer_l - wall * 1.4, case_outer_w - wall * 1.4, rim_h], max(corner_r - wall, 1));
        translate([0, 0, -0.01])
            rounded_box([
                case_outer_l - wall * 1.4 - rim_wall * 2,
                case_outer_w - wall * 1.4 - rim_wall * 2,
                rim_h + 0.02
            ], max(corner_r - wall - rim_wall, 1));
    }
}

module lid_rim_socket() {
    translate([0, 0, -0.01])
    difference() {
        rounded_box([
            case_outer_l - wall * 1.4 + rim_clearance * 2,
            case_outer_w - wall * 1.4 + rim_clearance * 2,
            rim_h + 0.02
        ], max(corner_r - wall + rim_clearance, 1));
        translate([0, 0, -0.01])
            rounded_box([
                case_outer_l - wall * 1.4 - rim_wall * 2 - rim_clearance * 2,
                case_outer_w - wall * 1.4 - rim_wall * 2 - rim_clearance * 2,
                rim_h + 0.04
            ], max(corner_r - wall - rim_wall - rim_clearance, 1));
    }
}

module bottom_case() {
    difference() {
        union() {
            rounded_box([case_outer_l, case_outer_w, case_outer_h], corner_r);
            bottom_rim();
        }
        translate([0, 0, floor_thickness])
            rounded_box([case_inner_l, case_inner_w, case_outer_h + 2], max(corner_r - wall, 1));
        all_channel_cuts(4);
        magnet_pockets(case_outer_h - magnet_h, magnet_h + 0.02);
    }
}

module lid_case() {
    lid_h = channel_d / 2 + lid_roof_thickness + rim_h;

    difference() {
        rounded_box([case_outer_l, case_outer_w, lid_h], corner_r);
        translate([0, 0, -0.01])
            lid_rim_socket();
        translate([0, 0, -floor_thickness - channel_d / 2 + rim_h])
            all_channel_cuts(4);
        magnet_pockets(0.35, magnet_h + 0.02);
    }
}

module labels() {
    for (i = [0 : 2])
        translate([-case_outer_l / 2 + 18, slot_y(i), case_outer_h + 0.25])
            linear_extrude(height = 0.6)
                text(slot_names[i], size = 5, halign = "left", valign = "center");
}

module preview_ghosts() {
    color([0.1, 0.1, 0.1, 0.28])
    for (i = [0 : 2])
        translate([0, slot_y(i), slot_z])
            rotate([0, 90, 0])
                cylinder(h = slot_lengths[i], d = od, center = true);
}

if (part == "bottom") {
    bottom_case();
} else if (part == "lid") {
    lid_case();
} else {
    color("steelblue") bottom_case();
    labels();
    translate([0, case_outer_w + 10, 0])
        color("lightgray") lid_case();
    preview_ghosts();
}
