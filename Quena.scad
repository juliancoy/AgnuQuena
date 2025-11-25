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
shell_width = 2.25;
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

//acoustic_length = 404.5; // Acoustic length from tone edge
acoustic_length = 396; // Acoustic length from tone edge
zadj = -8;
total_height = acoustic_length + unacoustic_length;   // total height

angled_transition_z = 2;
accent_ring_z = 0;

ov = 5;    // part overlap sleeve

non_mouthpiece_acoustic_length = acoustic_length - mouthpiece_active_length;
p1 = 120; // height of part1
p2 = 210-p1+ 13; // height of part 2
p3 = 100; // height of part 3
p4 = non_mouthpiece_acoustic_length - p1 - p2 - p3; // height of part 3 (whatever's left)
part_lengths = [p1,p2,p3,p4];
part_start = [0,p1,p1+p2,p1+p2+p3];


echo(p3);
e = 0.004;
friction_expand_default = 0.35;
tube_spacing_factor = 1.1;
insert_z_tolerance = 0.8;

//translate([20,0,0]) tube();

module tube_negative() {
    translate([0, 0, -e])
    cylinder(h = total_height + 2, d1 = id, d2 = ido);
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
        color("green") translate([0, 0, mouthpiece_actual_length-accent_ring_z]) sleve_wide((mouthpiece_actual_length) / total_height, friction_expand_default,insert_z_tolerance);
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
    translate([0,-yfactor * od * pieceno,z]){
        difference() {
            translate([0, 0, -part_start[pieceno]]) tube();
            if(pieceno<3)
                translate([0, 0, part_lengths[pieceno]-accent_ring_z]) cylinder(h = total_height, d = od * 1.1);    // top cut
            if(pieceno==3)
                translate([0, 0, part_lengths[pieceno]]) cylinder(h = total_height, d = od * 1.1);    // top cut
            translate([0,0,-e]) sleve_wide(part_start[pieceno] / total_height, 0); // bottom insert
        }
        if(pieceno < 3){ // top connector insert
            difference() {
                color("green") translate([0, 0, part_lengths[pieceno]-accent_ring_z]) sleve_wide((part_lengths[pieceno]) / total_height, friction_expand_default, insert_z_tolerance);
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
    
    
    for (i = [0,1,2,3]){
        translate([0,0,part_start[i]+mouthpiece_total_length])
        difference(){
            piece(i, 0);
            translate([0,0,-cube_cut/2]) cube([cube_cut,cube_cut,cube_cut], center=true);
        }
    }
}
module piecewise(){
    for (i = [0,1,2,3]){
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
        translate([0, 0, 342- mouthpiece_active_length+zadj]) rotate([-5, 90, 0]) cylinder(h = od, d = 10);     // A
        translate([0, 0, 307.25- mouthpiece_active_length+zadj]) rotate([5, 90, 0]) cylinder(h = od, d = 10);        // B
        translate([0, 0, 281.75- mouthpiece_active_length+zadj]) rotate([0, 90, 0]) cylinder(h = od, d = 10 - 0.5);     // C
        translate([0, 0, 246.5- mouthpiece_active_length+zadj]) rotate([5, 90, 0]) cylinder(h = od, d = 12 - 1);   // D
        translate([0, 0, 215- mouthpiece_active_length+zadj]) rotate([-5, 90, 0]) cylinder(h = od, d = 11);  // E
        translate([0, 0, 188- mouthpiece_active_length+zadj]) rotate([0, 90, 0]) cylinder(h = od, d = 10.13 + 0.75);  // F#
    }
}

// translate([-bw / 2, -bw / 2, 0]) cube([bw, bw, bl]);
translate([0,25,0])
mouthpiece();

//translate([0,75,0])
//tube();

for (i = [0,1,2,3]){
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