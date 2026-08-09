// Package watcher watches the config file and auth directory for changes and triggers hot reload callbacks.
//
// This is a simplified fsnotify-based watcher aligned with CLIProxyAPI's hot reload behavior:
// - Watch the parent directory of the config file (robust against atomic save/rename).
// - Watch the auth-dir directory for *.json changes (add/modify/remove/rename).
// - Debounce noisy event bursts and reload based on current filesystem state.
package watcher

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/fsnotify/fsnotify"
	"github.com/router-for-me/CLIProxyAPIHome/internal/config"
	"github.com/router-for-me/CLIProxyAPIHome/internal/util"
	log "github.com/sirupsen/logrus"
)

const (
	configReloadDebounce = 150 * time.Millisecond
	authReloadDebounce   = 150 * time.Millisecond
)

type Callbacks struct {
	// OnConfigReload is invoked after the config file is reloaded successfully.
	OnConfigReload func(ctx context.Context, cfg *config.Config)
	// OnConfigYAMLChange is invoked when the config file content changes (raw YAML bytes).
	// It is called even if the updated config cannot be parsed successfully.
	OnConfigYAMLChange func(ctx context.Context, data []byte)
	// OnAuthChange is invoked when auth-dir content changes and should be reloaded.
	OnAuthChange func(ctx context.Context)
}

// Watcher watches config.yaml and auth-dir for changes and triggers callbacks.
type Watcher struct {
	configPath string
	configDir  string
	configBase string

	authDir string

	cb Callbacks

	w *fsnotify.Watcher

	mu            sync.Mutex
	configTimer   *time.Timer
	authTimer     *time.Timer
	lastConfigSum string

	stopped atomic.Bool
}

// NewWatcher creates a new watcher.
func NewWatcher(configPath string, authDir string, cb Callbacks) (*Watcher, error) {
	// Keep validation before state changes so failures leave existing data intact.
	configPath = strings.TrimSpace(configPath)
	if configPath == "" {
		return nil, os.ErrInvalid
	}

	absConfigPath := cleanPathMaybeAbs(configPath)
	configDir := filepath.Dir(absConfigPath)
	configBase := filepath.Base(absConfigPath)

	resolvedAuthDir := strings.TrimSpace(authDir)
	if resolvedAuthDir != "" {
		if abs := cleanPathMaybeAbs(resolvedAuthDir); abs != "" {
			resolvedAuthDir = abs
		}
	}

	w, errNew := fsnotify.NewWatcher()
	if errNew != nil {
		return nil, errNew
	}

	return &Watcher{
		configPath: absConfigPath,
		configDir:  configDir,
		configBase: configBase,
		authDir:    resolvedAuthDir,
		cb:         cb,
		w:          w,
	}, nil
}

// Start starts the process.
func (w *Watcher) Start(ctx context.Context) error {
	// Keep validation before state changes so failures leave existing data intact.
	if w == nil || w.w == nil {
		return nil
	}
	if ctx == nil {
		ctx = context.Background()
	}

	if errAdd := w.w.Add(w.configDir); errAdd != nil {
		return errAdd
	}
	log.Debugf("watching config directory: %s", w.configDir)

	if strings.TrimSpace(w.authDir) != "" {
		if errEnsure := os.MkdirAll(w.authDir, 0o755); errEnsure != nil {
			return errEnsure
		}
		if errAdd := w.w.Add(w.authDir); errAdd != nil {
			return errAdd
		}
		log.Debugf("watching auth directory: %s", w.authDir)
	}

	go w.process(ctx)
	return nil
}

// Stop stops the process.
func (w *Watcher) Stop() error {
	if w == nil || w.w == nil {
		return nil
	}
	w.stopped.Store(true)
	w.stopTimers()
	return w.w.Close()
}

// process handles pending watcher events.
func (w *Watcher) process(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			_ = w.Stop()
			return
		case event, ok := <-w.w.Events:
			if !ok {
				return
			}
			w.handleEvent(ctx, event)
		case errWatch, ok := <-w.w.Errors:
			if !ok {
				return
			}
			log.Errorf("file watcher error: %v", errWatch)
		}
	}
}

// handleEvent handles an event.
func (w *Watcher) handleEvent(ctx context.Context, event fsnotify.Event) {
	if w == nil || w.stopped.Load() {
		return
	}
	name := cleanPathMaybeAbs(event.Name)
	if name == "" {
		return
	}

	// Config file events (watch parent dir; filter by basename).
	if filepath.Dir(name) == w.configDir && filepath.Base(name) == w.configBase {
		if event.Has(fsnotify.Write) || event.Has(fsnotify.Create) || event.Has(fsnotify.Rename) || event.Has(fsnotify.Remove) {
			w.scheduleConfigReload(ctx)
		}
		return
	}

	// Auth-dir events (watch directory; react to *.json changes).
	if strings.TrimSpace(w.authDir) != "" && filepath.Dir(name) == w.authDir && strings.HasSuffix(strings.ToLower(name), ".json") {
		if event.Has(fsnotify.Write) || event.Has(fsnotify.Create) || event.Has(fsnotify.Rename) || event.Has(fsnotify.Remove) || event.Has(fsnotify.Chmod) {
			w.scheduleAuthReload(ctx)
		}
	}
}

// stopTimers stops a timers.
func (w *Watcher) stopTimers() {
	w.mu.Lock()
	if w.configTimer != nil {
		w.configTimer.Stop()
		w.configTimer = nil
	}
	if w.authTimer != nil {
		w.authTimer.Stop()
		w.authTimer = nil
	}
	w.mu.Unlock()
}

// scheduleConfigReload handles a schedule config reload.
func (w *Watcher) scheduleConfigReload(ctx context.Context) {
	w.mu.Lock()
	if w.configTimer != nil {
		w.configTimer.Stop()
	}
	w.configTimer = time.AfterFunc(configReloadDebounce, func() {
		w.mu.Lock()
		w.configTimer = nil
		w.mu.Unlock()
		w.reloadConfigIfChanged(ctx)
	})
	w.mu.Unlock()
}

// reloadConfigIfChanged handles a reload config if changed.
func (w *Watcher) reloadConfigIfChanged(ctx context.Context) {
	// Normalize source data before building the derived payload.
	if w == nil || w.stopped.Load() {
		return
	}
	data, errRead := os.ReadFile(w.configPath)
	if errRead != nil || len(data) == 0 {
		return
	}
	sum := sha256.Sum256(data)
	sumHex := hex.EncodeToString(sum[:])

	w.mu.Lock()
	prev := w.lastConfigSum
	if prev != "" && prev == sumHex {
		w.mu.Unlock()
		return
	}
	w.lastConfigSum = sumHex
	w.mu.Unlock()

	if w.cb.OnConfigYAMLChange != nil {
		w.cb.OnConfigYAMLChange(ctx, data)
	}

	cfg, errLoad := config.LoadConfigOptional(w.configPath, false)
	if errLoad != nil {
		log.Errorf("failed to reload config %s: %v", w.configPath, errLoad)
		return
	}

	resolvedAuthDir, errResolveAuthDir := util.ResolveAuthDir(cfg.AuthDir)
	if errResolveAuthDir != nil {
		log.Errorf("failed to resolve auth directory from config: %v", errResolveAuthDir)
	} else if strings.TrimSpace(resolvedAuthDir) != "" {
		cfg.AuthDir = resolvedAuthDir
	}

	w.updateAuthDirWatch(cfg.AuthDir)

	if w.cb.OnConfigReload != nil {
		w.cb.OnConfigReload(ctx, cfg)
	}
}

// updateAuthDirWatch updates an auth dir watch.
func (w *Watcher) updateAuthDirWatch(nextAuthDir string) {
	nextAuthDir = strings.TrimSpace(nextAuthDir)
	if nextAuthDir != "" {
		nextAuthDir = cleanPathMaybeAbs(nextAuthDir)
	}

	w.mu.Lock()
	prevAuthDir := w.authDir
	if prevAuthDir == nextAuthDir {
		w.mu.Unlock()
		return
	}
	w.authDir = nextAuthDir
	w.mu.Unlock()

	// Update fsnotify watches outside the mutex.
	if prevAuthDir != "" && w.w != nil {
		_ = w.w.Remove(prevAuthDir)
	}
	if nextAuthDir == "" || w.w == nil {
		return
	}
	if errEnsure := os.MkdirAll(nextAuthDir, 0o755); errEnsure != nil {
		log.Errorf("failed to ensure auth directory %s: %v", nextAuthDir, errEnsure)
		return
	}
	if errAdd := w.w.Add(nextAuthDir); errAdd != nil {
		log.Errorf("failed to watch auth directory %s: %v", nextAuthDir, errAdd)
		return
	}
	log.Debugf("watching auth directory: %s", nextAuthDir)
}

// scheduleAuthReload handles a schedule auth reload.
func (w *Watcher) scheduleAuthReload(ctx context.Context) {
	if w == nil || w.stopped.Load() {
		return
	}
	if w.cb.OnAuthChange == nil {
		return
	}
	w.mu.Lock()
	if w.authTimer != nil {
		w.authTimer.Stop()
	}
	w.authTimer = time.AfterFunc(authReloadDebounce, func() {
		w.mu.Lock()
		w.authTimer = nil
		w.mu.Unlock()
		if w.cb.OnAuthChange != nil {
			w.cb.OnAuthChange(ctx)
		}
	})
	w.mu.Unlock()
}

// cleanPathMaybeAbs handles a clean path maybe abs.
func cleanPathMaybeAbs(path string) string {
	trimmed := strings.TrimSpace(path)
	if trimmed == "" {
		return ""
	}
	cleaned := filepath.Clean(trimmed)
	if filepath.IsAbs(cleaned) {
		return cleaned
	}
	if abs, errAbs := filepath.Abs(cleaned); errAbs == nil {
		return abs
	}
	return cleaned
}
