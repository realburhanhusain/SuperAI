const alwaysAvailablePages = new Set(['home', 'versions', 'config']);

export function isAlwaysAvailablePage(pageId: string) {
  return alwaysAvailablePages.has(pageId);
}

export function canOpenAppPage(pageId: string, coreRunning: boolean) {
  return coreRunning || isAlwaysAvailablePage(pageId);
}
