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
AirHeight = 15;
AirWidth = 9;
AirDepth = 1.9;
LipGap = 5;
LipRadius = 12;
toneHoleHeight = 11.8; 
toneHoleWidth = 9;
fippleBaseHeight = 2;
WedgeHeight = 0.8 * toneHoleHeight;
WedgeWidth = 12.5;
WedgeDepth = 4;


mouthpiece_active_length = 22.5; // distance from mouthpiece start to active edge

// shows the expected active length of the mouthpiece
// the top of this cylinder should be at the wind active edge
%translate([Dhalf, 0,]) cylinder(r = 3, h = mouthpiece_active_length+ov_male);

module MainBody()
{
	difference()
	{ 
		// main tubular section
		cylinder(r = Douter, h = TotalHeight);
		translate([0,0,-e]) 
		cylinder(r = Dinner, h = BodyHeight+e*2);
		// this is the tone hole
		translate([Douter - LipGap, -(AirWidth / 2) , TotalHeight - BodyHeight - AirHeight/4]) 
		cube([LipGap,AirWidth, AirHeight-3]);  // had to subtract a twiddle-factor here, the 3.
		// air stream canal
		translate([Douter-LipGap, -toneHoleWidth / 2 , BodyHeight]) 
		cube([AirDepth,toneHoleWidth, TotalHeight-BodyHeight+e]);
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
		translate([0,0,BodyHeight - toneHoleHeight - fippleBaseHeight ])
		cylinder(fippleBaseHeight,Dinner,Dinner);
		rotate([0,0,180])
		translate([-(Douter - LipGap),-Dinner, BodyHeight - toneHoleHeight - fippleBaseHeight- e ])
		cube([2*Dinner,2*Dinner,fippleBaseHeight+e*2]);
	}
}


module Blade()
{
    translate([Douter - LipGap + AirDepth/2 + WedgeDepth/2, WedgeWidth/2, BodyHeight - toneHoleHeight])
    {
        rotate(90,[1,0,0])
        rotate(90,[0,0,1])
        linear_extrude(height = WedgeWidth)
        {
            polygon([ [0,0], [0,WedgeDepth], [WedgeHeight, WedgeDepth/2] ]);
        }
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
