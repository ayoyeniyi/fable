// fable-interpreter: turns a passage into a validated SceneScript.
//
//	fable-interpreter validate  --manifest schema/manifest.hall-of-doors.json --book book/passages.json script.json
//	fable-interpreter generate  --scene hall-of-doors --out scripts/hall-of-doors.json
//	fable-interpreter serve     --addr :8787          (POST /interpret {"sceneId":"hall-of-doors"}, GET /health)
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/Thabhelo/fable/interpreter/internal/book"
	"github.com/Thabhelo/fable/interpreter/internal/llm"
	"github.com/Thabhelo/fable/interpreter/internal/script"
)

func loadManifest(root, sceneID string) (*script.Manifest, error) {
	data, err := os.ReadFile(filepath.Join(root, "schema", "manifest."+sceneID+".json"))
	if err != nil {
		return nil, err
	}
	var m script.Manifest
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, err
	}
	return &m, nil
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: fable-interpreter validate|generate|serve [flags]")
		os.Exit(2)
	}
	root := os.Getenv("FABLE_ROOT")
	if root == "" {
		root = "."
	}
	switch os.Args[1] {
	case "validate":
		fs := flag.NewFlagSet("validate", flag.ExitOnError)
		scene := fs.String("scene", "", "scene id (defaults to the script's sceneId)")
		fs.Parse(os.Args[2:])
		if fs.NArg() != 1 {
			log.Fatal("validate needs one script path")
		}
		data, err := os.ReadFile(fs.Arg(0))
		if err != nil {
			log.Fatal(err)
		}
		s, err := script.Parse(data)
		if err != nil {
			fmt.Println("INVALID:", err)
			os.Exit(1)
		}
		if *scene == "" {
			*scene = s.SceneID
		}
		bk, err := book.Load(filepath.Join(root, "book", "passages.json"))
		if err != nil {
			log.Fatal(err)
		}
		sc, err := bk.Scene(*scene)
		if err != nil {
			log.Fatal(err)
		}
		m, err := loadManifest(root, *scene)
		if err != nil {
			log.Fatal(err)
		}
		if errs := script.Validate(s, m, sc.SentenceIDs()); len(errs) > 0 {
			fmt.Println("INVALID:\n- " + strings.Join(errs, "\n- "))
			os.Exit(1)
		}
		fmt.Printf("VALID: %d beats, %d sentences in passage\n", len(s.Beats), sc.SentenceCount)
	case "generate":
		fs := flag.NewFlagSet("generate", flag.ExitOnError)
		scene := fs.String("scene", "hall-of-doors", "scene id")
		out := fs.String("out", "", "output path (default stdout)")
		model := fs.String("model", os.Getenv("FABLE_MODEL"), "Claude model id")
		fs.Parse(os.Args[2:])
		bk, err := book.Load(filepath.Join(root, "book", "passages.json"))
		if err != nil {
			log.Fatal(err)
		}
		sc, err := bk.Scene(*scene)
		if err != nil {
			log.Fatal(err)
		}
		m, err := loadManifest(root, *scene)
		if err != nil {
			log.Fatal(err)
		}
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
		defer cancel()
		s, attempts, err := llm.New(*model).Interpret(ctx, sc, m, "")
		if err != nil {
			for i, a := range attempts {
				fmt.Fprintf(os.Stderr, "--- attempt %d ---\n%s\n", i+1, a)
			}
			log.Fatal(err)
		}
		js, _ := json.MarshalIndent(s, "", "  ")
		if *out == "" {
			fmt.Println(string(js))
		} else if err := os.WriteFile(*out, js, 0o644); err != nil {
			log.Fatal(err)
		} else {
			fmt.Printf("wrote %s (%d beats, %d attempt(s))\n", *out, len(s.Beats), len(attempts))
		}
	case "serve":
		fs := flag.NewFlagSet("serve", flag.ExitOnError)
		addr := fs.String("addr", ":8787", "listen address")
		model := fs.String("model", os.Getenv("FABLE_MODEL"), "Claude model id")
		fs.Parse(os.Args[2:])
		bk, err := book.Load(filepath.Join(root, "book", "passages.json"))
		if err != nil {
			log.Fatal(err)
		}
		dir := llm.New(*model)
		mux := http.NewServeMux()
		mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
			var ms runtime.MemStats
			runtime.ReadMemStats(&ms)
			json.NewEncoder(w).Encode(map[string]any{"ok": true, "heapMB": float64(ms.HeapAlloc) / 1e6, "scenes": len(bk.Scenes)})
		})
		mux.HandleFunc("GET /passages", func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(bk)
		})
		mux.HandleFunc("POST /interpret", func(w http.ResponseWriter, r *http.Request) {
			var req struct {
				SceneID         string `json:"sceneId"`
				ReadingPosition string `json:"readingPosition"` // sentence id the reader has reached
				NoCache         bool   `json:"noCache"`
			}
			if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<16)).Decode(&req); err != nil {
				http.Error(w, err.Error(), 400)
				return
			}
			sc, err := bk.Scene(req.SceneID)
			if err != nil {
				http.Error(w, err.Error(), 404)
				return
			}
			m, err := loadManifest(root, req.SceneID)
			if err != nil {
				http.Error(w, err.Error(), 404)
				return
			}
			cachePath := filepath.Join(root, "out", "cache", req.SceneID+".json")
			if !req.NoCache {
				if cached, err := os.ReadFile(cachePath); err == nil {
					if cs, perr := script.Parse(cached); perr == nil && len(script.Validate(cs, m, sc.SentenceIDs())) == 0 {
						w.Header().Set("Content-Type", "application/json")
						w.Header().Set("X-Fable-Cache", "hit")
						w.Write(cached)
						return
					}
				}
			}
			ctx, cancel := context.WithTimeout(r.Context(), 8*time.Minute)
			defer cancel()
			s, attempts, err := dir.Interpret(ctx, sc, m, req.ReadingPosition)
			if err != nil {
				http.Error(w, fmt.Sprintf("%v (attempts=%d)", err, len(attempts)), 502)
				return
			}
			js, _ := json.MarshalIndent(s, "", "  ")
			os.MkdirAll(filepath.Dir(cachePath), 0o755)
			os.WriteFile(cachePath, js, 0o644)
			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("X-Fable-Cache", "miss")
			w.Write(js)
		})
		log.Printf("fable-interpreter listening on %s (model %s)", *addr, *model)
		log.Fatal(http.ListenAndServe(*addr, mux))
	default:
		log.Fatalf("unknown command %q", os.Args[1])
	}
}
