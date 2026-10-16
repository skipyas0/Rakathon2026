# MDT Copilot – obecné rady a postřehy ze tří konzultací

**Projekt:** Rakathon 2026, výzva Asseco MDT Copilot  
**Zdroje:** poznámky z první technicko-produktové konzultace, druhé datově/AI orientované konzultace a třetí konzultace s medičkou (16. 10. 2026).  
**Účel:** stručný pracovní kontext pro tým a coding agenty. **Nejde o specifikaci funkcí aplikace ani o popis průběhu MDT.**

> **Jak číst:** „Z konzultace“ označuje myšlenku zachycenou v neformálních poznámkách, nikoli ověřený požadavek. „Dopad pro tým“ je pracovní interpretace. Nejasné či sporné informace je nutné ověřit u zadavatelů. Přesné zadání a README datasetu mají přednost.

## 1. Strategické priority

- **Začít konceptem a malým funkčním jádrem.** První mentor několikrát zdůraznil, že problém je komplexní a nemá smysl zabřednout do detailů dříve, než bude jasná základní myšlenka a její přínos.
- **Najít skutečnou inovaci, nejen technickou demonstraci.** Zvlášť zdůrazněna byla perspektiva pacienta prostřednictvím **PROMs** (patient-reported outcome measures), která se podle prvního mentora v obdobných řešeních stále nedostatečně využívá.
- **Pracovat s klinickým kontextem, nikoli jen s izolovanými údaji.** Kombinace nálezů, potíží a pacientských preferencí může být důležitější než jednotlivé záznamy. Původní poznámky zmiňují i záměrné chyby v datech.
- **Neřešit zbytečně organizační problémy mimo jádro výzvy.** Druhý mentor výslovně nedoporučil zabývat se výběrem konkrétních lékařů. Připustil zjednodušení na čtyři odbornosti pro prototyp; toto číslo je jeho doporučení, ne univerzální popis klinické reality.

## 2. Praktické poznatky o zdravotnictví

- **Praxe je heterogenní.** Podle třetí konzultace existují významné rozdíly i v rámci jedné nemocnice. Nedělat z jedné zkušenosti obecně platné pravidlo.
- **Odbornosti se doplňují a překrývají.** Druhý mentor upozornil, že odborné role a jejich hierarchie jsou složitější než několik pevných kategorií. Třetí konzultace zároveň potvrdila význam interdisciplinárního pohledu a potřebu informací mimo úzkou specializaci.
- **Není samozřejmé, že každý odborník zná pacienta osobně nebo má úplný kontext.** Z třetí konzultace plyne důležitost kvalitních, srozumitelných a dohledatelných podkladů. Nejde o důkaz, že některá profese je vždy lépe informovaná než jiná.
- **Pacientské preference jsou klinicky relevantní.** Postoj k invazivní léčbě, prioritám a zátěži léčby může zásadně změnit prakticky přijatelný postup. Klinická vhodnost a pacientova ochota daný postup podstoupit jsou rozdílné otázky.
- **Klinická situace se vyvíjí v čase.** Historické údaje je třeba interpretovat v kontextu pozdější léčby, vyšetření a změn zdravotního stavu.

## 3. Kvalita dat, standardy a interoperabilita

- **FHIR (HL7 Fast Healthcare Interoperability Resources) je důležitá výchozí konvence.** První mentor doporučil získat s ním praktickou zkušenost, případně vyzkoušet **InterSystems IRIS**, FHIR server a lokální API pro čtení/import dat. Přesná infrastruktura nebyla v poznámkách potvrzena.
- **Není nutné uchovávat všechno v jednom systému.** Z konzultace zazněla možnost kombinovat interní práci s daty v IRIS a standardizovanou reprezentaci vybraných informací ve FHIR. Jde o možnost, nikoli architektonický požadavek.
- **Konkrétní technický tip:** mentor zmiňoval připravený skript pro nastavení další FHIR instance; při kopírování se musí změnit její **název i base URL**, alternativou je konfigurace v UI. Ověřit existenci skriptu, přístupy a odkazovanou **část 5 tutorialu**.
- **DASTA / eZdravie / NIS** zazněly jako kontext reálné nemocniční interoperability. Převod DASTA → FHIR není nutný pro dodaný hackathonový dataset, který je již ve FHIR. Výraz „dastra“ z poznámek je pravděpodobně DASTA, ale toto označení nebylo během konzultace potvrzeno.
- **Klinické kódy interpretovat včetně číselníku a kontextu.** V první konzultaci padla nejasná zmínka o kódu „43“; bez příslušného kódového systému nelze určit jeho význam.
- **Dodaný dataset má šest pacientů a záměrné nesrovnalosti.** Podle oficiálního `README.md` jsou všechna data **syntetická**, přestože v první konzultaci zaznělo i tvrzení o původně reálných anonymizovaných datech. Řiďte se dokumentací datasetu.

## 4. AI: spolehlivost, komplexita a náklady

- **Multi-agent / multi-LLM přístup stojí za experiment.** Zazněl návrh specializovaných modelů podle klinických oblastí a následné vzájemné či centrální kontroly. Podobná dvoustupňová kontrola byla zmíněna i pro přiřazování informací k odbornostem.

## 5. Uživatelská relevance a ochrana informací

- **Méně informací může znamenat lepší orientaci.** Druhý mentor doporučil omezovat nerelevantní obsah. Úplnost podkladových dat a stručnost jejich prezentace však nejsou totéž.
- **Perspektivy různých odborností mohou být odlišné.** Konzultace 2 doporučila oborově relevantní pohledy. Konkrétní podobu UI a proces používání aplikace tento dokument záměrně nespecifikuje.
- **Přístup k pacientským datům má být omezen oprávněními.** Druhý mentor popsal ideální model, v němž administrátor spravuje oprávnění a lékař vidí jen data pacientů, k nimž má přístup. Implementace plného nemocničního řízení oprávnění nebyla doporučena jako hlavní cíl prototypu.

## 6. Nejasnosti a informace k případnému ověření

- **Provozní detaily InterSystems:** dostupný server, přístupová práva, setup skript, lokální endpointy, tutorial. V první konzultaci zaznělo, že **Lubo** pracuje s obdobným systémem na Slovensku a mohl by dodat technické informace; totožnost a kontakt nejsou v poznámkách specifikovány.
- **Externí slovenské zdroje:** první mentor zmiňoval databáze klinických studií, standardních postupů a anonymizovaných/pseudonymizovaných pacientských dat. Konkrétní databáze, dostupnost a oprávnění nebyly doloženy.
- **Otázky v PROMs:** druhý mentor naznačil možnost, že odborníci sami formulují otázky; zapisovatel si příslušnou část konzultace nezachytil jistě. Nelze z toho dělat požadavek na implementaci.
- **Odpovědnost za finální klinické rozhodnutí:** první konzultace zdůrazňovala vedoucího, třetí konsenzus odborníků. To je otevřený rozpor v popisu praxe, nikoli podklad pro automatické rozhodnutí AI. Konkrétní proces je popsán v samostatném projektovém kontextu, zde se záměrně nerozebírá.
- **Jeden z dalších mentorů** byl v první konzultaci charakterizován spíše jako byznysově orientovaný a člen poroty. Jde o subjektivní neověřenou poznámku, nikoli technickou autoritu.

