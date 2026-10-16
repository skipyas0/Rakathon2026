# Zadání projektu: MDT Copilot – AI asistent pro multidisciplinární onkologické konzilium

Multidisciplinární onkologický tým (MDT / indikační onkologická komise) složený z klinického onkologa, chirurga, radiačního onkologa, radiologa a patologa má na projednání jednoho onkologického pacienta obvykle pouze **3 až 5 minut**. V současné praxi lékaři ztrácejí drahocenný čas ručním dohledáváním informací v nestrukturovaných textových záznamech v eZdraví a zároveň jim na komisi často chybí přímé propojení s daty o tom, jak se pacient skutečně cítí (dotazníky PROMs).

**Cíl řešení:** Vytvořit funkční prototyp webové aplikace, která pomocí umělé inteligence zkonsoliduje roztroušená klinická i pacientská data a vygeneruje modulární, konfigurovatelný podklad pro zasedání MDT, jenž po potvrzení poslouží jako oficiální záznam s konečným verdiktem a akčním plánem komise.

---

## 1. Shrnutí povinného minima (Compulsory MVP)

Pro úspěšné splnění základního zadání musí prototyp pokrývat následující pilíře:

* **Konsolidace dvou odlišných zdrojů dat:** Propojení nestrukturovaných lékařských zpráv z eZdraví (propouštěcí zprávy, laboratoř a onkomarkery, popisy CT/MRI, medikace) se strukturovanými daty z pacientských dotazníků kvality života a symptomů (PROMs) a daty z nominace na komisi.


* **Čtyřbloková architektura výstupního reportu:**
1. **Blok A – Společný úvod (Executive Summary):** Rychlá orientace do 30 sekund (identifikace, diagnóza, ECOG podle lékaře i pacienta, důvod zařazení, strukturovaná otázka pro komisi a kompaktní časová osa onemocnění).


2. **Blok B – Specializované sekce podle odborností:** Filtrování a interpretace dat na míru konkrétním specialistům (povinně alespoň **3 role** z výčtu: chirurg, klinický onkolog, radiolog, patolog, pacientský rozměr).


3. **Blok B2 – AI podpora rozhodování (Decision Support Panel):** Samostatný panel předkládající možnosti léčby z dodaných doporučených postupů (guidelines) pomocí RAG, předběžný screening vhodnosti pro otevřené klinické studie, návrh 2–3 klíčových otázek k diskusi a kontrolu souladu se standardy při zápisu závěru.


4. **Blok C – Zápis a závěr ze zasedání (MDT Resolution & Action Plan):** Rozhraní pro zápis a úpravu finálního rozhodnutí během zasedání (strukturovaný záznam kvóra, zvažovaných možností, zvoleného postupu s termínem re-evaluace, zdůvodnění, souladu s guidelines, odlišných stanovisek a zařazení do studie) a export výsledného dokumentu (PDF / HL7 FHIR).




* **Plná konfigurovatelnost před generováním:** Možnost pro předsedu komise či administrátora naklikat, které sekce a v jakém pořadí se vygenerují, které odbornosti jsou přítomné a jaká má být míra detailu (odrážky vs. narativní text).


* **Detekce varovných signálů (Red Flags):** Automatické vyhledávání rozporů a rizik napříč zdroji (např. laboratorní pokles hemoglobinu v kombinaci s extrémní únavou v dotazníku, nebo výrazný rozdíl mezi ECOG hodnoceným lékařem a pacientem), včetně určení závažnosti a citace obou zdrojů.


* **Dohledatelnost (Traceability) a ochrana proti halucinacím:** Každé tvrzení AI musí mít interaktivní proklik na přesný zdrojový záznam v eZdraví nebo v dotazníku. Chybějící údaje nesmí AI odhadovat, ale musí explicitně uvést, že se v dokumentaci nenacházejí.


* **Zodpovědná AI (Human-in-the-loop):** Veškerý text generovaný AI musí být vizuálně odlišen od textu potvrzeného lékařem. Žádný výstup AI se nestane oficiálním záznamem bez schválení lékařem.



---

## 2. Kompletní seznam podúkolů (Povinné položky a BONUSY)

Bonusové položky jsou nepovinná rozšíření, která přinášejí až **+10 % bodů navíc** (hodnotí se kvalita implementace, nikoliv počet).

### Architektura reportu – Blok A: Společný úvod (MDT Executive Summary)

* **[POVINNÉ] Základní identifikace a klinický stav:** Zobrazení hlavní onkologické diagnózy, hlavního důvodu zařazení na MDT a aktuálního klinického stavu (škála ECOG 0–4 hodnocená lékařem a souběžně uváděná pacientem; výrazný nesoulad automaticky generuje *red flag*).


* **[POVINNÉ] Otázka pro MDT:** Zobrazení strukturované otázky zadané nominujícím lékařem (AI ji smí zpřesnit, ale nesmí si ji domýšlet; pokud chybí, označí případ jako neúplný).


* **[POVINNÉ] Časová osa onemocnění (Clinical Timeline):** AI generovaná chronologická osa zahrnující datum diagnózy, staging, operace, linie systémové léčby a radioterapie, klíčová zobrazovací vyšetření, progrese a předchozí závěry MDT.


* **[BONUS] Stav připravenosti případu (Case Readiness):** Semafor úplnosti podkladů podle šablony pro daný typ nádoru (např. chybějící histologie, staging starší než 6 týdnů, nevyšetřené povinné biomarkery) s doporučením AI vrátit neúplný případ k doplnění nebo jej přesunout.



### Architektura reportu – Blok B: Specializované sekce podle odborností

* **[POVINNÉ] Zpracování minimálně 3 odborných rolí** z následujících 5 základních pohledů:


* **Chirurgický pohled:** Resekabilita, TNM staging, komorbidity ovlivňující operabilitu, předchozí chirurgické výkony, subjektivní kardiorespirační zdatnost z dotazníku.


* **Klinická onkologie & farmakoterapie:** Histologie a molekulární patologie (HER2, MSI, KRAS, PD-L1 aj.), dosavadní linie chemoterapie/imunoterapie, toxicita a subjektivní nežádoucí účinky hlášené pacientem (PROMs).


* **Radiologie & zobrazovací metody:** Časová osa a porovnání CT/MRI/PET-CT vyšetření podle kritérií RECIST (zmenšení vs. zvětšení lézí, nová metastatická ložiska).


* **Patologie:** Klíčové bioptické nálezy, grading, histologický typ, potřeba dovyšetření dalších biomarkerů.


* **Pacientský rozměr (PROMs / kvalita života):** Shrnutí subjektivních obtíží z dotazníku (bolest, úbytek hmotnosti, psychika, socioekonomická podpora), preference a cíle pacienta (např. kvalita života vs. agresivní léčba, postoj k operaci) a vývoj (trend) PROMs v čase.




* **[BONUS] AI předvýpočet odpovědi podle RECIST 1.1:** Automatický výpočet součtů cílových lézí z textových popisů v radiologické sekci, výrazně označený jako orientační a určený k potvrzení radiologem.


* **[BONUS] AI návrh chybějících biomarkerů:** Upozornění v patologické sekci na nevyšetřené biomarkery vyžadované podle diagnózy a guidelines (např. chybějící MSI/MMR u kolorektálního karcinomu).


* **[BONUS] Rozšíření o další odborné role:**
* *Nukleární medicína:* Výsledky PET-CT a scintigrafií (SUVmax, nová ložiska).


* *Paliativní a podpůrná péče:* Kontrola symptomů (bolest, dušnost, nutrice) a detekce potřeby včasného zapojení paliativního týmu (upozornění při kombinaci zhoršeného PS, vysoké symptomové zátěže a progrese).


* *Geriatrická onkologie / křehkost:* Screening křehkosti u starších pacientů (např. G8), polypragmazie, sociální zázemí pro rozhodnutí o intenzitě léčby.


* *Klinická genetika:* Indikace genetického poradenství a testování zárodečných mutací (např. BRCA1/2, Lynchův syndrom) na základě diagnózy, věku a rodinné anamnézy.


* *Koordinátor / onkologická sestra (case manager):* Logistika, termíny vyšetření, kontaktní osoba pro pacienta, stav realizace předchozích závěrů MDT.





### Architektura reportu – Blok B2: AI podpora rozhodování (Decision Support Panel)

* **[POVINNÉ] Možnosti léčby podle doporučených postupů:** Výčet relevantních terapeutických možností z dodaných guidelines (např. ESMO) na základě diagnózy, stadia, biomarkerů a předchozí léčby – výhradně pomocí RAG s odkazem na konkrétní pasáž dokumentu.


* **[POVINNÉ] Předběžný screening klinických studií:** Porovnání profilu pacienta s kritérii zařazení a vyřazení (inclusion/exclusion criteria) otevřených studií s výstupem *„potenciálně vhodný / nevhodný / chybí údaj“* a zdůvodněním u každého kritéria.


* **[POVINNÉ] Klíčové otázky k diskusi:** Návrh 2–3 klíčových klinických otázek, které musí komise na zasedání vyřešit.


* **[POVINNÉ] Kontrola souladu s guidelines při zápisu závěru:** Detekce odchylky zapsaného závěru od doporučených postupů s neblokujícím upozorněním a výzvou ke krátkému zdůvodnění.


* **[BONUS] Podobné případy:** Vyhledání anonymizovaných předchozích závěrů MDT s obdobnou klinickou konstelací jako inspirace pro komisi.



### Architektura reportu – Blok C: Zápis a závěr ze zasedání (MDT Resolution & Action Plan)

* **[POVINNÉ] Editovatelný zápis rozhodnutí a dalšího postupu:** Možnost přímo během zasedání nebo na jeho konci zapsat a upravit konečné doporučení včetně termínu re-evaluace.


* **[POVINNÉ] Strukturovaný záznam rozhodnutí:** Zachycení přítomných členů a odborností (kvórum), zvažovaných možností, zvoleného postupu, zdůvodnění, souladu s guidelines (ano/ne + důvod odchylky), odlišných stanovisek členů a případného zařazení do klinické studie.


* **[POVINNÉ] Export záznamu:** Export finálního podkladu spolu se závěrem do zdravotní dokumentace (např. PDF nebo zpráva HL7 FHIR).


* **[BONUS] Mapování exportu na FHIR R4 / mCODE:** Strukturovaný export využívající zdroje `Condition` (diagnóza, TNM), `Observation` (biomarkery, PS, PROMs), `QuestionnaireResponse`, `CarePlan` + `Task` (závěr a akční plán) a `Provenance` (původ tvrzení AI a záznam o potvrzení lékařem).


* **[BONUS] AI zapisovatel (Ambient Scribe):** Automatický návrh znění závěru a akčních kroků z textového (příp. audio) přepisu diskuse komise, s vizuálním odlišením návrhu AI od textu potvrzeného předsedou.


* **[BONUS] Akční plán s úkoly a sledování realizace:** Přiřazení konkrétní odpovědné osoby, termínu a stavu ke každému úkolu (např. objednání PET-CT koordinátorem do 14 dnů) a sledování, zda byl závěr skutečně realizován.


* **[BONUS] Shrnutí pro pacienta a praktického lékaře:** Generování srozumitelného shrnutí v laickém jazyce pro pacienta a stručné zprávy pro praktického/odesílajícího lékaře (podléhá schválení lékařem).


* **[BONUS] Uzamčení a verzování záznamu:** Elektronické potvrzení/uzamčení záznamu předsedou komise, po němž každá další úprava zakládá novou verzi s auditní stopou.



### Systémové požadavky, AI interpretace a bezpečnost

* **[POVINNÉ] Konfigurace sekcí a detailu:** Uživatelské nastavení výběru a pořadí sekcí, přítomných odborností (možnost skrýt či přesunout nepřítomnou odbornost) a míry detailu (odrážky vs. souvislý text).


* **[BONUS] Šablony podle typu nádoru/komise:** Přednastavené šablony (např. kolorektální karcinom, prs, plíce, GIT, uroonkologie) se seznamem povinných datových prvků pro kontrolu úplnosti.


* **[BONUS] Konfigurace pravidel pro Red Flags a zdrojů:** Nastavení prahových hodnot pro aktivaci varovných signálů a výběr konkrétních dokumentů guidelines/studií, se kterými má AI pracovat.


* **[BONUS] Výchozí pohled podle role:** Automatické přizpůsobení rozhraní přihlášenému specialistovi (např. chirurg vidí svou sekci hned pod společným úvodem).


* **[POVINNÉ] Základní Red Flags se závažností a dvojitou citací:** Detekce nesrovnalostí mezi objektivními nálezy a subjektivním dotazníkem s uvedením závažnosti a proklikem na oba zdroje.


* **[BONUS] Rozšířené typy Red Flags:** Detekce rozporů mezi lékařskými zprávami (např. různé TNM ve dvou nálezech), zastaralých podkladů, nových symptomů v dotazníku bez odpovídajícího vyšetření (např. bolest kostí → zvážit scintigrafii), rostoucích onkomarkerů při „stabilním“ nálezu na zobrazovacích metodách, významných lékových interakcí a zhoršujícího se trendu PROMs.


* **[POVINNÉ] Interaktivní dohledatelnost (Explainability):** Zobrazení přesného zdrojového záznamu z eZdraví či dotazníku po kliknutí na jakékoliv tvrzení AI a striktní přiznání chybějících dat.


* **[BONUS] Citace na úrovni věty a míra jistoty:** Zvýraznění konkrétní pasáže ve zdrojovém dokumentu včetně data a autora záznamu; zobrazení míry jistoty (confidence score) u odvozených údajů.


* **[BONUS] Strukturovaná NLP extrakce (Single Source of Truth):** Převod nestrukturovaných zpráv na strukturované datové prvky (TNM, histologie, biomarkery, linie léčby, dávky, RECIST) s možností potvrzení či opravy jedním klikem; ze stejných prvků se následně skládají všechny sekce, čímž je zaručena konzistence napříč reportem.


* **[BONUS] Konverzační asistent nad případem (Q&A):** Možnost klást během zasedání dotazy v přirozeném jazyce s odpověďmi čerpajícími výhradně z dat pacienta a doplněnými o citace.


* **[BONUS] Rozšířená bezpečnost, regulace a evaluace AI:**
* *Auditní stopa:* Uchovávání verze modelu, promptu, použitých zdrojů a identity lékaře, který výstup potvrdil nebo upravil.


* *Ochrana údajů a regulace:* Pseudonymizace dat před odesláním do modelu, zpracování v EU / on-premise, minimalizace dat (GDPR) a architektonický popis souladu s **AI Act** a **MDR** (vysokorizikový systém / zdravotnický prostředek).


* *Evaluace spolehlivosti:* Ověření systému na kontrolní sadě faktů a záměrně vložených chyb (měření přesnosti citací, míry halucinací a záchytu red flags oproti *ground truth*).





---

## 3. Fáze procesu MDT a jak je projekt podporuje

MDT není jednorázová schůzka, ale uzavřený třífázový proces, který musí aplikace podporovat v celém jeho životním cyklu:

| Fáze procesu MDT | Co dělá komise / lékaři | Jak fázi podporuje MDT Copilot |
| --- | --- | --- |
| **1. Před zasedáním**<br>

<br>*(Příprava a nominace)* | Ošetřující lékař nominuje pacienta s konkrétní otázkou pro komisi. Kontroluje se úplnost podkladů (histologie, aktuální staging, biomarkery, PROMs) a předseda sestavuje program zasedání.

 | • Přebírá data z nominace a ověřuje přítomnost otázky pro MDT (chybí-li, označí případ jako neúplný).

<br>

<br>• Umožňuje předsedovi nakonfigurovat strukturu reportu podle přítomných odborností a typu nádoru.

<br>

<br>• *(Bonus)* Pomocí semaforu **Case Readiness** kontroluje úplnost a aktuálnost podkladů a navrhuje chybějící biomarkery či vrácení neúplného případu k doplnění.

 |
| **2. Během zasedání**<br>

<br>*(Diskuse a rozhodnutí)* | Členové komise se musí během 3–5 minut zorientovat v případu, posoudit nálezy ze svých odborných pohledů, zvážit možnosti léčby vůči guidelines, klinickým studiím a preferencím pacienta a zapsat finální verdikt se zdůvodněním.

 | • Poskytuje **Executive Summary** a **Clinical Timeline** pro orientaci do 30 sekund.

<br>

<br>• Zobrazuje specializované sekce podle rolí a zvýrazňuje **Red Flags** (např. rozpory mezi laboratoří a dotazníkem pacienta) s proklikem na primární zdroj.

<br>

<br>• V **Decision Support Panelu** předkládá možnosti léčby s citacemi guidelines, screening klinických studií a klíčové otázky k diskusi.

<br>

<br>• Poskytuje strukturovaný formulář pro zápis rozhodnutí, hlídá soulad s guidelines a *(Bonus)* nabízí Q&A asistenta či **Ambient Scribe** pro návrh zápisu z diskuse.

 |
| **3. Po zasedání**<br>

<br>*(Realizace a sledování)* | Závěr komise se zapisuje do dokumentace a komunikuje pacientovi i ošetřujícím lékařům. Přidělují se konkrétní úkoly s odpovědností a termíny, kontroluje se jejich splnění a plánuje se re-evaluace.

 | • Exportuje potvrzený záznam a akční plán do nemocničních systémů (PDF / **HL7 FHIR R4 / mCODE**) včetně termínu re-evaluace.

<br>

<br>• *(Bonus)* Rozepisuje akční plán na konkrétní úkoly (`Task`) s odpovědnou osobou, termínem a sledováním stavu realizace.

<br>

<br>• *(Bonus)* Generuje srozumitelné shrnutí v laickém jazyce pro pacienta a zprávu pro praktického lékaře, uzamyká záznam a verzuje případné změny s auditní stopou.

 |

---

## 4. Hranice pro AI komponenty a očekávaný formát výstupů

Architektura systému je postavena na striktním dodržování principu **Human-in-the-loop** a nulové toleranci k nepodloženým domněnkám.

### Co AI smí dělat (Povolené kompetence)

* **Konsolidovat, filtrovat a sumarizovat:** Spojovat volný text z eZdraví s daty z dotazníků PROMs a strukturovat je do časové osy a sekcí podle lékařských rolí.


* **Upřesňovat formulace:** Jazykově či strukturovaně zpřesnit otázku pro MDT zadanou nominujícím lékařem.


* **Detekovat rozpory a upozorňovat (Red Flags):** Hledat klinické nesrovnalosti mezi různými zdroji dat, upozorňovat na chybějící podklady, nevyšetřené biomarkery nebo odchylky zapsaného závěru od doporučených postupů.


* **Předkládat podklady k rozhodnutí (RAG & Screening):** Vyhledávat relevantní pasáže v dodaných guidelines, porovnávat profil pacienta s kritérii klinických studií, navrhovat 2–3 diskusní otázky a předvyplňovat návrhy zápisu či orientační součty RECIST 1.1.



### Co AI nesmí dělat (Striktní omezení a hranice)

* **Nesmí vybírat léčbu ani rozhodovat:** AI pouze předkládá strukturované možnosti z doporučených postupů a studií; volbu terapie a finální verdikt vždy provádí lékařská komise.


* **Nesmí hádat, domýšlet ani halucinovat:** Pokud v dokumentaci údaj chybí (např. nezadaná otázka pro komisi, nevyšetřený biomarker, chybějící kritérium pro studii), AI si jej nesmí domyslet ani použít obecné znalosti modelu mimo dodané dokumenty. Musí výslovně uvést *„v dostupné dokumentaci se nenachází“* (příp. *„chybí údaj“*) a označit případ jako neúplný.


* **Nesmí blokovat klinické rozhodnutí lékaře:** Pokud se komise rozhodne pro postup, který se odchyluje od guidelines, AI na tuto skutečnost upozorní a vyžádá si krátké zdůvodnění odchylky, ale zápis nijak neblokuje.


* **Nesmí zapsat neověřený výstup do oficiální dokumentace:** Žádný text, extrahovaný prvek, součet RECIST ani návrh závěru ze zapisovatele se nestane součástí oficiálního záznamu bez explicitního potvrzení lékařem.



### Očekávaný formát výstupů a standardy

* **Vizuální a interaktivní formát v UI:**
* Každý výstup generovaný AI musí být v uživatelském rozhraní **vizuálně odlišen** od obsahu, který již potvrdil nebo zapsal lékař.


* Každé tvrzení AI musí fungovat jako interaktivní prvek s proklikem na primární zdroj (konkrétní nález v eZdraví, pasáž v guidelines nebo odpověď v dotazníku PROMs).


* Každý *Red Flag* musí obsahovat stupeň závažnosti a citaci obou zdrojů, které jsou v rozporu.


* Screening klinických studií musí mít pro každé kritérium striktní formát stavu: `potenciálně vhodný` / `nevhodný` / `chybí údaj` + konkrétní důvod.




* **Struktura dat a interoperabilita (Export):**
* Závěr komise nesmí být pouze volným textem, ale musí mít pevnou datovou strukturu (kvórum, zvažované možnosti, zvolený postup, termín re-evaluace, zdůvodnění, soulad s guidelines ano/ne + důvod odchylky, odlišná stanoviska, zařazení do studie).


* Výstupní sestava musí umožňovat export do **PDF** a/nebo mezinárodního standardu **HL7 FHIR R4** (s využitím onkologických profilů **mCODE** či **HL7 Europe Common Cancer Model**).


* Při mapování na FHIR R4 se využívají zdroje `Condition` (diagnóza, TNM rozsah), `Observation` (biomarkery, ECOG performance status, výsledky PROMs), `QuestionnaireResponse` (odpovědi z dotazníků), `CarePlan` + `Task` (rozhodnutí komise a konkrétní úkoly akčního plánu) a `Provenance` (záznam o tom, odkud tvrzení pochází a který lékař jej potvrdil).


* Kódování klinických pojmů má tam, kde je to možné, využívat standardní číselníky: **MKN-10 / ICD-O-3** (diagnózy a morfologie nádorů), **LOINC** (laboratorní testy) a **SNOMED CT** (klinické pojmy).