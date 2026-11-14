# SHADOW — sistemul de design v2: „Semnal pe negru”

Catalogul viu: **`/kit`** (`npm run dev`, apoi http://localhost:3000/kit). Interfața e în **engleză**; codul și
comentariile rămân în română.

## Ideea

Paleta vine din logo: **negrul** lui (`#0b0a0f`) e fundalul, **crema** lui (`#fef7ea`) e lumina interfeței, iar
**portocaliul** rămâne doar al logo-ului. Totul e în tonuri de fildeș pe negru. Culoarea apare **numai când corpul
are ceva de spus**: trei culori de stare, fiecare mereu cu forma și cuvântul ei.

Limbajul vizual e cel din logo: **pătrățele în grilă**. Din ele sunt desenate derulatorul misiunii (o celulă pe zi)
și drumul pachetului navă ↔ Pământ.

**Corpul interactiv** (`src/components/body/`) e o figură 3D din particule: pielea „de sticlă” (lumină la margini,
rețea de linii fine între noduri), înăuntru creierul, inima cu aorta, ganglionii cu vasele limfatice și oasele
picioarelor (colorate după stare), plus coloana și nervii, în crem. Se așază din praf la apariție, se leagănă încet,
urmărește cursorul, inima bate și o bandă de scanare urcă din când în când. Cu „reduce motion” e un cadru nemișcat.
Anatomia e în `anatomy.ts`, norul în `cloud.ts`, desenarea (tampon de pixeli, fără placă video) în `renderer.ts`.

**Icoanele de rol** de la intrare (`src/components/login/RoleIcon.tsx`, originalele în `docs/design/icons`) sunt în
`--color-crew` (#ffb45c), folosită doar acolo; medicul de zbor de pe Pământ are crucea ofițerului medical.

## Ce s-a schimbat față de v1 (Quaternion)

| v1 | v2 | De ce |
|---|---|---|
| 11 culori de paletă + o nuanță pe fiecare pilon, ecran și mediu; aurora colorată | **3 culori de stare** + neutre | prea multe culori: nu se mai înțelegea ce e important |
| pilonii colorați (violet, coral, mint, periwinkle) | pilonii au **iconiță și nume**, nu culoare | culoarea pilonului se confunda cu starea |
| accent periwinkle pe focus și linkuri | focus și linkuri **crem** | o culoare în plus, fără sens |
| fundal `#050507`, text alb-albăstrui | fundal și text **din logo** (negru cald, fildeș) | interfața și logo-ul arată ca aceeași familie |
| mono pentru toate cifrele | **Geist cu cifre tabulare**; mono doar pentru identificatori | în mono, cifrele mari arătau rarefiate |

## Culoarea

### Neutre

| Token | Valoare | Folosire |
|---|---|---|
| `bg` | `#0b0a0f` | fundalul |
| `surface` | `#111016` | bara laterală |
| `surface-2` | `#17161d` | câmpuri |
| `surface-3` | `#1e1d25` | butoane secundare, meniuri |
| `surface-4` | `#27262f` | hover, tooltip, inițialele contului |
| `fg` | `#f2ede4` | text principal |
| `fg-2` … `fg-4` | `fg` la 82 / 66 / 56% | corp, secundar, discret |
| `fg-5` | `fg` la 32% | **doar decor**, niciodată text |
| `line` … `line-3` | crem la 7,5 / 12 / 18% | despărțitoare, conturul cardurilor, hover |
| `line-4` | crem la 36% | **marginea câmpurilor** (≥ 3:1, WCAG 1.4.11) |
| `solid` / `on-solid` | `#fef7ea` / `#0b0a0f` | butonul primar, comutatorul pornit, ziua selectată |

### Semnal (singurele culori)

| `status` | Token | Culoare | Formă | Cuvânt |
|---|---|---|---|---|
| `ok` | `ok` | `#75dbb6` | ● | Within limits |
| `watch` | `watch` | `#f5c25f` | ▲ | Watch |
| `alert` | `alert` | `#fa6863` | ■ | Alert |
| `unknown` | `fg-4` | neutru | ○ | No data |

Verificate cu validatorul de palete (dataviz): ok ↔ watch ↔ alert se disting și la daltonism (ΔE ≥ 10 protan),
iar forma și cuvântul le deosebesc oricum.

`brand` (`#e2792e`) există ca token, dar se folosește **doar în logo**.

### Contrast (WCAG 2.1, verificat)

| Text | pe `bg` | pe `surface-4` | Cerut |
|---|---|---|---|
| `fg` | 16,9 : 1 | 12,8 : 1 | 4,5 : 1 |
| `fg-2` | 11,4 : 1 | 9,1 : 1 | 4,5 : 1 |
| `fg-3` | 7,6 : 1 | 6,4 : 1 | 4,5 : 1 |
| `fg-4` | 5,7 : 1 | 5,0 : 1 | 4,5 : 1 |
| `ok` / `watch` / `alert` ca text | 11,8 / 12,0 / 6,8 : 1 | 9,0 / 9,1 / 5,1 : 1 | 4,5 : 1 |
| `on-solid` pe `solid` (butonul primar) | 18,5 : 1 | | 4,5 : 1 |

Scanarea automată axe-core (WCAG 2.1 A + AA) trece fără erori pe toate ecranele.

## Tipografie

Geist pentru tot. Geist Mono **doar** pentru identificatori (`pk-0007`, numele testelor, amprentele din jurnal),
clasa `code`. Cifrele folosesc clasa `num` (cifre tabulare, ca să nu „sară” când se schimbă).

| Clasă | Mărime | Rol |
|---|---|---|
| `text-hero` | 44 | cifra unică a unui ecran (decalajul, întârzierea legăturii, doza) |
| `text-display` | 28 | valoarea unei măsurători |
| `text-title` | 18 | titlul unei alerte, al unui panou |
| `text-lead` | 15 | explicații, răspunsul medicului AI |
| `text-base` | 14 | textul de citit |
| `text-body` | 13,5 | controale, rânduri de listă |
| `text-small` | 12,5 | text secundar, stări |
| `text-caption` | 11,5 | titluri de secțiune, note |

## Forme și mișcare

- Raze: controale 12 (`rounded-xl`), carduri interioare 16 (`rounded-2xl`), carduri 22. Butoanele sunt pastile.
- Adâncimea vine din ton (`card-q`, `float-q`), nu din umbră.
- O singură mișcare fără acțiunea utilizatorului: zona în **alertă** de pe corp „respiră” încet (corpul din particule are și mișcările lui, descrise mai sus). Restul mișcărilor
  răspund la ce face utilizatorul. `prefers-reduced-motion` le oprește pe toate.
- În timpul unei alerte de radiații, lumina de fundal devine roșie: singura dată când fundalul are culoare.

## Componentele

`src/components/ui/index.tsx`: `Button`, `ButtonLink`, `IconButton`, `Spinner`, `Input`, `Textarea`, `Field`,
`Switch`, `Checkbox`, `Slider`, `Segmented`, `Kbd`, `Card`, `SectionTitle`, `Tag`, `LevelTag`, `StatusMark`,
`StatusBadge`, `Notice`, `ProblemCard`, `EmptyState`, `Skeleton`, `Meter`, `Metric`, `Tip`.
`src/components/ui/Select.tsx`: `Select`. `src/components/ui/overlays.tsx`: `Sheet`, `Dialog`, `Tabs`.
`src/components/charts/LineChart.tsx`: graficul (linie crem, banda normală, pragul, puncte colorate doar în afara
normalului, tooltip la hover și la săgeți, tabel ascuns pentru cititoarele de ecran).

## Regulile

1. **Culoarea e semnal.** Doar `ok`, `watch`, `alert`, și doar pentru o stare venită de la backend.
2. **Starea apare mereu cu formă și cuvânt** (`StatusBadge`, `StatusMark`, `Notice`).
3. **Textul nu poartă culoarea datelor**, cu excepția etichetei de stare.
4. Cel mult **un buton primar** pe ecran.
5. **„simulated data”** apare unde backend-ul trimite `source = simulated` sau `data_is_simulated = true`.
6. **Textele de interfață sunt în engleză**, în componente. Textele de conținut (titlurile alertelor, explicațiile,
   recomandările, câmpurile check-in-ului, erorile API) vin de la backend și se afișează exact cum vin.
7. **Fără resurse de pe internet:** fonturi locale, iconițe din `lucide-react`, logo din `public/brand/`.
8. **Focus vizibil** (inel crem) pe orice element interactiv; zonele corpului au butoane reale.
