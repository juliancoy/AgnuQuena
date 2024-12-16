// Agnuquena. Quena by agnuca
//
// OpenScad design by @agnuca 2020 https://github.com/agnunez
// Data from https://danelyepez.blogspot.com/2019/02/blog-post.html
$fn=180;

id=17.5;  //internal diamenter
od=22;    //outer diameter
th=416;   //total height : tuned down a quarter tone = 405.8
hole_shift = (th-404)/2;
bl=10;    //bezel length
bw=10;    //bezel width
bos=37;    //bezel outer slope angle
bl_adjz=0; // bezel z adjust
bis=5;    //bezel inner slope angle
ov=15;    //part overlap sleve
p1=th/3;     // heigh of part1
p2=2*th/3-p1-10; // height of part 2
p3=th-p1-p2; //height of part 3

translate([0,-2*od,0])part1();
part2();
translate([0,2*od,0])part3();

module part1(){
 difference(){
  tube();
  translate([0,0,p1])cylinder(h=th,d=od*1.1);
 }
  color("green")translate([0,0,p1])sleve_wide();
}
module part2(){
 translate([0,0,-p1]) difference(){
  tube();
  translate([0,0,p1+p2])cylinder(h=p3,d=od*1.1);
  cylinder(h=p1,d=od*1.1);
  translate([0,0,p1])sleve();
 }
 color("green")translate([0,0,p2])sleve_wide();
}
module part3(){
 translate([0,0,-p1-p2])difference(){
  tube();
  cylinder(h=p1+p2,d=od*1.1);
  translate([0,0,p1+p2])sleve();
 }
}

// i added a little width to make it fit more snugly
module sleve_wide(){
 difference(){
   cylinder(h=ov,d=od-(od-id)/2+0.25);
   cylinder(h=ov,d=id);
 }    
}

module sleve(){
 difference(){
   cylinder(h=ov,d=od-(od-id)/2);
   cylinder(h=ov,d=id);
 }    
}

module tube(){
  difference(){
    cylinder(h=th,d=od);
    translate([0,0,-1])cylinder(h=th+2,d=id);
    translate([0,0,bl+bl_adjz])rotate([0,bos,0])translate([id/2+bw/2+(od-id)/4,0,-od])
      cylinder(h=od*2,d=bw*1.3);
    translate([0,0,bl])rotate([0,-bis,0])translate([id/2-bw/2+(od-id)/4-0.2,0,-od])
      cylinder(h=od*2,d=bw);
  // holes
  //translate([0,0,bl+147])rotate([180,90,0])cylinder(h=od,d=5.3);  removes thumb hole
  translate([0,0,bl+179+hole_shift])rotate([0,90,0])cylinder(h=od,d=10.13+0.25+0.5);  
  translate([0,0,bl+204+hole_shift])rotate([0,90,0])cylinder(h=od,d=10.13-0.25);  
  translate([0,0,bl+237.5+hole_shift])rotate([5,90,0])cylinder(h=od,d=12-0.75);  
  translate([0,0,bl+270+hole_shift])rotate([0,90,0])cylinder(h=od,d=10-1.25);  
  translate([0,0,bl+292+hole_shift])rotate([0,90,0])cylinder(h=od,d=12-0.75);  
  translate([0,0,bl+334-2+hole_shift])rotate([-5,90,0])cylinder(h=od,d=9.08);  
  }
}
//translate([-bw/2,-bw/2,0])cube([bw,bw,bl]);
