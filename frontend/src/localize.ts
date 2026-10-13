const messages = {
  en: {
    title: "Electricity price",
    today: "Today",
    tomorrow: "Tomorrow",
    tomorrowMissing: "Tomorrow’s prices have not been published yet",
    current: "Now",
    best: "Cheapest window",
    average: "average",
    vat: "VAT",
    noData: "No prices are available",
    loading: "Loading prices…",
    retry: "Retry",
    resolution: "Resolution",
    duration: "Window",
    includeVat: "Include VAT",
    minutes: "min",
    hours: "h",
    error: "Could not load prices",
    relativeScale: "Relative scale for visible prices: low, middle, high",
  },
  et: {
    title: "Elektrihind",
    today: "Täna",
    tomorrow: "Homme",
    tomorrowMissing: "Homseid hindu pole veel avaldatud",
    current: "Praegu",
    best: "Soodsaim ajavahemik",
    average: "keskmine",
    vat: "KM",
    noData: "Hinnad puuduvad",
    loading: "Hindade laadimine…",
    retry: "Proovi uuesti",
    resolution: "Samm",
    duration: "Ajavahemik",
    includeVat: "Koos käibemaksuga",
    minutes: "min",
    hours: "h",
    error: "Hindade laadimine ebaõnnestus",
    relativeScale: "Nähtavate hindade suhteline skaala: madal, keskmine, kõrge",
  },
} as const;

export type MessageKey = keyof typeof messages.en;

export function localize(language: string | undefined, key: MessageKey): string {
  const locale = language?.toLowerCase().startsWith("et") ? messages.et : messages.en;
  return locale[key];
}

