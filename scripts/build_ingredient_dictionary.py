#!/usr/bin/env python3
"""Generates data/ingredient_dictionary.json (our own free ingredient dictionary: en/es/fr/de/it/pt).
Edit the table below to add words, then re-run:  python scripts/build_ingredient_dictionary.py
Format per line: english | spanish | french | german | italian | portuguese   (use / between synonyms)"""
import json
from pathlib import Path

TABLE = """
chicken | pollo | poulet | hähnchen/huhn | pollo | frango/galinha
chicken breast | pechuga de pollo | blanc de poulet | hähnchenbrust | petto di pollo | peito de frango
beef | ternera/carne de vaca/res | boeuf/bœuf | rindfleisch | manzo | carne de vaca/vaca
ground beef | carne picada de ternera/carne molida | boeuf haché | hackfleisch/rinderhack | carne macinata di manzo | carne picada de vaca
pork | cerdo | porc | schweinefleisch | maiale | porco/carne de porco
lamb | cordero | agneau | lamm | agnello | borrego/cordeiro
turkey | pavo | dinde | pute/truthahn | tacchino | peru
duck | pato | canard | ente | anatra | pato
bacon | beicon/panceta | lard/bacon | speck/bacon | pancetta | bacon/toucinho
ham | jamón | jambon | schinken | prosciutto cotto | fiambre/presunto
sausage | salchicha | saucisse | wurst | salsiccia | salsicha
chorizo | chorizo | chorizo | chorizo | chorizo | chouriço
egg | huevo | oeuf/œuf | ei | uovo | ovo
eggs | huevos | oeufs/œufs | eier | uova | ovos
salmon | salmón | saumon | lachs | salmone | salmão
tuna | atún | thon | thunfisch | tonno | atum
cod | bacalao | morue/cabillaud | kabeljau | merluzzo/baccalà | bacalhau
shrimp | gamba/camarón | crevette | garnele | gambero | camarão
prawns | gambas/langostinos | crevettes/gambas | garnelen | gamberoni | gambas
mussels | mejillones | moules | muscheln/miesmuscheln | cozze | mexilhões
squid | calamar | calmar | tintenfisch/kalmar | calamaro | lula
anchovies | anchoas | anchois | sardellen | acciughe | anchovas
milk | leche | lait | milch | latte | leite
butter | mantequilla | beurre | butter | burro | manteiga
cream | nata | crème | sahne | panna | natas
double cream | nata para montar | crème fraîche épaisse/crème entière | schlagsahne | panna da montare | natas para bater
yogurt | yogur | yaourt/yogourt | joghurt | yogurt | iogurte
cheese | queso | fromage | käse | formaggio | queijo
cheddar | queso cheddar | cheddar | cheddar | cheddar | queijo cheddar
mozzarella | mozzarella | mozzarella | mozzarella | mozzarella | mozzarela
parmesan | parmesano | parmesan | parmesan | parmigiano | parmesão
feta | queso feta | feta | feta/fetakäse | feta | queijo feta
goat cheese | queso de cabra | fromage de chèvre | ziegenkäse | formaggio di capra | queijo de cabra
cream cheese | queso crema | fromage à la crème | frischkäse | formaggio spalmabile | queijo creme
tomato | tomate | tomate | tomate | pomodoro | tomate
onion | cebolla | oignon | zwiebel | cipolla | cebola
red onion | cebolla roja/cebolla morada | oignon rouge | rote zwiebel | cipolla rossa | cebola roxa
garlic | ajo | ail | knoblauch | aglio | alho
potato | patata/papa | pomme de terre | kartoffel | patata | batata
sweet potato | boniato/batata | patate douce | süßkartoffel | patata dolce | batata-doce
carrot | zanahoria | carotte | karotte/möhre | carota | cenoura
celery | apio | céleri | sellerie | sedano | aipo
cucumber | pepino | concombre | gurke | cetriolo | pepino
lettuce | lechuga | laitue | salat/kopfsalat | lattuga | alface
spinach | espinacas | épinards | spinat | spinaci | espinafres
broccoli | brócoli | brocoli | brokkoli | broccoli | brócolos
cauliflower | coliflor | chou-fleur | blumenkohl | cavolfiore | couve-flor
cabbage | repollo/col | chou | kohl/weißkohl | cavolo | couve/repolho
kale | col rizada | chou frisé | grünkohl | cavolo nero/cavolo riccio | couve galega
zucchini | calabacín | courgette | zucchini | zucchina | curgete/courgette
eggplant | berenjena | aubergine | aubergine | melanzana | beringela
bell pepper | pimiento | poivron | paprika/paprikaschote | peperone | pimento
chili | guindilla/chile | piment | chili | peperoncino | piri-piri/malagueta
mushrooms | champiñones/setas | champignons | pilze/champignons | funghi | cogumelos
peas | guisantes | petits pois/pois | erbsen | piselli | ervilhas
green beans | judías verdes | haricots verts | grüne bohnen | fagiolini | feijão verde
corn | maíz | maïs | mais | mais | milho
leek | puerro | poireau | lauch/porree | porro | alho-porro
asparagus | espárragos | asperges | spargel | asparagi | espargos
beetroot | remolacha | betterave | rote bete | barbabietola | beterraba
pumpkin | calabaza | citrouille/potiron | kürbis | zucca | abóbora
spring onion | cebolleta | oignon vert/ciboule | frühlingszwiebel | cipollotto | cebolinha
shallot | chalota/escalonia | échalote | schalotte | scalogno | chalota/echalota
ginger | jengibre | gingembre | ingwer | zenzero | gengibre
avocado | aguacate | avocat | avocado | avocado | abacate
lemon | limón | citron | zitrone | limone | limão
lime | lima | citron vert | limette | lime | lima
orange | naranja | orange | orange | arancia | laranja
apple | manzana | pomme | apfel | mela | maçã
banana | plátano/banana | banane | banane | banana | banana
strawberries | fresas | fraises | erdbeeren | fragole | morangos
blueberries | arándanos | myrtilles | heidelbeeren | mirtilli | mirtilos
raspberries | frambuesas | framboises | himbeeren | lamponi | framboesas
grapes | uvas | raisin | trauben | uva | uvas
pineapple | piña | ananas | ananas | ananas | ananás
mango | mango | mangue | mango | mango | manga
coconut | coco | noix de coco | kokosnuss | cocco | coco
raisins | pasas | raisins secs | rosinen | uvetta | passas
dates | dátiles | dattes | datteln | datteri | tâmaras
almonds | almendras | amandes | mandeln | mandorle | amêndoas
walnuts | nueces | noix | walnüsse | noci | nozes
peanuts | cacahuetes | cacahuètes | erdnüsse | arachidi | amendoins
hazelnuts | avellanas | noisettes | haselnüsse | nocciole | avelãs
pine nuts | piñones | pignons | pinienkerne | pinoli | pinhões
cashews | anacardos | noix de cajou | cashewkerne | anacardi | castanha de caju
rice | arroz | riz | reis | riso | arroz
pasta | pasta | pâtes | nudeln/pasta | pasta | massa
spaghetti | espaguetis | spaghetti | spaghetti | spaghetti | esparguete
noodles | fideos | nouilles | nudeln | noodles/tagliatelle | massa chinesa/noodles
bread | pan | pain | brot | pane | pão
breadcrumbs | pan rallado | chapelure | paniermehl | pangrattato | pão ralado
flour | harina | farine | mehl | farina | farinha
plain flour | harina de trigo | farine de blé/farine | weizenmehl | farina 00 | farinha de trigo
cornstarch | maicena/almidón de maíz | maïzena/fécule de maïs | speisestärke/maisstärke | amido di mais/maizena | amido de milho/maizena
oats | avena/copos de avena | flocons d'avoine | haferflocken | fiocchi d'avena | aveia/flocos de aveia
couscous | cuscús | couscous | couscous | couscous | cuscuz
quinoa | quinoa/quinua | quinoa | quinoa | quinoa | quinoa
lentils | lentejas | lentilles | linsen | lenticchie | lentilhas
chickpeas | garbanzos | pois chiches | kichererbsen | ceci | grão-de-bico
kidney beans | alubias rojas/judías rojas | haricots rouges | kidneybohnen | fagioli rossi | feijão encarnado/feijão vermelho
black beans | frijoles negros/alubias negras | haricots noirs | schwarze bohnen | fagioli neri | feijão preto
white beans | alubias blancas/judías blancas | haricots blancs | weiße bohnen | fagioli bianchi/cannellini | feijão branco
tofu | tofu | tofu | tofu | tofu | tofu
sugar | azúcar | sucre | zucker | zucchero | açúcar
brown sugar | azúcar moreno | sucre roux/cassonade | brauner zucker | zucchero di canna | açúcar mascavado/açúcar amarelo
icing sugar | azúcar glas | sucre glace | puderzucker | zucchero a velo | açúcar em pó/açúcar de confeiteiro
honey | miel | miel | honig | miele | mel
maple syrup | sirope de arce | sirop d'érable | ahornsirup | sciroppo d'acero | xarope de ácer
chocolate | chocolate | chocolat | schokolade | cioccolato | chocolate
cocoa | cacao | cacao | kakao | cacao | cacau
baking powder | levadura química/polvo de hornear | levure chimique | backpulver | lievito in polvere | fermento em pó
yeast | levadura | levure | hefe | lievito | fermento
baking soda | bicarbonato | bicarbonate de soude | natron/backnatron | bicarbonato di sodio | bicarbonato de sódio
vanilla | vainilla | vanille | vanille | vaniglia | baunilha
salt | sal | sel | salz | sale | sal
pepper | pimienta | poivre | pfeffer | pepe | pimenta
black pepper | pimienta negra | poivre noir | schwarzer pfeffer | pepe nero | pimenta preta
paprika | pimentón/paprika | paprika | paprika | paprica | colorau/paprica
smoked paprika | pimentón ahumado/pimentón de la vera | paprika fumé | geräuchertes paprikapulver | paprica affumicata | paprica fumada
cumin | comino | cumin | kreuzkümmel | cumino | cominho
turmeric | cúrcuma | curcuma | kurkuma | curcuma | açafrão-da-índia/curcuma
cinnamon | canela | cannelle | zimt | cannella | canela
nutmeg | nuez moscada | noix de muscade | muskatnuss | noce moscata | noz-moscada
cloves | clavo/clavos | clous de girofle | nelken | chiodi di garofano | cravo
saffron | azafrán | safran | safran | zafferano | açafrão
oregano | orégano | origan | oregano | origano | orégãos/oregãos
basil | albahaca | basilic | basilikum | basilico | manjericão
parsley | perejil | persil | petersilie | prezzemolo | salsa
coriander | cilantro/coriandro | coriandre | koriander | coriandolo | coentros
mint | menta/hierbabuena | menthe | minze | menta | hortelã
thyme | tomillo | thym | thymian | timo | tomilho
rosemary | romero | romarin | rosmarin | rosmarino | alecrim
bay leaf | laurel/hoja de laurel | laurier/feuille de laurier | lorbeerblatt | alloro | folha de louro/louro
dill | eneldo | aneth | dill | aneto | endro
sage | salvia | sauge | salbei | salvia | salva
olive oil | aceite de oliva | huile d'olive | olivenöl | olio d'oliva | azeite
vegetable oil | aceite vegetal | huile végétale | pflanzenöl | olio vegetale | óleo vegetal
sunflower oil | aceite de girasol | huile de tournesol | sonnenblumenöl | olio di semi di girasole | óleo de girassol
vinegar | vinagre | vinaigre | essig | aceto | vinagre
balsamic vinegar | vinagre balsámico | vinaigre balsamique | balsamico-essig | aceto balsamico | vinagre balsâmico
soy sauce | salsa de soja | sauce soja | sojasauce | salsa di soia | molho de soja
mustard | mostaza | moutarde | senf | senape | mostarda
mayonnaise | mayonesa | mayonnaise | mayonnaise | maionese | maionese
ketchup | kétchup | ketchup | ketchup | ketchup | ketchup
tomato paste | concentrado de tomate | concentré de tomate | tomatenmark | concentrato di pomodoro | concentrado de tomate
canned tomatoes | tomate en lata/tomate triturado | tomates en conserve/tomates pelées | dosentomaten | pomodori pelati | tomate pelado/tomate enlatado
coconut milk | leche de coco | lait de coco | kokosmilch | latte di cocco | leite de coco
stock | caldo | bouillon | brühe | brodo | caldo
chicken stock | caldo de pollo | bouillon de poulet | hühnerbrühe | brodo di pollo | caldo de galinha
water | agua | eau | wasser | acqua | água
wine | vino | vin | wein | vino | vinho
red wine | vino tinto | vin rouge | rotwein | vino rosso | vinho tinto
white wine | vino blanco | vin blanc | weißwein | vino bianco | vinho branco
beer | cerveza | bière | bier | birra | cerveja
olives | aceitunas | olives | oliven | olive | azeitonas
capers | alcaparras | câpres | kapern | capperi | alcaparras
pesto | pesto | pesto | pesto | pesto | pesto
tahini | tahini/tahina | tahini | tahini | tahina | tahini
hummus | hummus | houmous | hummus | hummus | húmus
puff pastry | hojaldre | pâte feuilletée | blätterteig | pasta sfoglia | massa folhada
tortilla | tortilla | tortilla | tortilla | tortilla | tortilha
""".strip()

AISLE_FOR = {}  # aisle is looked up from the aisle table at runtime


def main():
    concepts = []
    for line in TABLE.splitlines():
        parts = [p.strip() for p in line.split("|")]
        assert len(parts) == 6, line
        en, es, fr, de, it, pt = parts
        concepts.append({"en": en, "es": es.split("/"), "fr": fr.split("/"), "de": de.split("/"), "it": it.split("/"), "pt": pt.split("/")})
    out = Path(__file__).resolve().parent.parent / "data" / "ingredient_dictionary.json"
    json.dump(concepts, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"{len(concepts)} ingredients x 6 languages -> {out}")


if __name__ == "__main__":
    main()
