"""
Object-Oriented F1 Undercut & Race Gap Simulator
Focus Driver: Lando Norris (McLaren) vs Max Verstappen (Red Bull Racing)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import pandas as pd


@dataclass
class TyreCompound:
    """Models tire degradation dynamics."""

    name: str
    base_pace_delta: float  # Seconds relative to ultimate baseline pace
    deg_per_lap: float  # Linear tire degradation penalty per lap
    deg_exponent: float = 1.05  # Non-linear thermal degradation curve coefficient

    def get_lap_delta(self, age: int) -> float:
        """Returns time penalty (in seconds) incurred by tire wear."""
        return self.base_pace_delta + (self.deg_per_lap * (age**self.deg_exponent))


class Car:
    """Represents a driver, their pit strategy, and race progression state."""

    def __init__(
        self,
        driver_id: str,
        base_driver_pace: float,
        start_tyre: TyreCompound,
        pit_lap: Optional[int] = None,
        next_tyre: Optional[TyreCompound] = None,
    ):
        self.driver_id = driver_id
        self.base_driver_pace = base_driver_pace
        self.current_tyre = start_tyre
        self.next_tyre = next_tyre
        self.pit_lap = pit_lap

        self.tyre_age = 0
        self.total_race_time = 0.0

    def step_lap(
        self,
        lap: int,
        pit_loss: float,
        cold_outlap_penalty: float,
        traffic_penalty: float = 0.0,
    ) -> Dict[str, float]:
        """Calculates lap telemetry, tire wear, pit loss, and traffic deltas."""
        is_pit_in = lap == self.pit_lap
        is_out_lap = self.pit_lap is not None and lap == (self.pit_lap + 1)

        # Handle Pit Stop (Tire change & pit lane traversal time)
        if is_pit_in and self.next_tyre:
            self.current_tyre = self.next_tyre
            self.tyre_age = 0
            pit_time = pit_loss
        else:
            pit_time = 0.0
            self.tyre_age += 1

        # Calculate time losses
        tyre_delta = self.current_tyre.get_lap_delta(self.tyre_age)
        outlap_delta = cold_outlap_penalty if is_out_lap else 0.0
        dirty_air = traffic_penalty if (is_out_lap and traffic_penalty > 0) else 0.0

        lap_time = (
            self.base_driver_pace
            + tyre_delta
            + pit_time
            + outlap_delta
            + dirty_air
        )
        self.total_race_time += lap_time

        return {
            "driver": self.driver_id,
            "lap": lap,
            "lap_time": round(lap_time, 3),
            "total_time": round(self.total_race_time, 3),
            "tyre_age": self.tyre_age,
            "compound": self.current_tyre.name,
            "is_pit_lap": is_pit_in,
        }


class UndercutSimulator:
    """Engine simulating lap-by-lap gap evolution between two competing cars."""

    def __init__(
        self,
        pit_loss: float = 21.5,
        cold_outlap_penalty: float = 1.8,
        traffic_penalty: float = 0.0,
    ):
        self.pit_loss = pit_loss
        self.cold_outlap_penalty = cold_outlap_penalty
        self.traffic_penalty = traffic_penalty

    def run(
        self, car_a: Car, car_b: Car, total_laps: int = 30
    ) -> pd.DataFrame:
        telemetry = []

        for lap in range(1, total_laps + 1):
            data_a = car_a.step_lap(
                lap, self.pit_loss, self.cold_outlap_penalty, self.traffic_penalty
            )
            data_b = car_b.step_lap(
                lap, self.pit_loss, self.cold_outlap_penalty, self.traffic_penalty
            )

            # Positive gap means Car A leads, Negative means Car B leads
            gap_b_to_a = round(data_b["total_time"] - data_a["total_time"], 3)

            telemetry.append(
                {
                    "Lap": lap,
                    f"{car_a.driver_id}_LapTime": data_a["lap_time"],
                    f"{car_b.driver_id}_LapTime": data_b["lap_time"],
                    f"{car_a.driver_id}_Compound": data_a["compound"],
                    f"{car_b.driver_id}_Compound": data_b["compound"],
                    "Gap_NOR_to_VER": gap_b_to_a,
                    "Leader": (
                        car_a.driver_id if gap_b_to_a > 0 else car_b.driver_id
                    ),
                }
            )

        return pd.DataFrame(telemetry)


def plot_undercut(df: pd.DataFrame, driver_a: str, driver_b: str):
    """Generates an F1 strategy graph showing lap times and gap evolution."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Plot 1: Lap Times
    ax1.plot(
        df["Lap"], df[f"{driver_a}_LapTime"], label=driver_a, color="#FF8000", lw=2
    )
    ax1.plot(
        df["Lap"], df[f"{driver_b}_LapTime"], label=driver_b, color="#3671C6", lw=2
    )
    ax1.set_ylabel("Lap Time (s)")
    ax1.set_title("F1 Pit Strategy: Lap Pace & Undercut Gap Evolution")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend()

    # Plot 2: Gap Evolution
    ax2.plot(
        df["Lap"], df["Gap_NOR_to_VER"], color="#4CAF50", lw=2.5, label="NOR Gap to VER"
    )
    ax2.axhline(0, color="white", linestyle=":", alpha=0.7)
    ax2.set_xlabel("Lap Number")
    ax2.set_ylabel("Gap (Seconds)")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend()

    plt.tight_layout()
    plt.savefig("undercut_simulation.png", dpi=300)
    print("📈 Chart saved as 'undercut_simulation.png'!")
    plt.show()


# --- Execution Script ---
if __name__ == "__main__":
    # 1. Define Tire Compounds
    mediums = TyreCompound(name="Medium", base_pace_delta=0.3, deg_per_lap=0.08)
    hards = TyreCompound(name="Hard", base_pace_delta=0.7, deg_per_lap=0.03)

    # 2. Setup Cars (Norris pits Lap 14 for undercut; Verstappen reacts on Lap 16)
    norris = Car(
        driver_id="NOR",
        base_driver_pace=85.0,
        start_tyre=mediums,
        pit_lap=14,
        next_tyre=hards,
    )
    verstappen = Car(
        driver_id="VER",
        base_driver_pace=85.0,
        start_tyre=mediums,
        pit_lap=16,
        next_tyre=hards,
    )

    # 3. Run Simulation (21.5s pit loss, 1.8s cold out-lap warm-up delay)
    sim = UndercutSimulator(pit_loss=21.5, cold_outlap_penalty=1.8)
    results = sim.run(norris, verstappen, total_laps=30)

    # 4. Print Results & Plot
    print("\n--- Telemetry Output ---")
    print(results[["Lap", "NOR_LapTime", "VER_LapTime", "Gap_NOR_to_VER", "Leader"]].head(20).to_string(index=False))
    
    plot_undercut(results, "NOR", "VER")
