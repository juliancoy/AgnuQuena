

cyl_cut_width = 10;
cut_angle = 30;
cut_height = 3;

module cyl_cut(){
    intersection(){
        union(){
            cylinder(h = cut_height, d2=id-e, d1=od+0.1);
            difference(){
                cylinder(h = cut_height, d=od+0.1);
                cylinder(h = cut_height, d1=id-e, d2=od+0.1);
                
            }
        }
        translate([hd/2, 0,0])
        cylinder(h = 100, d = 15, center=true);
    }
}
            
channel_shell_width = 1.5;
channel_scale_x = 0.4;
channel_scale_y = 2;
channel_length = 26;
module fipple_channel(){
    translate([hd/2, 0, channel_length/2])
    scale([channel_scale_x,channel_scale_y,1])
    cylinder(h = channel_length+0.1, r1 = 3, r2=1.72, center=true);
}

channel_straight = 10;
channel_overlap  = 10 + e;
module fipple(){
    translate([hd/2, 0, channel_straight/2])
    scale([channel_scale_x,channel_scale_y,1])
    cylinder(h = channel_straight, r = 4+channel_shell_width, center=true);

    hull($fn=80){
        // channel positive upper
        translate([hd/2, 0, channel_length/2 + channel_straight/2])
        scale([channel_scale_x,channel_scale_y,1])
        cylinder(h = channel_length-channel_straight, r1 = 4+channel_shell_width, r2 = 3+channel_shell_width, center=true);
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

channel_width = 20;
channel_height = 4;
connexion_size = 2;
aoa = 8;
    
module fipple_wide(){
    translate([hd/2-1, 0, 0])
    rotate([0,aoa,0])
    difference(){
        union(){
            
            // initial channel
            hull(){
                translate([0,channel_width/2,channel_straight/2])
                cylinder(h = channel_straight, d = channel_height, center=true);
                translate([0,-channel_width/2,channel_straight/2])
                cylinder(h = channel_straight, d = channel_height, center=true);
            }
            //expansive channel outer shell
            hull(){
                translate([0,channel_width/2,channel_straight + channel_overlap/2])
                cylinder(h = channel_overlap, d = channel_height, center=true);
                translate([0,-channel_width/2,channel_straight + channel_overlap/2])
                cylinder(h = channel_overlap, d = channel_height, center=true);
                // end circle
                rotate([0,-aoa,0])
                translate([-hd/2+1,0,mouthpiece_size-connexion_size-1])
                cylinder(h=connexion_size, d = od, center=true);
            }
            
            // supporting structures
            translate([-1.8,0,channel_straight])
            scale([1,20,1])
            rotate([0,-aoa-8,0])
            cylinder(h =2, d =1, center=true);
        }
        // initial channel
        hull(){
            translate([0,channel_width/2,-e])
            cylinder(h = channel_straight+channel_overlap+e*3, d = channel_height-shell_width, center=true);
            translate([0,-channel_width/2,-e])
            cylinder(h = channel_straight+channel_overlap+e*3, d = channel_height-shell_width, center=true);
        }
        // expanding channel
        
        hull(){
            translate([0,channel_width/2,channel_straight+channel_overlap/2-e])
            cylinder(h = channel_overlap+e*3, d = channel_height-shell_width, center=true);
            translate([0,-channel_width/2,channel_straight+channel_overlap/2-e])
            cylinder(h = channel_overlap+e*3, d = channel_height-shell_width, center=true);
                // end circle
                rotate([0,-aoa,0])
            translate([-id/2,0, mouthpiece_size-connexion_size-1])
            cylinder(h=connexion_size+e, d = id, center=true);
            
        }
        
        // hole cut
        translate([1,0,channel_straight+channel_overlap+7])
        rotate([0,30,0])
        hull(){
            translate([0,-4,0])
            cylinder(h = 6, r = 2, center=true);
            translate([0,4,0])
            cylinder(h = 6, r = 2, center=true);
            
            // expand the outflow area
            translate([7,0,-3])
            rotate([0,90,0])
            cylinder(h = 1, r = 6, center=true);
        }
        
        

        
    }  
    
    
    // inner sleeve
    difference(){
        difference() {
            color("green") translate([0, 0, mouthpiece_size-accent_ring_z]) sleve_wide((mouthpiece_size) / total_height, friction_expand_default);
            translate([0,0,-1])
            tube_negative();
        }
        translate([0,0,channel_straight/2-e])cylinder(d = od + 0.02, h = channel_straight, center=true);
        translate([0,0,channel_straight+5]) cyl_cut();
    }
}
