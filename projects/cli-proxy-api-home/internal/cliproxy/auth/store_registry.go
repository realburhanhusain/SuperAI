package auth

import (
	"sync"
)

var (
	storeMu         sync.RWMutex
	registeredStore Store
)

// GetTokenStore returns the globally registered token store.
func GetTokenStore() Store {
	storeMu.RLock()
	s := registeredStore
	storeMu.RUnlock()
	if s != nil {
		return s
	}
	storeMu.Lock()
	defer storeMu.Unlock()
	if registeredStore == nil {
		registeredStore = NewFileTokenStore()
	}
	return registeredStore
}
