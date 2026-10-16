# MDT Copilot | Projektový kontext pro tým a AI agenty

**Projekt:** Rakathon 2026, výzva Asseco Central Europe „MDT Copilot – Asistovaná interpretace pro multidisciplinární onkologické konzilium“  
**Stav dokumentu:** pracovní kontext, aktualizováno 16. 10. 2026 po dvou konzultacích s mentory  
**Určení:** produktový návrh, implementace, evaluace, práce AI coding agentů  
**Důvěrnost:** oficiální zadání je označeno `CONFIDENTIAL (by Asseco CE)`. Před publikací odvozeného kontextu ve veřejném repozitáři prověřit oprávnění.

## 0. Jak tento dokument číst

Informace níže mají rozdílnou závaznost:

- **[ZADÁNÍ]** – požadavek nebo údaj z oficiálního zadání Asseco. `BONUS` je výslovně nepovinný.
- **[DATA]** – fakt doložený v dodaném datasetu a jeho `README.md`.
- **[MENTOR 1]** – neformální konzultace s prvním mentorem (InterSystems/FHIR, obecný MDT workflow a klinický přínos).
- **[MENTOR 2]** – neformální konzultace s druhým, datově orientovaným mentorem (role, pohledy, filtrování dat, multi-LLM kontroly).
- **[NÁVRH]** – možné řešení od týmu/asistenta, které zatím není schválenou architekturou.
- **[OVĚŘIT]** – nejasné, nedoslovené nebo potenciálně rozporné informace z poznámek.

**Pokyn pro agenty:** Nikdy automaticky nepovažovat `[MENTOR]` nebo `[NÁVRH]` za povinný požadavek. Při rozporu dát přednost přesnému textu zadání a `README.md` datasetu, nejistotu explicitně označit.

## 1. Produktový účel a hranice odpovědnosti

**[ZADÁNÍ]** Vytvořit funkční webový prototyp, který konsoliduje dokumentaci onkologického pacienta a generuje **modulární, konfigurovatelný a zdrojově ověřitelný podklad** pro multidisciplinární onkologický tým (MDT). Podklad se dá použít jako strukturovaný zápis konečného rozhodnutí. Na jeden případ má MDT často **3–5 minut**; společný souhrn musí být pochopitelný přibližně za **30 sekund**.

Klíčové principy:

1. Případ přichází s **otázkou formulovanou ošetřujícím lékařem**. Pokud není, označit případ jako neúplný, AI otázku nesmí domyslet.
2. Systém poskytuje **fakta, nesrovnalosti, podklady, možnosti postupu a návrhy otázek k diskusi**.
3. **AI nerozhoduje o léčbě:** konečné rozhodnutí přijímá a potvrzuje lidská komise (`human-in-the-loop`). Výstup AI vizuálně oddělit od schváleného záznamu.
4. Důležitou inovací je **propojení objektivní klinické dokumentace s PROMs** (patient-reported outcome measures, tj. pacientem hlášené výsledky, symptomy a preference).
5. Výstup musí být **úsporný a relevantní**: nejprve to, co je pro otázku daného MDT podstatné, pak možnost rozbalení a ověření zdrojů.

**[MENTOR 1]** Soustředit se na koncept a fungující jádro, nezabřednout do komplexity všech hypotetických funkcí. Zapojení perspektivy pacienta je významný rozlišovací prvek.

**[MENTOR 2]** Záměr je především **vyhodnocovat dostupná data a vytvářet podpůrná doporučení**; nevytvářet systém pro výběr a přidělování lékařů. Tvrzení „máme rozhodnout“ v neformálních poznámkách **nelze chápat jako automatické rozhodnutí o léčbě**, které by odporovalo zadání.

## 2. Workflow MDT: před, během a po zasedání

| Fáze | Vstup | Požadovaný výsledek |
| --- | --- | --- |
| **Před MDT** | nominace, konkrétní otázka, klinická dokumentace, PROMs | kontrola dostupnosti podkladů, souhrn, timeline, odborné sekce, red flags, příprava agendy |
| **Během MDT** | společný souhrn a podklady pro specialisty | interpretace, diskuse možností dle guidelines a studií, vyjádření odborníků, zápis rozhodnutí |
| **Po MDT** | lékaři potvrzený závěr | konečný záznam, doporučený léčebný postup a plán re-evaluace, export; v širším workflow i navazující úkoly a jejich kontrola |

**[MENTOR 1]** Složení komise není stálé. Účastníci dostanou společný souhrn a své odborné podklady, každý se může vyjádřit. Komisi vede předsedající, často onkolog (případně koordinátor onkologické léčby); mechanismus výběru předsedy nebyl popsán. V dodaných datech jsou historické záznamy předsedajících a členů.

**[MENTOR 2]** Přidělování lékařů a jejich výběr do komise **není součástí doporučeného MVP**. Role a oprávnění lze pro prototyp předkonfigurovat.

> **Důležitý rozdíl:** Sestavení specialistů a jejich *odborností* ≠ autentizace uživatelů ≠ oprávnění vidět konkrétní pacienty ≠ pořadí a obsah sekcí v UI. Jde o různé problémy. V prototypu lze demonstrovat výběr pohledu bez plné nemocniční identity/access-control infrastruktury.

## 3. Přístupová oprávnění a role (nová konzultace)

**[MENTOR 2]** V reálném prostředí by přístup k pacientům závisel na oprávněních lékaře, která spravuje administrátor; ideálně by lékař viděl data pouze pacientů, ke kterým má oprávněný přístup. Některé role mají širší pravomoci než jiné. Odbornosti a hierarchie jsou v reálné nemocnici složitější než několik statických kategorií.

**[MENTOR 2: pracovní zjednodušení]** Pro hackathon uvažovat **čtyři odbornosti ze zadání** a administrátorský/koordinační pohled. Poznámky neurčují konečný seznam čtyř rolí.

**[ZADÁNÍ]** Jsou povinné **alespoň tři** odborné role. Zmiňované oblasti jsou chirurgie, klinická onkologie, radiologie a patologie. Zadání výslovně počítá s konfigurovatelností sekcí podle přítomných odborností.

**[NÁVRH]** Praktická demonstrace může mít:

- **Shared / executive view:** kompaktní souhrn + otázka pro MDT + klíčové red flags a preference pacienta.
- **Oncology view:** biomarkery, dosavadní léčba, toxicita, relevantní guidelines/studie a PROMs.
- **Radiology view:** staging, časová osa vyšetření, velikosti lézí, možné rozpory a nové nálezy.
- **Surgery view:** resekabilita/operabilita, komorbidity, předchozí výkony, funkční stav a subjektivní zdatnost.
- **Pathology view:** biopsie, histologie, grading, receptorový stav, biomarkery a chybějící vyšetření.
- **Coordinator/admin view:** společné informace + přepínání konfigurace, případně přehled všech odborných sekcí a stavu závěru.

**[MENTOR 2]** Každý odborník by ideálně dostal vlastní pohled. Zmíněný kompromis: správce/koordinátor vidí celkový přehled, jednotliví specialisté společný souhrn a svůj odborný pohled. **Čím méně nerelevantních informací v prvním pohledu, tím lépe.**

**[NÁVRH]** Pro MVP implementovat **role-based presentation** (filtrování a pořadí UI sekcí), nikoli deklarovat plnohodnotnou produkční **RBAC/ABAC autorizaci**. Skutečné omezení přístupu k pacientům by v produkci muselo být **vynuceno také na backendu**, nikoli pouhým skrytím komponent. Neprezentovat UI filtrování jako bezpečnostní opatření.

**[OVĚŘIT]** Má být pro demo jediný společný přehled přepínatelný podle role, nebo více skutečně přihlášených uživatelů s oddělenými datovými přístupy?

## 4. Dodaná data a jejich využití

**[DATA]** Dataset tvoří **šest zcela syntetických pacientských případů**. Nejde o klinicky validovaná data ani o reálné pacienty. Základní pracovní struktura:

| Zdroj | Formát / lokace v původním datasetu | Účel |
| --- | --- | --- |
| Pacienti P01–P06 | `pacienti/Pxx/Pxx_bundle.json`, vše v `fhir/bundles.ndjson` | FHIR R4 `Bundle` se záznamy pacienta |
| Čitelné podklady | `pacienti/Pxx/Pxx_pacient.md` | textový ekvivalent pro ruční kontrolu, ID odpovídají FHIR resources |
| Pacientský dotazník | `dotaznik/dotaznik_PROMs.md`, `dotaznik_PROMs_Questionnaire.json` | struktura otázek, stupnice, volné odpovědi |
| Odpovědi PROMs | FHIR `QuestionnaireResponse` v každém pacientském bundlu | **dvě vyplnění v čase**, trendy a preference |
| Guidelines | `guidelines/OBC_*.md`, `PRS_*.md`, `KRC_*.md`, `PLI_*.md` | zjednodušené **neoficiální** výtahy, číslované citovatelné pasáže |
| Studie | `studie/studie.json`, `.md`, `studie_ResearchStudy_bundle.json` | **šest fiktivních** studií, explicitní inclusion/exclusion kritéria |
| Ground truth | v `README.md` uváděná složka `ground_truth/` | očekávané red flags, fakta a kritéria studií; **v této sadě příloh zatím nedodáno** |

Poznámka: po importu se mohou soubory nacházet jinde než v původních složkách; vycházet ze skutečné struktury repozitáře.

### Klinické scénáře

| Pacient | Otázka pro komisi (zjednodušeně) |
| --- | --- |
| **P01** | HR+/HER2-low metastatický karcinom prsu s progresí po CDK4/6; další linie a studie RKT-01 |
| **P02** | HER2+ karcinom prsu, nové mozkové metastázy; lokální vs. systémová léčba a studie RKT-02 |
| **P03** | Kolorektální karcinom s jaterními metastázami; resekabilita po konverzní léčbě |
| **P04** | NSCLC stadium III; chirurgie vs. chemoradioterapie, operabilita |
| **P05** | Karcinom prsu, BRCA2 v nádoru; PARP inhibitor, anémie G3 a genetické dovyšetření |
| **P06** | HER2+ karcinom prsu, nejasné plicní ložisko a nádor ledviny; původ ložiska a pořadí léčby |

### FHIR mapování relevantních zdrojů

- `Patient`, `Condition`: pacient, diagnózy, staging/TNM, komorbidity.
- `DocumentReference`: textové klinické zprávy v `content.attachment.data` (**Base64 UTF-8**).
- `DiagnosticReport`, `Observation`, `ImagingStudy`: patologie, biomarkery, zobrazovací popisy, laboratoř, ECOG, trendy; některé texty v `presentedForm`.
- `MedicationRequest`, `MedicationAdministration`, `Procedure`: medikace, podání léčby a výkony.
- `QuestionnaireResponse`: PROMs. Schéma dotazníku je FHIR `Questionnaire` (`MDT-PROMS-1`).
- `ServiceRequest`, `Task`: nominace případu a stav projednání.
- `Composition`, `CarePlan`, `CareTeam`: předchozí závěry komise, doporučení a účastníci.
- Některá pole obsahují standardní kódy MKN-10/ICD-O-3, LOINC, ATC; FHIR ukázkové systémové URI `rakathon.example.org` jsou **identifikátory**, nikoli živé API endpointy.

**[DATA]** Dataset nemá skutečné DICOM snímky ani přepis živé diskuse MDT. Umělé nesrovnalosti a chybějící informace jsou součástí testovacích scénářů.

> **Rozpor poznámek:** `[MENTOR 1]` zmiňuje možnost, že „původně šlo o reálná anonymizovaná data“, ale oficiální `README.md` výslovně říká, že **všechna data byla vytvořena pro hackathon a jsou fiktivní**. Pro práci s tímto datasetem platí údaj z README. U budoucích reálných pacientských dat by se musely zvlášť řešit přístup, právní titul, ochrana údajů, smlouvy a modelový endpoint. Pouhé vypnutí trénování na API datech není dostatečná záruka.

## 5. PROMs a jejich rozdělení mezi odbornosti

**[DATA]** Dotazník `MDT-PROMS-1` obsahuje 0–10 škály bolesti, únavy, nevolnosti, dušnosti, nechutenství, neuropatických symptomů, průjmu, psychické zátěže a spánku; dále soběstačnost (laická paralela ECOG), chůzi, hmotnost, nové obtíže, alergie, další léky/doplňky, priority pacienta, volné vyjádření a podporu v domácnosti.

**[MENTOR 2]** Dotazníky a odpovědi mají být **rozdělovány relevantním odborníkům**. Mentor naznačil, že odborníci by si v širším systému mohli formulovat také vlastní otázky. Poznámka k tomu je neúplná.

**[NÁVRH]** Pro MVP **netvořit nový editor dotazníků**, protože dotazník i pacientské odpovědi už existují. Důležitější je mapovat jednotlivé odpovědi na užitečné odborné pohledy. Jde o **many-to-many** vazbu: stejná odpověď může být relevantní více odborníkům a nikdy nemá zmizet ze společného klinického modelu.

Příklady mapování (ilustrativní, nikoli pevná klinická pravidla):

- Dušnost, zdatnost, chůze → chirurgie/operabilita, klinická onkologie, případně radiologie v klinickém kontextu.
- Únava, nevolnost, neuropatie → klinická onkologie/toxicita, podpůrná péče.
- Bolest a nové lokalizované potíže → klinická onkologie, radiologie, relevantní chirurgický pohled.
- Preference léčby, kvalita života, domácí podpora → **společný souhrn** a všechna rozhodnutí, u nichž to mění volbu postupu.

**[OVĚŘIT]** Má UI umožňovat také editaci/konfiguraci dotazníku, nebo jen filtrovat již vyplněné PROMs? Zadání vyžaduje hlavně interpretaci dodaných odpovědí.

## 6. Co musí systém umět

### A. Společný souhrn a timeline [ZADÁNÍ]

- Identifikace případu, diagnóza, aktuální stav, důvod a konkrétní otázka pro MDT.
- ECOG dle lékaře **vedle** pacientem popsané soběstačnosti; nesoulad může být red flag.
- Klinická timeline: diagnóza, staging, zákroky, léčebné linie, restaging, progrese, předchozí MDT.
- Zdrojová ID na úrovni jednotlivých tvrzení.

### B. Odborné sekce [ZADÁNÍ]

- **Alespoň tři role**, lze skrýt/zobrazit/přeuspořádat, nastavit míru detailu.
- Nejde pouze o oddělené textové sumarizace; každá sekce vybírá to, co je **relevantní pro odbornou otázku**, a zachovává vazby na původní fakta.
- PROMs integrálně ovlivňují interpretaci, nejsou jen izolovaná stránka dotazníku.

### C. Red flags a úplnost [ZADÁNÍ]

- Odhalovat klinicky významné **nesrovnalosti a souvislosti** (např. pokles Hb + zvýšená únava), vždy se **závažností a citacemi**.
- Rozšířené kontroly rozporů, chybějících biomarkerů, zastaralých podkladů, nových symptomů a jejich neprověření jsou v zadání zčásti označené jako `BONUS`; pro kvalitní demo mohou být vhodné.
- Při nesouladu mezi zdroji ukázat **oba důkazy** a nezahlazovat rozpor výběrem pohodlnější hodnoty.

### D. Decision Support Panel [ZADÁNÍ]

- Relevantní **léčebné možnosti z dodaných guidelines**, nikoli volně domyšlená doporučení z paměti modelu.
- **Citovat konkrétní číslované pasáže** (`PRS-...`, `KRC-...`, `PLI-...`, `OBC-...`).
- Předběžný screening dodaných studií: pro **každé inclusion/exclusion kritérium** uvést **splněno / nesplněno / chybí údaj** včetně zdroje a vysvětlení. Souhrnné zařazení nesmí být přesvědčivější než dostupné podklady.
- Navrhnout **2–3 věcné otázky k diskusi**.
- Při zápisu závěru upozornit na nesoulad s guidelines a požádat o odůvodnění; **nesmí bez dalšího blokovat rozhodnutí komise**.

### E. Zápis, potvrzení a export [ZADÁNÍ]

- Editovatelný, **strukturovaný** zápis: složení MDT a odbornosti, uvažované varianty, vybraná varianta, zdůvodnění, případné odlišné názory, vztah ke guidelines/studii, plán re-evaluace.
- Explicitní **schválení lékařem**; před ním se AI návrh nesmí vydávat za oficiální rozhodnutí.
- Export finálního podkladu a závěru (např. **PDF / HL7 FHIR**).
- `BONUS`: AI přepisovatel diskuse, plnohodnotné sledování úkolů a termínů, audit/verzování, pacientské shrnutí, detailní FHIR/mCODE mapování.

## 7. Studie, zdroje a jejich důvěryhodnost

**[MENTOR 1 + MENTOR 2]** Ověřovat validitu/spolehlivost odborných podkladů, zejména klinických studií a doporučených postupů. První mentor zmiňoval původ publikace a důvěryhodnost zdroje, druhý výslovně upozornil na nutnost studie validovat.

**Zásadní rozlišení:**

1. **Dodané studie RKT-01 až RKT-06** jsou **fiktivní**, určené k testování matchingu. **Neověřovat jejich „existenci“ či kvalitu v reálných registrech** a nepředstírat peer review. Testuje se korektnost vyhodnocení jejich *dodaných* kritérií.
2. **Potenciální budoucí externí studie/publikace** by vyžadovaly oddělený mechanismus dohledání a hodnocení evidence: registrace studie, náborový stav, datum a verze protokolu, typ studie, zdroj publikace, metodologická kvalita, relevance pro konkrétního pacienta. **[NÁVRH / MIMO ZÁKLAD MVP]**
3. **Dodané guidelines** jsou hackathonové parafráze, nikoli závazná originální doporučení. V rámci benchmarku je použít jako poskytnutý znalostní podklad a citovat přesné ID pasáží.

**[OVĚŘIT]** Je vyhledávání skutečných, externě publikovaných studií součástí očekávání mentorů, nebo jen možná inovace? Podle oficiálního povinného rozsahu stačí screening dodaných studií.

## 8. Návrhy AI architektury z konzultací

### A. Rizika přímého LLM filtrování [MENTOR 2]

- Nespolehlivé, nekontrolované filtrování relevantních klinických informací může něco závažného **vynechat**.
- Posílat všem modelům kompletní rozsáhlou dokumentaci je zároveň **nákladné na tokeny a latenci**.
- Mentor navrhoval **více specializovaných AI agentů** podle odbornosti/domény (v poznámkách např. kardiologická oblast) s následnou **vzájemnou nebo centrální kontrolou**.
- Pro směrování PROMs a dalších informací k odborníkům padl nápad **multi-LLM workflow**: první model navrhne, komu je informace relevantní, druhý rozhodnutí reviduje, případně nastane další kontrola či diskuse modelů.

**[DŮLEŽITÉ]** To je **architektonický nápad mentora, nikoli povinnost zadání ani prokázaná metoda dosažení klinické spolehlivosti**. Shoda dvou LLM může být chybná a neprokazuje faktickou správnost. Modely mohou sdílet systematické chyby.

### B. Konzervativní MVP alternativa [NÁVRH]

```text
FHIR bundles + PROMs + guidelines + studie
       ↓
FHIR parser; dekódování textů; index resource IDs, času a referencí
       ↓
Jednotná reprezentace klinických faktů s proveniencí
       ↓
Deterministická pravidla + cílená LLM extrakce z volného textu
       ↓
Kontrola úplnosti, detekce konfliktů, trendy, screening kritérií studií
       ↓
Výběr pasáží guidelines + grounded LLM syntéza / otázky k diskusi
       ↓
Strukturovaný výstup s důkazy; případná nezávislá kontrola tvrzení
       ↓
Společné a rolově filtrované UI → lékařské schválení → export
```

Doporučené hranice:

- **Deterministicky**: data/časové intervaly, numerické trendy, explicitní prahy, úplnost polí, formulovatelná pravidla pro klinické studie.
- **LLM**: extrakce významu z textových zpráv, porovnání souvisejících tvrzení, stručná syntéza, identifikace témat k diskusi. Jen s ověřitelnými zdroji.
- **Zdrojové materiály**: pro relativně krátké dodané guidelines může stačit index číslovaných pasáží bez vektorové DB.
- **Kritická výstupní kontrola**: každé tvrzení musí mít identifikovatelné doklady, případně explicitní `unknown` / `needs_review` stav.
- **Specializovaní agenti**: zvážit až po fungujícím single-pass pipeline; A/B porovnat náklady, rychlost, přesnost a detekci red flags proti jednoduché architektuře.

**[NÁVRH]** Role-based UI nad **jedním sdíleným modelem faktů** je bezpečnější pro konzistenci než čtyři nezávislé textové souhrny, ve kterých by se stejná hodnota mohla lišit.

## 9. FHIR / InterSystems IRIS / provozní integrace

**[MENTOR 1]** Doporučeno vyzkoušet **InterSystems IRIS** a FHIR server/REST API. V konzultaci padlo:

- vytvořit další FHIR instanci/endpoint pomocí připraveného setup skriptu či konfigurace v UI; při kopírování změnit **název instance a base URL**;
- nahrát dostupné JSON/FHIR bundly a vyzkoušet jejich čtení/uložení přes API;
- možnost uchovávat část interních dat v IRIS a ukládat pouze standardizované výstupy do FHIR;
- projít jednoduchý FHIR loop z „části 5 tutorialu“;
- následně exportovat a ukládat **schválené** rozhodnutí a plán jako strukturované FHIR informace pro další systémy;
- v produkčním kontextu může nemocniční informační systém (NIS) převzít data z FHIR integrační vrstvy; skutečné propojení konkrétního NIS se pro hackathon nepředpokládá automaticky.

**[OVĚŘIT]** Existenci setup skriptu, oprávnění na IRIS instanci, funkčnost zápisu do FHIR serveru, přesné FHIR endpointy a tutorial.

**[Terminologie]** Zápis „fire“ znamená **FHIR (HL7 Fast Healthcare Interoperability Resources)**. V poznámkách uvedené „dastra“ pravděpodobně označuje **DASTA**; detaily národních integračních standardů jsou mimo současný dataset a je třeba je ověřit. **Dodaná data jsou již ve FHIR R4**, pro MVP tedy není třeba budovat DASTA → FHIR konverzi. Nápad nechat LLM transformovat libovolná data do FHIR je obecná možnost, **nikoli nutnost ani validace korektnosti FHIR**.

**[NÁVRH]** Vývoj backendu a UI může běžet paralelně nad **dohodnutým JSON kontraktem**. FHIR/IRIS integraci lze přidat za normalizační vstup/výstup bez převázání celé UI architektury na konkrétní server.

## 10. Kvalita, validace, evaluace

**[ZADÁNÍ]** U každého AI tvrzení umožnit ověření zdrojového záznamu; nevymýšlet chybějící údaje. Zápis rozhodnutí zůstává pod kontrolou lékaře.

**[NÁVRH]** Praktická mini-evaluace nad P01 a P02 (později zbytek):

- **Faktická přesnost**: klinická fakta a biomarkery souhlasí s příslušnými zdrojovými IDs.
- **Úplnost klíčových informací**: zda role-based filtrování nevynechá relevantní red flag či preferenci pacienta.
- **Provenience**: každý red flag/tvrzení odkazuje na skutečnou FHIR resource a správný text/datum.
- **Falešná jistota**: rozlišit `verified`, `conflicting`, `missing`, `requires_review`; neinterpretovat „nenalezeno“ jako negativní nález.
- **Trial screening**: každé Z/V kritérium vyhodnoceno se zdrojem; zaznamenat neurčitost a konflikt údajů.
- **Efektivita**: latence analýzy, počet LLM volání, tokenový rozpočet, doba nalezení zdroje v UI.
- **Bezpečnost workflow**: schválený závěr nikdy nevznikne samotnou generací AI.

**Příklady scénářů:** P01 – rozdíl ECOG a pacientské soběstačnosti, únava + Hb, nová bolest kyčle, neznámý stav ESR1, aktuálnost stagingu; P02 – mozkové metastázy, léčba kortikoidy, údaje relevantní pro anti-HER2 a trial eligibility. Konkrétní očekávané odpovědi ověřovat proti časově příslušným podkladům, nikoli je předem hardcodovat jako „pravdu“.

## 11. Hodnoticí kritéria a demonstrace [ZADÁNÍ]

| Kritérium | Váha |
| --- | ---: |
| Klinická hodnota a UX pro MDT | 30 % |
| Konfigurovatelnost systému | 20 % |
| Technické řešení AI a spolehlivost | 20 % |
| Datová integrace a standardy | 15 % |
| Podpora MDT procesu a zodpovědná AI | 15 % |
| BONUS funkce | až +10 % |

**Pětiminutové demo:** zvolit konfiguraci → vygenerovat podklad → 30sekundový souhrn → kliknout na zdroj alespoň jednoho faktu a jednoho red flagu → ukázat možnosti z guidelines a kritéria studie → upravit a potvrdit rozhodnutí → export. Stručně objasnit model, grounding, kontrolu halucinací a ochranu dat.

**[NÁVRH prioritizace]** První fungující vertikální průchod nad P01, následně ověřit P02 a možnost přepnutí role. Před implementací bonusů zajistit konfigurovatelnost, citace, PROMs a lékařský závěr.

## 12. Otevřená rozhodnutí a otázky

1. Které **čtyři odborné role** chce tým konkrétně ukázat? Zadání povinně požaduje pouze alespoň tři.
2. Jak přesně má vypadat společný view vs. specializované view a přepínání rolí?
3. Rozsah práv: jen **UI perspektivy**, nebo i autentizace a **server-side** omezení přístupu k pacientům?
4. Má existovat formulář pro tvorbu nových PROMs otázek, nebo stačí dodané odpovědi?
5. Máme implementovat **multi-agent kontrolu**, nebo kvalitní jednoduchou pipeline s cílenou validací? Jak tento experiment měřit?
6. Co znamená „validita studií“ pro čistě fiktivní studijní dataset? Očekává mentor externí publikační screening jako bonus?
7. Jaký je přesný přístup k **InterSystems IRIS**, FHIR serveru, nastavení endpointů a zmíněnému tutorialu?
8. Stačí PDF/FHIR export, nebo lze v demu i reálně **zapsat FHIR resource**?
9. Je dostupná kontrolní sada **ground truth**, nebo má tým vytvořit vlastní testy?
10. Jaké části rozhodovacího a schvalovacího procesu se mají modelovat (předseda, podpis, nesouhlas, datum, odpovědnost)?

## 13. Instrukce pro coding agenty

1. Nejdříve identifikujte aktuální soubory a datový kontrakt. **Nepředpokládejte**, že doporučení mentora je hotové technické rozhodnutí.
2. Respektujte standardní klinickou a FHIR terminologii od prvního návrhu datového modelu. Zachovávejte kódové systémy, jednotky, stav a časový kontext údajů.
3. Zachovávejte identifikátor pacienta a **provenienci na úrovni každého zdrojového tvrzení** (`resourceType`, `id`, datace, dle možností přesný úsek dokumentu). Nepřenášejte fakta mezi pacienty.
4. Rozlišujte explicitní fakt, odvozený závěr, hypotézu, chybějící informaci, konflikt a AI návrh. Neprezentujte odhad jako ověřený klinický údaj.
5. **Neodvozujte autorizaci z odbornosti ani z UI filtru.** Backend musí v produkčním nasazení nezávisle kontrolovat přístupová oprávnění.
6. Při práci se studiemi **nepředstírejte existenci fiktivních RKT studií**. Zdrojová kritéria jsou závazným testovacím vstupem, nikoli medicínsky ověřeným protokolem.
7. Preferujte deterministicky testovatelnou logiku pro numerické prahy, čas, konzistenci a některá studijní kritéria. LLM používejte tam, kde přináší prokazatelnou hodnotu.
8. Pokud navrhnete multi-LLM workflow, jasně určete účel každého modelu, kontrolované invarianty, náklady a **nezávislý evaluační postup**. Vzájemný souhlas modelů není klinická verifikace.
9. Oddělte **AI návrh** od **lékařsky potvrzeného rozhodnutí** i na úrovni datového modelu, UI a exportu.
10. Upřednostněte **ověřitelný end-to-end průchod** před nehotovými bonusy. Nedávejte do repozitáře tajné klíče ani skutečná zdravotní data; zvažte důvěrnost dokumentů Asseco.

## 14. Primární zdroje tohoto dokumentu

1. Oficiální dokument: **„MDT Copilot – Asistovaná interpretace pro multidisciplinární onkologické konzilium“**, Asseco CE, kapitoly 1–6 (označeno `CONFIDENTIAL`).
2. Dataset: `README.md`, `Pxx_bundle.json`, `Pxx_pacient.md`, `bundles.ndjson`, dokumentace dotazníku, guidelines a studií.
3. Poznámky z **první konzultace**: `konzultace s mentorem k řešení výzvy(1).txt`.
4. Poznámky z **druhé konzultace**: `další koo,s  tim druhym datovym men.txt`.

*Tento soubor je interpretační a koordinační kontext; primární zdroje mají přednost. Otevřené otázky nejsou rozhodnutími o implementaci.*
