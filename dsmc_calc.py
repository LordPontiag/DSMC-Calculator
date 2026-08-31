#!/usr/bin/env python3
"""
DSMC Setup Calculator - Enhanced Version
- Dimensions in brackets
- Velocity/Mach selection (Mach mode keeps V or T constant)
- Two-way particle weighting (Nppc <-> nEquivalentParticles)
- Formulas panel
- Fluid name input
- Hint icons
- Improved layout (2/5 left, 2/5 results, 1/5 formulas)
"""

import math
import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

K_B = 1.380649e-23

# ----------------------------------------------------------------------------
# Physics Helper Functions
# ----------------------------------------------------------------------------
def vhs_cross_section(dref, Tref, omega, T):
    return math.pi * (dref ** 2) * (Tref / T) ** (omega - 0.5)

def mean_free_path(n, sigma_T):
    return 1.0 / (math.sqrt(2.0) * n * sigma_T)

def mean_thermal_speed(mass, T):
    return math.sqrt(8.0 * K_B * T / (math.pi * mass))

def sound_speed(gamma, R_specific, T):
    return math.sqrt(gamma * R_specific * T)

def vhs_mu_ref(mass, dref, omega, Tref):
    return (15.0 * math.sqrt(math.pi * mass * K_B * Tref)) / (
        2.0 * math.pi * (dref ** 2) * (5.0 - 2.0 * omega) * (7.0 - 2.0 * omega)
    )

def vhs_mu(mu_ref, Tref, omega, T):
    return mu_ref * (T / Tref) ** omega

def recovery_temperature(T, gamma, M, Pr):
    r = math.sqrt(Pr)
    return T * (1.0 + r * (gamma - 1.0) / 2.0 * (M ** 2))

def eckert_reference_temperature(T, M, Tw):
    return T * (1.0 + 0.032 * (M ** 2) + 0.58 * (Tw / T - 1.0))

def fmt(x, sig=4):
    if x is None:
        return "n/a"
    try:
        ax = abs(float(x))
    except (TypeError, ValueError):
        return str(x)
    if ax != 0 and (ax < 1e-3 or ax >= 1e5):
        return f"{x:.{sig}e}"
    return f"{x:.{sig}g}"

def get_float(vars_dict, labels, key, required=True, default=None):
    s = vars_dict[key].get().strip()
    if s == "":
        if required:
            raise ValueError(f"'{labels.get(key, key)}' is required.")
        return default
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"'{labels.get(key, key)}' must be a number (got '{s}').")

# ----------------------------------------------------------------------------
# Field Specifications
# ----------------------------------------------------------------------------
SPECIES_FIELDS = [
    ("mass", "Molecular mass, m", "66.3e-27", "kg"),
    ("dref", "VHS ref diameter, d_ref", "4.17e-10", "m"),
    ("omega", "VHS viscosity index, ω", "0.81", ""),
    ("Tref", "VHS ref temperature, T_ref", "298.15", "K"),
    ("gamma", "Specific heat ratio, γ", "1.667", ""),
    ("Pr", "Prandtl number, Pr", "0.667", ""),
]

FLOW_FIELDS = [
    ("T", "Temperature, T", "150", "K"),
    ("U", "Bulk velocity, U", "736.5", "m/s"),
    ("M", "Mach number, M", "3.0", ""),
    ("P", "Pressure, P", "1.0", "Pa"),
    ("n", "Number density, n", "4e20", "m⁻³"),
]

MESH_FIELDS = [
    ("Vdomain", "Domain volume, V", "1.0", "m³"),
    ("Ncells", "Number of cells", "100000", ""),
    ("Vcell", "Cell volume, V_cell", "", "m³"),
    ("Nppc", "Particles per cell, Nppc", "20", ""),
    ("nEquivalentParticles", "nEquivalentParticles", "", ""),
]

LENGTH_FIELDS = [
    ("LKn", "Length for Kn, L_Kn", "0.5", "m"),
    ("LRe", "Length for Re, L_Re", "0.5", "m"),
    ("compression", "Compression ratio n/n∞", "1.0", ""),
    ("f1", "Collision safety factor f1", "0.2", ""),
    ("f2", "Transit safety factor f2", "0.3", ""),
]

VISCOUS_FIELDS = [
    ("x", "Distance from edge, x", "0.1", "m"),
    ("Tw", "Wall temperature, T_w", "150", "K"),
]

KN_FIELDS = [
    ("mass", "Molecular mass, m", "66.3e-27", "kg"),
    ("dref", "VHS ref diameter, d_ref", "4.17e-10", "m"),
    ("omega", "VHS viscosity index, ω", "0.81", ""),
    ("Tref", "VHS ref temperature, T_ref", "298.15", "K"),
    ("gamma", "Specific heat ratio, γ", "1.667", ""),
    ("T", "Temperature, T", "150", "K"),
    ("LKn", "Reference length, L_Kn", "0.5", "m"),
    ("Kn_target", "TARGET Kn", "0.1", ""),
    ("Vcell", "Cell volume (optional)", "", "m³"),
    ("Nppc", "Particles/cell (optional)", "20", ""),
]

RE_FIELDS = [
    ("mass", "Molecular mass, m", "66.3e-27", "kg"),
    ("dref", "VHS ref diameter, d_ref", "4.17e-10", "m"),
    ("omega", "VHS viscosity index, ω", "0.81", ""),
    ("Tref", "VHS ref temperature, T_ref", "298.15", "K"),
    ("gamma", "Specific heat ratio, γ", "1.667", ""),
    ("T", "Temperature, T", "150", "K"),
    ("LRe", "Reference length, L_Re", "0.5", "m"),
    ("Re_target", "TARGET Re", "5000", ""),
    ("P", "Pressure, P", "1.0", "Pa"),
    ("n", "Number density, n", "4e20", "m⁻³"),
    ("Vcell", "Cell volume (optional)", "", "m³"),
    ("Nppc", "Particles/cell (optional)", "20", ""),
    ("f1", "Collision safety factor f1", "0.2", ""),
    ("f2", "Transit safety factor f2", "0.3", ""),
]

ALL_LABELS = {}
for grp in [SPECIES_FIELDS, FLOW_FIELDS, MESH_FIELDS, LENGTH_FIELDS, VISCOUS_FIELDS, KN_FIELDS, RE_FIELDS]:
    for k, lbl, *_ in grp:
        ALL_LABELS[k] = lbl

# ----------------------------------------------------------------------------
# Hint Information
# ----------------------------------------------------------------------------
HINTS = {
    "rarefaction": {
        "title": "Rarefaction Coefficient",
        "text": "Scales the input density/pressure:\n\n" +
                "• 1.0 = Use inputs as-is\n" +
                "• 0.1 = 10× more rarefied (lower density)\n" +
                "• 10 = 10× less rarefied (higher density)\n\n" +
                "Use to quickly explore different Kn regimes\n" +
                "without manually changing P or n."
    },
    "compression": {
        "title": "Compression Ratio (n/n∞)",
        "text": "Expected maximum density ratio in domain:\n\n" +
                "• 1.0 = Uniform flow (no shocks)\n" +
                "• 2-5 = Supersonic flows with weak shocks\n" +
                "• 3-10 = Hypersonic blunt bodies\n" +
                "• 5-20 = Strong shock waves\n\n" +
                "Affects recommended time step only.\n" +
                "Higher values → smaller Δt for stability."
    },
    "nppc": {
        "title": "Particles Per Cell (Nppc)",
        "text": "Target simulated particles per cell:\n\n" +
                "• 10-20 = Standard DSMC (good accuracy)\n" +
                "• 20-50 = High accuracy (slower)\n" +
                "• 5-10 = Quick tests (lower accuracy)\n\n" +
                "Higher Nppc → better statistics but\n" +
                "higher computational cost.\n" +
                "nEquivalent = (n·Vcell) / Nppc"
    },
    "kn": {
        "title": "Knudsen Number (Kn)",
        "text": "Ratio of mean free path to characteristic length:\n\n" +
                "• Kn < 0.01: Continuum (use CFD)\n" +
                "• 0.01 < Kn < 0.1: Slip flow\n" +
                "• 0.1 < Kn < 10: Transitional (use DSMC)\n" +
                "• Kn > 10: Free molecular flow\n\n" +
                "DSMC is most efficient for 0.1 < Kn < 10."
    },
    "re": {
        "title": "Reynolds Number (Re)",
        "text": "Ratio of inertial to viscous forces:\n\n" +
                "• Re < 1: Stokes flow (creeping)\n" +
                "• 1 < Re < 1000: Laminar flow\n" +
                "• Re > 1000: Transitional/turbulent\n\n" +
                "For DSMC, ensure cell size < λ and\n" +
                "Δt < τ regardless of Re value."
    }
}

# ----------------------------------------------------------------------------
# Scrollable Frame
# ----------------------------------------------------------------------------
class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
    
    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
    
    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")
    
    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

# ----------------------------------------------------------------------------
# Hint Icon Widget
# ----------------------------------------------------------------------------
class HintIcon(tk.Button):
    def __init__(self, parent, key, **kwargs):
        super().__init__(
            parent,
            text="ⓘ",
            command=self.show_hint,
            cursor="hand2",
            font=("Arial", 11, "bold"),
            fg="white",
            bg="#1976D2",
            activeforeground="white",
            activebackground="#1565C0",
            relief="flat",
            bd=0,
            width=2,
            height=1,
            padx=0,
            pady=0,
            **kwargs
        )
        self.key = key

    def show_hint(self):
        if self.key in HINTS:
            info = HINTS[self.key]
            messagebox.showinfo(info["title"], info["text"])

# ----------------------------------------------------------------------------
# Main Application
# ----------------------------------------------------------------------------
class DSMCCalculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DSMC Setup Calculator - Enhanced")
        self.geometry("1600x950")
        
        # Configure modern styles
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Arial', 10))
        style.configure('TLabel', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10, 'bold'))
        style.configure('TRadiobutton', font=('Arial', 10))
        style.configure('TCheckbutton', font=('Arial', 10))
        style.configure('TLabelframe', font=('Arial', 11, 'bold'))
        style.configure('TLabelframe.Label', font=('Arial', 11, 'bold'))
        style.configure('TEntry', font=('Arial', 11))
        style.configure('TNotebook.Tab', font=('Arial', 11, 'bold'), padding=[12, 8])
        
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        tab1 = ttk.Frame(notebook)
        tab2 = ttk.Frame(notebook)
        tab3 = ttk.Frame(notebook)
        notebook.add(tab1, text="  1) Setup Calculator  ")
        notebook.add(tab2, text="  2) Solve for Kn  ")
        notebook.add(tab3, text="  3) Solve for Re  ")
        
        self.vars = {}
        self.kn_vars = {}
        self.re_vars = {}
        self.density_mode = tk.StringVar(value="P")
        self.velocity_mode = tk.StringVar(value="U")
        self.mach_constraint_mode = tk.StringVar(value="U")
        self.volume_mode = tk.StringVar(value="domain")
        self.particle_mode = tk.StringVar(value="Nppc")
        self.setup_entries = {}
        self.viscous_var = tk.BooleanVar(value=True)
        self.re_density_mode = tk.StringVar(value="P")
        
        self.build_setup_tab(tab1)
        self.build_kn_tab(tab2)
        self.build_re_tab(tab3)
    
    def build_setup_tab(self, parent):
        main = ttk.Frame(parent)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # -------------------------------------------------------------------------
        # Three panels: Left (larger), Results, Equations (smaller)
        # -------------------------------------------------------------------------

        # Left/input panel
        left_panel = ScrollableFrame(main)
        left_panel.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 5)
        )
        left_panel.configure(width=600)
        left_panel.pack_propagate(False)

        left = left_panel.scrollable_frame

        # Results panel
        results_frame = ttk.Frame(main)
        results_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5
        )

        # Equations panel
        formulas_frame = ttk.Frame(main)
        formulas_frame.pack(
            side="left",
            fill="both",
            padx=(5, 0)
        )
        formulas_frame.configure(width=350)
        formulas_frame.pack_propagate(False)

        self.build_formulas_panel(formulas_frame)
        
        # Rarefaction coefficient with hint
        rarefaction_frame = ttk.LabelFrame(left, text="⚙️ RAREFACTION CONTROL", padding=10)
        rarefaction_frame.pack(fill="x", pady=10)
        ttk.Label(rarefaction_frame, text="Rarefaction Coefficient:").pack(anchor="w")
        hint_row = ttk.Frame(rarefaction_frame)
        hint_row.pack(fill="x")
        ttk.Label(hint_row, text="1.0 = use inputs | 0.1 = 10× rarefied | 10 = 10× dense", 
                 foreground='gray').pack(side="left", anchor="w")
        HintIcon(hint_row, "rarefaction").pack(side="left", padx=5)
        self.rarefaction_var = tk.StringVar(value="1.0")
        ttk.Entry(rarefaction_frame, textvariable=self.rarefaction_var, width=20).pack(anchor="w", pady=5)
        
        # Species section
        species_frame = ttk.LabelFrame(left, text="📊 Species (VHS Model) - Prefilled for Argon (Ar)", padding=10)
        species_frame.pack(fill="x", pady=5)
        
        # Fluid name
        fluid_row = ttk.Frame(species_frame)
        fluid_row.pack(fill="x", pady=3)
        ttk.Label(fluid_row, text="Fluid name:", width=38, anchor="w").pack(side="left")
        self.fluid_name_var = tk.StringVar(value="Argon")
        ttk.Entry(fluid_row, textvariable=self.fluid_name_var, width=22).pack(side="left", padx=10)
        
        self.create_input_fields(species_frame, SPECIES_FIELDS, self.vars)
        
        # Flow state section
        flow_frame = ttk.LabelFrame(left, text="🌊 Flow State", padding=10)
        flow_frame.pack(fill="x", pady=5)
        
        # Density mode
        density_frame = ttk.Frame(flow_frame)
        density_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(density_frame, text="Specify density by:").pack(side="left")
        ttk.Radiobutton(density_frame, text="Pressure (P)", variable=self.density_mode, value="P").pack(side="left", padx=10)
        ttk.Radiobutton(density_frame, text="Number density (n)", variable=self.density_mode, value="n").pack(side="left")
        
        # Velocity / Mach mode
        velocity_frame = ttk.Frame(flow_frame)
        velocity_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(velocity_frame, text="Specify flow speed by:").pack(side="left")

        ttk.Radiobutton(
            velocity_frame,
            text="Velocity U",
            variable=self.velocity_mode,
            value="U",
            command=self.update_flow_controls
        ).pack(side="left", padx=10)

        ttk.Radiobutton(
            velocity_frame,
            text="Mach number M",
            variable=self.velocity_mode,
            value="M",
            command=self.update_flow_controls
        ).pack(side="left")

        # Mach constraint selection
        self.mach_constraint_frame = ttk.Frame(flow_frame)

        ttk.Label(
            self.mach_constraint_frame,
            text="For Mach mode, keep:"
        ).pack(side="left")

        ttk.Radiobutton(
            self.mach_constraint_frame,
            text="Velocity U constant",
            variable=self.mach_constraint_mode,
            value="U",
            command=self.update_flow_controls
        ).pack(side="left", padx=10)

        ttk.Radiobutton(
            self.mach_constraint_frame,
            text="Temperature T constant",
            variable=self.mach_constraint_mode,
            value="T",
            command=self.update_flow_controls
        ).pack(side="left")

        # Flow input fields
        self.create_input_fields(
            flow_frame,
            FLOW_FIELDS,
            self.vars,
            entry_registry=self.setup_entries
        )

        self.update_flow_controls()
        
        # Mesh section
        mesh_frame = ttk.LabelFrame(left, text="🔲 Mesh & Particle Weighting", padding=10)
        mesh_frame.pack(fill="x", pady=5)
        volume_frame = ttk.Frame(mesh_frame)
        volume_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(volume_frame, text="Specify cell volume by:").pack(side="left")
        ttk.Radiobutton(volume_frame, text="Domain + N_cells", variable=self.volume_mode, value="domain").pack(side="left", padx=10)
        ttk.Radiobutton(volume_frame, text="Direct V_cell", variable=self.volume_mode, value="cell").pack(side="left")

        # Particle weighting mode
        particle_frame = ttk.Frame(mesh_frame)
        particle_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(particle_frame, text="Specify particle weighting by:").pack(side="left")
        ttk.Radiobutton(
            particle_frame,
            text="Particles per cell (Nppc)",
            variable=self.particle_mode,
            value="Nppc",
            command=self.update_particle_controls
        ).pack(side="left", padx=10)
        ttk.Radiobutton(
            particle_frame,
            text="nEquivalentParticles",
            variable=self.particle_mode,
            value="nEq",
            command=self.update_particle_controls
        ).pack(side="left")

        self.create_input_fields(mesh_frame, MESH_FIELDS, self.vars, entry_registry=self.setup_entries)

        self.update_particle_controls()
        
        # Length section with hints
        length_frame = ttk.LabelFrame(left, text="📏 Reference Lengths & Time Step", padding=10)
        length_frame.pack(fill="x", pady=5)
        
        # Add fields with hints
        for i, (key, label, default, unit) in enumerate(LENGTH_FIELDS):
            row = ttk.Frame(length_frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=38, anchor="w").pack(side="left")
            var = tk.StringVar(value=default)
            self.vars[key] = var
            entry = ttk.Entry(row, textvariable=var, width=22)
            entry.pack(side="left", padx=10)
            if unit:
                ttk.Label(row, text=unit, width=12, anchor="w", foreground='gray').pack(side="left")
            if key in ["compression", "f1", "f2"]:
                hint_key = "compression" if key == "compression" else None
                if hint_key:
                    HintIcon(row, hint_key).pack(side="left", padx=2)
        
        # Boundary layer section
        bl_frame = ttk.LabelFrame(left, text="🔵 Boundary Layer (Optional)", padding=10)
        bl_frame.pack(fill="x", pady=5)
        ttk.Checkbutton(bl_frame, text="✓ Viscous (compute boundary layer)", variable=self.viscous_var).pack(anchor="w", pady=(0, 10))
        self.create_input_fields(bl_frame, VISCOUS_FIELDS, self.vars)
        ttk.Button(bl_frame, text="🔄 Auto-fill T_w with Recovery Temp", command=self.auto_recovery_temp).pack(pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill="x", pady=15)
        ttk.Button(btn_frame, text="📊 CALCULATE", command=self.calculate_setup).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Reset Defaults", command=self.reset_setup).pack(side="left", padx=5)
        
        # Results
        result_header = ttk.Frame(results_frame)
        result_header.pack(fill="x")
        ttk.Label(result_header, text="📈 RESULTS", font=("Arial", 14, "bold")).pack(anchor="w")
        
        self.result_text = scrolledtext.ScrolledText(results_frame, wrap="word", font=("Courier", 13), 
                                                     bg="white", relief="flat", padx=10, pady=10)
        self.result_text.pack(fill="both", expand=True, pady=10)
        self.result_text.insert("1.0", "Enter values in the input boxes on the left and click CALCULATE\n\n" +
                               "💡 Tip: Use rarefaction coefficient to scale density:\n" +
                               "   • 1.0 = use your input values directly\n" +
                               "   • 0.1 = 10× more rarefied (lower density)\n" +
                               "   • 10 = 10× less rarefied (higher density)")
        self.result_text.configure(state="disabled")
        
        btn_row = ttk.Frame(results_frame)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text=" Copy OpenFOAM", command=self.copy_openfoam).pack(side="left", padx=5)
        ttk.Button(btn_row, text=" Save Report", command=self.save_report).pack(side="left", padx=5)
        
        self.last_results = {}
    
    def build_formulas_panel(self, parent):
        ttk.Label(parent, text=" EQUATIONS USED", font=("Arial", 12, "bold")).pack(anchor="w", pady=5)
        
        formulas_text = scrolledtext.ScrolledText(parent, wrap="word", font=("Courier", 10),
                                                  bg="#f5f5f5", relief="flat", padx=8, pady=8)
        formulas_text.pack(fill="both", expand=True)
        
        formulas = """
══════════════════════════════════════════════════════╗
║  DSMC CALCULATOR - MATHEMATICAL FORMULAS             ║
╚══════════════════════════════════════════════════════╝

1. IDEAL GAS LAW
   P = n·k_B·T
   n = P/(k_B·T)

2. MASS DENSITY
   ρ = n·m

3. SOUND SPEED
   a = √(γ·R·T)
   where R = k_B/m
   (Mach mode, T constant:  U = M·a)
   (Mach mode, U constant:  a = U/M, T = a²/(γ·R))

4. MACH NUMBER
   M = U/a

5. VHS CROSS-SECTION
   σ_T = π·d_ref²·(T_ref/T)^(ω-0.5)

6. MEAN FREE PATH
   λ = 1/(√2·n·σ_T)

7. MEAN THERMAL SPEED
   c̄ = √(8·k_B·T/(π·m))

8. MEAN COLLISION TIME
   τ = λ/c̄

9. VHS VISCOSITY
   μ_ref = 15√(π·m·k_B·T_ref) / [2π·d_ref²·(5-2ω)(7-2ω)]
   μ = μ_ref·(T/T_ref)^ω

10. KNUDSEN NUMBER
    Kn = λ/L_Kn

11. REYNOLDS NUMBER
    Re = ρ·U·L_Re/μ

12. CELL SIZE
    Δx = V_cell^(1/3)

13. PARTICLE WEIGHTING
    n_eq = (n·V_cell)/N_ppc
    N_ppc = (n·V_cell)/n_eq

    where:
      n_eq = real molecules represented by one DSMC particle
      N_ppc = simulated particles per cell

14. TIME STEP
    Δt_coll = f₁·τ
    Δt_trans = f₂·Δx/(U + c̄)
    Δt = min(Δt_coll, Δt_trans)

15. RECOVERY TEMPERATURE
    T_r = T·[1 + Pr·(γ-1)/2·M²]

16. ECKERT REFERENCE TEMP
    T* = T·[1 + 0.032·M² + 0.58·(T_w/T - 1)]

17. BOUNDARY LAYER THICKNESS
    δ = 5·x/√Re_x
    θ = 0.664·x/√Re_x
    δ* = 1.721·x/√Re_x

═══════════════════════════════════════════════════════
Constants:
  k_B = 1.380649×10⁻²³ J/K (Boltzmann)
  
For Argon (Ar):
  m = 66.3×10⁻²⁷ kg
  d_ref = 4.17×10⁻¹⁰ m
  ω = 0.81
  γ = 5/3 ≈ 1.667
  Pr ≈ 0.667
═══════════════════════════════════════════════════════
"""
        formulas_text.insert("1.0", formulas)
        formulas_text.configure(state="disabled")
    
    def create_input_fields(self, parent, field_list, vars_dict, entry_registry=None):
        for i, (key, label, default, unit) in enumerate(field_list):
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=3)
            
            ttk.Label(row, text=label, width=38, anchor="w").pack(side="left")
            var = tk.StringVar(value=default)
            vars_dict[key] = var
            entry = ttk.Entry(row, textvariable=var, width=22)
            entry.pack(side="left", padx=10)
            if entry_registry is not None:
                entry_registry[key] = entry
            if unit:
                ttk.Label(row, text=unit, width=12, anchor="w", foreground='gray').pack(side="left")

    def update_flow_controls(self):
        """Enable/disable T, U, and M fields according to the selected mode."""
        mode = self.velocity_mode.get()

        # Hide Mach-specific options in normal velocity mode
        if mode == "M":
            self.mach_constraint_frame.pack(fill="x", pady=(0, 10))
        else:
            self.mach_constraint_frame.pack_forget()

        # Make sure the required entries exist
        if not all(k in self.setup_entries for k in ("T", "U", "M")):
            return

        T_entry = self.setup_entries["T"]
        U_entry = self.setup_entries["U"]
        M_entry = self.setup_entries["M"]

        if mode == "U":
            # U and T are independent inputs
            T_entry.configure(state="normal")
            U_entry.configure(state="normal")
            M_entry.configure(state="disabled")

        elif self.mach_constraint_mode.get() == "U":
            # M + U -> calculate T
            M_entry.configure(state="normal")
            U_entry.configure(state="normal")
            T_entry.configure(state="disabled")

        else:
            # M + T -> calculate U
            M_entry.configure(state="normal")
            T_entry.configure(state="normal")
            U_entry.configure(state="disabled")

    def update_particle_controls(self):
        """Enable the selected particle quantity and disable the calculated one."""
        if not all(
            k in self.setup_entries
            for k in ("Nppc", "nEquivalentParticles")
        ):
            return

        Nppc_entry = self.setup_entries["Nppc"]
        nEq_entry = self.setup_entries["nEquivalentParticles"]

        if self.particle_mode.get() == "Nppc":
            Nppc_entry.configure(state="normal")
            nEq_entry.configure(state="disabled")
        else:
            Nppc_entry.configure(state="disabled")
            nEq_entry.configure(state="normal")

    def resolve_flow_state(self):
        """
        Resolve T, U, sound speed and Mach number according to the selected
        velocity/Mach mode. Writes the computed quantity back into its field.
        Returns (T, U, a, M, R).
        """
        mass = get_float(self.vars, ALL_LABELS, "mass")
        gamma = get_float(self.vars, ALL_LABELS, "gamma")

        if mass <= 0:
            raise ValueError("Molecular mass must be positive.")
        if gamma <= 0:
            raise ValueError("Specific heat ratio gamma must be positive.")

        R = K_B / mass

        # Direct velocity mode: T and U are inputs, M is output
        if self.velocity_mode.get() == "U":
            T = get_float(self.vars, ALL_LABELS, "T")
            U = get_float(self.vars, ALL_LABELS, "U")

            if T <= 0:
                raise ValueError("Temperature must be positive.")
            if U < 0:
                raise ValueError("Velocity cannot be negative.")

            a = sound_speed(gamma, R, T)
            M = U / a

            self.vars["M"].set(f"{M:.6g}")
            return T, U, a, M, R

        # Mach mode: M is input
        M = get_float(self.vars, ALL_LABELS, "M")
        if M <= 0:
            raise ValueError("Mach number must be positive.")

        # M + U -> calculate T
        if self.mach_constraint_mode.get() == "U":
            U = get_float(self.vars, ALL_LABELS, "U")

            if U < 0:
                raise ValueError("Velocity cannot be negative.")

            a = U / M
            T = a ** 2 / (gamma * R)

            self.vars["T"].set(f"{T:.6g}")

        # M + T -> calculate U
        else:
            T = get_float(self.vars, ALL_LABELS, "T")

            if T <= 0:
                raise ValueError("Temperature must be positive.")

            a = sound_speed(gamma, R, T)
            U = M * a

            self.vars["U"].set(f"{U:.6g}")

        return T, U, a, M, R
    
    def auto_recovery_temp(self):
        try:
            mass = get_float(self.vars, ALL_LABELS, "mass")
            gamma = get_float(self.vars, ALL_LABELS, "gamma")
            Pr = get_float(self.vars, ALL_LABELS, "Pr")

            T, U, a, M, R = self.resolve_flow_state()

            Tr = recovery_temperature(T, gamma, M, Pr)
            self.vars["Tw"].set(f"{Tr:.2f}")
            messagebox.showinfo("Recovery Temperature", f"Mach = {fmt(M)}\nRecovery T = {fmt(Tr)} K\n\nFilled into T_w field")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def calculate_setup(self):
        lines = []
        try:
            # Read rarefaction coefficient
            rarefaction_str = self.rarefaction_var.get().strip()
            rarefaction = float(rarefaction_str) if rarefaction_str else 1.0
            if rarefaction <= 0:
                rarefaction = 1.0
            
            fluid_name = self.fluid_name_var.get().strip()
            if not fluid_name:
                fluid_name = "Unknown"
            
            mass = get_float(self.vars, ALL_LABELS, "mass")
            dref = get_float(self.vars, ALL_LABELS, "dref")
            omega = get_float(self.vars, ALL_LABELS, "omega")
            Tref = get_float(self.vars, ALL_LABELS, "Tref")
            gamma = get_float(self.vars, ALL_LABELS, "gamma")
            Pr = get_float(self.vars, ALL_LABELS, "Pr")

            # Resolve T, U, a and M from the selected flow-speed mode
            T, U, a, M, R = self.resolve_flow_state()

            # Density / pressure (evaluated after the resolved temperature)
            if self.density_mode.get() == "P":
                P_input = get_float(self.vars, ALL_LABELS, "P")
                P = P_input * rarefaction
                if P <= 0:
                    raise ValueError("Pressure must be positive.")
                n = P / (K_B * T)
            else:
                n_input = get_float(self.vars, ALL_LABELS, "n")
                n = n_input * rarefaction
                if n <= 0:
                    raise ValueError("Number density must be positive.")
                P = n * K_B * T
            
            rho = n * mass

            sigma = vhs_cross_section(dref, Tref, omega, T)
            lam = mean_free_path(n, sigma)
            c_bar = mean_thermal_speed(mass, T)
            tau = lam / c_bar
            mu_ref = vhs_mu_ref(mass, dref, omega, Tref)
            mu = vhs_mu(mu_ref, Tref, omega, T)
            
            lines.append("═" * 70)
            lines.append(f" DSMC SETUP CALCULATION RESULTS - {fluid_name}")
            lines.append("═" * 70)
            if rarefaction != 1.0:
                lines.append(f"⚠️  Rarefaction coefficient: {rarefaction} (density scaled by {rarefaction}×)")
            lines.append("")
            
            lines.append("─" * 70)
            lines.append("🌊 FLOW STATE")
            lines.append("─" * 70)
            lines.append(f"  Pressure, P [Pa]               = {fmt(P)}")
            lines.append(f"  Number density, n [m⁻³]        = {fmt(n)}")
            lines.append(f"  Mass density,  [kg/m³]        = {fmt(rho)}")
            lines.append(f"  Temperature, T [K]             = {fmt(T)}")
            lines.append(f"  Velocity, U [m/s]              = {fmt(U)}")
            lines.append(f"  Sound speed, a [m/s]           = {fmt(a)}")
            lines.append(f"  Mach number, M [-]             = {fmt(M)}")
            
            lines.append("")
            lines.append("─" * 70)
            lines.append("🔬 VHS MOLECULAR MODEL PROPERTIES")
            lines.append("─" * 70)
            lines.append(f"  Cross-section, σ [m²]          = {fmt(sigma)}")
            lines.append(f"  Mean free path, λ [m]          = {fmt(lam)}")
            lines.append(f"  Mean thermal speed, c̄ [m/s]    = {fmt(c_bar)}")
            lines.append(f"  Mean collision time, τ [s]     = {fmt(tau)}")
            lines.append(f"  Viscosity, μ [Pa·s]            = {fmt(mu)}")
            
            LKn = get_float(self.vars, ALL_LABELS, "LKn")
            Kn = lam / LKn
            LRe = get_float(self.vars, ALL_LABELS, "LRe")
            Re = rho * U * LRe / mu
            
            lines.append("")
            lines.append("─" * 70)
            lines.append("📐 DIMENSIONLESS NUMBERS")
            lines.append("─" * 70)
            lines.append(f"  Reference length (Kn), L_Kn [m] = {fmt(LKn)}")
            lines.append(f"  Knudsen number, Kn [-]         = {fmt(Kn)}")
            lines.append(f"  Reference length (Re), L_Re [m] = {fmt(LRe)}")
            lines.append(f"  Reynolds number, Re [-]        = {fmt(Re)}")
            
            if Kn < 0.01:
                lines.append("  → Continuum regime (CFD appropriate)")
            elif Kn < 0.1:
                lines.append("  → Slip flow regime")
            elif Kn < 10:
                lines.append("  → Transitional regime (DSMC required)")
            else:
                lines.append("  → Free molecular flow")
            
            # Mesh & particle weighting
            if self.volume_mode.get() == "domain":
                Vdomain = get_float(self.vars, ALL_LABELS, "Vdomain")
                Ncells = int(get_float(self.vars, ALL_LABELS, "Ncells"))
                if Vdomain <= 0:
                    raise ValueError("Domain volume must be positive.")
                if Ncells <= 0:
                    raise ValueError("Number of cells must be positive.")
                Vcell = Vdomain / Ncells
            else:
                Vcell = get_float(self.vars, ALL_LABELS, "Vcell")
                if Vcell <= 0:
                    raise ValueError("Cell volume must be positive.")
            
            dx = Vcell ** (1.0 / 3.0)
            N_real = n * Vcell

            # Two-way particle weighting
            if self.particle_mode.get() == "Nppc":
                Nppc = get_float(self.vars, ALL_LABELS, "Nppc")
                if Nppc <= 0:
                    raise ValueError("Particles per cell must be positive.")
                nEq = N_real / Nppc
                self.vars["nEquivalentParticles"].set(f"{nEq:.6g}")
            else:
                nEq = get_float(self.vars, ALL_LABELS, "nEquivalentParticles")
                if nEq <= 0:
                    raise ValueError("nEquivalentParticles must be positive.")
                Nppc = N_real / nEq
                self.vars["Nppc"].set(f"{Nppc:.6g}")
            
            lines.append("")
            lines.append("─" * 70)
            lines.append("🔲 MESH & PARTICLE STATISTICS")
            lines.append("─" * 70)
            lines.append(f"  Cell volume, V_cell [m³]       = {fmt(Vcell)}")
            lines.append(f"  Cell size, Δx [m]              = {fmt(dx)}")
            lines.append(f"  Real molecules per cell        = {fmt(N_real)}")
            lines.append(f"  Particles per cell, Nppc       = {fmt(Nppc)}")
            lines.append(f"  nEquivalentParticles           = {fmt(nEq)}")
            
            if dx > lam:
                lines.append(f"  ️  WARNING: Cell size ({fmt(dx)} m) > mean free path ({fmt(lam)} m)!")
                lines.append("     Consider refining mesh for better resolution.")
            
            f1 = get_float(self.vars, ALL_LABELS, "f1")
            f2 = get_float(self.vars, ALL_LABELS, "f2")
            dt_coll = f1 * tau
            dt_trans = f2 * dx / (U + c_bar)
            dt = min(dt_coll, dt_trans)
            
            lines.append("")
            lines.append("─" * 70)
            lines.append("⏱️  TIME STEP SELECTION")
            lines.append("─" * 70)
            lines.append(f"  Mean collision time, τ [s]     = {fmt(tau)}")
            lines.append(f"  dt (collision limit, f₁={f1})   = {fmt(dt_coll)} s")
            lines.append(f"  dt (transit limit, f₂={f2})     = {fmt(dt_trans)} s")
            lines.append(f"  ✅ RECOMMENDED dt [s]           = {fmt(dt)}")
            
            if self.viscous_var.get():
                try:
                    x = get_float(self.vars, ALL_LABELS, "x")
                    Tw_str = self.vars["Tw"].get().strip()
                    if Tw_str:
                        Tw = float(Tw_str)
                    else:
                        Tw = recovery_temperature(T, gamma, M, Pr)
                    
                    Tstar = eckert_reference_temperature(T, M, Tw)
                    mu_star = vhs_mu(mu_ref, Tref, omega, Tstar)
                    rho_star = P / (R * Tstar)
                    Rex = rho_star * U * x / mu_star
                    
                    delta = 5.0 * x / math.sqrt(Rex)
                    theta = 0.664 * x / math.sqrt(Rex)
                    delta_star = 1.721 * x / math.sqrt(Rex)
                    
                    lines.append("")
                    lines.append("─" * 70)
                    lines.append("🔵 BOUNDARY LAYER ESTIMATE (Flat Plate)")
                    lines.append("─" * 70)
                    lines.append(f"  Distance from edge, x [m]      = {fmt(x)}")
                    lines.append(f"  Wall temperature, T_w [K]      = {fmt(Tw)}")
                    lines.append(f"  Reference temperature, T* [K]  = {fmt(Tstar)}")
                    lines.append(f"  Local Reynolds number, Re_x    = {fmt(Rex)}")
                    lines.append(f"  BL thickness (99%), δ [m]      = {fmt(delta)}")
                    lines.append(f"  Displacement thickness, δ* [m] = {fmt(delta_star)}")
                    lines.append(f"  Momentum thickness, θ [m]      = {fmt(theta)}")
                    
                    Kn_x = lam / x
                    lines.append(f"  Local Knudsen number, Kn_x     = {fmt(Kn_x)}")
                    if Kn_x > 0.1:
                        lines.append("  ⚠️  WARNING: Kn_x > 0.1 - continuum BL theory may be inaccurate")
                except:
                    pass
            
            lines.append("")
            lines.append("═" * 70)
            
            self.last_results = {"n": n, "nEquivalentParticles": nEq, "P": P, "fluid": fluid_name}
            self.result_text.configure(state="normal")
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", "\n".join(lines))
            self.result_text.configure(state="disabled")
            
        except Exception as e:
            messagebox.showerror("❌ Input Error", str(e))
    
    def reset_setup(self):
        defaults = {
            "mass": "66.3e-27", "dref": "4.17e-10", "omega": "0.81", "Tref": "298.15",
            "gamma": "1.667", "Pr": "0.667", "T": "150", "U": "736.5", "M": "3.0",
            "P": "1.0", "n": "4e20", "Vdomain": "1.0", "Ncells": "100000", 
            "Vcell": "", "Nppc": "20", "nEquivalentParticles": "",
            "LKn": "0.5", "LRe": "0.5", 
            "compression": "1.0", "f1": "0.2", "f2": "0.3", "x": "0.1", 
            "Tw": "150", "rarefaction": "1.0"
        }
        for key, val in defaults.items():
            if key in self.vars:
                self.vars[key].set(val)
        
        self.fluid_name_var.set("Argon")
        self.density_mode.set("P")
        self.velocity_mode.set("U")
        self.mach_constraint_mode.set("U")
        self.volume_mode.set("domain")
        self.particle_mode.set("Nppc")
        self.viscous_var.set(True)

        self.update_flow_controls()
        self.update_particle_controls()
    
    def copy_openfoam(self):
        if not self.last_results:
            messagebox.showwarning("️ Warning", "Calculate first!")
            return
        snippet = f"""// DSMC Setup - Generated by DSMC Calculator
// Fluid: {self.last_results.get('fluid', 'Unknown')}
// Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

nEquivalentParticles    {fmt(self.last_results['nEquivalentParticles'])};

FreeStreamCoeffs
{{
    numberDensities
    {{
        Ar      {fmt(self.last_results['n'])};
    }};
}}"""
        self.clipboard_clear()
        self.clipboard_append(snippet)
        messagebox.showinfo("✅ Copied", "OpenFOAM snippet copied to clipboard!")
    
    def save_report(self):
        content = self.result_text.get("1.0", "end")
        if not content.strip() or "Enter values" in content:
            messagebox.showwarning("⚠️ Warning", "Calculate first!")
            return
        fname = filedialog.asksaveasfilename(defaultextension=".txt", 
                                              filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                                              initialfile=f"DSMC_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        if fname:
            with open(fname, "w") as f:
                f.write(f"DSMC Setup Calculator - Report\n")
                f.write(f"Fluid: {self.fluid_name_var.get()}\n")
                f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*70 + "\n\n")
                f.write(content)
            messagebox.showinfo("✅ Saved", f"Report saved to:\n{fname}")
    
    def build_kn_tab(self, parent):
        main = ttk.Frame(parent)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left/input panel
        left = ScrollableFrame(main)
        left.pack(side="left", fill="both", padx=(0, 10))
        left.configure(width=600)
        left.pack_propagate(False)

        left_frame = left.scrollable_frame

        # Right/results panel
        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True)
        
        info = ttk.Label(left_frame, text="Calculate required number density and pressure to achieve a target Knudsen number", wraplength=550)
        info.pack(fill="x", pady=10)
        
        frame = ttk.LabelFrame(left_frame, text="🎯 Solve for Kn - Enter Parameters", padding=10)
        frame.pack(fill="both", expand=True, pady=5)
        
        # Add hints to Kn fields
        for i, (key, label, default, unit) in enumerate(KN_FIELDS):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=38, anchor="w").pack(side="left")
            var = tk.StringVar(value=default)
            self.kn_vars[key] = var
            entry = ttk.Entry(row, textvariable=var, width=22)
            entry.pack(side="left", padx=10)
            if unit:
                ttk.Label(row, text=unit, width=12, anchor="w", foreground='gray').pack(side="left")
            if key == "Kn_target":
                HintIcon(row, "kn").pack(side="left", padx=2)
            elif key == "Nppc":
                HintIcon(row, "nppc").pack(side="left", padx=2)
        
        ttk.Button(left_frame, text="📊 CALCULATE REQUIRED n/P", command=self.calculate_kn).pack(pady=15)
        
        ttk.Label(right, text="📈 RESULTS", font=("Arial", 14, "bold")).pack(anchor="w")
        self.kn_result = scrolledtext.ScrolledText(right, wrap="word", font=("Courier", 13),
                                                   bg="white", relief="flat", padx=10, pady=10)
        self.kn_result.pack(fill="both", expand=True, pady=10)
        self.kn_result.insert("1.0", "Enter target Kn and parameters, then click CALCULATE")
        self.kn_result.configure(state="disabled")
    
    def calculate_kn(self):
        try:
            mass = get_float(self.kn_vars, ALL_LABELS, "mass")
            dref = get_float(self.kn_vars, ALL_LABELS, "dref")
            omega = get_float(self.kn_vars, ALL_LABELS, "omega")
            Tref = get_float(self.kn_vars, ALL_LABELS, "Tref")
            T = get_float(self.kn_vars, ALL_LABELS, "T")
            LKn = get_float(self.kn_vars, ALL_LABELS, "LKn")
            Kn_target = get_float(self.kn_vars, ALL_LABELS, "Kn_target")
            
            sigma = vhs_cross_section(dref, Tref, omega, T)
            lam_target = Kn_target * LKn
            n_req = 1.0 / (math.sqrt(2.0) * sigma * lam_target)
            P_req = n_req * K_B * T
            rho_req = n_req * mass
            
            c_bar = mean_thermal_speed(mass, T)
            tau = lam_target / c_bar
            
            lines = ["═" * 70]
            lines.append(" SOLVE FOR KNUDSEN NUMBER")
            lines.append("═" * 70)
            lines.append("")
            lines.append("─" * 70)
            lines.append("INPUT PARAMETERS")
            lines.append("─" * 70)
            lines.append(f"  Target Knudsen number, Kn [-]  = {Kn_target}")
            lines.append(f"  Reference length, L_Kn [m]     = {fmt(LKn)}")
            lines.append(f"  Temperature, T [K]             = {fmt(T)}")
            lines.append("")
            lines.append("─" * 70)
            lines.append("CALCULATED RESULTS")
            lines.append("─" * 70)
            lines.append(f"  Required mean free path, λ [m] = {fmt(lam_target)}")
            lines.append(f"  Required number density [m⁻³]  = {fmt(n_req)}")
            lines.append(f"  Required pressure [Pa]         = {fmt(P_req)}")
            lines.append(f"  Required mass density [kg/m³]  = {fmt(rho_req)}")
            lines.append(f"  Mean thermal speed [m/s]       = {fmt(c_bar)}")
            lines.append(f"  Mean collision time [s]        = {fmt(tau)}")
            
            try:
                Vcell = get_float(self.kn_vars, ALL_LABELS, "Vcell")
                Nppc = get_float(self.kn_vars, ALL_LABELS, "Nppc")
                N_real = n_req * Vcell
                nEq = N_real / Nppc
                lines.append("")
                lines.append("─" * 70)
                lines.append("MESH STATISTICS")
                lines.append("─" * 70)
                lines.append(f"  Cell volume, V_cell [m³]       = {fmt(Vcell)}")
                lines.append(f"  Real molecules per cell        = {fmt(N_real)}")
                lines.append(f"  nEquivalentParticles           = {fmt(nEq)}")
            except:
                pass
            
            lines.append("")
            lines.append("═" * 70)
            
            self.kn_result.configure(state="normal")
            self.kn_result.delete("1.0", "end")
            self.kn_result.insert("1.0", "\n".join(lines))
            self.kn_result.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("❌ Error", str(e))
    
    def build_re_tab(self, parent):
        main = ttk.Frame(parent)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left/input panel
        left = ScrollableFrame(main)
        left.pack(side="left", fill="both", padx=(0, 10))
        left.configure(width=600)
        left.pack_propagate(False)

        left_frame = left.scrollable_frame

        # Right/results panel
        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True)
        
        info = ttk.Label(left_frame, text="Calculate required velocity to achieve a target Reynolds number", wraplength=550)
        info.pack(fill="x", pady=10)
        
        frame = ttk.LabelFrame(left_frame, text="🎯 Solve for Re - Enter Parameters", padding=10)
        frame.pack(fill="both", expand=True, pady=5)
        
        density_frame = ttk.Frame(frame)
        density_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(density_frame, text="Specify density by:").pack(side="left")
        ttk.Radiobutton(density_frame, text="Pressure (P)", variable=self.re_density_mode, value="P").pack(side="left", padx=10)
        ttk.Radiobutton(density_frame, text="Number density (n)", variable=self.re_density_mode, value="n").pack(side="left")
        
        # Add fields with hints
        for i, (key, label, default, unit) in enumerate(RE_FIELDS):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=38, anchor="w").pack(side="left")
            var = tk.StringVar(value=default)
            self.re_vars[key] = var
            entry = ttk.Entry(row, textvariable=var, width=22)
            entry.pack(side="left", padx=10)
            if unit:
                ttk.Label(row, text=unit, width=12, anchor="w", foreground='gray').pack(side="left")
            if key == "Re_target":
                HintIcon(row, "re").pack(side="left", padx=2)
            elif key == "Nppc":
                HintIcon(row, "nppc").pack(side="left", padx=2)
        
        ttk.Button(left_frame, text="📊 CALCULATE REQUIRED VELOCITY", command=self.calculate_re).pack(pady=15)
        
        ttk.Label(right, text="📈 RESULTS", font=("Arial", 14, "bold")).pack(anchor="w")
        self.re_result = scrolledtext.ScrolledText(right, wrap="word", font=("Courier", 13),
                                                   bg="white", relief="flat", padx=10, pady=10)
        self.re_result.pack(fill="both", expand=True, pady=10)
        self.re_result.insert("1.0", "Enter target Re and parameters, then click CALCULATE")
        self.re_result.configure(state="disabled")
    
    def calculate_re(self):
        try:
            mass = get_float(self.re_vars, ALL_LABELS, "mass")
            dref = get_float(self.re_vars, ALL_LABELS, "dref")
            omega = get_float(self.re_vars, ALL_LABELS, "omega")
            Tref = get_float(self.re_vars, ALL_LABELS, "Tref")
            gamma = get_float(self.re_vars, ALL_LABELS, "gamma")
            T = get_float(self.re_vars, ALL_LABELS, "T")
            LRe = get_float(self.re_vars, ALL_LABELS, "LRe")
            Re_target = get_float(self.re_vars, ALL_LABELS, "Re_target")
            
            if self.re_density_mode.get() == "P":
                P = get_float(self.re_vars, ALL_LABELS, "P")
                n = P / (K_B * T)
            else:
                n = get_float(self.re_vars, ALL_LABELS, "n")
                P = n * K_B * T
            
            rho = n * mass
            mu_ref = vhs_mu_ref(mass, dref, omega, Tref)
            mu = vhs_mu(mu_ref, Tref, omega, T)
            
            U_req = Re_target * mu / (rho * LRe)
            R = K_B / mass
            a = sound_speed(gamma, R, T)
            M_req = U_req / a
            
            lines = ["═" * 70]
            lines.append("🎯 SOLVE FOR REYNOLDS NUMBER")
            lines.append("═" * 70)
            lines.append("")
            lines.append("─" * 70)
            lines.append("INPUT PARAMETERS")
            lines.append("─" * 70)
            lines.append(f"  Target Reynolds number, Re [-] = {Re_target}")
            lines.append(f"  Reference length, L_Re [m]     = {fmt(LRe)}")
            lines.append(f"  Temperature, T [K]             = {fmt(T)}")
            lines.append(f"  Pressure, P [Pa]               = {fmt(P)}")
            lines.append(f"  Number density, n [m³]        = {fmt(n)}")
            lines.append("")
            lines.append("─" * 70)
            lines.append("CALCULATED RESULTS")
            lines.append("─" * 70)
            lines.append(f"  Mass density, ρ [kg/m³]        = {fmt(rho)}")
            lines.append(f"  Viscosity, μ [Pa·s]            = {fmt(mu)}")
            lines.append(f"  ✅ Required velocity [m/s]      = {fmt(U_req)}")
            lines.append(f"  Sound speed, a [m/s]           = {fmt(a)}")
            lines.append(f"  Resulting Mach number, M [-]   = {fmt(M_req)}")
            
            if M_req < 0.05:
                lines.append("")
                lines.append("  ⚠️  WARNING: Very low Mach number (M < 0.05)")
                lines.append("     This Re may not be reachable in supersonic/hypersonic flow")
                lines.append("     without changing T, n, or L_Re")
            elif M_req > 30:
                lines.append("")
                lines.append("  ️  WARNING: Extremely high Mach number (M > 30)")
                lines.append("     Verify this is physically realistic for your facility")
            
            try:
                Vcell = get_float(self.re_vars, ALL_LABELS, "Vcell")
                Nppc = get_float(self.re_vars, ALL_LABELS, "Nppc")
                dx = Vcell ** (1/3)
                N_real = n * Vcell
                nEq = N_real / Nppc
                
                lam = mean_free_path(n, vhs_cross_section(dref, Tref, omega, T))
                c_bar = mean_thermal_speed(mass, T)
                tau = lam / c_bar
                
                lines.append("")
                lines.append("─" * 70)
                lines.append("MESH & TIME STEP INFO")
                lines.append("─" * 70)
                lines.append(f"  Cell volume, V_cell [m³]       = {fmt(Vcell)}")
                lines.append(f"  Real molecules per cell        = {fmt(N_real)}")
                lines.append(f"  nEquivalentParticles           = {fmt(nEq)}")
                lines.append(f"  Mean collision time, τ [s]     = {fmt(tau)}")
                
                f1 = get_float(self.re_vars, ALL_LABELS, "f1", required=False, default=0.2)
                f2 = get_float(self.re_vars, ALL_LABELS, "f2", required=False, default=0.3)
                dt_coll = f1 * tau
                dt_trans = f2 * dx / (U_req + c_bar)
                dt = min(dt_coll, dt_trans)
                
                lines.append(f"  Recommended dt [s]             = {fmt(dt)}")
            except:
                pass
            
            lines.append("")
            lines.append("═" * 70)
            
            self.re_result.configure(state="normal")
            self.re_result.delete("1.0", "end")
            self.re_result.insert("1.0", "\n".join(lines))
            self.re_result.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("❌ Error", str(e))

if __name__ == "__main__":
    app = DSMCCalculator()
    app.mainloop()
