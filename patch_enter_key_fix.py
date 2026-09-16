PATH = "frontend/wisemarket/src/pages/Home.jsx"


def replace_exact(content, before, after, label):
    if before not in content:
        print(f"  SKIP/WARN [{label}]: expected text not found.")
        return content, False
    if content.count(before) > 1:
        print(f"  WARN [{label}]: text appears more than once - manual check needed.")
        return content, False
    print(f"  OK [{label}]")
    return content.replace(before, after, 1), True


with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

before = '''            onKeyDown={e => {
              if (e.key === 'Enter' && isGtin) navigate(`/product/${query.trim()}`)
            }}'''

after = '''            onKeyDown={e => {
              if (e.key === 'Enter') {
                if (isGtin) {
                  navigate(`/product/${query.trim()}`)
                } else {
                  e.target.blur()
                }
              }
            }}'''

content, ok = replace_exact(content, before, after, "Enter key blurs input for non-GTIN search")

if ok:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nChange applied. File saved.")
else:
    print("\nChange NOT applied (see SKIP/WARN above). File NOT saved.")