// D/E/F# section for checking finger reach and sealing of the equal-area oval
// openings before a full flute print. It preserves production curvature/spacing.
use <Quena.scad>

coupon_start_z = 142;
coupon_length = 82;

translate([0, 0, -coupon_start_z])
intersection() {
    tube();
    translate([-20, -20, coupon_start_z])
    cube([40, 40, coupon_length]);
}
