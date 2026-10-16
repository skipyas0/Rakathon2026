**Zadání: MDT Copilot – Asistovaná interpretace pro multidisciplinární onkologické konzilium**

**1. Kontext a výzva**

Multidisciplinární onkologický tým (MDT / indikační onkologická komise) se skládá z několika specialistů: klinického onkologa, chirurga, radiačního onkologa, radiologa a patologa. Na projednání jednoho pacienta mají často jen **3 až 5 minut**.

V současnosti lékaři ztrácejí čas ručním dohledáváním informací v nestrukturovaných nálezech v eZdraví a často nemají propojená data o tom, jak se pacient skutečně cítí (data z dotazníku).

**Cíl hackathonu:** Vytvořit funkční prototyp webové aplikace, která s pomocí AI zkonsoliduje data pacienta a vygeneruje **modulární, konfigurovatelný podklad pro zasedání MDT**, který zároveň slouží jako oficiální záznam se zapsaným konečným verdiktem komise.

**Princip MDT, ze kterého musí řešení vycházet:** MDT není jen samotné zasedání, ale uzavřený proces ve třech fázích. MDT Copilot má podpořit všechny tři, nejen přípravu podkladu:

- **Před zasedáním (příprava):** nominace pacienta ošetřujícím lékařem s **konkrétní otázkou pro komisi**, kontrola úplnosti podkladů (histologie, aktuální staging, biomarkery, PROMs), sestavení programu zasedání.

- **Během zasedání (diskuse a rozhodnutí):** rychlá společná orientace, pohledy jednotlivých odborností, zvážení možností léčby ve vztahu k doporučeným postupům (guidelines), dostupným klinickým studiím a **preferencím pacienta**, zápis rozhodnutí se zdůvodněním.

- **Po zasedání (realizace a sledování):** komunikace závěru pacientovi a ošetřujícím lékařům, přidělení úkolů s odpovědností a termínem, kontrola realizace a plánovaná re-evaluace.

**Základní pravidlo pro AI:** AI připravuje, sumarizuje, upozorňuje a navrhuje – **rozhodnutí vždy přijímá komise** (princip *human-in-the-loop*). Každý výstup AI musí být vizuálně odlišen od obsahu potvrzeného lékařem.

**Rozsah zadání:** Všechny položky bez označení tvoří **povinné minimum**. Položky označené **BONUS** jsou nepovinná rozšíření – přinášejí body navíc, ale jejich absence není chybou.

**2. Architektura výstupního reportu**

Výstupní dokument vygenerovaný AI musí respektovat následující logickou strukturu (předpokládá se, že návrh výstupu připomínkují onkologové zapojení do hackathonu):

**A. Společný úvod (MDT Executive Summary)**

- **Pro koho:** Pro všechny členy komise k rychlé orientaci během 30 sekund.

- **Obsah:** Identifikace případu, hlavní onkologická diagnóza, aktuální klinický stav (ECOG / performance status – hodnocený lékařem a souběžně uváděný pacientem; výrazný rozdíl je automaticky red flag), hlavní důvod zařazení na MDT (např. *„Progrese po 1. linii léčby – otázka resekability versus změna systémové terapie“*).

- **Otázka pro MDT:** strukturovaná otázka zadaná navrhujícím lékařem při nominaci. AI ji může zpřesnit, nesmí si ji však domýšlet – pokud otázka chybí, případ se označí jako neúplný.

- **Časová osa onemocnění (Clinical Timeline):** AI generovaná kompaktní osa – datum diagnózy, staging, operace, linie systémové léčby a radioterapie, klíčová zobrazovací vyšetření, progrese, předchozí závěry MDT.

- **BONUS Stav připravenosti případu (Case Readiness):** semafor úplnosti podkladů podle šablony pro daný typ nádoru (např. chybí histologie, staging starší než 6 týdnů, nevyšetřené povinné biomarkery). Neúplný případ AI doporučí vrátit k doplnění nebo přesunout.

**B. Specializované sekce podle odborností (pohledy podle rolí)**

Každá sekce filtruje a interpretuje data podle potřeb daného specialisty. Povinně musí být zpracovány **alespoň 3 role**; další jsou volitelné podle konfigurace.

- **Chirurgický pohled:** resekabilita, TNM staging, komorbidity pacienta ovlivňující operabilitu, předchozí chirurgické výkony, subjektivní kardiorespirační zdatnost z dotazníku.

- **Klinická onkologie & farmakoterapie:** histologie a molekulární patologie (HER2, MSI, KRAS, PD-L1…), dosavadní linie chemoterapie/imunoterapie, toxicita a subjektivní nežádoucí účinky hlášené pacientem (PROMs).

- **Radiologie & zobrazovací metody:** časová osa a porovnání CT/MRI/PET-CT vyšetření (kritéria RECIST – zmenšení vs. zvětšení lézí, přítomnost nových metastáz).

  - **BONUS** AI předvýpočet odpovědi podle RECIST 1.1 z textových popisů (součty cílových lézí) – výrazně označený jako orientační, k potvrzení radiologem.

- **Patologie:** klíčové bioptické nálezy, grading, histologický typ, případná potřeba dovyšetření dalších biomarkerů.

  - **BONUS** AI návrh chybějících biomarkerů podle diagnózy a doporučených postupů (např. MSI/MMR u kolorektálního karcinomu, pokud není v dokumentaci).

- **Pacientský rozměr (PROMs / kvalita života):** shrnutí subjektivních obtíží z dotazníku (bolest, úbytek hmotnosti, psychický stav, socioekonomická podpora), **cíle a preference pacienta** (např. upřednostnění kvality života před agresivní léčbou, postoj k operaci) a trend PROMs v čase.

- **BONUS Další role:**

  - **Nukleární medicína:** výsledky PET-CT a scintigrafií (SUVmax, nová ložiska) – samostatně nebo jako součást radiologické sekce.

  - **Paliativní a podpůrná péče:** kontrola symptomů (bolest, dušnost, nutriční stav), potřeba včasného zapojení paliativního týmu; AI upozorní na kombinaci zhoršeného PS, vysoké symptomové zátěže a progrese.

  - **Geriatrická onkologie / křehkost:** u starších pacientů výsledek screeningu křehkosti (např. G8), polypragmazie, sociální zázemí – vstup pro rozhodnutí o intenzitě léčby.

  - **Klinická genetika:** indikace genetického poradenství a testování zárodečných mutací (např. BRCA1/2, Lynchův syndrom) podle diagnózy, věku a rodinné anamnézy.

  - **Koordinátor / onkologická sestra (case manager):** logistika, termíny vyšetření, kontaktní osoba pro pacienta, stav realizace předchozích závěrů MDT.

**B2. AI podpora rozhodování (Decision Support Panel)**

Samostatný panel, který je **součástí povinného minima**. AI **nevybírá** léčbu – pouze strukturovaně předkládá podklady k diskusi, vždy s citací zdroje:

- **Možnosti léčby podle doporučených postupů:** AI na základě diagnózy, stadia, biomarkerů a předchozí léčby vyjmenuje relevantní možnosti z dodaných guidelines (např. ESMO / národní standardy) s odkazem na konkrétní pasáž (RAG nad dodanými dokumenty, nikoli znalosti modelu).

- **Předběžný screening klinických studií:** porovnání profilu pacienta s kritérii zařazení/vyřazení otevřených studií; výstupem je seznam „potenciálně vhodný / nevhodný / chybí údaj“ s důvodem u každého kritéria.

- **Klíčové otázky k diskusi:** AI navrhne 2–3 otázky, které je třeba na zasedání vyřešit (např. *„Je před změnou linie nutná histologická verifikace nového ložiska v játrech?“*).

- **Kontrola souladu s guidelines při zápisu závěru:** pokud se zapsaný závěr odchyluje od doporučených postupů, AI na to upozorní a vyžádá si krátké zdůvodnění (nejde o blokaci).

- **BONUS Podobné případy:** vyhledání anonymizovaných předchozích závěrů MDT s obdobnou konstelací – jako inspirace, nikoli jako doporučení.

**C. Zápis a závěr ze zasedání MDT (MDT Resolution & Action Plan)**

- Možnost přímo během zasedání nebo na jeho konci **zapsat a upravit konečné rozhodnutí komise**.

- **Doporučení dalšího postupu:** (např. *„Indikována neoadjuvantní chemoterapie 4 cykly, následně kontrolní CT za 3 měsíce a re-evaluace na MDT“*), včetně termínu re-evaluace.

- **Strukturovaný záznam rozhodnutí** (nejen volný text): přítomní členové a odbornosti (kvórum), zvažované možnosti, zvolený postup, **zdůvodnění**, soulad s doporučenými postupy (ano / ne + důvod odchylky), odlišná stanoviska členů, zařazení do klinické studie.

- Export konečného podkladu spolu se závěrem (např. do PDF / zprávy HL7 FHIR) do zdravotní dokumentace.

  - **BONUS Mapování exportu na FHIR R4 / mCODE:** *Condition* (diagnóza, TNM), *Observation* (biomarkery, PS, PROMs), *QuestionnaireResponse*, *CarePlan* + *Task* (závěr a akční plán), *Provenance* (původ tvrzení AI a kdo je potvrdil).

- **BONUS AI zapisovatel (Ambient Scribe):** z přepisu diskuse (text, příp. audio) AI navrhne znění závěru a akční kroky; předseda je upraví a potvrdí. Návrh AI a potvrzený text musí být odlišeny.

- **BONUS Akční plán s úkoly a sledování realizace:** každý úkol má odpovědnou osobu, termín a stav (např. „objednat PET-CT – koordinátor – do 14 dnů“); kontrola, zda byl závěr po MDT skutečně realizován.

- **BONUS Shrnutí pro pacienta a pro praktického lékaře:** AI vygeneruje srozumitelné shrnutí závěru v laickém jazyce a stručnou zprávu pro praktického / odesílajícího lékaře – vždy po schválení lékařem.

- **BONUS Uzamčení a verzování záznamu:** po schválení předsedou se záznam uzamkne (elektronický podpis / potvrzení), každá pozdější změna vytváří novou verzi s auditní stopou.

**3. Klíčové požadavky na funkcionalitu**

1.  **Konfigurovatelnost struktury a sekcí:**

    - Uživatel (administrátor nebo předseda komise) si může předem naklikat:

      - Jaké sekce a v jakém pořadí se mají vygenerovat a zobrazit.

      - Které odbornosti jsou na daném konziliu přítomné (např. pokud chybí patolog, lze sekci skrýt nebo přesunout na konec).

      - Míru detailu (odrážkový seznam vs. narativní text).

      - **BONUS** Šablony podle typu nádoru / komise (např. kolorektální, prs, plíce, GIT, uroonkologie) včetně seznamu povinných datových prvků pro kontrolu úplnosti.

      - **BONUS** Pravidla pro red flags (aktivace, prahové hodnoty) a výběr dokumentů guidelines/studií, se kterými má AI pracovat.

      - **BONUS** Výchozí pohled pro každou roli (např. chirurg vidí svou sekci hned za souhrnem).

2.  **AI interpretace a propojení dat:**

    - Syntéza dvou odlišných zdrojů: nestrukturované lékařské zprávy + strukturovaný pacientský dotazník.

    - AI upozornění (tzv. *Red Flags*): upozornění na nesrovnalosti (např. laboratorní pokles hemoglobinu provázený hlášenou extrémní únavou v dotazníku). Každý red flag musí mít závažnost a citaci obou zdrojů.

    - **BONUS Rozšířené typy red flags:** rozpor mezi zdroji (různé TNM ve dvou zprávách), zastaralé podklady, nový symptom v dotazníku bez odpovídajícího vyšetření (např. bolest kostí → zvážit scintigrafii), rostoucí trend onkomarkerů při „stabilním“ nálezu, významné lékové interakce, zhoršující se trend PROMs.

3.  **Dohledatelnost dat (Explainability / Traceability):**

    - U každého tvrzení AI musí lékař po kliknutí vidět přesný zdrojový záznam (konkrétní nález z eZdraví nebo konkrétní odpověď z dotazníku pacienta), aby nedocházelo k halucinacím.

    - Pokud údaj v dostupných datech není, AI to musí výslovně uvést („v dostupné dokumentaci se nenachází“) místo odhadu.

    - **BONUS** Citace na úrovni věty se **zvýrazněnou konkrétní pasáží** zdrojového dokumentu, datem a autorem záznamu; u odvozených údajů zobrazení míry jistoty.

4.  **Zodpovědná AI (minimum):** žádný výstup AI se nestane součástí oficiálního záznamu bez potvrzení lékařem; obsah generovaný AI je vizuálně označen.

5.  **BONUS Strukturovaná extrakce (NLP):** AI převede nestrukturované zprávy na strukturované prvky (TNM, histologie, biomarkery, linie léčby, dávky, RECIST) s vazbou na zdroj. Lékař je může jedním klikem potvrdit nebo opravit. Ze stejných prvků se skládají všechny sekce – tentýž údaj tak nemůže být ve dvou sekcích uveden rozdílně.

6.  **BONUS Konverzační asistent nad případem (Q&A):** během zasedání může člen komise položit otázku v přirozeném jazyce (např. *„Kdy byla poslední dávka oxaliplatiny a s jakou toxicitou?“*). Odpověď výhradně z dat pacienta a s citací.

7.  **BONUS Rozšířená bezpečnost a spolehlivost AI:**

    - Auditní stopa: u každého výstupu se uchovává verze modelu, promptu, použité zdroje a kdo výstup potvrdil/upravil.

    - Ochrana údajů: pseudonymizace dat posílaných do modelu, zpracování v EU / on-premise, minimalizace dat (GDPR); popis, jak by řešení zapadlo do požadavků AI Act a MDR (v produkci jde pravděpodobně o vysoce rizikový systém / zdravotnický prostředek).

    - Evaluace: prokázání spolehlivosti na kontrolní sadě (např. 20 ověřitelných faktů a záměrně vložených nesrovnalostí) – přesnost citací, podíl halucinací, záchyt red flags.

**4. Dodaná data (dataset pro soutěžící)**

- **Mock data eZdraví (JSON / FHIR formát):** propouštěcí zprávy, laboratorní výsledky (trendy onkomarkerů v čase), popisy CT/MRI vyšetření, seznam předepsaných léků.

- **Pacientský dotazník (PROMs / JSON):** odpovědi na škálované otázky (bolest 0–10, skóre únavy, ECOG status, alergie, nové obtíže). Doporučuje se vycházet ze standardizovaných nástrojů (např. EORTC QLQ-C30, PRO-CTCAE, Distress Thermometer) a dodat **alespoň dvě vyplnění v čase**, aby bylo možné sledovat trend.

- **Nominace případu na MDT:** odesílající lékař, konkrétní otázka pro komisi, důvod zařazení, předchozí závěry MDT.

- **Výtah z doporučených postupů** pro daný typ nádoru (text/PDF s číslovanými pasážemi) a **seznam 3–5 fiktivních otevřených klinických studií** s kritérii zařazení a vyřazení – pro Decision Support Panel.

- **Více scénářů (3–5 pacientů)** s různými typy nádorů a otázkami, včetně záměrně vložených nesrovnalostí a chybějících údajů, a k nim **referenční řešení (ground truth)** pro hodnocení – očekávané red flags a klíčová fakta.

- Kódování podle standardů, kde je to možné: MKN-10 / ICD-O-3 (diagnóza, morfologie), LOINC (laboratoř), SNOMED CT, profily mCODE / IPS.

- **BONUS Mock přepis diskuse MDT** (text, příp. krátké audio) pro testování AI zapisovatele.

**5. Hodnoticí kritéria**

| **Kritérium** | **Váha** | **Popis** |
|:--:|----|----|
| **Klinická hodnota & UX pro MDT** | **30 %** | Přehlednost společného souhrnu, srozumitelnost sekcí podle rolí, intuitivní zápis konečného doporučení. |
| **Konfigurovatelnost systému** | **20 %** | Flexibilita nastavení šablon, přidávání/odebírání sekcí a změna jejich pořadí pro různé typy onkologických týmů. |
| **Technické řešení AI & spolehlivost** | **20 %** | Přesnost promptingu (minimalizace halucinací), interaktivní ověření zdrojů (citace), dodržení struktury výstupu. |
| **Datová integrace a standardy** | **15 %** | Schopnost logicky propojit subjektivní data z dotazníku s objektivními nálezy z eZdraví, export výsledku, využití FHIR a standardních terminologií. |
| **Podpora MDT procesu & zodpovědná AI** | **15 %** | Kvalita Decision Support Panelu (možnosti léčby s citací guidelines, screening studií), strukturovaný záznam rozhodnutí se zdůvodněním, human-in-the-loop a označení obsahu AI. |
| **Bonusové funkce** | **až +10 %** | Body navíc za kvalitně implementované položky označené BONUS (hodnotí se kvalita, ne počet). |

**6. Očekávaná prezentace výsledku (demo)**

Každý tým během max. 5 minut předvede celý cyklus MDT na jednom z dodaných pacientů:

- vygenerování podkladu podle zvolené konfigurace → orientace v souhrnu do 30 sekund → ověření alespoň jednoho tvrzení AI a jednoho red flagu kliknutím na zdroj → Decision Support Panel (možnosti léčby s citací guidelines, screening studií) → zápis a potvrzení závěru → export.

- **BONUS** Předvedení implementovaných bonusových funkcí (např. kontrola připravenosti, AI zapisovatel, shrnutí pro pacienta).

Součástí prezentace je krátký popis architektury AI (model, způsob groundingu/RAG, prevence halucinací, ochrana údajů).
