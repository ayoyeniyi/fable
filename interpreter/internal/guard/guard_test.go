package guard

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func req(remote, xff string) *http.Request {
	r := httptest.NewRequest("GET", "/rooms/status", nil)
	r.RemoteAddr = remote
	if xff != "" {
		r.Header.Set("X-Forwarded-For", xff)
	}
	return r
}

func TestProxiedRequestsAreNeitherLocalNorAnonymous(t *testing.T) {
	if !IsLocal(req("127.0.0.1:5000", "")) {
		t.Fatal("a direct loopback request is local")
	}
	if IsLocal(req("127.0.0.1:5000", "203.0.113.9")) {
		t.Fatal("a request through the proxy must not count as local")
	}
	if IsLocal(req("203.0.113.9:5000", "")) {
		t.Fatal("a remote request is not local")
	}
	if got := ClientIP(req("127.0.0.1:5000", "198.51.100.1, 203.0.113.9")); got != "203.0.113.9" {
		t.Fatalf("client behind the proxy = %s, want the address the proxy added", got)
	}
	if got := ClientIP(req("203.0.113.7:5000", "10.0.0.1")); got != "203.0.113.7" {
		t.Fatalf("a direct client cannot choose its address with X-Forwarded-For: got %s", got)
	}
}

func TestCostlyRequestsAreLimitedPerClientAndRefill(t *testing.T) {
	l := NewLimiter(Limits{CostlyPerHour: 3600, CostlyBurst: 2, RequestsPerMin: 60, RequestsBurst: 5})
	now := time.Unix(0, 0)
	l.now = func() time.Time { return now }
	if !l.Allow("a", true) || !l.Allow("a", true) || l.Allow("a", true) {
		t.Fatal("burst of 2 costly requests, then refused")
	}
	if !l.Allow("b", true) {
		t.Fatal("another client has its own allowance")
	}
	if !l.Allow("a", false) {
		t.Fatal("ordinary requests have a separate allowance")
	}
	now = now.Add(time.Second)
	if !l.Allow("a", true) {
		t.Fatal("one token a second refills")
	}
}

func TestMiddlewareAnswers429(t *testing.T) {
	l := NewLimiter(Limits{CostlyPerHour: 1, CostlyBurst: 1, RequestsPerMin: 60, RequestsBurst: 5})
	h := l.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	codes := []int{}
	for i := 0; i < 2; i++ {
		r := httptest.NewRequest("POST", "/peek", nil)
		r.RemoteAddr = "203.0.113.9:1"
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		codes = append(codes, w.Code)
	}
	if codes[0] != 200 || codes[1] != 429 {
		t.Fatalf("codes %v, want [200 429]", codes)
	}
}
