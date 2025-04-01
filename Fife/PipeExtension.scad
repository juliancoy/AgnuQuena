$fn = 100;
extension = 18;
overlap_z = 10;
e = 0.01;
id = 18;
od = 20;

module PipeExtension(){
    translate([0,0,overlap_z])
    difference(){
       cylinder(h = overlap_z, d=22, center=true);
       cylinder(h = overlap_z+e, d=od, center=true);
    }
    
    translate([0,0,-extension/2+2.5])
    difference(){
       cube([27,12,5], center=true);
       cylinder(h = overlap_z+e, d=od, center=true);
    }
    
    translate([-13,5.3,-4.7])
    rotate([0,0,-90])
    linear_extrude(1)
    text("18h 18id", size=2);
    
    translate([0,0,4])
    difference(){
       cylinder(h = 2, d1 = od, d2=22, center=true);
       cylinder(h = 2+e, d=od, center=true);
    }
    
    /*
    translate([0,0,-size_z/2])
    difference(){
       cylinder(h = 5, d=22, center=true);
       cylinder(h = size_z+e, d=18, center=true);
       cylinder(h = 5+e, d1=18, d2=22, center=true);
    }*/
    
    difference(){
       cylinder(h = extension, d=od, center=true);
       cylinder(h = overlap_z*2+e, d=18, center=true);
       //cylinder(h = 5+e, d1=18, d2=22, center=true);
    }
}

PipeExtension();