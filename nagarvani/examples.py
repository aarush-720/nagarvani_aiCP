"""Example complaints shown on the intake page (one click fills the text box).

These are the inputs of docs/DEMO_SCRIPT.md. Each one was run through the real pipeline,
and its output is recorded there; scripts/run_demo_script.py regenerates that file, and
tests/test_demo_script.py checks that every input still shows its behaviour.
Only DEMO_FAILURE comes from the test set (deliberately: a real classifier error).
"""
EXAMPLES = [
    {"key": "clean_marathi", "label": "१. स्पष्ट मराठी तक्रार / Clean Marathi",
     "behaviour": "A clean Marathi complaint that auto-routes",
     "text": "वारजे येथे नळाला चार दिवसांपासून पाणी आलेले नाही"},
    {"key": "romanised", "label": "२. रोमन लिपी / Romanised Marathi",
     "behaviour": "A romanised Marathi complaint",
     "text": "Baner madhe streetlight ek athavda band ahe, ratri khup andhar asto"},
    {"key": "code_mixed", "label": "३. मराठी-इंग्रजी मिश्र / Code-mixed",
     "behaviour": "A code-mixed Marathi-English complaint",
     "text": "Viman Nagar मध्ये drainage overflow होतोय, रस्त्यावर घाण पाणी आलंय"},
    {"key": "life_safety", "label": "४. जीवघेणा धोका / Life safety → P1",
     "behaviour": "A life-safety complaint forced to P1 by a visible rule",
     "text": "धनकवडीत मॅनहोलचे झाकण गायब आहे, शाळकरी मुले रोज इथून जातात"},
    {"key": "fuzzy", "label": "५. चुकीचे स्पेलिंग / Misspelt locality",
     "behaviour": "A misspelt locality rescued by the fuzzy resolver",
     "text": "हडप्सर मध्ये कचऱ्याचा मोठा ढीग साचला आहे"},
    {"key": "unknown_place", "label": "६. अनोळखी ठिकाण / Unknown locality",
     "behaviour": "An unknown locality that goes to review",
     "text": "उंड्री येथे रस्त्यावर मोठे खड्डे पडले आहेत"},
    {"key": "low_confidence", "label": "७. अस्पष्ट विभाग / Low confidence",
     "behaviour": "A low-confidence complaint that goes to review",
     "text": "कर्वेनगरमध्ये बांधकामाचे साहित्य रस्त्यावर ठेवले आहे"},
    {"key": "dup1", "label": "८अ. पुनरावृत्ती — पहिली / Duplicate, report 1",
     "behaviour": "Triple duplicate: report 1", "text": "हडपसर गाडीतळाजवळ रस्त्यावर खूप मोठे खड्डे पडले आहेत"},
    {"key": "dup2", "label": "८ब. पुनरावृत्ती — दुसरी / Duplicate, report 2",
     "behaviour": "Triple duplicate: report 2", "text": "हडपसर गाडीतळ येथे रस्त्यावर मोठे खड्डे पडले आहेत, गाड्या आदळतात"},
    {"key": "dup3", "label": "८क. पुनरावृत्ती — तिसरी / Duplicate, report 3",
     "behaviour": "Triple duplicate: report 3 (R32 escalates)", "text": "हडपसरमध्ये गाडीतळाजवळच्या रस्त्यावर खूप खड्डे पडले आहेत"},
    {"key": "failure", "label": "९. खरी चूक / An honest failure",
     "behaviour": "A real misclassification from the test set (T088)",
     "text": "बालाजीनगरमधील बंद पडलेल्या टायर दुकानात पाणी साचून अळ्या झाल्या आहेत"},
]
