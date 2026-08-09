package managementasset

import (
	"context"
	"embed"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"strings"

	"github.com/router-for-me/CLIProxyAPIHome/internal/config"
	"github.com/router-for-me/CLIProxyAPIHome/internal/util"
	log "github.com/sirupsen/logrus"
)

const (
	assetsDirName       = "assets"
	indexAssetName      = "index.html"
	managementAssetName = "management.html"
	userAssetName       = "user.html"
)

// AssetsDirName is the directory that stores hashed static assets.
const AssetsDirName = assetsDirName

// IndexFileName exposes the embedded entry asset filename.
const IndexFileName = indexAssetName

// ManagementFileName exposes the administrator control panel asset filename.
const ManagementFileName = managementAssetName

// UserFileName exposes the user workspace asset filename.
const UserFileName = userAssetName

// PanelFileNames lists all embedded control panel assets.
var PanelFileNames = []string{IndexFileName, ManagementFileName, UserFileName}

//go:embed all:static
var embeddedStaticFS embed.FS

// SetCurrentConfig is retained for compatibility with runtime wiring.
func SetCurrentConfig(cfg *config.Config) {
	_ = cfg
}

// StartAutoUpdater is retained for compatibility but does not perform remote updates.
func StartAutoUpdater(ctx context.Context, configFilePath string) {
	_ = ctx
	_ = configFilePath
	log.Debug("management asset auto-updater disabled: embedded assets are bundled at build time")
}

// StaticDir resolves the directory that stores the control panel assets.
func StaticDir(configFilePath string) string {
	if override := strings.TrimSpace(os.Getenv("MANAGEMENT_STATIC_PATH")); override != "" {
		return filepath.Clean(override)
	}

	if writable := util.WritablePath(); writable != "" {
		return filepath.Join(writable, "static")
	}

	configFilePath = strings.TrimSpace(configFilePath)
	if configFilePath == "" {
		return ""
	}

	base := filepath.Dir(configFilePath)
	if fileInfo, err := os.Stat(configFilePath); err == nil && fileInfo.IsDir() {
		base = configFilePath
	}

	return filepath.Join(base, "static")
}

// FilePath resolves the absolute path to the management control panel asset.
func FilePath(configFilePath string) string {
	return FilePathFor(configFilePath, ManagementFileName)
}

// FilePathFor resolves the absolute path to a specific control panel asset.
func FilePathFor(configFilePath string, assetName string) string {
	assetName = normalizePanelAssetName(assetName)
	if assetName == "" {
		return ""
	}

	dir := StaticDir(configFilePath)
	if dir == "" {
		return ""
	}
	return filepath.Join(dir, assetName)
}

// AssetPathFor resolves a path under the control panel static assets directory.
func AssetPathFor(configFilePath string, assetPath string) string {
	cleanedSlash := normalizeStaticAssetPath(assetPath)
	if cleanedSlash == "" {
		return ""
	}
	cleaned := filepath.Clean(filepath.FromSlash(cleanedSlash))

	dir := StaticDir(configFilePath)
	if dir == "" {
		return ""
	}

	assetsRoot := filepath.Join(dir, AssetsDirName)
	resolved := filepath.Join(assetsRoot, cleaned)
	if resolved != assetsRoot && !strings.HasPrefix(resolved, assetsRoot+string(filepath.Separator)) {
		return ""
	}
	return resolved
}

// OpenPanelAsset opens a control panel HTML asset from the local override, embedded bundle, or legacy static directory.
func OpenPanelAsset(configFilePath string, assetName string) (fs.File, error) {
	assetName = normalizePanelAssetName(assetName)
	if assetName == "" {
		return nil, fs.ErrNotExist
	}

	if hasStaticDirOverride() {
		return openDiskFile(FilePathFor(configFilePath, assetName))
	}

	file, errOpen := openEmbeddedFile(assetName)
	if errOpen == nil {
		return file, nil
	}
	if !os.IsNotExist(errOpen) {
		return nil, errOpen
	}

	return openDiskFile(FilePathFor(configFilePath, assetName))
}

// OpenStaticAsset opens a hashed static asset from the local override, embedded bundle, or legacy static directory.
func OpenStaticAsset(configFilePath string, assetPath string) (fs.File, error) {
	assetPath = normalizeStaticAssetPath(assetPath)
	if assetPath == "" {
		return nil, fs.ErrNotExist
	}

	if hasStaticDirOverride() {
		return openDiskFile(AssetPathFor(configFilePath, assetPath))
	}

	file, errOpen := openEmbeddedFile(path.Join(AssetsDirName, assetPath))
	if errOpen == nil {
		return file, nil
	}
	if !os.IsNotExist(errOpen) {
		return nil, errOpen
	}

	return openDiskFile(AssetPathFor(configFilePath, assetPath))
}

func normalizePanelAssetName(assetName string) string {
	assetName = strings.TrimSpace(assetName)
	if assetName == "" {
		return ""
	}

	base := filepath.Base(filepath.Clean(assetName))
	for _, panelAssetName := range PanelFileNames {
		if strings.EqualFold(base, panelAssetName) {
			return panelAssetName
		}
	}
	return ""
}

func normalizeStaticAssetPath(assetPath string) string {
	assetPath = strings.TrimSpace(assetPath)
	if assetPath == "" {
		return ""
	}

	assetPath = strings.TrimPrefix(assetPath, "/")
	cleaned := path.Clean(assetPath)
	if cleaned == "." || path.IsAbs(cleaned) || cleaned == ".." || strings.HasPrefix(cleaned, "../") {
		return ""
	}
	return cleaned
}

func hasStaticDirOverride() bool {
	return strings.TrimSpace(os.Getenv("MANAGEMENT_STATIC_PATH")) != ""
}

func openEmbeddedFile(assetPath string) (fs.File, error) {
	assetPath = normalizeStaticAssetPath(assetPath)
	if assetPath == "" {
		return nil, fs.ErrNotExist
	}

	file, errOpen := embeddedStaticFS.Open(path.Join("static", assetPath))
	if errOpen != nil {
		return nil, errOpen
	}

	fileInfo, errStat := file.Stat()
	if errStat != nil {
		if errClose := file.Close(); errClose != nil {
			log.WithError(errClose).Warn("failed to close embedded management asset after stat error")
		}
		return nil, errStat
	}
	if fileInfo.IsDir() {
		if errClose := file.Close(); errClose != nil {
			log.WithError(errClose).Warn("failed to close embedded management asset directory")
		}
		return nil, fs.ErrNotExist
	}

	return file, nil
}

func openDiskFile(filePath string) (fs.File, error) {
	filePath = strings.TrimSpace(filePath)
	if filePath == "" {
		return nil, fs.ErrNotExist
	}

	file, errOpen := os.Open(filePath)
	if errOpen != nil {
		return nil, errOpen
	}

	fileInfo, errStat := file.Stat()
	if errStat != nil {
		if errClose := file.Close(); errClose != nil {
			log.WithError(errClose).Warn("failed to close management asset after stat error")
		}
		return nil, errStat
	}
	if fileInfo.IsDir() {
		if errClose := file.Close(); errClose != nil {
			log.WithError(errClose).Warn("failed to close management asset directory")
		}
		return nil, fs.ErrNotExist
	}

	return file, nil
}
