use <Quena.scad>;

$fa = 0.1;
$fs = 0.1;

/********************************************************/
// Mikael Fernstrom
// 2014-06-11
// fipple02.scad
// Mouthpiece for a flute or whistle, including fipple	
/********************************************************/


shell_width = 2.25;
id = 17.5;  // internal diameter at mouthpiece
od = id + shell_width*2;  // outer diameter at mouthpiece
ov = 15;    // part overlap sleeve
ov_male = ov - 0.8; // z space left between merges. leave some gap to make sure they can close completely

Dhalf = (id + od) / 4;

e = 0.01;
Douter = od/2;
Dinner = id/2-0.5;
TotalHeight = 42;
BodyHeight = 25;
WindowHeight = 18;
WindowWidth = 11.2;
WindowDepth = 1;
LipGap = 5;
LipRadius = 12;
fastAirHeight = 10; 
fastAirWidth = 11.2;
fippleBaseHeight = 2;
BladeHeight = 17;
BladeWidth = 20;
BladeDepth = 7;
BladeDepthTop = 0.4;


mouthpiece_active_length = 22.5; // distance from mouthpiece start to active edge

// shows the expected active length of the mouthpiece
// the top of this cylinder should be at the wind active edge
//%translate([Dhalf, 0,]) cylinder(r = 3, h = mouthpiece_active_length+ov_male);

module MainBody()
{
	difference()
	{ 
		// main tubular section
		cylinder(r = Douter, h = TotalHeight);
		translate([0,0,-e]) 
		cylinder(r = Dinner, h = BodyHeight+e*2);
		// this is the tone hole
		translate([Douter - LipGap, -(WindowWidth / 2) , TotalHeight - BodyHeight - WindowHeight/2]) 
		cube([LipGap,WindowWidth, WindowHeight]);  
		// Window 
		translate([Douter-LipGap, -fastAirWidth / 2 , BodyHeight]) 
		cube([WindowDepth,fastAirWidth, WindowHeight+e]);
		// lip-part cut out
		rotate(90, [1,0,0])
		translate([-1 * TotalHeight / 4, TotalHeight, -1 * Douter])
		cylinder(r = LipRadius, Douter * 2);
	}
}

module BladeBase()
{
	difference()
	{
		translate([0,0,BodyHeight - fastAirHeight - fippleBaseHeight ])
		cylinder(fippleBaseHeight,Dinner,Dinner);
		rotate([0,0,180])
		translate([-(Douter - LipGap),-Dinner, BodyHeight - fastAirHeight - fippleBaseHeight- e ])
		cube([2*Dinner,2*Dinner,fippleBaseHeight+e*2]);
	}
}


module Blade()
{
    difference(){
        intersection(){
            translate([Douter - LipGap + WindowDepth/2 + BladeDepth/2, BladeWidth/2, BodyHeight-WindowHeight])
            {
                rotate(90,[1,0,0])
                rotate(90,[0,0,1])
                linear_extrude(height = BladeWidth)
                {
                    polygon([ [0,0], [0,BladeDepth], [BladeHeight, BladeDepth/2 + BladeDepthTop/2], [BladeHeight, BladeDepth/2 - BladeDepthTop/2] ]);
                }
            }
            cylinder(h=100, r=Douter);
        }
        
        translate([0,0,BodyHeight-WindowHeight+BladeHeight+1])
        scale([1,2,1])
        rotate([0,90,0])
        cylinder(h=100, r=3, center=true);
        
        
        translate([0, 0, BodyHeight-WindowHeight-e])
        cylinder(h=BladeHeight-5, r1=Dinner, r2=Dinner -3);
        
    }
}


translate([0,0,ov_male]){
    MainBody();
    //BladeBase();
    Blade();
    
}

difference(){
    cylinder(h = ov_male, r = Dhalf);
    translate([0,0,-e])
    cylinder(h = ov_male+2*e, r = Dinner);
}
