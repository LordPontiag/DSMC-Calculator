# DSMC-Calculator
A graphical calculator for DSMC and rarefied gas dynamics calculations.
<img width="825" height="520" alt="image" src="https://github.com/user-attachments/assets/7831f46b-dc63-4ec4-9263-e63254c3f335" />

A lightweight, physics-based engineering tool for the **preliminary design and numerical setup** of Direct Simulation Monte Carlo (DSMC) simulations. It bridges macroscopic flow conditions (pressure, temperature, velocity) with molecular and numerical scales (mean free path, cell size, time step, particle weight).

## Core Features

- **Thermodynamics**: Calculates pressure, number density, mass density, speed of sound, and specific gas constant.
- **VHS Molecular Model**: Computes collision cross-sections, mean free path, mean thermal speed, collision time, and dynamic viscosity.
- **Dimensionless Parameters**: Evaluates Knudsen number (flow regime) and Reynolds number.
- **Inverse Design**:
  - Target `Kn` → Required `n` & `P`.
  - Target `Re` → Required `U` & `M`.
- **DSMC Discretization**: Suggests cell volume, cell dimension (`Δx`), real molecules per cell, and particle statistical weight (`Neq`).
- **Time-Step Guidance**: Computes collision-limited and transit-limited time steps with safety factors.
- **Boundary-Layer Estimates**: Provides recovery temperature, Eckert reference temperature, and flat-plate thickness (`δ`, `θ`, `δ*`).

## Quick Start

Provide the macroscopic state (e.g., temperature, pressure, velocity) and characteristic lengths. The tool outputs molecular properties, dimensionless numbers, and recommended DSMC grid/time parameters.

Easily run executable files on Linux or Windows, or you can run the python script. 

```bash
# Example (pseudo-command)
python dsmc_calc.py

