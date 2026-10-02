"""
Enriches the PaleoDB Taxa Atlas Registry with:
1. Authentic life restoration & paleoart reconstructions from life_images.json (replacing fossil/skeleton images)
2. Comprehensive ecological and paleontological profile details:
   - habitat_range: where the animal lived
   - geological_range: specific time period and chronological dates
   - diet_ecology: trophic level and ecological niche
   - morphology: physical traits, dimensions, and specialized adaptations
   - extinction_driver: evolutionary and environmental causes of extinction
"""
import json
from pathlib import Path

# Load life images
LIFE_IMAGES = {}
if Path("life_images.json").exists():
    with open("life_images.json", "r", encoding="utf-8") as f:
        LIFE_IMAGES = json.load(f)

# Comprehensive Paleontological & Ecological Profiles
ECOLOGY_DATA = {
    "PRAG-TAX-001": {
        "habitat_range": "Mammoth Steppe: continuous hyper-arid biome spanning Western Europe through Siberia, Beringia, and Northern North America.",
        "geological_range": "Late Pleistocene to mid-Holocene (~300,000 – 4,000 BP; Wrangel Island relict population survived until ~2000 BCE).",
        "diet_ecology": "Cold-adapted megaherbivore grazing primarily on high-protein steppe grasses, sedges, Artemisia, and willow shrubs.",
        "morphology": "Shoulder height 2.8–3.4 m; body mass 4–6 tonnes; dual-layer woolly coat with guard hairs up to 90 cm; spiraled tusks up to 4.2 m for sweeping snow.",
        "extinction_driver": "Rapid Holocene post-glacial warming causing peat-moss expansion and loss of nutrient-rich steppe-tundra, compounded by human hunting."
    },
    "PRAG-TAX-002": {
        "habitat_range": "Western, Central, and Eastern Europe, extending eastward into the Levant, Crimean Peninsula, Altai Mountains, and Uzbekistan.",
        "geological_range": "Middle to Late Pleistocene (~430,000 – 40,000 BP; last refugia in the Iberian Peninsula).",
        "diet_ecology": "Apex hominin hunter-gatherer specialized in close-range thrust-spear hunting of Pleistocene megafauna (mammoth, woolly rhino, bison, red deer).",
        "morphology": "Stocky cold-adapted stature (males ~165 cm, 78 kg); barrel-chested thorax; enlarged nasal chambers; heavy supraorbital tori; cranial capacity 1500–1600 cm³.",
        "extinction_driver": "Demographic assimilation and competitive exclusion by anatomically modern humans, exacerbated by Heinrich event climate instability."
    },
    "PRAG-TAX-003": {
        "habitat_range": "Eurasian steppe corridor, extending across Bronze Age trade routes, the Roman Empire, Mediterranean littoral, and medieval Europe.",
        "geological_range": "Late Neolithic / Bronze Age (~5,000 BP) through the Black Death (1346–1353 CE) and historical pandemics into modern endemic foci.",
        "diet_ecology": "Zoonotic Gram-negative facultative intracellular pathogen cycling between wild rodent hosts (marmots, gerbils) and flea vectors (Xenopsylla cheopis).",
        "morphology": "Non-motile encapsulated coccobacillus; length 1–2 μm; carries pPCP1, pCD1, and pMT1 virulence plasmids encoding Yop effectors and the Pla protease.",
        "extinction_driver": "Historical pandemic attenuation through host genetic selection (CCR5-Δ32), rodent population depletion, quarantine cordons, and modern antibiotics."
    },
    "PRAG-TAX-004": {
        "habitat_range": "North America (from Alberta to Mexico) and northern South America; extraordinarily abundant in the asphaltic Rancho La Brea tar seeps.",
        "geological_range": "Late Pleistocene (Rancholabrean land mammal age, ~125,000 – 9,500 BP).",
        "diet_ecology": "Hypercarnivorous pack predator targeting large ungulates including Western horses (Equus occidentalis), bison, and juvenile ground sloths.",
        "morphology": "Head-body length ~1.5 m; estimated weight 60–75 kg; heavy skull with bone-cracking carnassials, massive zygomatic arches, and short sturdy limbs.",
        "extinction_driver": "Abrupt prey collapse following the Quaternary extinction of North American megafauna, combined with complete evolutionary isolation from Canis lupus."
    },
    "PRAG-TAX-005": {
        "habitat_range": "Eurasian steppe-tundra from the British Isles across Central Europe and Siberia to the Yukon territory in Northwestern North America.",
        "geological_range": "Middle to Late Pleistocene (~600,000 – 13,000 BP).",
        "diet_ecology": "Apex predatory felid stalking reindeer, Pleistocene wild horses, juvenile steppe bison, and cave bear cubs in open sub-arctic plains.",
        "morphology": "Shoulder height ~1.2 m; head-body length 2.1 m; weight 300–360 kg; 10% larger than modern lions; lack of pronounced male mane based on Upper Paleolithic cave art.",
        "extinction_driver": "Rapid collapse of specialized tundra-steppe prey populations (reindeer and bison) during Bølling-Allerød warming and post-glacial forest expansion."
    },
    "PRAG-TAX-006": {
        "habitat_range": "Holarctic steppe-tundra belt extending across Great Britain, Northern Eurasia, Siberia, Alaska, and the Canadian Yukon.",
        "geological_range": "Middle to Late Pleistocene (~1.5 Ma – 5,400 BP; northern Yukon relict populations survived into the mid-Holocene).",
        "diet_ecology": "Cold-tolerant bulk grazer consuming C3 grasses, rushes, sedges, and dwarf birch in mosaic permafrost grasslands.",
        "morphology": "Shoulder height over 2 m; weight exceeding 1,000 kg; massive crescent horn cores with a tip-to-tip span over 1 meter; pronounced muscular thoracic hump.",
        "extinction_driver": "Replacement of arid mammoth steppe by moist shrub-tundra and taiga; introgressive hybridization with ancient taurine cattle yielded the European wisent."
    },
    "PRAG-TAX-007": {
        "habitat_range": "Central, High-Altitude, and Eastern Asia; verified fossil occurrences at Denisova Cave (Altai Krai) and Baishiya Karst Cave (Tibetan Plateau).",
        "geological_range": "Middle to Late Pleistocene (~300,000 – 30,000 BP).",
        "diet_ecology": "Archaic hunter-gatherer exploiting alpine ungulates (bharal, yak, woolly rhino) under extreme hypoxia and sub-zero montane conditions.",
        "morphology": "Massive robust molars with complex three-rooted anatomy; wide cranial vault; EPAS1 high-altitude hypoxia adaptations introgressed into modern Tibetans.",
        "extinction_driver": "Demographic absorption and gene flow into encroaching modern human populations, leaving 4–6% genetic heritage in modern Australo-Melanesians."
    },
    "PRAG-TAX-008": {
        "habitat_range": "Continental Australia, New Guinea, and historically restricted to the dense temperate rainforests and button grass plains of Tasmania.",
        "geological_range": "Pliocene to Holocene (~4 Ma – 1936 CE; last captive individual died at Beaumaris Zoo in Hobart).",
        "diet_ecology": "Solitary nocturnal apex marsupial predator hunting pademelons, Bennett's wallabies, bettongs, and ground-nesting seabirds by endurance tracking.",
        "morphology": "Shoulder height ~60 cm; weight 15–30 kg; 15–20 dark transverse dorsal stripes; semi-rigid tail; backward-opening pouch; remarkable 80-degree jaw gape.",
        "extinction_driver": "Intensive government-funded agricultural bounty eradication (1888–1909), habitat clearance, competition with feral dogs, and disease outbreaks."
    },
    "PRAG-TAX-009": {
        "habitat_range": "Northern Eurasia permafrost zone, from the Iberian Peninsula and Britain eastward across Siberia to the Chukchi Peninsula.",
        "geological_range": "Middle to Late Pleistocene (~350,000 – 14,000 BP).",
        "diet_ecology": "Low-slung specialist grazer utilizing its keeled anterior horn to sweep snow aside to graze on subnivean grasses, mosses, and sedges.",
        "morphology": "Body length 3.7 m; shoulder height ~2 m; weight 1.8–2.7 tonnes; massive anterior nasal horn up to 1.35 m; dense double-layered reddish woolly fleece.",
        "extinction_driver": "Sudden Bølling-Allerød warming (~14,000 BP) causing heavy snowfall regimes that immobilized the short-legged rhino and suffocated steppe vegetation."
    },
    "PRAG-TAX-010": {
        "habitat_range": "Americas: widespread throughout North America (abundant at Rancho La Brea) and western South America in open woodland and scrub margins.",
        "geological_range": "Early to Late Pleistocene (Blancan to Rancholabrean, ~1.6 Ma – 10,000 BP).",
        "diet_ecology": "Ambush apex machairodontine predator targeting bison, camelops, Western horses, and juvenile mastodons/mammoths.",
        "morphology": "Shoulder height 1.0 m; mass 160–280 kg; recurved maxillary saber canines up to 28 cm; massively hypertrophied cervical vertebrae and forelimb adductor muscles.",
        "extinction_driver": "Abrupt demise of all large herbivorous megafauna prey at the Younger Dryas boundary, compounded by human hunter colonization."
    },
    "PRAG-TAX-011": {
        "habitat_range": "Endemic exclusively to the dry coastal lowlands and subtropical palm forests of Mauritius in the western Indian Ocean.",
        "geological_range": "Holocene (~10,000 BP – 1662 CE; confirmed last reliable observation in offshore islets).",
        "diet_ecology": "Flightless ground frugivore and seed predator feeding on fallen tambalacoque (dodo tree) fruits, palm nuts, berries, and bulbous roots.",
        "morphology": "Standing height ~1 m; weight 10–18 kg; blue-gray plumage; heavy hooked bill with yellow sheath; rudimentary wings; stout yellow feet with robust claws.",
        "extinction_driver": "Complete devastation of ground nests by introduced invasive mammals (pigs, macaque monkeys, rats, dogs) and deforestation by Dutch settlers."
    },
    "PRAG-TAX-012": {
        "habitat_range": "Eastern and Central North America; nesting in mixed deciduous forests of the Great Lakes and wintering across the Southern United States.",
        "geological_range": "Pliocene to early 20th century (~3 Ma – 1914 CE; Martha, the last survivor, died at Cincinnati Zoo).",
        "diet_ecology": "Obligate nomadic forest granivore foraging in hyper-dense flocks of billions, consuming beech mast, acorns, chestnuts, berries, and cultivated grain.",
        "morphology": "Total length 39–42 cm; weight ~340 g; iridescent metallic neck plumage; long pointed tail; exceptional aerodynamic flight reaching speeds over 100 km/h.",
        "extinction_driver": "Unrestricted industrial market hunting facilitated by telegraph tracking and railroad transport, coupled with mass clearing of eastern hardwood forests."
    },
    "PRAG-TAX-013": {
        "habitat_range": "Southern Cone of South America: Argentine Pampas and Patagonian shrub-steppe (famed preservation in Cueva del Milodón, Chile).",
        "geological_range": "Late Pleistocene to early Holocene (~1.8 Ma – 10,200 BP).",
        "diet_ecology": "Bulk ground herbivore grazing on tough Patagonian tussock grasses, sedges, and thorny sub-Antarctic scrub.",
        "morphology": "Total length ~3 m; estimated weight 1.0–2.0 tonnes; semi-fossorial robust limbs; subdermal osteoderm beads embedded in thick leather; dense coarse yellowish coat.",
        "extinction_driver": "Synergistic impact of post-glacial aridification across the Patagonian plains and specialized hunting pressure by early Clovis-era Paleo-Indians."
    },
    "PRAG-TAX-014": {
        "habitat_range": "North America, from the high Arctic of Alaska and the Yukon south across the continental United States into the central Mexican highlands.",
        "geological_range": "Middle to Late Pleistocene (~1.8 Ma – 11,000 BP).",
        "diet_ecology": "Hypercarnivore and apex scavenger capable of kleptoparasitizing dire wolf and sabertooth cat kills, tracking horses, caribou, and bison across open plains.",
        "morphology": "Shoulder height on all fours 1.5–1.8 m; erect height 3.7 m; body mass up to 1,000 kg; disproportionately long cursorial limbs, broad muzzle, and deep nasal cavity.",
        "extinction_driver": "Collapse of megaherbivore carrion availability, intense resource competition from expanding brown bears (Ursus arctos), and human predation."
    },
    "PRAG-TAX-015": {
        "habitat_range": "Global pandemic epicenter radiating from military camps across Europe and North America to the Pacific Islands and remote Arctic permafrost villages.",
        "geological_range": "Modern archival paleovirological aRNA (1918–1920 CE pandemic, sequenced from permafrost victim lung tissue).",
        "diet_ecology": "Avian-origin H1N1 influenza A virus causing hyper-induction of pro-inflammatory cytokines (cytokine storm) and acute hemorrhagic pulmonary edema.",
        "morphology": "Pleomorphic spherical virion 80–120 nm in diameter; enveloped host-derived lipid bilayer; segmented negative-sense ssRNA genome; HA and NA surface glycoproteins.",
        "extinction_driver": "Depletion of immunologically naive human hosts, herd immunity, and rapid genetic drift toward less lethal seasonal endemic H1N1 descendents."
    },
    "PRAG-TAX-016": {
        "habitat_range": "South American Pampas, Gran Chaco, and southern mesopotamian savannas of Argentina, Uruguay, and Southern Brazil.",
        "geological_range": "Middle to Late Pleistocene (~400,000 – 11,000 BP).",
        "diet_ecology": "Low-slung specialist grazer feeding on abrasive silica-rich savanna grasses, dry forbs, and riparian sedges.",
        "morphology": "Length 3.6 m; height 1.5 m; mass 1.4–2.0 tonnes; massive dome-like fused osteoderm carapace; flexible tail sheath terminating in a spiked, bone-mace caudal club.",
        "extinction_driver": "Climatic restructuring of Pampean wetlands at the Pleistocene-Holocene transition, coupled with targeted ambush hunting by early South American hunters."
    },
    "PRAG-TAX-017": {
        "habitat_range": "South American continent: Pampas grasslands, Chaco plains, and Patagonian river basins (first identified by Charles Darwin during the Beagle voyage).",
        "geological_range": "Late Pliocene to Late Pleistocene (~2.5 Ma – 11,000 BP).",
        "diet_ecology": "Semi-aquatic or mixed-feeding notoungulate grazing on tough grasses, marshland vegetation, and semi-submerged riparian foliage.",
        "morphology": "Length 2.7 m; shoulder height 1.5 m; body mass ~1.5 tonnes; barrel-shaped torso; elevated dorsal nostrils; continuously growing hypsodont chisel incisors.",
        "extinction_driver": "Prolonged aridification of South American river valley ecosystems combined with human hunting of large, slow-moving notoungulate populations."
    },
    "PRAG-TAX-018": {
        "habitat_range": "South Island of New Zealand: lowland podocarp-broadleaf forests, subalpine shrublands, and coastal dunelands.",
        "geological_range": "Late Pleistocene to Holocene (~2 Ma – ~1440 CE; completely exterminated within 100–150 years of Māori settlement).",
        "diet_ecology": "Primary avian megaherbivore browsing on tough twigs, subalpine herbs, fallen fruits, and beech foliage using heavy gizzard stones (gastroliths).",
        "morphology": "Standing height up to 3.6 m; weight up to 250 kg; extreme reverse sexual dimorphism (females twice as massive as males); total loss of all wing bones and pectoral girdle.",
        "extinction_driver": "Rapid, systematic overhunting by Polynesian settlers, widespread clearance of native forests through anthropogenic burning, and dog predation of moa nests."
    }
}

# Update frontend and backend registries
targets = [
    Path("frontend/client/src/lib/paleo_atlas_registry.json"),
    Path("backend/data/paleo_atlas_registry.json")
]

for p in targets:
    if not p.exists():
        continue
    with open(p, "r", encoding="utf-8") as f:
        registry = json.load(f)
    
    updated_count = 0
    for entry in registry:
        tid = entry["tax_id"]
        # Update image from life_images.json
        if tid in LIFE_IMAGES:
            entry["image_url"] = LIFE_IMAGES[tid]["url"]
            entry["image_caption"] = LIFE_IMAGES[tid]["caption"]
        # Update ecological & paleontological fields
        if tid in ECOLOGY_DATA:
            entry.update(ECOLOGY_DATA[tid])
            updated_count += 1
            
    with open(p, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    print(f"Updated {updated_count} taxa in {p}")
