-- Local wrapper, 2026-10-09. The full mathematical argument is OpenAI's.
import OAI.Computability.FourierTransform.Main

open OAI.PowerSaving Filter Asymptotics
namespace Race

/-- The endpoint is excluded: no pure-power bound at 2/10^11 is asserted. -/
theorem frontier : ∀ s : ℚ, s < (1 : ℚ) / 50000000000 →
    ∃ order solve W, DFTProgram order solve W ∧
      (fun n : ℕ => (W n : ℝ)) =O[atTop]
        (fun n : ℕ => (n : ℝ) * (Real.log (n : ℝ)) ^ (1 - (s : ℝ))) := by
  intro s hs
  obtain ⟨order, solve, a, b, hprogram, _⟩ := RAM.Bench.flagshipOne
  refine ⟨order, solve, RAM.Bench.lunch a b id, hprogram, ?_⟩
  have hs' : (s : ℝ) < (1 : ℝ) / 50000000000 := by
    have h := Rat.cast_strictMono (K := ℝ) hs
    simpa only [Rat.cast_div, Rat.cast_one, Rat.cast_ofNat] using h
  have ha : alpha = 1 - (1 : ℝ) / 50000000000 := by norm_num [alpha]
  have hv : alpha < 1 - (s : ℝ) := by rw [ha]; linarith
  have hwork := Skies.lunch_big (N := id) a b
    (fun n => ⟨le_rfl, by dsimp; omega⟩)
  exact (hwork.trans_isLittleO (Skies.flight_little hv)).isBigO

end Race
