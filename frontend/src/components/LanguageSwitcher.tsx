import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";

const LANGUAGES = [
  { code: "en", name: "English", flag: "EN" },
  { code: "pt-BR", name: "Portugues", flag: "PT" },
  { code: "es", name: "Espanol", flag: "ES" },
  { code: "fr", name: "Francais", flag: "FR" },
  { code: "de", name: "Deutsch", flag: "DE" },
  { code: "zh", name: "\u7b80\u4f53\u4e2d\u6587", flag: "\u4e2d" },
  { code: "ja", name: "\u65e5\u672c\u8a9e", flag: "\u65e5" },
  { code: "ko", name: "\ud55c\uad6d\uc5b4", flag: "\ud55c" },
  { code: "it", name: "Italiano", flag: "IT" },
  { code: "ru", name: "\u0420\u0443\u0441\u0441\u043a\u0438\u0439", flag: "RU" },
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
    i18n.changeLanguage(code);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 bg-white border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors"
      >
        <span className="text-[10px] font-bold text-gray-400">{current.flag}</span>
        <span>{current.name}</span>
        <svg className={`w-3 h-3 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-44 bg-white border border-gray-200 rounded-lg shadow-lg z-50 py-1 max-h-80 overflow-y-auto">
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
              <span className="text-[10px] font-bold text-gray-400 w-5 text-center">{lang.flag}</span>
              <span>{lang.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
