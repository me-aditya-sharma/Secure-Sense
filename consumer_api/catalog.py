RIGHTS_SOURCE = "https://consumerhelpline.gov.in/public/index.php/consumerrights"
RIGHTS = [
    {"id":"safety","title":"The right to safety","short":"Your wellbeing comes first.","body":"Consumers have a right to protection against goods and services hazardous to life and property. Check safety information and preserve evidence of a dangerous product.","example":"A faulty appliance overheats: stop using it and document the defect."},
    {"id":"information","title":"The right to be informed","short":"Know what you are agreeing to.","body":"Consumers should receive information about quality, quantity, potency, purity, standard and price. Ask for clear terms and verify claims before buying.","example":"A refund depends on an undisclosed fee: ask for the written policy."},
    {"id":"choice","title":"The right to choose","short":"A decision without pressure.","body":"Access to a variety of goods and services at competitive prices supports an informed choice. Pause when a seller pressures you into an unwanted purchase.","example":"A service provider insists on an unnecessary paid add-on."},
    {"id":"heard","title":"The right to be heard","short":"Your concern deserves attention.","body":"Consumer interests should receive consideration in appropriate forums. Keep a written record of your complaint and the business's response.","example":"Customer support repeatedly closes a documented complaint."},
    {"id":"redressal","title":"The right to seek redressal","short":"A way to put things right.","body":"Consumers can seek redress against unfair trade practices and exploitation. The appropriate remedy depends on the facts and applicable procedure.","example":"A returned order has not been refunded despite written confirmation."},
    {"id":"education","title":"The right to consumer education","short":"Confidence starts with understanding.","body":"Knowing your rights and responsibilities helps you make informed decisions. Learn to verify claims and identify appropriate complaint channels.","example":"Recognizing that a familiar-sounding voice does not establish identity."},
]
for right in RIGHTS:
    right.update(source=RIGHTS_SOURCE, reviewed="2026-11-02")

CHANNELS = [
    {"id":"consumer","title":"National Consumer Helpline","label":"Consumer grievance","description":"For help with purchase, refund and service complaints at the pre-litigation stage.","url":"https://consumerhelpline.gov.in/","phone":"1915","source":"https://consumerhelpline.gov.in/public/about"},
    {"id":"commission","title":"e-Jagriti","label":"Consumer commission","description":"For consumer commission case filing and case management. Check the applicable procedure and documents.","url":"https://e-jagriti.gov.in/","phone":None,"source":"https://grahak.maharashtra.gov.in/en/online-e-filling/"},
    {"id":"cybercrime","title":"National Cyber Crime Reporting Portal","label":"Suspected cybercrime","description":"For suspected online fraud or cybercrime. For financial cyber fraud, promptly contact 1930 and your bank through an official channel.","url":"https://cybercrime.gov.in/","phone":"1930","source":"https://mrm-ncrp.mha.gov.in/restoration/"},
]
