// Agnuquena. Quena by agnuca
//
// OpenScad design by @agnuca 2020 https://github.com/agnunez
// Data from https://danelyepez.blogspot.com/2019/02/blog-post.html
// Modified by Julian Coy 2024-2025
// https://github.com/juliancoy/AgnuQuena

$fn = 180; 
shell_width = 4.5;
id = 17.5;  // internal diameter at mouthpiece
od = id + shell_width;  // outer diameter at mouthpiece

// Taper to the outlet (o)
taper = 0;
ido = id - taper;
odo = od - taper;
th = 408.5;   // total height : tuned down a quarter tone = 405.8
notch_length = 3; // estimate
al = th - notch_length; // Acoustic length from tone edge

hole_shift = (th - 404) / 2;
angled_transition_z = 2;

bl = 10;    // bezel length
bw = 12;    // bezel width
bos = 20;   // bezel outer slope angle
bl_adjz=-6; // bezel z adjust
ov = 13;    // part overlap sleeve
ov_male = ov - 0.8; // z space left between merges. leave some gap to make sure they can close completely

p0 = 15;
p1 = 5; // height of part1
p2 = 127; // height of part 2
p3 = th - p0 - p1 - p2; // height of part 3 (whatever's left)
echo(p3);
epsilon = 0.004;
friction_expand_default = 0.25;
tube_spacing_factor = 1.1;

translate([0, -tube_spacing_factor * od * 2, 0]) part0();
translate([0, -tube_spacing_factor * od, 0]) part1();
part2();
translate([0, tube_spacing_factor * od, 0]) part3();

//translate([20,0,0]) tube();

module tube_negative() {
    translate([0, 0, -epsilon])
    cylinder(h = th + 2, d1 = id, d2 = ido);
}

module part0(){
    difference() {
        tube();
        translate([0, 0, p0]) cylinder(h = th, d = od * 1.1);
    }
    difference() {
        color("green") translate([0, 0, p0]) sleve_wide(p1 / th, friction_expand_default);
        translate([0, 0, 0]) tube_negative();
    }
}

module part1() {
    translate([0, 0, -p0]) difference() {
        tube();
        translate([0, 0, p1]) cylinder(h = th, d = od * 1.1);
        cylinder(h = p0, d = od * 1.1);
        translate([0, 0, p0 - epsilon]) sleve_wide(p0 / th, 0);
    }
    difference() {
        color("green") translate([0, 0, p1]) sleve_wide((p1) / th, friction_expand_default);
        translate([0, 0, 0]) tube_negative();
    }
}

module part2() {
    translate_z = p0 + p1 + p2;
    difference() {
        translate([0, 0, -translate_z])
        tube();
        translate([0, 0,translate_z]) cylinder(h = th, d = od * 1.1);
        cylinder(h = p1, d = od * 1.1); // bottom cut
        translate([0, 0, p1 - epsilon]) sleve_wide(p1 / th, 0);
    }
    difference(){
        color("green") translate([0, 0, p2]) sleve_wide((p0 + p1 + p2) / th, friction_expand_default);

        translate([0, 0, - translate_z]) tube_negative();
    }
}


module part3() {
    translate([0, 0, -p2 - p1- p0 ]) difference() {
        tube();
        translate([0, 0, p1 + p2 + p0 - epsilon]) sleve_wide((p1 + p2) / th, 0);
        cylinder(h=p0+p1+p2,d=od*1.1);
    }
}

// i added a little width to make it fit more snugly
// This is the inner piece on top
// its additive
module sleve_wide(height_on_tube_normalized, friction_expand) {
    odlb = od * (1 - height_on_tube_normalized) + odo * height_on_tube_normalized; // outer diameter linear interpolate bottom
    odlt = od * (1 - (height_on_tube_normalized + ov/th)) + odo * (height_on_tube_normalized + ov/th); // outer diameter linear interpolate top
    odltt = od * (1 - (height_on_tube_normalized + (ov+angled_transition_z)/th)) + odo * (height_on_tube_normalized + (ov+angled_transition_z)/th); // outer diameter linear interpolate top
    
    obot = odlb - shell_width / 2 + friction_expand;
    otop = odlt - shell_width / 2 + friction_expand;
    
    odlttt = (ov+angled_transition_z)/th;
    idltt_id  = id  * (1 - (height_on_tube_normalized + odlttt));
    idltt_ido = ido * (height_on_tube_normalized + odlttt);
    idltt = idltt_id + idltt_ido ; // outer diameter linear interpolate top

    
    cylinder(h = ov_male, d1 = obot, d2=otop);
    
    // angled top part
    translate([0, 0, ov_male-epsilon]) cylinder(h = angled_transition_z, d1 = otop, d2 = idltt);
    
}

module end_blown_cut_round(){
    /*
    translate([0, 0, bl]) 
    rotate([0, -bis, 0]) 
    translate([id / 2 - bw / 2 + (od - id) / 4 - 0.2, 0, -od])
    cylinder(h = od * 2, d = bw);*/
    
    translate([0, 0, bl + bl_adjz]) 
    rotate([0, bos, 0]) 
    translate([id / 2 + bw / 2 + (od - id) / 4, 0, -od])
    scale([1,2,1])
    cylinder(h = od * 2, d = bw * 1.3);
}


module end_blown_cut_square(){
    cube_width = bw * 1.3;
    translate([-10, -od, 0]) 
    rotate([0, bos, 0]) 
    translate([id / 2 + bw / 2 + (od - id) / 4, 0, -od])
    cube([cube_width, od*2, od*2]);
}
//

module tube() {
    difference() {
        cylinder(h = th, d1 = od, d2 = odo);
        tube_negative();
        
        // Active edge
        end_blown_cut_round();
        
        // Measured frequency for 100% infill PLA
        // Note  Expected  Actual (Hz)
        // G     392       391
        // A     440       443
        // B     493.88    488
        // C     523       528
        // D     587.33    595
        // E     659.25    660
        // F#    740       745
        // G     784       785

        // holes
        // translate([0, 0, bl + 147]) rotate([180, 90, 0]) cylinder(h = od, d = 5.3);  // removes thumb hole
        translate([0, 0, bl + 334 - 1 + hole_shift]) rotate([-5, 90, 0]) cylinder(h = od, d = 10);     // A
        translate([0, 0, bl + 298.25 + hole_shift]) rotate([5, 90, 0]) cylinder(h = od, d = 10);        // B
        translate([0, 0, bl + 272.75 + hole_shift]) rotate([0, 90, 0]) cylinder(h = od, d = 10 - 0.5);     // C
        translate([0, 0, bl + 237.5 + hole_shift]) rotate([5, 90, 0]) cylinder(h = od, d = 12 - 1);   // D
        translate([0, 0, bl + 206 + hole_shift]) rotate([0, 90, 0]) cylinder(h = od, d = 11);  // E
        translate([0, 0, bl + 179 + hole_shift]) rotate([0, 90, 0]) cylinder(h = od, d = 10.13 + 0.75);  // F#
    }
}

// translate([-bw / 2, -bw / 2, 0]) cube([bw, bw, bl]);