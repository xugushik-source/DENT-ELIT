# МАСТЕР-ПРОМПТ ORDER PROFIT: клон сайта «ELIT DENT»

Это полная техническая инструкция для ИИ (ChatGPT, Claude или любого другого,
умеющего писать код). Вставь этот файл целиком первым сообщением в чат с ИИ,
а сразу за ним — заполненный файл `CLIENT_BRIEF.md` (бриф с данными нового
клиента). ИИ должен собрать сайт, у которого **механика, дизайн-система и все
эффекты один в один совпадают с ELIT DENT**, а меняются только данные:
название клиники, тон/палитра, контакты, врачи/услуги (или другие сущности —
см. ниже), цены, фотографии.

Ты — опытный веб-разработчик агентства ORDER PROFIT. Тебе нужно собрать
premium-сайт для клиента точно по образцу «ELIT DENT» — той же архитектуры,
того же стека, тех же эффектов, — но с данными нового клиента вместо ELIT DENT.

## ГЛАВНОЕ ПРАВИЛО

Всё, что ниже помечено как **МЕХАНИКА**, нужно воспроизвести **дословно, без
изменений** — это не описание «в духе того», а рабочий исходный код, который
нужно скопировать один в один (только цветовые токены и текст на 3 языках
могут отличаться, если бриф просит другой язык/палитру). Всё, что помечено
**ПЕРЕМЕННОЕ**, — берётся из брифа клиента и заполняется заново.

Если бриф не указывает языки — используй ровно ту же тройку (армянский,
русский, английский, коды `hy`/`ru`/`en`, `hy` — язык по умолчанию) и ту же
структуру `data/site.json → languages`. Если бриф просит другой набор языков —
меняй только список кодов, вся остальная логика мультиязычности (циклы по
`languages.supported`, генерация `/lang/...`-URL, hreflang) остаётся такой же.

## Стек и принципы (МЕХАНИКА)

- Статический сайт: Python 3 + Jinja2, никакого Node/React/фреймворков на
  фронтенде — чистые HTML/CSS/vanilla JS.
- `build.py` читает `data/*.json` (структурированный контент) и
  `content/{lang}.json` (UI-строки интерфейса) через Jinja2-шаблоны из
  `templates/` и рендерит статику в `dist/{lang}/...` — папочные URL вида
  `/ru/services/dental-implants/`, не `.html`-файлы напрямую.
- Каждый запуск `python3 build.py` полностью пересобирает `dist/` с нуля.
- Деплой — на любой статический хостинг (Vercel: `outputDirectory: dist`,
  без команды сборки, поскольку `dist/` уже готов).
- После каждой сборки — `python3 validate.py`, он обязан вывести
  `PASSED: 0 errors` перед тем, как сайт считается готовым (см. ниже, это
  тоже механика — файл целиком приложен).

## Структура проекта (МЕХАНИКА)

```
data/site.json           → бренд, контакты, SEO, фичефлаги, статистика, рейтинг
data/doctors.json        → сущности-специалисты (в другой вертикали — сотрудники/номера/блюда)
data/services.json       → услуги (в другой вертикали — меню/номера отеля/прайс-лист)
data/technology.json     → технологии/оборудование
data/reviews.json        → отзывы
data/process-default.json → общий 5-шаговый процесс (используется на всех страницах услуг)
content/hy.json           → UI-строки интерфейса на армянском
content/ru.json           → UI-строки интерфейса на русском
content/en.json           → UI-строки интерфейса на английском
templates/                → Jinja2-шаблоны (см. полный код ниже)
static/css/tokens.css     → цветовые/типографические токены (ПЕРЕМЕННОЕ — палитра клиента)
static/css/main.css       → компоненты дизайн-системы (МЕХАНИКА)
static/js/main.js         → вся интерактивность (МЕХАНИКА)
static/brand/             → логотип клиента (ПЕРЕМЕННОЕ — только файл клиента, не придумывать)
static/images/            → фотографии клиента (ПЕРЕМЕННОЕ)
build.py                  → генератор сайта (МЕХАНИКА)
validate.py               → автоматическая проверка перед сдачей (МЕХАНИКА)
```

## Что именно ПЕРЕМЕННОЕ (берётся из брифа клиента)

- Название бренда, слоган, год основания, логотип (реальный файл клиента —
  никогда не придумывать и не рисовать новый; технически можно только
  обрезать/сжать/изменить размер присланного файла).
- Цветовые токены в `tokens.css` (`--color-bg`, `--color-accent` и т.д.) —
  палитра под бренд клиента. Структура токенов и то, как они используются в
  компонентах, не меняется.
- Телефон, WhatsApp-номер, email, адрес (на каждом языке), часы работы,
  города обслуживания, соцсети (только реальные, не придумывать).
- Список специалистов/сущностей (`doctors.json`): имена, роли, стаж, языки,
  фото, биография, образование, сертификаты — количество произвольное.
- Список услуг/товаров (`services.json`): контент, изображения, **цена и
  валюта** (валюта = та, что реально используется в стране клиента, не
  копировать валюту ELIT DENT бездумно), FAQ, привязка к специалисту/технологии.
- Список технологий/оборудования (`technology.json`) — опционально.
- Отзывы (`reviews.json`) — только реальные после запуска; на демо-этапе
  честно вымышленные (см. `demoMode` ниже), никогда не выдавать за настоящие.
- `data/site.json → stats` и `trustItems` — цифры и формулировки должны
  реально соответствовать переданным данным (кол-во специалистов, языков,
  направлений) — это проверяет `validate.py`, см. ниже.
- `content/{lang}.json` — это в основном **механический шаблон текста
  интерфейса** (кнопки, заголовки разделов), но в нескольких местах в нём
  буквально зашито название клиники (например `trust.title`,
  `hero.eyebrow`-соседние тексты, `whatsapp.*Template`, `footer.disclosure`,
  `aboutPage.eyebrow`) — замени в них "ELIT DENT" на новое название клиники
  везде, где оно встречается, остальной текст интерфейса можно оставить как
  есть (это фирменный стиль ORDER PROFIT), если в брифе не попросят другой тон.
- `featureFlags.demoMode` и `footer.disclosure` — пока данные вымышленные,
  `demoMode: true` и есть дисклеймер в подвале (текст ниже, механика). Когда
  клиент подтвердит все данные как настоящие — `demoMode: false` и дисклеймер
  убирается/меняется.

## Что именно МЕХАНИКА (никогда не менять смысл/поведение, только код ниже)

1. **Вся сборка**: `build.py`, разделение data/content/templates/static,
   папочные URL, полный набор страниц (главная, список услуг + карточка
   услуги, список специалистов + карточка специалиста, технологии, о клинике,
   отзывы, контакты, 404).
2. **Полноэкранная заставка (splash) с логотипом** при первом заходе за
   сессию: чёрный фон, логотип клиента по центру, плавное появление (scale +
   opacity), пауза ~1.5 сек, плавное исчезновение (~0.7 сек), больше не
   показывается повторно при переходах между страницами (флаг в
   `sessionStorage`). Логотип — переменный, сам механизм — нет.
3. **Хлебные крошки (breadcrumb)** на каждой странице, кроме главной:
   «Главная / Раздел» на страницах-списках, «Главная / Раздел / Название» на
   карточках — общий partial-шаблон, никогда не убирать ни с одной страницы.
4. **Scroll-reveal анимация**: каждый блок на каждой странице плавно
   появляется (fade + translateY) при попадании в область видимости через
   `IntersectionObserver`, с небольшим каскадом (~80мс) между соседними
   элементами в сетке. Без JS или при `prefers-reduced-motion` — контент
   виден сразу, без анимации (прогрессивное усиление, не обязательное
   условие показа контента).
5. **Форма записи + WhatsApp**: модальное окно записи (имя, телефон, услуга,
   способ связи, комментарий) собирает сообщение и открывает `wa.me`-ссылку.
   **Номер телефона клиента обязан попадать в текст сообщения** — это
   когда-то ломалось и является самым важным с бизнес-точки зрения местом
   сайта, трогать с максимальной осторожностью. Отдельно — запись «к
   конкретному специалисту» с его именем в сообщении (передаётся через
   `data-doctor`). Все статичные WhatsApp-ссылки (шапка, подвал, плавающая
   кнопка, нижний бар) рендерятся на сервере через Jinja2-функцию `wa_url()`
   — никогда `href="#"` с переписыванием через JS.
6. **Мобильное меню, нижний бар (Звонок/WhatsApp/Запись), плавающая кнопка
   WhatsApp** — с доступностью (focus-trap, `aria-expanded`/`aria-hidden`,
   закрытие по Escape, возврат фокуса).
7. **SEO**: `SITE_URL` берётся из переменной окружения при сборке
   (`SITE_URL=https://realdomain.com python3 build.py`), иначе — из
   `data/site.json → seo.productionUrl`. Отсюда строятся canonical, hreflang
   (включая `x-default`), Open Graph, `sitemap.xml`, `robots.txt`. Никогда не
   хардкодить домен где-либо ещё. Структурированные данные (JSON-LD):
   `Dentist`/аналог на главной, `BreadcrumbList` + `Service` + `FAQPage` на
   карточке услуги, `BreadcrumbList` + `Person` на карточке специалиста.
   Пока `demoMode: true` — никогда не генерировать `AggregateRating` (это
   было бы выдачей вымышленного рейтинга за настоящий).
8. **`validate.py`** — обязательный автоматический прогон перед сдачей:
   битые ссылки/картинки, незаменённые `{{ }}`/`{% %}`, оставшийся
   плейсхолдерный текст, отсутствие `<title>`/description/canonical,
   дублирующиеся canonical, несовпадение языковых версий страниц, а также
   проверка данных «в цифрах»: число специалистов/услуг/отзывов должно
   совпадать с тем, что реально указано в `stats`/`rating`.
9. **Дизайн-система**: одна и та же шкала отступов/типографики и структура
   компонентов (карточки, кнопки, модалка, шапка, подвал) — под новый бренд
   меняется только палитра цветов (`tokens.css`), не структура CSS.

## Полные образцы схем данных

### `data/site.json` (структура одна в один, значения — из брифа)

```json
{
  "brand": {
    "clinicName": "ELIT DENT",
    "tagline": {
      "hy": "Պրեմիում ատամնաբուժություն",
      "ru": "Премиальная стоматология",
      "en": "Premium Dental Care"
    },
    "developer": "ORDER PROFIT",
    "foundedYear": 2014,
    "logo": {
      "full": "/brand/logo-full-light.png",
      "horizontal": "/brand/logo-full-light.png",
      "mark": "/brand/logo-mark-light.png",
      "light": "/brand/logo-full-light.png",
      "dark": "/brand/logo-full-dark.png",
      "favicon": "/favicon-32.png",
      "_note": "Original ELIT DENT logo supplied by the client (gold tooth-ribbon mark + serif wordmark), unmodified in design. See AUDIT_V2.md for the exact source-to-production file trail. Do not regenerate or redesign this mark."
    }
  },
  "contact": {
    "phone": "+995 579 145 634",
    "phoneUri": "tel:+995579145634",
    "whatsapp": "+995 579 145 634",
    "whatsappNumber": "995579145634",
    "whatsappUri": "https://wa.me/995579145634",
    "email": "info@elitdent.example",
    "emailIsLive": false,
    "address": {
      "hy": "Իր. Աբաշիձեի փող. 14, Վաքե, Թբիլիսի 0179, Վրաստան",
      "ru": "ул. Ир. Абашидзе 14, Ваке, Тбилиси 0179, Грузия",
      "en": "14 Ir. Abashidze St, Vake, Tbilisi 0179, Georgia"
    },
    "googleMapsUrl": null,
    "googleBusinessUrl": null,
    "socials": {
      "instagram": null,
      "facebook": null,
      "tiktok": null,
      "youtube": null
    }
  },
  "seo": {
    "country": "Georgia",
    "city": "Tbilisi",
    "serviceAreas": [
      "Tbilisi",
      "Vake",
      "Saburtalo",
      "Vera"
    ],
    "productionUrl": "https://dent-elit.vercel.app",
    "_note": "Overridable at build time via the SITE_URL environment variable (see build.py) — set it to the real client domain on launch, nothing else in the templates hardcodes a URL."
  },
  "languages": {
    "default": "hy",
    "supported": [
      "hy",
      "ru",
      "en"
    ]
  },
  "featureFlags": {
    "servicesEnabled": true,
    "doctorProfilesEnabled": true,
    "technologyEnabled": true,
    "reviewsEnabled": true,
    "beforeAfterEnabled": false,
    "galleryEnabled": true,
    "bookingEnabled": true,
    "whatsappEnabled": true,
    "offersEnabled": false,
    "blogEnabled": false,
    "multilingualEnabled": true,
    "demoMode": true
  },
  "visual": {
    "heroVariant": "doctorFocus",
    "servicesVariant": "grid",
    "doctorVariant": "cards",
    "reviewVariant": "cards"
  },
  "homepageSections": [
    "hero",
    "trust",
    "services",
    "technology",
    "doctorSpotlight",
    "patientExperience",
    "team",
    "reviews",
    "finalCTA"
  ],
  "trustItems": [
    {
      "icon": "digital",
      "key": "digitalDentistry"
    },
    {
      "icon": "languages",
      "key": "threeLanguages"
    },
    {
      "icon": "diagnostics",
      "key": "advancedDiagnostics"
    },
    {
      "icon": "planning",
      "key": "personalPlanning"
    }
  ],
  "stats": [
    {
      "value": "10+",
      "key": "yearsExperience"
    },
    {
      "value": "6",
      "key": "specialists"
    },
    {
      "value": "3",
      "key": "languages"
    },
    {
      "value": "12",
      "key": "treatmentAreas"
    }
  ],
  "rating": {
    "value": 4.9,
    "count": 11
  }
}
```

### `data/doctors.json` — один элемент массива (повторить по числу специалистов из брифа)

```json
{
  "slug": "vardan-hakobyan",
  "photo": "/images/doctors/vardan-hakobyan-portrait.jpg",
  "workingPhoto": "/images/doctors/vardan-hakobyan-working.jpg",
  "role": {
    "hy": "Գլխավոր բժիշկ, իմպլանտոլոգ-վիրաբույժ",
    "ru": "Главный врач, хирург-имплантолог",
    "en": "Chief Dentist, Implant Surgeon"
  },
  "name": "Dr. Vardan Hakobyan",
  "experienceYears": 14,
  "languages": [
    "hy",
    "ru",
    "en"
  ],
  "services": [
    "dental-implants",
    "oral-surgery",
    "crowns-prosthetics"
  ],
  "quote": {
    "hy": "Յուրաքանչյուր իմպլանտացիա սկսվում է ոչ թե պտուտակից, այլ ճշգրիտ պլանավորումից։",
    "ru": "Каждая имплантация начинается не с импланта, а с точного планирования.",
    "en": "Every implant case starts with precise planning, not with the implant itself."
  },
  "bio": {
    "hy": "Աշխատում է թվային պլանավորման սկզբունքով՝ համադրելով 3D КТ ախտորոշումը անհատական մոտեցման հետ։",
    "ru": "Работает по принципу цифрового планирования, сочетая 3D КТ-диагностику с индивидуальным подходом к каждому случаю.",
    "en": "Works from a digital-planning-first approach, combining 3D CBCT diagnostics with a fully individual treatment plan for every case."
  },
  "education": {
    "hy": [
      "ԲԴԲ, Երևանի պետական բժշկական համալսարան",
      "Օրդինատուրա՝ ծնոտա-դիմածնոտային վիրաբուժություն",
      "Իմպլանտոլոգիայի առաջադեմ դասընթաց (Գերմանիա)"
    ],
    "ru": [
      "DMD, Ереванский государственный медицинский университет",
      "Ординатура по челюстно-лицевой хирургии",
      "Курс повышения квалификации по имплантологии (Германия)"
    ],
    "en": [
      "DMD, Yerevan State Medical University",
      "Residency in Oral & Maxillofacial Surgery",
      "Advanced Implantology training programme (Germany)"
    ]
  },
  "certifications": [
    {
      "id": "DEMO-GE-DENT-2026-001",
      "label": {
        "hy": "Ստոմատոլոգիական պրակտիկայի սերտիֆիկատ",
        "ru": "Сертификат стоматологической практики",
        "en": "Certificate of Dental Practice"
      }
    },
    {
      "id": "DEMO-GE-IMPL-2026-014",
      "label": {
        "hy": "Ուղղորդված իմպլանտացիայի սերտիֆիկատ",
        "ru": "Сертификат по guided-имплантации",
        "en": "Guided Implant Placement Certificate"
      }
    }
  ]
}
```

### `data/services.json` — один элемент массива (повторить по числу услуг из брифа)

```json
{
  "slug": "dental-implants",
  "icon": "implant",
  "flagship": true,
  "cardImage": "/images/services/dental-implants.jpg",
  "heroImage": "/images/services/dental-implants-hero.jpg",
  "doctorSlug": "vardan-hakobyan",
  "technologyRefs": [
    "cbct-3d",
    "digital-planning"
  ],
  "relatedSlugs": [
    "crowns-prosthetics",
    "oral-surgery",
    "digital-diagnostics"
  ],
  "eyebrow": {
    "hy": "Իմպլանտավորում",
    "ru": "Имплантация",
    "en": "Dental Implants"
  },
  "title": {
    "hy": "Ատամների իմպլանտացիա",
    "ru": "Имплантация зубов",
    "en": "Dental Implants"
  },
  "shortCopy": {
    "hy": "Ամուր, բնական տեսք ունեցող լուծում կորցրած ատամի փոխարեն՝ հիմնված ճշգրիտ 3D պլանավորման վրա։",
    "ru": "Прочное, естественно выглядящее решение взамен утраченного зуба, основанное на точном 3D-планировании.",
    "en": "A stable, natural-looking replacement for a missing tooth, built on precise 3D planning."
  },
  "intro": {
    "hy": "Իմպլանտացիան թույլ է տալիս վերականգնել ինչպես ատամի ֆունկցիան, այնպես էլ ժպիտի բնական տեսքը։ Յուրաքանչյուր դեպք սկսվում է մանրամասն ախտորոշումից և անհատական պլանավորումից՝ նախքան որևէ վիրահատական քայլ։",
    "ru": "Имплантация восстанавливает не только функцию зуба, но и естественный вид улыбки. Каждый случай начинается с детальной диагностики и индивидуального планирования — ещё до хирургического этапа.",
    "en": "Implants restore both function and the natural appearance of your smile. Every case begins with detailed diagnostics and individual planning, well before any surgical step."
  },
  "aboutTreatment": {
    "hy": "Օգտագործելով 3D КТ պատկերում՝ ճշգրիտ որոշվում է ծնոտի ոսկրային հյուսվածքի վիճակը և իմպլանտի օպտիմալ դիրքը։ Սա նվազեցնում է անորոշությունը և բարձրացնում կանխատեսելիությունը։",
    "ru": "С помощью 3D КТ-снимка точно оценивается состояние костной ткани и определяется оптимальное положение импланта. Это снижает неопределённость и повышает предсказуемость результата.",
    "en": "A 3D CBCT scan is used to assess bone quality and plan the ideal implant position in advance, which reduces uncertainty and makes the outcome far more predictable."
  },
  "whoItIsFor": {
    "hy": [
      "Կորցրել եք մեկ կամ մի քանի ատամ",
      "Հանովի պրոթեզն այլևս հարմարավետ չէ",
      "Ցանկանում եք երկարաժամկետ, կայուն լուծում"
    ],
    "ru": [
      "Вы потеряли один или несколько зубов",
      "Съёмный протез больше не устраивает по комфорту",
      "Вы хотите долгосрочное, стабильное решение"
    ],
    "en": [
      "You've lost one or more teeth",
      "A removable denture is no longer comfortable",
      "You want a long-term, stable solution"
    ]
  },
  "benefits": {
    "hy": [
      "Բնական տեսք և ֆունկցիա",
      "Չի ազդում հարևան ատամների վրա",
      "Ախտորոշման հիման վրա կանխատեսելի արդյունք",
      "Երկարաժամկետ լուծում ճիշտ խնամքի դեպքում"
    ],
    "ru": [
      "Естественный вид и функция",
      "Не затрагивает соседние зубы",
      "Предсказуемый результат за счёт точной диагностики",
      "Долговечное решение при правильном уходе"
    ],
    "en": [
      "Natural look and bite function",
      "Doesn't affect neighboring teeth",
      "Predictable outcome thanks to precise diagnostics",
      "Long-lasting with proper care"
    ]
  },
  "faq": [
    {
      "q": {
        "hy": "Որքա՞ն է տևում ամբողջ գործընթացը",
        "ru": "Сколько занимает весь процесс",
        "en": "How long does the whole process take"
      },
      "a": {
        "hy": "Ժամկետը կախված է ոսկրային հյուսվածքի վիճակից և անհատական պլանից. մանրամասները քննարկվում են խորհրդատվության ժամանակ։",
        "ru": "Сроки зависят от состояния костной ткани и индивидуального плана — детали обсуждаются на консультации.",
        "en": "Timing depends on bone condition and your individual plan — we'll walk through specifics at the consultation."
      }
    },
    {
      "q": {
        "hy": "Ցավոտ գործընթա՞ց է",
        "ru": "Это болезненная процедура",
        "en": "Is the procedure painful"
      },
      "a": {
        "hy": "Իրականացվում է տեղային անզգայացման ներքո՝ հարմարավետությանն ուշադրություն դարձնելով բուժման ողջ ընթացքում։",
        "ru": "Процедура проводится под местной анестезией, комфорту пациента уделяется внимание на каждом этапе.",
        "en": "It's performed under local anesthesia, with attention to comfort at every stage."
      }
    },
    {
      "q": {
        "hy": "Ի՞նչ արժե ատամի իմպլանտացիան",
        "ru": "Сколько стоит имплантация зуба",
        "en": "How much does a dental implant cost"
      },
      "a": {
        "hy": "Արժեքը որոշվում է անհատական պլանից հետո՝ կախված ախտորոշումից և ընտրված նյութերից։",
        "ru": "Стоимость определяется после диагностики и составления индивидуального плана лечения.",
        "en": "Pricing is determined after diagnostics, once your individual treatment plan is set."
      }
    }
  ],
  "price": {
    "amount": 350,
    "currency": "$",
    "prefix": {
      "hy": "Սկսած",
      "ru": "От",
      "en": "From"
    },
    "note": {
      "hy": "Վերջնական արժեքը որոշվում է ախտորոշումից և բուժման պլան կազմելուց հետո։",
      "ru": "Точная стоимость определяется после диагностики и составления плана лечения.",
      "en": "The exact price is set after diagnostics and your personal treatment plan."
    }
  }
}
```

### `data/technology.json` — один элемент массива (опционально, если у клиента есть технологии/оборудование)

```json
{
  "slug": "cbct-3d",
  "icon": "cbct",
  "image": "/images/technology/cbct.jpg",
  "name": {
    "hy": "3D КТ ախտորոշում",
    "ru": "3D КТ-диагностика",
    "en": "CBCT 3D Diagnostics"
  },
  "shortExplain": {
    "hy": "Եռաչափ պատկերում, որը ցույց է տալիս ոսկրային հյուսվածքի ամբողջական կառուցվածքը։",
    "ru": "Трёхмерное изображение, показывающее полную структуру костной ткани.",
    "en": "A three-dimensional scan that shows the complete structure of the jawbone."
  },
  "patientBenefit": {
    "hy": "Ձեզ համար սա նշանակում է ավելի ճշգրիտ պլան և ավելի քիչ անակնկալներ բուժման ընթացքում։",
    "ru": "Для вас это означает более точный план лечения и меньше неожиданностей в процессе.",
    "en": "For you, that means a more accurate plan and fewer surprises during treatment."
  }
}
```

### `data/reviews.json` — структура файла + один элемент (реальные отзывы после запуска, вымышленные — только на демо-этапе с честной пометкой)

```json
{
  "_note": "ELIT DENT is a fictional demonstration clinic (see footer disclosure on every page). These reviews are written as a consistent fictional dataset — not copied from any real patient or clinic — to show what a fully populated reviews section looks like. No isDemo badges are rendered in the UI; this file's own _note is the only place that says so.",
  "aggregateRatingEnabled": true,
  "items": [
    {
      "id": "r1",
      "serviceSlug": "dental-implants",
      "quote": {
        "hy": "Երկար ժամանակ վախենում էի իմպլանտից, բայց այստեղ ամեն ինչ բացատրեցին 3D նկարով, նախքան որևէ որոշում կայացնելը։ Գործընթացը եղավ հենց այնպես, ինչպես ասել էին։",
        "ru": "Долго боялась имплантации, но здесь всё показали на 3D-снимке ещё до принятия решения. Всё прошло именно так, как объяснили заранее.",
        "en": "I put off getting an implant for years, but they walked me through the 3D scan before I decided anything. The whole process matched exactly what they'd described."
      },
      "authorInitial": {
        "hy": "Անի Կ.",
        "ru": "Анна К.",
        "en": "Anna K."
      }
    }
  ]
}
```

### `data/process-default.json` — общий 5-шаговый процесс лечения/обслуживания (МЕХАНИКА, содержание можно оставить как есть или адаптировать под вертикаль клиента)

```json
[
  {
    "step": "01",
    "title": {
      "hy": "Խորհրդատվություն",
      "ru": "Консультация",
      "en": "Consultation"
    },
    "desc": {
      "hy": "Ականջալուր ենք ձեր հարցերին ու ակնկալիքներին, զննում ենք բերանի խոռոչի ընդհանուր վիճակը և պատասխանում ենք ձեզ հետաքրքրող բոլոր հարցերին։",
      "ru": "Внимательно выслушиваем ваши пожелания и жалобы, проводим первичный осмотр и отвечаем на все интересующие вопросы — без спешки.",
      "en": "We listen to your goals and concerns, review your overall oral health, and answer every question before anything else happens."
    }
  },
  {
    "step": "02",
    "title": {
      "hy": "Թվային ախտորոշում",
      "ru": "Цифровая диагностика",
      "en": "Digital diagnostics"
    },
    "desc": {
      "hy": "Անհրաժեշտության դեպքում կատարում ենք 3D КТ հետազոտություն և ներբերանային սկանավորում՝ ամբողջական և ճշգրիտ պատկերի համար։",
      "ru": "При необходимости выполняем 3D КТ-диагностику и внутриротовое сканирование, чтобы получить точную и полную картину.",
      "en": "Where relevant, we use 3D CBCT imaging and intraoral scanning to see the full picture with precision, not guesswork."
    }
  },
  {
    "step": "03",
    "title": {
      "hy": "Անհատական բուժման պլան",
      "ru": "Персональный план лечения",
      "en": "Personal treatment plan"
    },
    "desc": {
      "hy": "Ախտորոշման տվյալների հիման վրա կազմում ենք հստակ, փուլային բուժման պլան՝ բացատրելով յուրաքանչյուր քայլի իմաստը։",
      "ru": "На основе диагностики составляем понятный поэтапный план лечения и объясняем смысл каждого шага.",
      "en": "Based on the diagnostics, we build a clear, staged treatment plan and walk you through what each step is for."
    }
  },
  {
    "step": "04",
    "title": {
      "hy": "Բուժում",
      "ru": "Лечение",
      "en": "Treatment"
    },
    "desc": {
      "hy": "Իրականացնում ենք բուժումը՝ առաջնորդվելով պլանով, ժամանակակից տեխնոլոգիաներով և հարմարավետության հանդեպ ուշադրությամբ։",
      "ru": "Проводим лечение согласно плану, с использованием современных технологий и вниманием к вашему комфорту на каждом этапе.",
      "en": "We carry out the treatment according to plan, using modern technology and paying close attention to your comfort throughout."
    }
  },
  {
    "step": "05",
    "title": {
      "hy": "Հետբուժումային հսկողություն",
      "ru": "Наблюдение после лечения",
      "en": "Follow-up"
    },
    "desc": {
      "hy": "Հետևում ենք արդյունքին, նշանակում ենք վերահսկիչ այցեր և միշտ հասանելի ենք հարցերի դեպքում։",
      "ru": "Следим за результатом, назначаем контрольные визиты и остаёмся на связи, если у вас появятся вопросы.",
      "en": "We monitor how you're healing, schedule check-ins, and stay reachable if anything comes up afterward."
    }
  }
]
```

### `content/ru.json` — полный шаблон UI-текста интерфейса (МЕХАНИКА текста, кроме упоминаний "ELIT DENT" — их заменить на новое название; повторить структуру для каждого языка из брифа)

```json
{
  "htmlLang": "ru",
  "dir": "ltr",
  "meta": {
    "titleSuffix": "ELIT DENT — Премиальная стоматология"
  },
  "nav": {
    "home": "Главная",
    "services": "Услуги",
    "doctors": "Врачи",
    "technology": "Технологии",
    "about": "О клинике",
    "reviews": "Отзывы",
    "contact": "Контакты",
    "bookConsultation": "Записаться на консультацию"
  },
  "common": {
    "call": "Позвонить",
    "whatsapp": "WhatsApp",
    "learnMore": "Подробнее",
    "readMore": "Читать далее",
    "viewAll": "Смотреть все",
    "backTo": "Назад к",
    "close": "Закрыть",
    "menu": "Меню",
    "language": "Язык",
    "priceNote": "Стоимость после консультации",
    "demoDataBadge": "Демо-данные"
  },
  "hero": {
    "eyebrow": "Современная стоматология, личный подход",
    "headline": "Лечение, спланированное вокруг вас, а не по шаблону",
    "description": "Цифровая диагностика, индивидуально спланированное лечение и команда, которая объясняет каждый шаг заранее.",
    "ctaPrimary": "Записаться на консультацию",
    "ctaSecondary": "Написать в WhatsApp",
    "trustChips": [
      "Цифровая стоматология",
      "3 языка",
      "Индивидуальное планирование"
    ]
  },
  "trust": {
    "title": "Почему пациенты выбирают ELIT DENT",
    "items": {
      "digitalDentistry": {
        "title": "Цифровая стоматология",
        "desc": "3D-диагностика и внутриротовое сканирование в основе каждого плана лечения."
      },
      "threeLanguages": {
        "title": "3 языка",
        "desc": "Консультация и лечение на армянском, русском и английском языках."
      },
      "advancedDiagnostics": {
        "title": "Продвинутая диагностика",
        "desc": "3D КТ-снимки и стоматологический микроскоп для точных решений."
      },
      "personalPlanning": {
        "title": "Индивидуальное планирование",
        "desc": "Поэтапный план именно для вашего случая, объяснённый до начала лечения."
      }
    },
    "stats": {
      "yearsExperience": "лет клинике",
      "specialists": "специалистов",
      "languages": "языка приёма",
      "treatmentAreas": "направлений лечения"
    }
  },
  "services": {
    "eyebrow": "Услуги",
    "title": "Лечение, выстроенное вокруг вашего случая",
    "description": "От плановой профилактики до сложной имплантации и эстетики — каждая услуга начинается с плана, а не с догадок.",
    "ctaViewAll": "Смотреть все услуги"
  },
  "technology": {
    "eyebrow": "Технологии",
    "title": "Точность в основе каждого решения",
    "description": "Цифровые инструменты, которые делают планирование лечения точным, а не приблизительным."
  },
  "doctorSpotlight": {
    "eyebrow": "Знакомство с врачом",
    "title": "Планирование всегда предшествует лечению",
    "description": "Каждый случай начинается с разговора и понятного плана — на удобном для вас языке.",
    "ctaMeetTeam": "Познакомиться с командой"
  },
  "patientExperience": {
    "eyebrow": "Ваш визит",
    "title": "От первого «здравствуйте» до плана лечения",
    "description": "Чего ожидать, шаг за шагом.",
    "steps": {
      "arrival": {
        "title": "Приход в клинику",
        "desc": "Спокойная встреча и короткий разговор о том, что вас беспокоит."
      },
      "consultation": {
        "title": "Консультация",
        "desc": "Сначала слушаем, затем осматриваем, затем объясняем, что увидели."
      },
      "diagnostics": {
        "title": "Диагностика",
        "desc": "Цифровые снимки там, где это нужно, — чтобы не оставалось догадок."
      },
      "treatment": {
        "title": "Лечение",
        "desc": "Проводится по плану, который вы уже видели и поняли."
      },
      "followUp": {
        "title": "Наблюдение после лечения",
        "desc": "Мы на связи после лечения и отвечаем на вопросы, если они возникают."
      }
    }
  },
  "team": {
    "eyebrow": "Наша команда",
    "title": "Люди, которые заботятся о вас",
    "description": "Команда, выстроенная вокруг понятной коммуникации и цифрового планирования."
  },
  "reviews": {
    "eyebrow": "Отзывы пациентов",
    "title": "Что говорят пациенты",
    "description": "Истории людей, которые прошли лечение в ELIT DENT — от первой консультации до результата.",
    "ratingLabel": "Рейтинг пациентов"
  },
  "finalCTA": {
    "eyebrow": "Мы готовы, когда готовы вы",
    "title": "Спланируем ваше лечение вместе",
    "description": "Запишитесь на консультацию или напишите нам напрямую в WhatsApp — ответим на удобном вам языке."
  },
  "footer": {
    "servicesTitle": "Услуги",
    "clinicTitle": "Клиника",
    "contactTitle": "Контакты",
    "languagesTitle": "Языки",
    "socialTitle": "Мы в соцсетях",
    "developedBy": "Концепция и разработка сайта —",
    "rights": "Все права защищены.",
    "disclosure": "Демонстрационная версия сайта. Название клиники, специалисты, отзывы, цены, лицензии, адрес и другие представленные данные являются вымышленными и используются исключительно для демонстрации возможностей сайта."
  },
  "booking": {
    "title": "Запись на консультацию",
    "description": "Заполните несколько полей — подтвердим запись в WhatsApp.",
    "name": "Ваше имя",
    "phone": "Номер телефона",
    "service": "Интересующая услуга",
    "servicePlaceholder": "Выберите услугу",
    "contactMethod": "Удобный способ связи",
    "contactMethodOptions": [
      "WhatsApp",
      "Звонок"
    ],
    "message": "Комментарий (необязательно)",
    "submit": "Отправить через WhatsApp",
    "note": "После отправки откроется WhatsApp с заполненным сообщением — ничего не отправляется автоматически."
  },
  "whatsapp": {
    "defaultMessage": "Здравствуйте! Я посмотрел(а) сайт ELIT DENT и хочу записаться на консультацию.",
    "serviceMessageTemplate": "Здравствуйте! Я посмотрел(а) сайт ELIT DENT. Меня интересует «{service}», хочу узнать подробнее и записаться на консультацию.",
    "doctorMessageTemplate": "Здравствуйте! Я посмотрел(а) сайт ELIT DENT и хочу записаться на консультацию к {doctor}.",
    "bookingMessageTemplate": "Здравствуйте! Меня зовут {name}. Телефон: {phone}. Хочу записаться на консультацию{doctorClause}{serviceClause}. Удобный способ связи: {contact}.{messageClause}",
    "serviceClauseTemplate": " по услуге «{service}»",
    "doctorClauseTemplate": " к врачу {doctor}",
    "messageClauseTemplate": " Комментарий: {message}"
  },
  "servicesPage": {
    "eyebrow": "Все услуги",
    "title": "Стоматология, выстроенная вокруг вашего случая",
    "description": "Каждая страница услуги рассказывает, что это, кому подходит и как мы планируем лечение — до того, как вы на что-то согласитесь."
  },
  "serviceDetail": {
    "breadcrumbServices": "Услуги",
    "aboutTitle": "О лечении",
    "whoTitle": "Кому подходит",
    "benefitsTitle": "Преимущества",
    "processTitle": "Как мы работаем",
    "technologyTitle": "Используемые технологии",
    "doctorTitle": "Ваш врач",
    "pricingTitle": "Стоимость",
    "faqTitle": "Частые вопросы",
    "relatedTitle": "Похожие услуги",
    "ctaTitle": "Готовы обсудить свой случай?",
    "ctaDescription": "Запишитесь на консультацию или напишите в WhatsApp — расскажем о следующем шаге."
  },
  "doctorsPage": {
    "eyebrow": "Наши врачи",
    "title": "Команда, которая планирует ваше лечение",
    "description": "Каждый врач ELIT DENT работает по одному принципу: сначала диагностика, затем понятный план, затем объяснение каждого шага."
  },
  "doctorDetail": {
    "backToDoctors": "Все врачи",
    "expertiseTitle": "Направления",
    "servicesTitle": "Услуги",
    "languagesTitle": "Языки",
    "experienceLabel": "Стаж",
    "experienceSuffix": "лет",
    "educationTitle": "Образование и квалификация",
    "certificationsTitle": "Сертификаты",
    "ctaTitle": "Записаться на консультацию",
    "ctaDescription": "Врач и время подтвердим в WhatsApp сразу после сообщения."
  },
  "technologyPage": {
    "eyebrow": "Технологии",
    "title": "Оборудование, которое обеспечивает точность",
    "description": "Мы объясняем не только, что делает каждый прибор, но и что это значит лично для вас."
  },
  "aboutPage": {
    "eyebrow": "О клинике ELIT DENT",
    "title": "Стоматология, построенная на планировании, а не на рутине",
    "sections": {
      "philosophy": {
        "title": "Наша философия",
        "body": "Мы считаем, что хорошая стоматология начинается ещё до того, как инструмент коснётся зуба, — с чёткой диагностики и плана, который вы действительно понимаете."
      },
      "patientApproach": {
        "title": "Наш подход к пациентам",
        "body": "Каждый визит начинается с разговора. Мы объясняем находки простым языком, на удобном вам языке, и не начинаем лечение, пока план не согласован."
      },
      "digitalDentistry": {
        "title": "Цифровая стоматология",
        "body": "3D-снимки, внутриротовое сканирование и лечение под микроскопом позволяют планировать точно и показать вам, чего ожидать, ещё до начала лечения."
      },
      "team": {
        "title": "Наша команда",
        "body": "Сфокусированная команда специалистов — имплантология, ортодонтия, эстетическая стоматология, общая и семейная практика — работающих по единому стандарту."
      },
      "clinicEnvironment": {
        "title": "Клиника",
        "body": "Спокойная, неторопливая атмосфера, продуманная для комфорта пациента — от зоны ожидания до кабинета."
      },
      "technology": {
        "title": "Технологии",
        "body": "Полный список диагностических и лечебных инструментов — на отдельной странице «Технологии»."
      },
      "patientExperience": {
        "title": "Ваш опыт",
        "body": "От первого сообщения до контрольного визита — с вами работает одна и та же команда."
      },
      "cta": {
        "title": "Есть вопрос перед записью?",
        "body": "Напишите в WhatsApp или позвоните — с радостью ответим, прежде чем вы на что-то решитесь."
      }
    }
  },
  "reviewsPage": {
    "eyebrow": "Отзывы",
    "title": "Отзывы пациентов",
    "description": "Что говорят пациенты ELIT DENT о лечении, враче и общем впечатлении от клиники."
  },
  "contactPage": {
    "eyebrow": "Контакты",
    "title": "Обсудим ваш случай",
    "description": "Позвоните, напишите в WhatsApp или запишитесь на консультацию напрямую — как вам удобнее.",
    "phoneLabel": "Телефон",
    "emailLabel": "Email",
    "whatsappLabel": "WhatsApp",
    "hoursLabel": "Часы работы",
    "hoursWeekday": "Пн–Пт",
    "hoursWeekdayTime": "09:00–19:00",
    "hoursSaturday": "Сб",
    "hoursSaturdayTime": "10:00–17:00",
    "hoursSunday": "Вс",
    "hoursSundayTime": "по предварительной записи",
    "addressLabel": "Адрес",
    "directionsCta": "Открыть маршрут в Google Картах",
    "formTitle": "Написать нам",
    "paymentTitle": "Способы оплаты",
    "paymentOptions": [
      "Наличные",
      "Оплата картой",
      "Банковский перевод",
      "Рассрочка на длительное лечение — по согласованию"
    ],
    "safetyTitle": "Стерилизация и безопасность",
    "safetyItems": [
      "Многоэтапная стерилизация инструментов по протоколу",
      "Одноразовые расходные материалы там, где это предусмотрено",
      "Контроль упаковки и сроков стерильности инструментов",
      "Журнал стерилизации на каждый цикл",
      "Подготовка кабинета перед каждым пациентом"
    ],
    "generalFaqTitle": "Общие вопросы",
    "generalFaq": [
      {
        "q": "Можно ли записать ребёнка",
        "a": "Да, часть врачей принимает детей — при записи укажите возраст ребёнка, и мы подберём подходящего специалиста."
      },
      {
        "q": "Есть ли рассрочка на дорогостоящее лечение",
        "a": "Для протяжённого лечения (импланты, ортодонтия) возможна поэтапная оплата — условия обсуждаются на консультации."
      },
      {
        "q": "Какие есть противопоказания к лечению",
        "a": "Противопоказания индивидуальны и зависят от общего состояния здоровья — врач уточнит их на приёме перед составлением плана."
      },
      {
        "q": "Нужно ли брать с собой снимки, если они уже есть",
        "a": "Да, любые предыдущие снимки или медицинская история помогают точнее спланировать лечение с первого визита."
      }
    ]
  },
  "mobileBar": {
    "call": "Звонок",
    "whatsapp": "WhatsApp",
    "book": "Запись"
  },
  "notFound": {
    "title": "Страница не найдена",
    "description": "Страница, которую вы ищете, не существует или была перемещена.",
    "cta": "На главную"
  }
}
```

---

# ПОЛНЫЙ ИСХОДНЫЙ КОД МЕХАНИКИ (воспроизвести дословно, файл за файлом)

Ниже — весь код `build.py`, `validate.py`, все Jinja2-шаблоны, весь CSS и
весь JS сайта ELIT DENT. Создай точно такие же файлы по указанным путям с
точно таким же содержимым. Единственное, что можно/нужно менять внутри этих
файлов — это ничего: вся логика механическая. Если бриф просит другой набор
языков, единственная правка — список `languages.supported`/`default` в
`data/site.json`, сам код ниже уже работает с произвольным списком языков
через циклы.

### FILE: `build.py`

```python
#!/usr/bin/env python3
"""
ELIT DENT / ORDER PROFIT dental engine — static site generator.

Reads /data (structured content) + /content/{lang}.json (UI strings) and
renders /templates through Jinja2 into /dist/{lang}/... This is the
"reusable engine" referenced in CUSTOMIZATION_GUIDE.md: swapping the JSON
in /data and /content, plus the tokens in static/css/tokens.css, is enough
to reskin the whole site for a different clinic without touching templates.
"""
import json
import os
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
DATA = ROOT / "data"
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

SITE_URL = None  # resolved in main(): $SITE_URL env var, else data/site.json -> seo.productionUrl


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def slugify_href(lang_prefix, *parts):
    return "/" + "/".join([lang_prefix.strip("/")] + [p.strip("/") for p in parts if p]) + "/"


def localize_service(raw, lang, lang_prefix, doctors_by_slug, tech_by_slug, services_by_slug):
    href = slugify_href(lang_prefix, "services", raw["slug"])
    doctor = None
    if raw.get("doctorSlug") and raw["doctorSlug"] in doctors_by_slug:
        d = doctors_by_slug[raw["doctorSlug"]]
        doctor = {
            "slug": d["slug"],
            "name": d["name"],
            "role": d["role"][lang],
            "photo": d["photo"],
            "href": slugify_href(lang_prefix, "doctors", d["slug"]),
        }
    technologies = []
    for t_slug in raw.get("technologyRefs", []):
        t = tech_by_slug.get(t_slug)
        if t:
            technologies.append({
                "slug": t["slug"],
                "name": t["name"][lang],
                "shortExplain": t["shortExplain"][lang],
                "image": t["image"],
            })
    related = []
    for r_slug in raw.get("relatedSlugs", []):
        r = services_by_slug.get(r_slug)
        if r:
            related.append({
                "slug": r["slug"],
                "title": r["title"][lang],
                "shortCopy": r["shortCopy"][lang],
                "cardImage": r["cardImage"],
                "href": slugify_href(lang_prefix, "services", r["slug"]),
            })
    faq = [{"q": item["q"][lang], "a": item["a"][lang]} for item in raw.get("faq", [])]
    return {
        "slug": raw["slug"],
        "icon": raw["icon"],
        "flagship": raw.get("flagship", False),
        "href": href,
        "cardImage": raw["cardImage"],
        "heroImage": raw["heroImage"],
        "eyebrow": raw["eyebrow"][lang],
        "title": raw["title"][lang],
        "shortCopy": raw["shortCopy"][lang],
        "intro": raw["intro"][lang],
        "aboutTreatment": raw["aboutTreatment"][lang],
        "whoItIsFor": raw["whoItIsFor"][lang],
        "benefits": raw["benefits"][lang],
        "faq": faq,
        "priceNote": raw["price"]["note"][lang],
        "priceDisplay": f"{raw['price']['prefix'][lang]} {raw['price']['amount']} {raw['price']['currency']}",
        "doctor": doctor,
        "technologies": technologies,
        "related": related,
    }


def localize_doctor(raw, lang, lang_prefix, services_by_slug):
    services = []
    for s_slug in raw.get("services", []):
        s = services_by_slug.get(s_slug)
        if s:
            services.append({
                "slug": s["slug"],
                "title": s["title"][lang],
                "href": slugify_href(lang_prefix, "services", s["slug"]),
            })
    certifications = [
        {"id": c["id"], "label": c["label"][lang]}
        for c in raw.get("certifications", [])
    ]
    return {
        "slug": raw["slug"],
        "name": raw["name"],
        "role": raw["role"][lang],
        "photo": raw["photo"],
        "workingPhoto": raw["workingPhoto"],
        "quote": raw["quote"][lang],
        "bio": raw["bio"][lang],
        "languages": raw["languages"],
        "services": services,
        "href": slugify_href(lang_prefix, "doctors", raw["slug"]),
        "experienceYears": raw.get("experienceYears"),
        "education": raw.get("education", {}).get(lang, []),
        "certifications": certifications,
    }


def localize_technology(raw, lang):
    return {
        "slug": raw["slug"],
        "icon": raw["icon"],
        "image": raw["image"],
        "name": raw["name"][lang],
        "shortExplain": raw["shortExplain"][lang],
        "patientBenefit": raw["patientBenefit"][lang],
    }


def localize_review(raw, lang, services_by_slug):
    service_title = None
    if raw.get("serviceSlug") and raw["serviceSlug"] in services_by_slug:
        service_title = services_by_slug[raw["serviceSlug"]]["title"][lang]
    return {
        "id": raw["id"],
        "authorInitial": raw["authorInitial"][lang],
        "quote": raw["quote"][lang],
        "serviceTitle": service_title,
    }


def build_nav_items(t, lang_prefix, active_key):
    entries = [
        ("home", slugify_href(lang_prefix)),
        ("services", slugify_href(lang_prefix, "services")),
        ("doctors", slugify_href(lang_prefix, "doctors")),
        ("technology", slugify_href(lang_prefix, "technology")),
        ("about", slugify_href(lang_prefix, "about")),
        ("reviews", slugify_href(lang_prefix, "reviews")),
        ("contact", slugify_href(lang_prefix, "contact")),
    ]
    return [
        {"key": key, "href": href, "label": t["nav"][key], "active": key == active_key}
        for key, href in entries
    ]


def breadcrumb_list_schema(items, site_url):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": item["name"], "item": site_url + item["href"]}
            for i, item in enumerate(items)
        ],
    }


def main():
    global SITE_URL
    site = load_json(DATA / "site.json")
    SITE_URL = os.environ.get("SITE_URL") or site["seo"]["productionUrl"]
    SITE_URL = SITE_URL.rstrip("/")
    services_raw = load_json(DATA / "services.json")
    doctors_raw = load_json(DATA / "doctors.json")
    technology_raw = load_json(DATA / "technology.json")
    reviews_raw = load_json(DATA / "reviews.json")
    process_default = load_json(DATA / "process-default.json")

    content = {lang: load_json(CONTENT / f"{lang}.json") for lang in site["languages"]["supported"]}

    services_by_slug = {s["slug"]: s for s in services_raw}
    doctors_by_slug = {d["slug"]: d for d in doctors_raw}
    tech_by_slug = {t["slug"]: t for t in technology_raw}

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    wa_number = site["contact"]["whatsappNumber"]
    env.globals["wa_url"] = lambda message: "https://wa.me/" + wa_number + "?text=" + quote(message)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    all_pages = []  # for sitemap: (lang, path)
    languages = site["languages"]["supported"]

    for lang in languages:
        t = content[lang]
        lang_prefix = f"/{lang}"

        services = [localize_service(s, lang, lang_prefix, doctors_by_slug, tech_by_slug, services_by_slug) for s in services_raw]
        doctors = [localize_doctor(d, lang, lang_prefix, services_by_slug) for d in doctors_raw]
        technologies = [localize_technology(tt, lang) for tt in technology_raw]
        reviews = [localize_review(r, lang, services_by_slug) for r in reviews_raw["items"]]

        def base_ctx(canonical_path, active_key, page_title, page_description, page_slug_for_translation):
            translations = {l: f"/{l}{page_slug_for_translation}" for l in languages}
            return {
                "lang": lang,
                "t": t,
                "site": site,
                "site_url": SITE_URL,
                "asset_prefix": "",
                "lang_prefix": lang_prefix,
                "home_url": slugify_href(lang_prefix),
                "nav_items": build_nav_items(t, lang_prefix, active_key),
                "translations": translations,
                "canonical_path": canonical_path,
                "page_title": f"{page_title} — {site['brand']['clinicName']}",
                "page_description": page_description,
                "whatsapp_default_message": t["whatsapp"]["defaultMessage"],
                "all_services": services,
                "footer_services": [{"title": s["title"], "href": s["href"]} for s in services[:6]],
                "current_year": date.today().year,
                "structured_data": None,
                "rating": site["rating"],
            }

        # ---- Home ----
        ctx = base_ctx(slugify_href(lang_prefix), "home", t["meta"]["titleSuffix"], t["hero"]["description"], "/")
        ctx.update({
            "services_home": services[:6],
            "doctors_home": doctors[:3],
            "technologies": technologies,
            "reviews": reviews[:3],
            "doctor_spotlight": doctors[0],
        })
        org_schema = {
            "@context": "https://schema.org",
            "@type": "Dentist",
            "name": site["brand"]["clinicName"],
            "telephone": site["contact"]["phone"],
        }
        ctx["structured_data"] = json.dumps(org_schema, ensure_ascii=False)
        html = env.get_template("pages/home.html").render(**ctx)
        write_file(DIST / lang / "index.html", html)
        all_pages.append((lang, f"/{lang}/"))

        # ---- Services list ----
        ctx = base_ctx(slugify_href(lang_prefix, "services"), "services", t["servicesPage"]["title"], t["servicesPage"]["description"], "/services/")
        ctx["services"] = services
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["services"], "href": slugify_href(lang_prefix, "services")},
        ]
        html = env.get_template("pages/services.html").render(**ctx)
        write_file(DIST / lang / "services" / "index.html", html)
        all_pages.append((lang, f"/{lang}/services/"))

        # ---- Service detail pages ----
        for s in services:
            ctx = base_ctx(s["href"], "services", s["title"], s["shortCopy"], f"/services/{s['slug']}/")
            ctx["service"] = s
            ctx["process_steps"] = [
                {"step": step["step"], "title": step["title"][lang], "desc": step["desc"][lang]}
                for step in process_default
            ]
            breadcrumb = [
                {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
                {"name": t["nav"]["services"], "href": slugify_href(lang_prefix, "services")},
                {"name": s["title"], "href": s["href"]},
            ]
            ctx["breadcrumb"] = breadcrumb
            schema = {
                "@context": "https://schema.org",
                "@graph": [
                    breadcrumb_list_schema(breadcrumb, SITE_URL),
                    {
                        "@context": "https://schema.org",
                        "@type": "Service",
                        "name": s["title"],
                        "description": s["shortCopy"],
                        "provider": {"@type": "Dentist", "name": site["brand"]["clinicName"]},
                    },
                ] + ([{
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": [
                        {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                        for f in s["faq"]
                    ],
                }] if s["faq"] else []),
            }
            ctx["structured_data"] = json.dumps(schema, ensure_ascii=False)
            html = env.get_template("pages/service_detail.html").render(**ctx)
            write_file(DIST / lang / "services" / s["slug"] / "index.html", html)
            all_pages.append((lang, s["href"]))

        # ---- Doctors list ----
        ctx = base_ctx(slugify_href(lang_prefix, "doctors"), "doctors", t["doctorsPage"]["title"], t["doctorsPage"]["description"], "/doctors/")
        ctx["doctors"] = doctors
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["doctors"], "href": slugify_href(lang_prefix, "doctors")},
        ]
        html = env.get_template("pages/doctors.html").render(**ctx)
        write_file(DIST / lang / "doctors" / "index.html", html)
        all_pages.append((lang, f"/{lang}/doctors/"))

        # ---- Doctor detail pages ----
        for d in doctors:
            ctx = base_ctx(d["href"], "doctors", d["name"], d["bio"], f"/doctors/{d['slug']}/")
            ctx["doctor"] = d
            breadcrumb = [
                {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
                {"name": t["nav"]["doctors"], "href": slugify_href(lang_prefix, "doctors")},
                {"name": d["name"], "href": d["href"]},
            ]
            ctx["breadcrumb"] = breadcrumb
            schema = {"@context": "https://schema.org", "@graph": [
                breadcrumb_list_schema(breadcrumb, SITE_URL),
                {"@context": "https://schema.org", "@type": "Person", "name": d["name"], "jobTitle": d["role"], "worksFor": {"@type": "Dentist", "name": site["brand"]["clinicName"]}},
            ]}
            ctx["structured_data"] = json.dumps(schema, ensure_ascii=False)
            html = env.get_template("pages/doctor_detail.html").render(**ctx)
            write_file(DIST / lang / "doctors" / d["slug"] / "index.html", html)
            all_pages.append((lang, d["href"]))

        # ---- Technology ----
        ctx = base_ctx(slugify_href(lang_prefix, "technology"), "technology", t["technologyPage"]["title"], t["technologyPage"]["description"], "/technology/")
        ctx["technologies"] = technologies
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["technology"], "href": slugify_href(lang_prefix, "technology")},
        ]
        html = env.get_template("pages/technology.html").render(**ctx)
        write_file(DIST / lang / "technology" / "index.html", html)
        all_pages.append((lang, f"/{lang}/technology/"))

        # ---- About ----
        ctx = base_ctx(slugify_href(lang_prefix, "about"), "about", t["aboutPage"]["title"], t["aboutPage"]["title"], "/about/")
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["about"], "href": slugify_href(lang_prefix, "about")},
        ]
        html = env.get_template("pages/about.html").render(**ctx)
        write_file(DIST / lang / "about" / "index.html", html)
        all_pages.append((lang, f"/{lang}/about/"))

        # ---- Reviews ----
        ctx = base_ctx(slugify_href(lang_prefix, "reviews"), "reviews", t["reviewsPage"]["title"], t["reviewsPage"]["description"], "/reviews/")
        ctx["reviews"] = reviews
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["reviews"], "href": slugify_href(lang_prefix, "reviews")},
        ]
        html = env.get_template("pages/reviews.html").render(**ctx)
        write_file(DIST / lang / "reviews" / "index.html", html)
        all_pages.append((lang, f"/{lang}/reviews/"))

        # ---- Contact ----
        ctx = base_ctx(slugify_href(lang_prefix, "contact"), "contact", t["contactPage"]["title"], t["contactPage"]["description"], "/contact/")
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["contact"], "href": slugify_href(lang_prefix, "contact")},
        ]
        html = env.get_template("pages/contact.html").render(**ctx)
        write_file(DIST / lang / "contact" / "index.html", html)
        all_pages.append((lang, f"/{lang}/contact/"))

        # ---- 404 ----
        # Written as a flat lang/404.html (not lang/404/index.html) since that's
        # the file shape static hosts (Netlify, S3, GitHub Pages, etc.) look for
        # as a custom per-path error page — so its canonical/hreflang must point
        # at the flat .html path too, not the directory-style URLs every other
        # page uses.
        ctx = base_ctx(f"/{lang}/404.html", "home", t["notFound"]["title"], t["notFound"]["description"], "/404.html")
        ctx["robots_noindex"] = True
        html = env.get_template("pages/404.html").render(**ctx)
        write_file(DIST / lang / "404.html", html)

    # ---- Root redirect (default language) ----
    default_lang = site["languages"]["default"]
    redirect_html = f"""<!doctype html>
<html lang="{default_lang}">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=/{default_lang}/">
<meta name="description" content="{site['brand']['clinicName']} — {site['brand']['tagline'][default_lang]}.">
<link rel="canonical" href="{SITE_URL}/{default_lang}/">
<title>{site['brand']['clinicName']}</title>
</head>
<body><p><a href="/{default_lang}/">{site['brand']['clinicName']}</a></p></body>
</html>"""
    write_file(DIST / "index.html", redirect_html)

    # ---- Root 404 (for hosts that look for a top-level 404.html, e.g. Vercel) ----
    shutil.copy(DIST / default_lang / "404.html", DIST / "404.html")

    # ---- robots.txt ----
    robots = f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"
    write_file(DIST / "robots.txt", robots)

    # ---- sitemap.xml ----
    urlset = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    seen = set()
    for lang, path in all_pages:
        if path in seen:
            continue
        seen.add(path)
        alt_links = "".join(
            f'<xhtml:link rel="alternate" hreflang="{l}" href="{SITE_URL}/{l}{path[len("/"+lang):]}"/>'
            for l in languages
        )
        urlset.append(f'<url><loc>{SITE_URL}{path}</loc>{alt_links}</url>')
    urlset.append("</urlset>")
    write_file(DIST / "sitemap.xml", "\n".join(urlset))

    # ---- Copy static assets ----
    shutil.copytree(STATIC / "css", DIST / "css", dirs_exist_ok=True)
    shutil.copytree(STATIC / "js", DIST / "js", dirs_exist_ok=True)
    shutil.copytree(STATIC / "images", DIST / "images", dirs_exist_ok=True,
                     ignore=shutil.ignore_patterns("real"))
    shutil.copytree(STATIC / "brand", DIST / "brand", dirs_exist_ok=True,
                     ignore=shutil.ignore_patterns("source"))
    for favicon_name in ("favicon-16.png", "favicon-32.png", "apple-touch-icon.png", "favicon-512.png"):
        src = STATIC / favicon_name
        if src.exists():
            shutil.copy(src, DIST / favicon_name)

    print(f"Built {len(all_pages)} pages across {len(languages)} languages into {DIST}")


if __name__ == "__main__":
    main()

```

### FILE: `validate.py`

```python
#!/usr/bin/env python3
"""
Post-build validator for the ELIT DENT / ORDER PROFIT dental engine.

Run after `python3 build.py`. Two passes:

1. Structural checks over every file in dist/: broken internal links,
   missing images, leftover placeholder/Lorem-ipsum/unrendered-template
   text, stray href="#", missing <title>/meta description/canonical,
   duplicate canonicals, and hy/ru/en content parity (every canonical
   path that exists in one language must exist in all supported ones).
2. Data-consistency checks over data/*.json directly: doctor count,
   service count, review count and the site-wide "stats" numbers must
   all agree with each other, since they're quoted independently on
   several pages (home trust strip, about page, doctor bios).

Exits 1 if anything is found, 0 if the build is clean. Intended to run
in CI / right before a deploy, not as part of build.py itself, so a
build can still be inspected locally even when it fails validation.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DIST = ROOT / "dist"

errors = []
warnings = []

PLACEHOLDER_PATTERNS = [
    r"\blorem ipsum\b",
    r"\bplaceholder\b",
    r"\bTBD\b",
    r"\bTODO\b",
    r"\bundefined\b",
    r"\bNone\b",
    r"уточняется",
    r"будет добавлено",
    r"\{\{",
    r"\{%",
]

HREF_RE = re.compile(r'href="([^"]*)"')
SRC_RE = re.compile(r'src="([^"]*)"')
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
DESC_RE = re.compile(r'<meta name="description" content="([^"]*)"')
CANONICAL_RE = re.compile(r'<link rel="canonical" href="([^"]*)"')


def check_html_file(path, canonicals_seen):
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(DIST).as_posix()

    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, text):
            errors.append(f"{rel}: matches placeholder/unrendered pattern /{pat}/")

    for m in re.finditer(r"elitdent\.example", text):
        context = text[max(0, m.start() - 20):m.start()]
        if "info@" not in context:
            errors.append(f"{rel}: stray elitdent.example outside the demo contact email")

    if 'href="#"' in text:
        errors.append(f'{rel}: href="#" placeholder link found')

    title_m = TITLE_RE.search(text)
    if not title_m or not title_m.group(1).strip():
        errors.append(f"{rel}: missing or empty <title>")

    desc_m = DESC_RE.search(text)
    if not desc_m or not desc_m.group(1).strip():
        errors.append(f"{rel}: missing or empty meta description")

    canon_m = CANONICAL_RE.search(text)
    if not canon_m:
        errors.append(f"{rel}: missing canonical link")
    else:
        canonicals_seen.setdefault(canon_m.group(1), []).append(rel)

    for href in HREF_RE.findall(text):
        check_internal_link(href, rel)
    for src in SRC_RE.findall(text):
        check_asset(src, rel)


def check_internal_link(href, rel):
    if not href or href.startswith(("http://", "https://", "mailto:", "tel:", "whatsapp:", "#")):
        return
    path = href.split("#")[0].split("?")[0]
    if not path:
        return
    target = DIST / path.lstrip("/") / "index.html" if path.endswith("/") else DIST / path.lstrip("/")
    if not target.exists():
        errors.append(f"{rel}: broken internal link -> {href}")


def check_asset(src, rel):
    if not src or src.startswith(("http://", "https://", "data:")):
        return
    target = DIST / src.lstrip("/")
    if not target.exists():
        errors.append(f"{rel}: missing asset -> {src}")


def check_language_parity():
    """Every /hy/... page must have a matching /ru/... and /en/... page."""
    languages = ["hy", "ru", "en"]
    page_dirs = {lang: set() for lang in languages}
    for lang in languages:
        lang_root = DIST / lang
        if not lang_root.exists():
            errors.append(f"missing top-level language directory: {lang}/")
            continue
        for index_file in lang_root.rglob("index.html"):
            page_dirs[lang].add(index_file.parent.relative_to(lang_root).as_posix())
    all_slugs = set().union(*page_dirs.values()) if page_dirs else set()
    for slug in sorted(all_slugs):
        missing = [lang for lang in languages if slug not in page_dirs[lang]]
        if missing:
            errors.append(f"page '{slug}' missing for language(s): {', '.join(missing)}")


def check_sitemap_and_robots():
    robots = DIST / "robots.txt"
    if not robots.exists():
        errors.append("robots.txt missing from dist/")
    elif "Sitemap:" not in robots.read_text(encoding="utf-8"):
        errors.append("robots.txt has no Sitemap: line")

    sitemap = DIST / "sitemap.xml"
    if not sitemap.exists():
        errors.append("sitemap.xml missing from dist/")
    else:
        text = sitemap.read_text(encoding="utf-8")
        if "elitdent.example" in text:
            errors.append("sitemap.xml contains the placeholder elitdent.example domain")
        if not text.strip().startswith("<?xml"):
            errors.append("sitemap.xml does not look like well-formed XML")


def check_data_consistency():
    site = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
    doctors = json.loads((DATA / "doctors.json").read_text(encoding="utf-8"))
    services = json.loads((DATA / "services.json").read_text(encoding="utf-8"))
    reviews = json.loads((DATA / "reviews.json").read_text(encoding="utf-8"))

    stats = {s["key"]: s["value"] for s in site.get("stats", [])}

    if stats.get("specialists") != str(len(doctors)):
        errors.append(
            f"data/site.json stats.specialists = {stats.get('specialists')!r} "
            f"but data/doctors.json has {len(doctors)} doctors"
        )
    if stats.get("treatmentAreas") != str(len(services)):
        errors.append(
            f"data/site.json stats.treatmentAreas = {stats.get('treatmentAreas')!r} "
            f"but data/services.json has {len(services)} services"
        )
    if stats.get("languages") != str(len(site["languages"]["supported"])):
        errors.append(
            f"data/site.json stats.languages = {stats.get('languages')!r} "
            f"but {len(site['languages']['supported'])} languages are configured"
        )

    rating = site.get("rating", {})
    if rating.get("count") != len(reviews["items"]):
        errors.append(
            f"data/site.json rating.count = {rating.get('count')!r} "
            f"but data/reviews.json has {len(reviews['items'])} reviews"
        )
    if reviews.get("aggregateRatingEnabled") and not site.get("featureFlags", {}).get("demoMode") is False:
        # demoMode=true + aggregateRatingEnabled=true is fine for the UI rating line,
        # but must never be paired with a fabricated AggregateRating JSON-LD block.
        for lang in site["languages"]["supported"]:
            home = DIST / lang / "index.html"
            if home.exists() and "AggregateRating" in home.read_text(encoding="utf-8"):
                errors.append(
                    f"{lang}/index.html emits AggregateRating JSON-LD while demoMode is true "
                    "— fabricated third-party rating schema is not allowed in demo mode"
                )

    doctor_slugs = {d["slug"] for d in doctors}
    service_slugs = {s["slug"] for s in services}
    for s in services:
        if s.get("doctorSlug") and s["doctorSlug"] not in doctor_slugs:
            errors.append(f"data/services.json: service '{s['slug']}' references unknown doctorSlug '{s['doctorSlug']}'")
    for d in doctors:
        for s_slug in d.get("services", []):
            if s_slug not in service_slugs:
                errors.append(f"data/doctors.json: doctor '{d['slug']}' references unknown service '{s_slug}'")
    for r in reviews["items"]:
        if r.get("serviceSlug") and r["serviceSlug"] not in service_slugs:
            errors.append(f"data/reviews.json: review '{r['id']}' references unknown serviceSlug '{r['serviceSlug']}'")

    max_experience = max((d.get("experienceYears", 0) for d in doctors), default=0)
    founded_year_gap = 2026 - site["brand"].get("foundedYear", 2026)
    if stats.get("yearsExperience", "").rstrip("+") and int(stats["yearsExperience"].rstrip("+")) > max(max_experience, founded_year_gap):
        errors.append(
            f"data/site.json stats.yearsExperience = {stats.get('yearsExperience')!r} "
            f"is higher than any doctor's experienceYears (max {max_experience}) or the clinic's own age ({founded_year_gap}y)"
        )


def main():
    if not DIST.exists():
        print("dist/ does not exist — run `python3 build.py` first.", file=sys.stderr)
        sys.exit(1)

    canonicals_seen = {}
    html_files = sorted(DIST.rglob("*.html"))
    for path in html_files:
        check_html_file(path, canonicals_seen)

    # index.html and 404.html at dist root are intentional mechanical copies
    # (a meta-refresh redirect stub to the default language, and a root 404 for
    # hosts like Vercel that look for one) — they share their canonical with the
    # real page on purpose, so they're excluded from the duplicate check.
    root_copies = {"index.html", "404.html"}
    for url, files in canonicals_seen.items():
        real_dupes = [f for f in files if f not in root_copies]
        if len(real_dupes) > 1:
            errors.append(f"duplicate canonical '{url}' used by: {', '.join(real_dupes)}")

    check_language_parity()
    check_sitemap_and_robots()
    check_data_consistency()

    print(f"Checked {len(html_files)} HTML files in {DIST}.")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        print(f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s).")
        sys.exit(1)

    print(f"\nPASSED: 0 errors, {len(warnings)} warning(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()

```

### FILE: `templates/base.html`

```html
<!doctype html>
<html lang="{{ lang }}" dir="{{ t.dir }}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>document.documentElement.classList.add('js-reveal');</script>
<title>{{ page_title }}</title>
<meta name="description" content="{{ page_description }}">
{% if robots_noindex %}<meta name="robots" content="noindex, follow">{% endif %}
<link rel="canonical" href="{{ site_url }}{{ canonical_path }}">
{% for l, path in translations.items() %}
<link rel="alternate" hreflang="{{ l }}" href="{{ site_url }}{{ path }}">
{% endfor %}
<link rel="alternate" hreflang="x-default" href="{{ site_url }}{{ translations[site.languages.default] }}">
<meta property="og:title" content="{{ page_title }}">
<meta property="og:description" content="{{ page_description }}">
<meta property="og:type" content="website">
<meta property="og:locale" content="{{ lang }}">
<meta property="og:url" content="{{ site_url }}{{ canonical_path }}">
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="/favicon-16.png" sizes="16x16" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{{ asset_prefix }}/css/tokens.css">
<link rel="stylesheet" href="{{ asset_prefix }}/css/main.css">
{% if structured_data %}
<script type="application/ld+json">{{ structured_data | safe }}</script>
{% endif %}
</head>
<body data-whatsapp-number="{{ site.contact.whatsappNumber }}" class="has-bottom-bar">

<div class="intro-splash" id="introSplash" aria-hidden="true">
  <img src="{{ asset_prefix }}/brand/logo-splash.jpg" alt="{{ site.brand.clinicName }}" class="intro-splash-logo">
</div>
<script>
(function () {
  var SESSION_KEY = 'elitdentSplashShown';
  var alreadyShown = true;
  try { alreadyShown = sessionStorage.getItem(SESSION_KEY) === '1'; } catch (e) {}
  var el = document.getElementById('introSplash');
  if (alreadyShown || !el) {
    if (el) el.remove();
  } else {
    try { sessionStorage.setItem(SESSION_KEY, '1'); } catch (e) {}
    el.classList.add('is-active');
    document.body.style.overflow = 'hidden';
    setTimeout(function () {
      el.classList.add('is-hiding');
      document.body.style.overflow = '';
      setTimeout(function () { el.remove(); }, 700);
    }, 1500);
  }
})();
</script>

{% include "partials/header.html" %}
{% include "partials/mobile_nav.html" %}

<main>
{% block content %}{% endblock %}
</main>

{% include "partials/footer.html" %}
{% include "partials/booking_modal.html" %}
{% include "partials/bottom_bar.html" %}
{% include "partials/whatsapp_float.html" %}

<script src="{{ asset_prefix }}/js/main.js"></script>
</body>
</html>

```

### FILE: `templates/partials/breadcrumb.html`

```html
{% if breadcrumb %}
<nav class="breadcrumb" aria-label="Breadcrumb">
  {% for b in breadcrumb %}
    {% if not loop.last %}<a href="{{ b.href }}">{{ b.name }}</a><span class="sep">/</span>{% else %}<span>{{ b.name }}</span>{% endif %}
  {% endfor %}
</nav>
{% endif %}

```

### FILE: `templates/partials/header.html`

```html
<header class="site-header">
  <div class="container header-inner">
    <a class="brand" href="{{ home_url }}">
      {% if site.brand.logo.mark %}
        <img class="brand-mark" src="{{ site.brand.logo.mark }}" alt="{{ site.brand.clinicName }}" width="36" height="36">
      {% else %}
        <span class="brand-mark" data-logo-placeholder title="Logo pending — see CONTENT_REQUIRED.md">ED</span>
      {% endif %}
      <span>{{ site.brand.clinicName }}</span>
    </a>

    <nav class="main-nav" aria-label="Primary">
      <ul>
        {% for item in nav_items %}
        <li><a href="{{ item.href }}" class="{{ 'is-active' if item.active else '' }}">{{ item.label }}</a></li>
        {% endfor %}
      </ul>
    </nav>

    <div class="header-actions">
      <div class="lang-switch" aria-label="{{ t.common.language }}">
        {% for l in site.languages.supported %}
        <a href="{{ translations[l] }}" class="{{ 'is-active' if l == lang else '' }}" hreflang="{{ l }}">{{ l | upper }}</a>
        {% endfor %}
      </div>
      <button type="button" class="btn btn-primary btn-sm" data-open-booking>{{ t.nav.bookConsultation }}</button>
    </div>

    <div class="header-mobile-actions">
      <div class="lang-switch" aria-label="{{ t.common.language }}">
        {% for l in site.languages.supported %}
        <a href="{{ translations[l] }}" class="{{ 'is-active' if l == lang else '' }}" hreflang="{{ l }}">{{ l | upper }}</a>
        {% endfor %}
      </div>
      <button type="button" class="hamburger" data-nav-toggle aria-label="{{ t.common.menu }}" aria-expanded="false">
        <span></span>
      </button>
    </div>
  </div>
</header>

```

### FILE: `templates/partials/mobile_nav.html`

```html
<div class="mobile-nav-overlay" data-nav-overlay aria-hidden="true">
  <div class="mobile-nav-top">
    <a class="brand" href="{{ home_url }}">
      {% if site.brand.logo.mark %}
        <img class="brand-mark" src="{{ site.brand.logo.mark }}" alt="{{ site.brand.clinicName }}" width="36" height="36">
      {% else %}
        <span class="brand-mark" data-logo-placeholder>ED</span>
      {% endif %}
      <span>{{ site.brand.clinicName }}</span>
    </a>
    <button type="button" class="hamburger" data-nav-close aria-label="{{ t.common.close }}">✕</button>
  </div>
  <nav class="mobile-nav-list" aria-label="Mobile">
    {% for item in nav_items %}
    <a href="{{ item.href }}">{{ item.label }}</a>
    {% endfor %}
  </nav>
  <div class="mobile-nav-footer">
    <a class="btn btn-outline btn-block" href="{{ site.contact.phoneUri }}">{{ t.common.call }} {{ site.contact.phone }}</a>
    <button type="button" class="btn btn-primary btn-block" data-open-booking>{{ t.nav.bookConsultation }}</button>
  </div>
</div>

```

### FILE: `templates/partials/footer.html`

```html
<footer class="site-footer">
  <div class="container">
    <div class="footer-top">
      <div>
        <div class="footer-brand">{{ site.brand.clinicName }}</div>
        <p class="footer-tagline">{{ site.brand.tagline[lang] }}</p>
      </div>
      <div class="footer-col">
        <h4>{{ t.footer.servicesTitle }}</h4>
        <ul>
          {% for s in footer_services %}
          <li><a href="{{ s.href }}">{{ s.title }}</a></li>
          {% endfor %}
        </ul>
      </div>
      <div class="footer-col">
        <h4>{{ t.footer.clinicTitle }}</h4>
        <ul>
          <li><a href="{{ lang_prefix }}/about/">{{ t.nav.about }}</a></li>
          <li><a href="{{ lang_prefix }}/doctors/">{{ t.nav.doctors }}</a></li>
          <li><a href="{{ lang_prefix }}/technology/">{{ t.nav.technology }}</a></li>
          <li><a href="{{ lang_prefix }}/reviews/">{{ t.nav.reviews }}</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>{{ t.footer.contactTitle }}</h4>
        <ul>
          <li><a href="{{ site.contact.phoneUri }}">{{ site.contact.phone }}</a></li>
          <li><a href="{{ site.contact.whatsappUri }}" target="_blank" rel="noopener">{{ t.common.whatsapp }}</a></li>
          <li><a href="{{ lang_prefix }}/contact/">{{ t.nav.contact }}</a></li>
        </ul>
        {% if site.contact.socials.instagram or site.contact.socials.facebook or site.contact.socials.tiktok or site.contact.socials.youtube %}
        <h4 style="margin-top:24px;">{{ t.footer.socialTitle }}</h4>
        <ul>
          {% if site.contact.socials.instagram %}<li><a href="{{ site.contact.socials.instagram }}" target="_blank" rel="noopener">Instagram</a></li>{% endif %}
          {% if site.contact.socials.facebook %}<li><a href="{{ site.contact.socials.facebook }}" target="_blank" rel="noopener">Facebook</a></li>{% endif %}
          {% if site.contact.socials.tiktok %}<li><a href="{{ site.contact.socials.tiktok }}" target="_blank" rel="noopener">TikTok</a></li>{% endif %}
          {% if site.contact.socials.youtube %}<li><a href="{{ site.contact.socials.youtube }}" target="_blank" rel="noopener">YouTube</a></li>{% endif %}
        </ul>
        {% endif %}
      </div>
    </div>
    <div class="footer-bottom">
      <div>© {{ current_year }} {{ site.brand.clinicName }}. {{ t.footer.rights }}</div>
      <div>{{ t.footer.developedBy }} <span class="footer-developer">{{ site.brand.developer }}</span></div>
    </div>
    <p class="footer-disclosure">{{ t.footer.disclosure }}</p>
  </div>
</footer>

```

### FILE: `templates/partials/booking_modal.html`

```html
<div class="modal-backdrop" data-booking-modal aria-hidden="true">
  <div class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="booking-title">
    <button type="button" class="modal-close" data-close-booking aria-label="{{ t.common.close }}">✕</button>
    <h2 id="booking-title">{{ t.booking.title }}</h2>
    <p class="text-muted">{{ t.booking.description }}</p>
    <form data-booking-form
          data-message-template="{{ t.whatsapp.bookingMessageTemplate }}"
          data-service-clause="{{ t.whatsapp.serviceClauseTemplate }}"
          data-doctor-clause="{{ t.whatsapp.doctorClauseTemplate }}"
          data-message-clause="{{ t.whatsapp.messageClauseTemplate }}">
      <div class="form-field">
        <label for="booking-name">{{ t.booking.name }}</label>
        <input type="text" id="booking-name" name="name" autocomplete="name" required>
      </div>
      <div class="form-field">
        <label for="booking-phone">{{ t.booking.phone }}</label>
        <input type="tel" id="booking-phone" name="phone" autocomplete="tel" inputmode="tel" required>
      </div>
      <div class="form-field">
        <label for="booking-service">{{ t.booking.service }}</label>
        <select id="booking-service" name="service">
          <option value="">{{ t.booking.servicePlaceholder }}</option>
          {% for s in all_services %}
          <option value="{{ s.title }}">{{ s.title }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="form-field">
        <label for="booking-contact">{{ t.booking.contactMethod }}</label>
        <select id="booking-contact" name="contactMethod">
          <option value="{{ t.booking.contactMethodOptions[0] }}">{{ t.booking.contactMethodOptions[0] }}</option>
          <option value="{{ t.booking.contactMethodOptions[1] }}">{{ t.booking.contactMethodOptions[1] }}</option>
        </select>
      </div>
      <div class="form-field">
        <label for="booking-message">{{ t.booking.message }}</label>
        <textarea id="booking-message" name="message"></textarea>
      </div>
      <button type="submit" class="btn btn-whatsapp btn-block">{{ t.booking.submit }}</button>
      <p class="form-note">{{ t.booking.note }}</p>
    </form>
  </div>
</div>

```

### FILE: `templates/partials/bottom_bar.html`

```html
<div class="mobile-bottom-bar">
  <a href="{{ site.contact.phoneUri }}">
    <svg class="bar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
    <span>{{ t.mobileBar.call }}</span>
  </a>
  <a href="{{ wa_url(whatsapp_default_message) }}" target="_blank" rel="noopener">
    <svg class="bar-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.29-1.39a9.9 9.9 0 0 0 4.75 1.21h.01c5.46 0 9.9-4.45 9.9-9.91C21.96 6.45 17.5 2 12.04 2zm5.8 14.16c-.24.68-1.4 1.3-1.93 1.38-.5.08-1.11.11-1.79-.11a15.3 15.3 0 0 1-1.6-.58 12.4 12.4 0 0 1-4.5-3.97c-.66-.88-1.1-1.85-1.24-2.9-.08-.62.02-1.14.34-1.6.12-.18.5-.58.86-.58h.6c.19 0 .32.01.46.35.16.4.55 1.4.6 1.5.05.1.08.22.02.36-.06.14-.1.22-.2.34l-.3.35c-.1.1-.2.21-.09.41.11.2.5.9 1.1 1.46.75.7 1.4.98 1.6 1.09.2.11.32.09.44-.03l.62-.68c.16-.17.29-.15.48-.08.19.07 1.2.6 1.4.71.2.11.34.16.39.25.05.1.05.55-.19 1.23z"/></svg>
    <span>{{ t.mobileBar.whatsapp }}</span>
  </a>
  <button type="button" class="book-btn" data-open-booking>
    <svg class="bar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="18" rx="3"/><path d="M3 10h18M8 2v4M16 2v4"/></svg>
    <span>{{ t.mobileBar.book }}</span>
  </button>
</div>

```

### FILE: `templates/partials/whatsapp_float.html`

```html
<a class="whatsapp-float" href="{{ wa_url(whatsapp_default_message) }}" target="_blank" rel="noopener" aria-label="{{ t.common.whatsapp }}">
  <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26"><path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.29-1.39a9.9 9.9 0 0 0 4.75 1.21h.01c5.46 0 9.9-4.45 9.9-9.91C21.96 6.45 17.5 2 12.04 2zm5.8 14.16c-.24.68-1.4 1.3-1.93 1.38-.5.08-1.11.11-1.79-.11a15.3 15.3 0 0 1-1.6-.58 12.4 12.4 0 0 1-4.5-3.97c-.66-.88-1.1-1.85-1.24-2.9-.08-.62.02-1.14.34-1.6.12-.18.5-.58.86-.58h.6c.19 0 .32.01.46.35.16.4.55 1.4.6 1.5.05.1.08.22.02.36-.06.14-.1.22-.2.34l-.3.35c-.1.1-.2.21-.09.41.11.2.5.9 1.1 1.46.75.7 1.4.98 1.6 1.09.2.11.32.09.44-.03l.62-.68c.16-.17.29-.15.48-.08.19.07 1.2.6 1.4.71.2.11.34.16.39.25.05.1.05.55-.19 1.23z"/></svg>
</a>

```

### FILE: `templates/partials/home/hero.html`

```html
<section class="hero">
  <div class="container hero-grid">
    <div class="hero-copy reveal" data-reveal-group="hero">
      <span class="eyebrow">{{ t.hero.eyebrow }}</span>
      <h1>{{ t.hero.headline }}</h1>
      <p class="body-lg">{{ t.hero.description }}</p>
      <div class="hero-actions">
        <button type="button" class="btn btn-primary" data-open-booking>{{ t.hero.ctaPrimary }}</button>
        <a class="btn btn-whatsapp" href="{{ wa_url(whatsapp_default_message) }}" target="_blank" rel="noopener">{{ t.hero.ctaSecondary }}</a>
      </div>
      <div class="hero-chips">
        {% for chip in t.hero.trustChips %}
        <span class="chip">{{ chip }}</span>
        {% endfor %}
      </div>
    </div>
    <div class="hero-media reveal" data-reveal-group="hero">
      <img class="photo" src="/images/hero/doctor-hero.jpg" alt="{{ site.brand.clinicName }}" width="960" height="720" loading="eager" fetchpriority="high">
    </div>
  </div>
</section>

```

### FILE: `templates/partials/home/trust.html`

```html
<section>
  <div class="container">
    <h2 class="reveal" style="text-align:center; margin-bottom: 40px;">{{ t.trust.title }}</h2>
    <div class="trust-grid">
      {% for item in site.trustItems %}
      <div class="trust-item reveal" data-reveal-group="trust">
        <h3>{{ t.trust['items'][item.key].title }}</h3>
        <p>{{ t.trust['items'][item.key].desc }}</p>
      </div>
      {% endfor %}
    </div>
    <div class="stats-row">
      {% for stat in site.stats %}
      <div class="stats-item reveal" data-reveal-group="stats">
        <span class="stats-value">{{ stat.value }}</span>
        <span class="stats-label">{{ t.trust.stats[stat.key] }}</span>
      </div>
      {% endfor %}
    </div>
  </div>
</section>

```

### FILE: `templates/partials/home/services.html`

```html
<section class="section-alt">
  <div class="container">
    <div class="section-head reveal">
      <span class="eyebrow">{{ t.services.eyebrow }}</span>
      <h2>{{ t.services.title }}</h2>
      <p class="body-lg">{{ t.services.description }}</p>
    </div>
    <div class="card-grid cols-3">
      {% for s in services_home %}
      <a class="service-card reveal" data-reveal-group="services" href="{{ s.href }}">
        <div class="service-card-media">
          <img class="photo" src="{{ s.cardImage }}" alt="{{ s.title }}" width="480" height="360" loading="lazy">
        </div>
        <div class="service-card-body">
          <h3>{{ s.title }}</h3>
          <p>{{ s.shortCopy }}</p>
          <span class="link-arrow">{{ t.common.learnMore }} <span class="arrow">→</span></span>
        </div>
      </a>
      {% endfor %}
    </div>
    <div style="text-align:center; margin-top: 40px;">
      <a class="btn btn-outline" href="{{ lang_prefix }}/services/">{{ t.services.ctaViewAll }}</a>
    </div>
  </div>
</section>

```

### FILE: `templates/partials/home/technology.html`

```html
<section>
  <div class="container">
    <div class="section-head reveal">
      <span class="eyebrow">{{ t.technology.eyebrow }}</span>
      <h2>{{ t.technology.title }}</h2>
      <p class="body-lg">{{ t.technology.description }}</p>
    </div>
    <div class="card-grid cols-3">
      {% for tech in technologies %}
      <div class="tech-card reveal" data-reveal-group="tech">
        <div class="tech-card-media">
          <img class="photo" src="{{ tech.image }}" alt="{{ tech.name }}" width="400" height="250" loading="lazy">
        </div>
        <h3>{{ tech.name }}</h3>
        <p class="explain">{{ tech.shortExplain }}</p>
        <p class="benefit">{{ tech.patientBenefit }}</p>
      </div>
      {% endfor %}
    </div>
  </div>
</section>

```

### FILE: `templates/partials/home/doctorSpotlight.html`

```html
<section class="section-alt">
  <div class="container two-col">
    <div class="reveal" data-reveal-group="spotlight">
      <div class="hero-media" style="aspect-ratio: 4/5;">
        <img class="photo" src="{{ doctor_spotlight.workingPhoto }}" alt="{{ doctor_spotlight.name }}" width="480" height="600" loading="lazy">
      </div>
    </div>
    <div class="reveal" data-reveal-group="spotlight">
      <span class="eyebrow">{{ t.doctorSpotlight.eyebrow }}</span>
      <h2>{{ t.doctorSpotlight.title }}</h2>
      <p class="body-lg">{{ t.doctorSpotlight.description }}</p>
      <p style="font-family:var(--font-heading); font-size:1.1875rem; margin-top:20px;">“{{ doctor_spotlight.quote }}”</p>
      <p class="text-muted">{{ doctor_spotlight.name }} — {{ doctor_spotlight.role }}</p>
      <a class="btn btn-outline" href="{{ lang_prefix }}/doctors/" style="margin-top:12px;">{{ t.doctorSpotlight.ctaMeetTeam }}</a>
    </div>
  </div>
</section>

```

### FILE: `templates/partials/home/patientExperience.html`

```html
<section>
  <div class="container">
    <div class="section-head centered reveal">
      <span class="eyebrow">{{ t.patientExperience.eyebrow }}</span>
      <h2>{{ t.patientExperience.title }}</h2>
      <p class="body-lg">{{ t.patientExperience.description }}</p>
    </div>
    <div class="experience-list">
      {% for key in ['arrival','consultation','diagnostics','treatment','followUp'] %}
      <div class="experience-step reveal" data-reveal-group="experience">
        <h3>{{ t.patientExperience.steps[key].title }}</h3>
        <p>{{ t.patientExperience.steps[key].desc }}</p>
      </div>
      {% endfor %}
    </div>
  </div>
</section>

```

### FILE: `templates/partials/home/team.html`

```html
<section class="section-alt">
  <div class="container">
    <div class="section-head reveal">
      <span class="eyebrow">{{ t.team.eyebrow }}</span>
      <h2>{{ t.team.title }}</h2>
      <p class="body-lg">{{ t.team.description }}</p>
    </div>
    <div class="card-grid cols-3">
      {% for d in doctors_home %}
      <a class="doctor-card reveal" data-reveal-group="team" href="{{ d.href }}">
        <div class="doctor-card-media">
          <img class="photo" src="{{ d.photo }}" alt="{{ d.name }}" width="360" height="480" loading="lazy">
        </div>
        <h3>{{ d.name }}</h3>
        <p class="role">{{ d.role }}</p>
        {% if d.experienceYears %}<p class="spec">{{ d.experienceYears }} {{ t.doctorDetail.experienceSuffix }}</p>{% endif %}
      </a>
      {% endfor %}
    </div>
    <div style="text-align:center; margin-top: 40px;">
      <a class="btn btn-outline" href="{{ lang_prefix }}/doctors/">{{ t.doctorSpotlight.ctaMeetTeam }}</a>
    </div>
  </div>
</section>

```

### FILE: `templates/partials/home/reviews.html`

```html
<section>
  <div class="container">
    <div class="section-head centered reveal">
      <span class="eyebrow">{{ t.reviews.eyebrow }}</span>
      <h2>{{ t.reviews.title }}</h2>
      <p class="body-lg">{{ t.reviews.description }}</p>
      <p class="rating-line"><strong>★ {{ rating.value }}</strong> · {{ t.reviews.ratingLabel }} ({{ rating.count }})</p>
    </div>
    <div class="card-grid cols-3">
      {% for r in reviews %}
      <div class="review-card reveal" data-reveal-group="reviews">
        <p class="quote">“{{ r.quote }}”</p>
        <p class="author">{{ r.authorInitial }}{% if r.serviceTitle %} — {{ r.serviceTitle }}{% endif %}</p>
      </div>
      {% endfor %}
    </div>
    <div style="text-align:center; margin-top: 40px;">
      <a class="btn btn-outline" href="{{ lang_prefix }}/reviews/">{{ t.common.viewAll }}</a>
    </div>
  </div>
</section>

```

### FILE: `templates/partials/home/finalCTA.html`

```html
<section>
  <div class="container">
    <div class="final-cta reveal">
      <div class="final-cta-grid">
        <div>
          <span class="eyebrow" style="color: var(--color-accent);">{{ t.finalCTA.eyebrow }}</span>
          <h2>{{ t.finalCTA.title }}</h2>
          <p>{{ t.finalCTA.description }}</p>
          <div class="final-cta-actions">
            <button type="button" class="btn btn-primary" style="background: var(--color-accent); color: var(--color-text);" data-open-booking>{{ t.hero.ctaPrimary }}</button>
            <a class="btn btn-outline" href="{{ site.contact.phoneUri }}">{{ site.contact.phone }}</a>
            <a class="btn btn-whatsapp" href="{{ wa_url(whatsapp_default_message) }}" target="_blank" rel="noopener">{{ t.common.whatsapp }}</a>
          </div>
        </div>
        <div class="final-cta-media">
          <img class="photo" src="/images/cta/final-cta.jpg" alt="{{ site.brand.clinicName }}" width="480" height="360" loading="lazy">
        </div>
      </div>
    </div>
  </div>
</section>

```

### FILE: `templates/pages/home.html`

```html
{% extends "base.html" %}
{% block content %}
{% for section in site.homepageSections %}
  {% include "partials/home/" + section + ".html" %}
{% endfor %}
{% endblock %}

```

### FILE: `templates/pages/services.html`

```html
{% extends "base.html" %}
{% block content %}
<section class="page-header">
  <div class="container">
    {% include "partials/breadcrumb.html" %}
    <span class="eyebrow">{{ t.servicesPage.eyebrow }}</span>
    <h1>{{ t.servicesPage.title }}</h1>
    <p class="body-lg">{{ t.servicesPage.description }}</p>
  </div>
</section>
<section style="padding-top:0;">
  <div class="container">
    <div class="card-grid cols-3">
      {% for s in services %}
      <a class="service-card reveal" data-reveal-group="services" href="{{ s.href }}">
        <div class="service-card-media">
          <img class="photo" src="{{ s.cardImage }}" alt="{{ s.title }}" width="480" height="360" loading="lazy">
        </div>
        <div class="service-card-body">
          <h3>{{ s.title }}</h3>
          <p>{{ s.shortCopy }}</p>
          <span class="link-arrow">{{ t.common.learnMore }} <span class="arrow">→</span></span>
        </div>
      </a>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}

```

### FILE: `templates/pages/service_detail.html`

```html
{% extends "base.html" %}
{% block content %}
<section class="page-header">
  <div class="container">
    {% include "partials/breadcrumb.html" %}
    <span class="eyebrow">{{ service.eyebrow }}</span>
    <h1>{{ service.title }}</h1>
    <p class="body-lg">{{ service.intro }}</p>
    <div class="hero-actions">
      <button type="button" class="btn btn-primary" data-open-booking data-service="{{ service.title }}">{{ t.hero.ctaPrimary }}</button>
      <a class="btn btn-whatsapp" href="{{ wa_url(t.whatsapp.serviceMessageTemplate.replace('{service}', service.title)) }}" target="_blank" rel="noopener">{{ t.hero.ctaSecondary }}</a>
    </div>
  </div>
</section>

<section style="padding-top:0;">
  <div class="container">
    <div class="hero-media reveal" style="aspect-ratio:21/9;">
      <img class="photo" src="{{ service.heroImage }}" alt="{{ service.title }}" width="1200" height="500" loading="lazy">
    </div>
  </div>
</section>

<section>
  <div class="container two-col">
    <div class="reveal">
      <h2>{{ t.serviceDetail.aboutTitle }}</h2>
      <p class="body-lg">{{ service.aboutTreatment }}</p>
    </div>
    <div class="reveal">
      <h2>{{ t.serviceDetail.whoTitle }}</h2>
      <ul style="display:flex; flex-direction:column; gap:12px;">
        {% for item in service.whoItIsFor %}
        <li style="padding-left:20px; position:relative;">
          <span style="position:absolute; left:0; color:var(--color-accent);">—</span>{{ item }}
        </li>
        {% endfor %}
      </ul>
    </div>
  </div>
</section>

<section class="section-alt">
  <div class="container">
    <h2 class="reveal">{{ t.serviceDetail.benefitsTitle }}</h2>
    <div class="card-grid cols-3">
      {% for b in service.benefits %}
      <div class="trust-item reveal" data-reveal-group="benefits"><p style="margin:0;">{{ b }}</p></div>
      {% endfor %}
    </div>
  </div>
</section>

<section>
  <div class="container">
    <h2 class="reveal">{{ t.serviceDetail.processTitle }}</h2>
    <div class="process-list">
      {% for step in process_steps %}
      <div class="process-step reveal" data-reveal-group="process">
        <span class="step-num">{{ step.step }}</span>
        <h3>{{ step.title }}</h3>
        <p>{{ step.desc }}</p>
      </div>
      {% endfor %}
    </div>
  </div>
</section>

{% if service.technologies %}
<section class="section-alt">
  <div class="container">
    <h2 class="reveal">{{ t.serviceDetail.technologyTitle }}</h2>
    <div class="card-grid cols-3">
      {% for tech in service.technologies %}
      <div class="tech-card reveal" data-reveal-group="tech">
        <div class="tech-card-media"><img class="photo" src="{{ tech.image }}" alt="{{ tech.name }}" width="400" height="250" loading="lazy"></div>
        <h3>{{ tech.name }}</h3>
        <p class="explain">{{ tech.shortExplain }}</p>
      </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endif %}

{% if service.doctor %}
<section>
  <div class="container two-col">
    <div class="reveal">
      <div class="hero-media" style="aspect-ratio:4/5;">
        <img class="photo" src="{{ service.doctor.photo }}" alt="{{ service.doctor.name }}" width="480" height="600" loading="lazy">
      </div>
    </div>
    <div class="reveal">
      <h2>{{ t.serviceDetail.doctorTitle }}</h2>
      <h3 style="margin-top:0;">{{ service.doctor.name }}</h3>
      <p class="text-muted">{{ service.doctor.role }}</p>
      <a class="btn btn-outline" href="{{ service.doctor.href }}">{{ t.common.learnMore }}</a>
    </div>
  </div>
</section>
{% endif %}

<section class="section-alt">
  <div class="container" style="max-width: 640px;">
    <h2 class="reveal">{{ t.serviceDetail.pricingTitle }}</h2>
    <div class="pricing-row reveal">
      <span>{{ service.title }}</span>
      <strong>{{ service.priceDisplay }}</strong>
    </div>
    <p class="text-muted" style="font-size:0.875rem; margin-top:10px;">{{ service.priceNote }}</p>
  </div>
</section>

{% if service.faq %}
<section>
  <div class="container" style="max-width: 780px;">
    <h2 class="reveal">{{ t.serviceDetail.faqTitle }}</h2>
    <div>
      {% for item in service.faq %}
      <div class="faq-item reveal">
        <button type="button" class="faq-question"><span>{{ item.q }}</span><span class="plus">+</span></button>
        <div class="faq-answer"><div class="faq-answer-inner">{{ item.a }}</div></div>
      </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endif %}

{% if service.related %}
<section class="section-alt">
  <div class="container">
    <h2 class="reveal">{{ t.serviceDetail.relatedTitle }}</h2>
    <div class="related-strip">
      {% for r in service.related %}
      <a class="service-card reveal" href="{{ r.href }}">
        <div class="service-card-media"><img class="photo" src="{{ r.cardImage }}" alt="{{ r.title }}" width="320" height="240" loading="lazy"></div>
        <div class="service-card-body">
          <h3>{{ r.title }}</h3>
          <p>{{ r.shortCopy }}</p>
        </div>
      </a>
      {% endfor %}
    </div>
  </div>
</section>
{% endif %}

<section>
  <div class="container">
    <div class="final-cta reveal">
      <div class="final-cta-grid" style="grid-template-columns: 1fr;">
        <div>
          <h2>{{ t.serviceDetail.ctaTitle }}</h2>
          <p>{{ t.serviceDetail.ctaDescription }}</p>
          <div class="final-cta-actions">
            <button type="button" class="btn btn-primary" style="background: var(--color-accent); color: var(--color-text);" data-open-booking data-service="{{ service.title }}">{{ t.hero.ctaPrimary }}</button>
            <a class="btn btn-outline" href="{{ site.contact.phoneUri }}">{{ site.contact.phone }}</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
{% endblock %}

```

### FILE: `templates/pages/doctors.html`

```html
{% extends "base.html" %}
{% block content %}
<section class="page-header">
  <div class="container">
    {% include "partials/breadcrumb.html" %}
    <span class="eyebrow">{{ t.doctorsPage.eyebrow }}</span>
    <h1>{{ t.doctorsPage.title }}</h1>
    <p class="body-lg">{{ t.doctorsPage.description }}</p>
  </div>
</section>
<section style="padding-top:0;">
  <div class="container">
    <div class="card-grid cols-3">
      {% for d in doctors %}
      <a class="doctor-card reveal" data-reveal-group="doctors" href="{{ d.href }}">
        <div class="doctor-card-media">
          <img class="photo" src="{{ d.photo }}" alt="{{ d.name }}" width="360" height="480" loading="lazy">
        </div>
        <h3>{{ d.name }}</h3>
        <p class="role">{{ d.role }}</p>
        {% if d.experienceYears %}<p class="spec">{{ d.experienceYears }} {{ t.doctorDetail.experienceSuffix }}</p>{% endif %}
      </a>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}

```

### FILE: `templates/pages/doctor_detail.html`

```html
{% extends "base.html" %}
{% block content %}
<section class="page-header">
  <div class="container">
    {% include "partials/breadcrumb.html" %}
  </div>
</section>
<section style="padding-top:0;">
  <div class="container two-col">
    <div class="reveal">
      <div class="hero-media" style="aspect-ratio:3/4;">
        <img class="photo" src="{{ doctor.photo }}" alt="{{ doctor.name }}" width="480" height="640" loading="eager">
      </div>
    </div>
    <div class="reveal">
      <h1>{{ doctor.name }}</h1>
      <p class="eyebrow" style="margin-top:0;">{{ doctor.role }}{% if doctor.experienceYears %} · {{ doctor.experienceYears }} {{ t.doctorDetail.experienceSuffix }} {{ t.doctorDetail.experienceLabel | lower }}{% endif %}</p>
      <p class="body-lg">{{ doctor.bio }}</p>
      <p style="font-family:var(--font-heading); font-size:1.0625rem;">“{{ doctor.quote }}”</p>

      <h3>{{ t.doctorDetail.languagesTitle }}</h3>
      <div class="hero-chips" style="margin-top:0;">
        {% for l in doctor.languages %}<span class="chip">{{ l | upper }}</span>{% endfor %}
      </div>

      {% if doctor.education %}
      <h3 style="margin-top:28px;">{{ t.doctorDetail.educationTitle }}</h3>
      <ul style="display:flex; flex-direction:column; gap:6px;">
        {% for item in doctor.education %}
        <li style="padding-left:20px; position:relative; font-size:0.9375rem; color:var(--color-text-muted);"><span style="position:absolute; left:0; color:var(--color-accent);">—</span>{{ item }}</li>
        {% endfor %}
      </ul>
      {% endif %}

      {% if doctor.certifications %}
      <h3 style="margin-top:24px;">{{ t.doctorDetail.certificationsTitle }}</h3>
      <ul style="display:flex; flex-direction:column; gap:6px;">
        {% for cert in doctor.certifications %}
        <li style="padding-left:20px; position:relative; font-size:0.9375rem; color:var(--color-text-muted);">
          <span style="position:absolute; left:0; color:var(--color-accent);">—</span>{{ cert.label }} <span class="text-muted" style="font-size:0.8125rem;">· {{ cert.id }}</span>
        </li>
        {% endfor %}
      </ul>
      {% endif %}

      {% if doctor.services %}
      <h3 style="margin-top:28px;">{{ t.doctorDetail.servicesTitle }}</h3>
      <ul style="display:flex; flex-direction:column; gap:8px;">
        {% for s in doctor.services %}
        <li><a class="link-arrow" href="{{ s.href }}">{{ s.title }} <span class="arrow">→</span></a></li>
        {% endfor %}
      </ul>
      {% endif %}

      <div class="hero-actions">
        <button type="button" class="btn btn-primary" data-open-booking data-doctor="{{ doctor.name }}">{{ t.doctorDetail.ctaTitle }}</button>
        <a class="btn btn-whatsapp" href="{{ wa_url(t.whatsapp.doctorMessageTemplate.replace('{doctor}', doctor.name)) }}" target="_blank" rel="noopener">{{ t.common.whatsapp }}</a>
      </div>
      <p class="text-muted" style="font-size:0.875rem;">{{ t.doctorDetail.ctaDescription }}</p>
    </div>
  </div>
</section>
{% endblock %}

```

### FILE: `templates/pages/technology.html`

```html
{% extends "base.html" %}
{% block content %}
<section class="page-header">
  <div class="container">
    {% include "partials/breadcrumb.html" %}
    <span class="eyebrow">{{ t.technologyPage.eyebrow }}</span>
    <h1>{{ t.technologyPage.title }}</h1>
    <p class="body-lg">{{ t.technologyPage.description }}</p>
  </div>
</section>
<section style="padding-top:0;">
  <div class="container">
    <div class="card-grid cols-3">
      {% for tech in technologies %}
      <div class="tech-card reveal" data-reveal-group="tech">
        <div class="tech-card-media">
          <img class="photo" src="{{ tech.image }}" alt="{{ tech.name }}" width="400" height="250" loading="lazy">
        </div>
        <h3>{{ tech.name }}</h3>
        <p class="explain">{{ tech.shortExplain }}</p>
        <p class="benefit">{{ tech.patientBenefit }}</p>
      </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}

```

### FILE: `templates/pages/about.html`

```html
{% extends "base.html" %}
{% block content %}
<section class="page-header">
  <div class="container">
    {% include "partials/breadcrumb.html" %}
    <span class="eyebrow">{{ t.aboutPage.eyebrow }} · {{ site.brand.foundedYear }}</span>
    <h1>{{ t.aboutPage.title }}</h1>
    <div class="stats-row" style="border-top:none; padding-top:0; margin-top:32px;">
      {% for stat in site.stats %}
      <div class="stats-item reveal" data-reveal-group="about-stats">
        <span class="stats-value">{{ stat.value }}</span>
        <span class="stats-label">{{ t.trust.stats[stat.key] }}</span>
      </div>
      {% endfor %}
    </div>
  </div>
</section>

<section style="padding-top:0; padding-bottom: 0;">
  <div class="container" style="text-align:center;">
    <img src="{{ site.brand.logo.full }}" alt="{{ site.brand.clinicName }} — {{ site.brand.tagline[lang] }}"
         style="max-width: 420px; width: 100%; border-radius: var(--radius-lg); margin-inline:auto;" loading="lazy">
  </div>
</section>

{% for key in ['philosophy','patientApproach','digitalDentistry','team','clinicEnvironment','technology','patientExperience'] %}
<section class="about-section">
  <div class="container" style="max-width: 780px;">
    <h2 class="reveal">{{ t.aboutPage.sections[key].title }}</h2>
    <p class="body-lg reveal">{{ t.aboutPage.sections[key].body }}</p>
  </div>
  {% if key == 'team' %}
  <div class="container" style="max-width: 960px; margin-top: 32px;">
    <div class="hero-media reveal" style="aspect-ratio:16/9;">
      <img class="photo" src="/images/clinic/team.jpg" alt="{{ site.brand.clinicName }} team" width="960" height="540" loading="lazy">
    </div>
  </div>
  {% elif key == 'clinicEnvironment' %}
  <div class="container" style="max-width: 960px; margin-top: 32px;">
    <div class="hero-media reveal" style="aspect-ratio:16/9;">
      <img class="photo" src="/images/clinic/reception.jpg" alt="{{ site.brand.clinicName }} reception" width="960" height="540" loading="lazy">
    </div>
  </div>
  {% endif %}
</section>
{% endfor %}

<section class="section-alt">
  <div class="container" style="max-width: 780px; text-align:center;">
    <h2 class="reveal">{{ t.aboutPage.sections.cta.title }}</h2>
    <p class="body-lg reveal">{{ t.aboutPage.sections.cta.body }}</p>
    <div class="hero-actions" style="justify-content:center;">
      <button type="button" class="btn btn-primary" data-open-booking>{{ t.hero.ctaPrimary }}</button>
      <a class="btn btn-whatsapp" href="{{ wa_url(whatsapp_default_message) }}" target="_blank" rel="noopener">{{ t.hero.ctaSecondary }}</a>
    </div>
  </div>
</section>
{% endblock %}

```

### FILE: `templates/pages/reviews.html`

```html
{% extends "base.html" %}
{% block content %}
<section class="page-header">
  <div class="container">
    {% include "partials/breadcrumb.html" %}
    <span class="eyebrow">{{ t.reviewsPage.eyebrow }}</span>
    <h1>{{ t.reviewsPage.title }}</h1>
    <p class="body-lg">{{ t.reviewsPage.description }}</p>
    <p class="rating-line"><strong>★ {{ rating.value }}</strong> · {{ t.reviews.ratingLabel }} ({{ rating.count }})</p>
  </div>
</section>
<section style="padding-top:0;">
  <div class="container">
    <div class="card-grid cols-3">
      {% for r in reviews %}
      <div class="review-card reveal" data-reveal-group="reviews">
        <p class="quote">“{{ r.quote }}”</p>
        <p class="author">{{ r.authorInitial }}{% if r.serviceTitle %} — {{ r.serviceTitle }}{% endif %}</p>
      </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}

```

### FILE: `templates/pages/contact.html`

```html
{% extends "base.html" %}
{% block content %}
<section class="page-header">
  <div class="container">
    {% include "partials/breadcrumb.html" %}
    <span class="eyebrow">{{ t.contactPage.eyebrow }}</span>
    <h1>{{ t.contactPage.title }}</h1>
    <p class="body-lg">{{ t.contactPage.description }}</p>
  </div>
</section>
<section style="padding-top:0;">
  <div class="container contact-grid">
    <div class="reveal">
      <div class="contact-detail">
        <span class="text-muted">{{ t.contactPage.phoneLabel }}</span>
        <a class="link-arrow" href="{{ site.contact.phoneUri }}">{{ site.contact.phone }}</a>
      </div>
      <div class="contact-detail">
        <span class="text-muted">{{ t.contactPage.whatsappLabel }}</span>
        <a class="link-arrow" href="{{ wa_url(whatsapp_default_message) }}" target="_blank" rel="noopener">{{ site.contact.whatsapp }}</a>
      </div>
      <div class="contact-detail">
        <span class="text-muted">{{ t.contactPage.emailLabel }}</span>
        <span>{{ site.contact.email }}</span>
      </div>
      <div class="contact-detail">
        <span class="text-muted">{{ t.contactPage.hoursLabel }}</span>
        <span>
          {{ t.contactPage.hoursWeekday }} {{ t.contactPage.hoursWeekdayTime }}<br>
          {{ t.contactPage.hoursSaturday }} {{ t.contactPage.hoursSaturdayTime }}<br>
          {{ t.contactPage.hoursSunday }} — {{ t.contactPage.hoursSundayTime }}
        </span>
      </div>
      <div class="contact-detail">
        <span class="text-muted">{{ t.contactPage.addressLabel }}</span>
        <span>{{ site.contact.address[lang] }}</span>
      </div>
      <div style="margin-top:32px;">
        <button type="button" class="btn btn-primary" data-open-booking>{{ t.nav.bookConsultation }}</button>
      </div>
    </div>
    <div class="reveal">
      <div class="map-card">
        <div class="map-card-body">
          <span class="eyebrow">{{ t.contactPage.addressLabel }}</span>
          <p>{{ site.contact.address[lang] }}</p>
          <a class="link-arrow" href="https://www.google.com/maps/search/?api=1&amp;query={{ site.contact.address.en | urlencode }}" target="_blank" rel="noopener">{{ t.contactPage.directionsCta }} <span class="arrow">→</span></a>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="section-alt">
  <div class="container two-col">
    <div class="reveal">
      <h2>{{ t.contactPage.paymentTitle }}</h2>
      <ul style="display:flex; flex-direction:column; gap:10px;">
        {% for item in t.contactPage.paymentOptions %}
        <li style="padding-left:20px; position:relative;"><span style="position:absolute; left:0; color:var(--color-accent);">—</span>{{ item }}</li>
        {% endfor %}
      </ul>
    </div>
    <div class="reveal">
      <h2>{{ t.contactPage.safetyTitle }}</h2>
      <ul style="display:flex; flex-direction:column; gap:10px;">
        {% for item in t.contactPage.safetyItems %}
        <li style="padding-left:20px; position:relative;"><span style="position:absolute; left:0; color:var(--color-accent);">—</span>{{ item }}</li>
        {% endfor %}
      </ul>
    </div>
  </div>
</section>

<section>
  <div class="container" style="max-width: 780px;">
    <h2 class="reveal">{{ t.contactPage.generalFaqTitle }}</h2>
    <div>
      {% for item in t.contactPage.generalFaq %}
      <div class="faq-item reveal">
        <button type="button" class="faq-question"><span>{{ item.q }}</span><span class="plus">+</span></button>
        <div class="faq-answer"><div class="faq-answer-inner">{{ item.a }}</div></div>
      </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}

```

### FILE: `templates/pages/404.html`

```html
{% extends "base.html" %}
{% block content %}
<section class="page-header">
  <div class="container" style="text-align:center;">
    <h1>{{ t.notFound.title }}</h1>
    <p class="body-lg">{{ t.notFound.description }}</p>
    <a class="btn btn-primary" href="{{ home_url }}">{{ t.notFound.cta }}</a>
  </div>
</section>
{% endblock %}

```

### FILE: `static/css/tokens.css`

```css
:root {
  /* Color */
  --color-bg: #FAF7F1;
  --color-surface: #FFFFFF;
  --color-surface-alt: #F1EBE0;
  --color-text: #221F1A;
  --color-text-muted: #6B6459;
  --color-border: #E4DBCB;
  --color-primary: #221F1A;
  --color-primary-contrast: #FAF7F1;
  --color-accent: #B8925A;
  --color-accent-strong: #9C7745;
  --color-accent-soft: #EFE3CF;
  --color-whatsapp: #3F7A5C;
  --color-whatsapp-contrast: #FFFFFF;

  /* Typography */
  --font-heading: 'Noto Serif', 'Noto Serif Armenian', 'Noto Sans Armenian', serif;
  --font-body: 'Noto Sans', 'Noto Sans Armenian', sans-serif;

  --fs-display: clamp(2.25rem, 1.5rem + 3vw, 3.5rem);
  --fs-h1: clamp(2rem, 1.4rem + 2.2vw, 2.75rem);
  --fs-h2: clamp(1.6rem, 1.3rem + 1.4vw, 2.125rem);
  --fs-h3: clamp(1.25rem, 1.1rem + 0.6vw, 1.5rem);
  --fs-body-lg: 1.1875rem;
  --fs-body: 1rem;
  --fs-caption: 0.8125rem;
  --fs-eyebrow: 0.8125rem;
  --fs-button: 0.9375rem;

  /* Spacing */
  --space-unit: 8px;
  --section-spacing: clamp(64px, 8vw, 128px);
  --container-width: 1360px;
  --container-gutter: clamp(20px, 5vw, 64px);

  /* Radii */
  --radius-sm: 6px;
  --radius-md: 14px;
  --radius-lg: 28px;
  --radius-pill: 999px;

  /* Shadow */
  --shadow-card: 0 12px 32px -16px rgba(34, 31, 26, 0.18);
  --shadow-modal: 0 24px 64px -24px rgba(34, 31, 26, 0.35);

  /* Motion */
  --transition-fast: 180ms cubic-bezier(.2,.7,.2,1);
  --transition-medium: 320ms cubic-bezier(.2,.7,.2,1);
  --transition-slow: 600ms cubic-bezier(.2,.7,.2,1);
  --reveal-stagger: 80ms;

  /* Z-index */
  --z-header: 100;
  --z-drawer: 200;
  --z-modal: 300;
  --z-splash: 400;
  --z-bottom-bar: 90;
}

```

### FILE: `static/css/main.css`

```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif:ital,wght@0,400;0,600;0,700;1,400&family=Noto+Serif+Armenian:wght@400;600;700&family=Noto+Sans:wght@400;500;600;700&family=Noto+Sans+Armenian:wght@400;500;600;700&display=swap');

/* ---------- Reset ---------- */
*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
body {
  margin: 0;
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-body);
  font-size: var(--fs-body);
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
  overflow-x: hidden;
}
img { max-width: 100%; display: block; }
a { color: inherit; text-decoration: none; }
button { font: inherit; cursor: pointer; }
ul { margin: 0; padding: 0; list-style: none; }
h1, h2, h3, h4 { font-family: var(--font-heading); margin: 0 0 0.5em; line-height: 1.15; font-weight: 600; }
p { margin: 0 0 1em; }
.container {
  width: 100%;
  max-width: var(--container-width);
  margin-inline: auto;
  padding-inline: var(--container-gutter);
}
section { padding-block: var(--section-spacing); }
.section-alt { background: var(--color-surface-alt); }
:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 3px; }

/* ---------- Typography helpers ---------- */
.eyebrow {
  display: inline-block;
  font-size: var(--fs-eyebrow);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-accent-strong);
  font-weight: 600;
  margin-bottom: 0.75em;
}
.text-muted { color: var(--color-text-muted); }
.body-lg { font-size: var(--fs-body-lg); color: var(--color-text-muted); }
.section-head { max-width: 640px; margin-bottom: clamp(32px, 5vw, 56px); }
.section-head.centered { margin-inline: auto; text-align: center; }
h1, .h1 { font-size: var(--fs-h1); }
h2, .h2 { font-size: var(--fs-h2); }
h3, .h3 { font-size: var(--fs-h3); }
.display { font-size: var(--fs-display); }

/* ---------- Buttons ---------- */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5em;
  padding: 16px 28px;
  border-radius: var(--radius-md);
  font-size: var(--fs-button);
  font-weight: 500;
  letter-spacing: 0.01em;
  border: 1px solid transparent;
  transition: background var(--transition-fast), color var(--transition-fast), border-color var(--transition-fast), transform var(--transition-fast);
  white-space: nowrap;
}
.btn:active { transform: translateY(1px); }
.btn-primary { background: var(--color-primary); color: var(--color-primary-contrast); }
.btn-primary:hover { background: var(--color-accent); color: var(--color-text); }
.btn-outline { background: transparent; color: var(--color-text); border-color: var(--color-border); }
.btn-outline:hover { border-color: var(--color-accent); color: var(--color-accent-strong); }
.btn-whatsapp { background: var(--color-whatsapp); color: var(--color-whatsapp-contrast); }
.btn-whatsapp:hover { background: #356848; }
.btn-sm { padding: 10px 18px; font-size: 0.875rem; }
.btn-block { width: 100%; justify-content: center; }
.link-arrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  color: var(--color-text);
}
.link-arrow .arrow { transition: transform var(--transition-fast); }
.link-arrow:hover .arrow { transform: translateX(4px); }
.link-arrow:hover { color: var(--color-accent-strong); }

/* ---------- Header ---------- */
.site-header {
  position: sticky;
  top: 0;
  z-index: var(--z-header);
  background: transparent;
  border-bottom: 1px solid transparent;
  transition: background var(--transition-medium), border-color var(--transition-medium), box-shadow var(--transition-medium);
}
.site-header.is-scrolled {
  background: rgba(250, 247, 241, 0.92);
  backdrop-filter: saturate(180%) blur(14px);
  -webkit-backdrop-filter: saturate(180%) blur(14px);
  border-bottom-color: var(--color-border);
}
.header-inner {
  display: flex;
  align-items: center;
  gap: 20px;
  min-height: 84px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--color-text);
  margin-right: auto;
}
.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-heading);
  font-weight: 700;
  color: var(--color-accent-strong);
  font-size: 0.9rem;
  flex-shrink: 0;
  object-fit: cover;
}
.brand-mark[data-logo-placeholder] { outline: 1px dashed var(--color-accent); outline-offset: 2px; }
.brand-logo-full { height: 40px; width: auto; flex-shrink: 0; }
.main-nav { display: none; min-width: 0; flex-shrink: 1; }
.main-nav ul { display: flex; gap: 11px; align-items: center; flex-wrap: nowrap; }
.main-nav a {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text);
  position: relative;
  padding-block: 4px;
  white-space: nowrap;
}
.main-nav a::after {
  content: '';
  position: absolute;
  left: 0; right: 0; bottom: -2px;
  height: 2px;
  background: var(--color-accent);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform var(--transition-fast);
}
.main-nav a:hover::after, .main-nav a.is-active::after { transform: scaleX(1); }
.header-actions { display: none; align-items: center; gap: 12px; flex-shrink: 0; }
.brand { flex-shrink: 0; }
.lang-switch { display: flex; gap: 6px; font-size: 0.8125rem; font-weight: 600; }
.lang-switch a {
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
}
.lang-switch a.is-active { color: var(--color-text); background: var(--color-accent-soft); }
.header-mobile-actions { display: flex; align-items: center; gap: 12px; margin-left: auto; }
.hamburger {
  width: 40px; height: 40px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; border: 1px solid var(--color-border); border-radius: var(--radius-sm);
}
.hamburger span { display: block; width: 18px; height: 2px; background: var(--color-text); position: relative; }
.hamburger span::before, .hamburger span::after {
  content: ''; position: absolute; left: 0; width: 18px; height: 2px; background: var(--color-text);
  transition: transform var(--transition-fast);
}
.hamburger span::before { top: -6px; }
.hamburger span::after { top: 6px; }

@media (min-width: 1360px) {
  .main-nav { display: block; }
  .header-actions { display: flex; }
  .header-mobile-actions { display: none; }
}

/* ---------- Mobile nav overlay ---------- */
.mobile-nav-overlay {
  position: fixed; inset: 0; z-index: var(--z-drawer);
  background: var(--color-bg);
  display: flex; flex-direction: column;
  padding: 24px var(--container-gutter) 40px;
  transform: translateY(-8px);
  opacity: 0;
  visibility: hidden;
  transition: opacity var(--transition-medium), transform var(--transition-medium), visibility var(--transition-medium);
}
.mobile-nav-overlay.is-open { opacity: 1; transform: translateY(0); visibility: visible; }
.mobile-nav-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
.mobile-nav-list { display: flex; flex-direction: column; gap: 4px; }
.mobile-nav-list a {
  display: block; padding: 16px 4px; font-family: var(--font-heading); font-size: 1.5rem;
  border-bottom: 1px solid var(--color-border);
  opacity: 0; transform: translateY(10px);
  transition: opacity var(--transition-medium), transform var(--transition-medium);
}
.mobile-nav-overlay.is-open .mobile-nav-list a { opacity: 1; transform: translateY(0); }
.mobile-nav-list a:nth-child(1) { transition-delay: 40ms; }
.mobile-nav-list a:nth-child(2) { transition-delay: 80ms; }
.mobile-nav-list a:nth-child(3) { transition-delay: 120ms; }
.mobile-nav-list a:nth-child(4) { transition-delay: 160ms; }
.mobile-nav-list a:nth-child(5) { transition-delay: 200ms; }
.mobile-nav-list a:nth-child(6) { transition-delay: 240ms; }
.mobile-nav-list a:nth-child(7) { transition-delay: 280ms; }
.mobile-nav-footer { margin-top: auto; padding-top: 32px; display: flex; flex-direction: column; gap: 16px; }
@media (prefers-reduced-motion: reduce) {
  .mobile-nav-list a { transition: none; opacity: 1; transform: none; }
  .mobile-nav-overlay { transition: none; }
}

/* ---------- Hero ---------- */
.hero {
  padding-block: clamp(40px, 7vw, 96px) clamp(48px, 8vw, 96px);
}
.hero-grid {
  display: grid;
  gap: 40px;
  align-items: center;
}
.hero-copy { max-width: 560px; }
.hero-copy h1 { margin-bottom: 0.4em; }
.hero-actions { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 28px; }
.hero-chips { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 32px; }
.chip {
  font-size: var(--fs-caption);
  padding: 8px 14px;
  border-radius: var(--radius-pill);
  background: var(--color-surface-alt);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
}
.hero-media {
  border-radius: var(--radius-lg);
  overflow: hidden;
  aspect-ratio: 4 / 5;
}
.hero-media img { width: 100%; height: 100%; object-fit: cover; }
@media (min-width: 900px) {
  .hero-grid { grid-template-columns: 1fr 1fr; gap: 64px; }
  .hero-media { aspect-ratio: 16 / 12; }
}

/* photo treatment shared across galleries */
.photo { filter: saturate(0.94) sepia(0.06) contrast(1.02); }

/* ---------- Trust strip ---------- */
.trust-grid {
  display: grid;
  gap: 24px;
  grid-template-columns: repeat(2, 1fr);
}
@media (min-width: 720px) { .trust-grid { grid-template-columns: repeat(4, 1fr); } }
.trust-item {
  padding: 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
.trust-item h3 { font-size: 1rem; margin-bottom: 0.35em; }
.trust-item p { font-size: 0.9rem; color: var(--color-text-muted); margin: 0; }
.trust-icon { width: 32px; height: 32px; margin-bottom: 14px; color: var(--color-accent-strong); }

.stats-row {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px;
  margin-top: 48px; padding-top: 40px; border-top: 1px solid var(--color-border);
  text-align: center;
}
@media (min-width: 720px) { .stats-row { grid-template-columns: repeat(4, 1fr); } }
.stats-value { display: block; font-family: var(--font-heading); font-size: 2.25rem; color: var(--color-accent-strong); line-height: 1; }
.stats-label { display: block; margin-top: 8px; font-size: 0.8125rem; color: var(--color-text-muted); }

/* ---------- Cards grid ---------- */
.card-grid {
  display: grid;
  gap: 28px;
  grid-template-columns: 1fr;
}
@media (min-width: 640px) { .card-grid { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 1024px) { .card-grid.cols-3 { grid-template-columns: repeat(3, 1fr); } }

.service-card {
  display: block;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface);
  transition: border-color var(--transition-medium);
}
.service-card:hover { border-color: var(--color-accent); }
.service-card-media { aspect-ratio: 4 / 3; overflow: hidden; }
.service-card-media img { width: 100%; height: 100%; object-fit: cover; transition: transform var(--transition-slow); }
.service-card:hover .service-card-media img { transform: scale(1.05); }
.service-card-body { padding: 22px; }
.service-card-body h3 { font-size: 1.125rem; margin-bottom: 0.4em; }
.service-card-body p {
  color: var(--color-text-muted);
  font-size: 0.9375rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.service-card-body .link-arrow { margin-top: 12px; font-size: 0.9375rem; }

.doctor-card { text-align: left; }
.doctor-card-media { aspect-ratio: 3 / 4; border-radius: var(--radius-md); overflow: hidden; margin-bottom: 16px; }
.doctor-card-media img { width: 100%; height: 100%; object-fit: cover; }
.doctor-card h3 { font-size: 1.0625rem; margin-bottom: 0.2em; position: relative; display: inline-block; }
.doctor-card h3::after {
  content: ''; position: absolute; left: 0; bottom: -4px; height: 1px; width: 100%;
  background: var(--color-accent); transform: scaleX(0); transform-origin: left; transition: transform var(--transition-fast);
}
.doctor-card:hover h3::after { transform: scaleX(1); }
.doctor-card .role { color: var(--color-accent-strong); font-size: 0.875rem; margin-bottom: 6px; }
.doctor-card .spec { color: var(--color-text-muted); font-size: 0.875rem; }

.tech-card { padding: 26px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
.tech-card-media { aspect-ratio: 16/10; border-radius: var(--radius-sm); overflow: hidden; margin-bottom: 18px; }
.tech-card-media img { width: 100%; height: 100%; object-fit: cover; }
.tech-card h3 { font-size: 1.0625rem; margin-bottom: 0.4em; }
.tech-card .explain { font-size: 0.9375rem; color: var(--color-text-muted); margin-bottom: 10px; }
.tech-card .benefit { font-size: 0.875rem; padding-top: 10px; border-top: 1px dashed var(--color-border); }

/* ---------- Process timeline ---------- */
.process-list { display: grid; gap: 32px; }
@media (min-width: 860px) { .process-list { grid-template-columns: repeat(5, 1fr); gap: 20px; } }
.process-step .step-num {
  font-family: var(--font-heading);
  font-size: 1.75rem;
  color: var(--color-accent);
  margin-bottom: 10px;
  display: block;
}
.process-step h3 { font-size: 1rem; margin-bottom: 0.4em; }
.process-step p { font-size: 0.875rem; color: var(--color-text-muted); }

/* ---------- Patient experience ---------- */
.experience-list { display: grid; gap: 24px; }
@media (min-width: 860px) { .experience-list { grid-template-columns: repeat(5, 1fr); } }
.experience-step { border-left: 2px solid var(--color-accent-soft); padding-left: 16px; }
.experience-step h3 { font-size: 1rem; }
.experience-step p { font-size: 0.875rem; color: var(--color-text-muted); }

/* ---------- FAQ ---------- */
.faq-item { border-bottom: 1px solid var(--color-border); }
.faq-question {
  width: 100%; display: flex; justify-content: space-between; align-items: center;
  padding: 20px 0; background: none; border: none; text-align: left; font-family: var(--font-heading); font-size: 1.0625rem; color: var(--color-text);
}
.faq-question .plus { transition: transform var(--transition-fast); font-size: 1.25rem; color: var(--color-accent-strong); }
.faq-item.is-open .plus { transform: rotate(45deg); }
.faq-answer {
  max-height: 0; overflow: hidden; transition: max-height var(--transition-medium);
  color: var(--color-text-muted); font-size: 0.9375rem;
}
.faq-answer-inner { padding-bottom: 20px; }

/* ---------- Reviews ---------- */
.review-card {
  padding: 26px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md);
  position: relative;
}
.review-card .quote { font-size: 1.0625rem; font-family: var(--font-heading); margin-bottom: 16px; }
.review-card .author { font-size: 0.875rem; color: var(--color-text-muted); }
.rating-line { font-size: 0.9375rem; color: var(--color-text-muted); margin-top: 10px; }
.rating-line strong { color: var(--color-accent-strong); }

/* ---------- Final CTA ---------- */
.final-cta { background: var(--color-primary); color: var(--color-primary-contrast); border-radius: var(--radius-lg); overflow: hidden; }
.final-cta-grid { display: grid; gap: 32px; align-items: center; padding: clamp(32px, 5vw, 64px); }
.final-cta h2 { color: var(--color-primary-contrast); }
.final-cta p { color: rgba(250,247,241,0.75); }
.final-cta-media { aspect-ratio: 4/3; border-radius: var(--radius-md); overflow: hidden; }
.final-cta-media img { width: 100%; height: 100%; object-fit: cover; }
.final-cta-actions { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 24px; }
.final-cta .btn-outline { border-color: rgba(250,247,241,0.35); color: var(--color-primary-contrast); }
.final-cta .btn-outline:hover { border-color: var(--color-accent); color: var(--color-accent); }
@media (min-width: 900px) { .final-cta-grid { grid-template-columns: 1.1fr 0.9fr; } }

/* ---------- Breadcrumb ---------- */
.breadcrumb { font-size: 0.8125rem; color: var(--color-text-muted); margin-bottom: 24px; }
.breadcrumb a:hover { color: var(--color-accent-strong); }
.breadcrumb .sep { margin-inline: 6px; }

/* ---------- Footer ---------- */
.site-footer { background: var(--color-primary); color: rgba(250,247,241,0.85); padding-block: var(--section-spacing) 32px; }
.footer-top { display: grid; gap: 40px; grid-template-columns: 1fr; margin-bottom: 48px; }
@media (min-width: 720px) { .footer-top { grid-template-columns: 1.4fr 1fr 1fr 1fr; } }
.footer-brand { font-family: var(--font-heading); font-size: 1.375rem; color: var(--color-primary-contrast); margin-bottom: 10px; }
.footer-tagline { color: rgba(250,247,241,0.6); font-size: 0.9375rem; }
.footer-col h4 { color: var(--color-primary-contrast); font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 16px; }
.footer-col ul { display: flex; flex-direction: column; gap: 10px; }
.footer-col a { color: rgba(250,247,241,0.75); font-size: 0.9375rem; }
.footer-col a:hover { color: var(--color-accent); }
.footer-bottom {
  border-top: 1px solid rgba(250,247,241,0.15);
  padding-top: 24px;
  display: flex; flex-direction: column; gap: 8px; align-items: center; text-align: center;
  font-size: 0.8125rem; color: rgba(250,247,241,0.55);
}
.footer-bottom a { color: rgba(250,247,241,0.75); }
.footer-bottom a:hover { color: var(--color-accent); }
.footer-disclosure {
  margin: 16px auto 0; max-width: 720px; text-align: center;
  font-size: 0.75rem; line-height: 1.6; color: rgba(250,247,241,0.4);
}

/* ---------- Intro splash ---------- */
.intro-splash {
  display: none;
  position: fixed; inset: 0; z-index: var(--z-splash);
  align-items: center; justify-content: center;
  background: #000;
  opacity: 1;
  transition: opacity 700ms ease;
}
.intro-splash.is-active { display: flex; }
.intro-splash.is-hiding { opacity: 0; }
.intro-splash-logo {
  width: min(70vw, 420px);
  height: auto;
  opacity: 0;
  transform: scale(0.92);
  animation: introSplashLogoIn 900ms cubic-bezier(.22,1,.36,1) forwards;
}
@keyframes introSplashLogoIn {
  to { opacity: 1; transform: scale(1); }
}
@media (prefers-reduced-motion: reduce) {
  .intro-splash { transition: none; }
  .intro-splash-logo { animation: none; opacity: 1; transform: none; }
}

/* ---------- Booking modal ---------- */
.modal-backdrop {
  position: fixed; inset: 0; background: rgba(34,31,26,0.55); z-index: var(--z-modal);
  display: flex; align-items: flex-end; justify-content: center;
  opacity: 0; visibility: hidden; transition: opacity var(--transition-medium), visibility var(--transition-medium);
}
.modal-backdrop.is-open { opacity: 1; visibility: visible; }
.modal-panel {
  background: var(--color-surface); width: 100%; max-width: 560px;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  padding: 32px var(--container-gutter) calc(32px + env(safe-area-inset-bottom));
  max-height: 88vh; overflow-y: auto;
  transform: translateY(24px);
  transition: transform var(--transition-medium);
  box-shadow: var(--shadow-modal);
}
.modal-backdrop.is-open .modal-panel { transform: translateY(0); }
@media (min-width: 720px) {
  .modal-backdrop { align-items: center; }
  .modal-panel { border-radius: var(--radius-lg); }
}
.modal-close { position: absolute; top: 20px; right: 20px; background: none; border: none; font-size: 1.5rem; color: var(--color-text-muted); }
.form-field { margin-bottom: 18px; }
.form-field label { display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 6px; }
.form-field input, .form-field select, .form-field textarea {
  width: 100%; padding: 13px 16px; border-radius: var(--radius-sm); border: 1px solid var(--color-border);
  background: var(--color-bg); font: inherit; color: var(--color-text);
}
.form-field textarea { resize: vertical; min-height: 90px; }
.form-note { font-size: 0.8125rem; color: var(--color-text-muted); margin-top: 12px; }

/* ---------- Desktop WhatsApp float ---------- */
.whatsapp-float {
  position: fixed; right: 24px; bottom: 24px; z-index: var(--z-bottom-bar);
  width: 56px; height: 56px; border-radius: 50%;
  background: var(--color-whatsapp); color: #fff;
  display: none; align-items: center; justify-content: center;
  box-shadow: var(--shadow-card);
  transition: transform var(--transition-fast);
}
.whatsapp-float:hover { transform: scale(1.06); }
@media (min-width: 960px) { .whatsapp-float { display: flex; } }

/* ---------- Mobile bottom bar ---------- */
.mobile-bottom-bar {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: var(--z-bottom-bar);
  display: flex; background: var(--color-surface); border-top: 1px solid var(--color-border);
  padding-bottom: env(safe-area-inset-bottom);
}
.mobile-bottom-bar a, .mobile-bottom-bar button {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 12px 4px; font-size: 0.75rem; font-weight: 600; background: none; border: none; color: var(--color-text);
}
.mobile-bottom-bar .bar-icon { width: 20px; height: 20px; }
.mobile-bottom-bar .book-btn { color: var(--color-accent-strong); }
@media (min-width: 960px) { .mobile-bottom-bar { display: none; } }
body.has-bottom-bar { padding-bottom: 64px; }
@media (min-width: 960px) { body.has-bottom-bar { padding-bottom: 0; } }

/* ---------- Reveal animation ----------
   Content is visible by default (progressive enhancement). Only once main.js
   has confirmed it's running does it add "js-reveal" to <html>, which is what
   switches .reveal elements to the hidden pre-animation state; main.js then
   flips .is-visible via IntersectionObserver. If JS never runs (blocked,
   fails, disabled), nothing below this point ever goes invisible. */
.js-reveal .reveal { opacity: 0; transform: translateY(16px); transition: opacity var(--transition-slow), transform var(--transition-slow); }
.js-reveal .reveal.is-visible { opacity: 1; transform: translateY(0); }
@media (prefers-reduced-motion: reduce) {
  .js-reveal .reveal { opacity: 1; transform: none; transition: none; }
}

/* ---------- Misc pages ---------- */
.page-header { padding-block: clamp(40px, 6vw, 72px) clamp(24px, 4vw, 40px); }
.two-col { display: grid; gap: 40px; }
@media (min-width: 900px) { .two-col { grid-template-columns: 1fr 1fr; align-items: center; } }
.about-section + .about-section { border-top: 1px solid var(--color-border); }
.contact-grid { display: grid; gap: 40px; }
@media (min-width: 900px) { .contact-grid { grid-template-columns: 1fr 1fr; } }
.contact-detail { padding: 18px 0; border-bottom: 1px solid var(--color-border); display: flex; justify-content: space-between; gap: 12px; }
.map-card {
  aspect-ratio: 16/9; border-radius: var(--radius-md); background: var(--color-surface-alt);
  border: 1px solid var(--color-border); display: flex; align-items: center; justify-content: center;
  padding: 32px;
}
.map-card-body { text-align: center; display: flex; flex-direction: column; gap: 10px; align-items: center; }
.map-card-body p { margin: 0; color: var(--color-text-muted); }
.pricing-row { display: flex; justify-content: space-between; align-items: baseline; padding: 14px 0; border-bottom: 1px solid var(--color-border); }
.related-strip { display: flex; gap: 20px; overflow-x: auto; padding-bottom: 8px; }
.related-strip .service-card { flex: 0 0 320px; width: 320px; }

```

### FILE: `static/js/main.js`

```javascript
(function () {
  'use strict';

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var lastFocusedEl = null;

  function getFocusable(container) {
    return Array.prototype.slice.call(
      container.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')
    ).filter(function (el) { return el.offsetParent !== null; });
  }

  function trapFocus(container, e) {
    if (e.key !== 'Tab') return;
    var focusable = getFocusable(container);
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  /* ---------------- Header scroll state ---------------- */
  var header = document.querySelector('.site-header');
  if (header) {
    var onScroll = function () {
      header.classList.toggle('is-scrolled', window.scrollY > 8);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---------------- Mobile nav overlay ---------------- */
  var hamburger = document.querySelector('[data-nav-toggle]');
  var overlay = document.querySelector('[data-nav-overlay]');
  var navClose = document.querySelector('[data-nav-close]');

  function openNav() {
    if (!overlay) return;
    lastFocusedEl = document.activeElement;
    overlay.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    overlay.setAttribute('aria-hidden', 'false');
    hamburger && hamburger.setAttribute('aria-expanded', 'true');
    var focusable = getFocusable(overlay);
    if (focusable.length) focusable[0].focus();
  }
  function closeNav() {
    if (!overlay || !overlay.classList.contains('is-open')) return;
    overlay.classList.remove('is-open');
    document.body.style.overflow = '';
    overlay.setAttribute('aria-hidden', 'true');
    hamburger && hamburger.setAttribute('aria-expanded', 'false');
    if (lastFocusedEl) lastFocusedEl.focus();
  }
  if (hamburger) hamburger.addEventListener('click', openNav);
  if (navClose) navClose.addEventListener('click', closeNav);
  if (overlay) {
    overlay.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', closeNav);
    });
    overlay.addEventListener('keydown', function (e) { trapFocus(overlay, e); });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      closeNav();
      closeModal();
    }
  });

  /* ---------------- FAQ accordion ---------------- */
  document.querySelectorAll('.faq-item').forEach(function (item) {
    var btn = item.querySelector('.faq-question');
    var answer = item.querySelector('.faq-answer');
    if (!btn || !answer) return;
    btn.setAttribute('aria-expanded', 'false');
    btn.addEventListener('click', function () {
      var isOpen = item.classList.contains('is-open');
      document.querySelectorAll('.faq-item.is-open').forEach(function (openItem) {
        if (openItem !== item) {
          openItem.classList.remove('is-open');
          openItem.querySelector('.faq-answer').style.maxHeight = null;
          openItem.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
        }
      });
      if (isOpen) {
        item.classList.remove('is-open');
        answer.style.maxHeight = null;
        btn.setAttribute('aria-expanded', 'false');
      } else {
        item.classList.add('is-open');
        answer.style.maxHeight = answer.scrollHeight + 'px';
        btn.setAttribute('aria-expanded', 'true');
      }
    });
  });

  /* ---------------- Reveal on scroll ---------------- */
  var revealEls = document.querySelectorAll('.reveal');
  if (revealEls.length) {
    if (prefersReducedMotion || !('IntersectionObserver' in window)) {
      revealEls.forEach(function (el) { el.classList.add('is-visible'); });
    } else {
      var groups = {};
      revealEls.forEach(function (el) {
        var group = el.getAttribute('data-reveal-group') || 'default';
        groups[group] = groups[group] || [];
        groups[group].push(el);
      });
      Object.keys(groups).forEach(function (key) {
        groups[key].forEach(function (el, i) {
          el.style.transitionDelay = (i * 80) + 'ms';
        });
      });
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            io.unobserve(entry.target);
          }
        });
      }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
      revealEls.forEach(function (el) { io.observe(el); });
    }
  }

  /* ---------------- WhatsApp deep links ----------------
     Static links are rendered server-side (see wa_url() in build.py) — only
     the booking form still needs to build one at submit time, from the
     values the visitor just typed. */
  var body = document.body;
  var waNumber = body.getAttribute('data-whatsapp-number');

  function buildWhatsappUrl(message) {
    return 'https://wa.me/' + waNumber + '?text=' + encodeURIComponent(message);
  }

  /* ---------------- Booking modal ---------------- */
  var modalBackdrop = document.querySelector('[data-booking-modal]');
  var modalOpenTriggers = document.querySelectorAll('[data-open-booking]');
  var modalCloseTriggers = document.querySelectorAll('[data-close-booking]');
  var bookingForm = document.querySelector('[data-booking-form]');
  var modalPanel = modalBackdrop ? modalBackdrop.querySelector('.modal-panel') : null;
  var presetDoctor = '';

  function openModal(presetService, presetDoctorName) {
    if (!modalBackdrop) return;
    lastFocusedEl = document.activeElement;
    presetDoctor = presetDoctorName || '';
    modalBackdrop.classList.add('is-open');
    modalBackdrop.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    if (presetService && bookingForm) {
      var select = bookingForm.querySelector('[name="service"]');
      if (select) select.value = presetService;
    }
    if (bookingForm) {
      var nameInput = bookingForm.querySelector('[name="name"]');
      if (nameInput) nameInput.focus();
    }
  }
  function closeModal() {
    if (!modalBackdrop || !modalBackdrop.classList.contains('is-open')) return;
    modalBackdrop.classList.remove('is-open');
    modalBackdrop.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (lastFocusedEl) lastFocusedEl.focus();
  }
  modalOpenTriggers.forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      openModal(el.getAttribute('data-service'), el.getAttribute('data-doctor'));
    });
  });
  modalCloseTriggers.forEach(function (el) { el.addEventListener('click', closeModal); });
  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', function (e) {
      if (e.target === modalBackdrop) closeModal();
    });
  }
  if (modalPanel) {
    modalPanel.addEventListener('keydown', function (e) { trapFocus(modalPanel, e); });
  }

  if (bookingForm) {
    var tmpl = bookingForm.getAttribute('data-message-template') || '';
    bookingForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = bookingForm.querySelector('[name="name"]').value.trim();
      var phone = bookingForm.querySelector('[name="phone"]').value.trim();
      var service = bookingForm.querySelector('[name="service"]').value;
      var contact = bookingForm.querySelector('[name="contactMethod"]').value;
      var msg = bookingForm.querySelector('[name="message"]').value.trim();

      var serviceClause = service ? bookingForm.getAttribute('data-service-clause').replace('{service}', service) : '';
      var doctorClause = presetDoctor ? bookingForm.getAttribute('data-doctor-clause').replace('{doctor}', presetDoctor) : '';
      var messageClause = msg ? bookingForm.getAttribute('data-message-clause').replace('{message}', msg) : '';

      var finalMessage = tmpl
        .replace('{name}', name || '—')
        .replace('{phone}', phone || '—')
        .replace('{doctorClause}', doctorClause)
        .replace('{serviceClause}', serviceClause)
        .replace('{contact}', contact)
        .replace('{messageClause}', messageClause);

      window.open(buildWhatsappUrl(finalMessage), '_blank', 'noopener');
      closeModal();
      bookingForm.reset();
    });
  }
})();

```


---

# ФИНАЛЬНЫЕ ШАГИ

1. Создай все файлы по путям, указанным выше (структура + весь код механики).
2. Заполни `data/*.json` и `content/{lang}.json` данными из приложенного
   брифа клиента (`CLIENT_BRIEF.md`), следуя схемам и примерам выше.
3. Помести логотип и фотографии клиента в `static/brand/` и
   `static/images/...` по путям, указанным в `data/site.json`/`doctors.json`/
   `services.json`/`technology.json`.
4. Подставь палитру клиента в `static/css/tokens.css` (только цветовые
   токены, остальное не трогать).
5. Выполни `python3 build.py`, затем `python3 validate.py`.
6. `validate.py` обязан вывести `PASSED: 0 errors` — если есть ошибки,
   исправь их (обычно это опечатка в пути к картинке, незаполненное поле
   перевода на одном из языков, или расхождение чисел в `stats`) и повтори
   сборку и проверку, пока не будет `PASSED: 0 errors`.
7. Покажи получившиеся файлы и структуру `dist/` пользователю, либо, если
   инструмент это умеет, упакуй `dist/` в архив для скачивания или выложи
   на статический хостинг.

Не пропускай шаг с `validate.py` — это единственная гарантия, что сайт не
уедет клиенту с битой ссылкой, незаполненным переводом или забытым
плейсхолдерным текстом.
