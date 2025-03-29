import math

# Constants
speed_of_sound = 343000  # mm/s
fundamental_freq = 440  # A4 in Hz
bore_diameter = 18  # mm - standard for many flutes
bore_diameter = 22  # mm - 2mm clearance each side for adjustments
embouchure_offset = 35  # mm from top (adjusted for fife-style positioning) - UPDATED
embouchure_diameter = 10  # mm
embouchure_stretch = 8  # mm for oval embouchure hole

# Add stock at the beginning (top) of the flute
top_stock = 10  # mm stock at the beginning

# Acoustic calculations
def calculate_ideal_acoustic_position(freq):
    """Calculate ideal position based on acoustic theory"""
    wavelength = speed_of_sound / freq
    return wavelength / 2  # half-wavelength for open-open flute

# Calculate ideal positions
a4_freq = 440
b4_freq = 493.88
csharp5_freq = 554.37
d5_freq = 587.33
e5_freq = 659.25
fsharp5_freq = 739.99
gsharp5_freq = 830.61

# Theoretical acoustic positions (from embouchure)
ideal_positions = {
    "A4": calculate_ideal_acoustic_position(a4_freq),
    "B4": calculate_ideal_acoustic_position(b4_freq),
    "C#5": calculate_ideal_acoustic_position(csharp5_freq),
    "D5": calculate_ideal_acoustic_position(d5_freq),
    "E5": calculate_ideal_acoustic_position(e5_freq),
    "F#5": calculate_ideal_acoustic_position(fsharp5_freq),
    "G#5": calculate_ideal_acoustic_position(gsharp5_freq)
}

# Apply embouchure offset correction to all positions
for key in ideal_positions:
    ideal_positions[key] -= embouchure_offset

# Fine-tuned ergonomic positions based on considerations in the document
# These positions are measured from embouchure
# Note: Since we changed the embouchure position, we need to recalculate these
# We'll keep the same relative spacing between holes to maintain ergonomics
ergonomic_positions = {
    "A4": 380,  # End of the flute (all holes closed)
    "B4": 340,  # Hole 6 - Right hand, ring finger
    "C#5": 313, # Hole 5 - Right hand, middle finger
    "D5": 288,  # Hole 4 - Right hand, index finger
    "E5": 258,  # Hole 3 - Left hand, ring finger
    "F#5": 230, # Hole 2 - Left hand, middle finger
    "G#5": 205  # Hole 1 - Left hand, index finger
}

# Adjusted positions with top stock added
embouchure_pos = embouchure_offset + top_stock
adjusted_positions = {}
for note, pos in ergonomic_positions.items():
    adjusted_positions[note] = pos + top_stock

# Adjusted hole diameters to compensate for ergonomic position shifts
hole_diameters = {
    "B4": 9.0,   # Slightly enlarged from baseline
    "C#5": 9.0,  # Slightly enlarged to compensate for downward shift
    "D5": 9.0,   # Standard size
    "E5": 9.0,   # Standard size
    "F#5": 9.0,  # Standard size
    "G#5": 9.0   # Standard size
}

# Total length of the flute
total_length = adjusted_positions["A4"]

# SVG Configuration
svg_width = 100  # mm - width of the SVG canvas
svg_height = math.ceil(total_length + 100)  # Total length plus margins
svg_height = math.ceil(total_length + 40)  # Total length plus margins

# Create SVG file
with open("flute_a_major_six_hole.svg", "w") as f:
    # SVG header and container
    f.write(f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{svg_width}mm" height="{svg_height}mm" viewBox="0 0 {svg_width} {svg_height}"
     xmlns="http://www.w3.org/2000/svg" version="1.1">
  <title>Six-Hole A Major Flute Design (Fife-Style Embouchure)</title>
  <desc>Flute design showing hole placements based on acoustic and ergonomic considerations, with fife-style embouchure position</desc>
  
  <!-- Background for better visibility -->
  <rect x="0" y="0" width="{svg_width}" height="{svg_height}" fill="#f8f8f8"/>
  
  <!-- Flute tube outline -->
  <rect x="{svg_width/2 - bore_diameter/2}" y="0" width="{bore_diameter}" height="{total_length}" 
        fill="white" stroke="black" stroke-width="0.5"/>
  """)
    if False:
        f.write(f"""
  <!-- Top stock indicator -->
  <rect x="{svg_width/2 - bore_diameter/2}" y="0" width="{bore_diameter}" height="{top_stock}" 
        fill="#eeeeee" stroke="black" stroke-width="0.5"/>
  <text x="{svg_width/2 + bore_diameter/2 + 8}" y="{top_stock/2 + 4}" font-family="sans-serif" font-size="8">Top Stock</text>
  
  """)
    f.write(f"""
  <!-- Cut point indicators -->
  <line x1="{svg_width/2 - bore_diameter/2 - 5}" y1="0" x2="{svg_width/2 + bore_diameter/2 + 5}" y2="0" 
        stroke="red" stroke-width="1"/>
  <text x="{svg_width/2 - bore_diameter/2 - 40}" y="5" font-family="sans-serif" font-size="8">Top Cut</text>
  
  <line x1="{svg_width/2 - bore_diameter/2 - 5}" y1="{total_length}" x2="{svg_width/2 + bore_diameter/2 + 5}" y2="{total_length}" 
        stroke="red" stroke-width="1"/>
  <text x="{svg_width/2 - bore_diameter/2 - 40}" y="{total_length+10}" font-family="sans-serif" font-size="8">Bottom Cut</text>
  
  <!-- Embouchure hole (oval shape) -->
  <circle cx="{svg_width/2}" cy="{embouchure_pos-embouchure_stretch/2}" r="{embouchure_diameter/2}" 
         fill="none" stroke="red" stroke-width="1"/>
  <circle cx="{svg_width/2}" cy="{embouchure_pos+embouchure_stretch/2}" r="{embouchure_diameter/2}" 
         fill="none" stroke="red" stroke-width="1"/>
  <rect x="{svg_width/2-embouchure_diameter/2}" y="{embouchure_pos-embouchure_stretch/2}" width="{embouchure_diameter}" height="{embouchure_stretch}" 
        fill="none" stroke="red" stroke-width="1"/>
  <text x="{svg_width/2 + bore_diameter/2 + 8}" y="{embouchure_pos + 4}" font-family="sans-serif" font-size="8">Embouchure</text>
""")
    
    # Add fingering holes (excluding A4 which is the open end)
    notes = ["B4", "C#5", "D5", "E5", "F#5", "G#5"]
    hand_labels = ["R3", "R2", "R1", "L3", "L2", "L1"]  # Finger labels: Right/Left hand, finger number
    
    for i, note in enumerate(notes):
        position = adjusted_positions[note]
        diameter = hole_diameters[note]
        
        # Draw the hole
        f.write(f"""  <!-- {note} Hole (Hole {6-i}) -->
  <circle cx="{svg_width/2}" cy="{position}" r="{diameter/2}" 
         fill="none" stroke="blue" stroke-width="1.5"/>
  <text x="{svg_width/2 + bore_diameter/2 + 8}" y="{position + 4}" font-family="sans-serif" font-size="8">{note} ({hand_labels[i]})</text>
""")
    
    if False:
        # Add spacing measurements between adjacent holes
        prev_pos = embouchure_pos
        for i, note in enumerate(["G#5", "F#5", "E5", "D5", "C#5", "B4"]):
            curr_pos = adjusted_positions[note]
            spacing = curr_pos - prev_pos
            mid_pos = (curr_pos + prev_pos) / 2
            
            f.write(f"""  <!-- Spacing from previous hole to {note} -->
    <line x1="{svg_width/2 - bore_diameter/2 - 10}" y1="{prev_pos}" x2="{svg_width/2 - bore_diameter/2 - 10}" y2="{curr_pos}" 
            stroke="green" stroke-width="0.5"/>
    <line x1="{svg_width/2 - bore_diameter/2 - 12}" y1="{prev_pos}" x2="{svg_width/2 - bore_diameter/2 - 8}" y2="{prev_pos}" 
            stroke="green" stroke-width="0.5"/>
    <line x1="{svg_width/2 - bore_diameter/2 - 12}" y1="{curr_pos}" x2="{svg_width/2 - bore_diameter/2 - 8}" y2="{curr_pos}" 
            stroke="green" stroke-width="0.5"/>
    <text x="{svg_width/2 - bore_diameter/2 - 25}" y="{mid_pos}" font-family="sans-serif" font-size="7" fill="green">{spacing:.1f}mm</text>
    """)
            prev_pos = curr_pos
    
        # Add spacing from last hole to end
        last_pos = adjusted_positions["B4"]
        end_pos = adjusted_positions["A4"]
        end_spacing = end_pos - last_pos
        end_mid = (end_pos + last_pos) / 2
        
        f.write(f"""  <!-- Spacing from last hole to end -->
    <line x1="{svg_width/2 - bore_diameter/2 - 10}" y1="{last_pos}" x2="{svg_width/2 - bore_diameter/2 - 10}" y2="{end_pos}" 
            stroke="green" stroke-width="0.5"/>
    <line x1="{svg_width/2 - bore_diameter/2 - 12}" y1="{last_pos}" x2="{svg_width/2 - bore_diameter/2 - 8}" y2="{last_pos}" 
            stroke="green" stroke-width="0.5"/>
    <line x1="{svg_width/2 - bore_diameter/2 - 12}" y1="{end_pos}" x2="{svg_width/2 - bore_diameter/2 - 8}" y2="{end_pos}" 
            stroke="green" stroke-width="0.5"/>
    <text x="{svg_width/2 - bore_diameter/2 - 25}" y="{end_mid}" font-family="sans-serif" font-size="7" fill="green">{end_spacing:.1f}mm</text>
    """)
    
    # Add legend and flute information

    if False:
        f.write(f"""  <!-- Legend and design information -->
    <rect x="5" y="{svg_height - 75}" width="{svg_width - 10}" height="65" 
            fill="white" stroke="black" stroke-width="0.5" rx="3" ry="3"/>
    <text x="10" y="{svg_height - 60}" font-family="sans-serif" font-size="8" font-weight="bold">Six-Hole A Major Flute (Fife-Style)</text>
    <text x="10" y="{svg_height - 50}" font-family="sans-serif" font-size="7">• Scale: A4 (440Hz) to G#5</text>
    <text x="10" y="{svg_height - 40}" font-family="sans-serif" font-size="7">• Total length: {total_length}mm (including {top_stock}mm top stock)</text>
    <text x="10" y="{svg_height - 30}" font-family="sans-serif" font-size="7">• Embouchure position: {embouchure_pos}mm from top ({embouchure_offset}mm offset + {top_stock}mm stock)</text>
    <text x="10" y="{svg_height - 20}" font-family="sans-serif" font-size="7">• Bore diameter: {bore_diameter}mm, Hole diameters: 9.0mm</text>
    <text x="10" y="{svg_height - 10}" font-family="sans-serif" font-size="7">• Fife-style embouchure placement for improved ergonomics</text>
    """)
        
    # Close the SVG tag
    f.write("</svg>\n")

print(f"Fife-style flute design SVG generated with total length: {total_length}mm")
print(f"Embouchure position: {embouchure_pos}mm from top")
print(f"Acoustic length (A4): {ergonomic_positions['A4']}mm")
print(f"Total length with stock: {total_length}mm")
print("\nHole positions from embouchure (without top stock):")
for note in ["G#5", "F#5", "E5", "D5", "C#5", "B4"]:
    print(f"  {note}: {ergonomic_positions[note]}mm")

print("\nActual hole positions from top of flute (with top stock):")
for note in ["G#5", "F#5", "E5", "D5", "C#5", "B4"]:
    print(f"  {note}: {adjusted_positions[note]}mm")

print(f"Total length {total_length}")