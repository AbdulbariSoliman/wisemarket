PATH = "frontend/wisemarket/src/pages/Home.jsx"


def replace_exact(content, before, after, label):
    if before not in content:
        print("  SKIP/WARN [" + label + "]: expected text not found.")
        return content, False
    if content.count(before) > 1:
        print("  WARN [" + label + "]: text appears more than once - manual check needed.")
        return content, False
    print("  OK [" + label + "]")
    return content.replace(before, after, 1), True


with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

before = """            <div className="card" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}
              onClick={() => { setQuery(dinner.search); inputRef.current?.focus() }}>
              <span style={{ fontSize: 36 }}>{dinner.icon}</span>
              <div style={{ flex: 1 }}>
                <p style={{ margin: 0, fontWeight: 600, fontSize: 15 }}>{dinner.name}</p>
                <p style={{ margin: '3px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                  Tap to find ingredients \u2192
                </p>
              </div>"""

after = """            <div className="card" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}
              onClick={() => navigate(`/recipe/${dinner.name.toLowerCase().replace(/\\s+/g, '_')}`)}>
              <span style={{ fontSize: 36 }}>{dinner.icon}</span>
              <div style={{ flex: 1 }}>
                <p style={{ margin: 0, fontWeight: 600, fontSize: 15 }}>{dinner.name}</p>
                <p style={{ margin: '3px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                  Tap for the full recipe \u2192
                </p>
              </div>"""

content, ok = replace_exact(content, before, after, "navigate to RecipeView instead of just searching")

if ok:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nChange applied. File saved.")
else:
    print("\nChange NOT applied (see SKIP/WARN above). File NOT saved.")