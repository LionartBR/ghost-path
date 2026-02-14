import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";

const LANGUAGES = [
  { code: "en", name: "English", countryCode: "us" },
  { code: "pt-BR", name: "Portugu\u00eas", countryCode: "br" },
  { code: "es", name: "Espa\u00f1ol", countryCode: "es" },
  { code: "fr", name: "Fran\u00e7ais", countryCode: "fr" },
  { code: "de", name: "Deutsch", countryCode: "de" },
  { code: "zh", name: "\u7b80\u4f53\u4e2d\u6587", countryCode: "cn" },
  { code: "ja", name: "\u65e5\u672c\u8a9e", countryCode: "jp" },
  { code: "ko", name: "\ud55c\uad6d\uc5b4", countryCode: "kr" },
  { code: "it", name: "Italiano", countryCode: "it" },
  { code: "ru", name: "\u0420\u0443\u0441\u0441\u043a\u0438\u0439", countryCode: "ru" },
];

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = LANGUAGES.find((l) => l.code === i18n.language) || LANGUAGES[0];

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSelect = (code: string) => {
    void i18n.changeLanguage(code);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 bg-white border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors"
      >
        <span className={`fi fi-${current.countryCode} text-sm rounded-sm`} />
        <span>{current.name}</span>
        <svg className={`w-3 h-3 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1 w-44 bg-white border border-gray-200 rounded-lg shadow-lg z-50 py-1 max-h-80 overflow-y-auto">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => handleSelect(lang.code)}
              className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2.5 transition-colors ${
                lang.code === i18n.language
                  ? "bg-indigo-50 text-indigo-700 font-medium"
                  : "text-gray-700 hover:bg-gray-50"
              }`}
            >
              <span className={`fi fi-${lang.countryCode} text-sm rounded-sm`} />
              <span>{lang.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
