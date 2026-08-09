import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { AppErrorBoundary } from './AppErrorBoundary';
import App from './App';
import { I18nProvider } from './i18n';
import { applyTheme, detectInitialTheme } from './theme';
import './styles.css';

applyTheme(detectInitialTheme());

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider>
      <AppErrorBoundary>
        <App />
      </AppErrorBoundary>
    </I18nProvider>
  </StrictMode>
);
