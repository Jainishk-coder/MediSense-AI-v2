import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from langchain_classic.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

import db

app = Flask(__name__)
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
KB_DIR = Path("health_faiss_db")
KB_METADATA_FILE = Path("data") / "kb_metadata.json"


def load_kb_metadata():
    default = {"source_count": 0, "chunk_count": 0, "source_files": []}
    if not KB_METADATA_FILE.exists():
        return default
    try:
        return json.loads(KB_METADATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return default


KB_METADATA = load_kb_metadata()

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"local_files_only": True},
)
vectorstore = FAISS.load_local(
    str(KB_DIR),
    embeddings,
    allow_dangerous_deserialization=True,
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 7})

llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model="llama-3.3-70b-versatile",
    temperature=0.35,
)

PROMPT_EN = PromptTemplate(
    input_variables=["context", "question"],
    template="""
You are MediSense AI, a warm and careful medical information assistant.

Reply only in English. Keep the tone natural, kind, and simple.

Rules:
- Do not diagnose. Use words like "could be", "may be", and "needs a doctor to confirm".
- Do not prescribe specific medicines or dosages.
- Do not mention database, PDFs, sources, chunks, or context.
- Use the provided medical context first. If the context is limited, say what is generally possible and advise medical review.
- Keep the answer around 170-260 words.
- Make the answer feel premium and useful, not like a plain paragraph dump.
- Use this friendly structure when symptoms are involved:
  **Quick take:** 1-2 lines on what it may suggest.
  **What you can do now:** 3-4 safe bullets.
  **See a doctor urgently/soon if:** clear red flags or duration-based advice.
  **One question:** ask only the most useful follow-up question.

For symptom questions:
1. Start with empathy.
2. Explain likely possibilities without confirming a disease.
3. Give safe home-care steps.
4. Clearly say when to see a doctor.
5. Ask 1-2 useful follow-up questions at the end if needed.

For general health questions:
Answer directly with symptoms, prevention, practical habits, and when to consult a clinician.

For medicine questions:
Explain what the medicine is commonly used for, key safety cautions, when not to take it, and when to contact a doctor.
Do not give a personalized dose. If the user already took a medicine, respond with safety checks and next steps.

For emergency symptoms:
Start with urgent medical care advice before any other explanation.

Medical context:
{context}

User message:
{question}

Answer:
""",
)

PROMPT_HI = PromptTemplate(
    input_variables=["context", "question"],
    template="""
You are MediSense AI, ek warm aur careful health assistant.

Reply sirf Hindi/Hinglish roman style me do. Devanagari use mat karo. Tone simple doctor-jaisi conversation wali rakho.

Rules:
- Diagnosis confirm mat karo. "ho sakta hai", "lag sakta hai", "doctor confirm karenge" jaisi language use karo.
- Specific medicine ya dosage prescribe mat karo.
- Database, PDF, source, chunk, ya context ka zikr mat karo.
- Medical context ko priority do. Context limited ho to general safe advice do aur doctor consult bol do.
- Answer 180-280 words ke aas paas rakho.
- Short paragraphs rakho; bullets tabhi use karo jab useful ho.

Symptoms wale sawal me:
1. Empathy se start karo.
2. Simple words me possible causes batao, diagnosis confirm nahi.
3. Ghar par safe care steps batao.
4. Doctor ko kab dikhana hai clearly bolo.
5. End me 1-2 follow-up questions pucho agar zarurat ho.

Answer ko helpful aur premium feel do:
**Quick take:** short explanation.
**Abhi kya karein:** 3-4 safe bullets.
**Doctor ko kab dikhana hai:** red flags/duration.
**Ek sawal:** sirf ek useful follow-up.

General health question me:
Direct answer do, common symptoms, prevention, lifestyle tips aur doctor consult advice do.

Medicine wale sawal me:
Medicine kis kaam me aati hai, important safety cautions, kab avoid karni chahiye, aur doctor ko kab contact karna hai batao.
Personal dose prescribe mat karo. Agar user bolta hai ki woh medicine le raha hai, to safety checks aur next steps batao.

Emergency symptoms me:
Sabse pehle urgent medical help lene ko bolo.

Medical context:
{context}

User message:
{question}

Answer:
""",
)

qa_chain_en = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    return_source_documents=True,
    chain_type_kwargs={"prompt": PROMPT_EN},
)

qa_chain_hi = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    return_source_documents=True,
    chain_type_kwargs={"prompt": PROMPT_HI},
)

GREETINGS_EN = {"hi", "hello", "hey", "hii", "hiii", "good morning", "good afternoon", "good evening"}
GREETINGS_HI = {"namaste", "namaskar", "kaise ho", "kaise hain", "ram ram", "pranam", "sat sri akal"}
THANKS = {"thanks", "thank you", "thankyou", "shukriya", "dhanyawad", "dhanyavaad", "guidance"}
GOODBYES = {"bye", "goodbye", "see you", "take care", "alvida", "fir milenge", "phir milte hain"}
ABOUT = {"who are you", "what can you do", "help", "tum kaun ho", "aap kaun hain", "madad", "tumhara naam"}
ACKNOWLEDGEMENTS = {"ok", "okay", "okk", "fine", "alright", "got it", "samajh gaya", "samjh gaya"}

MEDICAL_KEYWORDS = {
    "fever", "cold", "flu", "cough", "headache", "pain", "vomiting", "nausea",
    "dizziness", "fatigue", "weakness", "diarrhea", "breathing", "chest", "throat",
    "asthma", "diabetes", "sugar", "bp", "pressure", "heart", "stomach", "rash",
    "infection", "covid", "dengue", "malaria", "typhoid", "migraine", "doctor",
    "hospital", "medicine", "health", "medical", "symptom", "disease", "kidney",
    "liver", "allergy", "pregnancy", "prevent", "prevention", "treatment", "urine",
    "skin", "eye", "ear", "anxiety", "stress", "sleep", "bukhar", "khansi", "sardi",
    "sir", "dard", "ulti", "chakkar", "pet", "gala", "saans", "kamzori", "jukaam",
    "lakshan", "bimari", "tabiyat", "ilaj", "dawai", "dawa", "seene", "peshab",
    "medication", "tablet", "capsule", "dose", "dosage", "drug", "antibiotic",
    "painkiller", "paracetamol", "paracetemol", "acetaminophen", "ibuprofen",
    "aspirin", "cetirizine", "azithromycin", "amoxicillin", "ors", "inhaler",
    "insulin", "metformin", "antacid", "antihistamine", "i am taking", "taking",
    "le raha", "le rahi", "kha raha", "kha rahi",
}

EMERGENCY_PATTERNS = [
    "chest pain", "can't breathe", "cannot breathe", "difficulty breathing",
    "shortness of breath", "unconscious", "fainting", "stroke", "heart attack",
    "severe bleeding", "vomiting blood", "blood in stool", "seizure", "blue lips",
    "one side weakness", "slurred speech", "worst headache", "stiff neck",
    "severe dehydration", "suicidal", "self harm", "seene me dard", "saans nahi",
    "saans lene me dikkat", "behosh", "dil ka daura", "bahut khoon", "khoon ki ulti",
]

DOCTOR_SOON_PATTERNS = [
    "3 days", "three days", "high fever", "blood", "pregnant", "pregnancy",
    "baby", "infant", "elderly", "diabetes", "asthma", "kidney", "heart disease",
    "worse", "worsening", "not improving", "bahut tez", "teen din", "garbhavati",
    "past 3 days", "since 3 days", "more than 3 days", "2 days", "two days",
]

FOLLOW_UP_HINTS = {
    "yes", "no", "yeah", "yep", "nope", "same", "still", "now", "today",
    "yesterday", "days", "day", "hours", "hour", "since", "past", "from",
    "it", "this", "that", "also", "more", "less", "mild", "severe",
    "high", "low", "better", "worse", "improving", "not", "again",
}

HINDI_WORDS = {
    "mujhe", "mera", "meri", "mere", "hai", "hain", "hun", "hoon", "kya", "kaise",
    "bukhar", "dard", "khansi", "sardi", "jukaam", "gala", "ulti", "dast", "chakkar",
    "kamzori", "thakan", "saans", "dawai", "dawa", "ilaj", "batao", "bataiye",
    "karun", "lagta", "taklif", "tabiyat", "bimari", "lakshan", "nahi", "bahut",
}

HINDI_PHRASES = [
    "ho raha", "ho rahi", "kitne din", "kya karun", "gale me", "pet me",
    "sir dard", "bukhar hai", "khansi hai", "dard hai", "saans lene",
]


def normalize(text):
    return re.sub(r"\s+", " ", text.lower().strip())


def detect_language(text):
    lower = normalize(text)
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    if any(phrase in lower for phrase in HINDI_PHRASES):
        return "hi"
    words = set(re.findall(r"[a-z]+", lower))
    if len(words & HINDI_WORDS) >= 2:
        return "hi"
    if len(words & HINDI_WORDS) == 1 and len(words) <= 5:
        return "hi"
    return "en"


def format_history(messages):
    if not messages:
        return "No previous messages."
    lines = []
    for msg in messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content'][:450]}")
    return "\n".join(lines)


def build_title(question):
    title = question.strip().replace("\n", " ")
    return (title[:47] + "...") if len(title) > 50 else (title or "New Chat")


def is_medical_query(query):
    words = set(re.findall(r"[a-z]+", query))
    return bool(words & MEDICAL_KEYWORDS) or any(word in query for word in MEDICAL_KEYWORDS)


def contains_any(query, phrases):
    return any(phrase in query for phrase in phrases)


def has_medical_history(chat_history_text):
    if not chat_history_text or chat_history_text == "No previous messages.":
        return False
    return is_medical_query(normalize(chat_history_text))


def is_follow_up_query(query, chat_history_text):
    if not has_medical_history(chat_history_text):
        return False
    words = set(re.findall(r"[a-z0-9]+", query))
    if len(words) <= 12 and words & FOLLOW_UP_HINTS:
        return True
    return any(pattern in query for pattern in DOCTOR_SOON_PATTERNS + EMERGENCY_PATTERNS)


def triage_level(query):
    if any(pattern in query for pattern in EMERGENCY_PATTERNS):
        return "urgent"
    if any(pattern in query for pattern in DOCTOR_SOON_PATTERNS):
        return "soon"
    return "self_care"


def special_response(query, lang):
    if query in GREETINGS_EN or query in GREETINGS_HI:
        if lang == "hi":
            return (
                "Namaste! Main MediSense AI hoon, aapka health information assistant.\n\n"
                "Aap symptoms, disease information, prevention, ya self-care ke baare me Hindi/Hinglish ya English me puch sakte ho."
            )
        return (
            "Hello! I'm MediSense AI, your health information assistant.\n\n"
            "You can ask about symptoms, disease information, prevention, or safe self-care in English or Hindi/Hinglish."
        )

    if contains_any(query, THANKS):
        if lang == "hi":
            return (
                "You're welcome! Khushi hui help karke.\n\n"
                "Agar symptoms 2-3 din se zyada rahen, worsen ho rahe hon, ya breathing issue/chest pain/high fever jaisa red flag ho, to doctor se consult karna best rahega."
            )
        return (
            "You're welcome! I'm glad I could help.\n\n"
            "Keep monitoring your symptoms, stay hydrated, and consult a doctor if symptoms persist, worsen, or you notice any red flags like breathing trouble, chest pain, very high fever, confusion, or dehydration."
        )

    if contains_any(query, ACKNOWLEDGEMENTS):
        if lang == "hi":
            return "Theek hai. Agar koi symptom change ho ya naya doubt aaye, mujhe bata dena."
        return "Got it. If anything changes or you want to check another symptom, tell me."

    if contains_any(query, GOODBYES):
        return "Goodbye! Take care of your health."

    if contains_any(query, ABOUT):
        if lang == "hi":
            return (
                "Main MediSense AI hoon. Main symptoms samajhne, possible causes explain karne, prevention aur self-care tips dene me help karta hoon.\n\n"
                "Main doctor ki jagah nahi le sakta, diagnosis confirm nahi karta, aur medicines prescribe nahi karta."
            )
        return (
            "I'm MediSense AI. I help explain symptoms, possible causes, prevention, and safe self-care.\n\n"
            "I cannot replace a doctor, confirm a diagnosis, or prescribe medicines."
        )
    return None


def enrich_question(question, chat_history_text, care_level):
    return (
        f"Care level detected by app: {care_level}\n"
        f"Recent conversation:\n{chat_history_text}\n\n"
        f"Current user message: {question}"
    )


def extract_source_names(source_documents):
    names = []
    for doc in source_documents[:4]:
        name = doc.metadata.get("source_file") or doc.metadata.get("source") or "Knowledge guide"
        if name not in names:
            names.append(name)
    return names


def generate_answer(question, chat_history_text):
    lang = detect_language(question)
    query = normalize(question)
    is_follow_up = is_follow_up_query(query, chat_history_text)

    special = special_response(query, lang)
    if special and not is_follow_up:
        return special, lang, "info", []

    if not is_medical_query(query) and not is_follow_up:
        if lang == "hi":
            return (
                "Main health-related sawalon me hi madad kar sakta hoon.\n\n"
                "Aap symptoms, disease, prevention, ya self-care ke baare me puch sakte ho, jaise: 'mujhe bukhar aur sir dard hai'."
            ), lang, "info", []
        return (
            "I can only help with health-related questions.\n\n"
            "Try asking about symptoms, diseases, prevention, or self-care, for example: 'I have fever and headache'."
        ), lang, "info", []

    care_level = triage_level(query)
    enriched = enrich_question(question, chat_history_text, care_level)

    if lang == "hi":
        enriched = f"IMPORTANT: Reply in Hindi/Hinglish roman only.\n\n{enriched}"
        result = qa_chain_hi.invoke({"query": enriched})
    else:
        enriched = f"IMPORTANT: Reply in English only.\n\n{enriched}"
        result = qa_chain_en.invoke({"query": enriched})

    answer = result["result"].strip()
    sources = extract_source_names(result.get("source_documents", []))

    if care_level == "urgent":
        warning = (
            "**Urgent:** These symptoms may need immediate medical attention. Please contact emergency services or go to the nearest hospital now."
            if lang == "en"
            else "**Urgent:** Yeh symptoms emergency ho sakte hain. Abhi emergency services ya nearest hospital se contact karo."
        )
        if warning not in answer:
            answer = f"{warning}\n\n{answer}"

    return answer, lang, care_level, sources


db.init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/kb-status", methods=["GET"])
def api_kb_status():
    return jsonify(
        {
            "ready": KB_DIR.exists(),
            "source_count": KB_METADATA.get("source_count", 0),
            "chunk_count": KB_METADATA.get("chunk_count", 0),
            "sources": KB_METADATA.get("source_files", [])[:12],
        }
    )


@app.route("/api/conversations", methods=["GET"])
def api_list_conversations():
    return jsonify(db.list_conversations())


@app.route("/api/conversations", methods=["POST"])
def api_create_conversation():
    data = request.get_json(silent=True) or {}
    title = data.get("title", "New Chat")
    return jsonify(db.create_conversation(title))


@app.route("/api/conversations/<conv_id>", methods=["GET"])
def api_get_conversation(conv_id):
    conv = db.get_conversation(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    conv["messages"] = db.get_messages(conv_id)
    return jsonify(conv)


@app.route("/api/conversations/<conv_id>", methods=["DELETE"])
def api_delete_conversation(conv_id):
    db.delete_conversation(conv_id)
    return jsonify({"success": True})


@app.route("/api/conversations/<conv_id>/rename", methods=["PUT"])
def api_rename_conversation(conv_id):
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title required"}), 400
    db.rename_conversation(conv_id, title)
    return jsonify({"success": True, "title": title[:80]})


@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json() or {}
        question = data.get("question", "").strip()
        conv_id = data.get("conversation_id")

        if not question:
            return jsonify({"answer": "Please enter a health-related question."})

        if not conv_id or not db.get_conversation(conv_id):
            conv = db.create_conversation(build_title(question))
            conv_id = conv["id"]

        history = db.get_recent_history(conv_id, max_pairs=4)
        chat_history_text = format_history(history)

        db.add_message(conv_id, "user", question)

        conv = db.get_conversation(conv_id)
        if conv and conv["title"] == "New Chat":
            db.rename_conversation(conv_id, build_title(question))

        answer, lang, care_level, sources = generate_answer(question, chat_history_text)
        db.add_message(conv_id, "assistant", answer)

        return jsonify(
            {
                "answer": answer,
                "conversation_id": conv_id,
                "lang": lang,
                "care_level": care_level,
                "sources": sources,
            }
        )
    except Exception as exc:
        return jsonify({"answer": f"Something went wrong. Please try again.\n\n({exc})"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
