// AgnuQuena carrying case
// Self-contained OpenSCAD model inspired by common hinged enclosure patterns:
// rounded shell, mating rim, snap-fit hinge, snap clip, and fitted internal channels.

$fn = 64;

// Select "bottom", "lid", "bottom_p1s", "lid_p1s", "hinge_coupon",
// "full_hinge_coupon", "latch", "latch_coupon", "assembly", "preview", or "none".
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
// Close, printable fit around each part.  These are diametral/radial clearances;
// the separate axial clearance below controls end play.
part_clearance = 0.3;
connector_d = od + shell_width * 2;
channel_d = od + part_clearance * 2;
connector_channel_d = connector_d + part_clearance * 2;
max_channel_d = connector_channel_d;
axial_clearance = 0.6;
end_clearance = axial_clearance / 2;
// Keep the round cutter slightly proud of the nominal pocket ends.  This
// removes a coplanar cut face that can leave the cylindrical bore visibly
// stopping short of the terminal wall after tessellation/export.
bore_end_overlap = 0.08;
wall = 3;
floor_thickness = 2.8;
lid_roof_thickness = 2.8;
corner_r = 7;

// Compact lands retain enough material between channels while keeping the
// diagonal P1S export inside a conservative 220 x 220 mm usable square.
row_gap = 2.5;
row_pitch = max_channel_d + row_gap;
short_row_min_gap = 18;
channel_edge_land = 2.5;
// The single interior bed rises just past the tube equator.  It replaces the
// former deck, separate cradle blocks, and cantilever retention features.
equator_pass = 0.8;
channel_deck_h = 12.85; // max_channel_d / 2 + equator_pass
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
// Each recess has only the specified total axial play, shared between its ends.
profile_cut_spans = [
    profile_lengths[0] + axial_clearance,
    profile_lengths[1] + axial_clearance,
    profile_lengths[2] + axial_clearance
];
profile_cut_center_offsets = [0, 0, 0];
short_row_min_length = profile_cut_spans[1] + profile_cut_spans[2]
    + short_row_min_gap * 3;
case_inner_l = max(
    profile_cut_spans[0] + channel_edge_land * 2,
    short_row_min_length
);
case_inner_w = row_pitch + max_channel_d + channel_edge_land * 2;
case_outer_l = case_inner_l + wall * 2;
case_outer_w = case_inner_w + wall * 2;
case_outer_h = floor_thickness + channel_deck_h;
slot_z = floor_thickness + max_channel_d / 2;

rim_h = 2.4;
rim_wall = 1.4;
rim_clearance = 0.6;
lid_z_clearance = 0.3;

lid_closed_z = case_outer_h + lid_z_clearance;

hinge_outer_d = 6.8;
hinge_axle_d = 3.2;
hinge_socket_clearance = 0.35;
hinge_socket_d = hinge_axle_d + hinge_socket_clearance;
hinge_stator_closed = 1;
hinge_nub_l = 3.0;
hinge_pin_tip_l = 0.8;
hinge_pin_tip_r = 0.4;
hinge_socket_depth = 4.2;
hinge_install_flex_span = 80;
hinge_backer_extension = 1.2;
hinge_nub_support_y = 0.9;
hinge_nub_support_gap = 0.2;
hinge_nub_support_base_overlap = 0.15;
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
latch_nub_d = 3.0;
latch_nub_l = 2.6;
latch_nub_tip_l = 0.7;
latch_nub_tip_r = 0.35;
latch_socket_clearance = 0.4;
latch_socket_d = latch_nub_d + latch_socket_clearance;
latch_socket_depth = 3.8;
latch_knuckle_outer_d = 6.6;
latch_knuckle_gap = 1.6;
latch_install_flex_span = latch_clip_w;
latch_carrier_t = 1.6;
latch_carrier_h = 5.6;
latch_axis_z = latch_clip_bottom_z + latch_clip_total_h / 2;
latch_mount_x = latch_clip_w / 2 + latch_knuckle_gap;

// Integral radial snap latch. Two lid axles press into open C-knuckles on the
// bottom; the knuckle lips, not a long lid carrier, provide the compliance.
latch_snap_nub_d = 3.2;
latch_snap_socket_clearance = 0.30;
latch_snap_socket_d = latch_snap_nub_d + latch_snap_socket_clearance;
latch_snap_outer_d = 7.0;
latch_snap_throat = 2.7;
latch_snap_knuckle_w = 8.0;
latch_snap_lip_t = 1.4;
latch_snap_lip_l = 7.0;
latch_snap_lead = 1.2;
latch_snap_pair_x = 19;
latch_snap_axis_y = case_outer_w / 2 + 6.5;
latch_snap_axis_z = lid_closed_z + 2.0;

// Compact harmonica-case style ball snaps.
latch_ball_d = 3.4;
latch_ball_neck_d = 2.6;
latch_cup_bore_d = 3.15;
latch_cup_cavity_d = 3.75;
latch_cup_outer_d = 7.0;
latch_cup_h = 5.2;
latch_cup_slot_w = 1.2;
latch_cup_lip_t = 1.4;
latch_cup_flex_l = 5.2;
latch_pair_x = 19;
latch_center_y = case_outer_w / 2 + 4.5;
latch_center_z = lid_closed_z + 1.0;

// Final simple harmonica-case latch: one lid tongue, one shallow nub, and one
// shallow recess in the bottom front wall.
latch_tongue_w = 16.0;
latch_tongue_t = 1.6;
latch_tongue_flex_l = 11.0;
latch_tongue_y = case_outer_w / 2 - latch_tongue_t / 2;
latch_nub_r = 1.2;
latch_nub_protrusion = 1.00;
latch_indent_depth = 0.65;
latch_release_deflection = latch_nub_protrusion - latch_indent_depth;
latch_nub_z = case_outer_h - 1.35;
latch_point_xs = [-72, 72];
latch_point_count = 2;
latch_tongue_tip_w = 13.5;
latch_tongue_root_w = 22.0;
latch_tongue_root_blend_h = 2.4;
thumb_grip_w = 30;
thumb_grip_rib_h = 0.75;
thumb_grip_rib_depth = 0.45;
thumb_grip_rib_count = 5;
thumb_grip_z0 = 0.8;
thumb_grip_pitch = 1.55;

module smooth_latch_tongue(xc, local_y, bottom_z) {
    slice_h = 1.4;
    hull() {
        translate([xc, local_y, bottom_z])
            rounded_box([
                latch_tongue_tip_w,
                latch_tongue_t,
                slice_h
            ], 0.7);
        translate([xc, local_y,
            bottom_z + latch_tongue_flex_l - slice_h])
            rounded_box([
                latch_tongue_root_w,
                latch_tongue_t,
                slice_h
            ], 0.7);
    }
    // A shallow, wider shoulder overlaps the case wall and removes the hard
    // visual/mechanical corner at the tongue root.
    hull() {
        translate([xc, local_y,
            bottom_z + latch_tongue_flex_l - latch_tongue_root_blend_h])
            rounded_box([
                latch_tongue_root_w,
                latch_tongue_t,
                latch_tongue_root_blend_h
            ], 0.8);
        translate([xc, local_y - 0.35,
            bottom_z + latch_tongue_flex_l - 0.5])
            rounded_box([
                latch_tongue_root_w + 4,
                latch_tongue_t + 0.7,
                1.8
            ], 0.9);
    }
}

module lid_thumb_grip() {
    // Five low rounded ribs centered between the two latches. Their shallow
    // profile is printable without support but provides a clear tactile pull
    // target for a thumb or fingertip.
    for (i = [0 : thumb_grip_rib_count - 1])
        translate([
            0,
            case_outer_w / 2 + thumb_grip_rib_depth / 2 - 0.08,
            thumb_grip_z0 + i * thumb_grip_pitch
        ]) rounded_box([
            thumb_grip_w - i * 1.2,
            thumb_grip_rib_depth,
            thumb_grip_rib_h
        ], thumb_grip_rib_h / 2);
}

short_row_gap = (
    case_inner_l - profile_cut_spans[1] - profile_cut_spans[2]
) / 3;
short_tube_cut_center = -case_inner_l / 2
    + short_row_gap
    + profile_cut_spans[1] / 2;
mouth_cut_center = case_inner_l / 2
    - short_row_gap
    - profile_cut_spans[2] / 2;
slot_xs = [
    // Keep the longest tube body centered axially.  Its connector and free-end
    // clearances remain intentionally asymmetric inside the channel profile.
    0,
    short_tube_cut_center - profile_cut_center_offsets[1],
    mouth_cut_center + profile_cut_center_offsets[2]
];
slot_ys = [-row_pitch / 2, row_pitch / 2, row_pitch / 2];
slot_rot_zs = [0, 0, 180];

function slot_x(i) = slot_xs[i];
function slot_y(i) = slot_ys[i];
function slot_rot_z(i) = slot_rot_zs[i];
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

module profiled_channel_cut(i, extra_depth = 0, flat_relief = true) {
    x0 = body_x0(i);
    x1 = body_x1(i);
    x2 = connector_x1(i);
    cut_x0 = x0 - end_clearance;
    cut_x1 = (slot_has_connector[i] ? x2 : x1) + end_clearance;

    union() {
        profiled_segment(
            cut_x0 - bore_end_overlap,
            x0,
            channel_d,
            channel_d
        );

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
            profiled_segment(
                x2,
                cut_x1 + bore_end_overlap,
                channel_d,
                channel_d
            );
        } else {
            profiled_segment(x0, x1, channel_d, channel_d);
            profiled_segment(
                x1,
                cut_x1 + bore_end_overlap,
                channel_d,
                channel_d
            );
        }

        // Open only the material above the cradle lip.  The relief must begin
        // at equator_pass, not below the tube centerline, so the cylindrical
        // sidewall remains curved all the way to its just-past-equator top.
        // The lid omits this relief and retains its matching cylindrical cut.
        if (flat_relief) {
            relief_h = profile_d(i) / 2 + extra_depth;
            translate([
                (cut_x0 + cut_x1) / 2,
                0,
                equator_pass + relief_h / 2
            ])
                cube([
                    cut_x1 - cut_x0,
                    profile_d(i),
                    relief_h
                ], center = true);
        }
    }
}

module all_channel_cuts(extra_depth = 0, flat_relief = true) {
    for (i = [0 : 2])
        translate([slot_x(i), slot_y(i), slot_z])
            rotate([0, 0, slot_rot_z(i)])
                profiled_channel_cut(i, extra_depth, flat_relief);
}

// Nominal solid envelopes for collision and fit validation.  These follow the
// stored flute bodies and expanded connector regions, without channel
// clearance, and are intentionally independent of preview-only geometry.
module stored_part_proxy(i) {
    x0 = body_x0(i);
    x1 = body_x1(i);
    x2 = connector_x1(i);

    union() {
        if (slot_has_connector[i]) {
            profiled_segment(x0, x1 - connector_backset, od, od);
            profiled_segment(
                x1 - connector_backset,
                x1 - connector_expand_start,
                od,
                connector_d
            );
            profiled_segment(
                x1 - connector_expand_start,
                x1 + connector_expand_end,
                connector_d,
                connector_d
            );
            profiled_segment(
                x1 + connector_expand_end,
                x2,
                connector_d,
                od
            );
        } else {
            profiled_segment(x0, x1, od, od);
        }
    }
}

module stored_parts_proxy() {
    for (i = [0 : 2])
        translate([slot_x(i), slot_y(i), slot_z])
            rotate([0, 0, slot_rot_z(i)])
                stored_part_proxy(i);
}

module bottom_channel_deck() {
    // One continuous, visually simple bed forms every half-cylinder cradle.
    difference() {
        translate([0, 0, floor_thickness])
            rounded_box(
                [case_inner_l + 0.4, case_inner_w + 0.4, channel_deck_h],
                max(corner_r - wall + 0.2, 1)
            );
        all_channel_cuts(channel_deck_h + 1);
    }
}

module x_cylinder_between(x1, x2, d) {
    translate([(x1 + x2) / 2, 0, 0])
        rotate([0, 90, 0])
            cylinder(h = x2 - x1, d = d, center = true);
}

module hinge_pin_pair(left_root, right_root, local_y, local_z) {
    left_tip = left_root - hinge_nub_l;
    right_tip = right_root + hinge_nub_l;

    translate([0, local_y, local_z]) {
        // Rounded ogive noses self-center in the sealed sockets. Each hull
        // blends a spherical cap into the full-diameter bearing without a
        // sharp annular edge.
        hull() {
            translate([left_tip + hinge_pin_tip_r, 0, 0])
                sphere(r = hinge_pin_tip_r);
            x_cylinder_between(
                left_tip + hinge_pin_tip_l - 0.05,
                left_tip + hinge_pin_tip_l + 0.01,
                hinge_axle_d
            );
        }
        x_cylinder_between(
            left_tip + hinge_pin_tip_l - 0.02,
            left_root + 0.1,
            hinge_axle_d
        );

        x_cylinder_between(
            right_root - 0.1,
            right_tip - hinge_pin_tip_l + 0.02,
            hinge_axle_d
        );
        hull() {
            x_cylinder_between(
                right_tip - hinge_pin_tip_l - 0.01,
                right_tip - hinge_pin_tip_l + 0.05,
                hinge_axle_d
            );
            translate([right_tip - hinge_pin_tip_r, 0, 0])
                sphere(r = hinge_pin_tip_r);
        }
    }
}

module hinge_pin_breakaway_supports(
    left_root, right_root, local_y, local_z, base_z
) {
    post_top = local_z - hinge_axle_d / 2 - hinge_nub_support_gap;
    post_bottom = base_z - hinge_nub_support_base_overlap;
    post_h = post_top - post_bottom;
    left_tip = left_root - hinge_nub_l;
    right_tip = right_root + hinge_nub_l;
    left_x1 = left_tip + hinge_pin_tip_l - 0.1;
    left_x2 = left_root + 0.1;
    right_x1 = right_root - 0.1;
    right_x2 = right_tip - hinge_pin_tip_l + 0.1;

    if (post_h > 0) {
        for (span = [[left_x1, left_x2], [right_x1, right_x2]])
            translate([
                (span[0] + span[1]) / 2,
                local_y,
                post_bottom + post_h / 2
            ])
                cube([
                    span[1] - span[0],
                    hinge_nub_support_y,
                    post_h
                ], center = true);
    }
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

module hinge_barrel_rect_support(x1, x2, local_y, local_z, base_z) {
    support_h = local_z - hinge_outer_d / 2 - base_z + 0.35;
    if (support_h > 0)
        translate([
            (x1 + x2) / 2,
            local_y,
            base_z + support_h / 2
        ])
            cube([
                x2 - x1,
                hinge_backer_extension,
                support_h
            ], center = true);
}

module hinge_socket_channel_cut(x1, x2, local_y, local_z) {
    // The bottom stator remains a continuous blind cylinder. Assembly relies
    // on axial ABS flex in the lid/hinge carrier, not a split socket mouth.
    translate([0, local_y, local_z])
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
    web_h = local_z - case_outer_h + hinge_outer_d / 2 + 0.35;
    web_y = 3.6;

    translate([
        (x1 + x2) / 2,
        hinge_axis_y + web_y / 2,
        case_outer_h - 0.25 + web_h / 2
    ])
        cube([x2 - x1, web_y, web_h], center = true);
}

module bottom_hinge_socket_cuts() {
    L2 = -hinge_span / 6 - hinge_gap / 2;
    R1 = hinge_span / 6 + hinge_gap / 2;

    hinge_socket_channel_cut(
        L2 - hinge_socket_depth,
        L2 + 0.1,
        hinge_axis_y,
        hinge_axis_z
    );
    hinge_socket_channel_cut(
        R1 - 0.1,
        R1 + hinge_socket_depth,
        hinge_axis_y,
        hinge_axis_z
    );
}

module bottom_hinge() {
    for (segment = hinge_bottom_knuckles) {
        bottom_hinge_web(segment[0], segment[1], hinge_axis_z);
        hinge_support(segment[0], segment[1], hinge_axis_z);
    }
}

module lid_hinge() {
    local_axis_z = hinge_axis_z - lid_closed_z;
    M1 = -hinge_span / 6 + hinge_gap / 2;
    M2 = hinge_span / 6 - hinge_gap / 2;

    for (segment = hinge_lid_knuckles) {
        hinge_support(segment[0], segment[1], local_axis_z);
    }

    // Short, tapered nubs snap into the outer hinge sockets.
    hinge_pin_pair(M1, M2, hinge_axis_y, local_axis_z);
    if (part == "lid")
        hinge_pin_breakaway_supports(
            M1, M2, hinge_axis_y, local_axis_z, 0
        );
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
        translate([x, latch_carrier_t / 2 + latch_clip_r / 2 - 0.2, rib_z0])
            rounded_box([latch_clip_grip_rib_w, latch_clip_r, rib_h], latch_clip_r / 2);
}

module latch_clip_core() {
    difference() {
        union() {
            translate([0, latch_clip_jaw_y, 0])
                rounded_box([latch_clip_w, latch_clip_depth, latch_clip_wall], latch_clip_r);
            translate([0, latch_clip_jaw_y, latch_clip_top_offset])
                rounded_box([latch_clip_w, latch_clip_depth, latch_clip_wall], latch_clip_r);
            rounded_box([latch_clip_w, latch_carrier_t, latch_clip_total_h], latch_clip_r);
            latch_grip_ribs();
        }
        latch_entry_bevels();
    }
}

module latch_clip() {
    translate([0, latch_clip_bridge_y, latch_clip_bottom_z])
        union() {
            latch_clip_core();
            latch_nub_pair();
        }
}

module latch_nub_pair(local_y = latch_carrier_t / 2,
                      local_z = latch_clip_total_h / 2) {
    left_root = -latch_clip_w / 2;
    right_root = latch_clip_w / 2;
    left_tip = left_root - latch_nub_l;
    right_tip = right_root + latch_nub_l;
    translate([0, local_y - 0.2, local_z]) {
        hull() {
            translate([left_tip + latch_nub_tip_r, 0, 0]) sphere(r = latch_nub_tip_r);
            x_cylinder_between(left_tip + latch_nub_tip_l - 0.15,
                left_tip + latch_nub_tip_l + 0.15, latch_nub_d);
        }
        x_cylinder_between(left_tip + latch_nub_tip_l - 0.25, left_root + 3.0, latch_nub_d);
        x_cylinder_between(right_root - 3.0, right_tip - latch_nub_tip_l + 0.25, latch_nub_d);
        hull() {
            x_cylinder_between(right_tip - latch_nub_tip_l - 0.15,
                right_tip - latch_nub_tip_l + 0.15, latch_nub_d);
            translate([right_tip - latch_nub_tip_r, 0, 0]) sphere(r = latch_nub_tip_r);
        }
    }
}

module lid_integral_latch() {
    local_axis_z = latch_axis_z - lid_closed_z;
    carrier_h = latch_carrier_h;

    // The lid-side bridge is the spring. Pulling its center outward bows it
    // across X, shortening the nub span so both nubs clear the bottom sockets.
    union() {
        translate([0, latch_clip_bridge_y, local_axis_z])
            rounded_box([latch_clip_w, latch_carrier_t, carrier_h], latch_clip_r);
        translate([0, latch_clip_bridge_y, 0])
            latch_nub_pair(latch_carrier_t / 2, local_axis_z);
        for (x = [-latch_clip_w / 2 + 5, latch_clip_w / 2 - 5])
            hull() {
                translate([x, front_pull_y, lid_pull_z + front_pull_h / 2])
                    sphere(r = 1.4);
                translate([x, latch_clip_bridge_y, local_axis_z + carrier_h / 2 - 0.7])
                    sphere(r = 1.4);
            }
    }
}

module latch_snap_axle(xc, local_z) {
    translate([0, latch_snap_axis_y, local_z])
        x_cylinder_between(
            xc - latch_snap_knuckle_w / 2,
            xc + latch_snap_knuckle_w / 2,
            latch_snap_nub_d
        );
}

module bottom_latch_knuckle(xc) {
    socket_r = latch_snap_socket_d / 2;
    lip_y = socket_r + latch_snap_lip_t / 2;
    top_z = latch_snap_axis_z + latch_snap_lip_l;

    difference() {
        union() {
            translate([0, latch_snap_axis_y, latch_snap_axis_z])
                x_cylinder_between(
                    xc - latch_snap_knuckle_w / 2,
                    xc + latch_snap_knuckle_w / 2,
                    latch_snap_outer_d
                );
            for (side = [-1, 1])
                hull() {
                    translate([
                        xc,
                        latch_snap_axis_y + side * lip_y,
                        latch_snap_axis_z + latch_snap_outer_d / 4
                    ]) cube([
                        latch_snap_knuckle_w,
                        latch_snap_lip_t,
                        latch_snap_outer_d / 2
                    ], center = true);
                    translate([
                        xc,
                        latch_snap_axis_y + side * (lip_y + latch_snap_lead),
                        top_z
                    ]) cube([
                        latch_snap_knuckle_w,
                        latch_snap_lip_t,
                        0.8
                    ], center = true);
                }
        }
        translate([0, latch_snap_axis_y, latch_snap_axis_z])
            x_cylinder_between(
                xc - latch_snap_knuckle_w / 2 - 0.1,
                xc + latch_snap_knuckle_w / 2 + 0.1,
                latch_snap_socket_d
            );
        translate([
            xc,
            latch_snap_axis_y,
            latch_snap_axis_z + latch_snap_lip_l / 2 + 0.1
        ]) cube([
            latch_snap_knuckle_w + 0.4,
            latch_snap_throat,
            latch_snap_lip_l + latch_snap_outer_d
        ], center = true);
    }

    // Low web transfers pull load into the bottom front rail.
    hull() {
        translate([xc, front_pull_y, bottom_pull_z]) sphere(r = 1.5);
        translate([
            xc,
            latch_snap_axis_y,
            latch_snap_axis_z - latch_snap_outer_d / 2 + 0.8
        ]) sphere(r = 1.5);
    }
}

module bottom_radial_latch() {
    for (xc = [-latch_snap_pair_x, latch_snap_pair_x])
        bottom_latch_knuckle(xc);
}

module lid_radial_latch() {
    local_axis_z = latch_snap_axis_z - lid_closed_z;
    for (xc = [-latch_snap_pair_x, latch_snap_pair_x]) {
        support_x = xc - sign(xc) * (latch_snap_knuckle_w / 2 + 3.0);
        translate([0, latch_snap_axis_y, local_axis_z])
            x_cylinder_between(
                xc < 0 ? xc - latch_snap_knuckle_w / 2 : support_x,
                xc < 0 ? support_x : xc + latch_snap_knuckle_w / 2,
                latch_snap_nub_d
            );
        hull() {
            translate([support_x, front_pull_y, lid_pull_z + front_pull_h / 2])
                sphere(r = 1.5);
            translate([support_x, latch_snap_axis_y, local_axis_z])
                sphere(r = latch_snap_nub_d / 2);
        }
    }
}

module bottom_harmonica_latch() {
    for (xc = [-latch_pair_x, latch_pair_x]) {
        difference() {
            union() {
                translate([xc, latch_center_y,
                    latch_center_z - latch_cup_h / 2])
                    cylinder(h = latch_cup_h, d = latch_cup_outer_d);
                hull() {
                    translate([xc, front_pull_y, bottom_pull_z]) sphere(r = 1.5);
                    translate([xc, latch_center_y,
                        latch_center_z - latch_cup_h / 2 + 0.8]) sphere(r = 1.5);
                }
            }
            translate([xc, latch_center_y, latch_center_z])
                sphere(d = latch_cup_cavity_d);
            translate([xc, latch_center_y, latch_center_z])
                cylinder(h = latch_cup_h / 2 + 0.1, d = latch_cup_bore_d);
            // One outward split lets the cup expand without weakening both
            // attachment roots.
            translate([xc, latch_center_y + latch_cup_outer_d / 2,
                latch_center_z])
                cube([latch_cup_slot_w, latch_cup_outer_d,
                    latch_cup_h + 0.4], center = true);
        }
    }
}

module lid_harmonica_latch() {
    local_z = latch_center_z - lid_closed_z;
    for (xc = [-latch_pair_x, latch_pair_x]) {
        translate([xc, latch_center_y, local_z])
            sphere(d = latch_ball_d);
        translate([xc, latch_center_y, local_z + latch_ball_d / 2 - 0.1])
            cylinder(h = 2.2, d = latch_ball_neck_d);
        hull() {
            translate([xc, front_pull_y, lid_pull_z + front_pull_h / 2])
                sphere(r = 1.4);
            translate([xc, latch_center_y, local_z + latch_ball_d / 2 + 1.2])
                sphere(r = 1.3);
        }
    }
}

module lid_simple_latch() {
    local_nub_z = latch_nub_z - lid_closed_z;
    tongue_bottom_z = local_nub_z - 0.6;
    inner_y = latch_tongue_y - latch_tongue_t / 2;

    for (xc = latch_point_xs)
        union() {
            smooth_latch_tongue(xc, latch_tongue_y, tongue_bottom_z);
            translate([
                xc,
                inner_y + latch_nub_r - latch_nub_protrusion,
                local_nub_z
            ]) sphere(r = latch_nub_r);
        }
}

module bottom_simple_latch_indent_cut() {
    pocket_depth = latch_tongue_t + 0.25;
    pocket_base_y = case_outer_w / 2 - pocket_depth;
    for (xc = latch_point_xs) {
        // Receive the complete tongue thickness so its outside face is flush
        // with the uninterrupted front edge of the closed case.
        translate([
            xc,
            case_outer_w / 2 - pocket_depth / 2 + 0.1,
            latch_nub_z - 1.0
        ]) rounded_box([
            latch_tongue_root_w + 1.0,
            pocket_depth + 0.2,
            latch_tongue_flex_l - 1.0
        ], 0.8);
        translate([
            xc,
            pocket_base_y + latch_nub_r - latch_indent_depth,
            latch_nub_z
        ]) sphere(r = latch_nub_r + 0.05);
    }
}

module lid_simple_latch_relief_cuts() {
    local_nub_z = latch_nub_z - lid_closed_z;
    relief_bottom = local_nub_z - 0.9;
    relief_h = latch_tongue_flex_l - latch_tongue_root_blend_h;
    for (xc = latch_point_xs) {
        // Side slots define the cantilever; the wider upper shoulder remains
        // joined to the lid and carries the bending load into the shell.
        for (side = [-1, 1])
            translate([
                xc + side * (latch_tongue_root_w / 2 + 0.35),
                case_outer_w / 2 - wall / 2,
                relief_bottom
            ]) cube([0.7, wall + 1.0, relief_h]);
        // Hidden pocket behind the tongue provides outward release travel.
        translate([
            xc - latch_tongue_root_w / 2 - 0.4,
            case_outer_w / 2 - wall - 0.2,
            relief_bottom
        ]) cube([
            latch_tongue_root_w + 0.8,
            wall - latch_tongue_t + 0.25,
            relief_h
        ]);
    }
}

module latch_socket_knuckles() {
    socket_y = latch_clip_bridge_y + latch_carrier_t / 2;
    for (side = [-1, 1]) {
        inner_x = side * latch_mount_x;
        outer_x = side * (latch_mount_x + latch_socket_depth);
        x1 = min(inner_x, outer_x);
        x2 = max(inner_x, outer_x);
        union() {
          difference() {
            translate([0, socket_y, latch_axis_z])
                x_cylinder_between(x1, x2, latch_knuckle_outer_d);
            translate([0, socket_y, latch_axis_z])
                x_cylinder_between(x1 - 0.1, x2 + 0.1, latch_socket_d);
          }
          hull() {
            translate([side * (front_pull_w / 2 - 3.0),
                front_pull_y, bottom_pull_z]) sphere(r = 1.3);
            translate([side * (latch_mount_x + latch_socket_depth / 2),
                socket_y, latch_axis_z - 3.0]) sphere(r = 1.2);
          }
        }
    }
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

module bottom_case_core() {
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
        bottom_channel_deck();
    }
}

module bottom_case() {
    bottom_case_core();
}

module bottom_assembly() {
    difference() {
        union() {
            bottom_case();
            bottom_hinge();
        }
        bottom_hinge_socket_cuts();
        bottom_simple_latch_indent_cut();
    }
}

module lid_case() {
    lid_h = max_channel_d / 2 + lid_roof_thickness + rim_h;

    difference() {
        rounded_box([case_outer_l, case_outer_w, lid_h], corner_r);
        translate([0, 0, -0.01])
            lid_rim_socket();
        translate([0, 0, -lid_closed_z])
            all_channel_cuts(4, false);
    }
}

module lid_assembly() {
    difference() {
        union() {
            lid_case();
            lid_hinge();
            lid_simple_latch();
            lid_thumb_grip();
        }
        lid_bottom_hinge_relief();
        lid_simple_latch_relief_cuts();
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
}

module hinge_coupon() {
    coupon_span = hinge_install_flex_span + 24;
    coupon_base_l = coupon_span + 12;
    coupon_base_w = 18;
    coupon_base_h = 3;
    coupon_wall_t = hinge_tab_t;
    coupon_wall_h = hinge_outer_d + 4;
    coupon_axis_z = coupon_base_h + hinge_outer_d / 2 + 2;
    coupon_gap_y = 18;
    coupon_socket_y = coupon_base_w + coupon_gap_y;
    middle_x1 = -hinge_install_flex_span / 2;
    middle_x2 = hinge_install_flex_span / 2;
    left_socket_x1 = -coupon_span / 2;
    left_socket_x2 = middle_x1 - hinge_gap;
    right_socket_x1 = middle_x2 + hinge_gap;
    right_socket_x2 = coupon_span / 2;

    module coupon_label(label_text, y) {
        translate([-coupon_base_l / 2 + 4, y - coupon_base_w / 2 + 2.8, coupon_base_h - 0.15])
            linear_extrude(height = 0.5)
                text(label_text, size = 4, halign = "left", valign = "bottom");
    }

    module pin_coupon_half() {
        union() {
            translate([-coupon_base_l / 2, -coupon_base_w / 2, 0])
                cube([coupon_base_l, coupon_base_w, coupon_base_h]);
            translate([0, -coupon_base_w / 2 + coupon_wall_t / 2, coupon_base_h + hinge_outer_d / 2 + 2])
                cube([middle_x2 - middle_x1, coupon_wall_t, hinge_outer_d + 4], center = true);
            translate([0, -coupon_base_w / 2 + coupon_wall_t, coupon_axis_z])
                x_cylinder_between(middle_x1, middle_x2, hinge_outer_d);
            hinge_barrel_rect_support(
                middle_x1,
                middle_x2,
                -coupon_base_w / 2 + coupon_wall_t,
                coupon_axis_z,
                coupon_base_h
            );
            hinge_pin_pair(
                middle_x1,
                middle_x2,
                -coupon_base_w / 2 + coupon_wall_t,
                coupon_axis_z
            );
            hinge_pin_breakaway_supports(
                middle_x1,
                middle_x2,
                -coupon_base_w / 2 + coupon_wall_t,
                coupon_axis_z,
                coupon_base_h
            );
        }
    }

    module socket_coupon_half() {
        translate([0, coupon_socket_y, 0])
        difference() {
            union() {
                translate([-coupon_base_l / 2, -coupon_base_w / 2, 0])
                    cube([coupon_base_l, coupon_base_w, coupon_base_h]);
                for (segment = [
                    [left_socket_x1, left_socket_x2],
                    [right_socket_x1, right_socket_x2]
                ]) {
                    translate([(segment[0] + segment[1]) / 2, -coupon_base_w / 2 + coupon_wall_t / 2, coupon_base_h + coupon_wall_h / 2])
                        cube([segment[1] - segment[0], coupon_wall_t, coupon_wall_h], center = true);
                    translate([0, -coupon_base_w / 2 + coupon_wall_t, coupon_axis_z])
                        x_cylinder_between(segment[0], segment[1], hinge_outer_d);
                    hinge_barrel_rect_support(
                        segment[0],
                        segment[1],
                        -coupon_base_w / 2 + coupon_wall_t,
                        coupon_axis_z,
                        coupon_base_h
                    );
                }
                coupon_label("SOCKETS", 0);
            }
            hinge_socket_channel_cut(
                middle_x1 - hinge_gap - hinge_socket_depth,
                middle_x1 - hinge_gap + 0.1,
                -coupon_base_w / 2 + coupon_wall_t,
                coupon_axis_z
            );
            hinge_socket_channel_cut(
                middle_x2 + hinge_gap - 0.1,
                middle_x2 + hinge_gap + hinge_socket_depth,
                -coupon_base_w / 2 + coupon_wall_t,
                coupon_axis_z
            );
        }
    }

    pin_coupon_half();
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
    }

    module full_axle_half() {
        L2 = -hinge_span / 6 - hinge_gap / 2;
        R1 = hinge_span / 6 + hinge_gap / 2;
        translate([0, coupon_bottom_y, 0])
        difference() {
            union() {
                full_hinge_base(0, "CASE SOCKETS");
                for (segment = hinge_bottom_knuckles) {
                    translate([(segment[0] + segment[1]) / 2, -coupon_base_w / 2 + hinge_tab_t / 2, coupon_base_h + hinge_outer_d / 2 + 2])
                        cube([
                            segment[1] - segment[0],
                            hinge_tab_t,
                            hinge_outer_d + 4
                        ], center = true);
                    translate([0, -coupon_base_w / 2 + hinge_tab_t, coupon_axis_z])
                        x_cylinder_between(segment[0], segment[1], hinge_outer_d);
                    hinge_barrel_rect_support(
                        segment[0],
                        segment[1],
                        -coupon_base_w / 2 + hinge_tab_t,
                        coupon_axis_z,
                        coupon_base_h
                    );
                }
            }
            hinge_socket_channel_cut(
                L2 - hinge_socket_depth,
                L2 + 0.1,
                -coupon_base_w / 2 + hinge_tab_t,
                coupon_axis_z
            );
            hinge_socket_channel_cut(
                R1 - 0.1,
                R1 + hinge_socket_depth,
                -coupon_base_w / 2 + hinge_tab_t,
                coupon_axis_z
            );
        }
    }

    module full_socket_half() {
        M1 = -hinge_span / 6 + hinge_gap / 2;
        M2 = hinge_span / 6 - hinge_gap / 2;
        translate([0, coupon_socket_y, 0])
        union() {
            full_hinge_base(0, "LID PINS");
            for (segment = hinge_lid_knuckles) {
                translate([(segment[0] + segment[1]) / 2, -coupon_base_w / 2 + hinge_tab_t / 2, coupon_base_h + hinge_outer_d / 2 + 2])
                    cube([
                        segment[1] - segment[0],
                        hinge_tab_t,
                        hinge_outer_d + 4
                    ], center = true);
                translate([0, -coupon_base_w / 2 + hinge_tab_t, coupon_axis_z])
                    x_cylinder_between(segment[0], segment[1], hinge_outer_d);
                hinge_barrel_rect_support(
                    segment[0],
                    segment[1],
                    -coupon_base_w / 2 + hinge_tab_t,
                    coupon_axis_z,
                    coupon_base_h
                );
            }
            hinge_pin_pair(
                M1,
                M2,
                -coupon_base_w / 2 + hinge_tab_t,
                coupon_axis_z
            );
            hinge_pin_breakaway_supports(
                M1,
                M2,
                -coupon_base_w / 2 + hinge_tab_t,
                coupon_axis_z,
                coupon_base_h
            );
        }
    }

    full_axle_half();
    full_socket_half();
}

module latch_coupon() {
    coupon_w = latch_point_xs[len(latch_point_xs) - 1] - latch_point_xs[0]
        + latch_tongue_w + 20;
    wall_h = latch_tongue_flex_l + 3;
    lid_face_y = -12;
    bottom_face_y = 12;

    // Lid fragment: full production flex length, root thickness, and nub.
    union() {
        translate([0, lid_face_y - 3, wall_h - 3])
            rounded_box([coupon_w, 6, 3], 1.0);
        for (xc = latch_point_xs) {
            smooth_latch_tongue(
                xc,
                lid_face_y - latch_tongue_t / 2,
                0.8
            );
            translate([xc,
                lid_face_y + latch_nub_r - latch_nub_protrusion,
                latch_nub_r + 0.8]) sphere(r = latch_nub_r);
        }
        translate([0, lid_face_y - case_outer_w / 2, 0])
            lid_thumb_grip();
    }

    // Bottom fragment: a realistic wall section with only the shallow dimple.
    difference() {
        translate([0, bottom_face_y + 2, 0])
            rounded_box([coupon_w, 4, wall_h], 1.0);
        for (xc = latch_point_xs)
            translate([xc,
                bottom_face_y - latch_nub_r + latch_indent_depth,
                latch_nub_r + 0.8]) sphere(r = latch_nub_r + 0.05);
    }
}
if (part == "none") {
} else if (part == "bottom") {
    bottom_assembly();
} else if (part == "lid") {
    lid_assembly();
} else if (part == "bottom_p1s") {
    rotate([0, 0, 45]) bottom_assembly();
} else if (part == "lid_p1s") {
    rotate([0, 0, 45])
        translate([0, 0, max_channel_d / 2 + lid_roof_thickness + rim_h])
            rotate([180, 0, 0]) lid_assembly();
} else if (part == "hinge_coupon") {
    hinge_coupon();
} else if (part == "full_hinge_coupon") {
    full_hinge_coupon();
} else if (part == "latch") {
    lid_simple_latch();
} else if (part == "latch_coupon") {
    latch_coupon();
} else if (part == "assembly" || part == "print_in_place") {
    closed_assembly_case();
} else {
    color("steelblue") bottom_assembly();
    labels();
    translate([0, 0, lid_closed_z])
        color("lightgray") lid_assembly();
    preview_ghosts();
}
