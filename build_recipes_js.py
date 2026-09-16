PATH = "frontend/wisemarket/src/data/recipes.js"

CONTENT = """// ============================================================
// WISEMARKET \u2014 CURATED RECIPES
// ============================================================
// searchTerm is always GERMAN, to match the product catalog
// (Migros names are DE) - regardless of which language a
// recipe's steps/name are displayed in.
//
// LANGUAGE STATUS: "en" and "de" are fully written and reviewed.
// "fr" and "it" fields exist in the shape but are NOT YET
// POPULATED with real content - do not display fr/it text to
// users until a native speaker has reviewed it. This is
// intentional: machine-translated cooking instructions can
// introduce real errors, so we're not shipping unreviewed text.
//
// seeAlso: OPTIONAL links to real external sources (chef videos,
// official recipe pages). LINKS ONLY - we never reproduce a
// chef's actual recipe text. Always legal, same as a "See also"
// reference in an encyclopedia article.
// ============================================================

export const RECIPES = {

  roast_chicken: {
    id: "roast_chicken",
    category: "meat",
    area: "Swiss",
    image: null,
    video: null,
    servings: 4,
    text: {
      en: {
        name: "Roast Chicken",
        steps: [
          "Preheat oven to 200\u00b0C.",
          "Pat the chicken dry, rub with olive oil, salt, and herbs inside and out.",
          "Peel and chop potatoes, carrots, and onions; toss with oil and salt in a roasting tray.",
          "Place chicken on top of the vegetables.",
          "Roast ~75 minutes, until the juices run clear and the vegetables are tender. Cook poultry until fully done.",
          "Rest 10 minutes before carving; serve with the roasted vegetables.",
        ],
      },
      de: {
        name: "Gebratenes Poulet",
        steps: [
          "Ofen auf 200\u00b0C vorheizen.",
          "Poulet trocken tupfen, innen und aussen mit Oliven\u00f6l, Salz und Kr\u00e4utern einreiben.",
          "Kartoffeln, Karotten und Zwiebeln sch\u00e4len und schneiden; mit \u00d6l und Salz in eine Bratform geben.",
          "Poulet auf das Gem\u00fcse legen.",
          "Ca. 75 Minuten braten, bis der Fleischsaft klar austritt und das Gem\u00fcse weich ist. Gefl\u00fcgel immer vollst\u00e4ndig durchgaren.",
          "10 Minuten ruhen lassen, dann tranchieren und mit dem Gem\u00fcse servieren.",
        ],
      },
      fr: null,
      it: null,
    },
    ingredients: [
      { searchTerm: "poulet",     nameEn: "Whole chicken", nameDe: "Ganzes Poulet",       measure: "1 (~1.4 kg)" },
      { searchTerm: "kartoffeln", nameEn: "Potatoes",      nameDe: "Kartoffeln",           measure: "800 g" },
      { searchTerm: "karotten",   nameEn: "Carrots",       nameDe: "Karotten",             measure: "300 g" },
      { searchTerm: "zwiebeln",   nameEn: "Onion",         nameDe: "Zwiebeln",             measure: "2" },
      { searchTerm: "olivenoel",  nameEn: "Olive oil",     nameDe: "Oliven\u00f6l",             measure: "3 tbsp" },
      { searchTerm: "kraeuter",   nameEn: "Fresh herbs",   nameDe: "Frische Kr\u00e4uter",      measure: "1 bunch" },
      { searchTerm: "salz",       nameEn: "Salt",          nameDe: "Salz",                 measure: "to taste" },
    ],
    source: { kind: "curated", label: "WiseMarket", url: null },
    seeAlso: [],
  },

  pasta_bolognese: {
    id: "pasta_bolognese",
    category: "pantry",
    area: "Italian",
    image: null,
    video: null,
    servings: 4,
    text: {
      en: {
        name: "Pasta Bolognese",
        steps: [
          "Finely chop onion and garlic. Heat olive oil in a pan.",
          "Saut\u00e9 onion and garlic until soft.",
          "Add minced beef; brown thoroughly until fully cooked.",
          "Add chopped tomatoes, season, and simmer 20\u201330 minutes.",
          "Meanwhile cook spaghetti in salted water until al dente.",
          "Drain pasta and serve topped with the sauce.",
        ],
      },
      de: {
        name: "Pasta Bolognese",
        steps: [
          "Zwiebel und Knoblauch fein hacken. Oliven\u00f6l in einer Pfanne erhitzen.",
          "Zwiebel und Knoblauch and\u00fcnsten, bis sie weich sind.",
          "Hackfleisch dazugeben; gut anbraten, bis es vollst\u00e4ndig durchgegart ist.",
          "Gehackte Tomaten dazugeben, w\u00fcrzen und 20\u201330 Minuten k\u00f6cheln lassen.",
          "In der Zwischenzeit Spaghetti in Salzwasser al dente kochen.",
          "Pasta abgiessen und mit der Sauce servieren.",
        ],
      },
      fr: null,
      it: null,
    },
    ingredients: [
      { searchTerm: "spaghetti",   nameEn: "Spaghetti",        nameDe: "Spaghetti",          measure: "500 g" },
      { searchTerm: "hackfleisch", nameEn: "Minced beef",      nameDe: "Hackfleisch",        measure: "500 g" },
      { searchTerm: "tomaten",     nameEn: "Chopped tomatoes", nameDe: "Gehackte Tomaten",   measure: "800 g" },
      { searchTerm: "zwiebeln",    nameEn: "Onion",            nameDe: "Zwiebeln",           measure: "1" },
      { searchTerm: "knoblauch",   nameEn: "Garlic",           nameDe: "Knoblauch",          measure: "2 cloves" },
      { searchTerm: "olivenoel",   nameEn: "Olive oil",        nameDe: "Oliven\u00f6l",           measure: "2 tbsp" },
      { searchTerm: "salz",        nameEn: "Salt & pepper",    nameDe: "Salz & Pfeffer",     measure: "to taste" },
    ],
    source: { kind: "curated", label: "WiseMarket", url: null },
    seeAlso: [
      { label: "Gordon Ramsay's Spaghetti Bolognese (YouTube)", url: "https://www.youtube.com/watch?v=Sk_CGtA4HIY" },
    ],
  },

  light_salad: {
    id: "light_salad",
    category: "fresh_produce",
    area: "Swiss",
    image: null,
    video: null,
    servings: 2,
    text: {
      en: {
        name: "Light Salad",
        steps: [
          "Season salmon and pan-fry until cooked through.",
          "Wash and tear salad leaves; slice cucumber and avocado.",
          "Whisk olive oil with lemon juice, salt, and pepper for the dressing.",
          "Toss leaves with dressing, top with cucumber, avocado, and flaked salmon.",
        ],
      },
      de: {
        name: "Leichter Salat",
        steps: [
          "Lachs w\u00fcrzen und in der Pfanne durchbraten.",
          "Salatbl\u00e4tter waschen und zupfen; Gurke und Avocado in Scheiben schneiden.",
          "Oliven\u00f6l mit Zitronensaft, Salz und Pfeffer f\u00fcr das Dressing verr\u00fchren.",
          "Bl\u00e4tter mit Dressing mischen, mit Gurke, Avocado und Lachsflocken garnieren.",
        ],
      },
      fr: null,
      it: null,
    },
    ingredients: [
      { searchTerm: "salat",     nameEn: "Mixed salad leaves", nameDe: "Gemischte Salatbl\u00e4tter", measure: "150 g" },
      { searchTerm: "lachs",     nameEn: "Salmon fillet",      nameDe: "Lachsfilet",              measure: "200 g" },
      { searchTerm: "avocado",   nameEn: "Avocado",            nameDe: "Avocado",                 measure: "1" },
      { searchTerm: "gurken",    nameEn: "Cucumber",           nameDe: "Gurke",                   measure: "1/2" },
      { searchTerm: "olivenoel", nameEn: "Olive oil",          nameDe: "Oliven\u00f6l",                measure: "2 tbsp" },
      { searchTerm: "zitrone",   nameEn: "Lemon",              nameDe: "Zitrone",                 measure: "1" },
    ],
    source: { kind: "curated", label: "WiseMarket", url: null },
    seeAlso: [],
  },

  salmon_and_veg: {
    id: "salmon_and_veg",
    category: "fish",
    area: "Swiss",
    image: null,
    video: null,
    servings: 4,
    text: {
      en: {
        name: "Salmon & Veg",
        steps: [
          "Preheat oven to 200\u00b0C.",
          "Chop vegetables, toss with oil and salt, spread on a tray.",
          "Place salmon fillets on the tray, drizzle with oil, top with lemon slices.",
          "Bake ~18\u201320 minutes until the salmon is cooked through and flakes easily.",
        ],
      },
      de: {
        name: "Lachs mit Gem\u00fcse",
        steps: [
          "Ofen auf 200\u00b0C vorheizen.",
          "Gem\u00fcse schneiden, mit \u00d6l und Salz mischen, auf ein Blech verteilen.",
          "Lachsfilets auf das Blech legen, mit \u00d6l betr\u00e4ufeln, mit Zitronenscheiben belegen.",
          "Ca. 18\u201320 Minuten backen, bis der Lachs durchgegart ist und sich leicht mit der Gabel teilen l\u00e4sst.",
        ],
      },
      fr: null,
      it: null,
    },
    ingredients: [
      { searchTerm: "lachs",     nameEn: "Salmon fillets",   nameDe: "Lachsfilets",       measure: "4 (~600 g)" },
      { searchTerm: "gemuese",   nameEn: "Mixed vegetables", nameDe: "Gemischtes Gem\u00fcse", measure: "600 g" },
      { searchTerm: "zitrone",   nameEn: "Lemon",            nameDe: "Zitrone",           measure: "1" },
      { searchTerm: "olivenoel", nameEn: "Olive oil",        nameDe: "Oliven\u00f6l",          measure: "3 tbsp" },
      { searchTerm: "salz",      nameEn: "Salt & pepper",    nameDe: "Salz & Pfeffer",    measure: "to taste" },
    ],
    source: { kind: "curated", label: "WiseMarket", url: null },
    seeAlso: [],
  },

  raclette_evening: {
    id: "raclette_evening",
    category: "dairy",
    area: "Swiss",
    image: null,
    video: null,
    servings: 4,
    text: {
      en: {
        name: "Raclette Evening",
        steps: [
          "Boil potatoes (skin on) until tender; keep warm.",
          "Slice raclette cheese for the raclette grill.",
          "Melt cheese in the raclette pans until bubbling.",
          "Serve melted cheese over potatoes with cornichons and pickled onions.",
        ],
      },
      de: {
        name: "Raclette-Abend",
        steps: [
          "Kartoffeln mit Schale kochen, bis sie weich sind; warm halten.",
          "Raclettek\u00e4se f\u00fcr den Raclette-Ofen in Scheiben schneiden.",
          "K\u00e4se in den Pf\u00e4nnchen schmelzen, bis er blubbert.",
          "Geschmolzenen K\u00e4se \u00fcber Kartoffeln servieren, mit Cornichons und Silberzwiebeln.",
        ],
      },
      fr: null,
      it: null,
    },
    ingredients: [
      { searchTerm: "raclettekaese",   nameEn: "Raclette cheese", nameDe: "Raclettek\u00e4se",   measure: "800 g" },
      { searchTerm: "kartoffeln",      nameEn: "Potatoes",        nameDe: "Kartoffeln",      measure: "1 kg" },
      { searchTerm: "cornichons",      nameEn: "Cornichons",      nameDe: "Cornichons",      measure: "1 jar" },
      { searchTerm: "silberzwiebeln",  nameEn: "Pickled onions",  nameDe: "Silberzwiebeln",  measure: "1 jar" },
    ],
    source: { kind: "curated", label: "WiseMarket", url: null },
    seeAlso: [],
  },

  fondue_night: {
    id: "fondue_night",
    category: "dairy",
    area: "Swiss",
    image: null,
    video: null,
    servings: 4,
    text: {
      en: {
        name: "Fondue Night",
        steps: [
          "Rub the caquelon (fondue pot) with the cut garlic clove.",
          "Add white wine and warm gently.",
          "Add the cheese gradually, stirring until melted and smooth.",
          "Cut bread into cubes and serve for dipping. Keep the fondue warm over the burner.",
        ],
      },
      de: {
        name: "Fondue-Abend",
        steps: [
          "Caquelon (Fonduetopf) mit der aufgeschnittenen Knoblauchzehe ausreiben.",
          "Weisswein dazugeben und sanft erw\u00e4rmen.",
          "K\u00e4se nach und nach dazugeben, r\u00fchren bis er geschmolzen und glatt ist.",
          "Brot in W\u00fcrfel schneiden und zum Dippen servieren. Fondue \u00fcber der Flamme warm halten.",
        ],
      },
      fr: null,
      it: null,
    },
    ingredients: [
      { searchTerm: "fonduekaese", nameEn: "Fondue cheese mix", nameDe: "Fonduek\u00e4se-Mischung", measure: "800 g" },
      { searchTerm: "brot",        nameEn: "White bread",       nameDe: "Weissbrot",           measure: "1 loaf" },
      { searchTerm: "weisswein",   nameEn: "White wine",        nameDe: "Weisswein",           measure: "300 ml" },
      { searchTerm: "knoblauch",   nameEn: "Garlic",            nameDe: "Knoblauch",           measure: "1 clove" },
    ],
    source: { kind: "curated", label: "WiseMarket", url: null },
    seeAlso: [],
  },

  pizza_night: {
    id: "pizza_night",
    category: "bakery",
    area: "Italian",
    image: null,
    video: null,
    servings: 4,
    text: {
      en: {
        name: "Pizza Night",
        steps: [
          "Preheat oven to its highest setting (~250\u00b0C).",
          "Roll out the dough and spread with passata; season.",
          "Top with torn mozzarella and a drizzle of olive oil.",
          "Bake 8\u201312 minutes until the crust is golden and cheese bubbles.",
          "Finish with fresh basil before serving.",
        ],
      },
      de: {
        name: "Pizza-Abend",
        steps: [
          "Ofen auf h\u00f6chste Stufe vorheizen (~250\u00b0C).",
          "Teig ausrollen und mit Passata bestreichen; w\u00fcrzen.",
          "Mit zerzupftem Mozzarella belegen und mit Oliven\u00f6l betr\u00e4ufeln.",
          "8\u201312 Minuten backen, bis der Rand goldbraun ist und der K\u00e4se blubbert.",
          "Vor dem Servieren mit frischem Basilikum garnieren.",
        ],
      },
      fr: null,
      it: null,
    },
    ingredients: [
      { searchTerm: "pizzateig",  nameEn: "Pizza dough",        nameDe: "Pizzateig",   measure: "2 bases" },
      { searchTerm: "mozzarella", nameEn: "Mozzarella",         nameDe: "Mozzarella",  measure: "250 g" },
      { searchTerm: "tomaten",    nameEn: "Tomatoes / passata", nameDe: "Passata",     measure: "400 g" },
      { searchTerm: "basilikum",  nameEn: "Basil",              nameDe: "Basilikum",   measure: "1 bunch" },
      { searchTerm: "olivenoel",  nameEn: "Olive oil",          nameDe: "Oliven\u00f6l",    measure: "2 tbsp" },
    ],
    source: { kind: "curated", label: "WiseMarket", url: null },
    seeAlso: [],
  },

  zurcher_geschnetzeltes: {
    id: "zurcher_geschnetzeltes",
    category: "meat",
    area: "Swiss",
    image: null,
    video: null,
    servings: 4,
    text: {
      en: {
        name: "Z\u00fcrcher Geschnetzeltes",
        steps: [
          "Cut veal into thin strips.",
          "Sear veal strips in butter over high heat, in batches; set aside.",
          "In the same pan, saut\u00e9 sliced mushrooms and shallots.",
          "Deglaze with white wine, reduce slightly.",
          "Stir in cream, return the veal to the pan, and heat through until fully cooked.",
          "Serve with r\u00f6sti or rice.",
        ],
      },
      de: {
        name: "Z\u00fcrcher Geschnetzeltes",
        steps: [
          "Kalbfleisch in d\u00fcnne Streifen schneiden.",
          "Kalbfleischstreifen portionenweise in Butter bei starker Hitze anbraten; beiseitestellen.",
          "In derselben Pfanne Champignons und Schalotten and\u00fcnsten.",
          "Mit Weisswein abl\u00f6schen, leicht einkochen lassen.",
          "Rahm dazugeben, das Kalbfleisch zur\u00fcck in die Pfanne geben und vollst\u00e4ndig durcherhitzen.",
          "Mit R\u00f6sti oder Reis servieren.",
        ],
      },
      fr: null,
      it: null,
    },
    ingredients: [
      { searchTerm: "kalbfleisch", nameEn: "Veal",       nameDe: "Kalbfleisch",  measure: "600 g" },
      { searchTerm: "champignons", nameEn: "Mushrooms",  nameDe: "Champignons",  measure: "250 g" },
      { searchTerm: "schalotten",  nameEn: "Shallots",   nameDe: "Schalotten",   measure: "2" },
      { searchTerm: "weisswein",   nameEn: "White wine", nameDe: "Weisswein",    measure: "100 ml" },
      { searchTerm: "rahm",        nameEn: "Cream",      nameDe: "Rahm",         measure: "300 ml" },
      { searchTerm: "butter",      nameEn: "Butter",     nameDe: "Butter",       measure: "2 tbsp" },
    ],
    source: { kind: "curated", label: "WiseMarket", url: null },
    seeAlso: [],
  },

  roesti: {
    id: "roesti",
    category: "pantry",
    area: "Swiss",
    image: null,
    video: null,
    servings: 4,
    text: {
      en: {
        name: "Swiss R\u00f6sti",
        steps: [
          "Boil potatoes whole, with skin, until just tender (not fully cooked). Cool, then grate coarsely.",
          "Season grated potato with salt.",
          "Heat butter in a non-stick pan, add potato, press into an even round.",
          "Fry until golden and crisp on the bottom (~10 min).",
          "Flip (using a plate) and fry the other side until golden and cooked through.",
        ],
      },
      de: {
        name: "Schweizer R\u00f6sti",
        steps: [
          "Kartoffeln mit Schale kochen, bis sie knapp weich sind (nicht ganz gar). Abk\u00fchlen lassen, grob raffeln.",
          "Geriebene Kartoffeln salzen.",
          "Butter in einer beschichteten Pfanne erhitzen, Kartoffeln dazugeben, zu einem gleichm\u00e4ssigen Rundling pressen.",
          "Braten, bis die Unterseite goldbraun und knusprig ist (~10 Min.).",
          "Mit einem Teller wenden und die andere Seite goldbraun und vollst\u00e4ndig durchgaren.",
        ],
      },
      fr: null,
      it: null,
    },
    ingredients: [
      { searchTerm: "kartoffeln", nameEn: "Potatoes", nameDe: "Kartoffeln", measure: "1 kg" },
      { searchTerm: "butter",     nameEn: "Butter",   nameDe: "Butter",     measure: "3 tbsp" },
      { searchTerm: "salz",       nameEn: "Salt",     nameDe: "Salz",       measure: "to taste" },
    ],
    source: { kind: "curated", label: "WiseMarket", url: null },
    seeAlso: [],
  },

};

// ============================================================
// Lookup helpers (curated layer, always checked first)
// ============================================================

export function getCuratedRecipe(idOrName) {
  const key = String(idOrName || "").toLowerCase().replace(/\\s+/g, "_");
  if (RECIPES[key]) return RECIPES[key];
  return Object.values(RECIPES).find(r =>
    Object.values(r.text).some(t => t && t.name.toLowerCase() === String(idOrName).toLowerCase())
  ) || null;
}

export function getRecipeText(recipe, lang) {
  const chosen = lang || "en";
  return recipe.text[chosen] || recipe.text.en;
}

export function listCuratedRecipesByArea(area) {
  return Object.values(RECIPES).filter(r => !area || r.area === area);
}
"""


def main():
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(CONTENT)
    print("Wrote " + PATH)
    print("Recipe count: " + str(CONTENT.count('id: "')))


if __name__ == "__main__":
    main()