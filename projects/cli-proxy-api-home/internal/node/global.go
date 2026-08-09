package node

var globalRegistry = NewRegistry()

// GlobalRegistry returns the shared node registry.
func GlobalRegistry() *Registry {
	return globalRegistry
}
