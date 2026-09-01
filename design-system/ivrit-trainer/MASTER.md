# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** Ivrit Trainer
**Generated:** 2026-09-01 10:36:47
**Category:** Language Learning App
**Стек:** один HTML-файл без сборки, ванильный JS, Flask отдаёт как есть.
**Платформа:** Telegram Mini App (только мобильный, тёмная тема обязательна).
**Design Dials:** Variance 6/10 (Balanced / Modern) | Motion 4/10 (Standard) | Density 5/10 (Standard)

---

## Global Rules

### Color Palette

**Отклонение от генератора — осознанное.** Генератор предложил «учебное
индиго» (#4F46E5). Мы держим белый и синий флага Израиля: у продукта
должен быть узнаваемый вид, привязанный к стране, язык которой он учит.
Все пары проверены на контраст WCAG AA расчётом, а не на глаз.

| Роль | Светлая | Тёмная | Переменная |
|------|---------|--------|------------|
| Фон | `#EEF4FB` | `#0A1420` | `--bg` |
| Карточка | `#FFFFFF` | `#152232` | `--surface` |
| Текст | `#0B1B2B` | `#E9F1F9` | `--text` |
| Приглушённый | `#586A7C` | `#9DB0C4` | `--muted` |
| Граница | `#D3E1F0` | `#26374B` | `--border` |
| Основной | `#0038B8` | `#6FA8F5` | `--primary` |
| Текст на основном | `#FFFFFF` | `#08182F` | `--on-primary` |
| Тхелет (светлый синий) | `#7FC3E8` | `#4E86B8` | `--tchelet` |
| Верно | `#137A3C` | `#4FC77E` | `--ok` |
| Ошибка | `#B5231B` | `#FF7B72` | `--bad` |
| Описка | `#8A5A00` | `#E0A94A` | `--warn` |

Темам на главном экране раздаются оттенки по `TOPIC_HUE` — тринадцать
одинаковых плиток глаз не различает.

### Typography

**Отклонение от генератора — осознанное.** Он предложил Baloo 2 и Comic
Neue как «детские, образовательные». Аудитория продукта — взрослые олим,
детский шрифт читался бы снисходительно.

- **Интерфейс:** системный (`-apple-system`, `Segoe UI`, `Roboto`) —
  приложение внутри Telegram должно выглядеть частью телефона.
- **Иврит:** `Noto Sans Hebrew`. Это не эстетика: весь банк с
  огласовками, а системные шрифты рисуют их вкривь — точки наезжают на
  буквы. Единственный подключаемый шрифт.

### Spacing Variables

*Density: 5/10 — Standard*

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` / `0.25rem` | Tight gaps |
| `--space-sm` | `8px` / `0.5rem` | Icon gaps, inline spacing |
| `--space-md` | `16px` / `1rem` | Standard padding |
| `--space-lg` | `24px` / `1.5rem` | Section padding |
| `--space-xl` | `32px` / `2rem` | Large gaps |
| `--space-2xl` | `48px` / `3rem` | Section margins |
| `--space-3xl` | `64px` / `4rem` | Hero padding |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, buttons |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #16A34A;
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: #4F46E5;
  border: 2px solid #4F46E5;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}
```

### Cards

```css
.card {
  background: #EEF2FF;
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-md);
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease;
}

.input:focus {
  border-color: #4F46E5;
  outline: none;
  box-shadow: 0 0 0 3px #4F46E520;
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

---

## Style Guidelines

**Style:** Claymorphism

**Keywords:** Soft 3D, chunky, playful, toy-like, bubbly, thick borders (3-4px), double shadows, rounded (16-24px)

**Best For:** Educational apps, children's apps, SaaS platforms, creative tools, fun-focused, onboarding, casual games

**Key Effects:** Inner+outer shadows (subtle, no hard lines), soft press (200ms ease-out), fluffy elements, smooth transitions

### Page Pattern

**Pattern Name:** Hero + Testimonials + CTA

- **Conversion Strategy:** Social proof before CTA. Use a concise set of verified testimonials with photo, name, and role. CTA after social proof. Provide previous/next and pause controls; stop rotation on focus, hover, and reduced motion; announce slide position. Previous/next buttons and keyboard controls must expose every slide without dragging.
- **CTA Placement:** Hero (sticky) + Post-testimonials
- **Section Order:** Hero > Problem statement > Solution overview > Testimonials carousel > CTA

---

## Motion

**Stagger List** (Standard) — Trigger: load or scroll | Duration: 300-450ms | Easing: `back.out(1.4)`

```js
gsap.from('.grid-item', { opacity: 0, scale: 0.92, y: 16, duration: 0.4, stagger: { each: 0.06, from: 'start', grid: 'auto' }, ease: 'back.out(1.4)' });
```

**Framework notes:** grid: 'auto' lets GSAP infer rows/columns from a CSS grid layout for a natural wave stagger; Use matchMedia('(prefers-reduced-motion: reduce)') to skip non-essential motion and render the final state immediately

- ✅ Combine with from: 'center' for a bento-grid layout to draw the eye inward first
- ❌ Don't use back.out on dense data tables; the overshoot reads as sloppy on informational UI
- ⚡ Group DOM writes; avoid interleaving layout reads (getBoundingClientRect) between staggered tweens

---

## Anti-Patterns (Do NOT Use)

- ❌ Boring design
- ❌ No motivation

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile


---

## Решения проекта

- **Стиль:** сдержанный, со светом и текстурой. Первый заход был на
  клеймофизм («educational app» в выдаче скилла), но он рассчитан на
  детей. Аудитория продукта — взрослые репатрианты, среди них много
  людей творческих профессий, и мультяшность для них минус: конкурент
  на этом проседает. Сейчас взято из выдачи по «premium / texture»:
  слои света на фоне, зерно поверх, полупрозрачные карточки с
  размытием, редакционная типографика. Отскок остался только на
  нажатие.
- **Фон обязателен.** Без него карточки висят на пустом поле и всё
  читается бледно — проверено на живом экране.
- **Иконки:** встроенный SVG-спрайт. Эмодзи запрещены: разные на разных
  телефонах, не красятся под тему.
- **Маскот:** удод (национальная птица Израиля). Пять состояний в
  `static/mascot/`, готовятся скриптом из стикеров.
- **Касание:** минимум 44 px, зазор 8 px, смещение при нажатии не больше
  2 px — иначе читается как движение, а не как отклик.
- **Движение:** 150–300 мс, отскок `cubic-bezier(.34,1.56,.64,1)` только
  на нажатие. При `prefers-reduced-motion` выключается целиком.
- **Чего не делаем:** карты пути (нет линейного курса), монет (нет
  экономики), градиентов ради градиентов.
