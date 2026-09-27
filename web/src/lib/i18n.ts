export type Locale = "it" | "en";

export interface Translations {
  nav: { features: string; howItWorks: string; demo: string; faq: string; getStarted: string; source: string; x: string };
  hero: { badge: string; title: string; titleAccent: string; subtitle: string; cta: string; ctaSecondary: string };
  features: { eyebrow: string; title: string; subtitle: string; tools: { name: string; id: string; description: string; example: string }[] };
  howItWorks: { eyebrow: string; title: string; subtitle: string; steps: { title: string; description: string }[] };
  stack: { eyebrow: string; title: string; items: { name: string; description: string }[] };
  demo: { eyebrow: string; title: string; subtitle: string; videos: { src: string; label: string; description: string }[] };
  cta: { title: string; subtitle: string; github: string; x: string };
  footer: { description: string; made: string; by: string; domain: string; domainNote: string; independent: string; license: string };
  seo: { title: string; description: string };
  intro: { title: string; description: string };
  integration: { eyebrow: string; title: string; description: string; providers: { name: string; description: string }[]; note: string };
  install: { eyebrow: string; title: string; description: string; copy: string; copied: string; requirements: string; docs: string };
  sources: { eyebrow: string; title: string; description: string; items: { name: string; url: string; description: string }[]; updated: string; limitations: string[] };
  faq: { eyebrow: string; title: string; items: { question: string; answer: string }[] };
  accessibility: { skip: string; menu: string; closeMenu: string; switchLanguage: string; openGithub: string; openX: string };
  preview: { label: string; question: string; note: string; scheduled: string; unknownDelay: string };
}

export const translations: Record<Locale, Translations> = {
  it: {
    nav: {
      features: "Tool", howItWorks: "Come funziona", demo: "Demo", faq: "FAQ",
      getStarted: "Installa", source: "GitHub", x: "Seguimi su X",
    },
    hero: {
      badge: "Open source · 11 tool MCP · Self-hosted",
      title: "Trenitalia + Italo.",
      titleAccent: "Nel tuo client AI.",
      subtitle: "Stazioni, orari e stato dei treni attraverso un unico server MCP. Collega il tuo assistente ai dati di Trenitalia e Italo, senza API a pagamento.",
      cta: "Esplora su GitHub", ctaSecondary: "Seguimi su X",
    },
    intro: {
      title: "Un server MCP per Trenitalia e Italo",
      description: "MCP Trenitalia + Italo, anche chiamato Ciuff, è un server Python gratuito che espone dati ferroviari ai client compatibili con Model Context Protocol. Combina gli orari ufficiali NeTEx con le informazioni pubbliche di Viaggiatreno e Italo In Viaggio.",
    },
    integration: {
      eyebrow: "Due operatori, un'integrazione",
      title: "Chiedi una tratta. Consulta entrambe le fonti.",
      description: "Cerca stazioni e collegamenti diretti per Trenitalia, Italo o entrambi. I risultati mantengono operatore, fonte e validità dei dati, per distinguere un orario programmato da un aggiornamento live.",
      providers: [
        { name: "Trenitalia", description: "Orari NeTEx con calendario di servizio, partenze, arrivi e stato dei treni da Viaggiatreno. Le corse di oggi possono essere arricchite con informazioni live." },
        { name: "Italo", description: "Orari NeTEx dei servizi ferroviari diretti, stato dei treni e tabelloni da Italo In Viaggio. La data del servizio live resta non verificata quando la fonte non permette di accertarla." },
      ],
      note: "Progetto indipendente, non affiliato a Trenitalia o Italo.",
    },
    features: {
      eyebrow: "11 tool MCP",
      title: "Dalla ricerca della stazione allo stato del treno.",
      subtitle: "Sei nuovi tool affiancano i cinque originali. Ricerca comune per i due operatori e funzioni dedicate dove le fonti sono diverse.",
      tools: [
        {
          name: "Stazioni Trenitalia", id: "trenitalia_cerca_stazione",
          description: "Cerca una stazione nel catalogo locale, con fallback a Viaggiatreno quando necessario.",
          example: '"Cerca la stazione Trenitalia di Bologna"',
        },
        {
          name: "Partenze Trenitalia", id: "trenitalia_monitora_partenze",
          description: "Consulta il tabellone delle partenze live di Trenitalia con le informazioni disponibili dalla fonte.",
          example: '"Quali treni Trenitalia partono da Milano Centrale?"',
        },
        {
          name: "Arrivi Trenitalia", id: "trenitalia_monitora_arrivi",
          description: "Consulta gli arrivi live di Trenitalia in una stazione, con orari e ritardi quando disponibili.",
          example: '"Mostra gli arrivi Trenitalia a Roma Termini"',
        },
        {
          name: "Dettagli treno Trenitalia", id: "trenitalia_traccia_treno",
          description: "Interroga Viaggiatreno per numero del treno e stazione di origine, incluse fermate e stato disponibili.",
          example: '"Traccia il Trenitalia 9631 usando la sua stazione di origine"',
        },
        {
          name: "Orari Trenitalia", id: "trenitalia_orari_tra_stazioni",
          description: "Cerca corse dirette Trenitalia per la data richiesta. Per oggi può aggiungere informazioni live.",
          example: '"Trenitalia da Roma Termini a Milano Centrale domani dalle 8"',
        },
        {
          name: "Stazioni dei due operatori", id: "ciuff_cerca_stazioni",
          description: "Cerca per nome tra uno o entrambi gli operatori. Se il nome è ambiguo, restituisce le opzioni.",
          example: '"Trova Roma Termini per Trenitalia e Italo"',
        },
        {
          name: "Viaggi diretti", id: "ciuff_cerca_viaggi",
          description: "Cerca collegamenti diretti di Trenitalia e Italo per data e fascia oraria negli orari scaricati.",
          example: '"Trenitalia e Italo da Roma Termini a Milano Centrale domani dopo le 8"',
        },
        {
          name: "Stato del treno", id: "ciuff_stato_treno",
          description: "Richiede lo stato pubblico di un treno specificando operatore e numero, con indicazioni sulla freschezza dei dati.",
          example: '"Qual è lo stato di Italo 8908?"',
        },
        {
          name: "Tabellone Italo", id: "italo_tabellone",
          description: "Consulta arrivi o partenze Italo usando il nome della stazione o il suo codice Italo.",
          example: '"Mostra le partenze Italo da Roma Termini"',
        },
        {
          name: "Copertura e fonti", id: "ciuff_stato_fonti",
          description: "Mostra provenienza, aggiornamento e copertura degli orari locali. Non misura la disponibilità dei servizi esterni.",
          example: '"Fino a quando sono validi gli orari scaricati?"',
        },
        {
          name: "Siti ufficiali dei biglietti", id: "ciuff_link_biglietti",
          description: "Restituisce i link ai siti ufficiali di acquisto. Prezzi live, disponibilità dei posti e prenotazioni non sono integrati.",
          example: '"Dove posso acquistare sui siti ufficiali Trenitalia e Italo?"',
        },
      ],
    },
    howItWorks: {
      eyebrow: "Dalla fonte al tuo assistente",
      title: "Orari e dati live, con limiti espliciti.",
      subtitle: "Il server distingue ciò che è programmato da ciò che la fonte sta riportando. Una risposta mancante non diventa una conferma.",
      steps: [
        { title: "Scarica gli orari", description: "L'updater scarica e valida i feed ufficiali NeTEx. Le cache restano sul tuo sistema e permettono di consultare gli orari anche offline." },
        { title: "Verifica il calendario", description: "La ricerca usa la data richiesta, i giorni di servizio, le eccezioni e la validità del feed. Una copertura assente o scaduta viene segnalata." },
        { title: "Interroga le fonti live", description: "Viaggiatreno e Italo In Viaggio forniscono stato e tabelloni. I dati live di oggi restano separati dagli orari dei giorni futuri." },
        { title: "Mantieni visibili le incertezze", description: "Un ritardo mancante resta sconosciuto. Se la data del servizio Italo non è verificabile, il ritardo non viene associato a una corsa programmata per una data precisa." },
      ],
    },
    stack: {
      eyebrow: "Stack tecnico", title: "Python. MCP. Fonti consultabili.",
      items: [
        { name: "Python 3.12+", description: "Runtime del server" },
        { name: "MCP Python SDK 2.2", description: "SDK ufficiale Model Context Protocol" },
        { name: "stdio · HTTP · SSE", description: "Locale, Streamable HTTP e SSE legacy" },
        { name: "NeTEx", description: "Orari e calendari di servizio locali" },
        { name: "httpx", description: "Richieste asincrone alle fonti pubbliche" },
        { name: "Pydantic v2", description: "Validazione degli input dei tool" },
      ],
    },
    demo: {
      eyebrow: "Demo del progetto", title: "Il server nel client, in pratica.",
      subtitle: "Registrazioni originali dell'integrazione Trenitalia su Claude Desktop e Mobile. Documentano il flusso del client e precedono l'aggiunta di Italo.",
      videos: [
        { src: "/videos/demo-desktop-1.mp4", label: "Claude Desktop · Ricerca Trenitalia", description: "Registrazione della ricerca di treni con l'integrazione originale Trenitalia." },
        { src: "/videos/demo-desktop-2.mp4", label: "Claude Desktop · Stato Trenitalia", description: "Registrazione della consultazione dello stato di un treno Trenitalia." },
        { src: "/videos/demo-mobile.mp4", label: "Claude Mobile · Partenze Trenitalia", description: "Registrazione della consultazione delle partenze Trenitalia da mobile." },
      ],
    },
    install: {
      eyebrow: "Eseguilo sul tuo sistema", title: "Dal repository al tuo client MCP.",
      description: "Clona il progetto, installa le dipendenze e scarica gli orari. Avvia il server in stdio oppure scegli Streamable HTTP per un client remoto.",
      copy: "Copia comandi", copied: "Comandi copiati",
      requirements: "Python 3.12 o successivo. Internet serve per scaricare e aggiornare gli orari e per i tool live. Nessun account API a pagamento, database o servizio cloud richiesto.",
      docs: "Installazione e configurazione nel README",
    },
    sources: {
      eyebrow: "Provenienza e limiti", title: "Sai da dove arriva ogni dato.",
      description: "Gli orari provengono dai feed ufficiali pubblicati su CCISS. Lo stato dei treni arriva dai servizi pubblici degli operatori. Consulta ciuff_stato_fonti per le date delle tue cache locali.",
      items: [
        { name: "Trenitalia · NeTEx", url: "https://www.cciss.it/nap/mmtis/public/catalog/Asset/1080596", description: "Orari programmati, calendari e periodi di validità." },
        { name: "Italo · NeTEx", url: "https://www.cciss.it/nap/mmtis/public/catalog/Dataset/1813935", description: "Orari dei servizi ferroviari diretti, senza itinerari combinati." },
        { name: "Trenitalia · Viaggiatreno", url: "http://www.viaggiatreno.it/", description: "Stato, arrivi e partenze da endpoint pubblici non documentati, attualmente via HTTP." },
        { name: "Italo · In Viaggio", url: "https://italoinviaggio.italotreno.com/", description: "Stato e tabelloni da endpoint pubblici non documentati, senza una data di servizio affidabile." },
      ],
      updated: "Contenuti aggiornati il",
      limitations: [
        "La ricerca copre treni diretti. Non calcola coincidenze e non offre telemetria storica.",
        "Gli endpoint live non documentati possono cambiare o essere indisponibili. Il server non garantisce la continuità delle fonti esterne.",
        "Un ritardo assente non significa treno in orario. Per Italo la data del servizio live può restare non verificata.",
        "Il codice è MIT. Dataset e risposte degli operatori mantengono i propri termini; le cache scaricate restano locali.",
      ],
    },
    faq: {
      eyebrow: "Prima di iniziare", title: "Domande frequenti",
      items: [
        {
          question: "Che cos'è MCP Trenitalia + Italo?",
          answer: "È un server MCP gratuito e open source, anche chiamato Ciuff. Espone 11 tool per cercare stazioni e viaggi diretti, consultare stato e tabelloni e verificare le fonti di Trenitalia e Italo attraverso un client compatibile con Model Context Protocol.",
        },
        {
          question: "Servono API a pagamento o un abbonamento?",
          answer: "Il server non richiede API a pagamento, abbonamenti, database o servizi cloud. Puoi eseguirlo sul tuo computer. Eventuali costi del client AI o dell'hosting che scegli sono separati dal progetto.",
        },
        {
          question: "Quali client e trasporti sono supportati?",
          answer: "Puoi usare client MCP che supportano stdio, Streamable HTTP o SSE legacy, per esempio Claude Desktop con una configurazione locale. Scegli il trasporto supportato dal tuo client: python server.py per stdio, --streamable-http per /mcp e --sse per /sse. Il flag --http resta un alias di SSE legacy.",
        },
        {
          question: "Posso cercare treni per domani o per una data futura?",
          answer: "Sì, entro il periodo coperto dagli orari NeTEx scaricati. Il server verifica calendari ed eccezioni per la data richiesta e segnala cache mancanti o scadute. La ricerca riguarda collegamenti diretti; i dati live di oggi non vengono usati come stato di una corsa futura.",
        },
        {
          question: "Come vengono trattati i ritardi Italo?",
          answer: "La fonte pubblica Italo non fornisce una data di servizio affidabile. Quando non è verificabile, il server restituisce service_date null e freshness date_unverified e non associa quel ritardo a una corsa programmata per una data precisa. Un ritardo mancante resta null, senza essere interpretato come puntualità.",
        },
        {
          question: "Posso confrontare prezzi o prenotare biglietti?",
          answer: "No. Il tool ciuff_link_biglietti restituisce i link ai siti ufficiali di Trenitalia e Italo. Prezzi live, disponibilità dei posti, acquisto e prenotazione non sono implementati nel server.",
        },
        {
          question: "Come aggiorno gli orari? Funzionano offline?",
          answer: "Esegui python update_data.py per aggiornare entrambi gli operatori, oppure aggiungi --provider italo o --provider trenitalia. L'updater valida il nuovo feed prima di sostituire la cache; se fallisce, conserva il file precedente. Gli orari scaricati si consultano offline entro la loro validità. I tool live richiedono Internet. Puoi pianificare l'aggiornamento con lo scheduler del sistema operativo.",
        },
        {
          question: "È un servizio ufficiale di Trenitalia o Italo?",
          answer: "No. È un progetto indipendente di Salvatore Arena, non affiliato ai due operatori. Il codice è distribuito con licenza MIT; i dataset e le risposte delle fonti conservano i propri termini. Gli endpoint live pubblici sono non documentati e possono cambiare.",
        },
      ],
    },
    cta: {
      title: "Porta Trenitalia e Italo nel tuo progetto.",
      subtitle: "Leggi il codice, configura il server e contribuisci su GitHub. Per seguire il progetto, trovi Salvatore Arena su X.",
      github: "Apri il repository", x: "Segui @Fanfulladev",
    },
    footer: {
      description: "Server MCP open source per orari e informazioni live di Trenitalia e Italo.",
      made: "Creato", by: "da", domain: "ciuff.org", domainNote: '"Ciuff ciuff", come il treno.',
      independent: "Progetto indipendente. Non affiliato a Trenitalia o Italo.",
      license: "Licenza MIT",
    },
    seo: {
      title: "MCP Trenitalia + Italo | Orari e stato treni per AI",
      description: "Server MCP gratuito e open source per Trenitalia e Italo: 11 tool per stazioni, orari, stato e tabelloni. Python, self-hosted, senza API a pagamento.",
    },
    accessibility: {
      skip: "Vai al contenuto", menu: "Apri il menu", closeMenu: "Chiudi il menu", switchLanguage: "Read in English",
      openGithub: "Apri il repository GitHub di MCP Trenitalia + Italo", openX: "Apri il profilo X di Salvatore Arena",
    },
    preview: {
      label: "Esempio illustrativo",
      question: "Trenitalia e Italo da Roma Termini a Milano Centrale domani dopo le 8?",
      note: "Anteprima statica del flusso. Non mostra orari o risultati live.",
      scheduled: "Orario programmato", unknownDelay: "Ritardo non verificato",
    },
  },
  en: {
    nav: {
      features: "Tools", howItWorks: "How it works", demo: "Demos", faq: "FAQ",
      getStarted: "Install", source: "GitHub", x: "Follow on X",
    },
    hero: {
      badge: "Open source · 11 MCP tools · Self-hosted",
      title: "Trenitalia + Italo.", titleAccent: "In your AI client.",
      subtitle: "Stations, timetables and train status through one MCP server. Connect your assistant to Trenitalia and Italo data without paid APIs.",
      cta: "Explore on GitHub", ctaSecondary: "Follow me on X",
    },
    intro: {
      title: "An MCP server for Trenitalia and Italo",
      description: "MCP Trenitalia + Italo, also called Ciuff, is a free Python server that exposes railway data to clients supporting Model Context Protocol. It combines official NeTEx timetables with public information from Viaggiatreno and Italo In Viaggio.",
    },
    integration: {
      eyebrow: "Two operators, one integration", title: "Ask for a route. Check both sources.",
      description: "Search stations and direct journeys across Trenitalia, Italo or both. Results retain their operator, source and data validity, so a scheduled journey stays distinct from a live update.",
      providers: [
        { name: "Trenitalia", description: "NeTEx timetables with service calendars, plus departures, arrivals and train status from Viaggiatreno. Today's journeys can be enriched with live information." },
        { name: "Italo", description: "NeTEx timetables for direct rail services, plus train status and station boards from Italo In Viaggio. The live service date remains unverified when the source cannot establish it." },
      ],
      note: "Independent project, unaffiliated with Trenitalia or Italo.",
    },
    features: {
      eyebrow: "11 MCP tools", title: "From finding a station to checking a train.",
      subtitle: "Six new tools sit alongside the five original tools. Shared searches for both operators, with dedicated tools where the sources differ.",
      tools: [
        {
          name: "Trenitalia stations", id: "trenitalia_cerca_stazione",
          description: "Find a station in the local catalogue, with a Viaggiatreno fallback when needed.",
          example: '"Find the Trenitalia station in Bologna"',
        },
        {
          name: "Trenitalia departures", id: "trenitalia_monitora_partenze",
          description: "Read a live Trenitalia departure board with the information available from the source.",
          example: '"Which Trenitalia trains depart from Milano Centrale?"',
        },
        {
          name: "Trenitalia arrivals", id: "trenitalia_monitora_arrivi",
          description: "Read live Trenitalia arrivals at a station, including times and delays when available.",
          example: '"Show Trenitalia arrivals at Roma Termini"',
        },
        {
          name: "Trenitalia train details", id: "trenitalia_traccia_treno",
          description: "Query Viaggiatreno by train number and origin station for available stops and status.",
          example: '"Track Trenitalia 9631 using its origin station"',
        },
        {
          name: "Trenitalia timetables", id: "trenitalia_orari_tra_stazioni",
          description: "Find direct Trenitalia journeys for the requested date. Today's results can include live information.",
          example: '"Trenitalia from Roma Termini to Milano Centrale tomorrow from 8 am"',
        },
        {
          name: "Stations across operators", id: "ciuff_cerca_stazioni",
          description: "Search by name across one or both operators. Ambiguous names return choices.",
          example: '"Find Roma Termini for Trenitalia and Italo"',
        },
        {
          name: "Direct journeys", id: "ciuff_cerca_viaggi",
          description: "Search downloaded timetables for direct Trenitalia and Italo journeys by date and time window.",
          example: '"Trenitalia and Italo from Roma Termini to Milano Centrale tomorrow after 8 am"',
        },
        {
          name: "Train status", id: "ciuff_stato_treno",
          description: "Request public train status by operator and train number, including data freshness information.",
          example: '"What is the status of Italo 8908?"',
        },
        {
          name: "Italo station board", id: "italo_tabellone",
          description: "Read Italo arrivals or departures using the station name or its Italo code.",
          example: '"Show Italo departures from Roma Termini"',
        },
        {
          name: "Coverage and sources", id: "ciuff_stato_fonti",
          description: "Check local timetable provenance, update times and coverage. This does not measure upstream availability.",
          example: '"How far ahead do my downloaded timetables cover?"',
        },
        {
          name: "Official ticket sites", id: "ciuff_link_biglietti",
          description: "Get links to the official purchase sites. Live prices, seat availability and booking are not integrated.",
          example: '"Where can I buy on the official Trenitalia and Italo websites?"',
        },
      ],
    },
    howItWorks: {
      eyebrow: "From source to assistant", title: "Timetables and live data, with clear limits.",
      subtitle: "The server distinguishes scheduled journeys from what a source currently reports. A missing response never becomes a confirmation.",
      steps: [
        { title: "Download the timetables", description: "The updater downloads and validates official NeTEx feeds. Caches stay on your system and let you query timetables offline." },
        { title: "Check the calendar", description: "Searches use the requested date, service days, exceptions and feed validity. Missing or expired coverage is reported explicitly." },
        { title: "Query live sources", description: "Viaggiatreno and Italo In Viaggio provide train status and station boards. Today's live data stays separate from future timetables." },
        { title: "Keep uncertainty visible", description: "A missing delay stays unknown. If an Italo service date cannot be verified, its delay is not attached to a journey scheduled for a specific date." },
      ],
    },
    stack: {
      eyebrow: "Technical stack", title: "Python. MCP. Traceable sources.",
      items: [
        { name: "Python 3.12+", description: "Server runtime" },
        { name: "MCP Python SDK 2.2", description: "Official Model Context Protocol SDK" },
        { name: "stdio · HTTP · SSE", description: "Local, Streamable HTTP and legacy SSE" },
        { name: "NeTEx", description: "Local timetables and service calendars" },
        { name: "httpx", description: "Asynchronous requests to public sources" },
        { name: "Pydantic v2", description: "Tool input validation" },
      ],
    },
    demo: {
      eyebrow: "Project demos", title: "The server in a client, in practice.",
      subtitle: "Original recordings of the Trenitalia integration on Claude Desktop and Mobile. They show the client workflow and predate the addition of Italo.",
      videos: [
        { src: "/videos/demo-desktop-1.mp4", label: "Claude Desktop · Trenitalia search", description: "A recording of train search with the original Trenitalia integration." },
        { src: "/videos/demo-desktop-2.mp4", label: "Claude Desktop · Trenitalia status", description: "A recording of a Trenitalia train status query." },
        { src: "/videos/demo-mobile.mp4", label: "Claude Mobile · Trenitalia departures", description: "A recording of a Trenitalia departure query on mobile." },
      ],
    },
    install: {
      eyebrow: "Run it on your system", title: "From the repository to your MCP client.",
      description: "Clone the project, install its dependencies and download the timetables. Start the server over stdio, or choose Streamable HTTP for a remote client.",
      copy: "Copy commands", copied: "Commands copied",
      requirements: "Python 3.12 or later. Internet access is needed to download and refresh timetables and to use live tools. No paid API account, database or cloud service is required.",
      docs: "Installation and configuration in the README",
    },
    sources: {
      eyebrow: "Provenance and limits", title: "Know where each piece of data comes from.",
      description: "Timetables come from official feeds published on CCISS. Train status comes from the operators' public services. Use ciuff_stato_fonti to check the dates of your local caches.",
      items: [
        { name: "Trenitalia · NeTEx", url: "https://www.cciss.it/nap/mmtis/public/catalog/Asset/1080596", description: "Scheduled journeys, service calendars and validity periods." },
        { name: "Italo · NeTEx", url: "https://www.cciss.it/nap/mmtis/public/catalog/Dataset/1813935", description: "Direct rail timetables, excluding combined itineraries." },
        { name: "Trenitalia · Viaggiatreno", url: "http://www.viaggiatreno.it/", description: "Status, arrivals and departures from undocumented public endpoints, currently over HTTP." },
        { name: "Italo · In Viaggio", url: "https://italoinviaggio.italotreno.com/", description: "Status and boards from undocumented public endpoints without a reliable service date." },
      ],
      updated: "Content updated on",
      limitations: [
        "Search covers direct trains. It does not plan transfers or provide historic telemetry.",
        "Undocumented live endpoints can change or become unavailable. The server cannot guarantee upstream availability.",
        "A missing delay does not mean a train is on time. An Italo live service date may remain unverified.",
        "The code is MIT licensed. Datasets and provider responses retain their own terms; downloaded caches stay local.",
      ],
    },
    faq: {
      eyebrow: "Before you start", title: "Frequently asked questions",
      items: [
        {
          question: "What is MCP Trenitalia + Italo?",
          answer: "It is a free, open-source MCP server, also called Ciuff. Its 11 tools let clients supporting Model Context Protocol search stations and direct journeys, query train status and station boards, and inspect data sources for Trenitalia and Italo.",
        },
        {
          question: "Do I need paid APIs or a subscription?",
          answer: "The server requires no paid APIs, subscriptions, databases or cloud services. You can run it on your computer. Any costs of your chosen AI client or hosting provider are separate from this project.",
        },
        {
          question: "Which clients and transports are supported?",
          answer: "Use an MCP client that supports stdio, Streamable HTTP or legacy SSE, such as Claude Desktop with a local configuration. Choose a transport your client supports: python server.py for stdio, --streamable-http for /mcp, or --sse for /sse. The --http flag remains an alias for legacy SSE.",
        },
        {
          question: "Can I search for tomorrow or a future travel date?",
          answer: "Yes, within the coverage of your downloaded NeTEx timetables. The server checks service calendars and exceptions for the requested date and reports missing or expired caches. Search covers direct journeys; today's live data is not used as the status of a future journey.",
        },
        {
          question: "How are Italo delays handled?",
          answer: "Italo's public source does not provide a reliable service date. When it cannot be verified, the server returns service_date null and freshness date_unverified and does not attach that delay to a journey scheduled for a specific date. A missing delay stays null and is never interpreted as on time.",
        },
        {
          question: "Can I compare prices or book tickets?",
          answer: "No. The ciuff_link_biglietti tool returns links to the official Trenitalia and Italo websites. Live prices, seat availability, purchases and bookings are not implemented in the server.",
        },
        {
          question: "How do I update timetables? Do they work offline?",
          answer: "Run python update_data.py to refresh both operators, or add --provider italo or --provider trenitalia. The updater validates the new feed before replacing the cache; a failed update preserves the previous file. Downloaded timetables can be queried offline within their validity period. Live tools need Internet access. You can schedule updates using your operating system's scheduler.",
        },
        {
          question: "Is this an official Trenitalia or Italo service?",
          answer: "No. It is an independent project by Salvatore Arena, unaffiliated with either operator. The code is MIT licensed; datasets and source responses retain their own terms. The public live endpoints are undocumented and can change.",
        },
      ],
    },
    cta: {
      title: "Bring Trenitalia and Italo into your project.",
      subtitle: "Read the code, configure the server and contribute on GitHub. Follow Salvatore Arena on X for project updates.",
      github: "Open the repository", x: "Follow @Fanfulladev",
    },
    footer: {
      description: "An open-source MCP server for Trenitalia and Italo timetables and live information.",
      made: "Created", by: "by", domain: "ciuff.org", domainNote: '"Ciuff ciuff" is the sound of a train in Italian.',
      independent: "Independent project. Unaffiliated with Trenitalia or Italo.",
      license: "MIT license",
    },
    seo: {
      title: "MCP Trenitalia + Italo | Train timetables and status for AI",
      description: "Free, open-source MCP server for Trenitalia and Italo: 11 tools for stations, timetables, train status and boards. Self-hosted Python, no paid APIs.",
    },
    accessibility: {
      skip: "Skip to content", menu: "Open menu", closeMenu: "Close menu", switchLanguage: "Leggi in italiano",
      openGithub: "Open the MCP Trenitalia + Italo GitHub repository", openX: "Open Salvatore Arena's X profile",
    },
    preview: {
      label: "Illustrative example",
      question: "Trenitalia and Italo from Roma Termini to Milano Centrale tomorrow after 8 am?",
      note: "Static workflow preview. This is not a live timetable or search result.",
      scheduled: "Scheduled timetable", unknownDelay: "Delay not verified",
    },
  },
};
