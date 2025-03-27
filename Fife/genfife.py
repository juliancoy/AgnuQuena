import math

# Constants
speed_of_sound = 343000  # mm/s
fundamental_freq = 440  # A4
bore_diameter = 18  # mm
embouchure_offset = 20  # mm from top (adjusted for drilling ease)
embouchure_diameter = 10  # mm
hole_diameter = 6  # mm

# End correction factor for cylindrical pipe (approximate)
end_correction = 0.6 * (bore_diameter / 2)

# Effective length for A4
L_eff = speed_of_sound / (2 * fundamental_freq)
physical_length = L_eff + end_correction

# Hole positions (from embouchure center)
note_offsets = [
    0,   # A4
    35,  # B4
    65,  # C#5
    95,  # D5
    125, # E5
    155  # F#5
]

# Absolute hole positions from tube top (embouchure_offset + offsets)
hole_positions = [embouchure_offset + offset for offset in note_offsets]

# SVG drill guide setup
svg_width = 40  # Enough to show centerline and labels
svg_height = math.ceil(physical_length + 20)

with open("fife_a4.svg", "w") as f:
    f.write(f"""
<svg width='{svg_width}mm' height='{svg_height}mm' viewBox='0 0 {svg_width} {svg_height}' xmlns='http://www.w3.org/2000/svg'>
  <!-- Centerline -->
  <line x1='{svg_width / 2}' y1='0' x2='{svg_width / 2}' y2='{svg_height}' stroke='gray' stroke-dasharray='2 2'/>

  <!-- Cut point indicators -->
  <line x1='0' y1='0' x2='{svg_width}' y2='0' stroke='black' stroke-width='0.5'/>
  <text x='2' y='6' font-size='6'>Top Cut</text>

  <line x1='0' y1='{physical_length}' x2='{svg_width}' y2='{physical_length}' stroke='black' stroke-width='0.5'/>
  <text x='2' y='{physical_length - 2}' font-size='6'>Bottom Cut</text>

  <!-- Embouchure hole -->
  <circle cx='{svg_width / 2}' cy='{embouchure_offset}' r='{embouchure_diameter / 2}' fill='red' />
  <text x='{svg_width / 2 + 6}' y='{embouchure_offset + 4}' font-size='6'>Embouchure</text>

  <!-- Tone holes -->
""")

    labels = ['A4', 'B4', 'C#5', 'D5', 'E5', 'F#5']
    for i, y in enumerate(hole_positions):
        f.write(f"  <circle cx='{svg_width / 2}' cy='{y}' r='{hole_diameter / 2}' fill='blue' />\n")
        f.write(f"  <text x='{svg_width / 2 + 6}' y='{y + 4}' font-size='6'>{labels[i]}</text>\n")

    f.write("</svg>\n")

print(f"SVG generated with drill positions for acrylic tube, length: {physical_length:.2f} mm")

