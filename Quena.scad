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

$fn = 100;
// shell_width = 2.25;
shell_width = 1.5;
id = 17.5;  // internal diameter at mouthpiece
od = id + shell_width*2;  // outer diameter at mouthpiece
hd = (id+od)/2; // half diameter

// Taper to the outlet (o)
taper = 0;
ido = id - taper;
odo = od - taper;
mouthpiece_total_length = 30;
unacoustic_length = 6; 
mouthpiece_active_length = mouthpiece_total_length-unacoustic_length; // distance from mouthpiece start to active edge

pitch_raise_cents = 12; // measured tuning is flat by this amount
length_tuning_scale = pow(2, -pitch_raise_cents / 1200);
function tuned_length(length) = length * length_tuning_scale;

//acoustic_length = 404.5; // Acoustic length from tone edge
acoustic_length = tuned_length(396); // Acoustic length from tone edge
zadj = -8;
total_height = acoustic_length + unacoustic_length;   // total height

angled_transition_z = 3;
accent_ring_z = 0;

ov = 7;    // part overlap sleeve

non_mouthpiece_acoustic_length = acoustic_length - mouthpiece_active_length;

// 3-part
tube_part_1_length = 230; // height of part 1
tube_part_2_length = non_mouthpiece_acoustic_length - tube_part_1_length; // height of part 2 (whatever's left)
part_lengths = [tube_part_1_length, tube_part_2_length];
part_start = [0, tube_part_1_length];
tube_spacing_factor = 0.6;

e = 0.004;
friction_expand_default = 0.35;
insert_z_tolerance = 0.4;

// Equal-area ovals leave more tube material around the highly loaded sides of
// each opening without adding raised pads under the fingers.  Their long axis
// follows the flute; the narrower circumferential span improves bending strength.
tone_hole_axial_scale = 1.25;
tone_hole_circumferential_scale = 1 / tone_hole_axial_scale;

//translate([20,0,0]) tube();

module tube_negative() {
    translate([0, 0, -e])
    cylinder(h = total_height + 2, d1 = id, d2 = ido);
}

module tone_hole_air() {
    tone_hole(tuned_length(341)- mouthpiece_active_length+zadj, -5, 10.1);     // A
    tone_hole(tuned_length(302.75)- mouthpiece_active_length+zadj, 5, 10.35);  // B
    tone_hole(tuned_length(279.25)- mouthpiece_active_length+zadj, 0, 9.75);   // C
    tone_hole(tuned_length(245.5)- mouthpiece_active_length+zadj, 5, 11.1);    // D
    tone_hole(tuned_length(214.15)- mouthpiece_active_length+zadj, -5, 11.1);  // E
    tone_hole(tuned_length(186.2)- mouthpiece_active_length+zadj, 0, 11.13);   // F#
}

module tone_hole(z, angle, hole_d) {
    translate([0, 0, z])
    rotate([angle, 90, 0])
    scale([tone_hole_axial_scale, tone_hole_circumferential_scale, 1])
    cylinder(h = od + 3, d = hole_d);
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
        cylinder(h=mouthpiece_actual_length, d = od);
        translate([0, 0, mouthpiece_actual_length-accent_ring_z]) cylinder(h = total_height, d = od * 1.1);    // top cut
        translate([0,0,-e])cylinder(h=mouthpiece_actual_length+1, d = id); // inner cut
        end_blown_cut_round();
    }

    // connector
    difference() {
        color("green") translate([0, 0, mouthpiece_actual_length-accent_ring_z]) sleve_wide_outer((mouthpiece_actual_length) / total_height, friction_expand_default,insert_z_tolerance);
        translate([0,0,-1])
        tube_negative();
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
            if(pieceno<len(part_lengths) - 1)
                translate([0, 0, part_lengths[pieceno]-accent_ring_z]) cylinder(h = total_height, d = od * 1.1);    // top cut
            if(pieceno==len(part_lengths) - 1)
                translate([0, 0, part_lengths[pieceno]]) cylinder(h = total_height, d = od * 1.1);    // top cut
            translate([0,0,-e]) sleve_wide_outer(part_start[pieceno] / total_height, 0); // bottom insert
        }
        if(pieceno < len(part_lengths) - 1){ // top connector insert
            difference() {
                color("green") translate([0, 0, part_lengths[pieceno]-accent_ring_z]) sleve_wide_outer((part_lengths[pieceno]) / total_height, friction_expand_default, insert_z_tolerance);
                tube_negative();
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
        difference(){
            piece(i, tube_spacing_factor);
            translate([0,0,-cube_cut/2]) cube([cube_cut,cube_cut,cube_cut], center=true);
        }
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

// i added a little width to make it fit more snugly
// This is the inner piece on top
// its additive
module sleve_wide(height_on_tube_normalized, friction_expand, ztolerence=0) {
    odlb = od * (1 - height_on_tube_normalized) + odo * height_on_tube_normalized; // outer diameter linear interpolate bottom
    odlt = od * (1 - (height_on_tube_normalized + ov/total_height)) + odo * (height_on_tube_normalized + ov/total_height); // outer diameter linear interpolate top
    odltt = od * (1 - (height_on_tube_normalized + (ov+angled_transition_z)/total_height)) + odo * (height_on_tube_normalized + (ov+angled_transition_z)/total_height); // outer diameter linear interpolate top

    obot = odlb - shell_width + friction_expand;
    otop = odlt - shell_width + friction_expand;

    odlttt = (ov+angled_transition_z)/total_height;
    idltt_id  = id  * (1 - (height_on_tube_normalized + odlttt));
    idltt_ido = ido * (height_on_tube_normalized + odlttt);
    idltt = idltt_id + idltt_ido ; // outer diameter linear interpolate top

    cylinder(h = ov - ztolerence, d1 = obot, d2=otop);

    // angled top part
    if(accent_ring_z == 0)
    translate([0, 0, ov-e-ztolerence]) cylinder(h = angled_transition_z, d1 = otop, d2 = idltt);
}


// to keep a constant diameter across the part, this comes out
module sleve_wide_outer(height_on_tube_normalized, friction_expand, ztolerence=0) {
    odlb = od * (1 - height_on_tube_normalized) + odo * height_on_tube_normalized; // outer diameter linear interpolate bottom
    odlt = od * (1 - (height_on_tube_normalized + ov/total_height)) + odo * (height_on_tube_normalized + ov/total_height); // outer diameter linear interpolate top
    odltt = od * (1 - (height_on_tube_normalized + (ov+angled_transition_z)/total_height)) + odo * (height_on_tube_normalized + (ov+angled_transition_z)/total_height); // outer diameter linear interpolate top

    obot = odlb - shell_width + friction_expand;
    otop = odlt - shell_width + friction_expand;

    odlttt = (ov+angled_transition_z)/total_height;
    idltt_id  = id  * (1 - (height_on_tube_normalized + odlttt));
    idltt_ido = ido * (height_on_tube_normalized + odlttt);
    idltt = idltt_id + idltt_ido ; // outer diameter linear interpolate top

    translate([0,0,-2])
    difference(){
        union(){
            cylinder(h = ov - ztolerence, d1 = odlb+shell_width*2, d2=odlt+shell_width*2);
            translate([0,0,-angled_transition_z])
            cylinder(h = angled_transition_z, d1 = odlb, d2=odlt+shell_width*2);
            translate([0,0,ov - ztolerence])
            cylinder(h = angled_transition_z, d1 = odlt+shell_width*2, d2=odlb);
        }            
        cylinder(h = angled_transition_z+ov - ztolerence, d1 = odlb, d2=odlt);

        
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

// translate([-bw / 2, -bw / 2, 0]) cube([bw, bw, bl]);
translate([0,25,0])
mouthpiece();

//translate([0,75,0])
//tube();

for (i = [0 : len(part_lengths) - 1]) {
    if(accent_ring_z > 0) translate([0,0,-e]) inner_curve_ring(i);
    accent_ring(i);
}
piecewise();

/*
for testing measurements
translate([25,0,0]){
    mouthpiece();
    piecewise_vert();
}
*/
