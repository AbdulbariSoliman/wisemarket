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

before_dinners = """const DINNERS = [
  { icon:'\U0001f414', name:'Roast Chicken',    search:'poulet kartoffeln kr\u00e4uter' },
  { icon:'\U0001f35d', name:'Pasta Bolognese',  search:'hackfleisch pasta tomaten' },
  { icon:'\U0001f957', name:'Light Salad',      search:'salat lachs avocado' },
  { icon:'\U0001f41f', name:'Salmon & Veg',     search:'lachs gem\u00fcse zitrone' },
  { icon:'\U0001f9c0', name:'Raclette Evening', search:'raclettek\u00e4se kartoffeln cornichons' },
  { icon:'\U0001f372', name:'Fondue Night',     search:'fonduek\u00e4se brot weisswein' },
  { icon:'\U0001f355', name:'Pizza Night',      search:'mozzarella tomaten pizza teig' },
]"""

after_dinners = """const DINNERS = [
  { id:'roast_chicken',    icon:'\U0001f414', name:'Roast Chicken',    search:'poulet kartoffeln kr\u00e4uter' },
  { id:'pasta_bolognese',  icon:'\U0001f35d', name:'Pasta Bolognese',  search:'hackfleisch pasta tomaten' },
  { id:'light_salad',      icon:'\U0001f957', name:'Light Salad',      search:'salat lachs avocado' },
  { id:'salmon_and_veg',   icon:'\U0001f41f', name:'Salmon & Veg',     search:'lachs gem\u00fcse zitrone' },
  { id:'raclette_evening', icon:'\U0001f9c0', name:'Raclette Evening', search:'raclettek\u00e4se kartoffeln cornichons' },
  { id:'fondue_night',     icon:'\U0001f372', name:'Fondue Night',     search:'fonduek\u00e4se brot weisswein' },
  { id:'pizza_night',      icon:'\U0001f355', name:'Pizza Night',      search:'mozzarella tomaten pizza teig' },
]"""

content, ok1 = replace_exact(content, before_dinners, after_dinners, "add explicit id to each DINNERS entry")

before_nav = "onClick={() => navigate(`/recipe/${dinner.name.toLowerCase().replace(/\\s+/g, '_')}`)}>"
after_nav = "onClick={() => navigate(`/recipe/${dinner.id}`)}>"

content, ok2 = replace_exact(content, before_nav, after_nav, "use dinner.id directly for navigation")

if ok1 and ok2:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nBoth changes applied. File saved.")
else:
    print("\nOne or more changes NOT applied (see SKIP/WARN above). File NOT saved.")