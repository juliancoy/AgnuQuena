// AgnuQuena carrying case
// Self-contained OpenSCAD model inspired by common hinged enclosure patterns:
// rounded shell, mating rim, removable hinge pin, snap clip, and fitted internal channels.

$fn = 64;

// Select "bottom", "lid", "pin", "latch", "assembly", or "preview". Override from the CLI with:
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
ov = 7;
angled_transition_z = 3;
insert_z_tolerance = 0.4;

// Case fit and print parameters.
part_clearance = 0.6;
connector_d = od + shell_width * 2;
channel_d = od + part_clearance * 2;
connector_channel_d = connector_d + part_clearance * 2;
max_channel_d = connector_channel_d;
end_clearance = 7;
wall = 3;
floor_thickness = 2.8;
lid_roof_thickness = 2.8;
corner_r = 7;

row_gap = 8;
row_pitch = max_channel_d + row_gap;
inline_gap = 6;
connector_backset = angled_transition_z + 2;
connector_expand_start = 2;
connector_expand_end = ov - insert_z_tolerance - 2;
connector_extra_l = connector_expand_end + angled_transition_z;
slot_lengths = [tube_part_1_length, tube_part_2_length, mouthpiece_total_length];
slot_names = ["TUBE 1", "TUBE 2", "MOUTH"];
slot_has_connector = [true, false, true];
profile_lengths = [
    tube_part_1_length + connector_extra_l,
    tube_part_2_length,
    mouthpiece_total_length + connector_extra_l
];
profile_max_ds = [connector_channel_d, channel_d, connector_channel_d];
short_row_length = profile_lengths[1] + inline_gap + profile_lengths[2];
longest_slot = max(profile_lengths[0], short_row_length) + end_clearance * 2;
case_inner_l = longest_slot;
case_inner_w = row_pitch + max_channel_d;
case_outer_l = case_inner_l + wall * 2;
case_outer_w = case_inner_w + wall * 2;
case_outer_h = max_channel_d / 2 + floor_thickness + 4;
slot_z = floor_thickness + max_channel_d / 2;

rim_h = 2.4;
rim_wall = 1.4;
rim_clearance = 0.35;

lid_closed_z = case_outer_h - rim_h;

hinge_outer_d = 6.2;
hinge_pin_d = 1.75;
hinge_pin_clearance = 0.35;
hinge_hole_d = hinge_pin_d + hinge_pin_clearance;
hinge_axis_y = -case_outer_w / 2 - hinge_outer_d / 2 - 1.2;
hinge_axis_z = case_outer_h - rim_h / 2;
hinge_span = case_outer_l - 30;
hinge_gap = 1.0;
hinge_bottom_knuckles = [
    [-hinge_span / 2, -hinge_span / 6 - hinge_gap / 2],
    [ hinge_span / 6 + hinge_gap / 2,  hinge_span / 2]
];
hinge_lid_knuckles = [[-hinge_span / 6 + hinge_gap / 2, hinge_span / 6 - hinge_gap / 2]];
hinge_tab_t = 2.2;

front_pull_w = 48;
front_pull_depth = 3.6;
front_pull_h = 2.2;
front_pull_y = case_outer_w / 2 + front_pull_depth / 2 - 0.4;
bottom_pull_z = lid_closed_z - front_pull_h - 0.25;
lid_pull_z = front_pull_h;

latch_clip_w = 56;
latch_clip_depth = 7.5;
latch_clip_wall = 2.0;
latch_clip_r = 0.8;
latch_clip_clearance = 0.35;
latch_clip_bridge_y = front_pull_y + front_pull_depth / 2 + latch_clip_wall / 2 + latch_clip_clearance;
latch_clip_jaw_y = -(latch_clip_depth / 2 - latch_clip_wall / 2);
latch_clip_bottom_z = bottom_pull_z - latch_clip_wall - latch_clip_clearance;
latch_clip_top_jaw_z = lid_closed_z + lid_pull_z + front_pull_h + latch_clip_clearance;
latch_clip_top_offset = latch_clip_top_jaw_z - latch_clip_bottom_z;
latch_clip_total_h = latch_clip_top_offset + latch_clip_wall;

slot_xs = [
    0,
    -short_row_length / 2 + profile_lengths[1] / 2,
    short_row_length / 2 - profile_lengths[2] / 2
];
slot_ys = [-row_pitch / 2, row_pitch / 2, row_pitch / 2];

snap_d = 1.6;
snap_overlap = 0.8;
snap_z = slot_z + 2.4;
snap_positions = [-0.34, 0.34];

function slot_x(i) = slot_xs[i];
function slot_y(i) = slot_ys[i];
function profile_l(i) = profile_lengths[i];
function profile_d(i) = profile_max_ds[i];
function body_x0(i) = -profile_l(i) / 2;
function body_x1(i) = body_x0(i) + slot_lengths[i];
function connector_x1(i) = body_x1(i) + connector_extra_l;

module rounded_box(size, r) {
    hull() {
        for (x = [-size[0] / 2 + r, size[0] / 2 - r])
        for (y = [-size[1] / 2 + r, size[1] / 2 - r])
            translate([x, y, 0])
                cylinder(h = size[2], r = r);
    }
}

module profiled_segment(x1, x2, d1, d2) {
    translate([(x1 + x2) / 2, 0, 0])
        rotate([0, 90, 0])
            cylinder(h = x2 - x1, d1 = d1, d2 = d2, center = true);
}

module profiled_channel_cut(i, extra_depth = 0) {
    x0 = body_x0(i);
    x1 = body_x1(i);
    x2 = connector_x1(i);

    union() {
        profiled_segment(x0 - end_clearance, x0, channel_d, channel_d);

        if (slot_has_connector[i]) {
            profiled_segment(x0, x1 - connector_backset, channel_d, channel_d);
            profiled_segment(
                x1 - connector_backset,
                x1 - connector_expand_start,
                channel_d,
                connector_channel_d
            );
            profiled_segment(
                x1 - connector_expand_start,
                x1 + connector_expand_end,
                connector_channel_d,
                connector_channel_d
            );
            profiled_segment(
                x1 + connector_expand_end,
                x2,
                connector_channel_d,
                channel_d
            );
            profiled_segment(x2, x2 + end_clearance, channel_d, channel_d);
        } else {
            profiled_segment(x0, x1, channel_d, channel_d);
            profiled_segment(x1, x1 + end_clearance, channel_d, channel_d);
        }

        // Flat relief above the half-round keeps the part easy to remove.
        translate([0, 0, profile_d(i) / 4])
            cube([
                profile_l(i) + end_clearance * 2,
                profile_d(i),
                profile_d(i) / 2 + extra_depth
            ], center = true);
    }
}

module all_channel_cuts(extra_depth = 0) {
    for (i = [0 : 2])
        translate([slot_x(i), slot_y(i), slot_z])
            profiled_channel_cut(i, extra_depth);
}

module bottom_channel_cradle(i) {
    cradle_l = profile_l(i) + end_clearance * 2;
    channel_r = profile_d(i) / 2;
    cradle_overlap = 2;

    difference() {
        translate([0, 0, floor_thickness - cradle_overlap / 2 + channel_r / 2])
            cube([cradle_l, profile_d(i) + 2, channel_r + cradle_overlap], center = true);
        translate([0, 0, slot_z])
            profiled_channel_cut(i, 2);
    }
}

module snap_beads(i) {
    bead_l = min(18, max(8, slot_lengths[i] * 0.28));
    channel_r = channel_d / 2;

    for (x_factor = snap_positions)
    for (side = [-1, 1])
        union() {
            translate([
                body_x0(i) + slot_lengths[i] * (0.5 + x_factor),
                side * (channel_r - snap_overlap),
                snap_z
            ])
                rotate([0, 90, 0])
                    cylinder(h = bead_l, d = snap_d, center = true);
            translate([
                body_x0(i) + slot_lengths[i] * (0.5 + x_factor),
                side * (channel_r - snap_overlap),
                (floor_thickness + snap_z) / 2
            ])
                cube([bead_l, snap_d, snap_z - floor_thickness], center = true);
        }
}

module bottom_fitted_channels() {
    for (i = [0 : 2])
        translate([slot_x(i), slot_y(i), 0]) {
            bottom_channel_cradle(i);
            snap_beads(i);
        }
}

module x_cylinder_between(x1, x2, d) {
    translate([(x1 + x2) / 2, 0, 0])
        rotate([0, 90, 0])
            cylinder(h = x2 - x1, d = d, center = true);
}

module hinge_tab(x1, x2, local_z) {
    attach_y = -case_outer_w / 2 + 0.4;

    translate([
        (x1 + x2) / 2,
        (hinge_axis_y + attach_y) / 2,
        local_z
    ])
        cube([x2 - x1, attach_y - hinge_axis_y, hinge_tab_t], center = true);
}

module hinge_barrel(x1, x2, local_z, with_pin_hole = false) {
    translate([0, hinge_axis_y, local_z])
    difference() {
        x_cylinder_between(x1, x2, hinge_outer_d);
        if (with_pin_hole)
            x_cylinder_between(x1 - 0.1, x2 + 0.1, hinge_hole_d);
    }
}

module bottom_hinge() {
    for (segment = hinge_bottom_knuckles) {
        hinge_barrel(segment[0], segment[1], hinge_axis_z, true);
        hinge_tab(segment[0], segment[1], hinge_axis_z);
    }
}

module lid_hinge() {
    local_axis_z = hinge_axis_z - lid_closed_z;

    for (segment = hinge_lid_knuckles) {
        hinge_barrel(segment[0], segment[1], local_axis_z, true);
        hinge_tab(segment[0], segment[1], local_axis_z);
    }
}

module front_pull(local_z = bottom_pull_z) {
    translate([0, front_pull_y, local_z])
        rounded_box([front_pull_w, front_pull_depth, front_pull_h], 1.4);
}

module hinge_pin() {
    translate([0, hinge_axis_y, hinge_axis_z])
        x_cylinder_between(-hinge_span / 2 - 4, hinge_span / 2 + 4, hinge_pin_d);
}

module printable_hinge_pin() {
    translate([0, 0, hinge_pin_d / 2])
        x_cylinder_between(-hinge_span / 2 - 4, hinge_span / 2 + 4, hinge_pin_d);
}

module latch_clip_core() {
    union() {
        translate([0, latch_clip_jaw_y, 0])
            rounded_box([latch_clip_w, latch_clip_depth, latch_clip_wall], latch_clip_r);
        translate([0, latch_clip_jaw_y, latch_clip_top_offset])
            rounded_box([latch_clip_w, latch_clip_depth, latch_clip_wall], latch_clip_r);
        rounded_box([latch_clip_w, latch_clip_wall, latch_clip_total_h], latch_clip_r);
    }
}

module latch_clip() {
    translate([0, latch_clip_bridge_y, latch_clip_bottom_z])
        latch_clip_core();
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
    union() {
        difference() {
            union() {
                rounded_box([case_outer_l, case_outer_w, case_outer_h], corner_r);
                bottom_rim();
            }
            translate([0, 0, floor_thickness])
                rounded_box([case_inner_l, case_inner_w, case_outer_h + 2], max(corner_r - wall, 1));
            all_channel_cuts(4);
        }
        bottom_fitted_channels();
    }
}

module bottom_assembly() {
    bottom_case();
    bottom_hinge();
    front_pull(bottom_pull_z);
}

module lid_case() {
    lid_h = max_channel_d / 2 + lid_roof_thickness + rim_h;

    difference() {
        rounded_box([case_outer_l, case_outer_w, lid_h], corner_r);
        translate([0, 0, -0.01])
            lid_rim_socket();
        translate([0, 0, -floor_thickness - max_channel_d / 2 + rim_h])
            all_channel_cuts(4);
    }
}

module lid_assembly() {
    lid_case();
    lid_hinge();
    front_pull(lid_pull_z);
}

module labels() {
    for (i = [0 : 2])
        translate([slot_x(i) - profile_l(i) / 2 + 3, slot_y(i), case_outer_h + 0.25])
            linear_extrude(height = 0.6)
                text(slot_names[i], size = 5, halign = "left", valign = "center");
}

module preview_ghosts() {
    color([0.1, 0.1, 0.1, 0.28])
    for (i = [0 : 2])
        translate([slot_x(i), slot_y(i), slot_z])
            profiled_channel_cut(i);
}

module closed_assembly_case(show_pin = true) {
    bottom_assembly();
    translate([0, 0, lid_closed_z])
        lid_assembly();
    if (show_pin)
        hinge_pin();
    latch_clip();
}

if (part == "bottom") {
    bottom_assembly();
} else if (part == "lid") {
    lid_assembly();
} else if (part == "pin") {
    printable_hinge_pin();
} else if (part == "latch") {
    latch_clip_core();
} else if (part == "assembly" || part == "print_in_place") {
    closed_assembly_case();
} else {
    color("steelblue") bottom_assembly();
    labels();
    translate([0, 0, lid_closed_z])
        color("lightgray") lid_assembly();
    color("silver") hinge_pin();
    color("darkslategray") latch_clip();
    preview_ghosts();
}
