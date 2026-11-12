# Carga logo + menu de La Guapa. Se ejecuta DENTRO del contenedor:
#   docker compose run --rm -T saas-odoo odoo shell --no-http --workers=0 -d laguapa < scripts/load_laguapa.py
# Idempotente: si el producto ya existe (mismo nombre) lo actualiza.
import base64
import urllib.request

BASE = "https://thissa.store/wp-content/uploads/laguapabaq/"
LOGO = "others/cropped-LGR_Logo-02-1-optimized-380x380.webp"

# categoria -> lineas "nombre|precio|descripcion|imagen(relativa)"
MENU = {
"Entradas": """
Las Nirvanas|26000|Papas en cascos con fondue de cheddar, mermelada de tocineta al ron y café, parmesano|products/DSC00859-optimized-500x750.webp
Buenos Aires|31000|Dos chorizos argentinos, papas en cascos con cheddar, mermelada de tocineta, chimichurri|products/Entrada-Buenos-Aires-optimized-600x750.webp
A Palé|35000|Lomo de res, mix de quesos sobre fondue de champiñones, cebolla a la parrilla, pan de masa madre|others/Entradas-A-pale-600x750.jpg
Chori al Bastón|30000|Dos brochetas de choripán, chorizo argentino, chimichurri, cebolla encurtida, mozzarella|products/Entrada-Chori-al-Baston-optimized-1-600x750.webp
Sweet Disposition|28000|Papas a la francesa, cheddar, mermelada de tocineta, pulled pork caramelizado en BBQ|products/Entrada-Sweet-Disposition-optimized-600x750.webp
Burrata Raven|45000|Burrata sobre pasta de tomate, espinaca, parmesano, tomate cherry, aceitunas moradas|products/Entrada-Ravem-optimized-600x750.webp
Mini mini|35000|Seis mitades de mini burgers en tres sabores (picante, dulce y salado) sobre salsa Carrie|others/Mini-Mini-600x750.jpg
""",
"Burgers": """
Gigi Hadid|38000|Carne Angus 150 g, cheddar, doble tocineta, pepinillos importados, salsa de pimentón escalivado|products/Burger-Gigi-Hadid-optimized-600x750.webp
Belanova|40000|Carne Angus 150 g, pan pretzel, cheddar, tocineta, piña caramelizada, dip de queso crema|products/Burger-Belanova-optimized-600x750.webp
La Guapa|41000|Carne Angus 150 g, doble cheddar, tocineta ahumada, salsa barbacoa artesanal, cebolla crispy|products/Burger-La-Guapa-optimized-600x750.webp
Amy Winehouse|43000|Carne Angus 150 g, mermelada de tocineta al café, doble cheddar, cebolla caramelizada en vino tinto|products/Burger-Amy-Winehouse-optimized-600x750.webp
Spicy Krush (Pollo week)|40000|Pechuga de pollo empanizada, salsa dulce picante, miel, ajo, pepinillos agridulces|products/Burger-Spicy-optimized-e1793667745645-1-750x675.webp
Honeymoon|43000|Carne Angus 150 g, cheddar, mermelada de tocineta al café, queso costeño, pulled pork, mayoajo|products/HONEYMOON-optimized-500x750.webp
Tokischa|40000|Carne Angus 150 g, pimentones caramelizados en vinagre balsámico, BBQ, cebolla crunchy, dip de burrata|products/Burger-.-Tokischa-optimized-600x750.webp
Cardi B|46000|Carne Angus 300 g, doble cheddar, doble tocineta ahumada, pepinillos importados, salsa de pimentón|products/Burger-Cardi-B-optimized-600x750.webp
Kali Uchis|40000|Carne Angus 150 g, mozzarella, cebolla caramelizada en vino merlot, sriracha, mayoajo|products/Burger-Kali-Uchis-optimized-600x750.webp
Carrie Bradshaw (Burger Master)|41000|Pan de papa, pepper jack fundido, carne Angus 150 g adobada, pimentón verde, dip de tocineta|products/DSC09079-optimized-500x750.webp
Portman (vegetariana)|30000|Pan brioche, hamburguesa de garbanzo 150 g, pesto, dip de champiñones, mermelada de pera, queso vegano|products/Burger-Portman-optimized-600x750.webp
""",
"Pastas": """
Emily in Paris|32000|Pasta corta con salsa boloñesa napolitana, toque de pesto, lomo salteado 100 g, parmesano|others/Pastas-Emily-in-paris-600x750.jpg
Mia Thermopolis|36000|Fettuccini en salsa Alfredo con tocineta, espinaca, pechuga de pollo 100 g, parmesano|products/Pastas-Mia-Thermopolis.jpg-600x750.jpeg
Pastas A Palé|39000|Pasta larga con lomo salteado 100 g, cebolla, champiñones, mix de quesos, ajo, parmesano|products/Pastas-Pastas-a-Pale.jpg-600x750.jpeg
Pastas al Pesto (vegetariana)|34000|Pasta larga con pesto, almendras, tomate cherry, champiñones y queso vegano|others/Pastas-pastas-al-pesto-600x750.jpg
""",
"Hot Dogs": """
Sweet Child|29000|Mermelada de tocineta, cheddar, jalapeños importados, salchicha alemana rellena de cheddar|products/Hot-Dogs-Sweet-Child-optimized-600x750.webp
Wonderwall|30000|Fondue de mozzarella, champiñones con tocineta, mix de quesos, salchicha rellena de cheddar|products/Hot-Dog-Wonderwall-optimized-600x750.webp
Red Hot Chilli|27000|Salchicha rellena de queso, chili con carne, cheddar derretido, perejil|products/Hot-Dog-Red-Hot-optimized-600x750.webp
Abba|34000|Salchicha rellena de cheddar, piña caramelizada, queso crema, lomito 70 g|products/Hot-Dog-ABBA-optimized-600x750.webp
""",
"Especiales de la Casa": """
Bullock|47000|Sándwich de masa madre con lomo de res, BBQ de chimichurri, mozzarella de búfala, pesto de rúcula, papas en cascos|products/Sandwich-Bullock-optimized-600x750.webp
Guapobell al Pastor|33000|Tres tacos con pollo al pastor, guacamole, pico de gallo, piña caramelizada, cebolla encurtida|others/Guapo-bell-al-pastor-600x750.jpg
Guapobell Pulled Pork|35000|Tres tacos con pulled pork caramelizado, adobo pibil, guacamole, pico de gallo, cilantro|others/Guapo-bell-pulled-pork-600x750.jpg
El Guapo|37000|Pan de masa madre, mozzarella, pollo desmenuzado 100 g, champiñones, maíz en salsa Alfredo, mermelada de tocineta, papas|products/EL-GUAPO-optimized-750x714.webp
Chicken Little|40000|Tenders de pollo crujientes con salsa de miel, ajo, sriracha, parmesano y papas a la francesa|others/Chicken-Little-600x750.jpg
""",
"Cócteles": """
Mojitos|29000|Soda, yerbabuena macerada, ron, lima y cereza o corozo|
Copa Sangria|25000|Vino merlot, ron, soda, manzana y sandía|products/DSC09181-optimized-500x750.webp
Espresso Martini|30000|Licor de café, espresso de prensa francesa, vodka, semillas de café|products/DSC02846-optimized-733x750.webp
Después de la Playa|31000|Almíbar de maracuyá casero, whisky escocés, Tajín y limón|
Mick Jagger|33000|Jack Daniel's Honey, mermelada de piña, Tajín, cáscara de piña flameada, syrup simple|
Combi Completa|70000|15 shots de ron saborizado en maracuyá, flor de jamaica y cereza|products/Shots-Combi-Completa-optimized-600x750.webp
Para Lxs Guapxs|37000|Tequila reposado, vodka, ron Cartavio y ginger|
Josefinas|38000|Tequila José Cuervo con sabores de lima, flor de jamaica, maracuyá, cereza, corozo, mandarina o lychee, limón y Tajín|
Cosmopolitan|29000|Vodka, arándanos, cereza y lima|
Gin & Tonic|32000|Ginebra, cítricos, pepino y romero|
Caipiroshka|30000|Vodka, limón macerado, naranja en espiral y piña flameada con Tajín|
Sangría Game|78000|Sangría para 4 o 5 personas con manzana verde, sandía, ron, vino tinto y soda|
Cher|30000|Smirnoff de tamarindo, flor de jamaica, sal y chamoy|products/DSC08988-optimized-500x750.webp
Roble Morado|32000|Aguardiente, almíbar de frutos rojos, limón y escarchado de Tajín con chamoy|
Cielo Tinto|39000|Tequila mezcal, lychee, vino tinto, caléndula comestible y toque de fuego|products/DSC05741-optimized-500x750.webp
Aperol Spritz|30000|Aperol, Cinzano y toque cítrico|products/DSC05332-optimized-500x750.webp
""",
"La Guapa x Bruder": """
Chocolate Stout (8,5%)|19000|Cerveza negra con notas de madera, caramelo y malta tostada|
Barley Wine (12%)|20000|Vino de cebada inglés con extracto de ciruela|
IPA Maracuyá (6,5%)|18000|IPA amarga y afrutada con extracto de maracuyá|
Piña & Durazno (5%)|17000|Malta de cebada y trigo con extracto de piña|
""",
"Cervezas": """
Artesanal Tres Cordilleras|14000|Rosada, negra y mulata|
BBC Cajicá Miel|14000||
Heineken|15000||
Club Colombia|13000||
Stella|14000||
Corona|15000||
Costeñita|7000||
Modelo|17000||
""",
"Sodas": """
Soda Mandarina|19000||others/Mandarina-600x750.jpg
Soda Lychee|17000||others/Lychee-600x750.jpg
Soda Cereza|19000||others/Cereza-600x750.jpg
Soda Maracuyá|21000||others/Maracuya-600x750.jpg
Soda Flor de Jamaica|23000||others/Flor-de-Jamaica-600x750.jpg
Soda Corozo|20000||others/Corozo-600x750.jpg
""",
"Otras bebidas": """
Limonada Natural|12000||
Limonada Yerbabuena|13000||
Limonada Cerezada|14000||
Limonada de Coco|15000||
Limonada de Vino|15000||
Limonada de Corozo|12000||
Limonada de Flor de Jamaica|16000||
Jugo de Maracuyá|14000||
Jugo de Corozo|12000||
Jugo de Mandarina|11000||
Agua Manantial|6000||
Quatro / Sprite (400 ml)|6000||
Coca-Cola Normal / Zero (400 ml)|8000||
Manzana / Colombiana (400 ml)|6000||
Soda Michelada|10000||
Ginger Michelado|12000||
Soda y Té Hatsu (400 ml)|13000|Sabores frambuesa, sandía, blanco y lila|
""",
"Shots": """
Shot Tequila, Flor de Jamaica|11000|Tequila, flor de jamaica y lima, escarchado|
Shot Ron, Cereza|10000|Ron, cereza y Tajín, escarchado|
Shot Whisky, Maracuyá|9000|Whisky, syrup de maracuyá y Tajín, escarchado|
""",
"Postres": """
Brownie de Milo|16000|Brownie de Milo con helado de vainilla y salsa de chocolate|
Copa de Helado de Vainilla|12000|Helado de vainilla con chispitas y salsa de chocolate o arequipe|
""",
}


def fetch_b64(rel):
    if not rel:
        return False
    try:
        req = urllib.request.Request(BASE + rel, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return base64.b64encode(r.read())
    except Exception as e:
        print("  ! imagen no disponible:", rel, e)
        return False


# --- logo de la empresa
logo = fetch_b64(LOGO)
if logo:
    env.company.logo = logo
    print("Logo actualizado")

Cat = env["pos.category"]
Prod = env["product.template"]
n_new = n_upd = 0

for seq, (cat_name, block) in enumerate(MENU.items(), start=1):
    cat = Cat.search([("name", "=", cat_name)], limit=1) or Cat.create({"name": cat_name, "sequence": seq})
    for line in block.strip().splitlines():
        name, price, desc, img = (line.split("|") + ["", "", "", ""])[:4]
        vals = {
            "name": name.strip(),
            "list_price": float(price),
            "description_sale": desc.strip() or False,
            "available_in_pos": True,
            "sale_ok": True,
            "type": "consu",
            "pos_categ_ids": [(6, 0, [cat.id])],
        }
        prod = Prod.search([("name", "=", vals["name"])], limit=1)
        if prod:
            prod.write(vals)
            n_upd += 1
        else:
            image = fetch_b64(img.strip())
            if image:
                vals["image_1920"] = image
            Prod.create(vals)
            n_new += 1
    env.cr.commit()
    print("OK", cat_name)

print("Productos creados: %d, actualizados: %d" % (n_new, n_upd))
