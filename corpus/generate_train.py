"""
Generate the NagarVani template training corpus.

Each department has phrase banks in four input varieties:
  mr      Marathi in Devanagari
  hi      Hindi in Devanagari
  rom     Marathi typed in Latin script (as on WhatsApp)
  mix     Marathi-English code-mixed, Devanagari with English words

Every issue phrase carries semantic tags. The severity label of a generated
complaint is computed from those tags (not from keyword matching on the output
string) using the annotation guideline in docs/annotation_guideline.md.

The held-out test set (test_handwritten.tsv) was written separately, by hand,
and is NOT produced by this script.
"""
import csv, json, random, sys, os

random.seed(int(os.environ.get("SEED", 7)))
HERE = os.path.dirname(os.path.abspath(__file__))
GAZ = json.load(open(os.path.join(HERE, "..", "data", "gazetteer.json"), encoding="utf-8"))

# ---------------------------------------------------------------- issue banks
# (text, tags)  tags ⊂ {INJ, HAZ, RISK, OUTBREAK, SEWHOME, NUIS, OUTAGE, WASTE, REQ}
B = {}
B["ROAD"] = {
 "mr": [("रस्त्यावर खूप खड्डे पडले आहेत", []), ("रस्ता पूर्ण उखडला आहे", []),
        ("डांबरीकरण खराब झाले आहे", []), ("रस्त्याच्या मधोमध मोठा खड्डा आहे", []),
        ("खड्ड्यात पडून एक दुचाकीस्वार जखमी झाला", ["INJ"]),
        ("खड्ड्यामुळे अपघात झाला, एक माणूस जखमी", ["INJ"]),
        ("खड्ड्यामुळे कधीही अपघात होऊ शकतो", ["RISK"]),
        ("रस्ता खचला आहे, वाहनं अडकतात", ["RISK"]),
        ("स्पीड ब्रेकर खूप उंच आहे, गाड्यांचं नुकसान होतं", []),
        ("फूटपाथ तुटला आहे", []), ("रस्ता खोदून ठेवला आहे आणि बुजवला नाही", []),
        ("गतिरोधकावर रंग नाही, रात्री दिसत नाही", ["RISK"]),
        ("रस्त्यावरची खडी सगळीकडे पसरली आहे", [])],
 "hi": [("सड़क पर बहुत गड्ढे हैं", []), ("सड़क पूरी टूट गई है", []),
        ("गड्ढे की वजह से एक आदमी गिरकर घायल हो गया", ["INJ"]),
        ("गड्ढे से कभी भी दुर्घटना हो सकती है", ["RISK"]),
        ("सड़क खोदकर छोड़ दी गई है", []), ("फुटपाथ टूटा हुआ है", []),
        ("स्पीड ब्रेकर बहुत ऊंचा है", [])],
 "rom": [("rastyavar khup khadde aahet", []), ("rasta kharab zala aahe", []),
         ("khadda padla aahe road var", []), ("khaddyat padun ek manus jakhmi zala", ["INJ"]),
         ("khaddya mule accident hou shakto", ["RISK"]), ("rasta khodun thevla aahe", []),
         ("footpath tutla aahe", []), ("speed breaker khup uncha aahe", [])],
 "mix": [("road वर मोठे potholes आहेत", []), ("road पूर्ण खराब झालाय", []),
         ("pothole मुळे bike slip होऊन accident झाला", ["INJ"]),
         ("pothole मुळे accident होऊ शकतो", ["RISK"]), ("road खोदून ठेवलाय, repair केलं नाही", []),
         ("footpath चे paver blocks निघालेत", []), ("speed breaker ला marking नाही", ["RISK"])],
}
B["SWM"] = {
 "mr": [("कचरा उचलला जात नाही", []), ("कचराकुंडी भरून वाहत आहे", []),
        ("घंटागाडी येत नाही", []), ("रस्त्याच्या कडेला कचऱ्याचा ढीग आहे", []),
        ("कचरा जाळला जातो, धूर होतो", ["NUIS"]), ("कचऱ्याचा घाण वास येतो", ["NUIS"]),
        ("मोकळ्या जागेत लोक कचरा टाकतात", []), ("ओला आणि सुका कचरा वेगळा घेत नाहीत", ["REQ"]),
        ("कचऱ्यावर माश्या आणि डास झाले आहेत", ["NUIS"]), ("रस्त्याची झाडलोट होत नाही", ["REQ"]),
        ("सार्वजनिक शौचालय अस्वच्छ आहे", [])],
 "hi": [("कचरा नहीं उठाया जा रहा", []), ("कूड़ेदान भरकर बह रहा है", []),
        ("कचरा गाड़ी नहीं आती", []), ("कूड़े का ढेर लगा है", []),
        ("कचरा जलाया जाता है, धुआं होता है", ["NUIS"]), ("कूड़े से बदबू आ रही है", ["NUIS"])],
 "rom": [("kachra uchalla jat nahi", []), ("kachra gadi yet nahi", []),
         ("kachrakundi bharun vahat aahe", []), ("kachryacha dhig aahe", []),
         ("kachra jaltat, dhur hoto", ["NUIS"]), ("kachryacha vaas yetoy", ["NUIS"]),
         ("ghantagadi yet nahi", [])],
 "mix": [("garbage collection होत नाही", []), ("dustbin overflow होतोय", []),
         ("garbage van येत नाही", []), ("कचऱ्याचा dump तयार झालाय", []),
         ("garbage burning होतं, smoke येतो", ["NUIS"]), ("कचऱ्याचा खूप smell येतो", ["NUIS"]),
         ("wet dry segregation होत नाही", ["REQ"])],
}
B["WATER"] = {
 "mr": [("नळाला पाणी येत नाही", ["OUTAGE"]), ("पाणीपुरवठा बंद आहे", ["OUTAGE"]),
        ("पाणी कमी दाबाने येते", []), ("पाइपलाइन फुटली आहे, पाणी वाया जाते", ["WASTE"]),
        ("नळाला गढूळ पाणी येते", ["NUIS"]), ("दूषित पाण्यामुळे लोक आजारी पडले", ["OUTBREAK"]),
        ("पाण्याची वेळ ठरलेली नाही", ["REQ"]), ("पाण्याचे बिल जास्त आले आहे", ["REQ"]),
        ("व्हॉल्व्हमधून पाणी गळते", []), ("पाण्याची टाकी साफ केली नाही", []),
        ("नवीन नळ जोडणी हवी आहे", ["REQ"])],
 "hi": [("नल में पानी नहीं आ रहा", ["OUTAGE"]), ("पानी की सप्लाई बंद है", ["OUTAGE"]),
        ("पानी बहुत कम प्रेशर से आता है", []), ("पाइपलाइन फट गई है, पानी बर्बाद हो रहा है", ["WASTE"]),
        ("गंदा पानी आ रहा है", ["NUIS"]), ("गंदे पानी से लोग बीमार हो गए", ["OUTBREAK"])],
 "rom": [("nalala pani yet nahi", ["OUTAGE"]), ("pani purvatha band aahe", ["OUTAGE"]),
         ("pani kami pressure ne yete", []), ("pipeline futli aahe", ["WASTE"]),
         ("gadhul pani yete", ["NUIS"]), ("dushit panyamule lok aajari padle", ["OUTBREAK"]),
         ("pani vaya jatay leakage mule", ["WASTE"])],
 "mix": [("water supply बंद आहे", ["OUTAGE"]), ("पाणी low pressure ने येतं", []),
         ("pipeline burst झाली आहे", ["WASTE"]), ("नळाला dirty water येतं", ["NUIS"]),
         ("contaminated पाण्यामुळे सगळे sick पडलेत", ["OUTBREAK"]), ("valve मधून leakage होतंय", []),
         ("water bill चुकीचं आलंय", ["REQ"])],
}
B["DRAIN"] = {
 "mr": [("ड्रेनेज तुंबले आहे", ["NUIS"]), ("सांडपाणी रस्त्यावर वाहत आहे", ["NUIS"]),
        ("चेंबरचे झाकण उघडे आहे", ["HAZ"]), ("मॅनहोलवर झाकण नाही", ["HAZ"]),
        ("सांडपाणी घरात येत आहे", ["SEWHOME"]), ("गटार तुंबून घाण पाणी साचले आहे", ["NUIS"]),
        ("पावसाळी गटार साफ केलेले नाही", []), ("नाल्याची सफाई झाली नाही", []),
        ("ड्रेनेज लाइन फुटली आहे", ["NUIS"]), ("गटारावर झाकण नाही, कोणी पडू शकते", ["HAZ"]),
        ("पावसाचे पाणी रस्त्यावर साचते", [])],
 "hi": [("नाली जाम हो गई है", ["NUIS"]), ("गटर का पानी सड़क पर बह रहा है", ["NUIS"]),
        ("मैनहोल का ढक्कन खुला है", ["HAZ"]), ("सीवर का पानी घर में आ रहा है", ["SEWHOME"]),
        ("नाले की सफाई नहीं हुई", [])],
 "rom": [("drainage tumbli aahe", ["NUIS"]), ("sandpani rastyavar vahat aahe", ["NUIS"]),
         ("chamber che jhakan ughade aahe", ["HAZ"]), ("manhole var jhakan nahi", ["HAZ"]),
         ("sandpani gharat yet aahe", ["SEWHOME"]), ("gatar tumbla aahe", ["NUIS"]),
         ("nalyachi safai zali nahi", [])],
 "mix": [("drainage block झालंय", ["NUIS"]), ("sewage road वर overflow होतंय", ["NUIS"]),
         ("manhole open आहे, cover नाही", ["HAZ"]), ("sewage घरात backflow होतंय", ["SEWHOME"]),
         ("storm water drain clean केली नाही", []), ("drainage line leak होतेय", ["NUIS"])],
}
B["ELEC"] = {
 "mr": [("पथदिवे बंद आहेत", []), ("रस्त्यावरचे दिवे लागत नाहीत", []),
        ("विजेची तार तुटून खाली पडली आहे", ["HAZ"]), ("खांबाला करंट लागत आहे", ["HAZ"]),
        ("विजेचा खांब वाकला आहे, पडू शकतो", ["HAZ"]), ("दिवे दिवसाही चालू असतात", ["REQ"]),
        ("दिवा सतत बंद-चालू होतो", ["REQ"]), ("नवीन पथदिवे बसवावेत", ["REQ"]),
        ("गल्लीत अंधार असतो, दिवा बंद", []), ("डीपी बॉक्स उघडा आहे", ["HAZ"]),
        ("हायमास्ट दिवा बंद आहे", [])],
 "hi": [("स्ट्रीट लाइट बंद है", []), ("गली में अंधेरा रहता है, लाइट खराब है", []),
        ("बिजली का तार टूटकर लटक रहा है", ["HAZ"]), ("खंभे में करंट आ रहा है", ["HAZ"]),
        ("बिजली का खंभा झुक गया है", ["HAZ"]), ("नई स्ट्रीट लाइट लगवाइए", ["REQ"])],
 "rom": [("street light band aahe", []), ("pathdive band aahet", []),
         ("vijechi taar tutli aahe", ["HAZ"]), ("khambala current lagto", ["HAZ"]),
         ("khamb vakla aahe, padu shakto", ["HAZ"]), ("galli madhe andhar aahe, light band", []),
         ("navin street light lava", ["REQ"])],
 "mix": [("street light काम करत नाही", []), ("light pole ला shock लागतो", ["HAZ"]),
         ("electric wire लटकतेय road वर", ["HAZ"]), ("street lights दिवसा पण ON असतात", ["REQ"]),
         ("high mast light बंद आहे", []), ("pole वाकलाय, कधीही पडेल", ["HAZ"])],
}
B["HEALTH"] = {
 "mr": [("डासांचा खूप त्रास आहे", []), ("धूरफवारणी होत नाही", []),
        ("डेंग्यूचे रुग्ण वाढले आहेत", ["OUTBREAK"]), ("मलेरियाचे रुग्ण आढळले आहेत", ["OUTBREAK"]),
        ("मेलेले जनावर रस्त्यावर पडले आहे", ["NUIS"]), ("उंदरांचा उपद्रव वाढला आहे", []),
        ("उघड्यावर अन्न टाकले जाते, दुर्गंधी येते", ["NUIS"]), ("साचलेल्या पाण्यात डासांच्या अळ्या आहेत", []),
        ("उघड्यावर शौच केले जाते", ["NUIS"]), ("हॉटेलमध्ये अस्वच्छता आहे", [])],
 "hi": [("मच्छरों का बहुत प्रकोप है", []), ("फॉगिंग नहीं होती", []),
        ("डेंगू के मरीज बढ़ गए हैं", ["OUTBREAK"]), ("मरा हुआ जानवर पड़ा है, बदबू आ रही है", ["NUIS"]),
        ("चूहों का आतंक है", [])],
 "rom": [("dasancha tras aahe", []), ("fawarni hot nahi", []),
         ("dengue che rugn vadhle", ["OUTBREAK"]), ("melela prani padla aahe", ["NUIS"]),
         ("undir khup zale aahet", []), ("ughdyavar shauch kartat", ["NUIS"])],
 "mix": [("mosquito problem खूप वाढलाय", []), ("fogging होत नाही", []),
         ("dengue cases वाढलेत", ["OUTBREAK"]), ("dead dog पडलाय road वर", ["NUIS"]),
         ("rats चा त्रास आहे", []), ("मच्छरांच्या larvae साचलेल्या पाण्यात आहेत", [])],
}
B["TREE"] = {
 "mr": [("झाड रस्त्यावर पडले आहे", ["HAZ"]), ("झाडाची फांदी तुटून लटकत आहे", ["HAZ"]),
        ("झाड वाकले आहे, पडण्याची भीती आहे", ["HAZ"]), ("झाडांची छाटणी करावी", ["REQ"]),
        ("बेकायदेशीर वृक्षतोड झाली आहे", []), ("पडलेल्या फांद्या उचलल्या नाहीत", []),
        ("झाडामुळे पथदिवा झाकला गेला आहे", ["REQ"]), ("झाड पडून गाडीचे नुकसान झाले", ["RISK"]),
        ("उद्यानातील झाडांची निगा राखली जात नाही", ["REQ"])],
 "hi": [("पेड़ सड़क पर गिर गया है", ["HAZ"]), ("पेड़ की डाल टूटकर लटक रही है", ["HAZ"]),
        ("पेड़ की छंटाई करवाइए", ["REQ"]), ("अवैध पेड़ कटाई हुई है", [])],
 "rom": [("zad rastyavar padle aahe", ["HAZ"]), ("zadachi fandi latakli aahe", ["HAZ"]),
         ("zadachi chhatni kara", ["REQ"]), ("anadhikrut vruksh tod zali", []),
         ("padlelya fandya uchlalya nahit", [])],
 "mix": [("tree fall झालंय road वर", ["HAZ"]), ("branch तुटून लटकतेय", ["HAZ"]),
         ("tree trimming करायचं आहे", ["REQ"]), ("illegal tree cutting झालंय", []),
         ("झाड पडून car चं नुकसान झालं", ["RISK"])],
}
B["ENCROACH"] = {
 "mr": [("फूटपाथवर फेरीवाल्यांनी अतिक्रमण केले आहे", []), ("रस्त्यावर अनधिकृत टपऱ्या आहेत", []),
        ("दुकानदारांनी रस्त्यावर सामान ठेवले आहे", []), ("अनधिकृत फलक लावले आहेत", ["REQ"]),
        ("बेवारस वाहने रस्त्याकडेला पडून आहेत", []), ("हातगाड्यांमुळे वाहतूक कोंडी होते", []),
        ("अनधिकृत होर्डिंग कधीही पडू शकते", ["HAZ"]), ("पदपथावर बांधकाम साहित्य ठेवले आहे", [])],
 "hi": [("फुटपाथ पर अतिक्रमण है", []), ("सड़क पर अवैध ठेले लगे हैं", []),
        ("अवैध बैनर लगे हैं", ["REQ"]), ("लावारिस गाड़ियां पड़ी हैं", [])],
 "rom": [("footpath var atikraman aahe", []), ("anadhikrut tapri aahe", []),
         ("feriwalyanni rasta adavla aahe", []), ("anadhikrut flex lavle aahet", ["REQ"]),
         ("bewaras gadya padun aahet", [])],
 "mix": [("footpath वर hawkers चं encroachment आहे", []), ("illegal stalls लावलेत road वर", []),
         ("illegal banners लावलेत", ["REQ"]), ("abandoned vehicles पडून आहेत", []),
         ("hoarding illegal आहे आणि पडू शकतं", ["HAZ"])],
}
B["BUILD"] = {
 "mr": [("परवानगी न घेता बांधकाम सुरू आहे", []), ("अनधिकृत मजला बांधला जात आहे", []),
        ("जुन्या इमारतीची भिंत कोसळण्याच्या स्थितीत आहे", ["HAZ"]), ("धोकादायक इमारत आहे", ["HAZ"]),
        ("स्लॅबचे तुकडे खाली पडत आहेत", ["HAZ"]), ("नदीपात्रात बांधकाम केले जात आहे", []),
        ("बांधकामाचा राडारोडा रस्त्यावर टाकला आहे", []), ("बांधकाम परवानगीचा अर्ज प्रलंबित आहे", ["REQ"]),
        ("भिंत कोसळून लोक जखमी झाले", ["INJ"]), ("खोदकामाला संरक्षक भिंत नाही", ["RISK"])],
 "hi": [("बिना अनुमति के निर्माण हो रहा है", []), ("अवैध मंजिल बनाई जा रही है", []),
        ("पुरानी इमारत खतरनाक हालत में है", ["HAZ"]), ("दीवार गिरने से लोग घायल हुए", ["INJ"])],
 "rom": [("anadhikrut bandhkam chalu aahe", []), ("parvangi nastana majla bandhtat", []),
         ("dhokadayak imarat aahe", ["HAZ"]), ("bhint koslnar aahe", ["HAZ"]),
         ("bandhkam cha radaroda rastyavar", [])],
 "mix": [("illegal construction चालू आहे", []), ("building permission न घेता floor बांधतायत", []),
         ("dangerous building आहे, wall पडेल", ["HAZ"]), ("excavation ला safety wall नाही", ["RISK"]),
         ("construction debris road वर टाकलाय", [])],
}
B["VET"] = {
 "mr": [("भटक्या कुत्र्यांचा त्रास आहे", []), ("कुत्र्याने चावा घेतला", ["INJ"]),
        ("पिसाळलेला कुत्रा फिरत आहे", ["HAZ"]), ("मोकाट जनावरे रस्त्यावर फिरतात", []),
        ("कुत्र्यांची नसबंदी करावी", ["REQ"]), ("जखमी जनावर रस्त्यावर पडले आहे", ["RISK"]),
        ("कुत्री गाड्यांच्या मागे धावतात, अपघात होऊ शकतो", ["RISK"]), ("डुकरांचा उपद्रव आहे", []),
        ("माकडांचा त्रास वाढला आहे", []), ("कुत्री रात्रभर भुंकतात", ["REQ"])],
 "hi": [("आवारा कुत्तों का आतंक है", []), ("कुत्ते ने काट लिया", ["INJ"]),
        ("आवारा मवेशी सड़क पर घूमते हैं", []), ("पागल कुत्ता घूम रहा है", ["HAZ"]),
        ("कुत्तों की नसबंदी करवाइए", ["REQ"])],
 "rom": [("bhatkya kutryancha tras aahe", []), ("kutra chavla", ["INJ"]),
         ("pisalela kutra firtoy", ["HAZ"]), ("mokat janavare rastyavar", []),
         ("kutryanchi nasbandi kara", ["REQ"])],
 "mix": [("stray dogs चा खूप त्रास आहे", []), ("dog bite झाला", ["INJ"]),
         ("stray cattle road वर बसतात", []), ("stray dogs bike च्या मागे लागतात", ["RISK"]),
         ("dogs ची sterilization करा", ["REQ"])],
}

# ------------------------------------------------------------- other slots
PREFIX = {"mr": ["", "", "नमस्कार, ", "साहेब, ", "कृपया लक्ष द्या, ", "तक्रार: "],
          "hi": ["", "", "नमस्ते, ", "सर, ", "कृपया ध्यान दें, "],
          "rom": ["", "", "namaskar, ", "saheb, ", "please "],
          "mix": ["", "", "Hello sir, ", "Please ", "नमस्कार, "]}
SUFFIX = {"mr": ["", "", " लवकर दुरुस्ती करा", " कृपया कारवाई करावी", " तक्रार करूनही दखल घेतली नाही"],
          "hi": ["", "", " जल्दी ठीक करवाइए", " कृपया कार्रवाई करें"],
          "rom": ["", "", " lavkar kara", " karvai kara please"],
          "mix": ["", "", " please लवकर action घ्या", " urgent आहे"]}
LOC_TPL = {"mr": ["{L} मध्ये", "{L} येथे", "{L} भागात", "{L} परिसरात"],
           "hi": ["{L} में", "{L} इलाके में"],
           "rom": ["{L} madhe", "{L} yethe", "{L} bhagat"],
           "mix": ["{L} मध्ये", "{L} area मध्ये", "{L} ला"]}
DUR = {"mr": [("{n} दिवसांपासून", 1), ("गेले {n} दिवस", 1), ("{w} आठवड्यांपासून", 7), ("महिनाभरापासून", 30)],
       "hi": [("{n} दिनों से", 1), ("{w} हफ्तों से", 7), ("एक महीने से", 30)],
       "rom": [("{n} divas pasun", 1), ("{w} aathvade zale", 7), ("mahina zala", 30)],
       "mix": [("{n} days पासून", 1), ("{w} weeks झाले", 7), ("एक month झाला", 30)]}
NUM = {"mr": {1: "एक", 2: "दोन", 3: "तीन", 4: "चार", 5: "पाच", 6: "सहा", 7: "सात", 10: "दहा"},
       "hi": {1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पांच", 6: "छह", 7: "सात", 10: "दस"},
       "rom": {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 10: "10"},
       "mix": {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 10: "10"}}
VULN = {"mr": ["शाळेजवळ", "हॉस्पिटलसमोर", "दवाखान्याजवळ"], "hi": ["स्कूल के पास", "अस्पताल के सामने"],
        "rom": ["shalejaval", "hospital samor"], "mix": ["school जवळ", "hospital समोर"]}

def loc_alias(lang):
    key = random.choice(list(GAZ["localities"]))
    al = GAZ["localities"][key]["aliases"]
    latin = [a for a in al if a.isascii()]
    deva = [a for a in al if not a.isascii()]
    if lang == "rom":
        a = random.choice(latin)
    elif lang == "mix":
        a = random.choice(latin + deva)
        a = a.title() if a.isascii() else a
    else:
        a = random.choice(deva)
    return key, a

BAND = ["P1", "P2", "P3", "P4"]
def guideline_severity(dept, tags, days, vuln):
    """Annotation guideline (docs/annotation_guideline.md) applied to semantic tags."""
    if {"INJ", "HAZ", "OUTBREAK", "SEWHOME"} & set(tags):
        return "P1"
    b = 3
    if "REQ" in tags: b = 4
    if {"RISK", "NUIS", "WASTE"} & set(tags): b = min(b, 2)
    if dept == "WATER" and "OUTAGE" in tags and days >= 2: b = min(b, 2)
    if dept == "SWM" and days >= 3: b = min(b, 2)
    if vuln: b = max(1, b - 1)
    if days >= 14: b = max(1, b - 1)
    return f"P{b}"

def make(dept, lang):
    issue, tags = random.choice(B[dept][lang])
    parts = []
    key = "NONE"
    days = 0
    vuln = False
    if random.random() < 0.8:
        key, alias = loc_alias(lang)
        parts.append(random.choice(LOC_TPL[lang]).format(L=alias))
    if random.random() < 0.15:
        parts.append(random.choice(VULN[lang])); vuln = True
    parts.append(issue)
    if random.random() < 0.3:
        tpl, unit = random.choice(DUR[lang])
        if "{n}" in tpl:
            n = random.choice([1, 2, 3, 4, 5, 6, 7, 10]); days = n * unit
            s = tpl.format(n=NUM[lang][n])
        elif "{w}" in tpl:
            n = random.choice([1, 2, 3]); days = n * unit
            s = tpl.format(w=NUM[lang][n])
        else:
            days = unit; s = tpl
        parts.append(s)
    random.shuffle(parts) if random.random() < 0.3 else None
    text = random.choice(PREFIX[lang]) + ", ".join(parts) + random.choice(SUFFIX[lang])
    return dict(text=text.strip(), lang=lang, dept=dept, loc=key,
                sev=guideline_severity(dept, tags, days, vuln))

def main(n_per_dept=200, out=os.path.join(HERE, "train_template.tsv")):
    langs = ["mr"] * 5 + ["hi"] * 2 + ["rom"] * 2 + ["mix"] * 2
    rows, seen = [], set()
    for d in B:
        tries = 0
        k = 0
        while k < n_per_dept and tries < n_per_dept * 20:
            tries += 1
            r = make(d, random.choice(langs))
            if r["text"] in seen: continue
            seen.add(r["text"]); r["id"] = f"G{len(rows)+1:04d}"; rows.append(r); k += 1
    random.shuffle(rows)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "lang", "dept", "loc", "sev", "text"], delimiter="\t")
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}")

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
