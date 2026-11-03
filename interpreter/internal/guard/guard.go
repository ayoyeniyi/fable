// Package guard protects the service when it runs on a public server (docs/BACKEND.md).
//
// Behind Caddy every request arrives from 127.0.0.1, so "is this local?" and "who is this?" must look at the
// X-Forwarded-For header that Caddy sets (it replaces any value a client sends). The limiter spends per-client
// tokens: the routes that start Claude or Blender work cost far more than reading status or fetching files.
package guard

import (
	"net"
	"net/http"
	"strings"
	"sync"
	"time"
)

// ClientIP is the address of the headset: Caddy's X-Forwarded-For when the request came through it, otherwise the
// connection's own address.
func ClientIP(r *http.Request) string {
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		host = r.RemoteAddr
	}
	if ip := net.ParseIP(host); ip != nil && ip.IsLoopback() {
		if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
			parts := strings.Split(xff, ",")
			return strings.TrimSpace(parts[len(parts)-1])
		}
	}
	return host
}

// IsLocal: the request came from this machine directly, not through the proxy (owner-only tools).
func IsLocal(r *http.Request) bool {
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return false
	}
	ip := net.ParseIP(host)
	return ip != nil && ip.IsLoopback() && r.Header.Get("X-Forwarded-For") == "" && r.Header.Get("Forwarded") == ""
}

// Costly lists the routes that start Claude or Blender work.
var Costly = map[string]bool{
	"POST /peek": true, "POST /interpret": true, "POST /chapters/prepare": true, "POST /rooms/prepare": true,
}

// Limits for one client.
type Limits struct {
	CostlyPerHour  float64 // sustained rate of costly requests
	CostlyBurst    float64
	RequestsPerMin float64 // everything else (status polls, file downloads)
	RequestsBurst  float64
}

// Defaults suit a reader: a Peek every minute or two, a chapter every few minutes, status polled every few seconds.
var Defaults = Limits{CostlyPerHour: 60, CostlyBurst: 15, RequestsPerMin: 240, RequestsBurst: 120}

type bucket struct {
	tokens float64
	last   time.Time
}

// Limiter is a per-client token bucket for costly and ordinary requests.
type Limiter struct {
	L   Limits
	mu  sync.Mutex
	b   map[string]*bucket
	now func() time.Time
}

func NewLimiter(l Limits) *Limiter { return &Limiter{L: l, b: map[string]*bucket{}, now: time.Now} }

// Allow spends one token for this client and route kind; false when the client is over its rate.
func (l *Limiter) Allow(client string, costly bool) bool {
	rate, burst, key := l.L.RequestsPerMin/60, l.L.RequestsBurst, "r:"+client
	if costly {
		rate, burst, key = l.L.CostlyPerHour/3600, l.L.CostlyBurst, "c:"+client
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	now := l.now()
	b := l.b[key]
	if b == nil {
		b = &bucket{tokens: burst, last: now}
		l.b[key] = b
		if len(l.b) > 50000 { // forget idle clients rather than grow without bound
			for k, v := range l.b {
				if now.Sub(v.last) > time.Hour {
					delete(l.b, k)
				}
			}
		}
	}
	b.tokens += now.Sub(b.last).Seconds() * rate
	if b.tokens > burst {
		b.tokens = burst
	}
	b.last = now
	if b.tokens < 1 {
		return false
	}
	b.tokens--
	return true
}

// Middleware refuses clients over their rate with 429 (the headset already backs off and retries on 429).
func (l *Limiter) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" {
			next.ServeHTTP(w, r)
			return
		}
		if !l.Allow(ClientIP(r), Costly[r.Method+" "+r.URL.Path]) {
			w.Header().Set("Retry-After", "60")
			http.Error(w, "too many requests from this headset; try again in a minute", http.StatusTooManyRequests)
			return
		}
		next.ServeHTTP(w, r)
	})
}
