"""
Object-Oriented F1 Race Strategy Simulator
Dynamic Weather Transitions (Dry -> Wet) & Tire Crossover Analysis
"""

from dataclasses import dataclass
import os
from typing import Dict, List, Optional

import fastf1
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Setup cache
os.makedirs("f1_cache", exist_ok=True)
fastf1.Cache.enable_cache("f1_cache")


@dataclass
class TyreCompound:
    """Models pace, wear, and wetness sensitivity per compound."""
    name: str
    base_pace_delta: float  # Pace offset in dry conditions (seconds)
    deg_per_lap: float
    min_wetness: float      # Minimum track wetness % where tire is effective
    max_wetness: float      # Maximum track wetness % before tire loses grip
    wet_sensitivity: float  # Penalty coefficient when outside optimal wetness window

    def get_lap_delta(self, age: int, track_wetness: float) -> float:
        """Calculates pace penalty based on tire age AND track moisture."""
        # Age wear penalty
        age_penalty = self.deg_per_lap * (age ** 1.05)

        # Moisture penalty (exponential loss if outside compound window)
        moisture_penalty = 0.0
        if track_wetness < self.min_wetness:
            moisture_penalty = self.wet_sensitivity * ((self.min_wetness - track_wetness) ** 2)
        elif track_wetness > self.max_wetness:
            moisture_penalty = self.wet_sensitivity * ((track_wetness - self.max_wetness) ** 2)

        return self.base_pace_delta + age_penalty + moisture_penalty


class WeatherProfile:
    """Simulates track wetness progression across the race distance."""
    def __init__(self, total_laps: int, rain_start_lap: Optional[int] = 12, peak_wetness: float = 80.0):
        self.total_laps = total_laps
        self.rain_start_lap = rain_start_lap
        self.peak_wetness = peak_wetness

    def get_wetness_for_lap(self, lap: int) -> float:
        """Returns track wetness percentage (0% = Bone Dry, 100% = Torrential Rain)."""
        if self.rain_start_lap is None or lap < self.rain_start_lap:
            return 0.0
        
        # Linear transition up to peak wetness over 10 laps, then stabilization
        laps_into_rain = lap - self.rain_start_lap
        wetness = min(self.peak_wetness, laps_into_rain * 10.0)
        return round(wetness, 1)


class ReactiveCar:
    """Car entity capable of making dynamic pit strategy calls during changing weather."""

    def __init__(
        self,
        driver_id: str,
        base_driver_pace: float,
        start_tyre: TyreCompound,
        available_compounds: Dict[str, TyreCompound],
        planned_pit_lap: Optional[int] = None,
    ):
        self.driver_id = driver_id
        self.base_driver_pace = base_driver_pace
        self.current_tyre = start_tyre
        self.available_compounds = available_compounds
        self.planned_pit_lap = planned_pit_lap
        
        self.tyre_age = 0
        self.total_race_time = 0.0

    def evaluate_crossover(self, track_wetness: float) -> Optional[TyreCompound]:
        """Evaluates whether to pit for Intermediates/Wets based on current track wetness."""
        best_compound = self.current_tyre
        lowest_delta = self.current_tyre.get_lap_delta(self.tyre_age, track_wetness)

        # Check if fresh alternative compound offers > 2.0s pace gain (offsetting pit loss)
        for compound in self.available_compounds.values():
            fresh_delta = compound.get_lap_delta(0, track_wetness)
            if fresh_delta < (lowest_delta - 2.0):
                lowest_delta = fresh_delta
                best_compound = compound

        return best_compound if best_compound != self.current_tyre else None

    def step_lap(
        self, lap: int, track_wetness: float, pit_loss: float, cold_outlap_penalty: float
    ) -> Dict[str, float]:
        
        # Check weather-based reactive pit stop or planned stop
        recommended_tyre = self.evaluate_crossover(track_wetness)
        is_pit_lap = (lap == self.planned_pit_lap) or (recommended_tyre is not None)

        if is_pit_lap and recommended_tyre:
            self.current_tyre = recommended_tyre
            self.tyre_age = 0
            pit_time = pit_loss
        elif is_pit_lap and self.planned_pit_lap == lap:
            # Fallback for planned dry pit stop
            self.current_tyre = self.available_compounds.get("HARD", self.current_tyre)
            self.tyre_age = 0
            pit_time = pit_loss
        else:
            pit_time = 0.0
            self.tyre_age += 1

        is_out_lap = pit_time > 0
        outlap_delta = cold_outlap_penalty if is_out_lap else 0.0

        tyre_delta = self.current_tyre.get_lap_delta(self.tyre_age, track_wetness)
        lap_time = self.base_driver_pace + tyre_delta + pit_time + outlap_delta
        self.total_race_time += lap_time

        return {
            "driver": self.driver_id,
            "lap": lap,
            "lap_time": round(lap_time, 3),
            "total_time": round(self.total_race_time, 3),
            "compound": self.current_tyre.name,
            "track_wetness": track_wetness,
            "is_pit": is_pit_lap,
        }


class WeatherSimulator:
    """Simulates multi-car dynamic race progression under changing weather."""

    def __init__(self, pit_loss: float = 21.5, cold_outlap_penalty: float = 2.0):
        self.pit_loss = pit_loss
        self.cold_outlap_penalty = cold_outlap_penalty

    def run(self, car_a: ReactiveCar, car_b: ReactiveCar, weather: WeatherProfile) -> pd.DataFrame:
        telemetry = []

        for lap in range(1, weather.total_laps + 1):
            wetness = weather.get_wetness_for_lap(lap)

            data_a = car_a.step_lap(lap, wetness, self.pit_loss, self.cold_outlap_penalty)
            data_b = car_b.step_lap(lap, wetness, self.pit_loss, self.cold_outlap_penalty)

            gap_b_to_a = round(data_b["total_time"] - data_a["total_time"], 3)

            telemetry.append({
                "Lap": lap,
                "TrackWetness": wetness,
                f"{car_a.driver_id}_LapTime": data_a["lap_time"],
                f"{car_b.driver_id}_LapTime": data_b["lap_time"],
                f"{car_a.driver_id}_Compound": data_a["compound"],
                f"{car_b.driver_id}_Compound": data_b["compound"],
                "Gap_NOR_to_VER": gap_b_to_a,
                "Leader": car_a.driver_id if gap_b_to_a > 0 else car_b.driver_id,
            })

        return pd.DataFrame(telemetry)


def plot_weather_simulation(df: pd.DataFrame):
    """Plots track wetness, lap pace, and tire compound crossover points."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    # Plot 1: Lap Times & Weather Overlay
    ax1.plot(df["Lap"], df["NOR_LapTime"], label="NOR Lap Time", color="#FF8000", lw=2)
    ax1.plot(df["Lap"], df["VER_LapTime"], label="VER Lap Time", color="#3671C6", lw=2)
    ax1.set_ylabel("Lap Time (s)")
    ax1.set_title("F1 Dynamic Weather Crossover & Strategy Simulator")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper left")

    # Secondary Y-axis for Track Wetness %
    ax1_twin = ax1.twinx()
    ax1_twin.plot(df["Lap"], df["TrackWetness"], label="Track Wetness %", color="cyan", linestyle=":", lw=2)
    ax1_twin.set_ylabel("Track Wetness (%)", color="cyan")

    # Plot 2: Gap Evolution
    ax2.plot(df["Lap"], df["Gap_NOR_to_VER"], color="#4CAF50", lw=2.5, label="NOR Gap to VER")
    ax2.axhline(0, color="white", linestyle="--", alpha=0.7)
    ax2.set_xlabel("Lap Number")
    ax2.set_ylabel("Gap (Seconds)")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend()

    plt.tight_layout()
    plt.savefig("weather_undercut_simulation.png", dpi=300)
    print("📈 Dynamic weather chart saved as 'weather_undercut_simulation.png'!")
    plt.show()


# --- Main Execution Script ---
if __name__ == "__main__":
    # Define Tire Compounds across weather spectrum
    compounds = {
        "MEDIUM": TyreCompound("MEDIUM", base_pace_delta=0.0, deg_per_lap=0.08, min_wetness=0.0, max_wetness=15.0, wet_sensitivity=0.08),
        "HARD": TyreCompound("HARD", base_pace_delta=0.5, deg_per_lap=0.03, min_wetness=0.0, max_wetness=12.0, wet_sensitivity=0.10),
        "INTERMEDIATE": TyreCompound("INTERMEDIATE", base_pace_delta=6.0, deg_per_lap=0.05, min_wetness=15.0, max_wetness=65.0, wet_sensitivity=0.04),
        "WET": TyreCompound("WET", base_pace_delta=14.0, deg_per_lap=0.02, min_wetness=60.0, max_wetness=100.0, wet_sensitivity=0.03),
    }

    # Setup Drivers (Norris reacts immediately on Lap 14 when rain starts; Verstappen delays 2 laps)
    norris = ReactiveCar("NOR", base_driver_pace=85.0, start_tyre=compounds["MEDIUM"], available_compounds=compounds)
    verstappen = ReactiveCar("VER", base_driver_pace=85.0, start_tyre=compounds["MEDIUM"], available_compounds=compounds, planned_pit_lap=17)

    # Setup Weather Profile (Rain starts on Lap 13 and increases wetness)
    weather = WeatherProfile(total_laps=30, rain_start_lap=13, peak_wetness=70.0)

    # Run Simulation
    sim = WeatherSimulator(pit_loss=21.5, cold_outlap_penalty=2.0)
    results = sim.run(norris, verstappen, weather)

    print(results[["Lap", "TrackWetness", "NOR_Compound", "VER_Compound", "NOR_LapTime", "VER_LapTime", "Gap_NOR_to_VER"]].head(25).to_string(index=False))
    plot_weather_simulation(results)
