import ThreeSumApsp.Statements.EndStatement

theorem Race.bound : EndStatement.ThreeSum.SolvedInTime ((2499 : Rat) / 1250) := by
  have exponent : (1.9992 : Rat) = ((2499 : Rat) / 1250) := by norm_num
  rw [← exponent]
  exact ThreeSumApsp.endStatement_theorem_22_3SUM
