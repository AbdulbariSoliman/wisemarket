PATH = "frontend/wisemarket/src/App.jsx"


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

before_import = "import Settings    from './pages/Settings'"
after_import = "import Settings    from './pages/Settings'\nimport RecipeView  from './pages/RecipeView'"
content, ok1 = replace_exact(content, before_import, after_import, "add RecipeView import")

before_route = '''        <Route path="/settings"   element={onboarded ? <Settings /> : <Navigate to="/onboarding" replace />} />'''
after_route = '''        <Route path="/settings"   element={onboarded ? <Settings /> : <Navigate to="/onboarding" replace />} />
        <Route path="/recipe/:recipeId" element={<RecipeView />} />'''
content, ok2 = replace_exact(content, before_route, after_route, "add /recipe/:recipeId route")

if ok1 and ok2:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\\nBoth changes applied. File saved.")
else:
    print("\\nOne or more changes NOT applied (see SKIP/WARN above). File NOT saved.")