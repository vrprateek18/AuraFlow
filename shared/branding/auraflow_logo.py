"""
AuraFlow — Vector Emblem & Logo Specification
Generates standalone SVG vector assets for AuraFlow.
"""
import math

def generate_auraflow_svg(size: int = 256) -> str:
    """Returns SVG string of the official AuraFlow emblem."""
    cx = size / 2.0
    cy = size / 2.0
    r_outer = size * 0.44
    r_mid = size * 0.34
    r_inner = size * 0.24
    r_core = size * 0.12

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">
  <defs>
    <radialGradient id="auraGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#8CEBFF" stop-opacity="0.9"/>
      <stop offset="60%" stop-color="#20BFEA" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#07111F" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="trajGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8CEBFF"/>
      <stop offset="100%" stop-color="#20BFEA"/>
    </linearGradient>
  </defs>

  <!-- Background Canvas -->
  <rect width="{size}" height="{size}" rx="{size * 0.2}" fill="#07111F"/>

  <!-- Outer Wave Ripple -->
  <circle cx="{cx}" cy="{cy}" r="{r_outer}" fill="none" stroke="#20BFEA" stroke-opacity="0.22" stroke-width="1.8"/>

  <!-- Mid Wave Ripple -->
  <circle cx="{cx}" cy="{cy}" r="{r_mid}" fill="none" stroke="#20BFEA" stroke-opacity="0.45" stroke-width="2.2"/>

  <!-- Cursor Trajectory Arc -->
  <path d="M {cx - r_inner} {cy} A {r_inner} {r_inner} 0 1 1 {cx + r_inner * 0.7} {cy - r_inner * 0.7}" 
        fill="none" stroke="url(#trajGrad)" stroke-width="3.5" stroke-linecap="round"/>

  <!-- Center Core Node & Glow -->
  <circle cx="{cx}" cy="{cy}" r="{r_core * 1.8}" fill="url(#auraGlow)"/>
  <circle cx="{cx}" cy="{cy}" r="{r_core}" fill="#20BFEA"/>
  <circle cx="{cx}" cy="{cy}" r="{r_core * 0.4}" fill="#FFFFFF"/>
</svg>"""
    return svg

if __name__ == "__main__":
    with open("auraflow_emblem.svg", "w", encoding="utf-8") as f:
        f.write(generate_auraflow_svg())
    print("AuraFlow emblem generated: auraflow_emblem.svg")
