shell_width = 2;
inner_dia = 18;
outer_dia = 22;
total_dia = outer_dia + shell_width;
height = 15;
e = 0.001;
$fn=80;
difference(){
cylinder(h = height, d = total_dia);
    translate([0,0,shell_width])
    difference(){
cylinder(h = height+e, d = outer_dia);
cylinder(h = height+e, d = inner_dia);
    }
}
