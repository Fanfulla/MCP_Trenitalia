export type Locale = "it" | "en";

export const translations = {
  it: {
    nav: {
      features: "Funzionalità",
      howItWorks: "Come funziona",
      getStarted: "Inizia",
    },
    hero: {
      badge: "Open Source — MCP Server",
      title: "Treni italiani in tempo reale.",
      titleAccent: "Per la tua AI.",
      subtitle:
        "Server MCP che permette a Claude e altri LLM di rispondere a domande sui treni italiani: orari, ritardi, partenze, arrivi e tracciamento live.",
      cta: "Vedi su GitHub",
      ctaSecondary: "Richiedi accesso Live",
    },
    features: {
      eyebrow: "5 Tool MCP",
      title: "Tutto ciò che serve per i treni italiani",
      subtitle:
        "Dati Viaggiatreno in tempo reale combinati con l'orario teorico NeTEx. Ogni tool accetta nomi in chiaro.",
      tools: [
        {
          name: "Cerca Stazione",
          id: "trenitalia_cerca_stazione",
          description:
            "Trova stazioni ferroviarie per nome e restituisce l'ID Viaggiatreno. Supporta ricerca parziale.",
          example: '"Cerca la stazione di Bologna"',
        },
        {
          name: "Partenze Live",
          id: "trenitalia_monitora_partenze",
          description:
            "Bacheca partenze in tempo reale: treno, destinazione, orario, ritardo, binario e stato.",
          example: '"Prossime partenze da Milano Centrale"',
        },
        {
          name: "Arrivi Live",
          id: "trenitalia_monitora_arrivi",
          description:
            "Bacheca arrivi in tempo reale con provenienza, orario programmato, ritardo e binario.",
          example: '"Treni in arrivo a Roma Termini"',
        },
        {
          name: "Traccia Treno",
          id: "trenitalia_traccia_treno",
          description:
            "Telemetria completa: ultima stazione, ritardo, fermate effettuate, soppresse e anomalie.",
          example: '"Dov\'è il Frecciarossa 9631?"',
        },
        {
          name: "Orari tra Stazioni",
          id: "trenitalia_orari_tra_stazioni",
          description:
            "Orario ibrido NeTEx + live: trova corse tra A e B, con cross-check e ritardo real-time.",
          example: '"Treni da Tuscolana ad Aurelia domani mattina"',
        },
      ],
    },
    howItWorks: {
      eyebrow: "Architettura",
      title: "Come funziona",
      subtitle:
        "Logica ibrida che combina dati offline e real-time per massima affidabilità.",
      steps: [
        {
          title: "NeTEx Offline",
          description:
            "25.480 corse ferroviarie con fermate e orari. Filtra per giorno della settimana e periodo di validità.",
        },
        {
          title: "Cross-check Live",
          description:
            "Per le corse entro 90 minuti, verifica che il treno compaia nella bacheca partenze reale di Viaggiatreno.",
        },
        {
          title: "Ritardo Real-time",
          description:
            "Arricchisce ogni corsa con il ritardo attuale da Viaggiatreno, in parallelo con asyncio.gather.",
        },
        {
          title: "Fallback Intelligente",
          description:
            "Se NeTEx non trova risultati, interroga la bacheca live e verifica fermata per fermata il percorso reale.",
        },
      ],
    },
    stack: {
      eyebrow: "Stack tecnico",
      title: "Costruito con strumenti moderni",
      items: [
        { name: "Python 3.12", description: "Runtime" },
        { name: "FastMCP", description: "MCP Server + SSE" },
        { name: "httpx", description: "Client HTTP asincrono" },
        { name: "Pydantic v2", description: "Validazione input" },
        { name: "NeTEx", description: "Orario teorico offline" },
        { name: "Viaggiatreno", description: "API real-time" },
      ],
    },
    cta: {
      title: "Pronto a provarlo?",
      subtitle:
        "Il codice è open source su GitHub. Per la versione hosted su Claude Web, contattami su LinkedIn.",
      github: "Codice sorgente",
      linkedin: "Richiedi accesso Live",
    },
    footer: {
      made: "Fatto con",
      by: "da",
      description: "MCP Server per dati ferroviari italiani in tempo reale",
      domain: "ciuff.org",
      domainNote: "\"ciuff ciuff\" — come il treno",
    },
  },
  en: {
    nav: {
      features: "Features",
      howItWorks: "How it works",
      getStarted: "Get Started",
    },
    hero: {
      badge: "Open Source — MCP Server",
      title: "Italian trains in real time.",
      titleAccent: "For your AI.",
      subtitle:
        "MCP Server that lets Claude and other LLMs answer questions about Italian trains: schedules, delays, departures, arrivals, and live tracking.",
      cta: "View on GitHub",
      ctaSecondary: "Request Live Access",
    },
    features: {
      eyebrow: "5 MCP Tools",
      title: "Everything you need for Italian trains",
      subtitle:
        "Real-time Viaggiatreno data combined with NeTEx timetable. Every tool accepts human-readable names.",
      tools: [
        {
          name: "Station Search",
          id: "trenitalia_cerca_stazione",
          description:
            "Find train stations by name and get the Viaggiatreno ID. Supports partial search.",
          example: '"Find Bologna station"',
        },
        {
          name: "Live Departures",
          id: "trenitalia_monitora_partenze",
          description:
            "Real-time departure board: train, destination, time, delay, platform and status.",
          example: '"Next departures from Milano Centrale"',
        },
        {
          name: "Live Arrivals",
          id: "trenitalia_monitora_arrivi",
          description:
            "Real-time arrival board with origin, scheduled time, delay and platform.",
          example: '"Trains arriving at Roma Termini"',
        },
        {
          name: "Track Train",
          id: "trenitalia_traccia_treno",
          description:
            "Full telemetry: last station, delay, completed stops, cancelled stops and anomalies.",
          example: '"Where is Frecciarossa 9631?"',
        },
        {
          name: "Station-to-Station",
          id: "trenitalia_orari_tra_stazioni",
          description:
            "Hybrid NeTEx + live timetable: find routes from A to B, with cross-check and real-time delay.",
          example: '"Trains from Tuscolana to Aurelia tomorrow morning"',
        },
      ],
    },
    howItWorks: {
      eyebrow: "Architecture",
      title: "How it works",
      subtitle:
        "Hybrid logic combining offline and real-time data for maximum reliability.",
      steps: [
        {
          title: "NeTEx Offline",
          description:
            "25,480 train routes with stops and schedules. Filters by day of week and validity period.",
        },
        {
          title: "Live Cross-check",
          description:
            "For routes within 90 minutes, verifies the train appears on Viaggiatreno's real departure board.",
        },
        {
          title: "Real-time Delay",
          description:
            "Enriches each route with current delay from Viaggiatreno, in parallel with asyncio.gather.",
        },
        {
          title: "Smart Fallback",
          description:
            "If NeTEx finds no results, queries the live board and verifies stop-by-stop the actual route.",
        },
      ],
    },
    stack: {
      eyebrow: "Tech Stack",
      title: "Built with modern tools",
      items: [
        { name: "Python 3.12", description: "Runtime" },
        { name: "FastMCP", description: "MCP Server + SSE" },
        { name: "httpx", description: "Async HTTP client" },
        { name: "Pydantic v2", description: "Input validation" },
        { name: "NeTEx", description: "Offline timetable" },
        { name: "Viaggiatreno", description: "Real-time API" },
      ],
    },
    cta: {
      title: "Ready to try it?",
      subtitle:
        "The code is open source on GitHub. For the hosted version on Claude Web, reach out on LinkedIn.",
      github: "Source Code",
      linkedin: "Request Live Access",
    },
    footer: {
      made: "Made with",
      by: "by",
      description: "MCP Server for real-time Italian railway data",
      domain: "ciuff.org",
      domainNote: "\"ciuff ciuff\" — like a train",
    },
  },
} as const;

export type Translations = typeof translations.it;
