"""
NICE CLASSIFICATION DATABASE — TMEP Chapter 1400 (Nov 2025 Edition)
Full 45-class database with keywords, descriptions, and validation data.
Based on the 12th Edition of the Nice Agreement (current as of Nov 2025).
"""

# ─────────────────────────────────────────────────────────────────────────────
# COMPLETE NICE CLASSIFICATION — ALL 45 CLASSES
# ─────────────────────────────────────────────────────────────────────────────

NICE_CLASSES = {
    # ── GOODS (Classes 1–34) ──────────────────────────────────────────────────
    1: {
        "category": "GOODS",
        "title": "Chemicals",
        "description": "Chemicals for industry, science, photography; unprocessed artificial resins; "
                       "unprocessed plastics; fertilizers; fire extinguishing compositions; "
                       "tempering and soldering preparations; chemical substances for preserving foodstuffs; "
                       "tanning substances; adhesives for industry.",
        "keywords": [
            "chemical", "chemicals", "adhesive", "fertilizer", "resin", "solvent",
            "catalyst", "reagent", "polymer", "plastic raw material", "glue industrial",
            "photographic chemical", "tanning", "fire extinguishing", "flux"
        ]
    },
    2: {
        "category": "GOODS",
        "title": "Paints and Coatings",
        "description": "Paints, varnishes, lacquers; preservatives against rust and against deterioration "
                       "of wood; colorants, dyes; inks for printing; raw natural resins; "
                       "metals in foil and powder form for use in painting, decorating, printing.",
        "keywords": [
            "paint", "varnish", "lacquer", "dye", "colorant", "pigment", "ink printing",
            "rust prevention", "coating", "primer", "stain wood", "enamel", "glaze"
        ]
    },
    3: {
        "category": "GOODS",
        "title": "Cosmetics and Cleaning Products",
        "description": "Non-medicated cosmetics and toiletry preparations; non-medicated dentifrices; "
                       "perfumery, essential oils; bleaching preparations; cleaning, polishing, "
                       "scouring and abrasive preparations.",
        "keywords": [
            "cosmetic", "shampoo", "soap", "perfume", "fragrance", "lotion", "cream skincare",
            "toothpaste", "deodorant", "makeup", "lipstick", "foundation", "cleanser",
            "detergent", "bleach", "polish", "conditioner hair", "sunscreen", "moisturizer",
            "hair care", "body wash", "face wash", "cologne", "essential oil", "nail polish"
        ]
    },
    4: {
        "category": "GOODS",
        "title": "Lubricants and Fuels",
        "description": "Industrial oils and greases; lubricants; dust absorbing, wetting and binding "
                       "compositions; fuels and illuminants; candles and wicks for lighting.",
        "keywords": [
            "lubricant", "oil industrial", "grease", "fuel", "petrol", "gasoline", "diesel",
            "candle", "wax", "kerosene", "biofuel", "engine oil", "motor oil"
        ]
    },
    5: {
        "category": "GOODS",
        "title": "Pharmaceuticals and Medical Preparations",
        "description": "Pharmaceuticals, medical and veterinary preparations; sanitary preparations "
                       "for medical purposes; dietetic food and substances adapted for medical use; "
                       "food for babies; dietary supplements; plasters, materials for dressings; "
                       "material for stopping teeth; disinfectants; preparations for destroying "
                       "vermin; fungicides, herbicides.",
        "keywords": [
            "pharmaceutical", "drug", "medicine", "medication", "supplement", "vitamin",
            "antibiotic", "vaccine", "disinfectant", "bandage", "plaster medical",
            "baby food", "dietary supplement", "herbicide", "pesticide", "fungicide",
            "veterinary", "dental filling", "antiseptic", "laxative", "analgesic"
        ]
    },
    6: {
        "category": "GOODS",
        "title": "Metal Goods",
        "description": "Common metals and their alloys; ores; metal building and construction materials; "
                       "transportable buildings of metal; non-electric cables and wires of common metal; "
                       "small items of metal hardware; metal containers for storage or transport; safes.",
        "keywords": [
            "metal", "steel", "iron", "aluminum", "copper", "wire metal", "cable metal",
            "safe", "lock metal", "nail", "screw", "bolt", "metal container", "metal pipe",
            "metal hardware", "metal building", "chain", "metal fitting"
        ]
    },
    7: {
        "category": "GOODS",
        "title": "Machinery",
        "description": "Machines, machine tools, power-operated tools; motors and engines (not for "
                       "land vehicles); machine coupling and transmission components; "
                       "agricultural implements other than hand-operated; incubators for eggs; "
                       "automatic vending machines.",
        "keywords": [
            "machine", "machinery", "engine", "motor industrial", "pump", "compressor",
            "turbine", "robot industrial", "tool power", "generator", "vending machine",
            "conveyor", "agricultural machine", "drill machine", "lathe"
        ]
    },
    8: {
        "category": "GOODS",
        "title": "Hand Tools",
        "description": "Hand tools and implements (hand-operated); cutlery; side arms, except firearms; "
                       "razors.",
        "keywords": [
            "hand tool", "knife", "fork", "spoon", "cutlery", "razor", "scissors",
            "hammer", "screwdriver manual", "saw hand", "plier", "wrench", "chisel",
            "sword", "blade", "shears"
        ]
    },
    9: {
        "category": "GOODS",
        "title": "Scientific and Electronic Apparatus",
        "description": "Scientific, research, navigation, surveying, photographic, cinematographic, "
                       "audiovisual, optical, weighing, measuring, signalling, detecting, testing, "
                       "inspecting, life-saving and teaching apparatus and instruments; "
                       "apparatus and instruments for conducting, switching, transforming, accumulating, "
                       "regulating or controlling the distribution or use of electricity; "
                       "computers; computer hardware and software; "
                       "audio and video recordings; downloadable digital content.",
        "keywords": [
            "software", "computer software", "app", "application", "mobile app",
            "computer", "laptop", "tablet", "smartphone", "hardware", "electronic",
            "downloadable", "digital content", "video game", "game software",
            "operating system", "firmware", "database software", "saas", "platform software",
            "camera", "telephone", "headphone", "speaker electronic", "television",
            "monitor", "server", "semiconductor", "circuit", "battery", "charger",
            "gps", "navigation device", "scanner", "printer hardware", "calculator",
            "data storage", "usb", "hard drive", "cloud software", "artificial intelligence software",
            "machine learning software", "recorded music", "downloadable music", "ebook",
            "downloadable video", "streaming software", "vr headset", "drone", "robot"
        ]
    },
    10: {
        "category": "GOODS",
        "title": "Medical Devices",
        "description": "Surgical, medical, dental and veterinary apparatus and instruments; "
                       "artificial limbs, eyes and teeth; orthopedic articles; suture materials; "
                       "therapeutic and assistive devices adapted for persons with disabilities; "
                       "massage apparatus; apparatus, devices and articles for nursing infants; "
                       "sexual activity apparatus, devices and articles.",
        "keywords": [
            "medical device", "surgical instrument", "dental instrument", "prosthetic",
            "wheelchair", "orthopedic", "hearing aid", "stethoscope", "syringe",
            "catheter", "implant", "pacemaker", "crutch", "bandage medical device",
            "thermometer medical", "blood pressure monitor", "massage device"
        ]
    },
    11: {
        "category": "GOODS",
        "title": "Environmental Control Apparatus",
        "description": "Apparatus and installations for lighting, heating, cooling, steam generating, "
                       "cooking, drying, ventilating, water supply and sanitary purposes.",
        "keywords": [
            "light fixture", "lamp", "bulb", "air conditioner", "heater", "furnace",
            "refrigerator", "freezer", "oven", "microwave", "dishwasher", "washer",
            "dryer", "ventilation", "air purifier", "water filter", "toilet", "faucet",
            "shower", "boiler", "heat pump", "hvac", "stove", "cooking appliance"
        ]
    },
    12: {
        "category": "GOODS",
        "title": "Vehicles",
        "description": "Vehicles; apparatus for locomotion by land, air or water.",
        "keywords": [
            "vehicle", "car", "automobile", "truck", "motorcycle", "bicycle", "boat",
            "ship", "aircraft", "airplane", "helicopter", "electric vehicle", "ev",
            "scooter", "train", "bus", "trailer", "wheel vehicle", "tire", "car part"
        ]
    },
    13: {
        "category": "GOODS",
        "title": "Firearms",
        "description": "Firearms; ammunition and projectiles; explosives; fireworks.",
        "keywords": [
            "firearm", "gun", "pistol", "rifle", "ammunition", "bullet", "explosive",
            "firework", "grenade", "weapon", "shotgun"
        ]
    },
    14: {
        "category": "GOODS",
        "title": "Jewelry and Timepieces",
        "description": "Precious metals and their alloys; jewellery, precious and semi-precious stones; "
                       "horological and chronometric instruments.",
        "keywords": [
            "jewelry", "jewellery", "ring", "necklace", "bracelet", "earring", "watch",
            "clock", "gold", "silver precious", "diamond", "gemstone", "timepiece",
            "brooch", "pendant", "charm jewelry"
        ]
    },
    15: {
        "category": "GOODS",
        "title": "Musical Instruments",
        "description": "Musical instruments; music stands and music holders; "
                       "conducting batons.",
        "keywords": [
            "musical instrument", "guitar", "piano", "violin", "drum", "trumpet",
            "flute", "keyboard instrument", "saxophone", "bass", "instrument accessory"
        ]
    },
    16: {
        "category": "GOODS",
        "title": "Paper and Printed Matter",
        "description": "Paper and cardboard; printed matter; bookbinding material; "
                       "photographs; stationery and office requisites; "
                       "adhesives for stationery or household purposes; "
                       "drawing materials and materials for artists; paintbrushes; "
                       "instructional and teaching materials.",
        "keywords": [
            "paper", "printed matter", "book", "magazine", "newspaper", "brochure",
            "stationery", "pen", "pencil", "notebook", "envelope", "cardboard",
            "photo print", "poster printed", "greeting card", "label printed",
            "manual printed", "instruction book", "catalog printed", "pamphlet"
        ]
    },
    17: {
        "category": "GOODS",
        "title": "Rubber and Plastic Products",
        "description": "Unprocessed and semi-processed rubber, gutta-percha, gum, asbestos, mica "
                       "and substitutes for all these materials; "
                       "plastics and resins in extruded form for use in manufacture; "
                       "packing, stopping and insulating materials; "
                       "flexible pipes, tubes and hoses.",
        "keywords": [
            "rubber", "gasket", "seal rubber", "insulation", "hose", "tube rubber",
            "plastic semi-processed", "foam insulation", "tape insulating"
        ]
    },
    18: {
        "category": "GOODS",
        "title": "Leather Goods",
        "description": "Leather and imitations of leather; animal skins and hides; "
                       "luggage and carrying bags; umbrellas and parasols; "
                       "walking sticks; whips, harness and saddlery; collars, leashes and clothing for animals.",
        "keywords": [
            "leather", "bag", "handbag", "purse", "wallet", "luggage", "suitcase",
            "backpack", "umbrella", "tote bag", "briefcase", "belt leather", "harness",
            "saddle", "pet collar", "leash"
        ]
    },
    19: {
        "category": "GOODS",
        "title": "Building Materials",
        "description": "Building and construction materials, not of metal; "
                       "rigid pipes for building; asphalt, pitch, tar and bitumen; "
                       "transportable buildings, not of metal; "
                       "monuments, not of metal.",
        "keywords": [
            "building material", "cement", "concrete", "brick", "tile", "wood building",
            "glass building", "stone", "gravel", "asphalt", "pipe non-metal", "lumber"
        ]
    },
    20: {
        "category": "GOODS",
        "title": "Furniture",
        "description": "Furniture, mirrors, picture frames; containers of plastic or wood for storage "
                       "or transport; unworked or semi-worked bone, horn, whalebone or mother-of-pearl; "
                       "shells; meerschaum; yellow amber.",
        "keywords": [
            "furniture", "chair", "table", "desk", "bed", "sofa", "couch", "mirror",
            "shelf", "cabinet", "wardrobe", "mattress", "pillow", "cushion", "frame picture"
        ]
    },
    21: {
        "category": "GOODS",
        "title": "Household Utensils",
        "description": "Household or kitchen utensils and containers; cookware and tableware; "
                       "combs and sponges; brushes; brush-making materials; articles for cleaning purposes; "
                       "unworked or semi-worked glass (except building glass); glassware, porcelain and earthenware.",
        "keywords": [
            "kitchen utensil", "pot", "pan", "cup", "mug", "plate", "bowl", "glass tableware",
            "cutlery set", "brush household", "comb", "sponge", "broom", "bucket",
            "storage container household", "vase", "canteen", "flask"
        ]
    },
    22: {
        "category": "GOODS",
        "title": "Cordage and Textile Fibers",
        "description": "Ropes and string; nets; tents and tarpaulins; awnings of textile or synthetic materials; "
                       "sails; sacks for the transport and storage of materials in bulk; "
                       "padding, cushioning and stuffing materials; raw fibrous textile materials and substitutes.",
        "keywords": [
            "rope", "string", "net", "tent", "tarpaulin", "sack", "padding stuffing",
            "fiber textile raw", "twine", "cord", "canvas"
        ]
    },
    23: {
        "category": "GOODS",
        "title": "Yarns and Threads",
        "description": "Yarns and threads for textile use.",
        "keywords": [
            "yarn", "thread", "sewing thread", "knitting yarn", "embroidery thread"
        ]
    },
    24: {
        "category": "GOODS",
        "title": "Textiles",
        "description": "Textiles and substitutes for textiles; household linen; curtains of textile or plastic.",
        "keywords": [
            "textile", "fabric", "cloth", "linen", "bedsheet", "towel", "curtain",
            "blanket", "duvet", "tablecloth", "upholstery fabric"
        ]
    },
    25: {
        "category": "GOODS",
        "title": "Clothing and Footwear",
        "description": "Clothing, footwear, headgear.",
        "keywords": [
            "clothing", "clothes", "apparel", "shirt", "t-shirt", "pants", "jeans",
            "dress", "skirt", "jacket", "coat", "suit", "shoes", "boots", "sneakers",
            "sandals", "hat", "cap", "gloves", "socks", "underwear", "sportswear",
            "swimwear", "uniform", "footwear", "headgear", "fashion apparel"
        ]
    },
    26: {
        "category": "GOODS",
        "title": "Lace and Embroidery",
        "description": "Lace, braid and embroidery, and haberdashery ribbons and bows; "
                       "buttons, hooks and eyes, pins and needles; "
                       "artificial flowers; hair decorations; false hair.",
        "keywords": [
            "lace", "embroidery", "button", "needle", "pin sewing", "ribbon",
            "artificial flower", "hair accessory", "bow ribbon", "zipper"
        ]
    },
    27: {
        "category": "GOODS",
        "title": "Floor Coverings",
        "description": "Carpets, rugs, mats and matting, linoleum and other materials for covering "
                       "existing floors; wall hangings, not of textile.",
        "keywords": [
            "carpet", "rug", "mat", "flooring", "linoleum", "wall hanging"
        ]
    },
    28: {
        "category": "GOODS",
        "title": "Games and Sporting Goods",
        "description": "Games, toys and playthings; video game apparatus; "
                       "gymnastic and sporting articles; "
                       "decorations for Christmas trees.",
        "keywords": [
            "toy", "game board", "puzzle", "doll", "sport equipment", "gym equipment",
            "football", "basketball", "tennis racket", "golf club", "ski", "snowboard",
            "christmas decoration", "playing card", "chess", "game controller hardware",
            "fishing equipment", "hunting equipment non-firearm"
        ]
    },
    29: {
        "category": "GOODS",
        "title": "Meat and Processed Foods",
        "description": "Meat, fish, poultry and game; meat extracts; preserved, frozen, dried and cooked "
                       "fruits and vegetables; jellies, jams, compotes; eggs; milk, cheese, butter, "
                       "yogurt and other milk products; oils and fats for food.",
        "keywords": [
            "meat", "fish food", "poultry", "cheese", "butter", "milk", "yogurt",
            "egg", "vegetable preserved", "fruit preserved", "jam", "jelly food",
            "frozen food", "dairy", "oil food", "margarine", "broth", "soup canned"
        ]
    },
    30: {
        "category": "GOODS",
        "title": "Coffee and Staple Foods",
        "description": "Coffee, tea, cocoa and artificial coffee; rice, pasta and noodles; "
                       "tapioca and sago; flour and preparations made from cereals; "
                       "bread, pastries and confectionery; chocolate; ice cream, sorbets and other edible ices; "
                       "sugar, honey, treacle; yeast, baking-powder; salt, seasonings, spices, preserved herbs; "
                       "vinegar, sauces and other condiments; ice.",
        "keywords": [
            "coffee", "tea", "cocoa", "chocolate", "sugar", "flour", "bread", "cake",
            "pastry", "cookie", "candy", "ice cream", "pasta", "noodle", "rice",
            "spice", "seasoning", "sauce", "condiment", "vinegar", "honey", "salt"
        ]
    },
    31: {
        "category": "GOODS",
        "title": "Agricultural Products",
        "description": "Raw and unprocessed agricultural, aquacultural, horticultural and forestry products; "
                       "raw and unprocessed grains and seeds; fresh fruits and vegetables, fresh herbs; "
                       "natural plants and flowers; bulbs, seedlings and seeds for planting; "
                       "live animals; foodstuffs and beverages for animals; malt.",
        "keywords": [
            "fresh fruit", "fresh vegetable", "plant", "flower", "seed", "live animal",
            "pet food", "animal feed", "grain", "unprocessed agricultural", "malt", "bulb plant"
        ]
    },
    32: {
        "category": "GOODS",
        "title": "Beer and Non-Alcoholic Beverages",
        "description": "Beer; non-alcoholic beverages; mineral and aerated waters; "
                       "fruit beverages and fruit juices; syrups and other non-alcoholic preparations "
                       "for making beverages.",
        "keywords": [
            "beer", "non-alcoholic beverage", "soft drink", "soda", "juice", "water bottled",
            "energy drink", "sports drink", "lemonade", "cola", "syrup beverage"
        ]
    },
    33: {
        "category": "GOODS",
        "title": "Alcoholic Beverages",
        "description": "Alcoholic beverages, except beers; alcoholic preparations for making beverages.",
        "keywords": [
            "wine", "spirits", "whiskey", "vodka", "rum", "gin", "liquor", "alcohol",
            "champagne", "brandy", "tequila", "cocktail preparation"
        ]
    },
    34: {
        "category": "GOODS",
        "title": "Tobacco Products",
        "description": "Tobacco and tobacco substitutes; cigarettes and cigars; "
                       "electronic cigarettes and oral vaporizers for smokers; "
                       "smokers' articles; matches.",
        "keywords": [
            "tobacco", "cigarette", "cigar", "vape", "e-cigarette", "match", "lighter",
            "pipe smoking", "nicotine", "rolling paper"
        ]
    },

    # ── SERVICES (Classes 35–45) ──────────────────────────────────────────────
    35: {
        "category": "SERVICES",
        "title": "Advertising and Business Services",
        "description": "Advertising; business management; business administration; "
                       "office functions; online marketplaces for buyers and sellers; "
                       "import-export agency services.",
        "keywords": [
            "advertising", "marketing", "business management", "business consulting",
            "public relations", "recruitment", "staffing", "retail store", "online marketplace",
            "import export", "business administration", "telemarketing", "seo",
            "market research", "business strategy", "ecommerce platform", "franchise"
        ]
    },
    36: {
        "category": "SERVICES",
        "title": "Insurance and Financial Services",
        "description": "Insurance; financial affairs; monetary affairs; real estate affairs.",
        "keywords": [
            "insurance", "financial service", "banking", "investment", "real estate",
            "mortgage", "loan", "credit", "fund management", "stock exchange",
            "cryptocurrency", "fintech", "payment service", "money transfer",
            "tax service", "accounting financial", "brokerage", "leasing financial"
        ]
    },
    37: {
        "category": "SERVICES",
        "title": "Building and Repair Services",
        "description": "Construction services; installation and repair services; "
                       "mining extraction; oil and gas drilling.",
        "keywords": [
            "construction", "building service", "repair", "maintenance", "installation",
            "plumbing", "electrical installation", "painting service", "cleaning service building",
            "renovation", "carpentry service", "roofing", "drilling"
        ]
    },
    38: {
        "category": "SERVICES",
        "title": "Telecommunications Services",
        "description": "Telecommunications services.",
        "keywords": [
            "telecommunications", "telecom", "internet provider", "broadband", "wireless",
            "telephone service", "satellite communication", "cable tv", "streaming platform",
            "voip", "messaging service", "email service", "social media platform",
            "broadcasting", "radio service", "tv broadcasting"
        ]
    },
    39: {
        "category": "SERVICES",
        "title": "Transport and Storage Services",
        "description": "Transport; packaging and storage of goods; travel arrangement.",
        "keywords": [
            "transport", "shipping", "delivery", "logistics", "freight", "courier",
            "travel agency", "airline service", "bus service", "taxi", "rideshare",
            "storage service", "warehousing", "moving service", "cargo"
        ]
    },
    40: {
        "category": "SERVICES",
        "title": "Treatment of Materials",
        "description": "Treatment of materials; recycling of waste and trash; "
                       "air purification and treatment of water; "
                       "printing services; food and drink preservation.",
        "keywords": [
            "printing service", "manufacturing service", "recycling", "water treatment",
            "food processing", "custom manufacturing", "material treatment", "dyeing service",
            "engraving service", "welding service", "air treatment"
        ]
    },
    41: {
        "category": "SERVICES",
        "title": "Education and Entertainment Services",
        "description": "Education; providing of training; entertainment; sporting and cultural activities; "
                       "publishing of texts other than publicity texts; "
                       "music streaming services.",
        "keywords": [
            "education", "training", "entertainment", "sports event", "cultural event",
            "music streaming service", "streaming entertainment", "publishing service",
            "online education", "e-learning", "tutoring", "school", "university service",
            "fitness class", "yoga class", "gaming service online", "concert",
            "theater", "film production", "podcast", "radio entertainment", "sports club",
            "news service", "journalism"
        ]
    },
    42: {
        "category": "SERVICES",
        "title": "Scientific and Technology Services",
        "description": "Scientific and technological services and research and design relating thereto; "
                       "industrial analysis, industrial research and industrial design services; "
                       "quality control and authentication services; "
                       "design and development of computer hardware and software; "
                       "software as a service (SaaS); cloud computing.",
        "keywords": [
            "technology service", "it service", "software development", "web development",
            "app development", "cloud computing", "saas service", "paas", "iaas",
            "cybersecurity service", "data analytics service", "ai service", "ml service",
            "research and development", "scientific research", "quality control",
            "technical consulting", "it consulting", "web hosting", "database service",
            "api service", "blockchain service", "testing software", "ux design",
            "computer programming", "network service"
        ]
    },
    43: {
        "category": "SERVICES",
        "title": "Food and Beverage Services",
        "description": "Services for providing food and drink; "
                       "temporary accommodation.",
        "keywords": [
            "restaurant", "cafe", "bar service", "catering", "food delivery service",
            "hotel", "accommodation", "bed and breakfast", "canteen", "food service",
            "coffee shop", "bakery service", "fast food"
        ]
    },
    44: {
        "category": "SERVICES",
        "title": "Medical and Veterinary Services",
        "description": "Medical services; veterinary services; "
                       "hygienic and beauty care for human beings or animals; "
                       "agriculture, aquaculture, horticulture and forestry services.",
        "keywords": [
            "medical service", "healthcare", "hospital", "clinic", "doctor service",
            "dental service", "veterinary service", "beauty salon", "spa service",
            "hair salon", "nursing", "pharmacy service", "therapy", "mental health service",
            "agriculture service", "landscaping", "gardening service", "telemedicine"
        ]
    },
    45: {
        "category": "SERVICES",
        "title": "Legal and Security Services",
        "description": "Legal services; security services for the physical protection of tangible property "
                       "and individuals; personal and social services rendered by others to meet the needs "
                       "of individuals; online social networking services.",
        "keywords": [
            "legal service", "law firm", "attorney service", "security service", "security guard",
            "investigation service", "social service", "dating service", "matchmaking",
            "online social network", "personal assistant service", "funeral service",
            "licensing service", "intellectual property service", "arbitration"
        ]
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# VALID CLASS NUMBERS
# ─────────────────────────────────────────────────────────────────────────────
VALID_CLASS_NUMBERS = set(range(1, 46))

# ─────────────────────────────────────────────────────────────────────────────
# NICE AGREEMENT EDITION TIMELINE
# Used for §1401.09 through §1401.15 version checks
# ─────────────────────────────────────────────────────────────────────────────
NICE_EDITION_TIMELINE = {
    "7th":  {"start": "1992-01-01", "end": "1996-12-31", "section": "1401.09"},
    "8th":  {"start": "1997-01-01", "end": "2001-12-31", "section": "1401.11",
             "notes": "Class 42 was split into Classes 42, 43, 44, and 45."},
    "9th":  {"start": "2002-01-01", "end": "2006-12-31", "section": "1401.12",
             "notes": "Major reclassification of services in Class 41 and 42."},
    "10th": {"start": "2007-01-01", "end": "2011-12-31", "section": "1401.13",
             "notes": "Expansion of Class 9 to include downloadable digital content."},
    "11th": {"start": "2012-01-01", "end": "2022-12-31", "section": "1401.14",
             "notes": "Additions to Class 35, 38, and 42 for internet-based services."},
    "12th": {"start": "2023-01-01", "end": "9999-12-31", "section": "1401.15",
             "notes": "Current edition. Refinements to tech, AI, and digital service classifications."}
}

# ─────────────────────────────────────────────────────────────────────────────
# OUTDATED CLASSES (Pre-8th Edition Class 42 expansions)
# §1401.11 — The 8th Edition split old Class 42 into 42, 43, 44, 45
# ─────────────────────────────────────────────────────────────────────────────
OLD_CLASS_42_SERVICES = {
    "restaurant": 43, "cafe": 43, "hotel": 43, "catering": 43, "accommodation": 43,
    "medical": 44, "dental": 44, "veterinary": 44, "beauty": 44, "salon": 44,
    "legal": 45, "security guard": 45, "social service": 45,
    "scientific research": 42, "it service": 42, "software development": 42
}

# ─────────────────────────────────────────────────────────────────────────────
# KNOWN MISCLASSIFICATION PATTERNS
# Maps (keyword → correct_class) for common applicant errors
# ─────────────────────────────────────────────────────────────────────────────
COMMON_MISCLASSIFICATIONS = {
    # Tech goods misclassified
    ("software", 25): (9, "Software is a digital product → Class 9, not clothing (Class 25)"),
    ("software", 35): (42, "Software development is a tech service → Class 42, not business services (Class 35)"),
    ("app", 35): (9, "Mobile app (downloadable) → Class 9; if SaaS → Class 42"),
    ("website", 35): (42, "Website development is IT service → Class 42"),
    ("downloadable music", 41): (9, "Downloadable music is a digital product → Class 9"),
    ("music streaming service", 9): (41, "Streaming service is entertainment → Class 41"),
    ("printed manual", 9): (16, "Printed manuals are printed matter → Class 16"),
    # Food/Bev misclassified
    ("restaurant", 43): (43, "OK"),
    ("restaurant", 35): (43, "Restaurant services → Class 43, not business services"),
    ("coffee beverage", 30): (30, "OK - coffee as a product"),
    ("coffee shop", 30): (43, "Coffee shop (service) → Class 43"),
    # Medical misclassified
    ("medical device", 5): (10, "Medical devices → Class 10, not pharmaceuticals (Class 5)"),
    ("pharmaceutical", 10): (5, "Pharmaceuticals → Class 5, not medical devices (Class 10)"),
    # Old Class 42 issues
    ("restaurant service", 42): (43, "Post 8th Ed.: restaurant services → Class 43 (split from old Class 42)"),
    ("medical service", 42): (44, "Post 8th Ed.: medical services → Class 44 (split from old Class 42)"),
    ("legal service", 42): (45, "Post 8th Ed.: legal services → Class 45 (split from old Class 42)"),
}

# ─────────────────────────────────────────────────────────────────────────────
# SPECIMEN TYPE CATEGORIES
# Used for §1401.06 and §1401.07 analysis
# ─────────────────────────────────────────────────────────────────────────────
SPECIMEN_TYPES = {
    "goods_valid": [
        "product label", "product packaging", "product tag", "product photo",
        "hang tag", "point of sale display", "screenshot showing product for sale"
    ],
    "goods_invalid": [
        "invoice", "purchase order", "business card", "letterhead",
        "press release", "rendering", "mockup", "logo alone"
    ],
    "services_valid": [
        "website screenshot", "advertisement", "brochure", "promotional material",
        "screenshot of service", "service description page"
    ],
    "services_invalid": [
        "product label", "invoice", "business card alone", "rendering"
    ]
}

# ─────────────────────────────────────────────────────────────────────────────
# FILING FEE STRUCTURE (USPTO, Nov 2025)
# Used for §1401.04
# ─────────────────────────────────────────────────────────────────────────────
USPTO_FEES = {
    "TEAS_PLUS": 250,          # Per class
    "TEAS_STANDARD": 350,      # Per class
    "PAPER": 750               # Per class (discouraged)
}

def get_class_info(class_number: int) -> dict:
    """Return full info for a given class number."""
    return NICE_CLASSES.get(class_number, None)

def get_valid_classes() -> set:
    """Return all valid Nice Classification numbers."""
    return VALID_CLASS_NUMBERS

def get_keywords_for_class(class_number: int) -> list:
    """Return keyword list for a class."""
    info = NICE_CLASSES.get(class_number)
    return info["keywords"] if info else []

def suggest_class_for_keyword(keyword: str) -> list:
    """
    Given a keyword, suggest possible classes.
    Returns list of (class_number, title, match_score).
    """
    keyword_lower = keyword.lower().strip()
    suggestions = []

    for cls_num, cls_info in NICE_CLASSES.items():
        score = 0
        for kw in cls_info["keywords"]:
            if keyword_lower == kw:
                score += 10  # Exact match
            elif keyword_lower in kw or kw in keyword_lower:
                score += 5   # Partial match
            elif any(word in kw for word in keyword_lower.split()):
                score += 2   # Word-level match

        if score > 0:
            suggestions.append((cls_num, cls_info["title"], score))

    suggestions.sort(key=lambda x: x[2], reverse=True)
    return suggestions[:5]  # Top 5 suggestions
