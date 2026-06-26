from flask import Flask, render_template, request, jsonify
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_classic.chains import RetrievalQA
import os
import re
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

import db

app = Flask(__name__)

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = FAISS.load_local(
    "health_faiss_db",
    embeddings,
    allow_dangerous_deserialization=True,
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model="llama-3.3-70b-versatile",
    temperature=0.55,
)

prompt_template_en = """
You are MediSense AI — a warm, caring health assistant having a natural conversation.

IMPORTANT: Respond ONLY in English. Write like a friendly doctor chatting — NOT like a medical report.

NEVER use these formats or headers:
- "Possible Condition" / "Why it may match" / "Self-Care" / "Recommendation"
- Section emoji headers like 🩺 🔍 🛡️ 📌
- Rigid numbered medical report structure

HOW TO RESPOND:

If user describes their SYMPTOMS (e.g. "I have fever and headache"):
1. Start with empathy — acknowledge how they feel
2. In simple words, explain what might be going on (use "could be" / "might be" — never confirm diagnosis)
3. Tell them what they should do right now at home
4. Tell them when to see a doctor
5. If key info is missing, ask 1-2 friendly follow-up questions at the end, such as:
   - "How many days have you been feeling this?"
   - "Do you have any other symptoms?"
   - "Is the pain mild or severe?"

If user asks a GENERAL health question (e.g. "symptoms of diabetes", "how to prevent heart disease"):
1. Answer the question directly — explain clearly what the condition is
2. Describe common symptoms and prevention in natural paragraphs
3. Give practical lifestyle tips in simple language
4. Do NOT treat them as if they have the disease — they are asking for information
5. End gently: suggest consulting a doctor for personal advice

STYLE RULES:
- Use short, readable paragraphs (2-4 sentences each)
- Use bullet points ONLY when listing symptoms or tips — keep it natural
- Use **bold** sparingly for important terms
- Keep response 180-280 words
- Never mention database, PDFs, context, sources, or knowledge base
- Never prescribe specific medicines or dosages

EMERGENCY: If chest pain, breathing difficulty, unconsciousness, severe bleeding, or stroke —
start with urgent medical attention warning, then continue naturally.

Context (use this medical information to inform your answer):
{context}

User message:
{question}

Your reply:
"""

prompt_template_hi = """
आप MediSense AI हैं — एक गर्मजोशी भरा, caring health assistant जो natural conversation करता है।

बहुत महत्वपूर्ण: पूरा जवाब केवल हिंदी में दें। Doctor से बातचीत जैसा लगे — medical report जैसा नहीं।

कभी भी ये format या headers न उपयोग करें:
- "संभावित स्थिति" / rigid sections / emoji section headers 🩺 🔍 🛡️ 📌
- Medical report जैसी कठोर structure

कैसे जवाब दें:

अगर user अपne लक्षण बता रहा है (जैसे "mujhe bukhar aur sir dard hai"):
1. empathy से शुरू करें
2. सरल शब्दों में बताएं क्या हो सकता है ("हो सकता है" — diagnosis confirm न करें)
3. अभी घर पर क्या करें
4. doctor को कब दिखाएं
5. अगर जानकारी incomplete है, अंत में 1-2 सवाल पूछें:
   - "Yeh kitne din se ho raha hai?"
   - "Koi aur symptom bhi hai?"

अगर user GENERAL health सवाल पूछ रहा है (जैसे "diabetes ke lakshan"):
1. सीधे सवाल का जवाब दें — बीमारी समझाएं
2. lakshan aur prevention natural paragraphs में
3. practical tips
4. उन्हें patient न समझें — वे information मांग रहे हैं
5. personal advice के लिए doctor consult की सलाह

Style: छोटे paragraphs, natural tone, 180-280 शब्द, database/PDF/sources का ज़िक्र न करें।

Emergency: सीने में दर्द, सांस की तकलीफ, बेहोशी — तत्काल medical help की चेतावनी से शुरू करें।

Context:
{context}

User message:
{question}

आपका jawab:
"""

PROMPT_EN = PromptTemplate(
    template=prompt_template_en,
    input_variables=["context", "question"],
)

PROMPT_HI = PromptTemplate(
    template=prompt_template_hi,
    input_variables=["context", "question"],
)

qa_chain_en = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    chain_type_kwargs={"prompt": PROMPT_EN},
)

qa_chain_hi = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    chain_type_kwargs={"prompt": PROMPT_HI},
)

GREETINGS_EN = {
    "hi", "hello", "hey", "hii", "hiii",
    "good morning", "good afternoon", "good evening",
}
GREETINGS_HI = {
    "namaste", "namaskar", "kaise ho", "kaise hain", "kaisi ho",
    "pranam", "ram ram", "sat sri akal",
}
THANKS_EN = {"thanks", "thank you", "thankyou", "thanks a lot", "thank you so much"}
THANKS_HI = {"dhanyawad", "dhanyavaad", "shukriya", "bahut dhanyawad", "thank you bhai"}
GOODBYE_EN = {"bye", "goodbye", "see you", "bye bye", "take care"}
GOODBYE_HI = {"alvida", "fir milenge", "phir milte hain", "chalo bye", "ab chalta hun"}
ABOUT_EN = {"who are you", "what can you do", "help", "can you help me", "your name"}
ABOUT_HI = {"tum kaun ho", "aap kaun hain", "kya kar sakte ho", "madad", "meri madad karo", "tumhara naam"}

MEDICAL_KEYWORDS = [
    "fever", "cold", "cough", "headache", "pain", "vomiting",
    "nausea", "dizziness", "fatigue", "weakness",
    "diarrhea", "breathing", "chest", "throat",
    "sore", "asthma", "diabetes", "sugar",
    "head", "body", "eye", "ear", "nose",
    "stomach", "rash", "infection", "virus",
    "bacteria", "covid", "flu", "dengue",
    "malaria", "typhoid", "migraine",
    "doctor", "hospital", "medicine",
    "health", "medical", "symptom", "disease",
    "bp", "pressure", "heart", "kidney",
    "liver", "allergy", "pregnancy",
    "prevent", "prevention", "symptoms", "treatment",
    "bukhar", "khansi", "sardi", "sir",
    "dard", "ulti", "chakkar", "pet",
    "gala", "saans", "kamzori", "jukaam",
    "lakshan", "bimari", "tabiyat", "ilaj",
]

EMERGENCY_KEYWORDS = [
    "chest pain", "can't breathe", "cannot breathe",
    "difficulty breathing", "breathing difficulty",
    "unconscious", "stroke", "heart attack",
    "severe bleeding", "blood vomiting",
]

EMERGENCY_KEYWORDS_HI = [
    "seene me dard", "saans nahi", "saans lene me", "behosh",
    "stroke", "heart attack", "dil ka daura", "bahut khoon",
    "khoon bah raha", "chakkar aa", "behosh ho",
]

HINDI_WORDS = {
    "mujhe", "mera", "meri", "mere", "hai", "hain", "hun", "hoon",
    "kya", "kaise", "kyun", "kab", "kahan", "kaun", "karo", "karein",
    "bukhar", "dard", "khansi", "sardi", "jukaam", "gala", "gale",
    "ulti", "dast", "chakkar", "kamzori", "thakan", "saans",
    "dawai", "dawa", "ilaj", "batao", "bataiye", "bataye",
    "karun", "karna", "lagta", "taklif", "tabiyat", "bimari",
    "lakshan", "dukh", "nahi", "nahin", "bahut", "thoda", "raha", "rahi",
    "apko", "aapko", "aap", "tumhe", "tumko", "meko",
}

HINDI_PHRASES = [
    "ho raha", "ho rahi", "ho gaya", "kitne din", "kya karun",
    "mujhe hai", "gale me", "pet me", "sir dard", "se hai",
    "bukhar hai", "khansi hai", "dard hai",
]


def format_history(messages):
    if not messages:
        return "No previous messages."
    lines = []
    for msg in messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content'][:500]}")
    return "\n".join(lines)


def build_title(question):
    title = question.strip().replace("\n", " ")
    if len(title) > 50:
        title = title[:47] + "..."
    return title or "New Chat"


def detect_language(text):
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    lower = text.lower().strip()

    for phrase in HINDI_PHRASES:
        if phrase in lower:
            return "hi"

    for phrase in GREETINGS_HI | THANKS_HI | GOODBYE_HI | ABOUT_HI:
        if phrase in lower:
            return "hi"

    words = set(re.findall(r"[a-z]+", lower))
    hindi_matches = len(words & HINDI_WORDS)

    if hindi_matches >= 2:
        return "hi"

    if hindi_matches >= 1 and len(words) <= 5:
        return "hi"

    return "en"


def handle_special_query(query, lang):
    if lang == "hi":
        if any(g in query for g in GREETINGS_HI) or query in {"hi", "hello", "hey"}:
            return (
                "Namaste! Main MediSense AI hoon — aapka health assistant.\n\n"
                "Aap mujhse apne symptoms, bimari ki jaankari, ya prevention ke baare mein "
                "Hindi ya English mein puch sakte hain. Aaj main aapki kaise madad kar sakta hoon?"
            )

        if any(w in query for w in THANKS_HI):
            return (
                "Koi baat nahi! Khushi hui madad kar ke.\n\n"
                "Agar symptoms zyada din tak rahein to doctor se zaroor milen. Apna khayal rakhiye!"
            )

        if any(w in query for w in GOODBYE_HI):
            return "Alvida! Apna swasthya ka khayal rakhiye. Phir milenge!"

        if any(w in query for w in ABOUT_HI):
            return (
                "Main MediSense AI hoon — aapka AI health assistant.\n\n"
                "Main symptoms samajhne, bimari ki jaankari, aur self-care tips mein madad karta hoon. "
                "Lekin main doctor ki jagah nahi le sakta aur dawai prescribe nahi karta.\n\n"
                "Koi bhi health sawal puchiye!"
            )
        return None

    if any(greet == query for greet in GREETINGS_EN):
        return (
            "Hello! I'm MediSense AI — your personal health assistant.\n\n"
            "Feel free to ask me about symptoms, diseases, prevention, or general health — "
            "in English or Hindi. How can I help you today?"
        )

    if any(word == query for word in THANKS_EN):
        return (
            "You're welcome! Glad I could help.\n\n"
            "If your symptoms persist, please do see a doctor. Take care!"
        )

    if any(word == query for word in GOODBYE_EN):
        return "Goodbye! Take care of your health. Have a wonderful day!"

    if any(word == query for word in ABOUT_EN):
        return (
            "I'm MediSense AI — your AI health assistant.\n\n"
            "I can help you understand symptoms, learn about diseases, and get self-care tips. "
            "I cannot confirm diagnoses or prescribe medicines — always consult a doctor for that.\n\n"
            "What would you like to know?"
        )

    return None


def is_medical_query(query):
    return any(word in query for word in MEDICAL_KEYWORDS)


def enrich_question(question, chat_history_text):
    if not chat_history_text or chat_history_text == "No previous messages.":
        return question
    return (
        "Recent conversation for context:\n"
        f"{chat_history_text}\n\n"
        f"Current message: {question}"
    )


def generate_answer(question, chat_history_text):
    lang = detect_language(question)
    query = question.lower().strip()

    special = handle_special_query(query, lang)
    if special:
        return special, lang

    if not is_medical_query(query):
        if lang == "hi":
            return (
                "Main sirf health aur medical sawalon mein madad karta hoon.\n\n"
                "Jaise: 'Mujhe bukhar hai', 'Diabetes ke lakshan', 'Seene me dard' — "
                "aap kuch bhi puch sakte hain!"
            ), lang

        return (
            "I can only help with health-related questions.\n\n"
            "Try asking about symptoms, diseases, or prevention — "
            "e.g. 'I have fever and headache' or 'symptoms of diabetes'."
        ), lang

    enriched = enrich_question(question, chat_history_text)

    if lang == "en":
        enriched = f"IMPORTANT: User wrote in ENGLISH. Reply in ENGLISH only.\n\n{enriched}"
    else:
        enriched = f"IMPORTANT: User wrote in HINDI/Hinglish. Reply in HINDI only.\n\n{enriched}"

    chain = qa_chain_hi if lang == "hi" else qa_chain_en
    response = chain.invoke({"query": enriched})
    answer = response["result"]

    is_emergency = any(word in query for word in EMERGENCY_KEYWORDS)
    if lang == "hi":
        is_emergency = is_emergency or any(word in query for word in EMERGENCY_KEYWORDS_HI)

    if is_emergency:
        if lang == "hi":
            answer = (
                "**Yeh stithi turant medical madad maang sakti hai.** "
                "Agar symptoms gambhir hain to abhi doctor ya emergency services se sampark karein.\n\n"
                + answer
            )
        else:
            answer = (
                "**This may need urgent medical attention.** "
                "If symptoms are severe, please contact a doctor or emergency services right away.\n\n"
                + answer
            )

    return answer, lang


db.init_db()


@app.route("/")
def home():
    return render_template("index.html")


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

        if not conv_id:
            conv = db.create_conversation(build_title(question))
            conv_id = conv["id"]
        elif not db.get_conversation(conv_id):
            conv = db.create_conversation(build_title(question))
            conv_id = conv["id"]

        history = db.get_recent_history(conv_id, max_pairs=4)
        chat_history_text = format_history(history)

        db.add_message(conv_id, "user", question)

        conv = db.get_conversation(conv_id)
        if conv and conv["title"] == "New Chat":
            db.rename_conversation(conv_id, build_title(question))

        answer, lang = generate_answer(question, chat_history_text)
        db.add_message(conv_id, "assistant", answer)

        return jsonify({
            "answer": answer,
            "conversation_id": conv_id,
            "lang": lang,
        })

    except Exception as e:
        return jsonify({"answer": f"Something went wrong. Please try again.\n\n({str(e)})"})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
    )
