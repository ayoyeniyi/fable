// fable-interpreter: turns a passage into a validated SceneScript.
//
//	fable-interpreter validate  --manifest schema/manifest.hall-of-doors.json --book book/passages.json script.json
//	fable-interpreter generate  --scene hall-of-doors [--variant 1] --out scripts/hall-of-doors.json
//	fable-interpreter serve     --addr :8787 [--wait 3s] [--warm]
//	    POST /interpret {"sceneId","readingPosition","noCache","waitSeconds"} -> 200 script (X-Fable-Cache hit|miss) or 202 generating
//	    POST /peek {"book","sentenceId","phrase","noCache","waitSeconds"} -> 200 mock model (X-Fable-Cache hit|miss) or 202
//	    GET /health, GET /jobs, GET /passages
//	fable-interpreter mock      --book alice --passage alice:c01.p013.s01 --phrase "golden key" [--out f.json] [--model id]
//	    --passage may be a phrase in quotes instead of an id: the first sentence containing it
//	fable-interpreter mock      --check content/library/clay/*.json     validate mock models against the schema rules
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/Thabhelo/fable/interpreter/internal/book"
	"github.com/Thabhelo/fable/interpreter/internal/books"
	"github.com/Thabhelo/fable/interpreter/internal/llm"
	"github.com/Thabhelo/fable/interpreter/internal/mock"
	"github.com/Thabhelo/fable/interpreter/internal/script"
	"github.com/Thabhelo/fable/interpreter/internal/server"
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
		fmt.Fprintln(os.Stderr, "usage: fable-interpreter validate|generate|serve|mock [flags]")
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
		variant := fs.Int("variant", 0, "reading of the passage: 0 plain, 1.. alternative directions")
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
		s, attempts, err := llm.New(*model).Interpret(ctx, sc, m, "", *variant)
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
		wait := fs.Duration("wait", 3*time.Second, "how long a request waits for a fresh script before answering 202 (the client may ask for more with waitSeconds)")
		warm := fs.Bool("warm", false, "generate every scene without a valid cache at startup (needs ANTHROPIC_API_KEY)")
		fs.Parse(os.Args[2:])
		bk, err := book.Load(filepath.Join(root, "book", "passages.json"))
		if err != nil {
			log.Fatal(err)
		}
		dir := llm.New(*model)
		srv := server.New(root, bk, dir)
		srv.DefaultWait = *wait
		srv.Model = dir.Model()
		srv.Peeker = dir
		if *warm {
			if os.Getenv("ANTHROPIC_API_KEY") == "" {
				log.Printf("--warm ignored: ANTHROPIC_API_KEY is not set")
			} else {
				log.Printf("warming %d scene(s)", srv.Warm())
			}
		}
		hs := &http.Server{Addr: *addr, Handler: srv.Handler(), ReadHeaderTimeout: 10 * time.Second, ReadTimeout: 30 * time.Second, WriteTimeout: 3 * time.Minute, IdleTimeout: 2 * time.Minute}
		go func() {
			sig := make(chan os.Signal, 1)
			signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
			<-sig
			log.Printf("shutting down")
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			hs.Shutdown(ctx)
		}()
		log.Printf("fable-interpreter listening on %s (model %s, key %v, wait %s)", *addr, srv.Model, os.Getenv("ANTHROPIC_API_KEY") != "", *wait)
		if err := hs.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}
	case "mock":
		runMock(root, os.Args[2:])
	default:
		log.Fatalf("unknown command %q", os.Args[1])
	}
}

func runMock(root string, args []string) {
	fs := flag.NewFlagSet("mock", flag.ExitOnError)
	slug := fs.String("book", "", "alice | oz | odyssey | gulliver")
	passage := fs.String("passage", "", "sentence id the highlight ends on (or a phrase that sentence contains)")
	phrase := fs.String("phrase", "", "the highlighted text")
	out := fs.String("out", "", "output path (default stdout)")
	model := fs.String("model", os.Getenv("FABLE_MODEL"), "Claude model id")
	check := fs.Bool("check", false, "validate the mock model files given as arguments instead of generating")
	fs.Parse(args)
	if *check {
		bad := 0
		for _, p := range fs.Args() {
			data, err := os.ReadFile(p)
			if err != nil {
				log.Fatal(err)
			}
			m, err := mock.Parse(data)
			var errs []string
			if err != nil {
				errs = []string{err.Error()}
			} else {
				read := ""
				if b, err := books.Load(root, m.Book); err == nil {
					if b.Ordinal(m.SentenceID) < 0 {
						errs = append(errs, fmt.Sprintf("sentenceId %q is not in %s", m.SentenceID, m.Book))
					} else {
						read, _ = b.TextUpTo(m.SentenceID, 1<<30)
					}
				}
				errs = append(errs, mock.Validate(m, read)...)
			}
			if len(errs) > 0 {
				bad++
				fmt.Printf("INVALID %s:\n- %s\n", p, strings.Join(errs, "\n- "))
			} else {
				fmt.Printf("VALID   %s: %d parts, %d triangles, %d labels\n", p, len(m.Parts), m.TriangleCount(), len(m.Labels))
			}
		}
		if bad > 0 {
			os.Exit(1)
		}
		return
	}
	if *slug == "" || *passage == "" || *phrase == "" {
		log.Fatal("mock needs --book, --passage and --phrase")
	}
	b, err := books.Load(root, *slug)
	if err != nil {
		log.Fatal(err)
	}
	sid := *passage
	if b.Ordinal(sid) < 0 {
		if sid = b.Find(*passage, ""); sid == "" {
			log.Fatalf("no sentence of %s is %q or contains it", *slug, *passage)
		}
	}
	if os.Getenv("ANTHROPIC_API_KEY") == "" {
		log.Fatal("mock needs ANTHROPIC_API_KEY (see docs/HANDOVER.md: the key lives in ~/.config/fable/env, never in the repo)")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	d := llm.New(*model)
	t0 := time.Now()
	m, attempts, err := d.Peek(ctx, b, sid, *phrase)
	took := time.Since(t0)
	if err != nil {
		for i, a := range attempts {
			fmt.Fprintf(os.Stderr, "--- attempt %d ---\n%s\n", i+1, a)
		}
		log.Fatalf("%v (after %s)", err, took.Round(time.Millisecond))
	}
	js := llm.MarshalModel(m)
	fmt.Fprintf(os.Stderr, "%s %q at %s: %d parts, %d triangles, %d labels, %d attempt(s), %s (model %s)\n", *slug, *phrase, sid, len(m.Parts), m.TriangleCount(), len(m.Labels), len(attempts), took.Round(time.Millisecond), d.Model())
	if *out == "" {
		fmt.Println(string(js))
	} else if err := os.WriteFile(*out, js, 0o644); err != nil {
		log.Fatal(err)
	}
}
