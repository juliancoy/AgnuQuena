$fn=80;
fast_air_chamber_x = 8;
fast_air_chamber_y = 2;
shell_width = 4;
outer_x=15;
inner_x=outer_x-shell_width;
midpoint_x = 1+ (outer_x + inner_x)/2;

// Create a rounded cube
module rounded_cube(size, r) {
    // Adjust the cube dimensions to account for the radius
    x = size[0] - 2 * r;
    y = size[1] - 2 * r;
    z = size[2] - 2 * r;
    
    // Use minkowski sum to create rounded edges
    minkowski() {
        cube([x, y, z], center = true);
        sphere(r = r);
    }
}

module windway(){
    
    cube([fast_air_chamber_x,fast_air_chamber_y,120], center=true);
}

module mouthpiece_tip(){
    difference(){
        scale([2,1,1])
        cylinder(h=10,r=5, center=true);
    }
}

module mouthpiece(){
    barrel_width = 17;
    mouthpiece_tip();
    translate([0,0,10])
    hull(){
        mouthpiece_tip();
        translate([0,2,20])
        rotate([0,0,0])
        rounded_cube([barrel_width,barrel_width,20], 2);
    }
}

module slow_windway(height=100){
    
    rounded_cube([inner_x,inner_x,height], 2);
}

difference(){
    mouthpiece();
    windway();
    
    translate([0,2,80])
    slow_windway();
    translate([0,2,85])
    rounded_cube([midpoint_x,midpoint_x,100], 2);
}

module p1(){
    translate([0,2,50])
    rounded_cube([midpoint_x,midpoint_x,100], 2);

    translate([0,2,55])
    rounded_cube([outer_x,outer_x,100], 2);
}


module p2(){
    translate([0,2,50])
    rounded_cube([midpoint_x,midpoint_x,100], 2);

    translate([0,2,55])
    rounded_cube([outer_x,outer_x,100], 2);
}

translate([20,0,0])
difference(){
    p1();
    translate([0,2,40]){
    slow_windway(200);
    translate([0,0,100])
    rounded_cube([midpoint_x,midpoint_x,100], 2);
    }
}


translate([-20,0,0])
difference(){
    p2();
    translate([0,2,40]){
    slow_windway(200);
    translate([0,0,100])
    rounded_cube([midpoint_x,midpoint_x,100], 2);
    }
}

