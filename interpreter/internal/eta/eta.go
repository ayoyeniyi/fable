// Package eta estimates how long a queued or running job has left, from how long this machine's recent jobs took.
// The chapter and room services put it in their status answers (etaSeconds), so the headset can say "about two
// minutes" from timings measured where the work happens rather than from numbers fixed in the app.
package eta

import (
	"math"
	"sort"
)

// Typical is the median of the most recent runs (at most the last 15), or seed when there are none yet. The median,
// not the mean: one build that waited out a network failure must not inflate every estimate after it.
func Typical(recent []float64, seed float64) float64 {
	var xs []float64
	for _, x := range recent {
		if x > 0 && !math.IsInf(x, 0) && !math.IsNaN(x) {
			xs = append(xs, x)
		}
	}
	if len(xs) > 15 {
		xs = xs[len(xs)-15:]
	}
	if len(xs) == 0 {
		return seed
	}
	sort.Float64s(xs)
	m := xs[len(xs)/2]
	if len(xs)%2 == 0 {
		m = (xs[len(xs)/2-1] + xs[len(xs)/2]) / 2
	}
	return m
}

// Remaining is the time left for one job on a single-worker queue: what the running job still needs (never less
// than a tenth of a typical run: a job past its usual time is not about to finish), plus a typical run for each job
// ahead of this one, plus this job's own run (less what it has already run, when it is the running one).
//
//	running   this job is the one running, for elapsed seconds
//	activeLeft  seconds the running job (another one) still needs; 0 when none is running
//	ahead     queued jobs that will run before this one
func Remaining(typical float64, running bool, elapsed float64, activeLeft float64, ahead int) float64 {
	if running {
		return math.Max(typical-elapsed, typical/10)
	}
	return activeLeft + float64(ahead)*typical + typical
}

// Left is what a running job still needs, for the jobs queued behind it.
func Left(typical, elapsed float64) float64 { return math.Max(typical-elapsed, typical/10) }
