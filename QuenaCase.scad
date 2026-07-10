// AgnuQuena carrying case
// Self-contained OpenSCAD model inspired by common hinged enclosure patterns:
// rounded shell, mating rim, snap-fit hinge, snap clip, and fitted internal channels.

$fn = 64;

// Select "bottom", "lid", "hinge_coupon", "full_hinge_coupon", "latch", "latch_coupon", "assembly", "preview", or "none".
// Override from the CLI with:
// openscad -D 'part="bottom"' -o QuenaCaseBottom.stl QuenaCase.scad
part = is_undef(part) ? "preview" : part;

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
rim_clearance = 0.6;
lid_z_clearance = 0.3;

lid_closed_z = case_outer_h + lid_z_clearance;

hinge_outer_d = 6.2;
hinge_axle_d = 2.8;
hinge_socket_clearance = 0.35;
hinge_socket_d = hinge_axle_d + hinge_socket_clearance;
hinge_snap_slot_h = 2.25;
hinge_snap_lead_in_h = 1.1;
hinge_axis_y = -case_outer_w / 2;
hinge_axis_z = case_outer_h + hinge_outer_d / 2;
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
latch_clip_lead_in = 1.0;
latch_clip_grip_rib_w = 3.0;
latch_clip_bridge_y = front_pull_y + front_pull_depth / 2 + latch_clip_wall / 2 + latch_clip_clearance;
latch_clip_jaw_y = -(latch_clip_depth / 2 - latch_clip_wall / 2);
latch_clip_bottom_z = bottom_pull_z - latch_clip_wall - latch_clip_clearance;
latch_clip_top_jaw_z = lid_closed_z + lid_pull_z + front_pull_h + latch_clip_clearance;
latch_clip_top_offset = latch_clip_top_jaw_z - latch_clip_bottom_z;
latch_clip_total_h = latch_clip_top_offset + latch_clip_wall;

slot_xs = [
    0,
    -case_inner_l / 2 + end_clearance + profile_lengths[1] / 2,
    case_inner_l / 2 - end_clearance - profile_lengths[2] / 2
];
slot_ys = [-row_pitch / 2, row_pitch / 2, row_pitch / 2];
slot_rot_zs = [0, 0, 180];

retainer_overcenter = 0.75;
retainer_wall = 2.0;
retainer_end_margin = 8;
retainer_connector_margin = 4;

function slot_x(i) = slot_xs[i];
function slot_y(i) = slot_ys[i];
function slot_rot_z(i) = slot_rot_zs[i];
function profile_l(i) = profile_lengths[i];
function profile_d(i) = profile_max_ds[i];
function body_x0(i) = -profile_l(i) / 2;
function body_x1(i) = body_x0(i) + slot_lengths[i];
function connector_x1(i) = body_x1(i) + connector_extra_l;
function retainer_x0(i) = body_x0(i) + retainer_end_margin;
function retainer_x1(i) = slot_has_connector[i]
    ? body_x1(i) - connector_backset - retainer_connector_margin
    : body_x1(i) - retainer_end_margin;
function retainer_l(i) = max(0, retainer_x1(i) - retainer_x0(i));
function retainer_count(i) = retainer_l(i) > 160 ? 4 : (retainer_l(i) > 80 ? 3 : 2);

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
            rotate([0, 0, slot_rot_z(i)])
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

module curved_retainer_band(i, x_center, band_l) {
    channel_r = channel_d / 2;
    cradle_overlap = 2;
    band_h = channel_r + cradle_overlap + retainer_overcenter;

    difference() {
        translate([
            x_center,
            0,
            floor_thickness - cradle_overlap / 2 + band_h / 2
        ])
            cube([band_l, channel_d + retainer_wall * 2, band_h], center = true);
        translate([0, 0, slot_z])
            profiled_channel_cut(i, 2);
    }
}

module curved_retainers(i) {
    count = retainer_count(i);
    usable_l = retainer_l(i);
    band_l = min(24, max(12, usable_l / (count * 2)));

    if (usable_l > 8)
        for (n = [0 : count - 1])
            curved_retainer_band(
                i,
                retainer_x0(i) + usable_l * (n + 0.5) / count,
                band_l
            );
}

module bottom_fitted_channels() {
    for (i = [0 : 2])
        translate([slot_x(i), slot_y(i), 0]) {
            rotate([0, 0, slot_rot_z(i)]) {
                bottom_channel_cradle(i);
                curved_retainers(i);
            }
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

module hinge_barrel(x1, x2, local_z) {
    translate([0, hinge_axis_y, local_z])
        x_cylinder_between(x1, x2, hinge_outer_d);
}

module hinge_socket_slot(x1, x2, local_z) {
    translate([(x1 + x2) / 2, hinge_axis_y - hinge_outer_d / 2 - 0.5, local_z])
        cube([x2 - x1 + 0.2, hinge_outer_d + 1, hinge_snap_slot_h], center = true);
}

module hinge_socket_lead_ins(x1, x2, local_z) {
    translate([0, hinge_axis_y - hinge_outer_d / 2 + 0.4, local_z + hinge_snap_slot_h / 2 + hinge_snap_lead_in_h / 2])
        rotate([45, 0, 0])
            cube([x2 - x1 + 0.2, hinge_snap_lead_in_h * 3, hinge_snap_lead_in_h], center = true);
    translate([0, hinge_axis_y - hinge_outer_d / 2 + 0.4, local_z - hinge_snap_slot_h / 2 - hinge_snap_lead_in_h / 2])
        rotate([-45, 0, 0])
            cube([x2 - x1 + 0.2, hinge_snap_lead_in_h * 3, hinge_snap_lead_in_h], center = true);
}

module hinge_socket_bore(x1, x2, local_z) {
    translate([0, hinge_axis_y, local_z])
        x_cylinder_between(x1 - 0.1, x2 + 0.1, hinge_socket_d);
}

module hinge_support(x1, x2, local_z) {
    union() {
        hinge_barrel(x1, x2, local_z);
        hinge_tab(x1, x2, local_z);
    }
}

module hinge_snap_axle(x1, x2, local_z) {
    translate([0, hinge_axis_y, local_z])
        x_cylinder_between(x1, x2, hinge_axle_d);
}

module bottom_hinge_web(x1, x2, local_z) {
    web_h = local_z - case_outer_h + hinge_axle_d / 2 + 0.35;
    web_y = 3.6;

    translate([
        (x1 + x2) / 2,
        hinge_axis_y + web_y / 2,
        case_outer_h - 0.25 + web_h / 2
    ])
        cube([x2 - x1, web_y, web_h], center = true);
}

module bottom_hinge() {
    for (segment = hinge_bottom_knuckles)
        bottom_hinge_web(segment[0], segment[1], hinge_axis_z);
    hinge_snap_axle(-hinge_span / 2, hinge_span / 2, hinge_axis_z);
}

module lid_hinge() {
    local_axis_z = hinge_axis_z - lid_closed_z;

    for (segment = hinge_lid_knuckles)
        hinge_support(segment[0], segment[1], local_axis_z);
}

module lid_hinge_socket_cuts() {
    local_axis_z = hinge_axis_z - lid_closed_z;

    hinge_socket_bore(-hinge_span / 2, hinge_span / 2, local_axis_z);
    hinge_socket_slot(-hinge_span / 2, hinge_span / 2, local_axis_z);
    hinge_socket_lead_ins(-hinge_span / 2, hinge_span / 2, local_axis_z);
}

module lid_bottom_hinge_relief() {
    local_axis_z = hinge_axis_z - lid_closed_z;
    relief_y = 5.2;
    relief_z = hinge_outer_d + 4;

    for (segment = hinge_bottom_knuckles)
        translate([
            (segment[0] + segment[1]) / 2,
            hinge_axis_y + relief_y / 2 - 0.4,
            local_axis_z
        ])
            cube([segment[1] - segment[0] + 0.6, relief_y, relief_z], center = true);
}

module lid_hinge_relief() {
    relief_y = hinge_outer_d + 1;
    relief_z = rim_h + hinge_outer_d / 2;

    for (segment = hinge_lid_knuckles)
        translate([
            (segment[0] + segment[1]) / 2,
            hinge_axis_y + relief_y / 2,
            case_outer_h + relief_z / 2
        ])
            cube([segment[1] - segment[0] + 2, relief_y, relief_z], center = true);
}

module front_pull(local_z = bottom_pull_z) {
    translate([0, front_pull_y, local_z])
        rounded_box([front_pull_w, front_pull_depth, front_pull_h], 1.4);
}

module latch_entry_bevels() {
    for (z = [
        latch_clip_wall + latch_clip_lead_in / 2,
        latch_clip_top_offset - latch_clip_lead_in / 2
    ])
        translate([
            0,
            latch_clip_jaw_y - latch_clip_depth / 2 + latch_clip_lead_in / 2,
            z
        ])
            rotate([45, 0, 0])
                cube([
                    latch_clip_w + 0.4,
                    latch_clip_lead_in * 2.5,
                    latch_clip_lead_in
                ], center = true);
}

module latch_grip_ribs() {
    rib_z0 = latch_clip_wall + 1.0;
    rib_h = latch_clip_total_h - latch_clip_wall * 2 - 2.0;

    for (x = [-latch_clip_w / 2 + 10, 0, latch_clip_w / 2 - 10])
        translate([x, latch_clip_wall / 2 + latch_clip_r / 2, rib_z0])
            rounded_box([latch_clip_grip_rib_w, latch_clip_r, rib_h], latch_clip_r / 2);
}

module latch_clip_core() {
    difference() {
        union() {
            translate([0, latch_clip_jaw_y, 0])
                rounded_box([latch_clip_w, latch_clip_depth, latch_clip_wall], latch_clip_r);
            translate([0, latch_clip_jaw_y, latch_clip_top_offset])
                rounded_box([latch_clip_w, latch_clip_depth, latch_clip_wall], latch_clip_r);
            rounded_box([latch_clip_w, latch_clip_wall, latch_clip_total_h], latch_clip_r);
            latch_grip_ribs();
        }
        latch_entry_bevels();
    }
}

module latch_clip() {
    translate([0, latch_clip_bridge_y, latch_clip_bottom_z])
        latch_clip_core();
}

module bottom_rim() {
    translate([0, 0, case_outer_h])
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
            lid_hinge_relief();
        }
        bottom_fitted_channels();
    }
}

module bottom_assembly() {
    union() {
        bottom_case();
        bottom_hinge();
        front_pull(bottom_pull_z);
    }
}

module lid_case() {
    lid_h = max_channel_d / 2 + lid_roof_thickness + rim_h;

    difference() {
        rounded_box([case_outer_l, case_outer_w, lid_h], corner_r);
        translate([0, 0, -0.01])
            lid_rim_socket();
        translate([0, 0, -lid_closed_z])
            all_channel_cuts(4);
    }
}

module lid_assembly() {
    difference() {
        union() {
            lid_case();
            lid_hinge();
            front_pull(lid_pull_z);
        }
        lid_hinge_socket_cuts();
        lid_bottom_hinge_relief();
    }
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
            rotate([0, 0, slot_rot_z(i)])
                profiled_channel_cut(i);
}

module closed_assembly_case() {
    bottom_assembly();
    translate([0, 0, lid_closed_z])
        lid_assembly();
    latch_clip();
}

module hinge_coupon() {
    coupon_span = 46;
    coupon_base_l = coupon_span + 12;
    coupon_base_w = 18;
    coupon_base_h = 3;
    coupon_wall_t = 3;
    coupon_wall_h = hinge_outer_d + 5;
    coupon_axis_z = coupon_base_h + hinge_outer_d / 2 + 2;
    coupon_socket_l = 24;
    coupon_gap_y = 18;
    coupon_socket_y = coupon_base_w + coupon_gap_y;
    lead_in_h = 1.1;

    module coupon_label(label_text, y) {
        translate([-coupon_base_l / 2 + 4, y - coupon_base_w / 2 + 2.8, coupon_base_h + 0.05])
            linear_extrude(height = 0.35)
                text(label_text, size = 4, halign = "left", valign = "bottom");
    }

    module axle_coupon_half() {
        union() {
            translate([-coupon_base_l / 2, -coupon_base_w / 2, 0])
                cube([coupon_base_l, coupon_base_w, coupon_base_h]);
            translate([-coupon_base_l / 2, -coupon_base_w / 2, coupon_base_h])
                cube([coupon_base_l, coupon_wall_t, coupon_wall_h]);
            translate([0, -coupon_base_w / 2 + coupon_wall_t, coupon_axis_z])
                x_cylinder_between(-coupon_span / 2, coupon_span / 2, hinge_axle_d);
            translate([0, -coupon_base_w / 2 + coupon_wall_t / 2, (coupon_base_h + coupon_axis_z) / 2])
                cube([coupon_span, coupon_wall_t, coupon_axis_z - coupon_base_h], center = true);
            coupon_label("AXLE", 0);
        }
    }

    module socket_coupon_half() {
        translate([0, coupon_socket_y, 0])
        union() {
            translate([-coupon_base_l / 2, -coupon_base_w / 2, 0])
                cube([coupon_base_l, coupon_base_w, coupon_base_h]);
            difference() {
                union() {
                    translate([0, -coupon_base_w / 2 + coupon_wall_t / 2, coupon_base_h + coupon_wall_h / 2])
                        cube([coupon_socket_l, coupon_wall_t, coupon_wall_h], center = true);
                    translate([0, -coupon_base_w / 2 + coupon_wall_t, coupon_axis_z])
                        x_cylinder_between(-coupon_socket_l / 2, coupon_socket_l / 2, hinge_outer_d);
                    translate([0, -coupon_base_w / 2 + coupon_wall_t + hinge_outer_d / 4, coupon_axis_z - hinge_outer_d / 4])
                        cube([coupon_socket_l, hinge_outer_d / 2, hinge_outer_d / 2], center = true);
                }
                translate([0, -coupon_base_w / 2 + coupon_wall_t, coupon_axis_z])
                    x_cylinder_between(-coupon_socket_l / 2 - 0.1, coupon_socket_l / 2 + 0.1, hinge_socket_d);
                translate([0, -coupon_base_w / 2 - hinge_outer_d / 2, coupon_axis_z])
                    cube([coupon_socket_l + 0.2, hinge_outer_d + 1, hinge_snap_slot_h], center = true);
                translate([0, -coupon_base_w / 2 + 0.4, coupon_axis_z + hinge_snap_slot_h / 2 + lead_in_h / 2])
                    rotate([45, 0, 0])
                        cube([coupon_socket_l + 0.2, lead_in_h * 3, lead_in_h], center = true);
                translate([0, -coupon_base_w / 2 + 0.4, coupon_axis_z - hinge_snap_slot_h / 2 - lead_in_h / 2])
                    rotate([-45, 0, 0])
                        cube([coupon_socket_l + 0.2, lead_in_h * 3, lead_in_h], center = true);
            }
            coupon_label("SOCKET", 0);
        }
    }

    axle_coupon_half();
    socket_coupon_half();
}

module full_hinge_coupon() {
    coupon_base_h = 3;
    coupon_base_w = 18;
    coupon_gap_y = 20;
    coupon_bottom_y = 0;
    coupon_socket_y = coupon_base_w + coupon_gap_y;
    coupon_axis_z = coupon_base_h + hinge_outer_d / 2 + 2;
    coupon_span = hinge_span;

    module full_hinge_base(y, label_text) {
        translate([-coupon_span / 2 - 6, y - coupon_base_w / 2, 0])
            cube([coupon_span + 12, coupon_base_w, coupon_base_h]);
        translate([-coupon_span / 2 - 2, y - coupon_base_w / 2 + 2.8, coupon_base_h + 0.05])
            linear_extrude(height = 0.35)
                text(label_text, size = 4, halign = "left", valign = "bottom");
    }

    module full_axle_half() {
        translate([0, coupon_bottom_y, 0])
        union() {
            full_hinge_base(0, "CASE AXLE");
            for (segment = hinge_bottom_knuckles)
                translate([(segment[0] + segment[1]) / 2, -coupon_base_w / 2 + 3.6 / 2, (coupon_base_h + coupon_axis_z) / 2])
                    cube([segment[1] - segment[0], 3.6, coupon_axis_z - coupon_base_h], center = true);
            translate([0, -coupon_base_w / 2 + 3.6, coupon_axis_z])
                x_cylinder_between(-coupon_span / 2, coupon_span / 2, hinge_axle_d);
        }
    }

    module full_socket_half() {
        translate([0, coupon_socket_y, 0])
        union() {
            full_hinge_base(0, "LID SOCKET");
            difference() {
                union() {
                    for (segment = hinge_lid_knuckles) {
                        translate([(segment[0] + segment[1]) / 2, -coupon_base_w / 2 + hinge_tab_t / 2, coupon_base_h + hinge_outer_d / 2 + 2])
                            cube([
                                segment[1] - segment[0],
                                hinge_tab_t,
                                hinge_outer_d + 4
                            ], center = true);
                        translate([0, -coupon_base_w / 2 + hinge_tab_t, coupon_axis_z])
                            x_cylinder_between(segment[0], segment[1], hinge_outer_d);
                    }
                }
                translate([0, -coupon_base_w / 2 + hinge_tab_t, coupon_axis_z])
                    x_cylinder_between(-coupon_span / 2 - 0.1, coupon_span / 2 + 0.1, hinge_socket_d);
                translate([0, -coupon_base_w / 2 - hinge_outer_d / 2, coupon_axis_z])
                    cube([coupon_span + 0.2, hinge_outer_d + 1, hinge_snap_slot_h], center = true);
                translate([0, -coupon_base_w / 2 - hinge_outer_d / 2 + 0.4, coupon_axis_z + hinge_snap_slot_h / 2 + hinge_snap_lead_in_h / 2])
                    rotate([45, 0, 0])
                        cube([coupon_span + 0.2, hinge_snap_lead_in_h * 3, hinge_snap_lead_in_h], center = true);
                translate([0, -coupon_base_w / 2 - hinge_outer_d / 2 + 0.4, coupon_axis_z - hinge_snap_slot_h / 2 - hinge_snap_lead_in_h / 2])
                    rotate([-45, 0, 0])
                        cube([coupon_span + 0.2, hinge_snap_lead_in_h * 3, hinge_snap_lead_in_h], center = true);
            }
        }
    }

    full_axle_half();
    full_socket_half();
}

module latch_coupon() {
    coupon_base_l = latch_clip_w + 18;
    coupon_base_w = 18;
    coupon_base_h = 3;
    pull_y = front_pull_y - latch_clip_bridge_y;
    bottom_pull_local_z = latch_clip_wall + latch_clip_clearance;
    lid_pull_local_z = latch_clip_top_offset - front_pull_h - latch_clip_clearance;

    module coupon_pull(local_z) {
        translate([0, pull_y, local_z])
            rounded_box([front_pull_w, front_pull_depth, front_pull_h], 1.4);
    }

    module pull_backer(local_z) {
        translate([-coupon_base_l / 2, pull_y - front_pull_depth / 2 - 2.8, local_z - coupon_base_h])
            cube([coupon_base_l, 6, coupon_base_h]);
    }

    union() {
        pull_backer(bottom_pull_local_z);
        coupon_pull(bottom_pull_local_z);
        pull_backer(lid_pull_local_z);
        coupon_pull(lid_pull_local_z);
        latch_clip_core();
        translate([-coupon_base_l / 2 + 3, pull_y - front_pull_depth / 2 - 2.2, 0.05])
            linear_extrude(height = 0.35)
                text("LATCH FIT", size = 4, halign = "left", valign = "bottom");
    }
}

if (part == "none") {
} else if (part == "bottom") {
    bottom_assembly();
} else if (part == "lid") {
    lid_assembly();
} else if (part == "hinge_coupon") {
    hinge_coupon();
} else if (part == "full_hinge_coupon") {
    full_hinge_coupon();
} else if (part == "latch") {
    latch_clip_core();
} else if (part == "latch_coupon") {
    latch_coupon();
} else if (part == "assembly" || part == "print_in_place") {
    closed_assembly_case();
} else {
    color("steelblue") bottom_assembly();
    labels();
    translate([0, 0, lid_closed_z])
        color("lightgray") lid_assembly();
    color("darkslategray") latch_clip();
    preview_ghosts();
}
