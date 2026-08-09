import React from 'react';
import { formatDatePart } from '../../utils/dateFormat';
import { RESPONSE_LANGUAGE_DEFAULT, RESPONSE_LANGUAGES_FALLBACK } from '../../constants/responseLanguages';

export { RESPONSE_LANGUAGE_DEFAULT };

export default function GeneralSettings({
  dateFormat,
  onDateFormatChange,
  responseLanguage,
  onResponseLanguageChange,
  responseLanguages = RESPONSE_LANGUAGES_FALLBACK,
}) {
  return (
    <section className="settings-section">
      <h3>General</h3>
      <p className="section-description">
        Display and language preferences for the application interface and model responses.
        Changes save automatically.
      </p>

      <div className="subsection">
        <h4>Display Preferences</h4>
        <div className="general-setting-row">
          <label htmlFor="date-format-select" className="general-setting-label">Date Format</label>
          <select
            id="date-format-select"
            value={dateFormat}
            onChange={(e) => onDateFormatChange(e.target.value)}
            className="select-input general-setting-select"
          >
            <option value="auto">Auto (browser locale)</option>
            <option value="MM/DD/YYYY">MM/DD/YYYY (US)</option>
            <option value="DD/MM/YYYY">DD/MM/YYYY (Europe / intl.)</option>
            <option value="YYYY-MM-DD">YYYY-MM-DD (ISO)</option>
          </select>
          <span className="general-setting-hint">
            Sidebar preview: {formatDatePart(new Date(), dateFormat)}
          </span>
        </div>
      </div>

      <div className="subsection general-subsection-divider">
        <h4>Response Language</h4>
        <p className="section-description general-section-note">
          Council and advisor models will be instructed to respond in this language.
          Conversation titles and internal search queries stay in English.
        </p>
        <div className="general-setting-row">
          <label htmlFor="response-language-select" className="general-setting-label">Model responses</label>
          <select
            id="response-language-select"
            value={responseLanguage}
            onChange={(e) => onResponseLanguageChange(e.target.value)}
            className="select-input general-setting-select"
          >
            {responseLanguages.map((lang) => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>
        </div>
      </div>
    </section>
  );
}
