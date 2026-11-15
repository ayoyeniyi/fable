package eta

import "testing"

func TestTypical(t *testing.T) {
	if got := Typical(nil, 90); got != 90 {
		t.Fatalf("no runs yet: the seed, got %v", got)
	}
	if got := Typical([]float64{30, 40, 5000}, 90); got != 40 {
		t.Fatalf("the median ignores one long outlier, got %v", got)
	}
	if got := Typical([]float64{30, 40}, 90); got != 35 {
		t.Fatalf("even count: mean of the middle two, got %v", got)
	}
}

func TestRemaining(t *testing.T) {
	if got := Remaining(60, true, 20, 0, 0); got != 40 {
		t.Fatalf("running for 20 of a typical 60: 40 left, got %v", got)
	}
	if got := Remaining(60, true, 90, 0, 0); got != 6 {
		t.Fatalf("overdue: never less than a tenth of a run, got %v", got)
	}
	if got := Remaining(60, false, 0, Left(60, 50), 2); got != 10+120+60 {
		t.Fatalf("queued behind a running job and two others, got %v", got)
	}
}
