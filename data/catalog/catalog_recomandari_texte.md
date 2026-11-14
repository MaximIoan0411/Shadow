# SHADOW — Catalog de recomandări și texte scurte

*NASA Space Apps Challenge 2026 · versiunea 1.0 · 13 noiembrie 2026*

> **Prototip de sprijin pentru decizie, nu dispozitiv medical.** Fiecare recomandare are o sursă. Cele marcate **NEVERIFICAT** sau care folosesc un prag **derivat** (ales de echipă) trebuie prezentate juriului ca ipoteze de proiectare. Pragurile numerice complete, cu sursa fiecăruia, sunt în `parameters.json`.

## Cuprins
1. Corecturi importante față de planul SHADOW
2. Catalogul de recomandări pe piloni
3. Texte scurte: funcția părților corpului
4. Texte scurte: de ce contează în spațiu (check-in)
5. Unde dovezile sunt slabe
6. Evenimentul solar real pentru simulator

## 1. Corecturi importante față de planul SHADOW

- **Imunitar — „63%”.** Cifra vine din Mishra et al. 2020, dar înseamnă **15 din 24 (62,5%)** de participanți cu ≥28 de zile de date înainte de simptome, într-o simulare retrospectivă a detecției în timp real (algoritmul CuSum). Nu înseamnă „63% din 32 de cazuri”. Autorii spun că valoarea probabil supraestimează detecția.
- **Imunitar — pragul de puls de noapte.** Regula „≥ +4 bpm peste mediana personală, 2 nopți la rând” (NightSignal) vine din **Alavi et al. 2022, Nature Medicine** (doi:10.1038/s41591-021-01593-2), nu din Mishra 2020. Sistemul prospectiv a alertat 67/84 (80%) de cazuri, cu o mediană de 3 zile înainte de simptome.
- **Imunitar — Rooney 2019.** 61% (14/23) pe ISS este corect, dar se referă la **eliminarea ADN-ului viral** în salivă sau urină, de obicei asimptomatică, nu la boală.
- **Oase — Robling 2002.** S-a încărcat **ulna** (membrul anterior al șobolanului), nu tibia. „~70% mai mult” e doar raportul a două câștiguri mici de BMC (≈11,7% vs 6,9%, valori NEVERIFICAT pe textul original). Cifre verificate (tot pe șobolani): forța ultimă +87% vs +64%, energia la rupere +165% vs +94% (Robling 2002, JBMR).
- **Oase — rata de pierdere.** „1–1,5%/lună” e media fără ARED. Cu ARED: col femural −0,32, șold total −0,64, coloană −0,47 %/lună (NASA Bone Evidence Report 2024, Tabelul 2).
- **Comportamental — PVT-B.** Basner, Mollicone & Dinges 2011 a apărut în **Acta Astronautica 69:949–959**, nu în Aviat Space Environ Med. Lapsus = RT ≥ 355 ms. Metrica cea mai sensibilă e **media 1/RT** (viteza de răspuns), nu media RT.
- **Comportamental — Van Dongen 2003.** Grupurile au avut 4 h sau 6 h de **timp în pat** pe noapte (plus un grup de control de 8 h), timp de 14 zile. Deficitele au fost echivalente cu până la 2 nopți nedormite. Somnolența subiectivă a crescut doar puțin, iar subiecții au fost în mare parte inconștienți de deficite.
- **Comportamental — tastare.** Acien 2022 nu dă praguri procentuale pe trăsături, doar AUC 72–80%, pe 14 subiecți, în inerție de somn. Rata de Backspace e puțin sensibilă (<0,1 SD; Fang et al. 2026, n=366): **hold time și viteza** sunt candidați mai buni. Raportul NTRS 20210022711 e o prezentare de concept, fără date.
- **Cardiovascular — două baseline-uri.** Pulsul de repaus **nu crește** în medie în zbor, iar tensiunea sistolică **scade** normal. SHADOW trebuie să compare valorile din zbor cu un baseline din zbor, altfel adaptarea normală apare ca alarmă.
- **Cardiovascular — predictori.** Pierderea de volum plasmatic (5–19%) **nu** separă cine leșină de cine nu. Lee 2015 a folosit tilt la 80° timp de 10 minute, nu un test în picioare.
- **Radiații — doza spre Marte.** Valoarea de 1,84 mSv/zi (Zeitlin 2013) a fost revizuită de echipa RAD la **1,58 ± 0,22 mSv/zi**; folosiți 1,58. ISS: 0,731 mSv/zi (ian.–feb. 2019). Suprafața Lunii: 1,369 mSv/zi.
- **Radiații — pagina CSA.** Pagina CSA din 26.02.2026 e o știre despre spectrometrul de neutroni CANS. Singura cifră e „~30% din radiația pe ISS vine de la neutroni”; nu conține praguri.
- **Comunicare — Marte.** Întârzierea într-un sens e de **3,0–22,3 min**, calculată din distanțele NSSDC. Conjuncția solară înseamnă ~14 zile fără comenzi, dar doar ~2 zile fără niciun semnal.
- **Numele riscurilor HRP.** Mai multe riscuri au fost comasate. Intoleranța ortostatică face acum parte din *Risk of Cardiovascular Adaptations…*. Capacitatea aerobă și masa musculară fac parte din *Risk of Mission Performance Decrements… Reduced Cardiorespiratory and Musculoskeletal Fitness*. Riscul imunitar se numește acum *Risk of In Mission Impacts, Adverse Health Events or Long-Term Health Impacts due to Altered Immune Response*. Numele exacte și URL-urile sunt mai jos și în JSON.

## 2. Catalogul de recomandări pe piloni

Legenda: ✓ = VERIFICAT pe sursă · ⚠ = NEVERIFICAT sau prag derivat (de prezentat ca ipoteză).

### Comportamental și cognitiv (Tastatura)

**Riscuri NASA HRP:** [Risk of Adverse Cognitive or Behavioral Changes and Psychiatric Disorders Leading to In-mission Health and Performance and Long-term Health Effects](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=99); [Risk of Performance Decrements and Adverse Health Outcomes Resulting from Sleep Loss, Circadian Desynchronization, and Work Overload](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=100)

**Nivel 1 — Te descurci singur**

1. ✓ **Când:** PVT-B sau tastarea arată abatere față de baseline-ul personal (ex. 1/RT sub prag), chiar dacă astronautul se simte odihnit  
   **Ce faci:** Nu te baza pe senzația subiectivă: refă PVT-B-ul de 3 minute înaintea oricărei sarcini critice și amân-o, dacă se poate, până la normalizare.  
   *Sursa:* [Van Dongen HPA, Maislin G, Mullington JM, Dinges DF. (2003). The cumulative cost of additional wakefulness: dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. Sleep 26(2):117-126. Erratum: Sleep 2004;27(4):600. + Evidence Report NASA 2016 (secțiunea Chronic Sleep Loss)](https://pubmed.ncbi.nlm.nih.gov/12683469/)
2. ✓ **Când:** Abatere susținută (mai multe sesiuni) după nopți scurte  
   **Ce faci:** Prioritizează o oportunitate de somn mai lungă (extensie/recuperare de somn) în următoarele nopți; o singură noapte de recuperare poate să nu fie suficientă.  
   *Sursa:* [Flynn-Evans E, Gregory K, Arsintescu L, Whitmire A. (2016). Evidence Report: Risk of Performance Decrements and Adverse Health Outcomes Resulting from Sleep Loss, Circadian Desynchronization, and Work Overload. NASA Human Research Program, Behavioral Health and Performance Element (Approved for Public Release: April 11, 2016). (Banks et al.: recuperare dependentă de doză; o noapte insuficientă)](https://humanresearchroadmap.nasa.gov/Evidence/reports/Sleep.pdf)
3. ✓ **Când:** Somnolență/abatere în timpul zilei și există fereastră pentru pauză  
   **Ce faci:** Dacă faci un pui de somn, păstrează-l scurt (~10 minute) și nu începe sarcini critice imediat după trezire; somnul de 30 min a afectat performanța până la o oră (inerție de somn). Programează pui de somn în mod controlat, pentru a nu deregla ritmul circadian.  
   *Sursa:* [Flynn-Evans E, Gregory K, Arsintescu L, Whitmire A. (2016). Evidence Report: Risk of Performance Decrements and Adverse Health Outcomes Resulting from Sleep Loss, Circadian Desynchronization, and Work Overload. NASA Human Research Program, Behavioral Health and Performance Element (Approved for Public Release: April 11, 2016). (Hilditch et al. 2016; observații Mars-520 despre napping)](https://humanresearchroadmap.nasa.gov/Evidence/reports/Sleep.pdf)
4. ✓ **Când:** Scădere a vitezei de răspuns înaintea unei sarcini cu cerințe mari de vigilență  
   **Ce faci:** Folosește cofeina strategic (doză planificată înaintea sarcinii), nu aproape de ora de somn: astronauții care au folosit stimulente au raportat că adorm mai greu.  
   *Sursa:* [Flynn-Evans E, Gregory K, Arsintescu L, Whitmire A. (2016). Evidence Report: Risk of Performance Decrements and Adverse Health Outcomes Resulting from Sleep Loss, Circadian Desynchronization, and Work Overload. NASA Human Research Program, Behavioral Health and Performance Element (Approved for Public Release: April 11, 2016). (Wyatt et al. 2004; Whitmire et al. 2013)](https://humanresearchroadmap.nasa.gov/Evidence/reports/Sleep.pdf)
5. ✓ **Când:** Abateri care apar la ore neobișnuite / după schimbări de program (semn de desincronizare circadiană)  
   **Ce faci:** Respectă programul de iluminare al stației (LED/SSLA care simulează ciclul lumină-întuneric) și orele fixe de somn; folosește timpul alocat pentru relaxare și autoîngrijire.  
   *Sursa:* [NASA HFBP. Risk from Inadequate Sleep and Irregular Schedules (pagină de referință NASA). + Evidence Report NASA 2016 (SSLA)](https://www.nasa.gov/reference/risk-from-inadequate-sleep-and-irregular-schedules/)
6. ✓ **Când:** Abateri de tastare/PVT însoțite de stare de spirit scăzută sau retragere socială  
   **Ce faci:** Aplică strategii de autoîngrijire recomandate de NASA: jurnal regulat, contact virtual cu familia, activități care reduc monotonia (ex. îngrijirea plantelor, privitul pe fereastră).  
   *Sursa:* [NASA HFBP. Risk of Behavioral Changes and Psychiatric Disorders (pagină de referință NASA).](https://www.nasa.gov/reference/risk-of-behavioral-conditions-and-psychiatric-disorders/)

**Nivel 2 — Anunți ofițerul medical**

1. ✓ **Când:** Abatere PVT-B peste pragul derivat (≥~1,24 SD față de baseline la 1/RT sau lapsusuri) pe mai multe sesiuni/zile, sau înainte de o operațiune critică (prag de proiectare, nu publicat)  
   **Ce faci:** Anunță ofițerul medical de la bord (CMO): evaluează somnul, volumul de muncă și orice medicație de somn sau de stimulare. Medicația de somn este contramăsura cea mai folosită pe ISS, iar efectul ei asupra inerției de somn la trezire forțată este încă studiat.  
   *Sursa:* [Flynn-Evans E, Gregory K, Arsintescu L, Whitmire A. (2016). Evidence Report: Risk of Performance Decrements and Adverse Health Outcomes Resulting from Sleep Loss, Circadian Desynchronization, and Work Overload. NASA Human Research Program, Behavioral Health and Performance Element (Approved for Public Release: April 11, 2016). (Executive summary: countermeasures; sleep inertia with hypnotics)](https://humanresearchroadmap.nasa.gov/Evidence/reports/Sleep.pdf)
2. ✓ **Când:** Abateri comportamentale persistente (tastare + PVT) împreună cu modificări de dispoziție, somn sau comportament raportate de astronaut sau de echipaj  
   **Ce faci:** CMO face o evaluare structurată și documentează; simptomele comportamentale nedetectate sau tratate inadecvat pot evolua spre tulburări psihiatrice.  
   *Sursa:* [NASA Human Research Roadmap. Risk of Adverse Cognitive or Behavioral Changes and Psychiatric Disorders Leading to In-mission Health and Performance and Long-term Health Effects (Short Title: Behavioral Health). Last Published 05/13/25. (Risk Statement și HSRB State of Knowledge)](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=99)

**Nivel 3 — Trimiți pe Pământ**

1. ✓ **Când:** Abaterea persistă în ciuda contramăsurilor de nivel 1–2 sau apare la mai mulți membri ai echipajului (suspiciune de supraîncărcare/probleme de program)  
   **Ce faci:** Cere Pământului replanificarea programului (scăderea volumului de muncă, ferestre de somn protejate); HRR documentează supraîncărcarea și problemele de programare în zbor.  
   *Sursa:* [NASA Human Research Roadmap. Risk of Performance Decrements and Adverse Health Outcomes Resulting from Sleep Loss, Circadian Desynchronization, and Work Overload (Short Title: Sleep). Last Published 05/13/25. (HSRB State of Knowledge)](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=100)
2. ✓ **Când:** Semne comportamentale/psihologice care nu se ameliorează la bord  
   **Ce faci:** Organizează o conferință privată cu profesioniștii medicali/de sănătate comportamentală de pe Pământ; în misiunile îndepărtate ia în calcul întârzierea comunicațiilor (până la 42 min în misiunile în spațiul îndepărtat, conform prezentării NASA Beard et al. 2021) și trimite pachetul de date în avans.  
   *Sursa:* [NASA HFBP. Risk of Behavioral Changes and Psychiatric Disorders (pagină de referință NASA). + Beard BL, Russell B, Krihak M, Burian B, Noel J, Beaugrand D, Shaw T, Pletcher D, Martin K. (2021). Supporting Crew Medical Decisions on Deep Space Missions: Real-Time Performance Monitoring. Prezentare, 11th IAASS Conference 2021 (virtual). NASA NTRS 20210022711.](https://www.nasa.gov/reference/risk-of-behavioral-conditions-and-psychiatric-disorders/)

### Cardiovascular (Inima)

**Riscuri NASA HRP:** [Risk of Cardiovascular Adaptations Contributing to Adverse Mission Performance and Health Outcomes](https://www.nasa.gov/reference/risk-of-cardiovascular-adaptations/); [Risk of Mission Performance Decrements and Adverse Health Outcomes Resulting from Reduced Cardiorespiratory and Musculoskeletal Fitness](https://www.nasa.gov/reference/risk-of-reduced-cardiorespiratory-and-musculoskeletal-fitness/)

**Nivel 1 — Te descurci singur**

1. ✓ **Când:** Zilnic în zbor, mai ales dacă pulsul la efort submaximal standardizat crește >3 % față de media personală sau scorul de fitness scade.  
   **Ce faci:** Respectă prescripția zilnică de exercițiu aerob și de rezistență (~1,5 h/zi, 6–7 zile/săpt.) și include sesiunile de intensitate mare prescrise; refă testul submaximal standardizat în aceleași condiții.  
   *Sursa:* [NASA HRP, pagina riscului de fitness; Moore et al. 2014 (via Fitness Evidence Report p.34); CV Evidence Report p.30–31 (English 2020)](https://www.nasa.gov/reference/risk-of-reduced-cardiorespiratory-and-musculoskeletal-fitness/)  
   *Notă:* Exercițiul viguros a fost asociat cu o scădere mai mică a VO2peak (CV ER: −6 % vs −15 %), dar Fitness ER raportează pentru același studiu −7 %/−10 %.
2. ⚠ NEVERIFICAT **Când:** La check-in: tensiune sistolică în zbor sub baseline-ul pre-zbor cu până la ~14 mmHg, fără simptome.  
   **Ce faci:** Nu acționa: e adaptarea așteptată la microgravitație. Notează valoarea; aplicația o compară cu baseline-ul tău din zbor, nu cu cel de pe Pământ.  
   *Sursa:* [Norsk P et al. 2015 J Physiol 593:573-584; Fu Q et al. 2019 Circulation 140:729-738](https://doi.org/10.1113/jphysiol.2014.284869)  
   *Notă:* Cifrele sunt confirmate doar în abstract.
3. ✓ **Când:** În ultimele 12–20 h înainte de aterizare / revenirea în gravitație.  
   **Ce faci:** Urmează protocolul de încărcare cu fluide și sare prescris (de ex. 18–20 ml/kg soluție salină, de 3–4 ori cu mesele) și îmbracă hainele de compresie (Kentavr/AGS/compresie graduală) conform instrucțiunilor.  
   *Sursa:* [CV Evidence Report (2022) p.31–35 PDF; Lee SMC et al. 2020 Front Physiol 11:784; pagina NASA CV Risk ('Lower-body compression garments and drinking lots of fluids prior to landing')](https://www.nasa.gov/reference/risk-of-cardiovascular-adaptations/)  
   *Notă:* Eficacitatea încărcării cu fluide pe volumul plasmatic nu a fost demonstrată direct după misiuni lungi (CV ER p.32).
4. ✓ **Când:** În primele ore–zile după aterizare (sau după coborârea pe Lună/Marte), la orice amețeală la ridicare.  
   **Ce faci:** Evită activitățile care provoacă hipotensiune ortostatică (ridicare bruscă, stat mult în picioare nemișcat), păstrează compresia, și așază-te/întinde-te imediat la amețeală; fă testul de ridicare din aplicație doar în prezența unui coleg.  
   *Sursa:* [CV Evidence Report (2022) p.26 PDF ('flight surgeons guide astronauts to avoid activities that may provoke the onset of orthostatic hypotension'); Lee SMC et al. 2015 Aerosp Med Hum Perform 86:A54-A67](https://humanresearchroadmap.nasa.gov/Evidence/reports/Cardio%20Risk%20EB%202022%20FINAL_4-3-2023.pdf)  
   *Notă:* Regula 'test doar cu un coleg prezent' e o alegere de siguranță a prototipului.
5. ✓ **Când:** Înainte de fiecare check-in de puls/HRV/tensiune.  
   **Ce faci:** Măsoară în aceleași condiții (aceeași oră, aceeași poziție, după 5 min de repaus, înainte de exercițiu) ca abaterile față de baseline să fie interpretabile.  
   *Sursa:* [Buchheit M 2014 Front Physiol 5:73 (interpretare individuală ținând cont de eroarea de măsurare și SWC; înregistrări de 5 min în repaus)](https://doi.org/10.3389/fphys.2014.00073)  
   *Notă:* Sursa e din medicina sportivă, nu din zboruri spațiale.

**Nivel 2 — Anunți ofițerul medical**

1. ⚠ NEVERIFICAT **Când:** Puls de repaus cu media pe 7 zile > baseline + 1×CV individual timp de ≥3 zile, sau lnRMSSD < baseline − 0,5×CV, ÎMPREUNĂ cu simptome (palpitații, amețeală, oboseală neobișnuită).  
   **Ce faci:** Anunță ofițerul medical de la bord (CMO) pentru reevaluare (măsurare repetată, ECG dacă e disponibil) și conferință medicală privată cu medicul de zbor.  
   *Sursa:* [CV Evidence Report (2022) p.79 PDF (cel puțin doi membri ai echipajului ISS au pregătire medicală suplimentară pentru probleme mai puțin urgente, cu sprijinul medicului de zbor); Buchheit 2014 pentru logica pragului](https://humanresearchroadmap.nasa.gov/Evidence/reports/Cardio%20Risk%20EB%202022%20FINAL_4-3-2023.pdf)  
   *Notă:* Pragul numeric de escaladare nu e publicat pentru astronauți; rolul CMO e verificat.
2. ⚠ NEVERIFICAT **Când:** Umflare, durere sau senzație de presiune nouă la gât (mai ales pe stânga), durere de cap unilaterală nouă sau umflare a feței peste cea obișnuită din zbor.  
   **Ce faci:** Anunță CMO; acesta contactează medicii de pe Pământ pentru ecografie ghidată a venei jugulare (s-au găsit flux stagnant la 6/11 și un tromb ocluziv tratat la bord).  
   *Sursa:* [NASA HSRB CV Risk – Concern of Venous Thromboembolism; CV Evidence Report (2022) p.19–21 PDF (Marshall-Goebel 2019; Pavela 2022)](https://www.nasa.gov/directorates/esdmd/hhp/cv-risk/)  
   *Notă:* Datele de flux și tromboză sunt verificate; lista de simptome de declanșare e derivată (trombul descris a fost asimptomatic, deci simptomele pot lipsi).
3. ⚠ NEVERIFICAT **Când:** La testul de ridicare după revenirea în gravitație: scădere TAS ≥20 mmHg sau TAD ≥10 mmHg în 3 min, ori creștere a pulsului ≥30 bpm față de valoarea în decubit, sau presincopă.  
   **Ce faci:** Oprește testul, întinde-te, anunță CMO / medicul de zbor; nu relua activitatea în picioare până la evaluare.  
   *Sursa:* [Freeman R et al. 2011 Clin Auton Res 21:69-72 (criterii de consens – text necitit); CV Evidence Report p.25–26 PDF (incidența presincopei)](https://doi.org/10.1007/s10286-011-0119-5)  
   *Notă:* Criteriile numerice trebuie confirmate pe textul consensului.

**Nivel 3 — Trimiți pe Pământ**

1. ✓ **Când:** Sincopă (pierderea cunoștinței), palpitații susținute/ritm neregulat, durere toracică, sau suspiciune de tromboză venoasă.  
   **Ce faci:** CMO inițiază răspunsul de urgență și contactează imediat medicul de zbor de pe Pământ (pe orbita joasă: întârziere ~2 s, revenire pe Pământ posibilă); pe misiuni spre Marte echipajul trebuie să poată stabiliza autonom.  
   *Sursa:* [CV Evidence Report (2022) p.79 PDF (Distance from Earth); p.13 PDF (episod de tahicardie ventriculară nesusținută de 14 bătăi); pagina NASA CV Risk (aritmii, cheaguri)](https://humanresearchroadmap.nasa.gov/Evidence/reports/Cardio%20Risk%20EB%202022%20FINAL_4-3-2023.pdf)  
   *Notă:* Nu e protocol medical NASA; prototipul doar recomandă escaladarea.
2. ⚠ NEVERIFICAT **Când:** Pierdere de fitness aerob >20 % față de pre-zbor la testul periodic, sau puls la efort submaximal în creștere în ciuda respectării prescripției.  
   **Ce faci:** Trimite datele specialiștilor de exercițiu de pe Pământ pentru revizuirea prescripției (intensitate, volum).  
   *Sursa:* [NASA HRP, pagina riscului de fitness (auto-evaluări periodice folosite pentru optimizarea antrenamentului; 12–38 % pierd >20 %)](https://www.nasa.gov/reference/risk-of-reduced-cardiorespiratory-and-musculoskeletal-fitness/)  
   *Notă:* Pragul de 20 % e o categorie descriptivă NASA, nu un criteriu operațional publicat.
3. ✓ **Când:** Înainte de aterizare după o misiune lungă, pentru astronauți cu risc crescut (femei, presincopă anterioară, tensiune/TAD scăzute în decubit față de baseline).  
   **Ce faci:** Echipa de pe Pământ planifică ziua aterizării: activități reduse, suport medical și recuperare prelungită.  
   *Sursa:* [Lee SMC et al. 2015 Aerosp Med Hum Perform 86(12 Suppl):A54-A67 (concluzie: planificatorii și medicii să anticipeze adaptarea activităților și a suportului medical); CV Evidence Report p.24–28 PDF](https://doi.org/10.3357/AMHP.EC08.2015)  
   *Notă:* Factorii de risc individuali provin din studii mici (Waters 2002, Charles 1999).

### Imunitar (Santinela)

**Riscuri NASA HRP:** [Risk of In Mission Impacts, Adverse Health Events or Long-Term Health Impacts due to Altered Immune Response](https://humanresearchroadmap.nasa.gov/Risks/?i=85)

**Nivel 1 — Te descurci singur**

1. ✓ **Când:** Alertă galbenă: pulsul mediu de noapte e cu +3 bpm peste mediana personală, sau o singură noapte cu ≥ +4 bpm (prag din NightSignal; folosirea lui ca nivel 1 e o alegere SHADOW).  
   **Ce faci:** Completează în aplicație jurnalul scurt de context: simptome (tuse, febră, durere de cap, oboseală), somn scurt, stres, efort intens. Remăsoară noaptea următoare. În studiu, alertele au fost declanșate și de stres sau alte evenimente fără legătură cu o infecție, iar participanții au adnotat alertele prin chestionare.  
   *Sursa:* [Alavi A, Bogu GK, Wang M, Rangan ES, Brooks AW, et al., Snyder MP. 2022. Real-time alerting system for COVID-19 and other stress events using wearable data. Nature Medicine 28:175–184.](https://www.nature.com/articles/s41591-021-01593-2)
2. ✓ **Când:** Orice alertă imună activă sau somn sub baseline-ul personal.  
   **Ce faci:** Prioritizează somnul și managementul oboselii conform programului (somnul și ritmul circadian sunt legate direct de funcția imună; pe orbită somnul e redus și ritmurile sunt dezaliniate). Folosește serviciile de suport comportamental/oboseală disponibile.  
   *Sursa:* [Crucian BE, Choukèr A, Simpson RJ, Mehta S, Marshall G, Smith SM, et al., Sams C. 2018. Immune System Dysregulation During Spaceflight: Potential Countermeasures for Deep Space Exploration Missions. Frontiers in Immunology 9:1437.](https://www.frontiersin.org/articles/10.3389/fimmu.2018.01437/full)
3. ✓ **Când:** Permanent, ca prevenție (nu doar la alertă).  
   **Ce faci:** Respectă programul prescris de exerciții aerobice și de rezistență. În Evidence Report-ul HRP, un fitness pre-zbor mai bun s-a asociat cu un risc mai mic de reactivare virală (29–39%), iar regimul candidat de contramăsuri include exerciții aerobice și de rezistență, dietă, suplimente și exerciții VR pentru reducerea stresului.  
   *Sursa:* [Mehta S, Crucian B. 2022. Evidence Report: Risk of Crew Adverse Health Event Due to Altered Immune Response. NASA Human Research Program, Human Health Countermeasures Element, Johnson Space Center (Approved for Public Release June 1, 2022).](https://humanresearchroadmap.nasa.gov/evidence/reports/IMMUNE%20EB%20Update%202021%20v02%20FINAL_6-15-22.pdf)
4. ✓ **Când:** Zilnic, mai ales în prima lună de misiune (perioada cu cele mai multe evenimente notabile).  
   **Ce faci:** Autoverificare rapidă a pielii și buzelor (erupții, roșeață cu iritație, herpes labial) și a simptomelor respiratorii superioare; notează-le în aplicație. Erupțiile au fost evenimentul cel mai raportat pe ISS (1,12/an de zbor).  
   *Sursa:* [Crucian B, Babiak-Vazquez A, Johnston S, Pierson DL, Ott CM, Sams C. 2016. Incidence of clinical symptoms during long-duration orbital spaceflight. International Journal of General Medicine 9:383–391.](https://doi.org/10.2147/IJGM.S114188)
5. ✓ **Când:** Permanent.  
   **Ce faci:** Respectă meniul și suplimentarea nutrițională prescrise. Crucian 2018 discută nutriția și alimentele funcționale ca o contramăsură imună (meniul ISS e sărac în fructe și legume).  
   *Sursa:* [Crucian BE, Choukèr A, Simpson RJ, Mehta S, Marshall G, Smith SM, et al., Sams C. 2018. Immune System Dysregulation During Spaceflight: Potential Countermeasures for Deep Space Exploration Missions. Frontiers in Immunology 9:1437.](https://www.frontiersin.org/articles/10.3389/fimmu.2018.01437/full)

**Nivel 2 — Anunți ofițerul medical**

1. ✓ **Când:** Alertă roșie NightSignal: puls mediu de noapte ≥ +4 bpm peste mediana personală două nopți la rând, mai ales dacă temperatura pielii depășește pragul SHADOW derivat sau apar simptome.  
   **Ce faci:** Anunță ofițerul medical de la bord (CMO) cu graficul puls/temperatură vs baseline și jurnalul de simptome. Doar CMO decide evaluarea sau tratamentul simptomatic din farmacia ISS (antihistaminice, antiinflamatoare, antimicrobiene); aplicația nu recomandă medicamente.  
   *Sursa:* [Alavi A, Bogu GK, Wang M, Rangan ES, Brooks AW, et al., Snyder MP. 2022. Real-time alerting system for COVID-19 and other stress events using wearable data. Nature Medicine 28:175–184.](https://www.nature.com/articles/s41591-021-01593-2)
2. ✓ **Când:** Erupție cutanată, herpes labial (posibilă reactivare HSV-1/VZV), simptome alergice sau respiratorii superioare apărute în misiune.  
   **Ce faci:** Raportează la CMO și descrie localizarea și evoluția. Reactivarea herpetică e de obicei asimptomatică, dar uneori produce leziuni cu virus infecțios, deci contează și pentru ceilalți membri ai echipajului.  
   *Sursa:* [Rooney BV, Crucian BE, Pierson DL, Laudenslager ML, Mehta SK. 2019. Herpes Virus Reactivation in Astronauts During Spaceflight and Its Application on Earth. Frontiers in Microbiology 10:16.](https://www.frontiersin.org/articles/10.3389/fmicb.2019.00016/full)

**Nivel 3 — Trimiți pe Pământ**

1. ✓ **Când:** Eveniment „notabil” după definiția NASA: simptomul durează >1 săptămână, se repetă sau se intensifică, sau nu răspunde la tratament.  
   **Ce faci:** CMO transmite cazul medicilor de zbor (flight surgeons) de pe Pământ, cu seria de date vs baseline. Pe misiuni cu întârziere de comunicare, pachetul de date se trimite asincron.  
   *Sursa:* [Mehta S, Crucian B. 2022. Evidence Report: Risk of Crew Adverse Health Event Due to Altered Immune Response. NASA Human Research Program, Human Health Countermeasures Element, Johnson Space Center (Approved for Public Release June 1, 2022).](https://humanresearchroadmap.nasa.gov/evidence/reports/IMMUNE%20EB%20Update%202021%20v02%20FINAL_6-15-22.pdf)
2. ✓ **Când:** Alerte roșii repetate (cluster de ≥2 zile roșii consecutive) care nu se rezolvă, sau combinate cu febră/simptome persistente (escaladare propusă de SHADOW).  
   **Ce faci:** Escaladare la echipa medicală de la sol pentru evaluare și eventuale probe biologice (salivă/sânge/urină pentru markeri virali și imuni, conform direcției de cercetare HRP).  
   *Sursa:* [NASA. Risk of Altered Immune System Responses (NASA HRP risk page; page last updated May 16, 2025).](https://www.nasa.gov/reference/risk-of-altered-immune-system-responses/)
3. ✓ **Când:** După aterizare: până la ~30 de zile post-ISS (eliminare VZV/CMV documentată).  
   **Ce faci:** Echipa medicală de la sol să fie informată despre riscul de transmitere a virusurilor eliminate către nou-născuți, adulți seronegativi sau persoane imunocompromise din jurul astronautului.  
   *Sursa:* [Rooney BV, Crucian BE, Pierson DL, Laudenslager ML, Mehta SK. 2019. Herpes Virus Reactivation in Astronauts During Spaceflight and Its Application on Earth. Frontiers in Microbiology 10:16.](https://www.frontiersin.org/articles/10.3389/fmicb.2019.00016/full)

### Oase și mușchi (Încărcarea)

**Riscuri NASA HRP:** [Risk of Bone Fracture due to Spaceflight-induced Changes to Bone](https://humanresearchroadmap.nasa.gov/Risks/?i=77); [Risk of Mission Performance Decrements and Adverse Health Outcomes Resulting from Reduced Cardiorespiratory and Musculoskeletal Fitness](https://humanresearchroadmap.nasa.gov/Risks/?i=180)

**Nivel 1 — Te descurci singur**

1. ✓ **Când:** Volumul sau sarcina zilnică de exercițiu (rezistență + aerob) sub planul personal; sau orice zi fără exercițiu  
   **Ce faci:** Completează prescripția: ~1,5 h/zi de rezistență și aerob, 6-7 zile/săptămână, cu accent pe exerciții încărcate pentru membrele inferioare (ARED).  
   *Sursa:* [NASA HRP (2025). Risk of Reduced Cardiorespiratory and Musculoskeletal Fitness (pagina oficială, actualizată 16 mai 2025)](https://www.nasa.gov/reference/risk-of-reduced-cardiorespiratory-and-musculoskeletal-fitness/)
2. ✓ **Când:** Sarcina folosită la ARED sub sarcina din baseline-ul personal  
   **Ce faci:** Crește progresiv sarcina spre nivelul pre-zbor. ARED permite până la 600 lbf (1675 N), iar sarcina mare, împreună cu nutriția adecvată, a păstrat DMO la șold în studiul Smith 2012 (n=5).  
   *Sursa:* [Smith SM, Heer MA, Shackelford LC, Sibonga JD, Ploutz-Snyder L, Zwart SR (2012). Benefits for bone from resistance exercise and nutrition in long-duration spaceflight: Evidence from biochemistry and densitometry. J Bone Miner Res 27(9):1896-1906](https://doi.org/10.1002/jbmr.1647)
3. ✓ **Când:** Masa corporală scade față de baseline-ul personal sau aportul energetic e sub plan  
   **Ce faci:** Respectă aportul energetic și suplimentul de vitamina D din plan. Beneficiul ARED pentru os a fost observat împreună cu menținerea masei corporale și vitamina D nominală.  
   *Sursa:* [Smith SM, Heer MA, Shackelford LC, Sibonga JD, Ploutz-Snyder L, Zwart SR (2012). Benefits for bone from resistance exercise and nutrition in long-duration spaceflight: Evidence from biochemistry and densitometry. J Bone Miner Res 27(9):1896-1906](https://doi.org/10.1002/jbmr.1647)
4. ✓ **Când:** Planificarea sesiunilor de încărcare (impact/rezistență) în ziua respectivă  
   **Ce faci:** Dacă orarul permite, împarte încărcarea în 2-4 sesiuni mai scurte, la câteva ore distanță, în loc de una lungă. Atenție: dovada provine DOAR din studii pe șobolani (Robling 2000-2002) și nu e o procedură NASA.  
   *Sursa:* [Robling AG, Hinant FM, Burr DB, Turner CH (2002). Improved bone structure and strength after long-term mechanical loading is greatest if loading is separated into short bouts. J Bone Miner Res 17(8):1545-1554](https://pubmed.ncbi.nlm.nih.gov/12162508/)
5. ✓ **Când:** Testul periodic de fitness lipsește sau e întârziat  
   **Ce faci:** Fă autoevaluarea periodică de fitness (forță/rezistență) pentru actualizarea abaterii față de baseline.  
   *Sursa:* [NASA HRP (2025). Risk of Reduced Cardiorespiratory and Musculoskeletal Fitness (pagina oficială, actualizată 16 mai 2025)](https://www.nasa.gov/reference/risk-of-reduced-cardiorespiratory-and-musculoskeletal-fitness/)

**Nivel 2 — Anunți ofițerul medical**

1. ✓ **Când:** Forța (ex. 1RM ARED sau test izokinetic genunchi/gleznă) scade >10% sub baseline-ul personal la 2 teste consecutive (prag derivat)  
   **Ce faci:** Anunță ofițerul medical de la bord pentru verificarea aderenței și a nutriției și pentru ajustarea locală a prescripției de exercițiu.  
   *Sursa:* [NASA Human Research Program (2024). Evidence Report: Risk of Mission Performance Decrements and Adverse Health Outcomes Resulting from Reduced Cardiorespiratory and Musculoskeletal Fitness (FINAL 03.04.2024)](https://humanresearchroadmap.nasa.gov/evidence/reports/Evidence%20report%20aerobic%20and%20muscle_FINAL%204-3-2024.pdf)
2. ✓ **Când:** Aderența la exercițiu sub plan mai multe zile consecutiv (ex. echipament defect, boală, accidentare) – prag de prototip  
   **Ce faci:** Anunță ofițerul medical pentru un plan alternativ de încărcare. Fără rezistență cu sarcină mare, ratele de pierdere osoasă se apropie de cele pre-ARED (~1-1,5%/lună).  
   *Sursa:* [NASA Human Research Program (2024). Evidence Report: Risk of Bone Fracture due to Spaceflight-induced Changes to Bone (HRP-F07-ERFT.R2, 18.07.2024)](https://humanresearchroadmap.nasa.gov/evidence/reports/Bone%20Fracture%20Evidence%20Report_07-18-2024.pdf)

**Nivel 3 — Trimiți pe Pământ**

1. ✓ **Când:** Forța scade >20% sub baseline (prag derivat) sau pierderea cumulată estimată de DMO depășește 10% la șold/coloană (prag derivat din criteriul Bone Summit)  
   **Ce faci:** Contactează echipa medicală de la sol (flight surgeon) pentru reevaluarea prescripției și pentru o eventuală contramăsură farmacologică. Bisfosfonatul + ARED a prevenit scăderea DMO la șold (Sibonga 2019), dar decizia aparține medicilor de pe Pământ.  
   *Sursa:* [Sibonga J, Matsumoto T, Jones J, Shapiro J, Lang T, Shackelford L, Smith SM, Young M, Keyak J, Kohri K, Ohshima H, Spector E, LeBlanc A (2019). Resistive exercise in astronauts on prolonged spaceflights provides partial protection against spaceflight-induced bone loss. Bone 128:112037](https://doi.org/10.1016/j.bone.2019.07.013)
2. ✓ **Când:** Înainte de o tranziție gravitațională (aselenizare, EVA pe suprafață, întoarcere pe Pământ) cu deficite mari de forță sau os față de baseline  
   **Ce faci:** Raportează la sol: riscul de cădere și de fractură crește la tranzițiile gravitaționale, iar FOR (sarcina aplicată / rezistența osului) crește când osul e slăbit.  
   *Sursa:* [NASA HRP (2025). Risk of Reduced Cardiorespiratory and Musculoskeletal Fitness (pagina oficială, actualizată 16 mai 2025)](https://www.nasa.gov/reference/risk-of-reduced-cardiorespiratory-and-musculoskeletal-fitness/)
3. ✓ **Când:** După misiune (mai ales >6 luni): planificarea urmăririi  
   **Ce faci:** Recomandă urmărire QCT/HR-pQCT, nu doar DXA. Recuperarea osului trabecular poate fi incompletă la 1-2 ani, chiar dacă DXA arată revenire.  
   *Sursa:* [NASA Human Research Program (2024). Evidence Report: Risk of Bone Fracture due to Spaceflight-induced Changes to Bone (HRP-F07-ERFT.R2, 18.07.2024)](https://humanresearchroadmap.nasa.gov/evidence/reports/Bone%20Fracture%20Evidence%20Report_07-18-2024.pdf)

### Radiații

**Riscuri NASA HRP:** [Risk of Radiation-Induced Cancers (formal: Risk of Radiation Carcinogenesis)](https://www.nasa.gov/reference/risk-of-radiation-induced-cancers/)

**Nivel 1 — Te descurci singur**

1. ✓ **Când:** Alertă SEP: rata dozei din habitat ≥2× media pe 24 h (prag derivat) sau notificare de eveniment SEP de la sol.  
   **Ce faci:** Mergi imediat în zona cea mai ecranată (cabina echipajului înconjurată de containere de apă / materiale bogate în hidrogen, ex. polietilenă) și rămâi acolo până când rata dozei revine la baseline.  
   *Sursa:* [NASA. Space Radiation Won't Stop NASA's Human Exploration.](https://www.nasa.gov/humans-in-space/space-radiation-wont-stop-nasas-human-exploration/)
2. ✓ **Când:** Vehicul în afara orbitei joase, avertizare timpurie SEP primită înainte de sosirea particulelor.  
   **Ce faci:** Reconfigurează adăpostul: mută containerele de apă și sacii de bagaje în jurul cabinelor (țintă: +10 cm echivalent apă); cronologia SEP lasă de obicei timp pentru reconfigurare.  
   *Sursa:* [NASA Office of the Chief Health & Medical Officer (2025). NASA-STD-3001 Technical Brief OCHMO-TB-020 Rev G (06/06/2025): Design for Ionizing Radiation Protection.](https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-020-radiation-protection.pdf)
3. ✓ **Când:** Alertă SEP în timpul unei activități extravehiculare (EVA).  
   **Ce faci:** Oprește EVA și revino în vehicul sau la ecranare în cel mult 2 ore de la alertă.  
   *Sursa:* [NASA Office of the Chief Health & Medical Officer (2025). NASA-STD-3001 Technical Brief OCHMO-TB-020 Rev G (06/06/2025): Design for Ionizing Radiation Protection.](https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-020-radiation-protection.pdf)
4. ⚠ NEVERIFICAT **Când:** EVA planificată în timp ce un SEP este în desfășurare sau o alertă de vreme spațială este activă.  
   **Ce faci:** Amână ieșirea până la încheierea alertei. Brieful NASA spune doar că SEP-urile perturbă puternic EVA-urile; regula de amânare este o extrapolare a noastră.  
   *Sursa:* [NASA Office of the Chief Health & Medical Officer (2025). NASA-STD-3001 Technical Brief OCHMO-TB-020 Rev G (06/06/2025): Design for Ionizing Radiation Protection.](https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-020-radiation-protection.pdf)
5. ✓ **Când:** Permanent (monitorizare de rutină).  
   **Ce faci:** Poartă permanent dozimetrul personal și aplică principiul ALARA: în timpul unei alerte, limitează timpul petrecut în modulele slab ecranate.  
   *Sursa:* [NASA (2025/2026). NASA-STD-3001, NASA Space Flight Human-System Standard, Volume 1 Rev C: Crew Health, Section 4.8 Space Permissible Exposure Limit for Spaceflight Radiation Exposure [V1 4029-4031] (web version, page last updated Mar 18, 2026).](https://www.nasa.gov/reference/4-0-human-performance/)

**Nivel 2 — Anunți ofițerul medical**

1. ✓ **Când:** După un SEP, membrul echipajului are greață, vărsături sau oboseală neobișnuită față de baseline-ul personal.  
   **Ce faci:** Anunță ofițerul medical de la bord: aceste simptome se potrivesc cu sindromul acut de iradiere și trebuie corelate cu doza înregistrată de dozimetru.  
   *Sursa:* [NASA Office of the Chief Health & Medical Officer (2025). NASA-STD-3001 Technical Brief OCHMO-TB-020 Rev G (06/06/2025): Design for Ionizing Radiation Protection.](https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-020-radiation-protection.pdf)
2. ⚠ NEVERIFICAT **Când:** Doza acumulată pe 30 de zile (dozimetru personal) depășește 50% din limita NASA de 250 mGy-Eq pentru organele hematopoietice sau sistemul circulator (fracția de 50% este derivată).  
   **Ce faci:** Ofițerul medical revizuiește istoricul dozei, verifică dacă adăpostirea a fost corectă și planifică reducerea expunerii (ALARA) pentru zilele următoare.  
   *Sursa:* [NASA (2025/2026). NASA-STD-3001, NASA Space Flight Human-System Standard, Volume 1 Rev C: Crew Health, Section 4.8 Space Permissible Exposure Limit for Spaceflight Radiation Exposure [V1 4029-4031] (web version, page last updated Mar 18, 2026).](https://www.nasa.gov/reference/4-0-human-performance/)

**Nivel 3 — Trimiți pe Pământ**

1. ⚠ NEVERIFICAT **Când:** Doza acumulată de la începutul SEP ≥ 25 mGy-Eq (10% din limita pe 30 de zile pentru organele hematopoietice; prag derivat) sau proiecția dozei de carieră depășește 600 mSv.  
   **Ce faci:** Trimite raport la Pământ (doza, durata, locul de adăpost). Pe Marte răspunsul vine cel mai devreme după ~6-45 min dus-întors, deci decizia de adăpostire nu așteaptă răspunsul.  
   *Sursa:* [NASA (2025/2026). NASA-STD-3001, NASA Space Flight Human-System Standard, Volume 1 Rev C: Crew Health, Section 4.8 Space Permissible Exposure Limit for Spaceflight Radiation Exposure [V1 4029-4031] (web version, page last updated Mar 18, 2026).](https://www.nasa.gov/reference/4-0-human-performance/)
2. ✓ **Când:** Doză estimată de corp întreg care se apropie de 0.7 Gy într-un interval scurt sau simptome de sindrom acut de iradiere.  
   **Ce faci:** Urgență medicală: notifică imediat Pământul (chirurgul de zbor) și urmează protocolul medical de la bord fără să aștepți răspunsul, din cauza întârzierii.  
   *Sursa:* [Guo J., Zeitlin C., Wimmer-Schweingruber R.F., Hassler D.M., Ehresmann B., Rafkin S., Freiherr von Forstner J.L., Khaksarighiri S., Liu W., Wang Y. (2021). Radiation environment for future human exploration on the surface of Mars: the current understanding based on MSL/RAD dose measurements. The Astronomy and Astrophysics Review 29: 8.](https://link.springer.com/article/10.1007/s00159-021-00136-5)

### Întârzierea comunicării

**Riscuri NASA HRP:** [Risk of Adverse Mission Outcomes Due to Earth Independent Human-Systems Operations (EIHSO Risk)](https://www.nasa.gov/hhp/human-system-risks/)

**Nivel 3 — Trimiți pe Pământ**

1. ✓ **Când:** Cu mai puțin de ~14 zile înainte de conjuncția solară Marte (moratoriu de comenzi ~2 săptămâni, ~2 zile fără niciun semnal).  
   **Ce faci:** Cere de la Pământ, înainte de conjuncție, protocoalele SEP și medicale actualizate; în timpul conjuncției echipajul aplică autonom nivelurile 1-2.  
   *Sursa:* [NASA/JPL (2023). NASA's Mars Fleet Will Still Conduct Science While Lying Low.](https://www.nasa.gov/solar-system/planets/mars/nasas-mars-fleet-will-still-conduct-science-while-lying-low/)

## 3. Texte scurte: funcția părților corpului (panoul de la click)

**Creier (pilonul comportamental).** Creierul coordonează atenția, memoria, deciziile și reacțiile rapide. În spațiu, somnul scurt, programul neregulat și izolarea îi pot scădea performanța fără ca astronautul să observe.  
*Sursa:* Van Dongen et al. 2003, Sleep 26(2):117 · [NASA HRP — Sleep risk](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=100)

**Inimă (pilonul cardiovascular).** Inima pompează sângele care duce oxigen și nutrienți în tot corpul. În microgravitație fluidele urcă spre cap și inima lucrează mai puțin împotriva gravitației, așa că la revenire pot apărea amețeli la ridicare.  
*Sursa:* [NASA HRP — Risk of Cardiovascular Adaptations](https://www.nasa.gov/reference/risk-of-cardiovascular-adaptations/) · CV Evidence Report 2022

**Sistemul imunitar (Santinela).** Sistemul imunitar apără corpul de virusuri, bacterii și celule anormale. În zbor, stresul, somnul perturbat și radiațiile îl dereglează, iar virusuri latente se pot reactiva: 14 din 23 de astronauți ISS au eliminat herpesvirusuri, de obicei fără simptome.  
*Sursa:* Rooney et al. 2019, Front Microbiol 10:16 · [NASA HRP — Immune risk](https://humanresearchroadmap.nasa.gov/Risks/?i=85)

**Oase și mușchi (Încărcarea).** Oasele susțin corpul și protejează organele, iar mușchii produc mișcarea; ambele se mențin prin încărcarea dată de greutatea corpului. Fără gravitație și fără exerciții, oasele portante pierd 1–1,5% din densitate pe lună; cu exercițiul zilnic cu greutăți de pe ISS (ARED), pierderea scade la circa 0,3–0,6% pe lună.  
*Sursa:* [NASA HRP — Risk of Spaceflight-Induced Bone Changes](https://www.nasa.gov/reference/risk-of-spaceflight-induced-bone-changes/) · NASA Bone Evidence Report 2024, Tabelul 2

## 4. Texte scurte: de ce contează în spațiu (coloana din check-in)

| Indicator | De ce contează în spațiu | Sursa |
|---|---|---|
| **Tensiunea** | În microgravitație fluidele se mută spre cap, iar tensiunea scade de obicei față de Pământ, de aceea SHADOW o compară cu normalul tău din zbor. Tendința ei ajută la pregătirea pentru revenirea în gravitație, când pot apărea amețeli. <br>*⚠ mărimea scăderii (8–14 mmHg) e confirmată doar pe abstract* | Norsk et al. 2015, J Physiol 593:573 (doar abstract); CV Evidence Report 2022 |
| **Pulsul** | În repaus, pulsul nu crește de obicei în zbor, așa că o creștere susținută față de normalul tău e un semnal real. Un puls de noapte cu câteva bătăi peste medie, mai multe nopți la rând, a precedat infecțiile în studii cu ceasuri inteligente. | Alavi et al. 2022, Nat Med 28:175 (✓); Fraser 2012 / Norsk 2015 (abstract) |
| **Glicemia** | Zborul de lungă durată poate reduce sensibilitatea la insulină, iar mesele sărite și stresul dezechilibrează glicemia. Măsurată dimineața, pe nemâncate, arată dacă alimentația îți susține energia pentru misiune. <br>*⚠ dovezi slabe, eșantion mic; pilonul glicemiei nu a fost cercetat în detaliu* | Hughson et al. 2016, Am J Physiol Heart Circ Physiol 310:H628 (titlul: „inflight insulin resistance”) |
| **Temperatura** | Într-un spațiu închis o infecție se poate transmite întregului echipaj, iar o creștere față de temperatura ta obișnuită poate fi primul semn. În zbor temperatura de repaus crește natural cu ~1 °C în primele luni, de aceea comparăm cu normalul tău din zbor. | Stahn et al. 2017, Sci Rep 7:16180 (✓; n=11) |
| **Somnul** | Astronauții dorm în medie sub 6,1 ore pe zi, din cauza luminii, a zgomotului și a programului încărcat. Două săptămâni de somn scurt pot scădea atenția cât două nopți nedormite, fără să-ți dai seama. | Basner et al. 2015, Aerosp Med Hum Perform 86:942 (✓); Van Dongen et al. 2003 (abstract oficial) |
| **Starea de spirit** | Izolarea, spațiul închis și distanța față de Pământ apasă pe sănătatea comportamentală. Compararea răspunsului tău cu datele obiective arată când „mă simt bine” nu se potrivește cu ce arată corpul. | [NASA HRP — Behavioral Health risk](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=99); Van Dongen et al. 2003 |
| **Nutriția** | Pe ISS, exercițiul cu greutăți a protejat oasele doar împreună cu un aport energetic suficient și vitamina D normală. Mesele sărite pot explica și o glicemie dezechilibrată sau o stare de oboseală. <br>*⚠ eșantion mic* | Smith et al. 2012, J Bone Miner Res 27:1896 (abstract; n=13) |

## 5. Unde dovezile sunt slabe (de spus deschis juriului)

- **Tastarea ca semnal de oboseală:** există un singur set mic de date etichetate (n=14, inerție de somn, nu privare cronică de somn). Nicio sursă nu stabilește câte zile trebuie pentru un baseline stabil; propunerea de ≥7 zile e **NEVERIFICAT**. Variabilitatea (SD/CV) și pauzele lungi nu au mărimi de efect publicate.
- **PVT și Van Dongen:** sunt studii de laborator pe adulți sănătoși, deci analog terestru. Pragul individual de 1,24 SD e derivat din ICC-ul PVT-ului de 10 minute.
- **Cardiovascular:** studiile au 6–14 astronauți, majoritatea bărbați. Nu există praguri HRV sau de puls publicate pentru astronauți; cele propuse vin din medicina sportivă (Buchheit 2014) și sunt **derivate**. 17 din 31 de valori au fost confirmate doar pe abstract.
- **Imunitar:** toți algoritmii (Mishra, Alavi, Smarr, Mason) au fost validați pe civili, pentru COVID-19, cu ceasuri comerciale. Regula „pași = 0” nu are sens în microgravitație. Regula pentru nivelul galben NightSignal e **NEVERIFICAT**.
- **Oase:** densitatea osoasă **nu se poate măsura la bord**, doar estima. Efectul împărțirii antrenamentului în mai multe sesiuni e demonstrat **doar pe animale** (Robling 2000–2002). La om există doar o meta-analiză indirectă (Babatunde 2012). Pentru Lună și Marte există doar date pe șoareci și șobolani.
- **Radiații:** pragurile de alertă (de 2× rata de doză, 10%/50% din limita pe 30 de zile) sunt **derivate**; NASA cere „praguri predefinite”, dar nu le publică. Nu s-a găsit o doză publicată pe ISS pentru SEP-ul din 11 mai 2024.

Lista completă, pe piloni, e în `parameters.json` → `note_dovezi_slabe`.

## 6. Evenimentul solar real pentru simulator (NASA DONKI)

- **SEP:** `2024-05-11T02:10:00-SEP-001`, detectat la 2024-05-11T02:10Z de GOES-P: SEISS >100 MeV.
- **CME asociat:** `2024-05-11T01:36:00-CME-001`, regiunea activă AR 13664, poziția S17W47. Erupția solară asociată a fost de clasă X5.8.
- **Context:** GLE 74, în timpul furtunii geomagnetice Gannon (mai 2024).
- **Link DONKI:** https://ccmc.gsfc.nasa.gov/DONKI/view/SEP/30714/-1
- **Datele brute** sunt în `donki_sep_event.json`. Pentru simulare, folosiți rata de doză din habitat ca baseline și aplicați pragul de alertă derivat (≥2× media pe 24 h).
- **Limită:** nu există o doză publicată pe ISS pentru acest eveniment. Valoarea de 8100 µGy măsurată pe Marte aparține altui eveniment (20 mai 2024).

---
*Generat pentru echipa SHADOW pe 13.11.2026. Pragurile, sursele (autor, an, DOI, URL) și modul de verificare al fiecărei valori sunt în `parameters.json`.*