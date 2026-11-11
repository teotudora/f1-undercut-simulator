# 🏎️ F1 Pit Stop, Undercut & Dynamic Weather Strategy Simulator

![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Fast-F1](https://img.shields.io/badge/dependency-Fast--F1-red.svg)
![SciPy](https://img.shields.io/badge/math-SciPy-00549E.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

An object-oriented Formula 1 race strategy engine written in Python. This framework models lap pace progression, pit lane time loss, cold out-lap penalties, non-linear tyre degradation curves, real session telemetry parameter fitting via `FastF1`, and dynamic track weather crossovers ($\text{Dry} \rightarrow \text{Intermediate} \rightarrow \text{Wet}$).

---

## 🚀 Key Features

- **Object-Oriented Strategy Architecture:** Clean, modular encapsulation using custom `TyreCompound`, `ReactiveCar`, `WeatherProfile`, and `WeatherSimulator` classes.
- **Dynamic Weather & Crossover Strategy:** Models compound grip windows and exponential pace decay when running slick tyres on damp/wet surfaces to calculate mathematical pit-stop crossover thresholds.
- **Telemetry Curve Fitting:** Scrapes real Grand Prix session timing streams via `FastF1` and fits non-linear compound degradation parameters using `scipy.optimize.curve_fit`.
- **Continuous Pace Integration:** Derives velocity time deltas over a unified 1-meter spatial grid ($d$):
  $$\Delta t(d) = \int \left( \frac{1}{v_{\text{comp}}(d)} - \frac{1}{v_{\text{ref}}(d)} \right) \mathrm{d}d$$
- **Visual Telemetry Dashboards:** Generates multi-panel Matplotlib charts tracking stint pace decay, track moisture percentage, and real-time head-to-head driver gap evolution.

---

## 📊 Weather Crossover Simulation Output

![F1 Dynamic Weather Crossover & Strategy Simulator](docs/assets/weather_crossover_plot.png)

---

## 🛠️ Quick Start

### 1. Clone & Install
```bash
git clone [https://github.com/teotudora/f1-undercut-simulator.git](https://github.com/teotudora/f1-undercut-simulator.git)
cd f1-undercut-simulator
pip install -r requirements.txt
