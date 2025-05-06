// Agnuquena. Quena by agnuca
//
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

$fn = 180; 
shell_width = 2.25;
id = 17.5;  // internal diameter at mouthpiece
od = id + shell_width*2;  // outer diameter at mouthpiece
hd = (id+od)/2; // half diameter

// Taper to the outlet (o)
taper = 0;
ido = id - taper;
odo = od - taper;
unacoustic_length = 14; 
mouthpiece_active_length = 18; // distance from mouthpiece start to active edge

acoustic_length = 404.5; // Acoustic length from tone edge
total_height = acoustic_length + unacoustic_length;   // total height

angled_transition_z = 2;
accent_ring_z = 2;

ov = 15;    // part overlap sleeve
ov_male = ov - 0.8; // z space left between merges. leave some gap to make sure they can close completely

mouthpiece_size = 50;
non_mouthpiece_acoustic_length = acoustic_length - mouthpiece_active_length;
p1 = 120; // height of part1
p2 = 120; // height of part 2
p3 = non_mouthpiece_acoustic_length - p1 - p2; // height of part 3 (whatever's left)
part_lengths = [p1,p2,p3];
part_start = [0,p1,p1+p2];

// shows the expected active length of the mouthpiece
%translate([hd/2, 0,mouthpiece_size-mouthpiece_active_length-2]) cylinder(r = 3, h = mouthpiece_active_length);

echo(p3);
e = 0.004;
friction_expand_default = 0.25;
tube_spacing_factor = 1.1;

//translate([20,0,0]) tube();

module tube_negative() {
    translate([0, 0, -e])
    cylinder(h = total_height + 2, d1 = id, d2 = ido);
}


module mouthpiece(){
    echo(mouthpiece_size);
    difference() {
        cylinder(h=mouthpiece_size, d = od);
        translate([0, 0, mouthpiece_size-accent_ring_z]) cylinder(h = total_height, d = od * 1.1);    // top cut
        translate([0,0,-e])cylinder(h=mouthpiece_size+1, d = id);
        // Active edge
        translate([0,0,mouthpiece_size-24])
        end_blown_cut_round();
    }
    difference() {
        color("green") translate([0, 0, mouthpiece_size-accent_ring_z]) sleve_wide((mouthpiece_size) / total_height, friction_expand_default);
        translate([0,0,-1])
        tube_negative();
    }
}

channel_length = 26;
module fipple_channel(){
    translate([id/2, 0, channel_length/2])
    scale([1,2,1])
    cylinder(h = channel_length+0.1, r1 = 3, r2=1.72, center=true);
}

module fipple(){
    
        
    hull($fn=80){
        translate([id/2, 0, channel_length/2])
        scale([1,2,1])
        cylinder(h = channel_length, r1 = 4, r2 = 3, center=true);
        // end stop
        translate([0,0,20])
        cylinder(d = od + e, h = shell_width, center=true);
    }
    
    difference(){
        mouthpiece();
        translate([0,0,20/2-e])
        cylinder(d = od + 0.02, h = 20, center=true);
    }
}

difference(){
    fipple();
    fipple_channel();
}

module piece(pieceno){
    echo(part_lengths[pieceno]);
    translate([0,-tube_spacing_factor * od * (pieceno+1),0]){
        difference() {
            translate([0, 0, -part_start[pieceno]]) tube();
            if(pieceno<2)
                translate([0, 0, part_lengths[pieceno]-accent_ring_z]) cylinder(h = total_height, d = od * 1.1);    // top cut
            if(pieceno==2)
                translate([0, 0, part_lengths[pieceno]]) cylinder(h = total_height, d = od * 1.1);    // top cut
            translate([0,0,-e]) sleve_wide(part_start[pieceno] / total_height, 0); // bottom insert
        }
        if(pieceno < 2){ // top connector insert
            difference() {
                color("green") translate([0, 0, part_lengths[pieceno]-accent_ring_z]) sleve_wide((part_lengths[pieceno]) / total_height, friction_expand_default);
                tube_negative();
            }
        }
        height_to_cut = height_to_cut + part_lengths[pieceno];
    }
}

height_to_cut = 0;
module piecewise(){
    difference(){
        for (i = [0,1,2]){
            piece(i);
        }
        cube_cut = 400;
        translate([0,0,-cube_cut/2]) cube([cube_cut,cube_cut,cube_cut], center=true);
    }
}

module accent_ring(){
    for (i = [0,1,2]){
        // also create its accent ring
        translate([od*1.1, -od*1.1*i, 0])
        difference(){
            cylinder(h=2, d = od);
            translate([0,0,-e])
            scale([1,1,1.1])
            cylinder(h=accent_ring_z, d = (id+od)/2);
        }
    }
}

module inner_curve_ring(){
    for (i = [0,1,2]){
        // also create its accent ring
        translate([od*1.1*2, -od*1.1*i, 0]){
            difference(){
                cylinder(h=2, d2 = hd, d1=id);
                translate([0,0,-e])
                scale([1,1,1+e])
                cylinder(h=accent_ring_z, d = id);
            }
            translate([0, 0, 2]){
                difference(){
                    cylinder(h=2, d = hd);
                    translate([0,0,-e])
                    scale([1,1,1.1])
                    cylinder(h=2, d2 = hd, d1=id);
                }
            }
        }
    }
}

//accent_ring();
//translate([0,0,-e]) inner_curve_ring();
piecewise();
//piece(0);

// i added a little width to make it fit more snugly
// This is the inner piece on top
// its additive
module sleve_wide(height_on_tube_normalized, friction_expand) {
    odlb = od * (1 - height_on_tube_normalized) + odo * height_on_tube_normalized; // outer diameter linear interpolate bottom
    odlt = od * (1 - (height_on_tube_normalized + ov/total_height)) + odo * (height_on_tube_normalized + ov/total_height); // outer diameter linear interpolate top
    odltt = od * (1 - (height_on_tube_normalized + (ov+angled_transition_z)/total_height)) + odo * (height_on_tube_normalized + (ov+angled_transition_z)/total_height); // outer diameter linear interpolate top

    obot = odlb - shell_width + friction_expand;
    otop = odlt - shell_width + friction_expand;

    odlttt = (ov+angled_transition_z)/total_height;
    idltt_id  = id  * (1 - (height_on_tube_normalized + odlttt));
    idltt_ido = ido * (height_on_tube_normalized + odlttt);
    idltt = idltt_id + idltt_ido ; // outer diameter linear interpolate top

    cylinder(h = ov_male, d1 = obot, d2=otop);

    // angled top part
    translate([0, 0, ov_male-e]) cylinder(h = angled_transition_z, d1 = otop, d2 = idltt);
}


bl = 10;    // notch translation
bw = 6;    // notch width
bos = 45;   // notch outer slope angle
bl_adjz=-1.5; // notch z adjust
module end_blown_cut_round(){
    translate([hd/2, 0, 0])
    rotate([0, bos, 0]) 
    scale([1.2,1.2,1])
    cylinder(h = od, d = bw, center=true);
}


module end_blown_cut_square(){
    cube_width = bw * 1.3;
    translate([-10, -od, 0]) 
    rotate([0, bos, 0]) 
    translate([id / 2 + bw / 2 + (od - id) / 4, 0, -od])
    cube([cube_width, od*2, od*2]);
}

module tube() {
    
    approx_last_hole = 57.5;
    %translate([od/2,0,non_mouthpiece_acoustic_length-approx_last_hole]) cylinder(h = approx_last_hole, d = 2);
    
    difference() {
        cylinder(h = non_mouthpiece_acoustic_length, d1 = od, d2 = odo);
        tube_negative();

        // Measured frequency for 100% infill PLA
        // Note  Expected  Actual (Hz)
        // G     392       386
        // A     440       434
        // B     493.88    478
        // C     523       514
        // D     587.33    580
        // E     659.25    654
        // F#    740       731
        // G     784       778

        // holes
        // translate([0, 0, bl + 147]) rotate([180, 90, 0]) cylinder(h = od, d = 5.3);  // removes thumb hole
        translate([0, 0, 342- mouthpiece_active_length]) rotate([-5, 90, 0]) cylinder(h = od, d = 10);     // A
        translate([0, 0, 307.25- mouthpiece_active_length]) rotate([5, 90, 0]) cylinder(h = od, d = 10);        // B
        translate([0, 0, 281.75- mouthpiece_active_length]) rotate([0, 90, 0]) cylinder(h = od, d = 10 - 0.5);     // C
        translate([0, 0, 246.5- mouthpiece_active_length]) rotate([5, 90, 0]) cylinder(h = od, d = 12 - 1);   // D
        translate([0, 0, 215- mouthpiece_active_length]) rotate([-5, 90, 0]) cylinder(h = od, d = 11);  // E
        translate([0, 0, 188- mouthpiece_active_length]) rotate([0, 90, 0]) cylinder(h = od, d = 10.13 + 0.75);  // F#
    }
}

// translate([-bw / 2, -bw / 2, 0]) cube([bw, bw, bl]);
