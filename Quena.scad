// Agnuquena. Quena by agnuca
//c
// OpenScad design by @agnuca 2020 https://github.com/agnunez
// Data from https://danelyepez.blogspot.com/2019/02/blog-post.html
// Modified by Julian Coy 2024-2025
// https://github.com/juliancoy/AgnuQuena

// Printing recommendations for Ender 3
// Slicer Ultimaker Cura
// Filament regular PLA
// .12mm default settings EXCEPT
// Infil 100%
// Flow 105% (printer dependant)
// Z-seam random
// Brim adhesion

// All production dimensions and tone-hole geometry are generated from the
// canonical design specification in designs/quena.json.
include <generated/quena_parameters.scad>

$fn = quena_facet_count;

//translate([20,0,0]) tube();

module tube_negative() {
    translate([0, 0, -e])
    cylinder(h = total_height + 2, d1 = id, d2 = ido);
}

module tone_hole_air() {
    tone_hole(tone_hole_a_z, tone_hole_a_angle, tone_hole_a_diameter);    // A
    tone_hole(tone_hole_b_z, tone_hole_b_angle, tone_hole_b_diameter);    // B
    tone_hole(tone_hole_c_z, tone_hole_c_angle, tone_hole_c_diameter);    // C
    tone_hole(tone_hole_d_z, tone_hole_d_angle, tone_hole_d_diameter);    // D
    tone_hole(tone_hole_e_z, tone_hole_e_angle, tone_hole_e_diameter);    // E
    tone_hole(tone_hole_fs_z, tone_hole_fs_angle, tone_hole_fs_diameter); // F#
}

module tone_hole(z, angle, hole_d) {
    // Match the nominal circular area before applying reciprocal X/Y scaling.
    // A rounded square made by offsetting a smaller square has area
    // side^2 - (4-PI)*radius^2.
    profile_side = hole_d * sqrt(
        (PI / 4) /
        (1 - (4 - PI) * tone_hole_corner_ratio * tone_hole_corner_ratio)
    );
    corner_r = profile_side * tone_hole_corner_ratio;

    translate([0, 0, z])
    rotate([angle, 90, 0])
    scale([tone_hole_axial_scale, tone_hole_circumferential_scale, 1])
    linear_extrude(height = od + 3)
    offset(r = corner_r)
    square(profile_side - 2 * corner_r, center = true);
}

module assembled_air_volume() {
    intersection() {
        union() {
            tube_negative();
            tone_hole_air();
            end_blown_cut_round();
        }
        translate([0,0,0])
        cylinder(h = total_height, d = od * 1.2);
    }
}


module mouthpiece(){
    echo(mouthpiece_total_length);
    mouthpiece_actual_length = mouthpiece_total_length;
    difference() {
        rounded_mouthpiece_body(mouthpiece_actual_length);
        end_blown_cut_round();
    }

    // connector
    difference() {
        color("green") translate([0, 0, mouthpiece_actual_length-accent_ring_z]) sleve_wide_outer((mouthpiece_actual_length) / total_height, mouthpiece_overlap, -mouthpiece_radial_interference, insert_z_tolerance);
        translate([0,0,-1])
        tube_negative();
    }
}

// Give the exposed blowing end a fully rounded wall cross-section. The radius
// is half the wall thickness, so the outer and inner fillets meet smoothly at
// the lip without changing either the production bore or outer diameter.
module rounded_mouthpiece_body(length) {
    lip_r = shell_width / 2;
    rotate_extrude(convexity = 10)
    union() {
        translate([id / 2 + lip_r, lip_r]) circle(r = lip_r);
        translate([id / 2, lip_r])
            square([shell_width, length - lip_r]);
    }
}


bl = 10;    // notch translation
bw = 8;    // notch width
bos = 45;   // notch outer slope angle
bl_adjz=-1.5; // notch z adjust
module end_blown_cut_round(rotz = 0){
    translate([hd/2, 0, 0.3])
    rotate([0, bos, rotz]) 
    scale([1.2,1.2,1])
    cylinder(h = 15, d = bw, center=true);
}


module piece(pieceno, yfactor, z=0){
    echo(part_lengths[pieceno]);
    rotate([0,0,360*((pieceno+3.5)/len(part_lengths) - 1)])
    translate([0,-yfactor * od,z]){
        difference() {
            translate([0, 0, -part_start[pieceno]]) tube();
            // Isolate the segment body at its local Z=0. Connector geometry
            // is added afterward and may intentionally extend below it.
            translate([0, 0, -cube_cut / 2])
                cube([cube_cut, cube_cut, cube_cut], center = true);
            if(pieceno<len(part_lengths) - 1)
                translate([0, 0, part_lengths[pieceno]-accent_ring_z]) cylinder(h = total_height, d = od * 1.1);    // top cut
            if(pieceno==len(part_lengths) - 1)
                translate([0, 0, part_lengths[pieceno]]) cylinder(h = total_height, d = od * 1.1);    // top cut
            if (pieceno == 0)
                translate([0,0,-e]) sleve_wide_outer(
                    part_start[pieceno] / total_height,
                    pieceno == 0 ? mouthpiece_overlap : tube_joint_overlap,
                    0
                ); // plain mating end under an upstream outer sleeve
        }
        if (pieceno == len(part_lengths) - 1) { // P2 lower outer sleeve
            difference() {
                color("green")
                    lower_tube_joint_sleeve(
                        part_start[pieceno] / total_height,
                        tube_joint_overlap,
                        tube_joint_radial_clearance
                    );
                translate([0, 0, -part_start[pieceno]]) tube_negative();
            }
        }
        height_to_cut = height_to_cut + part_lengths[pieceno];
    }
}

height_to_cut = 0;
cube_cut = 500;
module piecewise_vert(){
    // mouthpiece expectation
    %color([1,0,0,0.3])rotate([0,0,10]) translate([od/2,0,0]) cylinder(h = 6, d = 2);
    // total length expectation`
    %rotate([0,0,10]) translate([od/2,0,unacoustic_length]) cylinder(h = acoustic_length, d = 2);
    // approximate location of the furthest hole
    approx_last_hole = 57.5;
    %color([0,1,0,0.3])translate([od/2,0,total_height-approx_last_hole]) cylinder(h = approx_last_hole, d = 2);
    // approximate location of the closest hole
    %color([0,0,1,0.3])translate([od/2,0,unacoustic_length]) cylinder(h = acoustic_length/2, d = 2);
    
    
    for (i = [0 : len(part_lengths) - 1]) {
        translate([0,0,part_start[i]+mouthpiece_total_length])
        difference(){
            piece(i, 0);
            translate([0,0,-cube_cut/2]) cube([cube_cut,cube_cut,cube_cut], center=true);
        }
    }
}

module piecewise(){
    for (i = [0 : len(part_lengths) - 1]) {
        printable_piece(i, tube_spacing_factor);
    }
}

module printable_piece(pieceno, yfactor=0) {
    // Put each tube's plain free end on the bed. Connector features then build
    // upward, including P2's tapered sleeve lead-in.
    difference(){
        translate([0, 0, part_lengths[pieceno]])
            rotate([180, 0, 0])
                piece(pieceno, yfactor);
        translate([0,0,-cube_cut/2])
        cube([cube_cut,cube_cut,cube_cut], center=true);
    }
}

// Use the same conical primitive for every connector radius change. This
// keeps the mouthpiece and P2 insertion lead-ins identical in the SCAD source
// and in every exported STL.
module angled_radius_transition(
    transition_h,
    from_d,
    to_d,
    extension=0
) {
    diameter_slope = (to_d - from_d) / transition_h;
    translate([0, 0, -extension])
        cylinder(
            h = transition_h + extension * 2,
            d1 = from_d - diameter_slope * extension,
            d2 = to_d + diameter_slope * extension
        );
}

module angled_annular_transition(
    transition_h,
    outer_from_d,
    outer_to_d,
    inner_from_d,
    inner_to_d
) {
    difference() {
        angled_radius_transition(
            transition_h,
            outer_from_d,
            outer_to_d
        );
        angled_radius_transition(
            transition_h,
            inner_from_d,
            inner_to_d,
            e
        );
    }
}

module lower_tube_joint_sleeve(
    joint_height_normalized,
    overlap,
    radial_clearance=0
) {
    far_height = joint_height_normalized - overlap / total_height;
    joint_od = od * (1 - joint_height_normalized)
        + odo * joint_height_normalized;
    joint_id = id * (1 - joint_height_normalized)
        + ido * joint_height_normalized;
    far_od = od * (1 - far_height) + odo * far_height;
    fit_lead = min(0.5, overlap / 4);
    lead_height = far_height + fit_lead / total_height;
    lead_od = od * (1 - lead_height) + odo * lead_height;
    sleeve_extra_d = shell_width * 2;
    cavity_extra_d = radial_clearance * 2;

    union() {
        // Match the mouthpiece sleeve's tapered insertion lead-in. It adds no
        // radial clearance to the cylindrical retaining surface above it.
        translate([0, 0, -overlap - angled_transition_z])
            angled_annular_transition(
                angled_transition_z,
                far_od,
                far_od + sleeve_extra_d,
                far_od,
                far_od
            );

        // Keep the complete overlap cylindrical, like the mouthpiece socket.
        // The printed P1/P2 fit must not depend on a short terminal taper.
        translate([0, 0, -overlap])
            difference() {
                cylinder(
                    h = overlap + e,
                    d1 = far_od + sleeve_extra_d,
                    d2 = joint_od + sleeve_extra_d
                );
                union() {
                    translate([0, 0, -e])
                        cylinder(
                            h = fit_lead + e,
                            d1 = far_od,
                            d2 = lead_od + cavity_extra_d
                        );
                    translate([0, 0, fit_lead - e])
                        cylinder(
                            h = overlap - fit_lead + e * 2,
                            d1 = lead_od + cavity_extra_d,
                            d2 = joint_od + cavity_extra_d
                        );
                }
            }

        // Blend only the outside of the sleeve into P2. The inner shoulder is
        // intentionally left at the joint face so all 15 mm retain P1.
        translate([0, 0, -e])
            angled_annular_transition(
                angled_transition_z + e,
                joint_od + sleeve_extra_d,
                joint_od,
                joint_id,
                joint_id
            );
    }
}


module accent_ring(i=0){
    // also create its accent ring
    translate([od*1.1, -od*1.1*i, 0])
    difference(){
        cylinder(h=accent_ring_z, d = od);
        translate([0,0,-e])
        scale([1,1,1.1])
        cylinder(h=accent_ring_z, d = (id+od)/2);
    }
}

module inner_curve_ring(i=0){
    translate([od*1.1*2, -od*1.1*i, 0]){
            difference(){
                union(){
        translate([0, 0, accent_ring_z])
            cylinder(h=angled_transition_z, d1 = hd, d2=id);
                cylinder(h=accent_ring_z, d = hd);
        }
                translate([0,0,-e])
                scale([1,1,1.1])
                cylinder(h=accent_ring_z+angled_transition_z+e, d=id);
            }
    }
}

// to keep a constant diameter across the part, this comes out
module sleve_wide_outer(
    height_on_tube_normalized,
    overlap,
    socket_radial_adjustment=0,
    ztolerence=0,
    direction=1
) {
    odlb = od * (1 - height_on_tube_normalized) + odo * height_on_tube_normalized; // outer diameter linear interpolate bottom
    far_height = height_on_tube_normalized + direction * overlap / total_height;
    odlt = od * (1 - far_height) + odo * far_height; // outer diameter at the sleeve's far end
    cylinder_height = overlap - ztolerence;
    fit_lead = min(0.5, cylinder_height / 4);
    lead_height = height_on_tube_normalized
        + direction * (cylinder_height - fit_lead) / total_height;
    lead_od = od * (1 - lead_height) + odo * lead_height;

    translate([0,0,-2])
    difference(){
        union(){
            cylinder(
                h = cylinder_height,
                d1 = odlb + shell_width * 2,
                d2 = odlt + shell_width * 2
            );
            translate([0,0,-angled_transition_z])
            angled_radius_transition(
                angled_transition_z,
                odlb,
                odlt + shell_width * 2
            );
            translate([0,0,cylinder_height])
            angled_radius_transition(
                angled_transition_z,
                odlt + shell_width * 2,
                odlb
            );
        }
        union() {
            cylinder(
                h = cylinder_height - fit_lead + e,
                d1 = odlb + socket_radial_adjustment * 2,
                d2 = lead_od + socket_radial_adjustment * 2
            );
            translate([0, 0, cylinder_height - fit_lead])
                cylinder(
                    h = fit_lead + e,
                    d1 = lead_od + socket_radial_adjustment * 2,
                    d2 = odlt
                );
            translate([0, 0, cylinder_height - e])
                cylinder(
                    h = angled_transition_z + e * 2,
                    d = odlt
                );
        }
    }

}




module end_blown_cut_square(){
    cube_width = bw * 1.3;
    translate([-10, -od, 0]) 
    rotate([0, bos, 0]) 
    translate([id / 2 + bw / 2 + (od - id) / 4, 0, -od])
    cube([cube_width, od*2, od*2]);
}

module tube() {
    
    difference() {
        cylinder(h = non_mouthpiece_acoustic_length, d1 = od, d2 = odo);
        tube_negative();

        // Measured frequency for 100% infill PLA
        // Note  Expected  Actual (Hz)
        // G     392       383
        // A     440       428
        // B     493.88    470
        // C     523       505
        // D     587.33    564
        // E     659.25    630
        // F#    740       714
        // G     784       766

        // holes
        // translate([0, 0, bl + 147]) rotate([180, 90, 0]) cylinder(h = od, d = 5.3);  // removes thumb hole
        tone_hole_air();
    }
}

// Select a single printable component from the command line, for example:
// openscad -D 'export_part="part2"' -o QuenaPart2.stl Quena.scad
export_part = "layout";

if (export_part == "part1") {
    mouthpiece();
} else if (export_part == "part2") {
    // Preserve assembly coordinates; only the combined print layout flips it.
    piece(0, 0);
} else if (export_part == "part3") {
    // Preserve P2's joint-relative origin for assembly consumers. Slicers
    // place this standalone mesh on the bed automatically; the combined
    // layout uses printable_piece() to lift its lower sleeve to Z=0.
    piece(1, 0);
} else {
    translate([0,25,0]) mouthpiece();
    for (i = [0 : len(part_lengths) - 1]) {
        if(accent_ring_z > 0) translate([0,0,-e]) inner_curve_ring(i);
        accent_ring(i);
    }
    piecewise();
}

/*
for testing measurements
translate([25,0,0]){
    mouthpiece();
    piecewise_vert();
}
*/
