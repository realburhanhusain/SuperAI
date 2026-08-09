package registry

import "testing"

func TestGetXAIModelsIncludesImageAndVideoBuiltins(t *testing.T) {
	models := GetXAIModels()
	byID := make(map[string]*ModelInfo, len(models))
	for _, model := range models {
		if model != nil {
			byID[model.ID] = model
		}
	}

	for _, modelID := range []string{
		"grok-imagine-image",
		"grok-imagine-image-quality",
		"grok-imagine-video",
		"grok-imagine-video-1.5-preview",
	} {
		if byID[modelID] == nil {
			t.Fatalf("GetXAIModels() missing %q", modelID)
		}
	}
}
