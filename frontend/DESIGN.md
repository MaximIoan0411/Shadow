# SHADOW — sistemul de design

Preluat din **Quaternion 0.2.0** (`src/index.css`, `src/components/ui.tsx`, `Select.tsx`, `Chrome.tsx`) și adaptat
la SHADOW. Referința vizuală vie: **`/kit`** (`npm run dev`, apoi http://localhost:3000/kit).

## Ce am preluat și ce nu

| Din Quaternion | În SHADOW |
|---|---|
| fundalul negru `#050507`, suprafețele `surface` … `surface-4`, liniile `line` … `line-3`, textul `fg` … `fg-5` | **la fel** |
| Geist + Geist Mono, încărcate local din `@fontsource-variable` | **la fel** (merge offline, important pentru demo) |
| paleta: platinum, steel, violet, cyan, periwinkle, orchid, mint, amber, coral, warn, danger | **la fel** |
| razele 12 / 16 / 22, umbrele `card` și `float`, curbele `ease-out` / `ease-in-out` | **la fel** |
| `card-q` (sticlă), `float-q` (ridicat), `sidebar-q`, `nav-q`, `scroll-q`, `aurora`, `orb`, `shimmer-text`, `slider-q`, `prose-q` | **la fel** |
| inelul rotitor din jurul prompt-ului (`composer-glow`) | redenumit **`glow-ring`**; se folosește pe cardul medicului AI |
| o nuanță pe fiecare model / ecran (`SCREEN_HUE`) | o nuanță pe fiecare **ecran SHADOW** și pe fiecare **pilon** (`src/lib/hues.ts`) |
| `Button`, `IconButton`, `Switch`, `Slider`, `Segmented`, `Kbd`, `Orb`, `Tip`, `ProblemCard`, `Select`, preseturile de mișcare | **la fel**, în `src/components/ui/` (textele în română) |
| `Sidebar`, `Header` | adaptate: fără zona de tragere și butoanele ferestrei; contul autentificat jos; ceasul misiunii în antet |
| tema deschisă, Monaco, Dockview, xterm, Shiki, graficul echipelor | **nu** (nu le folosim) |
| — | nou: `StatusBadge`, `Card`, `Metric`, `PillarTag`, `SectionTitle`, `Dot`, `Input`, `Screen`, `Backdrop`, `.starfield`, `.num` |

## Culorile cu sens

**Starea** (vine de la backend în câmpul `status`; frontend-ul doar o colorează). Culoarea apare **mereu** cu forma și
cuvântul, prin `<StatusBadge status=… />`:

| `status` | Token | Culoare | Formă | Cuvânt |
|---|---|---|---|---|
| `ok` | `--color-status-ok` | mint `#7cf3d6` | ● | În limite |
| `watch` | `--color-status-watch` | warn `#f5c66b` | ▲ | De urmărit |
| `alert` | `--color-status-alert` | danger `#ff6b6b` | ■ | Alertă |
| `unknown` | `--color-status-unknown` | `fg-4` | ○ | Fără date |

**Pilonii** (aceleași familii ca în planul PDF): Tastatura = violet, Inima = coral, Santinela = mint,
Încărcarea = periwinkle. Clase Tailwind: `text-pillar-immune`, `bg-pillar-cardio/10` etc.

**Ecranele** (aurora, orb-ul, inelul AI-ului): `SCREEN_HUES` din `src/lib/hues.ts`. Controlul misiunii e singurul
ecran cu portocaliu (amber + coral), semnul distanței. Furtuna solară suprascrie ecranul cu `storm` (danger + amber).

## Cum construiești un ecran

```tsx
import { Header, Screen } from "@/components/layout/Shell";
import { Card, SectionTitle, StatusBadge, rise } from "@/components/ui";
import { motion } from "motion/react";

export default function CheckinPage() {
  return (
    <Screen screen="checkin" live={false}>               {/* nuanțele ecranului + aurora + rețeaua de puncte */}
      <Header title="Check-in de dimineață" mission={mission} />
      <div className="scroll-q min-h-0 flex-1 overflow-y-auto">
        <motion.div {...rise} className="mx-auto grid max-w-[1180px] gap-5 px-6 pb-16 pt-6">   {/* o singură intrare */}
          <Card as="section" aria-labelledby="h1">
            <SectionTitle id="h1" right={<StatusBadge status="ok" />}>Tensiunea</SectionTitle>
            …
          </Card>
        </motion.div>
      </div>
    </Screen>
  );
}
```

`live` aprinde aurora: folosiți-l cât timp un pachet e pe drum, AI-ul răspunde sau furtuna e activă.

## Regulile

1. **Culoarea e informație**, nu decor: stare, pilon, ecran. Orice altceva e în tonuri de gri (`fg-2` … `fg-5`).
2. **Starea apare mereu cu formă și cuvânt** (`StatusBadge`). Nu colorați un număr fără eticheta lui.
3. **Cifre:** valorile mari în Geist cu `tabular-nums`; ceasul, codurile și citirile mici în mono (`.num`).
4. **Raze:** controale `rounded-xl` (12), carduri interioare `rounded-2xl` (16), carduri și panouri `rounded-[var(--radius-card)]` (22). Butoanele sunt pastile (`rounded-full`).
5. **Adâncime din ton, nu din umbră:** `card-q` pentru carduri, `float-q` pentru ce plutește (meniuri, banner-ul de adăpost).
6. **O singură animație de intrare pe ecran** (`rise`); meniurile folosesc `pop`. `prefers-reduced-motion` oprește tot.
7. **Focus vizibil** (contur periwinkle) pe orice element interactiv; zonele corpului sunt butoane reale.
8. **Eticheta „date simulate”** apare unde backend-ul trimite `source = simulated` sau `data_is_simulated = true` (`<Metric simulated />`).
9. **Fără resurse de pe internet:** fonturile sunt locale, iconițele vin din `lucide-react`.
10. **Textele vin de la backend, în română**; componentele nu compun mesaje din bucăți.

## Fișierele

```
src/styles/tokens.css          tokenii și utilitarele (din Quaternion + stările, pilonii, .starfield, .num)
src/app/globals.css            fonturile locale + Tailwind + tokens.css
src/lib/hues.ts                SCREEN_HUES, PILLAR_HUE, STATUS_META, hueStyle()
src/components/ui/index.tsx    componentele de bază
src/components/ui/Select.tsx   lista derulantă (Radix)
src/components/layout/Shell.tsx  Screen, Backdrop, Sidebar, Header, SHIP_NAV, CMO_NAV
src/app/kit/page.tsx           catalogul vizual
```
