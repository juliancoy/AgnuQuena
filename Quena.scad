// Agnuquena. Quena by agnuca
//
// OpenScad design by @agnuca 2020 https://github.com/agnunez
// Data from https://danelyepez.blogspot.com/2019/02/blog-post.html
$fn=180;

id=17.5;  //internal diamenter
od=21;    //outer diameter
th=400;   //total height
bl=10;    //bezel length
bw=11;    //bezel width
bos=30;    //bezel outer slope angle
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
  color("green")translate([0,0,p1])sleve();
}
module part2(){
 translate([0,0,-p1]) difference(){
  tube();
  translate([0,0,p1+p2])cylinder(h=p3,d=od*1.1);
  cylinder(h=p1,d=od*1.1);
  translate([0,0,p1])sleve();
 }
 color("green")translate([0,0,p2])sleve();
}
module part3(){
 translate([0,0,-p1-p2])difference(){
  tube();
  cylinder(h=p1+p2,d=od*1.1);
  translate([0,0,p1+p2])sleve();
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
    translate([0,0,bl-0.7])rotate([0,bos,0])translate([id/2+bw/2+(od-id)/4,0,-od])
      cylinder(h=od*2,d=bw*1.3);
    translate([0,0,bl])rotate([0,-bis,0])translate([id/2-bw/2+(od-id)/4-0.2,0,-od])
      cylinder(h=od*2,d=bw);
  // holes
  translate([0,0,bl+147])rotate([180,90,0])cylinder(h=od,d=5.3);  
  translate([0,0,bl+179])rotate([0,90,0])cylinder(h=od,d=10.13);  
  translate([0,0,bl+204])rotate([0,90,0])cylinder(h=od,d=10.13);  
  translate([0,0,bl+237.5])rotate([5,90,0])cylinder(h=od,d=12);  
  translate([0,0,bl+270])rotate([0,90,0])cylinder(h=od,d=10);  
  translate([0,0,bl+292])rotate([0,90,0])cylinder(h=od,d=12);  
  translate([0,0,bl+334])rotate([-5,90,0])cylinder(h=od,d=10.08);  
  }
}
//translate([-bw/2,-bw/2,0])cube([bw,bw,bl]);
